import pandas as pd
import numpy as np
from tqdm import tqdm
import os

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
SCRIPTS_DIR = '/Users/rahulgirishkumar/TRADING/scripts/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/results/oneil_technical'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Files
DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')

# O'Neil Rules
RS_WINDOW = 252 # 12 months
RS_THRESHOLD = 80 # Top 20%
STOP_LOSS_PERC = 0.07 # 7% O'Neil Stop
MIN_VOLUME_SURGE = 1.4 # +40% ADV
VOL_AVG_PERIOD = 50
MIN_CONSOLIDATION_WEEKS = 5 # For Flat Base

def calculate_rs_rating(df_daily):
    """Calculate Relative Strength Rating for all tickers."""
    print("Calculating RS Ratings...")
    tickers = df_daily['Ticker'].unique()
    rs_data = []

    # Simple 12-month performance proxy for RS
    for ticker in tickers:
        ticker_df = df_daily[df_daily['Ticker'] == ticker].sort_values('Date')
        if len(ticker_df) < RS_WINDOW:
            continue
        
        # O'Neil RS often weighs recent performance higher (e.g. last 3 months weighted 40%)
        # Here we'll use a standard 12-month performance to rank
        p_current = ticker_df['Close'].iloc[-1]
        p_past = ticker_df['Close'].iloc[-RS_WINDOW]
        perf = (p_current / p_past) - 1
        rs_data.append({'Ticker': ticker, 'Perf': perf})

    rs_df = pd.DataFrame(rs_data)
    rs_df['RSRank'] = rs_df['Perf'].rank(pct=True) * 100
    return rs_df

def run_oneil_backtest():
    print(f"Loading daily data from {DAILY_FILE}...")
    df = pd.read_csv(DAILY_FILE)
    df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
    
    rs_lookup = calculate_rs_rating(df)
    
    all_trades = []
    tickers = rs_lookup[rs_lookup['RSRank'] >= RS_THRESHOLD]['Ticker'].unique()

    for ticker in tqdm(tickers, desc="Scanning O'Neil Bases"):
        res = df[df['Ticker'] == ticker].sort_values('Date').copy()
        if len(res) < VOL_AVG_PERIOD + RS_WINDOW:
            continue
            
        # Indicators
        res['VolAvg50'] = res['Volume'].rolling(VOL_AVG_PERIOD).mean()
        res['High52W'] = res['High'].rolling(252).max()
        res['SMA10'] = res['Close'].rolling(10).mean()
        res['SMA50'] = res['Close'].rolling(50).mean()
        
        # Find Breakouts from Bases
        # Logic for "Flat Base" or "Cup": Tight consolidation near highs
        for i in range(VOL_AVG_PERIOD, len(res)):
            row = res.iloc[i]
            prev_rows = res.iloc[i-25:i] # Look back 5 weeks for Flat Base
            
            # 1. Distance from 52W High (Must be within 15%)
            if row['Close'] < row['High52W'] * 0.85:
                continue
            
            # 2. Consolidation Check (Flat Base Proxy)
            base_high = prev_rows['High'].max()
            base_low = prev_rows['Low'].min()
            base_depth = (base_high / base_low) - 1
            
            # 3. Breakout Signal
            is_breakout = (row['Close'] > base_high) and (row['Volume'] >= row['VolAvg50'] * MIN_VOLUME_SURGE)
            
            if is_breakout and base_depth <= 0.20: # Flat bases/Cups are usually < 20% deep
                entry_price = row['Close']
                stop_loss = entry_price * (1 - STOP_LOSS_PERC)
                
                # Trade Management
                future_data = res.iloc[i+1:]
                for f_idx, f_row in future_data.iterrows():
                    # Stop out
                    if f_row['Low'] <= stop_loss:
                        all_trades.append({
                            'Ticker': ticker, 'Date': row['Date'], 'Entry': entry_price, 
                            'Exit': stop_loss, 'PnL': -STOP_LOSS_PERC, 'Type': 'StopLoss'
                        })
                        break
                    # Take Profit: 20% Gain or SMA50 break (O'Neil position trading)
                    if f_row['Close'] >= entry_price * 1.25: # 25% Profit Target
                        all_trades.append({
                            'Ticker': ticker, 'Date': row['Date'], 'Entry': entry_price, 
                            'Exit': f_row['Close'], 'PnL': (f_row['Close'] / entry_price) - 1, 'Type': 'Target_25%'
                        })
                        break
                    if f_row['Close'] < f_row['SMA50']:
                        all_trades.append({
                            'Ticker': ticker, 'Date': row['Date'], 'Entry': entry_price, 
                            'Exit': f_row['Close'], 'PnL': (f_row['Close'] / entry_price) - 1, 'Type': 'SMA50_Exit'
                        })
                        break
                # Deduplicate entries (avoid multiple signals in same base)
                # Skip forward in loop
                # i += 20 # Not allowed in range loop, but we can track last entry date
                pass

    if not all_trades:
        print("No O'Neil trades found.")
        return

    trades_df = pd.DataFrame(all_trades).drop_duplicates(subset=['Ticker', 'Date'])
    trades_df.to_csv(os.path.join(RESULTS_DIR, 'oneil_trades.csv'), index=False)
    
    # Classification by Price
    def classify_price(price):
        if price < 15: return 'Small-Cap (<$15)' # O'Neil prefers >$15
        if price < 50: return 'Mid-Price ($15-$50)'
        return 'Institutional (>$50)'
    
    trades_df['PriceCategory'] = trades_df['Entry'].apply(classify_price)
    
    summary = trades_df.groupby('PriceCategory').agg(
        Count=('PnL', 'count'),
        WinRate=('PnL', lambda x: (x > 0).mean()),
        AvgPnL=('PnL', 'mean'),
        MaxGain=('PnL', 'max')
    ).reset_index()

    print("\n--- Strategy #4: O'Neil Technical Core Summary ---")
    print(summary.to_string(index=False))
    summary.to_csv(os.path.join(RESULTS_DIR, 'oneil_summary.csv'), index=False)

if __name__ == "__main__":
    run_oneil_backtest()
