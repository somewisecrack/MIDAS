"""
backtest_engine.py — Deterministic backtest runner for MIDAS swing strategies.

Exit rule: each strategy has a holding_period (in trading days). We exit at the
close of the Nth trading day after entry. No dynamic exits (stop/target) in v1
— stop and take_profit are stored for display purposes only.

MFE (max favorable excursion) and MAE (max adverse excursion) are computed
over the holding window on a per-trade basis.
"""
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.core.strategy_adapter import scan_strategy, get_holding_days, list_strategies

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    ticker: str
    strategy: str
    strategy_id: str
    direction: str          # LONG | SHORT
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: Optional[float]
    return_pct: float
    holding_days: int
    mfe: float              # max favorable excursion % during hold
    mae: float              # max adverse excursion % during hold (stored as negative)
    confidence: int
    signal: str = ""
    reasoning: str = ""


@dataclass
class BacktestStats:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    sharpe: float = 0.0
    strategies_run: int = 0
    strategies_with_signals: int = 0


def _compute_mfe_mae(df: pd.DataFrame, entry_idx: int, exit_idx: int, direction: str, entry_price: float):
    """Compute MFE and MAE over the holding window [entry_idx+1, exit_idx]."""
    window = df.iloc[entry_idx + 1: exit_idx + 1]
    if window.empty or entry_price == 0:
        return 0.0, 0.0

    if direction == "LONG":
        highs = window["High"].values
        lows = window["Low"].values
        mfe = float(np.max(highs) - entry_price) / entry_price * 100
        mae = float(np.min(lows) - entry_price) / entry_price * 100  # negative
    else:  # SHORT
        highs = window["High"].values
        lows = window["Low"].values
        mfe = float(entry_price - np.min(lows)) / entry_price * 100
        mae = float(entry_price - np.max(highs)) / entry_price * 100  # negative

    return round(mfe, 3), round(mae, 3)


def _compute_equity_curve(trades: List[Trade]) -> List[Dict]:
    """Build a simple time-weighted equity curve from trade returns."""
    if not trades:
        return []
    sorted_trades = sorted(trades, key=lambda t: t.entry_date)
    equity = 10000.0
    curve = [{"date": sorted_trades[0].entry_date, "equity": equity}]
    for t in sorted_trades:
        equity *= (1 + t.return_pct / 100)
        curve.append({"date": t.exit_date, "equity": round(equity, 2)})
    return curve


def _compute_max_drawdown(equity_curve: List[Dict]) -> float:
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]["equity"]
    max_dd = 0.0
    for point in equity_curve[1:]:
        eq = point["equity"]
        if eq > peak:
            peak = eq
        dd = (eq - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 2)


def run_backtest(
    ticker: str,
    strategy_ids: List[str],
    df: pd.DataFrame,
    date_from: str,
    date_to: str,
) -> Dict:
    """
    Run backtesting for specified strategies on the given OHLCV DataFrame.

    Args:
        ticker: stock symbol (used for display)
        strategy_ids: list of strategy IDs from the registry
        df: DataFrame with columns Date, Open, High, Low, Close, Volume (sorted)
        date_from, date_to: range to backtest within (inclusive)

    Returns:
        { trades: [...], stats: {...}, equity_curve: [...] }
    """
    # Filter to backtest window
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    mask = (df["Date"] >= pd.Timestamp(date_from)) & (df["Date"] <= pd.Timestamp(date_to))
    df = df[mask].reset_index(drop=True)

    if len(df) < 30:
        return {
            "trades": [],
            "stats": asdict(BacktestStats()),
            "equity_curve": [],
            "error": f"Insufficient data in range ({len(df)} rows). Need at least 30 bars.",
        }

    all_trades: List[Trade] = []
    strategies_with_signals = 0

    for strategy_id in strategy_ids:
        strategy_trades = []

        for i in range(60, len(df)):  # start at bar 60 to give strategies enough history
            # Pass df up to bar i (look-forward protected)
            window_df = df.iloc[:i + 1].copy()
            window_df["Ticker"] = ticker

            signal = scan_strategy(strategy_id, window_df, ticker)
            if signal is None:
                continue

            direction = signal.get("type", "LONG")
            entry_price_raw = signal.get("entry_price", df.iloc[i]["Close"])
            stop_loss = signal.get("stop_loss", entry_price_raw * (0.97 if direction == "LONG" else 1.03))
            take_profit = signal.get("take_profit")

            # Entry is next bar's open (realistic simulation)
            if i + 1 >= len(df):
                continue
            entry_bar = df.iloc[i + 1]
            entry_date = str(entry_bar["Date"].date())
            entry_price = float(entry_bar["Open"])

            # Exit: close of bar N trading days after entry
            hold_days = get_holding_days(strategy_id, signal)
            exit_idx = min(i + 1 + hold_days, len(df) - 1)
            exit_bar = df.iloc[exit_idx]
            exit_date = str(exit_bar["Date"].date())
            exit_price = float(exit_bar["Close"])

            # Return calculation
            if direction == "LONG":
                return_pct = (exit_price - entry_price) / entry_price * 100
            else:
                return_pct = (entry_price - exit_price) / entry_price * 100
            return_pct = round(return_pct, 3)

            mfe, mae = _compute_mfe_mae(df, i + 1, exit_idx, direction, entry_price)

            trade = Trade(
                ticker=ticker,
                strategy=signal.get("strategy", strategy_id),
                strategy_id=strategy_id,
                direction=direction,
                entry_date=entry_date,
                exit_date=exit_date,
                entry_price=round(entry_price, 4),
                exit_price=round(exit_price, 4),
                stop_loss=round(float(stop_loss), 4),
                take_profit=round(float(take_profit), 4) if take_profit else None,
                return_pct=return_pct,
                holding_days=exit_idx - (i + 1),
                mfe=mfe,
                mae=mae,
                confidence=signal.get("confidence", 70),
                signal=signal.get("signal", ""),
                reasoning=signal.get("reasoning", ""),
            )
            strategy_trades.append(trade)

        if strategy_trades:
            strategies_with_signals += 1
        all_trades.extend(strategy_trades)

    # Sort trades by entry date
    all_trades.sort(key=lambda t: t.entry_date)

    # Compute stats
    stats = _compute_stats(all_trades, len(strategy_ids), strategies_with_signals)
    equity_curve = _compute_equity_curve(all_trades)

    return {
        "trades": [asdict(t) for t in all_trades],
        "stats": asdict(stats),
        "equity_curve": equity_curve,
    }


