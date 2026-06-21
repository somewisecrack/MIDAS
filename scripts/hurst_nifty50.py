"""
Hurst-Only Pairs Analysis — NIFTY 50 (yfinance)
==================================================
Same methodology as hurst_only_analysis.py but uses live yfinance download.

H < 0.5 on spread FIRST-DIFFERENCES (increments) = anti-persistent = mean-reverting.

Timeframes:  5m (60 days) | 15m (60 days) | daily (2 years)

Hurst methods:
  R/S  : Rescaled Range
  DFA  : Detrended Fluctuation Analysis
  Primary H = mean(R/S, DFA)  — Var excluded as primary (noisier)

Spread types tested per pair:
  log_ratio : log(p1) - log(p2)          [beta=1, zero fitting bias]
  ols       : log(p1) - beta*log(p2)     [OLS full-sample hedge ratio]
"""

import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from itertools import combinations
import statsmodels.api as sm
import yfinance as yf
import os, time

OUT_DIR = "/Users/rahulgirishkumar/TRADING/MIDAS/results"
os.makedirs(OUT_DIR, exist_ok=True)

# ─── Ticker Universe ──────────────────────────────────────────────────────────

TICKERS_RAW = [
    "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS",
    "TCS.NS","INFY.NS","TECHM.NS","LTIM.NS","HCLTECH.NS","WIPRO.NS",
    "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","KOTAKBANK.NS","AXISBANK.NS","INDUSINDBK.NS",
    "BAJFINANCE.NS","BAJAJFINSV.NS","SBILIFE.NS","HDFCLIFE.NS",
    "SUNPHARMA.NS","DRREDDY.NS","DIVISLAB.NS","CIPLA.NS","APOLLOHOSP.NS",
    "HINDUNILVR.NS","ITC.NS","BRITANNIA.NS","NESTLEIND.NS","TATACONSUM.NS",
    "MARUTI.NS","M&M.NS","HEROMOTOCO.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","TITAN.NS",
    "HINDALCO.NS","TATASTEEL.NS","JSWSTEEL.NS",
    "RELIANCE.NS","ONGC.NS","BPCL.NS","COALINDIA.NS","ADANIPORTS.NS","ADANIENT.NS",
    "NTPC.NS","POWERGRID.NS",
    "LT.NS","GRASIM.NS","ULTRACEMCO.NS","ASIANPAINT.NS",
    "BHARTIARTL.NS","UPL.NS",
]

# Sector groups for pair selection (only trade within same sector)
SECTORS = {
    "IT":          ["TCS.NS","INFY.NS","TECHM.NS","LTIM.NS","HCLTECH.NS","WIPRO.NS"],
    "Pvt_Banks":   ["HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","INDUSINDBK.NS"],
    "PSU_Banks":   ["SBIN.NS"],                          # solo — will pair with others
    "NBFC_Ins":    ["BAJFINANCE.NS","BAJAJFINSV.NS","SBILIFE.NS","HDFCLIFE.NS"],
    "Pharma":      ["SUNPHARMA.NS","DRREDDY.NS","DIVISLAB.NS","CIPLA.NS","APOLLOHOSP.NS"],
    "FMCG":        ["HINDUNILVR.NS","ITC.NS","BRITANNIA.NS","NESTLEIND.NS","TATACONSUM.NS"],
    "Auto":        ["MARUTI.NS","M&M.NS","HEROMOTOCO.NS","EICHERMOT.NS","BAJAJ-AUTO.NS"],
    "Metals":      ["HINDALCO.NS","TATASTEEL.NS","JSWSTEEL.NS"],
    "Energy_PSU":  ["ONGC.NS","BPCL.NS","COALINDIA.NS","NTPC.NS","POWERGRID.NS"],
    "Conglomerate":["RELIANCE.NS","ADANIPORTS.NS","ADANIENT.NS","LT.NS","GRASIM.NS"],
    "Consumer":    ["TITAN.NS","ASIANPAINT.NS","HINDUNILVR.NS","NESTLEIND.NS","BRITANNIA.NS"],
    "Indices":     ["^NSEI","^NSEBANK","NIFTY_FIN_SERVICE.NS"],   # reference only
}

