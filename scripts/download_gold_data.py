import yfinance as yf
import pandas as pd
import os

DATA_DIR = '/Users/rahulgirishkumar/TRADING/data'
os.makedirs(DATA_DIR, exist_ok=True)

def download_gold():
    ticker = 'GC=F'
    print(f"Downloading Daily data for {ticker}...")
    daily = yf.download(ticker, period='10y', interval='1d')
    daily.to_csv(os.path.join(DATA_DIR, 'gold_daily.csv'))
    
    print(f"Downloading 15m data for {ticker} (60 days)...")
    intraday_15m = yf.download(ticker, period='60d', interval='15m')
    intraday_15m.to_csv(os.path.join(DATA_DIR, 'gold_15m.csv'))
    
    print(f"Downloading 5m data for {ticker} (60 days)...")
    intraday_5m = yf.download(ticker, period='60d', interval='5m')
    intraday_5m.to_csv(os.path.join(DATA_DIR, 'gold_5m.csv'))
    
    print("Data acquisition complete.")

if __name__ == '__main__':
    download_gold()
