import pandas as pd
import numpy as np
from tqdm import tqdm
import os

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
SCRIPTS_DIR = '/Users/rahulgirishkumar/TRADING/scripts/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/results/boucher_runaway'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Files
DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')

# Boucher Rules
RS_WINDOW = 252 # 12 months
RS_THRESHOLD = 80 # Top 20%
MOMENTUM_PERIOD = 40 # ~2 months
MOMENTUM_THRESHOLD = 0.30 # 30%+ Move
FLAG_PERIOD = 20 # 4 weeks
MAX_FLAG_DEPTH = 0.25 # < 25% Correction
STOP_LOSS_MAX = 0.07 # 7% Hard Stop

def calculate_rs_rating(df_daily):
    """Calculate Relative Strength Rating for all tickers."""
    print("Calculating RS Ratings...")
    tickers = df_daily['Ticker'].unique()
    rs_data = []

    for ticker in tickers:
        ticker_df = df_daily[df_daily['Ticker'] == ticker].sort_values('Date')
        if len(ticker_df) < RS_WINDOW:
            continue
        
        p_current = ticker_df['Close'].iloc[-1]
        p_past = ticker_df['Close'].iloc[-RS_WINDOW]
        perf = (p_current / p_past) - 1
        rs_data.append({'Ticker': ticker, 'Perf': perf})

    rs_df = pd.DataFrame(rs_data)
    if not rs_df.empty:
        rs_df['RSRank'] = rs_df['Perf'].rank(pct=True) * 100
    return rs_df

def run_boucher_backtest():
    print(f"Loading daily data from {DAILY_FILE}...")
    df = pd.read_csv(DAILY_FILE)
    df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
    
    rs_lookup = calculate_rs_rating(df)
    if rs_lookup.empty:
        print("No tickers with enough history for RS calculation.")
        return

    all_trades = []
    tickers = rs_lookup[rs_lookup['RSRank'] >= RS_THRESHOLD]['Ticker'].unique()

    for ticker in tqdm(tickers, desc="Scanning Runaway Momentum Flags"):
        res = df[df['Ticker'] == ticker].sort_values('Date').copy()
        if len(res) < RS_WINDOW + MOMENTUM_PERIOD:
            continue
            
        # Indicators
        res['SMA10'] = res['Close'].rolling(10).mean()
        res['SMA20'] = res['Close'].rolling(20).mean()
        
        # Performance over last 40 days
        res['Perf40D'] = res['Close'].pct_change(MOMENTUM_PERIOD)
        
        # Identify Runaway Flags
        for i in range(RS_WINDOW, len(res)):
            row = res.iloc[i]
            
            # 1. Momentum Check (30% in 40 days)
            if row['Perf40D'] < MOMENTUM_THRESHOLD:
                continue
                
            # 2. Flag Check (Tight consolidation for ~21 bars)
            flag_rows = res.iloc[i-FLAG_PERIOD:i]
            if len(flag_rows) < FLAG_PERIOD: continue
            
            flag_high = flag_rows['High'].max()
            flag_low = flag_rows['Low'].min()
            flag_depth = (flag_high / flag_low) - 1
            
            if flag_depth > MAX_FLAG_DEPTH:
                continue
                
            # 3. Entry Logic (Thrust/Gap/Lap)
            # Thrust: Close > Flag High
            # Gap/Lap: Open > Previous Close or Open > Flag High (Approximated as High of consolidation)
            is_breakout = (row['Close'] > flag_high) or (row['Open'] > flag_high)
            
            if is_breakout:
                entry_price = row['Open'] if row['Open'] > flag_high else row['Close']
                
                # Stop: 7% or Flag Low
                stop_price = max(entry_price * (1 - STOP_LOSS_MAX), flag_low)
                
                # Trade Management
                future_data = res.iloc[i+1:]
                for f_idx, f_row in future_data.iterrows():
                    # Stop out
                    if f_row['Low'] <= stop_price:
                        all_trades.append({
                            'Ticker': ticker, 'Date': row['Date'], 'Entry': entry_price, 
                            'Exit': stop_price, 'PnL': (stop_price / entry_price) - 1, 'Type': 'Stop'
                        })
                        break
                    
                    # Exit: 40% correction from peak (Boucher Rule) or SMA10/20 break
                    # For simplicity, we'll use SMA10 break as the primary trailing stop
                    if f_row['Close'] < f_row['SMA10']:
                        all_trades.append({
                            'Ticker': ticker, 'Date': row['Date'], 'Entry': entry_price, 
                            'Exit': f_row['Close'], 'PnL': (f_row['Close'] / entry_price) - 1, 'Type': 'SMA10_Exit'
                        })
                        break

    if not all_trades:
        print("No Runaway Momentum trades found.")
        return

    trades_df = pd.DataFrame(all_trades).drop_duplicates(subset=['Ticker', 'Date'])
    trades_df.to_csv(os.path.join(RESULTS_DIR, 'boucher_trades.csv'), index=False)
    
    # Classification by Price
    def classify_price(price):
        if price < 5: return 'Penny (<$5)'
        if price < 20: return 'Low-Price ($5-$20)'
        if price < 100: return 'Mid-Price ($20-$100)'
        return 'High-Price (>$100)'
    
    trades_df['PriceCategory'] = trades_df['Entry'].apply(classify_price)
    
    summary = trades_df.groupby('PriceCategory').agg(
        Count=('PnL', 'count'),
        WinRate=('PnL', lambda x: (x > 0).mean()),
        AvgPnL=('PnL', 'mean'),
        MaxGain=('PnL', 'max')
    ).reset_index()

    print("\n--- Strategy #5: Boucher Runaway Momentum Summary ---")
    print(summary.to_string(index=False))
    summary.to_csv(os.path.join(RESULTS_DIR, 'boucher_summary.csv'), index=False)

if __name__ == "__main__":
    run_boucher_backtest()
