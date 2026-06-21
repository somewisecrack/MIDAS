"""
Hurst Exponent Sector Pairs Analysis
======================================
Tests economically-linked (same-sector) ticker pairs where
mean reversion is far more plausible than for random pairs.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import random
from itertools import combinations
from statsmodels.tsa.stattools import coint, adfuller
import statsmodels.api as sm
import os

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

DATA_DIR = "/Users/rahulgirishkumar/TRADING/MIDAS/data"

SECTORS = {
    "Energy":    ["XOM","CVX","COP","PSX","VLO","MPC","OXY","HAL","SLB","DVN","EOG","FANG"],
    "Banks":     ["JPM","BAC","WFC","C","GS","MS","USB","TFC","PNC","COF","RF","KEY","HBAN","CFG","FITB","MTB","ZION"],
    "Airlines":  ["UAL","DAL","AAL","LUV","ALK"],
    "Semis":     ["NVDA","AMD","INTC","QCOM","MU","AMAT","LRCX","KLAC","MCHP","ADI","NXPI","TXN","AVGO"],
    "Pharma":    ["JNJ","PFE","ABBV","MRK","BMY","AMGN","GILD","BIIB","REGN","VRTX"],
    "Retail":    ["WMT","COST","TGT","HD","LOW","AMZN","EBAY","DG","DLTR","ROST","TJX"],
    "Utilities": ["NEE","DUK","SO","AEP","EXC","SRE","D","XEL","PCG","WEC","ETR","PEG","PPL","CMS"],
}


# ── Hurst exponents ────────────────────────────────────────────────────────────

def hurst_rs(series: np.ndarray, min_window: int = 8) -> float:
    series = np.asarray(series, dtype=float)
    series = series[~np.isnan(series)]
    n = len(series)
    if n < 20:
        return np.nan
    lags = np.unique(np.geomspace(min_window, n // 2, num=20, dtype=int))
    rs_vals, lag_vals = [], []
    for lag in lags:
        sub_rs = []
        for start in range(0, n - lag, lag):
            chunk = series[start: start + lag]
            mean  = chunk.mean()
            dev   = np.cumsum(chunk - mean)
            r     = dev.max() - dev.min()
            s     = chunk.std(ddof=1)
            if s > 0:
                sub_rs.append(r / s)
        if sub_rs:
            rs_vals.append(np.mean(sub_rs))
            lag_vals.append(lag)
    if len(rs_vals) < 4:
        return np.nan
    slope, *_ = np.polyfit(np.log(lag_vals), np.log(rs_vals), 1)
    return float(slope)


def hurst_variance(series: np.ndarray) -> float:
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


# ── Data loader ────────────────────────────────────────────────────────────────

def load_closes(filename: str, needed_tickers: list) -> dict:
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path, usecols=["Date", "Close", "Ticker"])
    df = df[df["Ticker"].isin(needed_tickers)]
    df["Date"] = pd.to_datetime(df["Date"], utc=False)
    if df["Date"].dt.tz is not None:
        df["Date"] = df["Date"].dt.tz_convert(None)
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0]
    df = df.drop_duplicates(["Date", "Ticker"])
    out = {}
    for ticker, grp in df.groupby("Ticker", sort=False):
        s = grp.set_index("Date")["Close"].sort_index()
        s = s[~s.index.duplicated(keep="last")]
        out[ticker] = s
    return out


# ── Pair maths ────────────────────────────────────────────────────────────────

def align(s1, s2):
    idx = s1.index.intersection(s2.index)
    return s1.loc[idx], s2.loc[idx]


def spread_and_beta(s1, s2):
    log1 = np.log(s1.values)
    log2 = np.log(s2.values)
    X    = sm.add_constant(log2)
    res  = sm.OLS(log1, X).fit()
    beta = float(res.params[1])
    sprd = pd.Series(log1 - beta * log2, index=s1.index)
    return sprd, beta


def adf_pvalue(series):
    try:
        return adfuller(series.dropna(), maxlag=5, autolag="AIC")[1]
    except Exception:
        return np.nan


# ── Backtest ──────────────────────────────────────────────────────────────────

def backtest(spread, s1, s2, beta,
             entry_z=1.5, exit_z=0.25, stop_z=3.5, lookback=40):
    roll_mean = spread.rolling(lookback).mean()
    roll_std  = spread.rolling(lookback).std()
    z = (spread - roll_mean) / roll_std

    position, entry_price, entry_idx = 0, None, None
    trades = []
    z_arr  = z.values
    idx    = spread.index
    s1v    = s1.values
    s2v    = s2.values

    for i in range(lookback + 1, len(z_arr)):
        zi = z_arr[i]
        if np.isnan(zi):
            continue
        if position == 0:
            if   zi < -entry_z:  position, entry_price, entry_idx = +1, (s1v[i], s2v[i]), i
            elif zi >  entry_z:  position, entry_price, entry_idx = -1, (s1v[i], s2v[i]), i
        else:
            if abs(zi) < exit_z or abs(zi) > stop_z or i == len(z_arr) - 1:
                ep = np.log(entry_price[0]) - beta * np.log(entry_price[1])
                pnl = position * (spread.iloc[i] - ep)
                trades.append({"pnl": pnl, "bars": i - entry_idx,
                                "stopped": abs(zi) > stop_z, "entry_z": entry_price})
                position = 0

    if not trades:
        return {"n": 0, "pnl": 0, "wr": np.nan, "sharpe": np.nan, "bars": np.nan, "stops": 0}
    tr  = pd.DataFrame(trades)
    n   = len(tr)
    avg = tr["pnl"].mean()
    std = tr["pnl"].std()
    return {
        "n":      n,
        "pnl":    round(tr["pnl"].sum(), 5),
        "wr":     round((tr["pnl"] > 0).mean(), 3),
        "sharpe": round(avg / std * np.sqrt(252), 3) if std > 0 else np.nan,
        "bars":   round(tr["bars"].mean(), 1),
        "stops":  int(tr["stopped"].sum()),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def analyze_sector(sector, tickers, closes, tf, min_bars=180, lookback=40):
    present = [t for t in tickers if t in closes and len(closes[t]) >= min_bars]
    if len(present) < 2:
        return []

    rows = []
    for t1, t2 in combinations(present, 2):
        s1, s2 = align(closes[t1], closes[t2])
        if len(s1) < min_bars:
            continue

        sprd, beta = spread_and_beta(s1, s2)
        sv = sprd.values

        h_rs  = hurst_rs(sv)
        h_var = hurst_variance(sv)
        h     = np.nanmean([h_rs, h_var])

        try:
            _, coint_p, _ = coint(np.log(s1.values), np.log(s2.values))
        except Exception:
            coint_p = np.nan

        adf_p = adf_pvalue(sprd)

        bt = backtest(sprd, s1, s2, beta, lookback=lookback)

        rows.append({
            "tf": tf, "sector": sector,
            "t1": t1, "t2": t2,
            "n_bars": len(s1),
            "hurst_rs":  round(h_rs,  4) if not np.isnan(h_rs)  else np.nan,
            "hurst_var": round(h_var, 4) if not np.isnan(h_var) else np.nan,
            "hurst":     round(h,     4) if not np.isnan(h)     else np.nan,
            "mean_rev":  h < 0.5 if not np.isnan(h) else False,
            "coint_p":   round(coint_p, 4),
            "adf_p":     round(adf_p,   4) if not np.isnan(adf_p) else np.nan,
            "cointegrated": (coint_p < 0.10) if not np.isnan(coint_p) else False,
            "spread_stationary": (adf_p < 0.10) if not np.isnan(adf_p) else False,
            **{f"bt_{k}": v for k, v in bt.items()},
        })
    return rows


def main():
    all_tickers = list({t for tlist in SECTORS.values() for t in tlist})

    timeframes = {
        "daily": ("tickers_ohlcv.csv",      180, 40),
        "1h":    ("tickers_1h_ohlcv.csv",   500, 100),
        "15m":   ("tickers_15m_ohlcv.csv",  400, 80),
    }

    all_rows = []

    for tf, (fname, min_bars, lookback) in timeframes.items():
        print(f"\n{'═'*65}")
        print(f"  TIMEFRAME: {tf.upper()}")
        print(f"{'═'*65}")
        closes = load_closes(fname, all_tickers)
        print(f"  Loaded {len(closes)} tickers.")

        tf_rows = []
        for sector, tickers in SECTORS.items():
            rows = analyze_sector(sector, tickers, closes, tf, min_bars, lookback)
            tf_rows.extend(rows)
            n_pairs = len(rows)
            if n_pairs == 0:
                print(f"  {sector:12s}: no pairs")
                continue
            df_s = pd.DataFrame(rows)
            mr   = (df_s["mean_rev"] == True).sum()
            co   = (df_s["cointegrated"] == True).sum()
            avg_h = df_s["hurst"].mean()
            print(f"  {sector:12s}: {n_pairs:2d} pairs | "
                  f"H_avg={avg_h:.3f} | MR(H<0.5)={mr} | Coint={co}")

        all_rows.extend(tf_rows)

        df_tf = pd.DataFrame(tf_rows)
        if df_tf.empty:
            continue

        print(f"\n  {'─'*60}")
        print(f"  FULL RESULTS — {tf.upper()}")
        print(f"  {'─'*60}")
        print(f"  Total pairs:        {len(df_tf)}")
        mr_all = df_tf[df_tf["mean_rev"] == True]
        co_all = df_tf[df_tf["cointegrated"] == True]
        st_all = df_tf[df_tf["spread_stationary"] == True]
        mr_co  = df_tf[df_tf["mean_rev"] & df_tf["cointegrated"]]
        print(f"  Mean-reverting (H<0.5):      {len(mr_all)} ({len(mr_all)/len(df_tf)*100:.0f}%)")
        print(f"  Cointegrated (coint p<0.10): {len(co_all)} ({len(co_all)/len(df_tf)*100:.0f}%)")
        print(f"  ADF stationary (adf p<0.10): {len(st_all)} ({len(st_all)/len(df_tf)*100:.0f}%)")
        print(f"  Both MR + Coint:             {len(mr_co)}")

        # Hurst distribution
        print(f"\n  Hurst distribution:")
        bins = [0,0.3,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,1.0]
        hist = pd.cut(df_tf["hurst"], bins=bins).value_counts().sort_index()
        for interval, cnt in hist.items():
            bar = "█" * cnt
            label = "← MEAN REVERTING" if interval.right <= 0.5 else ""
            print(f"    {str(interval):18s}: {cnt:3d}  {bar} {label}")

        # Best pairs
        print(f"\n  Top pairs by Sharpe (cointegrated):")
        best = (df_tf[df_tf["cointegrated"] & (df_tf["bt_n"] >= 3)]
                .nlargest(10, "bt_sharpe")
                [["sector","t1","t2","hurst","coint_p","adf_p",
                  "bt_n","bt_wr","bt_pnl","bt_sharpe","bt_bars"]])
        print(best.to_string(index=False))

        # MR comparison
        active = df_tf[df_tf["bt_n"] > 0]
        if len(active) > 0:
            mr_t  = active[active["mean_rev"]]
            tmr_t = active[~active["mean_rev"]]
            print(f"\n  Mean-Rev vs Trending backtest comparison:")
            print(f"  {'Metric':<20} {'H<0.5 (MR)':>12} {'H>0.5 (Trend)':>14}")
            for m, lbl in [("bt_wr","Win Rate"),("bt_pnl","Total PnL"),("bt_sharpe","Sharpe")]:
                v1 = mr_t[m].mean()  if len(mr_t)  else float("nan")
                v2 = tmr_t[m].mean() if len(tmr_t) else float("nan")
                print(f"  {lbl:<20} {v1:>12.3f} {v2:>14.3f}")

    # Save
    out = pd.DataFrame(all_rows)
    path = "/Users/rahulgirishkumar/TRADING/MIDAS/results/hurst_sector_results.csv"
    out.to_csv(path, index=False)
    print(f"\n\nResults saved → {path}")

    # Cross-timeframe summary
    print(f"\n{'═'*65}")
    print(f"  CROSS-TIMEFRAME × SECTOR SUMMARY")
    print(f"{'═'*65}")
    summary = (out.groupby(["tf","sector"])
               .agg(n=("t1","count"),
                    pct_mr=("mean_rev","mean"),
                    avg_h=("hurst","mean"),
                    pct_coint=("cointegrated","mean"),
                    pct_adf=("spread_stationary","mean"),
                    med_sharpe=("bt_sharpe","median"),
                    pct_profit=("bt_pnl", lambda x: (x>0).mean()))
               .round(3))
    print(summary.to_string())

    # Absolute best pairs across all timeframes
    best_global = (out[(out["cointegrated"]) & (out["bt_n"] >= 3)]
                   .nlargest(15, "bt_sharpe")
                   [["tf","sector","t1","t2","hurst","coint_p","adf_p",
                     "bt_n","bt_wr","bt_pnl","bt_sharpe"]])
    print(f"\n  TOP 15 PAIRS OVERALL (cointegrated, ≥3 trades):")
    print(best_global.to_string(index=False))


if __name__ == "__main__":
    main()
