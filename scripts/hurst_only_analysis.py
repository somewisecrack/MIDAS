"""
Hurst-Only Pairs Analysis  (CORRECTED)
========================================
Core question: Does H < 0.5 on the spread alone (no cointegration test)
signal profitable mean reversion?

KEY FIX: Hurst must be applied to the FIRST DIFFERENCES of the spread
(spread increments / returns), NOT spread levels.

Why:
  - Log spread of two I(1) stocks is itself I(1) → variance grows linearly → H=0.5
  - For H < 0.5 we need ANTI-PERSISTENCE in the spread increments
  - OU mean-reverting spread ⟹ negative autocorrelation in dS ⟹ H(dS) < 0.5

Hurst methods compared:
  R/S  : Rescaled Range  (classic, robust)
  Var  : Variance scaling (straightforward)
  DFA  : Detrended Fluctuation Analysis — applied to dS directly (no cumsum)
  Corr : Lag-1 autocorrelation of dS (quick sanity check; negative = mean-reverting)

Spread definitions:
  log_ratio : log(p1) - log(p2)          [beta=1, no fitting bias]
  ols       : log(p1) - beta*log(p2)     [OLS full-sample beta]
"""

import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from itertools import combinations
import statsmodels.api as sm
import os, random

SEED = 42
random.seed(SEED); np.random.seed(SEED)

DATA_DIR = "/Users/rahulgirishkumar/TRADING/MIDAS/data"

SECTOR_TICKERS = {
    "Energy":    ["XOM","CVX","COP","DVN","PSX","VLO","EOG","OXY"],
    "Banks":     ["JPM","BAC","GS","WFC","MS","C","USB","TFC","PNC"],
    "Airlines":  ["UAL","DAL","AAL","LUV","ALK"],
    "Semis":     ["NVDA","AMD","MU","LRCX","AMAT","KLAC","ADI","TXN"],
    "Pharma":    ["JNJ","PFE","AMGN","GILD","MRK","BMY","ABBV"],
    "Utilities": ["NEE","DUK","SO","EXC","AEP","CMS","D","ETR","PPL","WEC"],
}

ALL_TICKERS = list({t for v in SECTOR_TICKERS.values() for t in v})


# ─── Hurst on first-differences of spread ────────────────────────────────────

