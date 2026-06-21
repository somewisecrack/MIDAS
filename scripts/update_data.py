import pandas as pd
import yfinance as yf
from tqdm import tqdm
import os
import time
from datetime import datetime, timedelta
import requests

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
MAX_RETRIES = 3
BATCH_SIZE = 50

def get_interval_from_filename(filename):
    if '1h' in filename: return '1h'
    if '15m' in filename: return '15m'
    if '30m' in filename: return '30m'
    if '5m' in filename: return '5m'
    return '1d'

def safe_download(tickers, start_date, interval, group_by='ticker'):
    """Download data with retries and a fallback to single-ticker downloads if batch fails."""
    for attempt in range(MAX_RETRIES):
        try:
            data = yf.download(tickers, start=start_date, interval=interval, 
                               group_by=group_by, threads=True, progress=False)
            if not data.empty:
                return data
        except Exception as e:
            print(f"Attempt {attempt+1} failed for batch: {e}")
            time.sleep(1)
    
    # If batch still fails, try one by one for this batch
    if len(tickers) > 1:
        print(f"Falling back to single-ticker downloads for this batch...")
        single_dfs = {}
        for t in tickers:
            try:
                s_data = yf.download(t, start=start_date, interval=interval, progress=False)
                if not s_data.empty:
                    single_dfs[t] = s_data
            except:
                print(f"Final failure for {t}")
        return single_dfs # Return a dict of DataFrames for the one-by-one results
    return None

def update_file(filepath):
    filename = os.path.basename(filepath)
    interval = get_interval_from_filename(filename)
    print(f"\n--- Updating {filename} (Interval: {interval}) ---")
    
    # Load existing data
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return

    if 'Date' not in df.columns:
        # Check if 'Datetime' exists
        if 'Datetime' in df.columns:
            df = df.rename(columns={'Datetime': 'Date'})
        else:
            print(f"Skipping {filename}: No recognizable date column.")
            return

    df['Date'] = pd.to_datetime(df['Date'], utc=True)
    latest_date = df['Date'].max()
    print(f"Latest data in file: {latest_date}")
    
    # Determine tickers
    if 'Ticker' in df.columns:
        tickers = sorted(df['Ticker'].astype(str).unique().tolist())
        is_multiticker = True
    else:
        # For single ticker files like gold_daily.csv, derive ticker from name or assume 'GC=F'
        ticker_name = filename.split('_')[0].upper()
        if ticker_name == 'GOLD': ticker_name = 'GC=F'
        tickers = [ticker_name]
        is_multiticker = False

    all_new_data = []
    for i in tqdm(range(0, len(tickers), BATCH_SIZE)):
        batch = tickers[i:i+BATCH_SIZE]
        start_fetch = latest_date.date()
        
        data = safe_download(batch, start_fetch, interval)
        
        if data is None: continue

        # Unified processing
        if isinstance(data, dict): # results from single-ticker fallback
            for t, t_df in data.items():
                t_df = t_df.reset_index()
                t_df = t_df.rename(columns={'Datetime': 'Date', 'index': 'Date'})
                if is_multiticker: t_df['Ticker'] = t
                all_new_data.append(t_df)
        elif len(batch) == 1:
            t_df = data.reset_index()
            t_df = t_df.rename(columns={'Datetime': 'Date', 'index': 'Date'})
            if is_multiticker: t_df['Ticker'] = batch[0]
            all_new_data.append(t_df)
        else:
            for t in batch:
                if t in data.columns.levels[0]:
                    t_df = data[t].dropna(how='all').reset_index()
                    t_df = t_df.rename(columns={'Datetime': 'Date', 'index': 'Date'})
                    t_df['Ticker'] = t
                    all_new_data.append(t_df)

        time.sleep(0.5)

    if all_new_data:
        new_df = pd.concat(all_new_data, ignore_index=True)
        new_df['Date'] = pd.to_datetime(new_df['Date'], utc=True)
        
        # Merge
        final_df = pd.concat([df, new_df], ignore_index=True)
        sort_cols = ['Ticker', 'Date'] if 'Ticker' in final_df.columns else ['Date']
        final_df = final_df.drop_duplicates(subset=sort_cols, keep='last').sort_values(sort_cols)
        
        final_df.to_csv(filepath, index=False)
        print(f"Updated {filename}: Success.")
    else:
        print(f"No new data found for {filename}.")

def main():
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory not found at {DATA_DIR}")
        return

    # 1. Update Price Data (OHLCV)
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv') and 'fundamental' not in f.lower()]
    for filename in files:
        update_file(os.path.join(DATA_DIR, filename))
    
    # 2. Update Fundamentals
    try:
        from download_fundamentals import update_fundamentals
        print("\n--- Starting Fundamental Updates ---")
        update_fundamentals()
    except Exception as e:
        print(f"Fundamental update skipped/failed: {e}")

if __name__ == "__main__":
    main()
