from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import yfinance as yf
from tqdm import tqdm


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
BATCH_SIZE = 25

TICKER_FILES = [
    ("tickers_ohlcv.csv", "1d", "5y"),
    ("tickers_1h_ohlcv.csv", "1h", "730d"),
    ("tickers_30m_ohlcv.csv", "30m", "60d"),
    ("tickers_15m_ohlcv.csv", "15m", "60d"),
    ("tickers_5m_ohlcv.csv", "5m", "60d"),
]

SINGLE_FILES = [
    ("SPY_ohlcv.csv", "SPY", "1d", "max"),
    ("gold_daily.csv", "GC=F", "1d", "10y"),
    ("gold_15m.csv", "GC=F", "15m", "60d"),
    ("gold_5m.csv", "GC=F", "5m", "60d"),
]

OUTPUT_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume", "Ticker", "Adj Close"]


def load_ticker_universe() -> list[str]:
    tickers: set[str] = set()
    for filename, _, _ in TICKER_FILES:
        path = DATA_DIR / filename
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=lambda c: c == "Ticker")
        tickers.update(df["Ticker"].dropna().astype(str).unique())
    return sorted(tickers)


def normalize_download_frame(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    frame = df.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        if ticker in frame.columns.get_level_values(0):
            frame = frame[ticker]
        elif ticker in frame.columns.get_level_values(1):
            frame = frame.xs(ticker, level=1, axis=1)
        else:
            return pd.DataFrame(columns=OUTPUT_COLUMNS)

    frame = frame.dropna(how="all").reset_index()
    frame = frame.rename(columns={"Datetime": "Date", "index": "Date"})
    if "Date" not in frame.columns:
        first_col = frame.columns[0]
        frame = frame.rename(columns={first_col: "Date"})

    frame["Ticker"] = ticker
    for col in OUTPUT_COLUMNS:
        if col not in frame.columns:
            frame[col] = pd.NA

    frame = frame[OUTPUT_COLUMNS]
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.tz_localize(None)
    frame = frame.dropna(subset=["Date", "Close"])
    return frame


def download_batch(tickers: list[str], interval: str, period: str) -> dict[str, pd.DataFrame]:
    raw = yf.download(
        tickers,
        period=period,
        interval=interval,
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )

    frames: dict[str, pd.DataFrame] = {}
    if len(tickers) == 1:
        frames[tickers[0]] = normalize_download_frame(raw, tickers[0])
        return frames

    for ticker in tickers:
        frames[ticker] = normalize_download_frame(raw, ticker)
    return frames


def download_with_fallback(tickers: list[str], interval: str, period: str) -> tuple[list[pd.DataFrame], list[str]]:
    frames: list[pd.DataFrame] = []
    failed: list[str] = []

    try:
        batch_frames = download_batch(tickers, interval, period)
    except Exception as exc:
        print(f"Batch failed ({tickers[0]}..{tickers[-1]}): {exc}")
        batch_frames = {}

    missing = []
    for ticker in tickers:
        frame = batch_frames.get(ticker, pd.DataFrame())
        if frame.empty:
            missing.append(ticker)
        else:
            frames.append(frame)

    for ticker in missing:
        try:
            frame = download_batch([ticker], interval, period).get(ticker, pd.DataFrame())
            if frame.empty:
                failed.append(ticker)
            else:
                frames.append(frame)
        except Exception:
            failed.append(ticker)
        time.sleep(0.15)

    return frames, failed


def refresh_ticker_file(filename: str, interval: str, period: str, tickers: list[str]) -> dict:
    print(f"\n=== Refreshing {filename} ({interval}, {period}) ===")
    all_frames: list[pd.DataFrame] = []
    failed: list[str] = []

    for i in tqdm(range(0, len(tickers), BATCH_SIZE)):
        batch = tickers[i : i + BATCH_SIZE]
        frames, batch_failed = download_with_fallback(batch, interval, period)
        all_frames.extend(frames)
        failed.extend(batch_failed)
        time.sleep(0.4)

    if not all_frames:
        print(f"No data downloaded for {filename}")
        return {"file": filename, "rows": 0, "tickers": 0, "failed": failed}

    final_df = pd.concat(all_frames, ignore_index=True)
    final_df = final_df.drop_duplicates(subset=["Ticker", "Date"], keep="last")
    final_df = final_df.sort_values(["Ticker", "Date"])
    final_df.to_csv(DATA_DIR / filename, index=False)

    latest_by_ticker = final_df.groupby("Ticker")["Date"].max()
    latest = latest_by_ticker.max()
    updated = int((latest_by_ticker == latest).sum())
    print(f"Saved {len(final_df):,} rows for {len(latest_by_ticker):,} tickers; {updated:,} at latest {latest}")
    if failed:
        print(f"Failed/no data: {', '.join(failed)}")
    return {
        "file": filename,
        "rows": len(final_df),
        "tickers": len(latest_by_ticker),
        "latest": str(latest),
        "updated": updated,
        "failed": failed,
    }


def refresh_single_file(filename: str, ticker: str, interval: str, period: str) -> dict:
    print(f"\n=== Refreshing {filename} ({ticker}, {interval}, {period}) ===")
    try:
        frame = download_batch([ticker], interval, period).get(ticker, pd.DataFrame())
    except Exception as exc:
        print(f"Failed {filename}: {exc}")
        return {"file": filename, "rows": 0, "failed": [ticker]}

    if frame.empty:
        print(f"No data downloaded for {filename}")
        return {"file": filename, "rows": 0, "failed": [ticker]}

    out = frame.drop(columns=["Ticker"], errors="ignore")
    out = out.drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
    out.to_csv(DATA_DIR / filename, index=False)
    print(f"Saved {len(out):,} rows; latest {out['Date'].max()}")
    return {"file": filename, "rows": len(out), "latest": str(out["Date"].max()), "failed": []}


def main() -> None:
    tickers = load_ticker_universe()
    print(f"Ticker universe: {len(tickers):,}")
    summaries = []

    for filename, interval, period in TICKER_FILES:
        summaries.append(refresh_ticker_file(filename, interval, period, tickers))

    for filename, ticker, interval, period in SINGLE_FILES:
        summaries.append(refresh_single_file(filename, ticker, interval, period))

    print("\n=== Summary ===")
    for summary in summaries:
        print(summary)


if __name__ == "__main__":
    main()