def hurst_rs(ds: np.ndarray) -> float:
    """
    R/S Hurst applied to spread increments ds = S(t) - S(t-1).
    H < 0.5 → spread increments are anti-persistent → spread is mean-reverting.
    """
    ds = ds[np.isfinite(ds)]
    n  = len(ds)
    if n < 30: return np.nan
    lags = np.unique(np.geomspace(8, n // 2, 20).astype(int))
    rs_list, l_list = [], []
    for lag in lags:
        sub = [ds[i:i+lag] for i in range(0, n - lag, lag)]
        rs_sub = []
        for chunk in sub:
            m   = chunk.mean()
            dev = np.cumsum(chunk - m)
            r   = dev.max() - dev.min()
            s   = chunk.std(ddof=1)
            if s > 0: rs_sub.append(r / s)
        if rs_sub:
            rs_list.append(np.mean(rs_sub)); l_list.append(lag)
    if len(rs_list) < 5: return np.nan
    slope, _ = np.polyfit(np.log(l_list), np.log(rs_list), 1)
    return float(slope)


def hurst_var(ds: np.ndarray) -> float:
    """
    Variance-scaling Hurst on spread increments.
    Var[ds(t) + ... + ds(t+lag-1)] = Var[S(t+lag) - S(t)] ∝ lag^(2H).
    """
    ds = ds[np.isfinite(ds)]
    n  = len(ds)
    if n < 30: return np.nan
    S    = np.cumsum(ds)                          # reconstruct spread levels
    lags = np.unique(np.geomspace(2, n // 4, 20).astype(int))
    vs, ls = [], []
    for lag in lags:
        diffs = S[lag:] - S[:-lag]
        if len(diffs) > 2:
            vs.append(np.var(diffs, ddof=1)); ls.append(lag)
    if len(vs) < 5: return np.nan
    slope, _ = np.polyfit(np.log(ls), np.log(vs), 1)
    return float(slope / 2)


def hurst_dfa(ds: np.ndarray) -> float:
    """
    DFA applied directly to spread increments (no extra integration step).
    Fits H from: F(lag) ∝ lag^H where F = RMS of detrended cumulative sum of ds.
    """
    ds = ds[np.isfinite(ds)]
    n  = len(ds)
    if n < 30: return np.nan
    # Integrate the increments once → gives the spread (level series)
    y    = np.cumsum(ds - ds.mean())
    lags = np.unique(np.geomspace(4, n // 4, 20).astype(int))
    f_list, l_list = [], []
    for lag in lags:
        n_segs = n // lag
        if n_segs < 2: continue
        rms_list = []
        for j in range(n_segs):
            seg = y[j*lag:(j+1)*lag]
            t   = np.arange(lag, dtype=float)
            p   = np.polyfit(t, seg, 1)
            rms_list.append(np.sqrt(np.mean((seg - np.polyval(p, t))**2)))
        if rms_list: f_list.append(np.mean(rms_list)); l_list.append(lag)
    if len(f_list) < 5: return np.nan
    slope, _ = np.polyfit(np.log(l_list), np.log(f_list), 1)
    return float(slope)


def hurst_acf(ds: np.ndarray, max_lag: int = 20) -> tuple[float, float]:
    """
    Autocorrelation-based H estimate.
    Returns (lag1_acf, hurst_from_acf).
    For i.i.d.: acf=0, H=0.5.  For MR: acf<0, H<0.5.
    H ≈ 1 + log(1 + rho_1) / log(2)  [approximation for AR(1)-like]
    """
    ds   = ds[np.isfinite(ds)]
    n    = len(ds)
    if n < 10: return np.nan, np.nan
    mu   = ds.mean()
    var  = np.var(ds, ddof=1)
    if var == 0: return 0.0, 0.5
    # lag-1 autocorrelation
    r1   = np.corrcoef(ds[:-1], ds[1:])[0, 1]
    # Hurst from ACF scaling: H = (1 + log2(1 + rho1)) / 2 — rough approximation
    h_acf = (1 + np.log2(1 + r1 + 1e-9)) / 2 if r1 > -1 else 0.0
    return float(r1), float(h_acf)


def hurst_ensemble(ds: np.ndarray):
    """All methods on spread increments."""
    h_rs  = hurst_rs(ds)
    h_var = hurst_var(ds)
    h_dfa = hurst_dfa(ds)
    r1, h_acf = hurst_acf(ds)
    vals  = [v for v in [h_rs, h_var, h_dfa] if not np.isnan(v)]
    h_avg = float(np.mean(vals)) if vals else np.nan
    return h_rs, h_var, h_dfa, h_acf, r1, h_avg


# ─── Data loader ─────────────────────────────────────────────────────────────

def load_tf(filename: str, needed: list) -> dict:
    path = os.path.join(DATA_DIR, filename)
    df   = pd.read_csv(path, usecols=["Date","Close","Ticker"])
    df   = df[df["Ticker"].isin(needed)]
    df["Date"] = pd.to_datetime(df["Date"], utc=False)
    if df["Date"].dt.tz is not None:
        df["Date"] = df["Date"].dt.tz_convert(None)
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0].drop_duplicates(["Date","Ticker"])
    out = {}
    for ticker, grp in df.groupby("Ticker", sort=False):
        s = grp.set_index("Date")["Close"].sort_index()
        s = s[~s.index.duplicated(keep="last")]
        out[ticker] = s
    return out


# ─── Spread + increments ─────────────────────────────────────────────────────

def get_spreads(s1: pd.Series, s2: pd.Series):
    """Return (spread_lr, dspread_lr, spread_ols, dspread_ols, beta)."""
    idx  = s1.index.intersection(s2.index)
    a, b = np.log(s1.loc[idx].values), np.log(s2.loc[idx].values)

    # Log ratio (beta=1)
    sp_lr  = a - b
    dsp_lr = np.diff(sp_lr)

    # OLS hedge
    try:
        X    = sm.add_constant(b)
        res  = sm.OLS(a, X).fit()
        beta = float(res.params[1])
    except Exception:
        beta = 1.0
    sp_ols  = a - beta * b
    dsp_ols = np.diff(sp_ols)

    return pd.Series(sp_lr,  index=idx), dsp_lr, \
           pd.Series(sp_ols, index=idx), dsp_ols, beta, idx


# ─── Backtest ────────────────────────────────────────────────────────────────

def backtest_zscore(spread: pd.Series,
                    entry_z: float = 1.0,
                    exit_z:  float = 0.0,
                    stop_z:  float = 3.5,
                    lookback: int  = 50) -> dict:
    """Rolling z-score mean-reversion backtest on the spread LEVELS."""
    mu  = spread.rolling(lookback).mean()
    sig = spread.rolling(lookback).std()
    z   = (spread - mu) / sig

    pos, ep, ei = 0, 0.0, 0
    trades = []
    sv, zv = spread.values, z.values

    for i in range(lookback + 1, len(sv)):
        zi = zv[i]
        if np.isnan(zi): continue
        if pos == 0:
            if   zi < -entry_z: pos, ep, ei = +1, sv[i], i
            elif zi >  entry_z: pos, ep, ei = -1, sv[i], i
        else:
            exit_now = (pos == +1 and zi >= -exit_z) or \
                       (pos == -1 and zi <=  exit_z) or \
                       abs(zi) > stop_z or i == len(sv) - 1
            if exit_now:
                trades.append({
                    "pnl":     pos * (sv[i] - ep),
                    "bars":    i - ei,
                    "stopped": abs(zi) > stop_z,
                })
                pos = 0

    if not trades:
        return {"n":0,"pnl":0.0,"wr":np.nan,"sharpe":np.nan,"avg_bars":np.nan}
    tr   = pd.DataFrame(trades)
    n    = len(tr)
    mu_t = tr["pnl"].mean()
    sd_t = tr["pnl"].std(ddof=1) if n > 1 else np.nan
    return {
        "n":       n,
        "pnl":     round(tr["pnl"].sum(), 5),
        "wr":      round((tr["pnl"] > 0).mean(), 3),
        "sharpe":  round(mu_t / sd_t, 3) if (sd_t and sd_t > 0) else np.nan,
        "avg_bars":round(tr["bars"].mean(), 1),
    }


# ─── Per-pair analysis ────────────────────────────────────────────────────────

def analyze_pair(t1, t2, s1, s2, sector, tf, lookback):
    sp_lr, dsp_lr, sp_ols, dsp_ols, beta, idx = get_spreads(s1, s2)
    if len(idx) < max(50, lookback * 2):
        return None

    # Hurst on increments of both spread types
    h_rs_lr,  h_var_lr,  h_dfa_lr,  h_acf_lr,  r1_lr,  h_avg_lr  = hurst_ensemble(dsp_lr)
    h_rs_ols, h_var_ols, h_dfa_ols, h_acf_ols, r1_ols, h_avg_ols = hurst_ensemble(dsp_ols)

    # Primary H = average of DFA + R/S on whichever spread gives lower H
    h_lr_primary  = np.nanmean([h for h in [h_rs_lr,  h_dfa_lr]  if not np.isnan(h)])
    h_ols_primary = np.nanmean([h for h in [h_rs_ols, h_dfa_ols] if not np.isnan(h)])

    if np.isnan(h_lr_primary) and np.isnan(h_ols_primary):
        return None

    if (not np.isnan(h_lr_primary)) and (not np.isnan(h_ols_primary)):
        if h_lr_primary <= h_ols_primary:
            sp_best, h_best, h_all, stype = sp_lr,  h_lr_primary,  h_avg_lr,  "log_ratio"
            r1_best = r1_lr
        else:
            sp_best, h_best, h_all, stype = sp_ols, h_ols_primary, h_avg_ols, "ols"
            r1_best = r1_ols
    elif not np.isnan(h_lr_primary):
        sp_best, h_best, h_all, stype, r1_best = sp_lr,  h_lr_primary,  h_avg_lr,  "log_ratio", r1_lr
    else:
        sp_best, h_best, h_all, stype, r1_best = sp_ols, h_ols_primary, h_avg_ols, "ols",       r1_ols

    # Backtest
    bt1  = backtest_zscore(sp_best, entry_z=1.0, exit_z=0.0,  lookback=lookback)
    bt15 = backtest_zscore(sp_best, entry_z=1.5, exit_z=0.25, lookback=lookback)

    return {
        "tf": tf, "sector": sector, "t1": t1, "t2": t2,
        "n_bars": len(idx),
        # Hurst log-ratio increments
        "h_lr_rs": round(h_rs_lr,  4) if not np.isnan(h_rs_lr)  else np.nan,
        "h_lr_var":round(h_var_lr, 4) if not np.isnan(h_var_lr) else np.nan,
        "h_lr_dfa":round(h_dfa_lr, 4) if not np.isnan(h_dfa_lr) else np.nan,
        "h_lr_avg":round(h_avg_lr, 4) if not np.isnan(h_avg_lr) else np.nan,
        "r1_lr":   round(r1_lr,    4) if not np.isnan(r1_lr)    else np.nan,
        # Hurst OLS-spread increments
        "h_ols_rs": round(h_rs_ols,  4) if not np.isnan(h_rs_ols)  else np.nan,
        "h_ols_var":round(h_var_ols, 4) if not np.isnan(h_var_ols) else np.nan,
        "h_ols_dfa":round(h_dfa_ols, 4) if not np.isnan(h_dfa_ols) else np.nan,
        "h_ols_avg":round(h_avg_ols, 4) if not np.isnan(h_avg_ols) else np.nan,
        "r1_ols":   round(r1_ols,    4) if not np.isnan(r1_ols)    else np.nan,
        # Best spread selected
        "h_best":   round(h_best,  4) if not np.isnan(h_best)  else np.nan,
        "h_all":    round(h_all,   4) if not np.isnan(h_all)   else np.nan,
        "r1_best":  round(r1_best, 4) if not np.isnan(r1_best) else np.nan,
        "mean_rev": (h_best < 0.5)    if not np.isnan(h_best)  else False,
        "stype":    stype,
        # Backtests
        "bt1_n":bt1["n"],  "bt1_pnl":bt1["pnl"],   "bt1_wr":bt1["wr"],
        "bt1_sharpe":bt1["sharpe"],  "bt1_bars":bt1["avg_bars"],
        "bt15_n":bt15["n"],"bt15_pnl":bt15["pnl"], "bt15_wr":bt15["wr"],
        "bt15_sharpe":bt15["sharpe"],"bt15_bars":bt15["avg_bars"],
    }


# ─── Timeframe processor ─────────────────────────────────────────────────────

def process_tf(tf, filename, min_bars, lookback):
    print(f"\n{'═'*68}")
    print(f"  TIMEFRAME: {tf.upper()}  (lookback={lookback}, min_bars={min_bars})")
    print(f"{'═'*68}")
    closes = load_tf(filename, ALL_TICKERS)
    print(f"  Loaded {len(closes)} tickers.")

    rows = []
    for sector, tickers in SECTOR_TICKERS.items():
        present = [t for t in tickers if t in closes and len(closes[t]) >= min_bars]
        if len(present) < 2: continue
        for t1, t2 in combinations(present, 2):
            r = analyze_pair(t1, t2, closes[t1], closes[t2], sector, tf, lookback)
            if r: rows.append(r)

    df = pd.DataFrame(rows)
    if df.empty:
        print("  No results."); return df

    mr  = df[df["mean_rev"]]
    tmr = df[~df["mean_rev"]]

    print(f"\n  Total pairs: {len(df)}")
    print(f"  H < 0.5 (MR):   {len(mr)}  ({len(mr)/len(df)*100:.1f}%)")
    print(f"  H ≥ 0.5:        {len(tmr)}  ({len(tmr)/len(df)*100:.1f}%)")

    # Hurst distribution
    print(f"\n  Primary H distribution (R/S + DFA on spread increments):")
    bins = [-0.5, 0.0, 0.2, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 1.1]
    hist = pd.cut(df["h_best"], bins=bins).value_counts().sort_index()
    for interval, cnt in hist.items():
        bar  = "█" * min(cnt, 60)
        flag = " ◄ MEAN REVERTING" if interval.right <= 0.5 else ""
        if cnt > 0:
            print(f"    {str(interval):20s}: {cnt:3d}  {bar}{flag}")

    # Method comparison
    print(f"\n  H statistics by method (spread increments):")
    for col, lbl in [("h_lr_rs","R/S log-ratio"),("h_lr_dfa","DFA log-ratio"),
                     ("h_ols_rs","R/S OLS"),("h_ols_dfa","DFA OLS"),
                     ("h_lr_var","Var log-ratio"),("h_ols_var","Var OLS")]:
        if col not in df.columns: continue
        s = df[col].dropna()
        if len(s) == 0: continue
        flag = f"  ← {(s < 0.5).sum()} pairs with H<0.5!" if (s < 0.5).sum() > 0 else ""
        print(f"    {lbl:20s}: min={s.min():.3f}  med={s.median():.3f}  max={s.max():.3f}{flag}")

    # Lag-1 ACF distribution
    print(f"\n  Lag-1 ACF of spread increments (negative = mean-reverting):")
    r1_col = "r1_best"
    if r1_col in df.columns:
        r1 = df[r1_col].dropna()
        neg = (r1 < 0).sum()
        print(f"    min={r1.min():.3f}  med={r1.median():.3f}  max={r1.max():.3f}  "
              f"neg={neg}/{len(r1)} ({neg/len(r1)*100:.0f}%)")

    # Show MR pairs if any
    if len(mr) > 0:
        print(f"\n  ── MEAN-REVERTING PAIRS (H<0.5) ──")
        cols = ["sector","t1","t2","h_best","h_lr_dfa","h_ols_dfa","r1_best",
                "bt1_n","bt1_wr","bt1_pnl","bt1_sharpe"]
        print(mr[cols].sort_values("h_best").to_string(index=False))

    # MR vs non-MR comparison
    print(f"\n  {'─'*55}")
    print(f"  Backtest comparison  H<0.5 vs H≥0.5  (entry_z=1.0)")
    print(f"  {'─'*55}")
    print(f"  {'Metric':<22} {'H<0.5':>10} {'H≥0.5':>10} {'Difference':>12}")
    for met, lbl in [("bt1_wr","Win rate"),("bt1_pnl","Total PnL"),
                     ("bt1_sharpe","Sharpe"),("bt1_bars","Avg bars")]:
        vMR  = mr[met].mean()  if len(mr)  > 0 else np.nan
        vTMR = tmr[met].mean() if len(tmr) > 0 else np.nan
        diff = (vMR - vTMR) if (not np.isnan(vMR) and not np.isnan(vTMR)) else np.nan
        print(f"  {lbl:<22} {vMR:>10.3f} {vTMR:>10.3f} {diff:>12.3f}")

    # Top pairs by Sharpe
    with_trades = df[df["bt1_n"] >= 5]
    if len(with_trades) > 0:
        print(f"\n  Top 10 pairs (entry_z=1.0, ≥5 trades):")
        cols = ["sector","t1","t2","h_best","r1_best","stype",
                "bt1_n","bt1_wr","bt1_pnl","bt1_sharpe"]
        print(with_trades.nlargest(10,"bt1_sharpe")[cols].to_string(index=False))

    return df


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    configs = [
        ("5m",    "tickers_5m_ohlcv.csv",   500,  100),
        ("15m",   "tickers_15m_ohlcv.csv",  400,   80),
        ("30m",   "tickers_30m_ohlcv.csv",  200,   60),
        ("1h",    "tickers_1h_ohlcv.csv",   200,   50),
        ("daily", "tickers_ohlcv.csv",       180,   40),
    ]

    all_dfs = []
    for tf, fname, mb, lb in configs:
        df = process_tf(tf, fname, mb, lb)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs: return

    combined = pd.concat(all_dfs, ignore_index=True)
    path = "/Users/rahulgirishkumar/TRADING/MIDAS/results/hurst_only_results.csv"
    combined.to_csv(path, index=False)

    # ── Cross-timeframe summary ──────────────────────────────────────────────
    print(f"\n\n{'═'*68}")
    print(f"  CROSS-TIMEFRAME SUMMARY")
    print(f"{'═'*68}")

    order = ["5m","15m","30m","1h","daily"]
    rows = []
    for tf in order:
        g = combined[combined["tf"] == tf]
        if len(g) == 0: continue
        mr  = g[g["mean_rev"]]
        tmr = g[~g["mean_rev"]]
        r1  = g["r1_best"].dropna()
        rows.append({
            "tf":          tf,
            "n_pairs":     len(g),
            "pct_H<0.5":   f"{len(mr)/len(g)*100:.1f}%",
            "min_H":       round(g["h_best"].min(), 3),
            "med_H":       round(g["h_best"].median(), 3),
            "neg_r1_pct":  f"{(r1<0).mean()*100:.0f}%",
            "med_r1":      round(r1.median(), 3),
            "MR_wr":       round(mr["bt1_wr"].mean(), 3)     if len(mr) else "—",
            "MR_sharpe":   round(mr["bt1_sharpe"].mean(), 3) if len(mr) else "—",
            "TMR_wr":      round(tmr["bt1_wr"].mean(), 3)     if len(tmr) else "—",
            "TMR_sharpe":  round(tmr["bt1_sharpe"].mean(), 3) if len(tmr) else "—",
        })
    print(pd.DataFrame(rows).set_index("tf").to_string())

    # ── Global MR pairs ──────────────────────────────────────────────────────
    all_mr = combined[combined["mean_rev"]].sort_values("h_best")
    print(f"\n  ALL H<0.5 PAIRS across timeframes ({len(all_mr)} total):")
    if len(all_mr) > 0:
        cols = ["tf","sector","t1","t2","h_best","r1_best",
                "bt1_n","bt1_wr","bt1_pnl","bt1_sharpe"]
        print(all_mr[cols].to_string(index=False))
    else:
        print("  None found. Lowest H pairs:")
        cols = ["tf","sector","t1","t2","h_best","r1_best",
                "bt1_n","bt1_wr","bt1_pnl","bt1_sharpe"]
        print(combined.nsmallest(15,"h_best")[cols].to_string(index=False))

    print(f"\n  Results → {path}")


if __name__ == "__main__":
    main()
