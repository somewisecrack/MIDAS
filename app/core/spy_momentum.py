"""
spy_momentum.py - S&P 500 monthly top/bottom momentum portfolio strategies.

SPY MOMENTUM-2 Static:
    Start with fixed capital and rebalance monthly.

SPY MOMENTUM-2 Dynamic:
    Start with fixed capital, add the same amount at every later monthly rebalance,
    then rebalance.

Both variants rank current S&P 500 constituents by the prior 2 trading-day
adjusted-close return ending on the previous trading day, then long the top 2
and short the bottom 2.

SPY_MOMENTUM_2D8_LONG_ONLY:
    Start with fixed capital, add the same amount at every later monthly
    rebalance, then long the top 8 prior 2-day gainers.

SPY_MOMENTUM_20D5_LONG_ONLY:
    Start with fixed capital, add the same amount at every later monthly
    rebalance, then long the top 5 prior 20-day gainers.

All variants are defined by a row in _PROFILES (lookback, long/short basket
sizes, monthly-contribution behaviour, display name); the backtest and scan
paths are shared and carry no per-strategy branching.
"""
import logging
from dataclasses import dataclass, asdict
from datetime import date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

from agent.data_loader import get_sp500_tickers

logger = logging.getLogger(__name__)

STATIC_ID = "spy_momentum_2_static"
DYNAMIC_ID = "spy_momentum_2_dynamic"
LONG_ONLY_2D8_ID = "spy_momentum_2d8_long_only"
LONG_ONLY_20D5_ID = "spy_momentum_20d5_long_only"
INITIAL_CAPITAL = 1000.0
MONTHLY_CONTRIBUTION = 1000.0


@dataclass(frozen=True)
class MomentumConfig:
    name: str
    lookback_days: int
    long_count: int
    short_count: int
    dynamic: bool


# One profile per SPY momentum variant. Adding a variant is a single row here:
# ranking lookback, basket sizes, and monthly-contribution behaviour are all
# data-driven, so the backtest and scan paths need no per-strategy branching.
_PROFILES: Dict[str, MomentumConfig] = {
    STATIC_ID:         MomentumConfig("SPY MOMENTUM-2 Static", 2, 2, 2, dynamic=False),
    DYNAMIC_ID:        MomentumConfig("SPY MOMENTUM-2 Dynamic", 2, 2, 2, dynamic=True),
    LONG_ONLY_2D8_ID:  MomentumConfig("SPY MOMENTUM-2D8 Long Only", 2, 8, 0, dynamic=True),
    LONG_ONLY_20D5_ID: MomentumConfig("SPY MOMENTUM-20D5 Long Only", 20, 5, 0, dynamic=True),
}

STRATEGY_IDS = set(_PROFILES)


@dataclass
class PortfolioLeg:
    ticker: str
    strategy: str
    strategy_id: str
    direction: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: Optional[float]
    return_pct: float
    holding_days: int
    mfe: float
    mae: float
    confidence: int
    signal: str = ""
    reasoning: str = ""


def is_spy_momentum_strategy(strategy_id: str) -> bool:
    return strategy_id in _PROFILES


def strategy_name(strategy_id: str) -> str:
    config = _PROFILES.get(strategy_id)
    return config.name if config else strategy_id


def _strategy_config(strategy_id: str) -> MomentumConfig:
    return _PROFILES[strategy_id]


def _download_close_prices(tickers: List[str], start: str, end: str, lookback_days: int = 2) -> pd.DataFrame:
    # Pad the fetch window so there is enough pre-entry history to rank on the
    # lookback. Trading days ≈ calendar days * 5/7, plus a holiday buffer.
    pad_days = max(30, lookback_days * 2 + 15)
    fetch_start = (pd.Timestamp(start) - pd.Timedelta(days=pad_days)).strftime("%Y-%m-%d")
    fetch_end = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.download(
        tickers,
        start=fetch_start,
        end=fetch_end,
        interval="1d",
        auto_adjust=True,
        group_by="column",
        threads=True,
        progress=False,
    )
    if raw is None or raw.empty:
        raise ValueError("No S&P 500 price data returned from yfinance.")
    close = raw["Close"].copy() if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if isinstance(close, pd.Series):
        close = close.to_frame(tickers[0])
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close.sort_index().dropna(axis=1, how="all")


