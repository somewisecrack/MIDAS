import pandas as pd
import numpy as np
from tqdm import tqdm
import os
from datetime import datetime, timedelta

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/backtests_strict'
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
ADR_PERIOD = 20

def run_strict_backtest():
    print("Loading daily data...")
    df_daily = pd.read_csv(DAILY_FILE)
    df_daily['Date'] = pd.to_datetime(df_daily['Date']).dt.tz_localize(None)
    
    print("Loading 1h data...")
    df_h1 = pd.read_csv(H1_FILE)
    df_h1['Date'] = pd.to_datetime(df_h1['Date']).dt.tz_localize(None)
    
    print("Loading 5m data...")
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
        
        # Calculate ADR (20-day average daily range as percentage)
        res_d['DayRangePct'] = (res_d['High'] - res_d['Low']) / res_d['Low']
        res_d['ADR20'] = res_d['DayRangePct'].rolling(window=ADR_PERIOD).mean()
        
        # Consolidation check (Simplified: Range of last 5 days < ADR20)
        res_d['Max5'] = res_d['High'].rolling(5).max()
        res_d['Min5'] = res_d['Low'].rolling(5).min()
        res_d['Consolidation'] = (res_d['Max5'] - res_d['Min5']) / res_d['Min5'] < (res_d['ADR20'] * 1.5)
        
        setup_mask = (
            (res_d['Move_3M'].shift(1) > BIG_MOVE_THRESHOLD) & 
            (res_d['Close'].shift(1) > res_d['SMA10'].shift(1)) &
            (res_d['Close'].shift(1) > res_d['SMA20'].shift(1)) &
            (res_d['Consolidation'].shift(1))
        )
        
        candidates = res_d[setup_mask]
        
        for idx, row in candidates.iterrows():
            trade_timestamp = row['Date']
            trade_date = trade_timestamp.date()
            adr_val = row['ADR20']
            
            # --- Tiered Execution Selection ---
            entry_price = None
            exit_price_lod = row['Low'] 
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
            
            # Tier 3: Daily Data fallback
            if entry_price is None and trade_timestamp <= cutoff_1y:
                entry_price = row['Open']
                entry_tier = "Daily"

            # --- Trade Follow-through (Strict Rules) ---
            if entry_price:
                # Rule: ADR Filter (Risk must be <= ADR)
                risk_pct = (entry_price - exit_price_lod) / entry_price
                if risk_pct > adr_val and risk_pct > 0.10: # Allow up to 10% risk or ADR
                    continue

                # 1. Check for LOD stop out on entry day
                if row['Low'] < exit_price_lod:
                    all_trades.append({
                        'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                        'ExitPrice': exit_price_lod, 'PnL': (exit_price_lod / entry_price) - 1,
                        'Type': 'Stop_LOD_EntryDay', 'Tier': entry_tier
                    })
                    continue

                # 2. Daily Management
                future_d = res_d[res_d['Date'] > trade_timestamp].sort_values('Date')
                if future_d.empty: 
                    continue

                is_active = True
                has_sold_half = False
                current_stop = exit_price_lod
                days_in_trade = 0
                
                for f_idx, f_row in future_d.iterrows():
                    days_in_trade += 1
                    
                    # Check Stop Loss first
                    if f_row['Low'] < current_stop:
                        exit_val = current_stop
                        pnl = (exit_val / entry_price) - 1
                        all_trades.append({
                            'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                            'ExitPrice': exit_val, 'PnL': pnl, 'Type': 'Stop_Hit', 'Tier': entry_tier
                        })
                        is_active = False
                        break
                    
                    # Rule: Sell Half after 3 days
                    if not has_sold_half and days_in_trade >= 3:
                        # Logic: We take a mid-day pnl check or just use close
                        has_sold_half = True
                        # Rule: Move stop to Breakeven
                        current_stop = entry_price 
                        
                    # Rule: Trail with SMA10 if price is above it
                    # But don't trail until at least day 3 or so
                    if days_in_trade >= 3:
                        if f_row['Close'] < f_row['SMA10']:
                            exit_val = f_row['Close']
                            pnl = (exit_val / entry_price) - 1
                            all_trades.append({
                                'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                                'ExitPrice': exit_val, 'PnL': pnl, 'Type': 'SMA10_Trail', 'Tier': entry_tier
                            })
                            is_active = False
                            break
                            
                if is_active:
                    last_row = future_d.iloc[-1]
                    pnl = (last_row['Close'] / entry_price) - 1
                    all_trades.append({
                        'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                        'ExitPrice': last_row['Close'], 'PnL': pnl, 'Type': 'End_Of_History', 'Tier': entry_tier
                    })

    if all_trades:
        trades_df = pd.DataFrame(all_trades)
        trades_df.to_csv(os.path.join(RESULTS_DIR, 'breakout_strict_results.csv'), index=False)
        
        print("\n--- Strict Original Rules Summary ---")
        print(f"Total Trades: {len(trades_df)}")
        print(f"Win Rate: {(trades_df['PnL'] > 0).mean():.2%}")
        print(f"Avg PnL: {trades_df['PnL'].mean():.2%}")
        
        # Analyze winners vs losers
        winners = trades_df[trades_df['PnL'] > 0]
        if not winners.empty:
            print(f"Avg Gain (Winners): {winners['PnL'].mean():.2%}")
            print(f"Max Gain: {winners['PnL'].max():.2%}")
            
    else:
        print("No trades found matching strict criteria.")

if __name__ == "__main__":
    run_strict_backtest()
