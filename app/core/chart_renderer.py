"""
chart_renderer.py — Server-side candlestick chart PNG generation using mplfinance.
Used to produce images that are sent to Gemma's vision model for pattern matching.
"""
import base64
import io
import logging
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

logger = logging.getLogger(__name__)


def render_window_png(
    data_rows: List[Dict],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    width_inches: int = 12,
    height_inches: int = 6,
    style: str = "nightclouds",
) -> str:
    """
    Render a candlestick chart for the specified date window.
    Returns base64-encoded PNG string suitable for Ollama's images field.

    Args:
        data_rows: list of dicts with keys: date, open, high, low, close, volume
        date_from: start date filter (ISO string)
        date_to: end date filter (ISO string)
        width_inches, height_inches: chart size
        style: mplfinance style name

    Returns:
        base64-encoded PNG string
    """
    df = pd.DataFrame(data_rows)
    df["Date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                             "close": "Close", "volume": "Volume"})
    df = df.set_index("Date").sort_index()

    if date_from:
        df = df[df.index >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df.index <= pd.Timestamp(date_to)]

    if df.empty:
        raise ValueError("No data in specified window for chart rendering.")

    # Cap at 500 bars for readability
    if len(df) > 500:
        df = df.tail(500)

    buf = io.BytesIO()
    try:
        fig, axes = mpf.plot(
            df,
            type="candle",
            style=style,
            volume=True,
            figsize=(width_inches, height_inches),
            returnfig=True,
            tight_layout=True,
        )
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
    except Exception as e:
        logger.error("mplfinance render error: %s", e)
        raise

    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def render_with_markers(
    data_rows: List[Dict],
    trades: List[Dict],
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """
    Render chart with buy/sell markers for a trade list.
    trades: list of dicts with entry_date, exit_date, direction.
    Returns base64 PNG.
    """
    df = pd.DataFrame(data_rows)
    df["Date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                             "close": "Close", "volume": "Volume"})
    df = df.set_index("Date").sort_index()

    if date_from:
        df = df[df.index >= pd.Timestamp(date_from)]
    if date_to:
        df = df[df.index <= pd.Timestamp(date_to)]

    if df.empty:
        raise ValueError("No data in window for marker chart.")

    # Build addplot markers
    buy_markers = pd.Series(index=df.index, dtype=float)
    sell_markers = pd.Series(index=df.index, dtype=float)

    for t in trades:
        entry_ts = pd.Timestamp(t["entry_date"])
        exit_ts = pd.Timestamp(t["exit_date"])
        if entry_ts in df.index:
            buy_markers[entry_ts] = df.loc[entry_ts, "Low"] * 0.98
        if exit_ts in df.index:
            sell_markers[exit_ts] = df.loc[exit_ts, "High"] * 1.02

    apds = []
    if buy_markers.notna().any():
        apds.append(mpf.make_addplot(buy_markers, type="scatter", markersize=80,
                                     marker="^", color="#26a641"))
    if sell_markers.notna().any():
        apds.append(mpf.make_addplot(sell_markers, type="scatter", markersize=80,
                                     marker="v", color="#f85149"))

    buf = io.BytesIO()
    fig, axes = mpf.plot(
        df,
        type="candle",
        style="nightclouds",
        volume=True,
        figsize=(14, 7),
        addplot=apds if apds else None,
        returnfig=True,
        tight_layout=True,
    )
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)

    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
