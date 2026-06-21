"""
Hurst-Only Pairs Analysis — Full MIDAS Dataset
===============================================
Runs the same corrected Hurst methodology on all tickers in the MIDAS data folder.
Pairs grouped by GICS sector. Summarises by timeframe and price range.

H applied to spread FIRST DIFFERENCES (increments), R/S + DFA consensus.
"""

import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from itertools import combinations
import statsmodels.api as sm
import os, random

SEED = 42
random.seed(SEED); np.random.seed(SEED)

DATA_DIR    = "/Users/rahulgirishkumar/TRADING/MIDAS/data"
OUT_DIR     = "/Users/rahulgirishkumar/TRADING/MIDAS/results"
os.makedirs(OUT_DIR, exist_ok=True)

# ─── GICS Sector Map ─────────────────────────────────────────────────────────
# S&P 500 GICS classification (curated for tickers present in the dataset)

SECTOR_MAP = {
    # ── Information Technology (top 20 by market cap / liquidity) ───────────
    "Info_Tech": [
        "AAPL","MSFT","NVDA","AVGO","ORCL","CRM","ACN","CSCO","IBM","TXN",
        "QCOM","AMD","INTC","AMAT","ADI","KLAC","LRCX","MU","ADSK","AKAM",
    ],
    # ── Health Care ─────────────────────────────────────────────────────────
    "Health_Care": [
        "JNJ","LLY","ABBV","TMO","ABT","MRK","DHR","AMGN","BMY","GILD",
        "UNH","CI","ELV","HCA","ISRG","REGN","VRTX","BIIB","ZBH","SYK",
    ],
    # ── Financials ──────────────────────────────────────────────────────────
    "Financials": [
        "JPM","BAC","WFC","GS","MS","BLK","AIG","CB","ALL","PRU",
        "MET","AXP","COF","DFS","SYF","PNC","USB","TFC","AFL","AIZ",
    ],
    # ── Consumer_Discretionary ──────────────────────────────────────────────
    "Consumer_Disc": [
        "AMZN","TSLA","HD","NKE","MCD","SBUX","TJX","LOW","GM","F",
        "ORLY","AZO","LVS","MGM","MAR","HLT","CCL","RCL","CMG","NCLH",
    ],
    # ── Consumer_Staples ────────────────────────────────────────────────────
    "Consumer_Stap": [
        "WMT","COST","PG","KO","PEP","PM","MO","CL","CHD","CLX",
        "KHC","HSY","GIS","MDLZ","KR","ADM","BG","IFF",
    ],
    # ── Energy ──────────────────────────────────────────────────────────────
    "Energy": [
        "XOM","CVX","COP","SLB","OXY","DVN","PSX","VLO","MPC","HES",
        "EOG","APA","AR","RRC","KMI","LNG","MMP","WMB",
    ],
    # ── Industrials ─────────────────────────────────────────────────────────
    "Industrials": [
        "HON","UPS","CAT","DE","MMM","GE","LMT","RTX","NOC","GD",
        "BA","LHX","TDG","FDX","CSX","NSC","UNP","EMR","ETN","ROK",
    ],
    # ── Materials ───────────────────────────────────────────────────────────
    "Materials": [
        "LIN","APD","DD","DOW","EMN","ECL","SHW","NEM","FCX","ALB",
        "BALL","CF","MOS","NUE","STLD","RS","WLK","ATI",
    ],
    # ── Utilities ───────────────────────────────────────────────────────────
    "Utilities": [
        "NEE","DUK","SO","EXC","AEP","CMS","D","ETR","PPL","WEC",
        "ES","ED","FE","CNP","ATO","SRE","PEG","XEL","AWK","NRG",
    ],
    # ── Real_Estate ─────────────────────────────────────────────────────────
    "Real_Estate": [
        "AMT","PLD","EQIX","SPG","O","WELL","AVB","EQR","PSA","ESS",
        "UDR","ARE","EXR","CUBE","ADC","NNN","FRT","KIM",
    ],
    # ── Communication_Services ──────────────────────────────────────────────
    "Comm_Services": [
        "GOOGL","META","NFLX","CMCSA","VZ","T","DIS","CHTR","TMUS",
        "EA","TTWO","OMC","IPG","NWSA","WBD",
    ],
}