# Tradeable sectors (exclude single-ticker and index sectors)
TRADE_SECTORS = {k: v for k, v in SECTORS.items()
                 if k != "PSU_Banks" and k != "Indices" and len(v) >= 2}

ALL_NEEDED = list({t for v in TRADE_SECTORS.values() for t in v})


# ─── Hurst on first-differences of spread ────────────────────────────────────

def hurst_rs(ds: np.ndarray) -> float:
    """R/S Hurst on spread increments. H<0.5 → mean-reverting."""
    ds = ds[np.isfinite(ds)]
    n  = len(ds)
    if n < 30: return np.nan
    lags = np.unique(np.geomspace(8, n // 2, 20).astype(int))
    rs_list, l_list = [], []
    for lag in lags:
        sub = [ds[i:i+lag] for i in range(0, n - lag, lag)]
        rs_sub = []
        for chunk in sub:
            dev = np.cumsum(chunk - chunk.mean())
            r   = dev.max() - dev.min()
            s   = chunk.std(ddof=1)
            if s > 0: rs_sub.append(r / s)
        if rs_sub: rs_list.append(np.mean(rs_sub)); l_list.append(lag)
    if len(rs_list) < 5: return np.nan
    slope, _ = np.polyfit(np.log(l_list), np.log(rs_list), 1)
    return float(slope)


def hurst_dfa(ds: np.ndarray) -> float:
    """DFA on spread increments. H<0.5 → mean-reverting."""
    ds = ds[np.isfinite(ds)]
    n  = len(ds)
    if n < 30: return np.nan
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


def hurst_var(ds: np.ndarray) -> float:
    """Variance-scaling on spread levels reconstructed from increments."""
    ds = ds[np.isfinite(ds)]
    n  = len(ds)
    if n < 30: return np.nan
    S    = np.cumsum(ds)
    lags = np.unique(np.geomspace(2, n // 4, 20).astype(int))
    vs, ls = [], []
    for lag in lags:
        d = S[lag:] - S[:-lag]
        if len(d) > 2: vs.append(np.var(d, ddof=1)); ls.append(lag)
    if len(vs) < 5: return np.nan
    slope, _ = np.polyfit(np.log(ls), np.log(vs), 1)
    return float(slope / 2)


def hurst_primary(ds):
    """Returns (h_rs, h_dfa, h_var, h_primary, lag1_acf)."""
    h_rs  = hurst_rs(ds)
    h_dfa = hurst_dfa(ds)
    h_var = hurst_var(ds)
    # Primary = mean of R/S and DFA (both robust; Var is auxiliary)
    vals  = [v for v in [h_rs, h_dfa] if not np.isnan(v)]
    h_p   = float(np.mean(vals)) if vals else np.nan
    # Lag-1 ACF of increments
    ds_   = ds[np.isfinite(ds)]
    r1    = float(np.corrcoef(ds_[:-1], ds_[1:])[0, 1]) if len(ds_) > 10 else np.nan
    return h_rs, h_dfa, h_var, h_p, r1


# ─── Backtest ────────────────────────────────────────────────────────────────

def backtest_zscore(spread: pd.Series, entry_z=1.0, exit_z=0.0,
                    stop_z=3.5, lookback=50) -> dict:
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
            done = (pos==+1 and zi>=-exit_z) or (pos==-1 and zi<=exit_z) \
                   or abs(zi)>stop_z or i==len(sv)-1
            if done:
                trades.append({"pnl": pos*(sv[i]-ep), "bars": i-ei,
                                "stopped": abs(zi)>stop_z})
                pos = 0
    if not trades:
        return {"n":0,"pnl":0.0,"wr":np.nan,"sharpe":np.nan,"avg_bars":np.nan}
    tr   = pd.DataFrame(trades)
    n    = len(tr)
    mu_t = tr["pnl"].mean()
    sd_t = tr["pnl"].std(ddof=1) if n > 1 else np.nan
    return {"n":n, "pnl":round(tr["pnl"].sum(),4),
            "wr":round((tr["pnl"]>0).mean(),3),
            "sharpe":round(mu_t/sd_t,3) if (sd_t and sd_t>0) else np.nan,
            "avg_bars":round(tr["bars"].mean(),1)}


# ─── Pair Analysis ────────────────────────────────────────────────────────────

def analyze_pair(t1, t2, s1, s2, sector, tf, lookback):
    idx = s1.index.intersection(s2.index)
    if len(idx) < max(50, lookback * 2): return None
    a = np.log(s1.loc[idx].values)
    b = np.log(s2.loc[idx].values)

    # Spread 1: log ratio
    sp_lr  = pd.Series(a - b, index=s1.loc[idx].index)
    dsp_lr = np.diff(a - b)

    # Spread 2: OLS
    try:
        X    = sm.add_constant(b)
        beta = float(sm.OLS(a, X).fit().params[1])
    except Exception:
        beta = 1.0
    sp_ols  = pd.Series(a - beta*b, index=s1.loc[idx].index)
    dsp_ols = np.diff(a - beta*b)

    # Hurst on increments of each spread
    h_rs_lr,  h_dfa_lr,  h_var_lr,  hp_lr,  r1_lr  = hurst_primary(dsp_lr)
    h_rs_ols, h_dfa_ols, h_var_ols, hp_ols, r1_ols = hurst_primary(dsp_ols)

    # Best spread = lower primary H
    if (not np.isnan(hp_lr)) and (not np.isnan(hp_ols)):
        if hp_lr <= hp_ols:
            sp_best, h_best, stype, r1_best = sp_lr,  hp_lr,  "log_ratio", r1_lr
        else:
            sp_best, h_best, stype, r1_best = sp_ols, hp_ols, "ols",       r1_ols
    elif not np.isnan(hp_lr):
        sp_best, h_best, stype, r1_best = sp_lr,  hp_lr,  "log_ratio", r1_lr
    else:
        sp_best, h_best, stype, r1_best = sp_ols, hp_ols, "ols",       r1_ols

    if np.isnan(h_best): return None

    bt1  = backtest_zscore(sp_best, entry_z=1.0, exit_z=0.0,  lookback=lookback)
    bt15 = backtest_zscore(sp_best, entry_z=1.5, exit_z=0.25, lookback=lookback)

    return {
        "tf": tf, "sector": sector, "t1": t1, "t2": t2,
        "n_bars": len(idx),
        # Hurst log-ratio
        "h_lr_rs": round(h_rs_lr,4) if not np.isnan(h_rs_lr) else np.nan,
        "h_lr_dfa":round(h_dfa_lr,4) if not np.isnan(h_dfa_lr) else np.nan,
        "h_lr_var":round(h_var_lr,4) if not np.isnan(h_var_lr) else np.nan,
        "r1_lr":   round(r1_lr,4)    if not np.isnan(r1_lr)    else np.nan,
        # Hurst OLS
        "h_ols_rs": round(h_rs_ols,4) if not np.isnan(h_rs_ols) else np.nan,
        "h_ols_dfa":round(h_dfa_ols,4) if not np.isnan(h_dfa_ols) else np.nan,
        "h_ols_var":round(h_var_ols,4) if not np.isnan(h_var_ols) else np.nan,
        "r1_ols":   round(r1_ols,4)    if not np.isnan(r1_ols)    else np.nan,
        # Best
        "h_best":   round(h_best,4)   if not np.isnan(h_best)   else np.nan,
        "r1_best":  round(r1_best,4)  if not np.isnan(r1_best)  else np.nan,
        "mean_rev": (h_best < 0.5),
        "stype":    stype,
        "ols_beta": round(beta, 4),
        # Backtests
        "bt1_n":bt1["n"],"bt1_pnl":bt1["pnl"],"bt1_wr":bt1["wr"],
        "bt1_sharpe":bt1["sharpe"],"bt1_bars":bt1["avg_bars"],
        "bt15_n":bt15["n"],"bt15_pnl":bt15["pnl"],"bt15_wr":bt15["wr"],
        "bt15_sharpe":bt15["sharpe"],"bt15_bars":bt15["avg_bars"],
    }


# ─── Data Fetch ───────────────────────────────────────────────────────────────

NSE_OPEN_UTC  = "03:45"    # 9:15 IST
NSE_CLOSE_UTC = "10:00"    # 15:30 IST

def fetch_closes(tickers, interval, period, filter_market_hours=True) -> dict:
    """Download Close prices, filter to NSE market hours for intraday."""
    print(f"  Downloading {interval} data for {len(tickers)} tickers...")

    # Download in batches to avoid rate limits
    all_closes = {}
    batch_size = 10
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        try:
            raw = yf.download(
                batch, period=period, interval=interval,
                progress=False, auto_adjust=True, threads=True
            )
            if raw.empty: continue

            # Extract Close
            if isinstance(raw.columns, pd.MultiIndex):
                close_df = raw["Close"]
            else:
                close_df = raw[["Close"]].rename(columns={"Close": batch[0]})

            close_df.index = pd.to_datetime(close_df.index, utc=True)

            # Filter to NSE market hours for intraday
            if filter_market_hours and interval not in ("1d","1wk","1mo"):
                t_idx = close_df.index.time
                open_t  = pd.Timestamp(f"2000-01-01 {NSE_OPEN_UTC}+00:00").time()
                close_t = pd.Timestamp(f"2000-01-01 {NSE_CLOSE_UTC}+00:00").time()
                mask = (t_idx >= open_t) & (t_idx <= close_t)
                close_df = close_df[mask]

            close_df.index = close_df.index.tz_localize(None)

            for ticker in close_df.columns:
                s = close_df[ticker].dropna()
                s = s[s > 0]
                if len(s) > 50:
                    all_closes[ticker] = s

        except Exception as e:
            print(f"  Warning: batch {batch[:3]}... failed: {e}")
        time.sleep(0.3)  # gentle rate limiting

    print(f"  Successfully loaded: {len(all_closes)} tickers.")
    return all_closes


# ─── Timeframe Processor ──────────────────────────────────────────────────────

def process_tf(tf_name, interval, period, min_bars, lookback, closes=None):
    print(f"\n{'═'*70}")
    print(f"  NIFTY-50 │ TIMEFRAME: {tf_name.upper():6s}  "
          f"(interval={interval}, lookback={lookback})")
    print(f"{'═'*70}")

    if closes is None:
        closes = fetch_closes(ALL_NEEDED, interval, period)

    rows = []
    for sector, tickers in TRADE_SECTORS.items():
        present = [t for t in tickers if t in closes and len(closes[t]) >= min_bars]
        if len(present) < 2: continue
        for t1, t2 in combinations(present, 2):
            r = analyze_pair(t1, t2, closes[t1], closes[t2], sector, tf_name, lookback)
            if r: rows.append(r)

    df = pd.DataFrame(rows)
    if df.empty:
        print("  No pairs computed."); return df, closes

    mr  = df[df["mean_rev"]]
    tmr = df[~df["mean_rev"]]

    print(f"\n  Total pairs analysed : {len(df)}")
    print(f"  H < 0.5 (MR)         : {len(mr)}  ({len(mr)/len(df)*100:.1f}%)")
    print(f"  H ≥ 0.5              : {len(tmr)}  ({len(tmr)/len(df)*100:.1f}%)")

    # H distribution
    print(f"\n  Primary H distribution (R/S+DFA on spread increments):")
    bins = [-0.5, 0.0, 0.2, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 1.1]
    hist = pd.cut(df["h_best"], bins=bins).value_counts().sort_index()
    for interval_bin, cnt in hist.items():
        if cnt == 0: continue
        bar  = "█" * min(cnt, 50)
        flag = " ◄ MR" if interval_bin.right <= 0.5 else ""
        print(f"    {str(interval_bin):20s}: {cnt:3d}  {bar}{flag}")

    # Method min H
    print(f"\n  Min Hurst seen by method:")
    for col, lbl in [("h_lr_rs","R/S log-ratio"),("h_lr_dfa","DFA log-ratio"),
                     ("h_ols_rs","R/S OLS"),("h_ols_dfa","DFA OLS")]:
        if col not in df.columns: continue
        s = df[col].dropna()
        mr_cnt = (s < 0.5).sum()
        flag = f"  ← {mr_cnt} pairs H<0.5!" if mr_cnt > 0 else ""
        print(f"    {lbl:20s}: min={s.min():.4f}  med={s.median():.4f}{flag}")

    # Lag-1 ACF
    r1 = df["r1_best"].dropna()
    neg = (r1 < 0).sum()
    print(f"\n  Lag-1 ACF of spread increments:")
    print(f"    min={r1.min():.3f}  med={r1.median():.3f}  max={r1.max():.3f}"
          f"  │  negative: {neg}/{len(r1)} ({neg/len(r1)*100:.0f}%)")

    # MR pairs table
    if len(mr) > 0:
        print(f"\n  ── ALL MEAN-REVERTING PAIRS (H<0.5) ──")
        cols = ["sector","t1","t2","h_best","h_lr_dfa","h_ols_dfa",
                "r1_best","ols_beta","stype","bt1_n","bt1_wr","bt1_pnl","bt1_sharpe"]
        print(mr[cols].sort_values("h_best").to_string(index=False))

    # H<0.5 vs H>=0.5 backtest
    print(f"\n  {'─'*58}")
    print(f"  Backtest: H<0.5 vs H≥0.5  (z_entry=1.0, z_exit=0)")
    print(f"  {'─'*58}")
    print(f"  {'Metric':<22} {'H<0.5':>10} {'H≥0.5':>10} {'Δ':>10}")
    for met, lbl in [("bt1_wr","Win rate"),("bt1_pnl","Total PnL"),
                     ("bt1_sharpe","Sharpe"),("bt1_bars","Avg bars/trade")]:
        vMR  = mr[met].mean()  if len(mr)  > 0 else np.nan
        vTMR = tmr[met].mean() if len(tmr) > 0 else np.nan
        diff = vMR - vTMR if not (np.isnan(vMR) or np.isnan(vTMR)) else np.nan
        def fmt(v): return f"{v:10.3f}" if not np.isnan(v) else f"{'—':>10}"
        print(f"  {lbl:<22}{fmt(vMR)}{fmt(vTMR)}{fmt(diff)}")

    # Top 15 pairs by Sharpe
    wt = df[df["bt1_n"] >= 5]
    if len(wt) > 0:
        print(f"\n  Top 15 pairs by Sharpe (entry_z=1.0, ≥5 trades):")
        cols = ["sector","t1","t2","h_best","r1_best","stype",
                "bt1_n","bt1_wr","bt1_pnl","bt1_sharpe"]
        top = wt.nlargest(15, "bt1_sharpe")[cols]
        top["mr"] = (top["h_best"] < 0.5).map({True: "★MR", False: ""})
        print(top.to_string(index=False))

    # Per-sector breakdown
    print(f"\n  Per-sector breakdown:")
    print(f"  {'Sector':<16} {'Pairs':>5} {'H<0.5':>6} {'min_H':>7} "
          f"{'MR_wr':>7} {'MR_sh':>7} {'TMR_wr':>8} {'TMR_sh':>8}")
    for sector in sorted(TRADE_SECTORS.keys()):
        gs = df[df["sector"] == sector]
        if len(gs) == 0: continue
        gm  = gs[gs["mean_rev"]]
        gtm = gs[~gs["mean_rev"]]
        min_h = gs["h_best"].min()
        mr_wr = gm["bt1_wr"].mean()    if len(gm)  > 0 else np.nan
        mr_sh = gm["bt1_sharpe"].mean() if len(gm) > 0 else np.nan
        tm_wr = gtm["bt1_wr"].mean()    if len(gtm) > 0 else np.nan
        tm_sh = gtm["bt1_sharpe"].mean() if len(gtm) > 0 else np.nan
        def f(v): return f"{v:7.3f}" if not np.isnan(v) else f"{'—':>7}"
        print(f"  {sector:<16} {len(gs):>5} {len(gm):>6} {min_h:>7.4f}"
              f"{f(mr_wr)}{f(mr_sh)}{f(tm_wr)}{f(tm_sh)}")

    return df, closes


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    configs = [
        # (name,   interval, period, min_bars, lookback)
        ("5m",    "5m",  "60d",  300,  100),
        ("15m",   "15m", "60d",  200,   80),
        ("daily", "1d",  "2y",   200,   50),
    ]

    all_dfs   = []
    cache_5m  = None
    cache_15m = None
    cache_1d  = None

    for tf_name, interval, period, mb, lb in configs:
        # Reuse cached data within same interval
        if   tf_name == "5m":    df, cache_5m  = process_tf(tf_name, interval, period, mb, lb)
        elif tf_name == "15m":   df, cache_15m = process_tf(tf_name, interval, period, mb, lb)
        elif tf_name == "daily": df, cache_1d  = process_tf(tf_name, interval, period, mb, lb)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs: return

    combined = pd.concat(all_dfs, ignore_index=True)
    path = os.path.join(OUT_DIR, "hurst_nifty50_results.csv")
    combined.to_csv(path, index=False)

    # ── Cross-timeframe summary ──────────────────────────────────────────────
    print(f"\n\n{'═'*70}")
    print(f"  CROSS-TIMEFRAME SUMMARY — NIFTY 50 PAIRS")
    print(f"{'═'*70}")

    summary = []
    for tf in ["5m","15m","daily"]:
        g   = combined[combined["tf"] == tf]
        if len(g) == 0: continue
        mr  = g[g["mean_rev"]]
        tmr = g[~g["mean_rev"]]
        r1  = g["r1_best"].dropna()
        summary.append({
            "tf":         tf,
            "pairs":      len(g),
            "H<0.5":      len(mr),
            "pct_H<0.5":  f"{len(mr)/len(g)*100:.1f}%",
            "min_H":      round(g["h_best"].min(), 3),
            "med_H":      round(g["h_best"].median(), 3),
            "neg_ACF%":   f"{(r1<0).mean()*100:.0f}%",
            "MR_WinRate": round(mr["bt1_wr"].mean(),3)    if len(mr)>0 else "—",
            "MR_Sharpe":  round(mr["bt1_sharpe"].mean(),3) if len(mr)>0 else "—",
            "TMR_WinRate":round(tmr["bt1_wr"].mean(),3)   if len(tmr)>0 else "—",
            "TMR_Sharpe": round(tmr["bt1_sharpe"].mean(),3) if len(tmr)>0 else "—",
        })
    print(pd.DataFrame(summary).set_index("tf").to_string())

    # ── Global H<0.5 pairs sorted by h_best ─────────────────────────────────
    all_mr = combined[combined["mean_rev"]].sort_values("h_best")
    print(f"\n  ALL H<0.5 PAIRS — {len(all_mr)} total across timeframes:")
    if len(all_mr) > 0:
        cols = ["tf","sector","t1","t2","h_best","r1_best",
                "bt1_n","bt1_wr","bt1_pnl","bt1_sharpe"]
        print(all_mr[cols].to_string(index=False))
    else:
        print("  None found. Top 15 closest to H=0.5:")
        cols = ["tf","sector","t1","t2","h_best","r1_best",
                "bt1_n","bt1_wr","bt1_pnl","bt1_sharpe"]
        print(combined.nsmallest(15,"h_best")[cols].to_string(index=False))

    # ── Best pairs by Sharpe across all TFs ─────────────────────────────────
    print(f"\n  GLOBAL TOP 20 by Sharpe (all TFs, ≥5 trades):")
    best = combined[combined["bt1_n"] >= 5].nlargest(20,"bt1_sharpe")
    cols = ["tf","sector","t1","t2","h_best","r1_best","bt1_n",
            "bt1_wr","bt1_pnl","bt1_sharpe"]
    best["MR"] = (best["h_best"] < 0.5).map({True:"★MR","False":""})
    print(best[cols + ["MR"]].to_string(index=False))

    print(f"\n  Full results saved → {path}")


if __name__ == "__main__":
    main()
