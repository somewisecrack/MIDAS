"""
data.py — /api/data/* endpoints: fetch, cache read, upload.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.core.data_service import (
    fetch_and_cache,
    load_from_cache,
    parse_csv_upload,
    resolve_preset,
)
from app.core.db import get_ticker_date_range, get_cached_tickers

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["data"])


class FetchRequest(BaseModel):
    ticker: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    preset: Optional[str] = None   # "1Y" | "3Y" | "5Y" | "10Y" | "MAX"
    force: bool = False


@router.post("/fetch")
async def fetch_data(req: FetchRequest):
    """Fetch OHLCV data from Yahoo Finance and cache locally."""
    if req.preset:
        date_from, date_to = resolve_preset(req.preset)
    elif req.date_from and req.date_to:
        date_from, date_to = req.date_from, req.date_to
    else:
        date_from, date_to = resolve_preset("1Y")

    try:
        result = fetch_and_cache(req.ticker, date_from, date_to, force=req.force)
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{ticker}")
async def get_data(
    ticker: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    preset: Optional[str] = None,
):
    """Return cached OHLCV rows for the given ticker and date range."""
    if preset:
        date_from, date_to = resolve_preset(preset)
    elif not (date_from and date_to):
        date_from, date_to = resolve_preset("1Y")

    try:
        rows = load_from_cache(ticker, date_from, date_to)
        meta = get_ticker_date_range(ticker)
        return {
            "ticker": ticker.upper(),
            "date_from": date_from,
            "date_to": date_to,
            "rows": len(rows),
            "data": rows,
            "meta": meta,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    ticker: Optional[str] = Form(None),
):
    """Upload a CSV file with OHLCV data. Optionally override the ticker symbol."""
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50 MB cap
        raise HTTPException(status_code=413, detail="File too large (max 50 MB).")
    try:
        detected_ticker, rows = parse_csv_upload(content, ticker_override=ticker or "")
        return {
            "status": "ok",
            "ticker": detected_ticker,
            "rows_imported": len(rows),
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/")
async def list_cached():
    """List all tickers available in the local cache."""
    tickers = get_cached_tickers()
    return {"tickers": tickers, "count": len(tickers)}
