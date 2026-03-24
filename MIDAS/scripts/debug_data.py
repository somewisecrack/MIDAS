import pandas as pd
import numpy as np
import os

DAILY_FILE = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'

def debug():
    print("Reading data...")
    df = pd.read_csv(DAILY_FILE)
    print(f"Raw rows: {len(df)}")
    
    # Try parsing manually
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date', 'Close'])
    print(f"Valid dates: {len(df)}")
    print(f"Min Date: {df['Date'].min()}")
    print(f"Max Date: {df['Date'].max()}")
    
    # Group by Date and Ticker to ensure uniqueness
    print("Grouping...")
    df = df.groupby(['Date', 'Ticker'], as_index=False)['Close'].last()
    print(f"Rows after group: {len(df)}")
    
    print("Pivoting...")
    prices = df.pivot(index='Date', columns='Ticker', values='Close').sort_index()
    print(f"Pivot shape: {prices.shape}")
    print(f"Pivot Index Range: {prices.index.min()} to {prices.index.max()}")
    print(f"Is index unique? {prices.index.is_unique}")
    
    # Check for duplicates manually
    if not prices.index.is_unique:
        print("DUPLICATE DATES FOUND IN INDEX:")
        print(prices.index[prices.index.duplicated()].unique())

if __name__ == "__main__":
    debug()