# Flatten to get all needed tickers
ALL_NEEDED = list({t for v in SECTOR_MAP.values() for t in v})

# ─── Hurst Functions ──────────────────────────────────────────────────────────

def hurst_rs(ds: np.ndarray) -> float:
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


def hurst_primary(ds):
    """Returns (h_rs, h_dfa, h_primary, lag1_acf)."""
    h_rs  = hurst_rs(ds)
    h_dfa = hurst_dfa(ds)
    vals  = [v for v in [h_rs, h_dfa] if not np.isnan(v)]
    h_p   = float(np.mean(vals)) if vals else np.nan
    ds_   = ds[np.isfinite(ds)]
    r1    = float(np.corrcoef(ds_[:-1], ds_[1:])[0, 1]) if len(ds_) > 10 else np.nan
    return h_rs, h_dfa, h_p, r1


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
                   or abs(zi) > stop_z or i == len(sv)-1
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

def analyze_pair(t1, t2, s1, s2, sector, tf, lookback, avg_price):
    idx = s1.index.intersection(s2.index)
    if len(idx) < max(50, lookback * 2): return None
    a = np.log(s1.loc[idx].values.astype(float))
    b = np.log(s2.loc[idx].values.astype(float))
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))): return None

    # Log-ratio spread
    sp_lr  = pd.Series(a - b, index=s1.loc[idx].index)
    dsp_lr = np.diff(a - b)

    # OLS spread
    try:
        X    = sm.add_constant(b)
        beta = float(sm.OLS(a, X).fit().params[1])
    except Exception:
        beta = 1.0
    sp_ols  = pd.Series(a - beta*b, index=s1.loc[idx].index)
    dsp_ols = np.diff(a - beta*b)

    h_rs_lr,  h_dfa_lr,  hp_lr,  r1_lr  = hurst_primary(dsp_lr)
    h_rs_ols, h_dfa_ols, hp_ols, r1_ols = hurst_primary(dsp_ols)

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

    bt = backtest_zscore(sp_best, entry_z=1.0, exit_z=0.0, lookback=lookback)

    # Price bucket
    p = avg_price
    if   p < 20:    pbkt = "<$20"
    elif p < 50:    pbkt = "$20-50"
    elif p < 100:   pbkt = "$50-100"
    elif p < 200:   pbkt = "$100-200"
    elif p < 500:   pbkt = "$200-500"
    else:           pbkt = "$500+"

    return {
        "tf": tf, "sector": sector, "t1": t1, "t2": t2,
        "n_bars": len(idx),
        "avg_price": round(avg_price, 1),
        "price_bucket": pbkt,
        "h_best":  round(h_best, 4) if not np.isnan(h_best) else np.nan,
        "h_lr_rs": round(h_rs_lr, 4) if not np.isnan(h_rs_lr) else np.nan,
        "h_lr_dfa":round(h_dfa_lr,4) if not np.isnan(h_dfa_lr) else np.nan,
        "h_ols_rs":round(h_rs_ols,4) if not np.isnan(h_rs_ols) else np.nan,
        "h_ols_dfa":round(h_dfa_ols,4)if not np.isnan(h_dfa_ols) else np.nan,
        "r1_best": round(r1_best, 4) if not np.isnan(r1_best) else np.nan,
        "mean_rev": (h_best < 0.5),
        "stype":    stype,
        "ols_beta": round(beta, 4),
        "bt_n":  bt["n"],  "bt_pnl": bt["pnl"],
        "bt_wr": bt["wr"], "bt_sharpe": bt["sharpe"],
        "bt_bars": bt["avg_bars"],
    }