def _month_start_rebalances(prices: pd.DataFrame, date_from: str, date_to: str) -> List[pd.Timestamp]:
    trading_days = prices.index[(prices.index >= pd.Timestamp(date_from)) & (prices.index <= pd.Timestamp(date_to))]
    if trading_days.empty:
        return []
    starts = (
        pd.Series(trading_days, index=trading_days)
        .groupby(pd.Index(trading_days).to_period("M"))
        .first()
    )
    return [pd.Timestamp(x) for x in starts.tolist()]


def _select_baskets(
    prices: pd.DataFrame,
    entry_date: pd.Timestamp,
    long_count: int,
    short_count: int,
    lookback_days: int,
) -> Tuple[List[str], List[str], pd.Series, pd.Timestamp]:
    entry_loc = prices.index.get_loc(entry_date)
    rank_end_loc = entry_loc - 1
    rank_start_loc = rank_end_loc - lookback_days
    if rank_start_loc < 0:
        raise ValueError("Insufficient pre-entry history for momentum ranking.")

    rank_start = prices.index[rank_start_loc]
    rank_end = prices.index[rank_end_loc]
    returns = prices.iloc[rank_end_loc] / prices.iloc[rank_start_loc] - 1.0
    returns = returns.replace([float("inf"), float("-inf")], pd.NA).dropna()
    if len(returns) < long_count + short_count:
        raise ValueError("Insufficient valid symbols for momentum ranking.")

    longs = returns.nlargest(long_count).index.tolist()
    shorts = returns.nsmallest(short_count).index.tolist() if short_count else []
    return longs, shorts, returns, rank_end


def _leg_return(entry_price: float, exit_price: float, direction: str) -> float:
    if entry_price == 0:
        return 0.0
    if direction == "LONG":
        return (exit_price - entry_price) / entry_price
    return (entry_price - exit_price) / entry_price


def _period_return(period_prices: pd.DataFrame, longs: List[str], shorts: List[str]) -> float:
    leg_returns = []
    for ticker in longs:
        leg_returns.append(_leg_return(float(period_prices[ticker].iloc[0]), float(period_prices[ticker].iloc[-1]), "LONG"))
    for ticker in shorts:
        leg_returns.append(_leg_return(float(period_prices[ticker].iloc[0]), float(period_prices[ticker].iloc[-1]), "SHORT"))
    return float(np.mean(leg_returns)) if leg_returns else 0.0


