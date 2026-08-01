"""
data_service.py — OHLCV fetch, cache, and CSV upload logic for the MIDAS web app.
Uses SQLite as the primary cache. yfinance is only called when cache is missing/stale.
"""
import io
import time
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

from app.core.db import upsert_ohlcv, get_ohlcv, get_ticker_date_range

logger = logging.getLogger(__name__)

# Presets: label → (years back from today, or None for max)
DATE_PRESETS: Dict[str, Optional[int]] = {
    "1Y": 1,
    "3Y": 3,
    "5Y": 5,
    "10Y": 10,
    "MAX": None,
}

# How old cached data can be before we consider it stale (in hours)
STALE_THRESHOLD_HOURS = 24


def _yfinance_end(date_to: str) -> str:
    """Convert MIDAS inclusive date_to into yfinance's exclusive end date."""
    return str(pd.Timestamp(date_to).date() + timedelta(days=1))


def _cache_required_max_date(date_to: str) -> str:
    """
    Return the latest daily bar date needed for cache coverage.

    The UI often requests "today". On weekends there is no daily bar for today,
    so a cache ending on the most recent weekday should satisfy the request.
    This avoids repeated refetches that can never produce a Saturday/Sunday bar.
    """
    requested = pd.Timestamp(date_to).date()
    today = date.today()
    if requested >= today:
        expected = today
        while expected.weekday() >= 5:
            expected -= timedelta(days=1)
        return str(expected)
    return date_to


def resolve_preset(preset: str) -> Tuple[str, str]:
    """Convert a preset label to (date_from, date_to) ISO strings."""
    today = date.today()
    years = DATE_PRESETS.get(preset.upper())
    if years is None:
        date_from = "1990-01-01"
    else:
        date_from = str(today - timedelta(days=years * 365))
    date_to = str(today)
    return date_from, date_to


def fetch_and_cache(ticker: str, date_from: str, date_to: str, force: bool = False) -> Dict:
    """
    Fetch OHLCV for ticker/range. Uses SQLite cache first.
    If force=True, always re-fetches from yfinance.
    Returns: { rows: int, cached: bool, ticker: str, date_from, date_to }
    """
    ticker = ticker.upper().strip()

    # Check if cache covers the requested range
    if not force:
        existing = get_ticker_date_range(ticker)
        required_max_date = _cache_required_max_date(date_to)
        if existing and existing["min_date"] <= date_from and existing["max_date"] >= required_max_date:
            logger.info("Cache hit for %s %s→%s", ticker, date_from, date_to)
            cached_rows = get_ohlcv(ticker, date_from, date_to)
            return {"rows": len(cached_rows), "cached": True, "ticker": ticker,
                    "date_from": date_from, "date_to": date_to}

    logger.info("Fetching from yfinance: %s %s→%s", ticker, date_from, date_to)
    try:
        raw = yf.download(
            ticker,
            start=date_from,
            end=_yfinance_end(date_to),
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        raise RuntimeError(f"yfinance error for {ticker}: {e}") from e

    if raw is None or raw.empty:
        raise ValueError(f"No data returned for ticker '{ticker}'. Check the symbol.")

    raw = raw.reset_index()

    # Normalise column names (yfinance sometimes returns MultiIndex)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    col_map = {c.lower(): c for c in raw.columns}
    date_col = col_map.get("date") or col_map.get("datetime") or "Date"

    rows = []
    for _, row in raw.iterrows():
        try:
            rows.append({
                "ticker": ticker,
                "date": str(pd.Timestamp(row[date_col]).date()),
                "open": float(row.get("Open", row.get("open", 0))),
                "high": float(row.get("High", row.get("high", 0))),
                "low": float(row.get("Low", row.get("low", 0))),
                "close": float(row.get("Close", row.get("close", 0))),
                "volume": int(row.get("Volume", row.get("volume", 0))),
            })
        except Exception:
            continue

    if not rows:
        raise ValueError(f"Could not parse OHLCV data for {ticker}.")

    upsert_ohlcv(rows)
    return {"rows": len(rows), "cached": False, "ticker": ticker,
            "date_from": date_from, "date_to": date_to}


def load_from_cache(ticker: str, date_from: str, date_to: str) -> List[Dict]:
    """Return cached OHLCV rows for ticker/range. Raises if empty."""
    ticker = ticker.upper().strip()
    rows = get_ohlcv(ticker, date_from, date_to)
    if not rows:
        raise ValueError(f"No cached data for {ticker} {date_from}→{date_to}. Fetch first.")
    return rows


def rows_to_dataframe(rows: List[Dict]) -> pd.DataFrame:
    """Convert list of OHLCV dicts to a sorted DataFrame with parsed dates."""
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    # Standardise to Title case for strategy compatibility
    df = df.rename(columns={
        "date": "Date", "open": "Open", "high": "High",
        "low": "Low", "close": "Close", "volume": "Volume",
    })
    df = df.sort_values("Date").reset_index(drop=True)
    if "Ticker" not in df.columns and "ticker" not in df.columns:
        df["Ticker"] = ""
    return df


def parse_csv_upload(content: bytes, ticker_override: str = "") -> Tuple[str, List[Dict]]:
    """
    Parse a user-uploaded CSV file.
    Expected columns (case-insensitive): Date, Open, High, Low, Close, Volume.
    Optional: Ticker column.
    Returns: (ticker, list of OHLCV dicts ready for upsert_ohlcv)
    """
    try:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        raise ValueError(f"Could not parse CSV: {e}")

    # Normalise column names
    df.columns = [c.strip().title() for c in df.columns]

    required = {"Date", "Open", "High", "Low", "Close", "Volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}. Got: {list(df.columns)}")

    # Determine ticker
    if ticker_override:
        ticker = ticker_override.upper().strip()
    elif "Ticker" in df.columns:
        ticker = str(df["Ticker"].iloc[0]).upper().strip()
    else:
        raise ValueError("CSV has no Ticker column. Provide ticker in the upload request.")

    rows = []
    for _, row in df.iterrows():
        try:
            rows.append({
                "ticker": ticker,
                "date": str(pd.Timestamp(row["Date"]).date()),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(float(row["Volume"])),
            })
        except Exception:
            continue

    if not rows:
        raise ValueError("No valid rows found in CSV.")

    if len(rows) > 100_000:
        raise ValueError(f"CSV too large: {len(rows)} rows. Max 100,000.")

    upsert_ohlcv(rows)
    return ticker, rows
