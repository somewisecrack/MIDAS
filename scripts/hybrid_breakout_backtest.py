import pandas as pd
import numpy as np
from tqdm import tqdm
import os
from datetime import datetime, timedelta

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/backtests_hybrid'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Files
DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')
H1_FILE = os.path.join(DATA_DIR, 'tickers_1h_ohlcv.csv')
M5_FILE = os.path.join(DATA_DIR, 'tickers_5m_ohlcv.csv')

# Qullamaggie Rules
WINDOW_3M = 63  # ~3 months
BIG_MOVE_THRESHOLD = 0.30
SMA_10 = 10
SMA_20 = 20

def run_hybrid_backtest():
    print("Loading daily data...")
    df_daily = pd.read_csv(DAILY_FILE)
    df_daily['Date'] = pd.to_datetime(df_daily['Date']).dt.tz_localize(None)
    
    print("Loading 1h data (~1.4M rows)...")
    df_h1 = pd.read_csv(H1_FILE)
    df_h1['Date'] = pd.to_datetime(df_h1['Date']).dt.tz_localize(None)
    
    print("Loading 5m data (~3.6M rows)...")
    # Low memory optimization or Dtype handling
    df_m5 = pd.read_csv(M5_FILE, low_memory=False)
    df_m5['Date'] = pd.to_datetime(df_m5['Date']).dt.tz_localize(None)
    
    tickers = df_daily['Ticker'].unique()
    all_trades = []

    # Calculate timestamps for tiering
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_60d = today - timedelta(days=65)
    cutoff_1y = today - timedelta(days=366)

    for ticker in tqdm(tickers, desc="Processing Tickers"):
        res_d = df_daily[df_daily['Ticker'] == ticker].sort_values('Date').copy()
        res_h1 = df_h1[df_h1['Ticker'] == ticker].sort_values('Date').copy()
        res_m5 = df_m5[df_m5['Ticker'] == ticker].sort_values('Date').copy()
        
        if len(res_d) < WINDOW_3M:
            continue
            
        # Indicators
        res_d['SMA10'] = res_d['Close'].rolling(window=SMA_10).mean()
        res_d['SMA20'] = res_d['Close'].rolling(window=SMA_20).mean()
        res_d['Move_3M'] = res_d['Close'].pct_change(periods=WINDOW_3M)
        
        # Setup Mask (shifted by 1 to act as "Setup complete yesterday, look for breakout today")
        setup_mask = (
            (res_d['Move_3M'].shift(1) > BIG_MOVE_THRESHOLD) & 
            (res_d['Close'].shift(1) > res_d['SMA10'].shift(1)) &
            (res_d['Close'].shift(1) > res_d['SMA20'].shift(1))
        )
        
        candidates = res_d[setup_mask]
        
        for idx, row in candidates.iterrows():
            trade_timestamp = row['Date']
            trade_date = trade_timestamp.date()
            
            # --- Tiered Execution Selection ---
            entry_price = None
            exit_price_lod = row['Low'] # Default LOD from daily
            entry_tier = ""
            
            # Tier 1: 5m Data (Last 60d)
            if trade_timestamp > cutoff_60d and not res_m5.empty:
                day_m5 = res_m5[res_m5['Date'].dt.date == trade_date]
                if not day_m5.empty:
                    orh = day_m5.iloc[0]['High']
                    lod = day_m5['Low'].min()
                    post_orh = day_m5.iloc[1:]
                    entry_pts = post_orh[post_orh['High'] > orh]
                    if not entry_pts.empty:
                        entry_price = orh * 1.001
                        exit_price_lod = lod
                        entry_tier = "5m"
            
            # Tier 2: 1h Data (Last 1y)
            if entry_price is None and trade_timestamp > cutoff_1y and not res_h1.empty:
                day_h1 = res_h1[res_h1['Date'].dt.date == trade_date]
                if not day_h1.empty:
                    orh = day_h1.iloc[0]['High']
                    post_orh = day_h1.iloc[1:]
                    entry_pts = post_orh[post_orh['High'] > orh]
                    if not entry_pts.empty:
                        entry_price = orh * 1.001
                        entry_tier = "1h"
            
            # Tier 3: Daily Data (Old History)
            if entry_price is None and trade_timestamp <= cutoff_1y:
                # Option A Proxy: Entered on Open if gap or near Open
                # For consistency, we'll assume a break of yesterday's high or just entry on Open
                # Kristjan says Option A is "Enter on Open".
                entry_price = row['Open']
                entry_tier = "Daily"

            # --- Trade Follow-through ---
            if entry_price:
                # Check for stop out on same day
                if row['Low'] < exit_price_lod:
                    pnl = (exit_price_lod / entry_price) - 1
                    all_trades.append({
                        'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                        'ExitPrice': exit_price_lod, 'PnL': pnl, 'Type': 'Stop_Same_Day', 'Tier': entry_tier
                    })
                else:
                    # Daily Trail
                    future_d = res_d[res_d['Date'] > trade_timestamp]
                    is_stopped = False
                    for f_idx, f_row in future_d.iterrows():
                        # Condition: Close below SMA10
                        if f_row['Close'] < f_row['SMA10']:
                            exit_val = f_row['Close']
                            pnl = (exit_val / entry_price) - 1
                            all_trades.append({
                                'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                                'ExitPrice': exit_val, 'PnL': pnl, 'Type': 'SMA10_Trail', 'Tier': entry_tier
                            })
                            is_stopped = True
                            break
                    if not is_stopped and not future_d.empty:
                        last_row = future_d.iloc[-1]
                        pnl = (last_row['Close'] / entry_price) - 1
                        all_trades.append({
                            'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                            'ExitPrice': last_row['Close'], 'PnL': pnl, 'Type': 'End_Of_Data', 'Tier': entry_tier
                        })

    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df.to_csv(os.path.join(RESULTS_DIR, 'breakout_hybrid_results.csv'), index=False)
        
        print("\n--- Hybrid Backtest Summary (Multi-Year) ---")
        print(f"Total Trades: {len(trades_df)}")
        print(f"Win Rate: {(trades_df['PnL'] > 0).mean():.2%}")
        print(f"Avg PnL: {trades_df['PnL'].mean():.2%}")
        print("\n--- Performance by Data Tier ---")
        print(trades_df.groupby('Tier')['PnL'].mean())
        print("\nTrade Counts by Tier:")
        print(trades_df['Tier'].value_counts())
    else:
        print("No trades found.")

if __name__ == "__main__":
    run_hybrid_backtest()
