import pandas as pd
import yfinance as yf
from tqdm import tqdm
import os
from datetime import datetime

DATA_FILE = '/Users/rahulgirishkumar/TRADING/data/tickers_5m_ohlcv.csv'
STUCK_TICKERS = ['BHF', 'BIIB', 'BILL', 'BIO', 'BK', 'BKE', 'BKNG', 'BKR', 'BLD', 'BLDR', 'BLK', 'BLKB', 'BMY', 'BR', 'BRKR', 'BRO', 'BSX', 'BURL', 'BWXT', 'BX', 'BXP', 'BYD', 'C', 'CACI', 'CAG', 'CAH', 'CAKE', 'CAR', 'CARR', 'CASY', 'CAT', 'CB', 'CBOE', 'CBRE', 'CBT', 'CC', 'CCI', 'CCK', 'CCL', 'CDNS', 'CDW', 'CE', 'CEG', 'CF', 'CFG', 'CFR', 'CG', 'CGNX', 'CHD', 'LOPE', 'LOW', 'LPLA', 'LRCX', 'LSTR', 'LULU', 'LUMN', 'LUV', 'LVS', 'LW', 'LXU', 'LYB', 'LYV', 'M', 'MA', 'MAA', 'MAN', 'MANH', 'MAR', 'MAS', 'MASI', 'MAT', 'MC', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MDU', 'MET', 'META', 'MGM', 'MGPI', 'MHK', 'MIDD', 'MKC', 'MKL', 'MKSI', 'MKTX', 'MLM', 'MMM', 'MNST', 'MO', 'MOD', 'MOH', 'MOS', 'MPC', 'RMBS', 'RMD', 'RNR', 'ROK']

def fix_tickers():
    print(f"Loading {DATA_FILE}...")
    df = pd.read_csv(DATA_FILE)
    df['Date'] = pd.to_datetime(df['Date'], utc=True)
    
    new_data = []
    # Use smaller batches or single to avoid yfinance "delisted" false positives
    for ticker in tqdm(STUCK_TICKERS):
        try:
            # Get data from March 13 to today
            data = yf.download(ticker, start='2026-03-13', interval='5m', progress=False)
            if not data.empty:
                data = data.reset_index()
                if 'Datetime' in data.columns:
                    data = data.rename(columns={'Datetime': 'Date'})
                data['Ticker'] = ticker
                data['Date'] = pd.to_datetime(data['Date'], utc=True)
                new_data.append(data)
        except Exception as e:
            print(f"Failed {ticker}: {e}")

    if new_data:
        new_df = pd.concat(new_data, ignore_index=True)
        # Combine and drop duplicates
        combined = pd.concat([df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=['Ticker', 'Date'], keep='last').sort_values(['Ticker', 'Date'])
        
        combined.to_csv(DATA_FILE, index=False)
        print(f"Successfully fixed {len(STUCK_TICKERS)} tickers in {DATA_FILE}")
    else:
        print("No data recovered.")

if __name__ == '__main__':
    fix_tickers()
