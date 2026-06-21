import pandas as pd
import yfinance as yf
from tqdm import tqdm
import os
import time

# --- Configuration ---
DAILY_DATA_FILE = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
BASE_DIR = '/Users/rahulgirishkumar/TRADING/data/'
CONFIGS = [
    {'interval': '15m', 'period': '60d', 'filename': 'tickers_15m_ohlcv.csv'},
    {'interval': '5m', 'period': '60d', 'filename': 'tickers_5m_ohlcv.csv'}
]

def download_data(tickers, interval, period, output_file):
    print(f"\n--- Downloading {interval} data (Period: {period}) ---")
    all_data = []
    batch_size = 50
    
    for i in tqdm(range(0, len(tickers), batch_size)):
        batch = tickers[i:i+batch_size]
        try:
            data = yf.download(batch, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
            
            for ticker in batch:
                if ticker in data.columns.levels[0]:
                    ticker_df = data[ticker].copy()
                    ticker_df = ticker_df.dropna(how='all')
                    if not ticker_df.empty:
                        ticker_df['Ticker'] = ticker
                        ticker_df = ticker_df.reset_index()
                        all_data.append(ticker_df)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Error downloading {interval} batch {batch}: {e}")

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        if 'Datetime' in final_df.columns:
            final_df = final_df.rename(columns={'Datetime': 'Date'})
            
        path = os.path.join(BASE_DIR, output_file)
        final_df.to_csv(path, index=False)
        print(f"Saved {len(final_df)} rows to {path}")
    else:
        print(f"No data downloaded for {interval}")

def main():
    if not os.path.exists(DAILY_DATA_FILE):
        print(f"Error: Daily data file not found at {DAILY_DATA_FILE}")
        return

    print("Loading tickers from daily data...")
    df_daily = pd.read_csv(DAILY_DATA_FILE)
    tickers = sorted(df_daily['Ticker'].unique().tolist())
    print(f"Found {len(tickers)} tickers.")

    for config in CONFIGS:
        download_data(tickers, config['interval'], config['period'], config['filename'])

if __name__ == "__main__":
    main()
