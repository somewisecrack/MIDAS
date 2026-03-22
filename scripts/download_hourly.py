import pandas as pd
import yfinance as yf
from tqdm import tqdm
import os
import time

# --- Configuration ---
DAILY_DATA_FILE = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
OUTPUT_FILE = '/Users/rahulgirishkumar/TRADING/data/tickers_1h_ohlcv.csv'
INTERVAL = '1h'
PERIOD = '1y'

def main():
    if not os.path.exists(DAILY_DATA_FILE):
        print(f"Error: Daily data file not found at {DAILY_DATA_FILE}")
        return

    print("Loading tickers from daily data...")
    df_daily = pd.read_csv(DAILY_DATA_FILE)
    tickers = sorted(df_daily['Ticker'].unique().tolist())
    print(f"Found {len(tickers)} tickers.")

    all_data = []
    
    # Download in batches to be efficient and avoid rate limits
    batch_size = 50
    for i in tqdm(range(0, len(tickers), batch_size)):
        batch = tickers[i:i+batch_size]
        try:
            # Download batch
            data = yf.download(batch, period=PERIOD, interval=INTERVAL, group_by='ticker', threads=True, progress=False)
            
            for ticker in batch:
                if ticker in data.columns.levels[0]:
                    ticker_df = data[ticker].copy()
                    ticker_df = ticker_df.dropna(how='all')
                    if not ticker_df.empty:
                        ticker_df['Ticker'] = ticker
                        ticker_df = ticker_df.reset_index()
                        all_data.append(ticker_df)
            
            # Small sleep to be respectful to API
            time.sleep(1)
            
        except Exception as e:
            print(f"Error downloading batch {batch}: {e}")

    if all_data:
        print("\nCombining data...")
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Rename 'Datetime' to 'Date' for consistency if it exists
        if 'Datetime' in final_df.columns:
            final_df = final_df.rename(columns={'Datetime': 'Date'})
            
        print(f"Saving to {OUTPUT_FILE}...")
        final_df.to_csv(OUTPUT_FILE, index=False)
        print(f"Done! Downloaded {len(final_df)} rows.")
    else:
        print("No data downloaded.")

if __name__ == "__main__":
    main()
