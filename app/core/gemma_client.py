"""
gemma_client.py — Thin wrapper around Ollama's HTTP API for MIDAS pattern search
and result interpretation. Uses gemma3:12b by default, falls back to gemma3:4b.

All Gemma calls are streamed and collected synchronously.
Image search encodes a server-side mplfinance PNG as base64.
"""
import base64
import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

import os

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "gemma3:12b")
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "gemma3:4b")
TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", 120))


def is_available() -> Dict[str, Any]:
    """Check if Ollama is running and which models are available."""
    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        if r.status_code != 200:
            return {"available": False, "models": []}
        models = [m["name"] for m in r.json().get("models", [])]
        return {"available": True, "models": models}
    except Exception:
        return {"available": False, "models": []}


def _pick_model() -> str:
    status = is_available()
    if not status["available"]:
        raise RuntimeError("Ollama is not running. Start it with: ollama serve")
    models = status["models"]
    for candidate in [PRIMARY_MODEL, FALLBACK_MODEL]:
        if any(candidate in m for m in models):
            return candidate
    # Use whatever is available if neither default is pulled
    if models:
        return models[0]
    raise RuntimeError(
        f"No models available in Ollama. Pull one with: ollama pull {PRIMARY_MODEL}"
    )


def _generate(prompt: str, images: Optional[List[str]] = None, model: Optional[str] = None) -> str:
    """Call Ollama /api/generate and collect the full response."""
    if model is None:
        model = _pick_model()

    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,   # deterministic-leaning for JSON extraction
            "num_predict": 2048,
        },
    }
    if images:
        payload["images"] = images

    try:
        r = httpx.post(
            f"{OLLAMA_BASE}/api/generate",
            json=payload,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("response", "")
    except httpx.TimeoutException:
        raise RuntimeError(f"Ollama timed out after {TIMEOUT}s. Try a smaller model or shorter date range.")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Ollama API error: {e.response.status_code} — {e.response.text[:200]}")


def _extract_json(text: str) -> Any:
    """Pull the first JSON array or object out of a potentially messy LLM response."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Find JSON block
    m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Find first [...] or {...}
    m = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return []


# ── Pattern search: text query ─────────────────────────────────────────────────

_TEXT_PATTERN_PROMPT = """You are a financial market analyst. You are given daily OHLCV data for {ticker} from {date_from} to {date_to}.

The user wants to find historical occurrences of this pattern:
"{query}"

Below is the OHLCV data (date, open, high, low, close, volume). Analyze it carefully:

{data_sample}

Find up to 5 date windows where the pattern described above occurred most clearly.
For each match, specify the start and end date of the pattern (the window that shows the setup, not the full dataset).
Rate your confidence from 0-100.

Return ONLY a valid JSON array, no other text. Format:
[
  {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "confidence": 75, "explanation": "One sentence describing why this matches."}}
]

If no pattern is found, return: []
"""


def find_pattern_text(ticker: str, data_rows: List[Dict], query: str) -> List[Dict]:
    """
    Ask Gemma to find occurrences of a described pattern in the OHLCV data.
    Returns list of { start, end, confidence, explanation } dicts.
    """
    # Build a compact data summary (at most 500 rows)
    rows = data_rows[-500:] if len(data_rows) > 500 else data_rows
    lines = ["date,open,high,low,close,volume"]
    for r in rows:
        lines.append(f"{r['date']},{r['open']:.2f},{r['high']:.2f},{r['low']:.2f},{r['close']:.2f},{int(r['volume'])}")
    data_sample = "\n".join(lines)

    date_from = rows[0]["date"] if rows else ""
    date_to = rows[-1]["date"] if rows else ""

    prompt = _TEXT_PATTERN_PROMPT.format(
        ticker=ticker,
        date_from=date_from,
        date_to=date_to,
        query=query,
        data_sample=data_sample,
    )

    raw = _generate(prompt)
    result = _extract_json(raw)
    if isinstance(result, list):
        return result
    return []


# ── Pattern search: image query ────────────────────────────────────────────────

_IMAGE_PATTERN_PROMPT = """You are a financial market analyst with expertise in chart patterns.

