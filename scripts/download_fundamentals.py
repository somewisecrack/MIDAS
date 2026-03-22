import pandas as pd
import yfinance as yf
from tqdm import tqdm
import os
import concurrent.futures
from datetime import datetime

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
TICKERS_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')
FUNDAMENTALS_FILE = os.path.join(DATA_DIR, 'tickers_fundamentals.csv')

def fetch_ticker_data(ticker):
    """Fetch fundamental data for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        # O'Neil CAN SLIM Fields
        data = {
            'Ticker': ticker,
            'UpdateDate': datetime.now().strftime('%Y-%m-%d'),
            'QuarterlyEarningsGrowth': info.get('earningsQuarterlyGrowth'), # C
            'AnnualEarningsGrowth': info.get('earningsGrowth'), # A
            'TrailingEPS': info.get('trailingEps'),
            'ForwardEPS': info.get('forwardEps'),
            'SharesOutstanding': info.get('sharesOutstanding'), # S
            'FloatShares': info.get('floatShares'), # S
            'InstitutionalOwnership': info.get('heldPercentInstitutions'), # I
            'FiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'), # N Proxy
            'PriceToEarnings': info.get('trailingPE'),
            'MarketCap': info.get('marketCap')
        }
        return data
    except Exception as e:
        # print(f"Error fetching {ticker}: {e}")
        return None

def update_fundamentals():
    print(f"Loading tickers from {TICKERS_FILE}...")
    df_ohlcv = pd.read_csv(TICKERS_FILE)
    tickers = sorted(df_ohlcv['Ticker'].unique().tolist())
    
    print(f"Fetching fundamentals for {len(tickers)} tickers using threading...")
    all_data = []
    
    # Use ThreadPoolExecutor to speed up Info fetching (I/O bound)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_ticker_data, ticker): ticker for ticker in tickers}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(tickers)):
            res = future.result()
            if res:
                all_data.append(res)

    if not all_data:
        print("No fundamental data fetched.")
        return

    new_df = pd.DataFrame(all_data)
    
    # Merge with existing file if it exists
    if os.path.exists(FUNDAMENTALS_FILE):
        old_df = pd.read_csv(FUNDAMENTALS_FILE)
        # We keep only the most recent update per ticker for analysis
        final_df = pd.concat([old_df, new_df], ignore_index=True)
        # Drop duplicates based on Ticker, keeping the latest UpdateDate
        final_df = final_df.sort_values('UpdateDate').drop_duplicates(subset=['Ticker'], keep='last')
    else:
        final_df = new_df

    final_df.to_csv(FUNDAMENTALS_FILE, index=False)
    print(f"Fundamentals updated and saved to {FUNDAMENTALS_FILE} ({len(final_df)} stocks).")

if __name__ == "__main__":
    update_fundamentals()
