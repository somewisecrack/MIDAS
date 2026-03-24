import pandas as pd
import numpy as np
from tqdm import tqdm
import os

# --- Configuration ---
DATA_FILE = '/Users/rahulgirishkumar/TRADING/tickers_ohlcv.csv'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/backtests'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Strategy Parameters
MIN_MOVE_PCT = 0.30          # 30% minimum move in 1-3 months
MOVE_LOOKBACK = 60           # ~3 months
CONSOLIDATION_MIN_DAYS = 10  # 2 weeks (approx)
CONSOLIDATION_MAX_DAYS = 40  # 2 months (approx)
ADR_PERIOD = 20              # 20-day Average Daily Range
MA_FAST = 10
MA_SLOW = 20

def calculate_adr(df, period=20):
    """Calculate Average Daily Range (as percentage)."""
    high_low_pct = (df['High'] - df['Low']) / df['Low']
    return high_low_pct.rolling(window=period).mean()

def backtest_strategy_one(df, ticker):
    """
    Qullamaggie Breakout (Option A - Daily Open entry).
    """
    if len(df) < MOVE_LOOKBACK + MA_SLOW:
        return []

    # Calculate Indicators
    df = df.copy()
    df['SMA10'] = df['Close'].rolling(window=MA_FAST).mean()
    df['SMA20'] = df['Close'].rolling(window=MA_SLOW).mean()
    df['ADR'] = calculate_adr(df, ADR_PERIOD)
    
    # Calculate Max Move in past 3 months
    df['Max_60_High'] = df['High'].rolling(window=MOVE_LOOKBACK).max()
    df['Min_60_Low'] = df['Low'].rolling(window=MOVE_LOOKBACK).min()
    df['Move_Pct'] = (df['Max_60_High'] - df['Min_60_Low']) / df['Min_60_Low']

    trades = []
    in_position = False
    entry_price = 0
    stop_loss = 0
    entry_date = None
    half_sold = False
    days_held = 0

    # Iteration
    for i in range(MOVE_LOOKBACK + MA_SLOW, len(df)):
        row = df.iloc[i]
        
        if not in_position:
            # 1. Big Move Filter
            if row['Move_Pct'] < MIN_MOVE_PCT:
                continue
            
            # 2. Consolidation Check
            recent_high = df.iloc[i-20:i]['High'].max()
            if row['Close'] < recent_high * 0.90:
                continue
            
            # Surfing MAs
            if row['Close'] < row['SMA10'] or row['Close'] < row['SMA20']:
                continue

            # 3. Breakout Entry (Option A: Open > consolidation high)
            consol_high = df.iloc[i-10:i]['High'].max()
            if row['Open'] > consol_high:
                entry_date = row['Date']
                entry_price = row['Open']
                # Stop = Low of Day (row['Low']) or max ADR
                stop_loss = row['Low']
                adr_val = row['ADR'] * entry_price
                if (entry_price - stop_loss) > adr_val:
                    stop_loss = entry_price - adr_val
                
                in_position = True
                half_sold = False
                days_held = 0
                
        else:
            days_held += 1
            
            # Exit Logic
            if not half_sold and days_held >= 4:
                if row['Close'] > entry_price:
                    half_sold = True
                    stop_loss = entry_price
            
            if row['Low'] < stop_loss:
                pnl = (stop_loss - entry_price) / entry_price
                trades.append({
                    'Ticker': ticker,
                    'EntryDate': entry_date,
                    'ExitDate': row['Date'],
                    'EntryPrice': entry_price,
                    'ExitPrice': stop_loss,
                    'PnL_Pct': pnl,
                    'ExitReason': 'Stopped Out'
                })
                in_position = False
                continue

            if half_sold and row['Close'] < row['SMA10']:
                pnl = (row['Close'] - entry_price) / entry_price
                trades.append({
                    'Ticker': ticker,
                    'EntryDate': entry_date,
                    'ExitDate': row['Date'],
                    'EntryPrice': entry_price,
                    'ExitPrice': row['Close'],
                    'PnL_Pct': pnl,
                    'ExitReason': 'MA Trail'
                })
                in_position = False

    return trades

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: Data file not found at {DATA_FILE}")
        return

    print("Loading data...")
    df_all = pd.read_csv(DATA_FILE)
    tickers = df_all['Ticker'].unique()
    
    all_trades = []
    
    print(f"Backtesting {len(tickers)} tickers...")
    for ticker in tqdm(tickers):
        df_ticker = df_all[df_all['Ticker'] == ticker].sort_values('Date').reset_index(drop=True)
        trades = backtest_strategy_one(df_ticker, ticker)
        all_trades.extend(trades)
    
    if all_trades:
        results_df = pd.DataFrame(all_trades)
        output_path = os.path.join(RESULTS_DIR, 'breakout_results.csv')
        results_df.to_csv(output_path, index=False)
        print(f"\nBacktest complete. Found {len(all_trades)} trades.")
        win_rate = len(results_df[results_df['PnL_Pct'] > 0]) / len(results_df)
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Avg PnL: {results_df['PnL_Pct'].mean():.2%}")
    else:
        print("\nNo trades found.")

if __name__ == "__main__":
    main()
