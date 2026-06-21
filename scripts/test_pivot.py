import pandas as pd
import os

DAILY_FILE = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'

def test_single():
    df = pd.read_csv(DAILY_FILE)
    df['Date'] = pd.to_datetime(df['Date']).dt.normalize()
    
    # Filter for APL
    df_a = df[df.Ticker == 'AAPL'].copy()
    print(f"AAPL rows: {len(df_a)}")
    print(f"AAPL Date Range: {df_a.Date.min()} to {df_a.Date.max()}")
    print(f"AAPL Unique Dates: {df_a.Date.nunique()}")
    
    # Pivot a subset of 10 tickers
    subset = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX', 'BRK-B', 'JPM']
    df_sub = df[df.Ticker.isin(subset)].copy()
    
    print("\nPivoting subset...")
    prices = df_sub.pivot(index='Date', columns='Ticker', values='Close').sort_index()
    print(f"Subset Pivot Shape: {prices.shape}")
    print(f"Subset Pivot Index Range: {prices.index.min()} to {prices.index.max()}")
    print(f"Is subset index unique? {prices.index.is_unique}")
    
if __name__ == "__main__":
    test_single()
