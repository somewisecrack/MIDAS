"""
gemma.py — /api/gemma/* endpoints: pattern search (text + image), interpretation.
Gracefully handles Ollama being offline — returns 503 with clear message.

MIDAS uses Gemma via Ollama for pattern search and interpretation.
"""
import base64
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.gemma_client import (
    is_available,
    find_pattern_text,
    find_pattern_image,
    interpret_backtest,
    interpret_scan,
)
from app.core.data_service import load_from_cache, resolve_preset
from app.core.chart_renderer import render_window_png
from app.core.db import get_backtest_run, save_pattern_search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gemma", tags=["gemma"])


def _require_ollama():
    status = is_available()
    if not status["available"]:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Ollama is not running.",
                "fix": "Run: ollama serve  (then: ollama pull gemma3:12b)",
            },
        )
    return status


class TextPatternRequest(BaseModel):
    ticker: str
    query: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    preset: Optional[str] = None


class InterpretRequest(BaseModel):
    run_id: str


class ScanInterpretRequest(BaseModel):
    scope: str
    date_from: str
    date_to: str
    results: List[dict]


class ChatMessage(BaseModel):
    role: str        # "user" | "assistant"
    content: str
    image_b64: Optional[str] = None   # base64 PNG/JPG if multimodal


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None       # override model selection
    stream: bool = True


@router.get("/status")
async def status():
    """Check if Ollama is running and which models are available."""
    s = is_available()
    return s


@router.get("/models")
async def list_models():
    """Return available Ollama models."""
    s = is_available()
    if not s["available"]:
        return {"available": False, "models": []}
    return {"available": True, "models": s.get("models", [])}


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Non-streaming chat endpoint. Returns the full assistant response.
    Supports multi-modal messages (text + base64 image).
    """
    _require_ollama()

    import httpx
    from app.core.gemma_client import _pick_model, OLLAMA_BASE, TIMEOUT

    model = req.model or _pick_model()

    ollama_messages = []
    for msg in req.messages:
        m: dict = {"role": msg.role, "content": msg.content}
        if msg.image_b64:
            m["images"] = [msg.image_b64]
        ollama_messages.append(m)

    try:
        r = httpx.post(
            f"{OLLAMA_BASE}/api/chat",
            json={"model": model, "messages": ollama_messages, "stream": False},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        reply = data.get("message", {}).get("content", "")
        return {"role": "assistant", "content": reply, "model": model}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Ollama timed out after {TIMEOUT}s.")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Streaming chat via Server-Sent Events.
    Each chunk: data: {"token": "..."}\n\n
    Final:       data: [DONE]\n\n
    """
    _require_ollama()

    import httpx
    import json as _json
    from fastapi.responses import StreamingResponse
    from app.core.gemma_client import _pick_model, OLLAMA_BASE, TIMEOUT

    model = req.model or _pick_model()

    ollama_messages = []
    for msg in req.messages:
        m: dict = {"role": msg.role, "content": msg.content}
        if msg.image_b64:
            m["images"] = [msg.image_b64]
        ollama_messages.append(m)

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_BASE}/api/chat",
                    json={"model": model, "messages": ollama_messages, "stream": True},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = _json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield f"data: {_json.dumps({'token': token})}\n\n"
                            if chunk.get("done"):
                                yield "data: [DONE]\n\n"
                                return
                        except Exception:
                            continue
        except Exception as e:
            yield f"data: {_json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/pattern/text")
async def pattern_text(req: TextPatternRequest):
    """Find historical occurrences of a described pattern using Gemma."""
    _require_ollama()

    if req.preset:
        date_from, date_to = resolve_preset(req.preset)
    elif req.date_from and req.date_to:
        date_from, date_to = req.date_from, req.date_to
    else:
        date_from, date_to = resolve_preset("1Y")

    try:
        rows = load_from_cache(req.ticker, date_from, date_to)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        windows = find_pattern_text(req.ticker.upper(), rows, req.query)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    search_id = save_pattern_search(
        ticker=req.ticker.upper(),
        query_type="text",
        query=req.query,
        matched_windows=windows,
    )

    return {
        "search_id": search_id,
        "ticker": req.ticker.upper(),
        "query": req.query,
        "windows": windows,
        "count": len(windows),
    }


@router.post("/pattern/image")
async def pattern_image(
    ticker: str = Form(...),
    date_from: Optional[str] = Form(None),
    date_to: Optional[str] = Form(None),
    preset: Optional[str] = Form(None),
    image_date_from: Optional[str] = Form(None),
    image_date_to: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """Find patterns similar to an uploaded chart image using Gemma vision."""
    _require_ollama()

    if preset:
        date_from, date_to = resolve_preset(preset)
    elif not (date_from and date_to):
        date_from, date_to = resolve_preset("1Y")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB).")

    image_b64 = base64.b64encode(content).decode("utf-8")

    try:
        rows = load_from_cache(ticker, date_from, date_to)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    img_from = image_date_from or date_from
    img_to = image_date_to or date_to

    try:
        windows = find_pattern_image(ticker.upper(), rows, image_b64, img_from, img_to)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    search_id = save_pattern_search(
        ticker=ticker.upper(),
        query_type="image",
        query=f"image:{file.filename}",
        matched_windows=windows,
    )

    return {
        "search_id": search_id,
        "ticker": ticker.upper(),
        "windows": windows,
        "count": len(windows),
    }


@router.post("/interpret")
async def interpret(req: InterpretRequest):
    """Ask Gemma for a plain-English interpretation of a backtest run."""
    _require_ollama()

    run = get_backtest_run(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{req.run_id}' not found.")

    try:
        text = interpret_backtest(
            ticker=run["ticker"],
            date_from=run["date_from"],
            date_to=run["date_to"],
            strategies=run["strategy_names"],
            stats=run["stats"],
            trades=run["trades"],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {"run_id": req.run_id, "interpretation": text}


@router.post("/interpret-scan")
async def interpret_scan_results(req: ScanInterpretRequest):
    """Ask Gemma for a plain-English interpretation of scan results."""
    _require_ollama()

    try:
        text = interpret_scan(
            scope=req.scope,
            date_from=req.date_from,
            date_to=req.date_to,
            results=req.results,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {"scope": req.scope, "interpretation": text, "count": len(req.results)}


@router.get("/chart/{ticker}")
async def render_chart(
    ticker: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    preset: Optional[str] = None,
):
    """Render a chart PNG (base64) for the given ticker/window."""
    if preset:
        date_from, date_to = resolve_preset(preset)
    elif not (date_from and date_to):
        date_from, date_to = resolve_preset("1Y")

    try:
        rows = load_from_cache(ticker, date_from, date_to)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        png_b64 = render_window_png(rows, date_from, date_to)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart render error: {e}")

    return {"ticker": ticker.upper(), "png_b64": png_b64}