# ─── Data Loader ─────────────────────────────────────────────────────────────

def load_closes(filepath, min_bars=100) -> dict:
    df = pd.read_csv(filepath, usecols=["Date","Ticker","Close"])
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Close","Ticker"])
    df = df[df["Close"] > 0]
    out = {}
    for ticker, grp in df.groupby("Ticker"):
        grp = grp.sort_values("Date").set_index("Date")["Close"]
        if len(grp) >= min_bars:
            out[ticker] = grp
    return out


# ─── Timeframe Processor ─────────────────────────────────────────────────────

def process_tf(tf_name, filepath, min_bars, lookback):
    print(f"\n{'═'*72}")
    print(f"  TIMEFRAME: {tf_name.upper():8s}  (file={os.path.basename(filepath)}, lookback={lookback})")
    print(f"{'═'*72}")

    closes = load_closes(filepath, min_bars)
    print(f"  Loaded {len(closes)} tickers with ≥{min_bars} bars")

    rows = []
    for sector, tickers in SECTOR_MAP.items():
        present = [t for t in tickers if t in closes]
        if len(present) < 2: continue
        pair_count = 0
        for t1, t2 in combinations(present, 2):
            avg_p = (closes[t1].mean() + closes[t2].mean()) / 2
            r = analyze_pair(t1, t2, closes[t1], closes[t2],
                             sector, tf_name, lookback, avg_p)
            if r:
                rows.append(r)
                pair_count += 1
        if pair_count > 0:
            print(f"    {sector:<22}: {len(present)} tickers → {pair_count} pairs")

    df = pd.DataFrame(rows)
    if df.empty:
        print("  No pairs computed."); return df

    mr  = df[df["mean_rev"]]
    tmr = df[~df["mean_rev"]]

    print(f"\n  Total pairs : {len(df)}")
    print(f"  H < 0.5     : {len(mr)} ({len(mr)/len(df)*100:.1f}%)")
    print(f"  H ≥ 0.5     : {len(tmr)} ({len(tmr)/len(df)*100:.1f}%)")

    # H distribution
    print(f"\n  H distribution (R/S+DFA on spread increments):")
    bins = [-0.5, 0.2, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8, 1.2]
    hist = pd.cut(df["h_best"], bins=bins).value_counts().sort_index()
    for iv, cnt in hist.items():
        if cnt == 0: continue
        bar  = "█" * min(cnt // 3 + 1, 50)
        flag = " ◄ MR" if iv.right <= 0.5 else ""
        print(f"    {str(iv):20s}: {cnt:4d}  {bar}{flag}")

    # Lag-1 ACF summary
    r1 = df["r1_best"].dropna()
    neg = (r1 < 0).sum()
    print(f"\n  Lag-1 ACF: min={r1.min():.3f} med={r1.median():.3f} max={r1.max():.3f}"
          f"  | negative: {neg}/{len(r1)} ({neg/len(r1)*100:.0f}%)")

    # H<0.5 vs H>=0.5 backtest comparison
    print(f"\n  {'─'*60}")
    print(f"  Backtest comparison  (z_entry=1.0, z_exit=0, stop=3.5)")
    print(f"  {'─'*60}")
    print(f"  {'Metric':<24} {'H<0.5':>10} {'H≥0.5':>10} {'Δ':>10}")
    for met, lbl in [("bt_wr","Win rate"),("bt_pnl","Total PnL"),
                     ("bt_sharpe","Sharpe"),("bt_bars","Avg bars/trade"),
                     ("bt_n","Avg trades/pair")]:
        vMR  = mr[met].mean()  if len(mr)  > 0 else np.nan
        vTMR = tmr[met].mean() if len(tmr) > 0 else np.nan
        diff = vMR - vTMR if not (np.isnan(vMR) or np.isnan(vTMR)) else np.nan
        def fmt(v): return f"{v:10.3f}" if not np.isnan(v) else f"{'—':>10}"
        print(f"  {lbl:<24}{fmt(vMR)}{fmt(vTMR)}{fmt(diff)}")

    # Per-sector breakdown
    print(f"\n  Per-sector breakdown:")
    print(f"  {'Sector':<22} {'Pairs':>5} {'H<0.5':>6} {'minH':>6}"
          f" {'MR_WR':>7} {'MR_Sh':>7} {'TMR_WR':>8} {'TMR_Sh':>8}")
    for sec in sorted(SECTOR_MAP.keys()):
        gs  = df[df["sector"] == sec]
        if len(gs) == 0: continue
        gm  = gs[gs["mean_rev"]]
        gtm = gs[~gs["mean_rev"]]
        minh = gs["h_best"].min()
        def f(v): return f"{v:7.3f}" if not np.isnan(v) else f"{'—':>7}"
        print(f"  {sec:<22} {len(gs):>5} {len(gm):>6} {minh:>6.3f}"
              f"{f(gm['bt_wr'].mean() if len(gm)>0 else np.nan)}"
              f"{f(gm['bt_sharpe'].mean() if len(gm)>0 else np.nan)}"
              f"{f(gtm['bt_wr'].mean() if len(gtm)>0 else np.nan)}"
              f"{f(gtm['bt_sharpe'].mean() if len(gtm)>0 else np.nan)}")

    # Price bucket breakdown
    print(f"\n  Price bucket breakdown:")
    print(f"  {'Bucket':<12} {'Pairs':>5} {'H<0.5':>6} {'pct':>6}"
          f" {'minH':>6} {'MR_WR':>7} {'MR_Sh':>7} {'TMR_WR':>8} {'TMR_Sh':>8}")
    for bkt in ["<$20","$20-50","$50-100","$100-200","$200-500","$500+"]:
        gb  = df[df["price_bucket"] == bkt]
        if len(gb) == 0: continue
        gm  = gb[gb["mean_rev"]]
        gtm = gb[~gb["mean_rev"]]
        pct = f"{len(gm)/len(gb)*100:.0f}%"
        minh = gb["h_best"].min()
        def f(v): return f"{v:7.3f}" if not np.isnan(v) else f"{'—':>7}"
        print(f"  {bkt:<12} {len(gb):>5} {len(gm):>6} {pct:>6}"
              f" {minh:>6.3f}"
              f"{f(gm['bt_wr'].mean() if len(gm)>0 else np.nan)}"
              f"{f(gm['bt_sharpe'].mean() if len(gm)>0 else np.nan)}"
              f"{f(gtm['bt_wr'].mean() if len(gtm)>0 else np.nan)}"
              f"{f(gtm['bt_sharpe'].mean() if len(gtm)>0 else np.nan)}")

    # Top 20 H<0.5 pairs by Sharpe
    wt = mr[mr["bt_n"] >= 5]
    if len(wt) > 0:
        print(f"\n  Top 20 H<0.5 pairs by Sharpe (≥5 trades):")
        cols = ["sector","t1","t2","h_best","r1_best","price_bucket",
                "bt_n","bt_wr","bt_pnl","bt_sharpe"]
        print(wt.nlargest(20,"bt_sharpe")[cols].to_string(index=False))

    return df


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    configs = [
        ("5m",    "tickers_5m_ohlcv.csv",  300, 100),
        ("15m",   "tickers_15m_ohlcv.csv", 200,  80),
        ("30m",   "tickers_30m_ohlcv.csv", 150,  60),
        ("1h",    "tickers_1h_ohlcv.csv",  200,  50),
        ("daily", "tickers_ohlcv.csv",     180,  40),
    ]

    all_dfs = []
    for tf_name, fname, mb, lb in configs:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  Skipping {tf_name}: {fname} not found"); continue
        df = process_tf(tf_name, fpath, mb, lb)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs: return

    combined = pd.concat(all_dfs, ignore_index=True)
    out_path = os.path.join(OUT_DIR, "hurst_midas_full_results.csv")
    combined.to_csv(out_path, index=False)

    # ── Cross-Timeframe Summary ──────────────────────────────────────────────
    print(f"\n\n{'═'*72}")
    print(f"  CROSS-TIMEFRAME SUMMARY")
    print(f"{'═'*72}")
    tfs = [c[0] for c in configs if os.path.exists(os.path.join(DATA_DIR, c[1]))]
    summary = []
    for tf in tfs:
        g   = combined[combined["tf"] == tf]
        if len(g) == 0: continue
        mr  = g[g["mean_rev"]]
        tmr = g[~g["mean_rev"]]
        r1  = g["r1_best"].dropna()
        summary.append({
            "tf":          tf,
            "pairs":       len(g),
            "H<0.5":       len(mr),
            "pct_H<0.5":   f"{len(mr)/len(g)*100:.1f}%",
            "min_H":       round(g["h_best"].min(), 3),
            "med_H":       round(g["h_best"].median(), 3),
            "neg_ACF%":    f"{(r1<0).mean()*100:.0f}%",
            "MR_WinRate":  round(mr["bt_wr"].mean(), 3)    if len(mr)>0 else "—",
            "MR_Sharpe":   round(mr["bt_sharpe"].mean(), 3) if len(mr)>0 else "—",
            "TMR_WinRate": round(tmr["bt_wr"].mean(), 3)   if len(tmr)>0 else "—",
            "TMR_Sharpe":  round(tmr["bt_sharpe"].mean(), 3) if len(tmr)>0 else "—",
        })
    print(pd.DataFrame(summary).set_index("tf").to_string())

    # ── Cross-Timeframe Price Bucket Summary ─────────────────────────────────
    print(f"\n  PRICE BUCKET SUMMARY (across all timeframes)")
    print(f"  {'Bucket':<12} {'TF':<7} {'Pairs':>5} {'H<0.5':>6} {'pct':>6}"
          f" {'minH':>6} {'MR_Sh':>7} {'TMR_Sh':>8}")
    for bkt in ["<$20","$20-50","$50-100","$100-200","$200-500","$500+"]:
        for tf in tfs:
            gb  = combined[(combined["tf"]==tf) & (combined["price_bucket"]==bkt)]
            if len(gb) == 0: continue
            gm  = gb[gb["mean_rev"]]
            gtm = gb[~gb["mean_rev"]]
            pct = f"{len(gm)/len(gb)*100:.0f}%"
            minh = gb["h_best"].min()
            def f(v): return f"{v:7.3f}" if not np.isnan(v) else f"{'—':>7}"
            print(f"  {bkt:<12} {tf:<7} {len(gb):>5} {len(gm):>6} {pct:>6}"
                  f" {minh:>6.3f}"
                  f"{f(gm['bt_sharpe'].mean() if len(gm)>0 else np.nan)}"
                  f"{f(gtm['bt_sharpe'].mean() if len(gtm)>0 else np.nan)}")

    # ── Global Top 30 H<0.5 pairs by Sharpe ─────────────────────────────────
    print(f"\n  GLOBAL TOP 30 H<0.5 PAIRS by Sharpe (≥5 trades, all TFs):")
    all_mr = combined[(combined["mean_rev"]) & (combined["bt_n"] >= 5)]
    if len(all_mr) > 0:
        cols = ["tf","sector","t1","t2","h_best","r1_best",
                "price_bucket","bt_n","bt_wr","bt_pnl","bt_sharpe"]
        print(all_mr.nlargest(30,"bt_sharpe")[cols].to_string(index=False))

    print(f"\n  Full results saved → {out_path}")


if __name__ == "__main__":
    main()