def _compute_stats(equity_curve: List[Dict], total_contributed: float, period_returns: List[float], strategies_run: int) -> Dict:
    if not equity_curve:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "total_return": 0.0,
            "sharpe": 0.0,
            "strategies_run": strategies_run,
            "strategies_with_signals": 0,
        }

    values = [float(p["equity"]) for p in equity_curve]
    peak = values[0]
    max_dd = 0.0
    for value in values[1:]:
        peak = max(peak, value)
        max_dd = min(max_dd, (value - peak) / peak * 100)

    wins = [r for r in period_returns if r > 0]
    losses = [r for r in period_returns if r <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    ending_value = values[-1]
    profit_on_contributions = (ending_value / total_contributed - 1.0) * 100 if total_contributed else 0.0

    return {
        "total_trades": len(period_returns),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(len(wins) / len(period_returns) * 100, 1) if period_returns else 0.0,
        "avg_return": round(float(np.mean(period_returns)) * 100, 3) if period_returns else 0.0,
        "avg_win": round(float(np.mean(wins)) * 100, 3) if wins else 0.0,
        "avg_loss": round(float(np.mean(losses)) * 100, 3) if losses else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else 999.0,
        "max_drawdown": round(max_dd, 2),
        "total_return": round(profit_on_contributions, 2),
        "sharpe": round(float(np.mean(period_returns) / np.std(period_returns) * np.sqrt(12)), 3) if len(period_returns) > 1 and np.std(period_returns) else 0.0,
        "strategies_run": strategies_run,
        "strategies_with_signals": 1 if period_returns else 0,
        "ending_value": round(ending_value, 2),
        "total_contributed": round(total_contributed, 2),
        "profit": round(ending_value - total_contributed, 2),
        "profit_on_contributions": round(profit_on_contributions, 2),
    }


def run_spy_momentum_backtest(strategy_id: str, date_from: str, date_to: str) -> Dict:
    config = _strategy_config(strategy_id)
    strategy = strategy_name(strategy_id)
    tickers = get_sp500_tickers()
    prices = _download_close_prices(tickers, date_from, date_to, config.lookback_days)
    rebalances = _month_start_rebalances(prices, date_from, date_to)
    if not rebalances:
        return {"trades": [], "stats": _compute_stats([], 0, [], 1), "equity_curve": [], "error": "No trading days in selected range."}

    value = 0.0
    total_contributed = 0.0
    initialized = False
    trades: List[PortfolioLeg] = []
    period_returns: List[float] = []
    equity_curve: List[Dict] = []
    holdings: List[Dict] = []

    for i, entry_date in enumerate(rebalances):
        next_date = rebalances[i + 1] if i + 1 < len(rebalances) else prices.index[prices.index <= pd.Timestamp(date_to)][-1]
        if next_date <= entry_date:
            continue

        contribution = INITIAL_CAPITAL if not initialized else (MONTHLY_CONTRIBUTION if config.dynamic else 0.0)
        value += contribution
        total_contributed += contribution
        if not initialized:
            equity_curve.append({"date": str(entry_date.date()), "equity": round(value, 2)})
            initialized = True

        try:
            longs, shorts, rank_returns, rank_asof = _select_baskets(
                prices,
                entry_date,
                config.long_count,
                config.short_count,
                config.lookback_days,
            )
        except ValueError as exc:
            logger.warning("Skipping %s rebalance: %s", entry_date.date(), exc)
            continue

        names = longs + shorts
        period_prices = prices.loc[entry_date:next_date, names].dropna(axis=1, how="any")
        longs = [t for t in longs if t in period_prices.columns]
        shorts = [t for t in shorts if t in period_prices.columns]
        names = longs + shorts
        if len(longs) < config.long_count or len(shorts) < config.short_count or len(period_prices) < 2:
            continue

        ret = _period_return(period_prices, longs, shorts)
        period_returns.append(ret)
        start_value = value
        value *= 1.0 + ret
        exit_date = pd.Timestamp(period_prices.index[-1])
        equity_curve.append({"date": str(exit_date.date()), "equity": round(value, 2)})

        leg_notional = start_value / len(names)
        for ticker in longs:
            entry_price = float(period_prices[ticker].iloc[0])
            exit_price = float(period_prices[ticker].iloc[-1])
            leg_ret = _leg_return(entry_price, exit_price, "LONG")
            trades.append(PortfolioLeg(
                ticker=ticker,
                strategy=strategy,
                strategy_id=strategy_id,
                direction="LONG",
                entry_date=str(entry_date.date()),
                exit_date=str(exit_date.date()),
                entry_price=round(entry_price, 4),
                exit_price=round(exit_price, 4),
                stop_loss=0.0,
                take_profit=None,
                return_pct=round(leg_ret * 100, 3),
                holding_days=max(0, len(period_prices) - 1),
                mfe=0.0,
                mae=0.0,
                confidence=80,
                signal=f"Top {config.long_count} S&P momentum long as of {rank_asof.date()}",
                reasoning=f"Prior {config.lookback_days}-trading-day return {rank_returns[ticker] * 100:.2f}%; leg notional ${leg_notional:.2f}.",
            ))
        for ticker in shorts:
            entry_price = float(period_prices[ticker].iloc[0])
            exit_price = float(period_prices[ticker].iloc[-1])
            leg_ret = _leg_return(entry_price, exit_price, "SHORT")
            trades.append(PortfolioLeg(
                ticker=ticker,
                strategy=strategy,
                strategy_id=strategy_id,
                direction="SHORT",
                entry_date=str(entry_date.date()),
                exit_date=str(exit_date.date()),
                entry_price=round(entry_price, 4),
                exit_price=round(exit_price, 4),
                stop_loss=0.0,
                take_profit=None,
                return_pct=round(leg_ret * 100, 3),
                holding_days=max(0, len(period_prices) - 1),
                mfe=0.0,
                mae=0.0,
                confidence=80,
                signal=f"Bottom {config.short_count} S&P momentum short as of {rank_asof.date()}",
                reasoning=f"Prior {config.lookback_days}-trading-day return {rank_returns[ticker] * 100:.2f}%; leg notional ${leg_notional:.2f}.",
            ))

        holdings.append({
            "entry_date": str(entry_date.date()),
            "exit_date": str(exit_date.date()),
            "rank_asof": str(rank_asof.date()),
            "longs": longs,
            "shorts": shorts,
            "contribution": contribution,
            "portfolio_return_pct": round(ret * 100, 3),
            "start_value": round(start_value, 2),
            "end_value": round(value, 2),
        })

    stats = _compute_stats(equity_curve, total_contributed, period_returns, 1)
    return {
        "trades": [asdict(t) for t in trades],
        "stats": stats,
        "equity_curve": equity_curve,
        "portfolio_holdings": holdings,
        "portfolio_strategy": True,
    }


def current_month_scan(
    strategy_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict:
    config = _strategy_config(strategy_id)
    # Anchor the scan on the selected start date (date_from), not "today".
    entry_anchor = pd.Timestamp(date_from or date_to or date.today().isoformat())
    tickers = get_sp500_tickers()
    prices = _download_close_prices(
        tickers,
        entry_anchor.strftime("%Y-%m-%d"),
        (entry_anchor + pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
        config.lookback_days,
    )

    entry_days = prices.index[prices.index >= entry_anchor]
    if entry_days.empty:
        raise ValueError("No trading day found on or after selected start date.")
    entry_date = pd.Timestamp(entry_days[0])
    longs, shorts, rank_returns, rank_asof = _select_baskets(
        prices,
        entry_date,
        config.long_count,
        config.short_count,
        config.lookback_days,
    )

    strategy = strategy_name(strategy_id)
    results = []
    for ticker in longs:
        close_price = float(prices.loc[rank_asof, ticker])
        results.append({
            "ticker": ticker,
            "strategy": strategy,
            "close_price": close_price,
            "direction": "LONG",
            "entry_price": close_price,
            "stop_loss": 0.0,
            "confidence": 80,
            "reasoning": f"Top {config.long_count} S&P 500 prior {config.lookback_days}-trading-day momentum as of {rank_asof.date()} ({rank_returns[ticker] * 100:.2f}%).",
        })
    for ticker in shorts:
        close_price = float(prices.loc[rank_asof, ticker])
        results.append({
            "ticker": ticker,
            "strategy": strategy,
            "close_price": close_price,
            "direction": "SHORT",
            "entry_price": close_price,
            "stop_loss": 0.0,
            "confidence": 80,
            "reasoning": f"Bottom {config.short_count} S&P 500 prior {config.lookback_days}-trading-day momentum as of {rank_asof.date()} ({rank_returns[ticker] * 100:.2f}%).",
        })
    return {
        "results": results,
        "entry_date": str(entry_date.date()),
        "rank_asof": str(rank_asof.date()),
    }
