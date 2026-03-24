import pandas as pd
import numpy as np
from tqdm import tqdm
import os

# --- Configuration ---
DAILY_DATA_FILE = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
INTRA_DATA_FILE = '/Users/rahulgirishkumar/TRADING/data/tickers_5m_ohlcv.csv'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/backtests_refined'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Qullamaggie Rules
WINDOW_3M = 63  # ~3 months of trading days
BIG_MOVE_THRESHOLD = 0.30  # 30% move
CONSOLIDATION_DAYS = 10  # Minimum days to consolidate
SMA_10 = 10
SMA_20 = 20

def run_backtest():
    print("Loading daily data for screening...")
    df_daily = pd.read_csv(DAILY_DATA_FILE)
    df_daily['Date'] = pd.to_datetime(df_daily['Date'])
    
    print("Loading 5m data for precise execution (this may take a moment)...")
    df_5m = pd.read_csv(INTRA_DATA_FILE)
    df_5m['Date'] = pd.to_datetime(df_5m['Date'])
    
    tickers = df_daily['Ticker'].unique()
    all_trades = []

    for ticker in tqdm(tickers, desc="Processing Tickers"):
        res_d = df_daily[df_daily['Ticker'] == ticker].sort_values('Date').copy()
        res_5 = df_5m[df_5m['Ticker'] == ticker].sort_values('Date').copy()
        
        if len(res_d) < WINDOW_3M or res_5.empty:
            continue
            
        # 1. Indicators
        res_d['SMA10'] = res_d['Close'].rolling(window=SMA_10).mean()
        res_d['SMA20'] = res_d['Close'].rolling(window=SMA_20).mean()
        
        # Big move (max price in last 3 months vs price at start of that window)
        res_d['Move_3M'] = res_d['Close'].pct_change(periods=WINDOW_3M)
        
        # 2. Setup Detection
        # Narrowing down: Look for days where we have a setup + potential breakout
        # Strategy: 
        # - Move > 30% in last 3 months
        # - Close > SMA10 and SMA20
        # - Range tightening (Consolidation) - simple proxy: price near SMA10
        setup_mask = (
            (res_d['Move_3M'].shift(1) > BIG_MOVE_THRESHOLD) & 
            (res_d['Close'].shift(1) > res_d['SMA10'].shift(1)) &
            (res_d['Close'].shift(1) > res_d['SMA20'].shift(1))
        )
        
        candidates = res_d[setup_mask]
        
        for idx, row in candidates.iterrows():
            trade_date = row['Date'].date()
            
            # Filter 5m data for this specific day
            day_5m = res_5[res_5['Date'].dt.date == trade_date].copy()
            if day_5m.empty:
                continue
                
            # --- Opening Range High (ORH) Entry ---
            # Rule: High of the first 5-min candle
            first_candle = day_5m.iloc[0]
            orh = first_candle['High']
            lod = day_5m['Low'].min() # Low of the Day stop
            
            # Entry logic: Did price cross ORH after the first candle?
            potential_entries = day_5m.iloc[1:]
            entry_triggered = potential_entries[potential_entries['High'] > orh]
            
            if not entry_triggered.empty:
                entry_price = orh * 1.001 # Slippage simulation
                entry_time = entry_triggered.iloc[0]['Date']
                
                # Check for stop out on same day
                post_entry = day_5m[day_5m['Date'] > entry_time]
                stopped_day = post_entry[post_entry['Low'] < lod]
                
                if not stopped_day.empty:
                    pnl = (lod / entry_price) - 1
                    all_trades.append({
                        'Ticker': ticker,
                        'EntryDate': entry_time,
                        'ExitDate': stopped_day.iloc[0]['Date'],
                        'EntryPrice': entry_price,
                        'ExitPrice': lod,
                        'PnL': pnl,
                        'Type': 'Stop_Same_Day'
                    })
                else:
                    # Carry trade forward in daily data
                    future_d = res_d[res_d['Date'] > pd.Timestamp(trade_date)]
                    if future_d.empty: continue
                    
                    sell_half_idx = min(len(future_d)-1, 3) # Sell 1/2 after 3 days
                    is_stopped = False
                    
                    # Trail with SMA10
                    for f_idx, f_row in future_d.iterrows():
                        if f_row['Low'] < f_row['SMA10']:
                            exit_price = min(f_row['Open'], f_row['SMA10'] * 0.999)
                            pnl = (exit_price / entry_price) - 1
                            all_trades.append({
                                'Ticker': ticker,
                                'EntryDate': entry_time,
                                'ExitDate': f_row['Date'],
                                'EntryPrice': entry_price,
                                'ExitPrice': exit_price,
                                'PnL': pnl,
                                'Type': 'SMA10_Exit'
                            })
                            is_stopped = True
                            break
                    
                    if not is_stopped:
                        last_row = future_d.iloc[-1]
                        pnl = (last_row['Close'] / entry_price) - 1
                        all_trades.append({
                            'Ticker': ticker,
                            'EntryDate': entry_time,
                            'ExitDate': last_row['Date'],
                            'EntryPrice': entry_price,
                            'ExitPrice': last_row['Close'],
                            'PnL': pnl,
                            'Type': 'End_Of_Data'
                        })

    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df.to_csv(os.path.join(RESULTS_DIR, 'breakout_refined_trades.csv'), index=False)
        
        print("\n--- Refined Backtest Summary ---")
        print(f"Total Trades: {len(trades_df)}")
        print(f"Win Rate: {(trades_df['PnL'] > 0).mean():.2%}")
        print(f"Average PnL: {trades_df['PnL'].mean():.2%}")
        print(f"Max drawdown (proxy): {trades_df['PnL'].min():.2%}")
        print(f"Results saved to {RESULTS_DIR}")
    else:
        print("No trades found matching setup criteria.")

if __name__ == "__main__":
    run_backtest()