I am showing you a chart image that represents a specific price pattern from {ticker}.
The image shows a chart from {date_from} to {date_to}.

Below is the OHLCV data for the same ticker across a wider time range:

{data_sample}

1. First, describe what pattern you see in the uploaded chart image (2-3 sentences).
2. Then find up to 5 historical date windows in the OHLCV data where a similar pattern occurred.

Return ONLY a valid JSON array, no other text. Format:
[
  {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "confidence": 75, "explanation": "One sentence describing the match."}}
]

If no similar pattern is found, return: []
"""


def find_pattern_image(
    ticker: str,
    data_rows: List[Dict],
    image_b64: str,
    image_date_from: str,
    image_date_to: str,
) -> List[Dict]:
    """
    Ask Gemma (vision) to match a chart image against historical OHLCV data.
    image_b64: base64-encoded PNG of the chart window.
    Returns list of { start, end, confidence, explanation } dicts.
    """
    rows = data_rows[-500:] if len(data_rows) > 500 else data_rows
    lines = ["date,open,high,low,close,volume"]
    for r in rows:
        lines.append(f"{r['date']},{r['open']:.2f},{r['high']:.2f},{r['low']:.2f},{r['close']:.2f},{int(r['volume'])}")
    data_sample = "\n".join(lines)

    prompt = _IMAGE_PATTERN_PROMPT.format(
        ticker=ticker,
        date_from=image_date_from,
        date_to=image_date_to,
        data_sample=data_sample,
    )

    raw = _generate(prompt, images=[image_b64])
    result = _extract_json(raw)
    if isinstance(result, list):
        return result
    return []


# ── Backtest interpretation ────────────────────────────────────────────────────

_INTERPRET_PROMPT = """You are a trading strategy analyst. You have just run a backtest with the following results:

Ticker: {ticker}
Date Range: {date_from} to {date_to}
Strategies: {strategies}

Performance Summary:
- Total Trades: {total_trades}
- Win Rate: {win_rate}%
- Avg Return per Trade: {avg_return}%
- Profit Factor: {profit_factor}
- Max Drawdown: {max_drawdown}%
- Total Return: {total_return}%
- Sharpe Ratio: {sharpe}

Sample Trades (top 5 by return):
{sample_trades}

Provide a concise, honest 3-paragraph analysis:
1. Overall assessment of these results (is this statistically meaningful? what are the concerns?)
2. What is working (if anything)?
3. What conditions or regimes might make these strategies more or less effective?

Be direct and specific. Do not use generic disclaimers. Under 250 words.
"""


def interpret_backtest(
    ticker: str,
    date_from: str,
    date_to: str,
    strategies: List[str],
    stats: Dict,
    trades: List[Dict],
) -> str:
    """
    Ask Gemma to provide a plain-English interpretation of backtest results.
    Returns the interpretation as a string.
    """
    top_trades = sorted(trades, key=lambda t: t.get("return_pct", 0), reverse=True)[:5]
    trade_lines = []
    for t in top_trades:
        trade_lines.append(
            f"  {t['entry_date']} → {t['exit_date']} | {t['strategy']} | "
            f"{t['direction']} | {t['return_pct']:.2f}%"
        )
    sample_trades = "\n".join(trade_lines) if trade_lines else "  (no trades)"

    prompt = _INTERPRET_PROMPT.format(
        ticker=ticker,
        date_from=date_from,
        date_to=date_to,
        strategies=", ".join(strategies),
        total_trades=stats.get("total_trades", 0),
        win_rate=stats.get("win_rate", 0),
        avg_return=stats.get("avg_return", 0),
        profit_factor=stats.get("profit_factor", 0),
        max_drawdown=stats.get("max_drawdown", 0),
        total_return=stats.get("total_return", 0),
        sharpe=stats.get("sharpe", 0),
        sample_trades=sample_trades,
    )

    return _generate(prompt)
