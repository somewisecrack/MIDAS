import pandas as pd
import numpy as np
from tqdm import tqdm
import os
from datetime import datetime

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/backtests_snapback'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Files
DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')
H1_FILE = os.path.join(DATA_DIR, 'tickers_1h_ohlcv.csv')
M15_FILE = os.path.join(DATA_DIR, 'tickers_15m_ohlcv.csv')
M5_FILE = os.path.join(DATA_DIR, 'tickers_5m_ohlcv.csv')

# Parabolic Short Rules
MIN_EXT_PERC = 0.50  # 50%+ in 10 days
MIN_DAYS = 10
SMA_DIST_PERC = 0.20 # 20% above SMA10
SMA_PERIOD = 10
SLIPPAGE = 0.002

def run_snapback_backtest():
    print("Loading daily data...")
    df_daily = pd.read_csv(DAILY_FILE)
    df_daily['Date'] = pd.to_datetime(df_daily['Date']).dt.tz_localize(None)
    
    # Intraday loaders (last 60d for 5m/15m, 1y for 1h)
    intra_files = {
        '1h': H1_FILE,
        '15m': M15_FILE,
        '5m': M5_FILE
    }
    
    intra_dfs = {}
    for tf, path in intra_files.items():
        if os.path.exists(path):
            print(f"Loading {tf} data...")
            df = pd.read_csv(path, low_memory=False)
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
            intra_dfs[tf] = df

    tickers = df_daily['Ticker'].unique()
    all_trades = []

    for ticker in tqdm(tickers, desc="Scanning for Parabolic Shorts"):
        res_d = df_daily[df_daily['Ticker'] == ticker].sort_values('Date').copy()
        if len(res_d) < 30: continue
        
        # Extension indicators
        res_d['SMA10'] = res_d['Close'].rolling(SMA_PERIOD).mean()
        res_d['SMA20'] = res_d['Close'].rolling(20).mean()
        res_d['P10D_Back'] = res_d['Close'].shift(10)
        res_d['Perf10D'] = (res_d['Close'] / res_d['P10D_Back']) - 1
        res_d['DistSMA10'] = (res_d['Close'] / res_d['SMA10']) - 1
        
        # Setup mask: Vertical extension
        setup_mask = (res_d['Perf10D'] >= MIN_EXT_PERC) & (res_d['DistSMA10'] >= SMA_DIST_PERC)
        candidates = res_d[setup_mask]
        
        for idx, row in candidates.iterrows():
            trade_timestamp = row['Date']
            trade_date = trade_timestamp.date()
            
            # --- 1. Multi-Timeframe Check (Intraday) ---
            for tf, df_intra in intra_dfs.items():
                res_intra = df_intra[(df_intra['Ticker'] == ticker) & (df_intra['Date'].dt.date == trade_date)].sort_values('Date')
                if res_intra.empty: continue
                
                # Opening Range Low (ORL) logic: 1st candle
                orl = res_intra.iloc[0]['Low']
                post_orl = res_intra.iloc[1:]
                entry_pts = post_orl[post_orl['Low'] < orl]
                
                if not entry_pts.empty:
                    entry_price = orl * (1 - SLIPPAGE)
                    hod = res_intra['High'].max() # High of Day stop
                    
                    # Track trade until SMA10 touch (Daily)
                    future_d = res_d[res_d['Date'] >= trade_timestamp].sort_values('Date')
                    for f_idx, f_row in future_d.iterrows():
                        # Stop out: HOD break (approximated by daily High)
                        if f_row['High'] > hod:
                            all_trades.append({
                                'Ticker': ticker, 'Date': trade_timestamp, 'TF': tf, 
                                'Entry': entry_price, 'Exit': hod, 'PnL': (entry_price / hod) - 1,
                                'Type': 'StopLoss_HOD'
                            })
                            break
                        # Target: SMA10 touch
                        if f_row['Low'] <= f_row['SMA10']:
                            exit_price = f_row['SMA10']
                            all_trades.append({
                                'Ticker': ticker, 'Date': trade_timestamp, 'TF': tf, 
                                'Entry': entry_price, 'Exit': exit_price, 'PnL': (entry_price / exit_price) - 1,
                                'Type': 'Target_SMA10'
                            })
                            break
            
            # --- 2. Historical Proxy (Daily Entry) ---
            # Entry on break of previous day's Low
            prev_row = res_d.loc[:idx].iloc[-2] if idx > 0 else None
            if prev_row is not None:
                entry_trigger = prev_row['Low']
                if row['Low'] < entry_trigger:
                    entry_price = entry_trigger * (1 - SLIPPAGE)
                    hod = row['High']
                    
                    future_d = res_d[res_d['Date'] >= trade_timestamp].sort_values('Date')
                    for f_idx, f_row in future_d.iterrows():
                        if f_row['High'] > hod:
                            all_trades.append({
                                'Ticker': ticker, 'Date': trade_timestamp, 'TF': 'Daily_Proxy', 
                                'Entry': entry_price, 'Exit': hod, 'PnL': (entry_price / hod) - 1,
                                'Type': 'StopLoss_HOD'
                            })
                            break
                        if f_row['Low'] <= f_row['SMA10']:
                            exit_price = f_row['SMA10']
                            all_trades.append({
                                'Ticker': ticker, 'Date': trade_timestamp, 'TF': 'Daily_Proxy', 
                                'Entry': entry_price, 'Exit': exit_price, 'PnL': (entry_price / exit_price) - 1,
                                'Type': 'Target_SMA10'
                            })
                            break

    # Summary
    if not all_trades:
        print("No snapback trades found.")
        return

    trades_df = pd.DataFrame(all_trades)
    
    # Classification by Price
    def classify_price(price):
        if price < 5: return 'Penny'
        if price < 20: return 'Low'
        if price < 100: return 'Mid'
        return 'High'
    
    trades_df['PriceCategory'] = trades_df['Entry'].apply(classify_price)
    trades_df.to_csv(os.path.join(RESULTS_DIR, 'snapback_all_trades.csv'), index=False)
    
    summary = trades_df.groupby(['TF', 'PriceCategory']).agg(
        Count=('PnL', 'count'),
        WinRate=('PnL', lambda x: (x > 0).mean()),
        AvgPnL=('PnL', 'mean'),
        MaxGain=('PnL', 'max')
    ).reset_index()

    print("\n--- Strategy #3: Parabolic Short (Snapback) Summary ---")
    print(summary.to_string(index=False))
    summary.to_csv(os.path.join(RESULTS_DIR, 'snapback_summary.csv'), index=False)

if __name__ == "__main__":
    run_snapback_backtest()
