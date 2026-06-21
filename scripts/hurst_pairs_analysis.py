"""
Hurst Exponent Pairs Trading Analysis
======================================
Analyzes spread mean-reversion via Hurst exponent across multiple timeframes,
then backtests a pairs trading strategy on mean-reverting pairs.

Hurst Exponent interpretation:
  H < 0.5  → mean-reverting (anti-persistent)
  H ≈ 0.5  → random walk (no memory)
  H > 0.5  → trending (persistent)
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import random
from itertools import combinations
from statsmodels.tsa.stattools import coint
import statsmodels.api as sm
from scipy import stats
import sys
import os

# ── Reproducibility ──────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HURST EXPONENT  (R/S method + variance scaling)
# ═══════════════════════════════════════════════════════════════════════════════

def hurst_rs(series: np.ndarray, min_window: int = 10) -> float:
    """
    Hurst exponent via the rescaled-range (R/S) method.
    Returns np.nan if series is too short or degenerate.
    """
    series = np.asarray(series, dtype=float)
    series = series[~np.isnan(series)]
    n = len(series)
    if n < 20:
        return np.nan

    lags = np.unique(np.geomspace(min_window, n // 2, num=20, dtype=int))
    rs_vals = []
    lag_vals = []
    for lag in lags:
        sub_rs = []
        for start in range(0, n - lag, lag):
            chunk = series[start: start + lag]
            mean = chunk.mean()
            dev = np.cumsum(chunk - mean)
            r = dev.max() - dev.min()
            s = chunk.std(ddof=1)
            if s > 0:
                sub_rs.append(r / s)
        if sub_rs:
            rs_vals.append(np.mean(sub_rs))
            lag_vals.append(lag)

    if len(rs_vals) < 4:
        return np.nan

    log_lags = np.log(lag_vals)
    log_rs   = np.log(rs_vals)
    slope, *_ = np.polyfit(log_lags, log_rs, 1)
    return float(slope)


def hurst_variance(series: np.ndarray) -> float:
    """
    Hurst exponent via variance-of-increments scaling.
    Faster, complementary cross-check.
    """
    series = np.asarray(series, dtype=float)
    series = series[~np.isnan(series)]
    n = len(series)
    if n < 20:
        return np.nan

    lags = np.unique(np.geomspace(2, n // 4, num=15, dtype=int))
    var_vals, lag_vals = [], []
    for lag in lags:
        diffs = series[lag:] - series[:-lag]
        if len(diffs) > 1:
            var_vals.append(np.var(diffs, ddof=1))
            lag_vals.append(lag)

    if len(var_vals) < 4:
        return np.nan

    slope, *_ = np.polyfit(np.log(lag_vals), np.log(var_vals), 1)
    return float(slope / 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

DATA_DIR = "/Users/rahulgirishkumar/TRADING/MIDAS/data"

def load_timeframe(tf: str) -> dict[str, pd.Series]:
    """
    Load close prices for a timeframe.
    Returns {ticker: pd.Series(close, index=datetime)}.
    """
    file_map = {
        "daily": "tickers_ohlcv.csv",
        "1h":    "tickers_1h_ohlcv.csv",
        "30m":   "tickers_30m_ohlcv.csv",
        "15m":   "tickers_15m_ohlcv.csv",
    }
    path = os.path.join(DATA_DIR, file_map[tf])
    print(f"  Loading {tf} data from {path} …", flush=True)

    df = pd.read_csv(path, usecols=["Date", "Close", "Ticker"])
    df["Date"] = pd.to_datetime(df["Date"], utc=False)
    # Strip timezone if present
    if df["Date"].dt.tz is not None:
        df["Date"] = df["Date"].dt.tz_convert(None)
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0]
    df = df.drop_duplicates(["Date", "Ticker"])

    # Build per-ticker dict via groupby (avoids pivot_table index bugs)
    out = {}
    for ticker, grp in df.groupby("Ticker", sort=False):
        s = grp.set_index("Date")["Close"].sort_index()
        s = s[~s.index.duplicated(keep="last")]
        out[ticker] = s

    print(f"  Loaded {len(out)} tickers.", flush=True)
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PAIR SELECTION  (cointegration filter)
# ═══════════════════════════════════════════════════════════════════════════════

def align_pair(s1: pd.Series, s2: pd.Series) -> tuple[pd.Series, pd.Series]:
    # Deduplicate index first (keep last bar per timestamp)
    s1 = s1[~s1.index.duplicated(keep="last")]
    s2 = s2[~s2.index.duplicated(keep="last")]
    idx = s1.index.intersection(s2.index)
    return s1.loc[idx], s2.loc[idx]


def compute_spread(s1: pd.Series, s2: pd.Series) -> tuple[pd.Series, float]:
    """OLS hedge ratio, returns (spread series, beta)."""
    log1 = np.log(s1.values)
    log2 = np.log(s2.values)
    X = sm.add_constant(log2)
    res = sm.OLS(log1, X).fit()
    beta = float(res.params[1])
    spread = pd.Series(log1 - beta * log2, index=s1.index)
    return spread, beta


def test_cointegration(s1: pd.Series, s2: pd.Series,
                       pvalue_thresh: float = 0.10) -> tuple[bool, float]:
    try:
        _, pval, _ = coint(np.log(s1), np.log(s2))
        return pval < pvalue_thresh, pval
    except Exception:
        return False, np.nan


# ═══════════════════════════════════════════════════════════════════════════════
# 4. BACKTEST  – z-score mean reversion
# ═══════════════════════════════════════════════════════════════════════════════

def backtest_pairs(spread: pd.Series,
                   s1: pd.Series,
                   s2: pd.Series,
                   beta: float,
                   entry_z: float = 1.5,
                   exit_z:  float = 0.25,
                   stop_z:  float = 3.5,
                   lookback: int   = 60) -> dict:
    """
    Rolling z-score mean-reversion strategy.
      - Long spread (long s1, short beta*s2) when z < -entry_z
      - Short spread when z > +entry_z
      - Exit when |z| < exit_z
      - Hard stop at |z| > stop_z
    Returns performance metrics dict.
    """
    roll_mean = spread.rolling(lookback).mean()
    roll_std  = spread.rolling(lookback).std()
    z = (spread - roll_mean) / roll_std

    position = 0   # +1 long spread, -1 short spread
    trades = []
    entry_price = None
    entry_z_val = None

    s1_arr = s1.values
    s2_arr = s2.values
    z_arr  = z.values
    idx    = spread.index

    for i in range(lookback + 1, len(z_arr)):
        zi = z_arr[i]
        if np.isnan(zi):
            continue

        if position == 0:
            if zi < -entry_z:
                position = 1
                entry_price = (s1_arr[i], s2_arr[i])
                entry_z_val = zi
                entry_idx = i
            elif zi > entry_z:
                position = -1
                entry_price = (s1_arr[i], s2_arr[i])
                entry_z_val = zi
                entry_idx = i
        else:
            # Exit conditions
            should_exit = (
                abs(zi) < exit_z or
                abs(zi) > stop_z or
                i == len(z_arr) - 1
            )
            if should_exit:
                # P&L as log-return of spread (proxy for combined position)
                spread_entry = np.log(entry_price[0]) - beta * np.log(entry_price[1])
                spread_exit  = spread.iloc[i]
                pnl = position * (spread_exit - spread_entry)
                holding = i - entry_idx
                trades.append({
                    "entry_date": idx[entry_idx],
                    "exit_date":  idx[i],
                    "holding_bars": holding,
                    "entry_z": entry_z_val,
                    "exit_z":  zi,
                    "pnl":     pnl,
                    "stopped": abs(zi) > stop_z,
                })
                position = 0
                entry_price = None

    if not trades:
        return {"n_trades": 0, "total_pnl": 0.0, "win_rate": np.nan,
                "sharpe": np.nan, "avg_holding": np.nan, "n_stopped": 0}

    df_t = pd.DataFrame(trades)
    n    = len(df_t)
    wins = (df_t["pnl"] > 0).sum()
    total_pnl = df_t["pnl"].sum()
    avg_pnl   = df_t["pnl"].mean()
    std_pnl   = df_t["pnl"].std()
    sharpe    = (avg_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else np.nan

    return {
        "n_trades":    n,
        "total_pnl":   round(total_pnl, 5),
        "win_rate":    round(wins / n, 3),
        "avg_pnl":     round(avg_pnl, 5),
        "sharpe":      round(sharpe, 3),
        "avg_holding": round(df_t["holding_bars"].mean(), 1),
        "n_stopped":   int(df_t["stopped"].sum()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_timeframe(tf: str,
                      n_tickers: int = 40,
                      n_pairs: int   = 60,
                      min_bars: int  = 120) -> pd.DataFrame:
    """
    For a given timeframe:
      1. Load data, sample random tickers
      2. Filter pairs with cointegration (p < 0.10)
      3. Compute Hurst on spread
      4. Backtest mean-reverting pairs (H < 0.5)
    """
    print(f"\n{'═'*60}")
    print(f"  TIMEFRAME: {tf.upper()}")
    print(f"{'═'*60}")

    prices = load_timeframe(tf)

    # Filter tickers with enough data
    valid = {t: s for t, s in prices.items() if len(s) >= min_bars}
    print(f"  Tickers with ≥{min_bars} bars: {len(valid)}")

    if len(valid) < 10:
        print("  Not enough tickers. Skipping.")
        return pd.DataFrame()

    # Sample tickers
    sampled = random.sample(sorted(valid.keys()),
                            min(n_tickers, len(valid)))
    print(f"  Sampled {len(sampled)} tickers: {sampled}")

    # Generate candidate pairs
    candidates = list(combinations(sampled, 2))
    random.shuffle(candidates)
    candidates = candidates[:n_pairs * 5]  # test more, keep best

    results = []
    tested  = 0
    kept    = 0

    for t1, t2 in candidates:
        if kept >= n_pairs:
            break
        tested += 1

        s1, s2 = align_pair(valid[t1], valid[t2])
        if len(s1) < min_bars:
            continue

        # Quick cointegration filter
        coint_pass, coint_pval = test_cointegration(s1, s2)

        spread, beta = compute_spread(s1, s2)
        spread_vals  = spread.values

        # Hurst (two methods, average)
        h_rs  = hurst_rs(spread_vals)
        h_var = hurst_variance(spread_vals)
        h_avg = np.nanmean([h_rs, h_var])

        # Backtest regardless of Hurst (so we can compare)
        # Lookback: ~40 bars for daily, ~100 for intraday
        tf_lookback = {"daily": 40, "1h": 100, "30m": 100, "15m": 80}
        lookback = tf_lookback.get(tf, max(20, min(80, len(spread) // 8)))
        bt = backtest_pairs(spread, s1, s2, beta, lookback=lookback)

        results.append({
            "tf":           tf,
            "ticker1":      t1,
            "ticker2":      t2,
            "n_bars":       len(spread),
            "coint_pval":   round(coint_pval, 4),
            "cointegrated": coint_pass,
            "beta":         round(beta, 4),
            "hurst_rs":     round(h_rs, 4) if not np.isnan(h_rs) else np.nan,
            "hurst_var":    round(h_var, 4) if not np.isnan(h_var) else np.nan,
            "hurst_avg":    round(h_avg, 4) if not np.isnan(h_avg) else np.nan,
            "mean_reverting": h_avg < 0.5,
            **bt,
        })
        kept += 1
        if kept % 10 == 0:
            print(f"    … analysed {kept}/{n_pairs} pairs", flush=True)

    print(f"  Tested {tested} pairs, kept {kept} with enough data.")
    return pd.DataFrame(results)


def print_summary(df: pd.DataFrame, tf: str):
    print(f"\n{'─'*60}")
    print(f"  SUMMARY — {tf.upper()}")
    print(f"{'─'*60}")
    if df.empty:
        print("  No results.")
        return

    mr = df[df["mean_reverting"] == True]
    co = df[df["cointegrated"]   == True]
    mr_co = df[df["mean_reverting"] & df["cointegrated"]]

    print(f"  Total pairs analysed  : {len(df)}")
    print(f"  Mean-reverting (H<0.5): {len(mr)}  ({len(mr)/len(df)*100:.0f}%)")
    print(f"  Cointegrated (p<0.10) : {len(co)}  ({len(co)/len(df)*100:.0f}%)")
    print(f"  Both MR + Coint       : {len(mr_co)}")

    print(f"\n  {'── Hurst Exponent Distribution ──':}")
    print(f"  Mean H : {df['hurst_avg'].mean():.3f}")
    print(f"  Median H: {df['hurst_avg'].median():.3f}")
    print(f"  Std  H : {df['hurst_avg'].std():.3f}")

    if len(mr_co) > 0 and mr_co["n_trades"].sum() > 0:
        active = mr_co[mr_co["n_trades"] > 0]
        print(f"\n  {'── Backtest: MR+Cointegrated pairs ──':}")
        print(f"  Pairs with trades     : {len(active)}")
        print(f"  Total trades          : {active['n_trades'].sum()}")
        print(f"  Avg win rate          : {active['win_rate'].mean():.1%}")
        print(f"  Avg total PnL (log)   : {active['total_pnl'].mean():.4f}")
        print(f"  Median Sharpe         : {active['sharpe'].median():.3f}")
        print(f"  % Pairs profitable    : {(active['total_pnl']>0).mean():.1%}")
        print(f"  Avg holding (bars)    : {active['avg_holding'].mean():.1f}")
        print(f"  Avg stops hit         : {active['n_stopped'].mean():.1f}")

        print(f"\n  Top 5 pairs by Sharpe:")
        cols = ["ticker1","ticker2","hurst_avg","coint_pval",
                "n_trades","win_rate","total_pnl","sharpe","avg_holding"]
        top5 = active.nlargest(5, "sharpe")[cols]
        print(top5.to_string(index=False))

    # All pairs backtest comparison
    with_trades = df[df["n_trades"] > 0]
    if len(with_trades) > 0:
        mr_trades  = with_trades[with_trades["mean_reverting"]]
        tmr_trades = with_trades[~with_trades["mean_reverting"]]
        print(f"\n  {'── Mean-Reverting vs Trending pairs (backtest) ──':}")
        print(f"  {'Metric':<25} {'H<0.5 (MR)':>12} {'H>0.5 (Trend)':>14}")
        print(f"  {'-'*52}")
        for metric, label in [("win_rate","Win Rate"),
                               ("total_pnl","Total PnL"),
                               ("sharpe","Sharpe")]:
            mr_val  = mr_trades[metric].mean()  if len(mr_trades)  else np.nan
            tmr_val = tmr_trades[metric].mean() if len(tmr_trades) else np.nan
            print(f"  {label:<25} {mr_val:>12.3f} {tmr_val:>14.3f}")


def main():
    all_results = []

    timeframes = {
        "daily": {"n_tickers": 60, "n_pairs": 80,  "min_bars": 200},
        "1h":    {"n_tickers": 50, "n_pairs": 80,  "min_bars": 800},
        "15m":   {"n_tickers": 40, "n_pairs": 60,  "min_bars": 400},
    }

    for tf, params in timeframes.items():
        df = analyze_timeframe(tf, **params)
        if not df.empty:
            print_summary(df, tf)
            all_results.append(df)

    # ── Combined cross-timeframe view ────────────────────────────────────────
    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        out_path = "/Users/rahulgirishkumar/TRADING/MIDAS/results/hurst_pairs_results.csv"
        combined.to_csv(out_path, index=False)
        print(f"\n\n{'═'*60}")
        print(f"  CROSS-TIMEFRAME SUMMARY")
        print(f"{'═'*60}")
        summary = (combined[combined["n_trades"] > 0]
                   .groupby("tf")
                   .agg(
                       n_pairs    = ("ticker1", "count"),
                       pct_mr     = ("mean_reverting", "mean"),
                       avg_hurst  = ("hurst_avg", "mean"),
                       pct_coint  = ("cointegrated", "mean"),
                       avg_winrate= ("win_rate", "mean"),
                       avg_pnl    = ("total_pnl", "mean"),
                       med_sharpe = ("sharpe", "median"),
                       pct_profit = ("total_pnl", lambda x: (x>0).mean()),
                   )
                   .round(3))
        print(summary.to_string())
        print(f"\n  Full results saved → {out_path}")

        # ── Best pairs overall ───────────────────────────────────────────────
        profitable_mr = (combined
                         .query("mean_reverting == True and cointegrated == True and n_trades >= 3")
                         .nlargest(10, "sharpe"))
        if len(profitable_mr) > 0:
            print(f"\n  TOP 10 MEAN-REVERTING PAIRS (all timeframes, by Sharpe):")
            cols = ["tf","ticker1","ticker2","hurst_avg","coint_pval",
                    "n_trades","win_rate","total_pnl","sharpe"]
            print(profitable_mr[cols].to_string(index=False))


if __name__ == "__main__":
    main()