def run_batch_backtest(
    tickers: List[str],
    strategy_ids: List[str],
    date_from: str,
    date_to: str,
) -> Dict:
    """
    Run backtesting for specified strategies across multiple tickers.
    Automatically fetches missing data using fetch_and_cache.
    """
    from app.core.data_service import fetch_and_cache, load_from_cache, rows_to_dataframe
    
    all_trades: List[Trade] = []
    strategies_with_signals = 0
    ticker_results = []
    
    for ticker in tickers:
        ticker = ticker.upper().strip()
        if not ticker: continue
        
        try:
            raw_rows = load_from_cache(ticker, date_from, date_to)
        except ValueError:
            try:
                fetch_and_cache(ticker, date_from, date_to, force=False)
                raw_rows = load_from_cache(ticker, date_from, date_to)
            except Exception as e:
                logger.warning(f"Skipping {ticker} due to fetch error: {e}")
                continue
                
        df = rows_to_dataframe(raw_rows)
        res = run_backtest(ticker, strategy_ids, df, date_from, date_to)
        
        if "error" not in res:
            strategies_with_signals += int(res.get("stats", {}).get("strategies_with_signals", 0) or 0)

            # We reconstruct Trade objects from dicts to merge them
            for t_dict in res["trades"]:
                all_trades.append(Trade(**t_dict))
                
            ticker_results.append({
                "ticker": ticker,
                "stats": res["stats"],
                "trades": res["trades"],
                "equity_curve": res["equity_curve"],
            })
            
    # Sort all combined trades by entry date
    all_trades.sort(key=lambda t: t.entry_date)
    
    # Recalculate combined stats across every successful ticker/strategy pair.
    stats = _compute_stats(
        all_trades,
        len(strategy_ids) * len(ticker_results),
        strategies_with_signals,
    )
    
    # Portfolio equity curve
    equity_curve = _compute_equity_curve(all_trades)
    
    return {
        "trades": [asdict(t) for t in all_trades],
        "stats": asdict(stats),
        "equity_curve": equity_curve,
        "ticker_results": ticker_results,
    }


def _compute_stats(trades: List[Trade], strategies_run: int, strategies_with_signals: int) -> BacktestStats:
    if not trades:
        return BacktestStats(
            strategies_run=strategies_run,
            strategies_with_signals=strategies_with_signals,
        )

    returns = [t.return_pct for t in trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    win_rate = len(wins) / len(returns) * 100
    avg_return = float(np.mean(returns))
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = round(gross_profit / gross_loss, 3) if gross_loss > 0 else 999.0

    # Simple compound total return
    equity = 10000.0
    for r in returns:
        equity *= (1 + r / 100)
    total_return = round((equity - 10000) / 10000 * 100, 2)

    # Sharpe (annualised, assuming ~252 bars/year)
    if len(returns) > 1:
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252 / max(1, len(returns))))
    else:
        sharpe = 0.0

    equity_curve = _compute_equity_curve(trades)
    max_drawdown = _compute_max_drawdown(equity_curve)

    return BacktestStats(
        total_trades=len(trades),
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=round(win_rate, 1),
        avg_return=round(avg_return, 3),
        avg_win=round(avg_win, 3),
        avg_loss=round(avg_loss, 3),
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
        total_return=total_return,
        sharpe=round(sharpe, 3),
        strategies_run=strategies_run,
        strategies_with_signals=strategies_with_signals,
    )
