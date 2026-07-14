"""
strategy_adapter.py — Bridges existing swing.py strategy functions to a clean
interface expected by the backtest engine.

Each strategy function in swing.py has signature:
    func(df: pd.DataFrame, ticker: str) -> Optional[Dict]

The returned dict has these relevant keys:
    type: "LONG" | "SHORT"
    entry_price: float
    stop_loss: float
    holding_period: str  (e.g. "Swing (10 days)", "3-4 days")
    confidence: int
    priority: str
    win_rate: str
    strategy: str

This adapter wraps each into a StrategyMeta + provides a unified scan call.
"""
import re
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

# Ensure agent/ package is importable (project root on path)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from agent.strategies.swing import SWING_STRATEGIES
from app.core.spy_momentum import DYNAMIC_ID, STATIC_ID


@dataclass
class StrategyMeta:
    id: str          # snake_case identifier
    name: str        # display name
    priority: str    # ELITE | HIGH | MEDIUM
    win_rate: str
    holding_period: str
    direction_hint: str  # LONG | SHORT | BOTH
    description: str = ""
    func: object = field(repr=False, default=None)


def _parse_holding_days(holding_str: str) -> int:
    """Extract a rough day count from strings like 'Swing (10 days)', '3-4 days', 'Monthly'."""
    s = holding_str.lower()
    if "month" in s:
        return 20
    m = re.search(r"(\d+)\s*-\s*(\d+)", s)
    if m:
        return int(m.group(2))  # use upper bound
    m = re.search(r"(\d+)\s*day", s)
    if m:
        return int(m.group(1))
    if "swing" in s:
        return 10
    if "long" in s or "medium" in s:
        return 15
    if "short" in s or "variable" in s:
        return 5
    return 10  # default fallback


def _make_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# ── Build the canonical strategy registry ────────────────────────────────────

# We run a quick dummy probe on the SWING_STRATEGIES list to extract metadata.
# Using a tiny 300-row random DataFrame so we get the dict keys even if signal=None.
_dummy_df = pd.DataFrame({
    "Ticker": ["PROBE"] * 300,
    "Date": pd.date_range("2020-01-01", periods=300),
    "Open": 100.0, "High": 102.0, "Low": 98.0, "Close": 101.0, "Volume": 1_000_000,
})

_REGISTRY: Dict[str, StrategyMeta] = {}

for _s in SWING_STRATEGIES:
    _meta = StrategyMeta(
        id=_make_id(_s["name"]),
        name=_s["name"],
        priority="MEDIUM",
        win_rate="N/A",
        holding_period="Swing",
        direction_hint="BOTH",
        func=_s["func"],
    )
    # Try probing to extract real metadata (strategy may legitimately return None on dummy data)
    try:
        _result = _s["func"](_dummy_df, "PROBE")
        if _result:
            _meta.priority = _result.get("priority", "MEDIUM")
            _meta.win_rate = _result.get("win_rate", "N/A")
            _meta.holding_period = _result.get("holding_period", "Swing")
            _meta.direction_hint = _result.get("type", "BOTH")
    except Exception:
        pass
    _REGISTRY[_meta.id] = _meta

_REGISTRY[STATIC_ID] = StrategyMeta(
    id=STATIC_ID,
    name="SPY MOMENTUM-2 Static",
    priority="ELITE",
    win_rate="Portfolio",
    holding_period="Monthly",
    direction_hint="BOTH",
    description="Monthly S&P 500 long/short momentum portfolio: long top 2 prior 2-day gainers and short bottom 2 prior 2-day losers, fixed starting capital.",
    func=None,
)

_REGISTRY[DYNAMIC_ID] = StrategyMeta(
    id=DYNAMIC_ID,
    name="SPY MOMENTUM-2 Dynamic",
    priority="ELITE",
    win_rate="Portfolio",
    holding_period="Monthly + Add",
    direction_hint="BOTH",
    description="Monthly S&P 500 long/short momentum portfolio: long top 2 prior 2-day gainers and short bottom 2 prior 2-day losers, adding the same capital each monthly rebalance.",
    func=None,
)


def list_strategies() -> List[Dict]:
    """Return all strategies as JSON-serialisable dicts."""
    result = []
    for meta in _REGISTRY.values():
        result.append({
            "id": meta.id,
            "name": meta.name,
            "priority": meta.priority,
            "win_rate": meta.win_rate,
            "holding_period": meta.holding_period,
            "direction_hint": meta.direction_hint,
        })
    return result


def get_strategy(strategy_id: str) -> Optional[StrategyMeta]:
    return _REGISTRY.get(strategy_id)


def scan_strategy(strategy_id: str, df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    """
    Run a single strategy on the given DataFrame.
    The df must have columns: Ticker, Date, Open, High, Low, Close, Volume.
    Injects the Ticker column value = ticker for filtering inside strategy functions.
    Returns raw strategy dict or None.
    """
    meta = _REGISTRY.get(strategy_id)
    if not meta or not meta.func:
        return None
    # Ensure Ticker column matches what strategy functions expect
    df = df.copy()
    df["Ticker"] = ticker
    try:
        return meta.func(df, ticker)
    except Exception:
        return None


def get_holding_days(strategy_id: str, signal: Optional[Dict] = None) -> int:
    """Return the expected holding period in trading days for a strategy."""
    if signal and "holding_period" in signal:
        return _parse_holding_days(signal["holding_period"])
    meta = _REGISTRY.get(strategy_id)
    if meta:
        return _parse_holding_days(meta.holding_period)
    return 10
