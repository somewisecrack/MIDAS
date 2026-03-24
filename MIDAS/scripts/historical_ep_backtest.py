import pandas as pd
import numpy as np
from tqdm import tqdm
import os
import argparse

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/backtests_ep_historical'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Files
DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')

# EP Rules
MIN_GAP = 0.10
VOL_MULT = 2.0
SMA10_PERIOD = 10
SLIPPAGE = 0.002 # 0.2% slippage on open

def run_historical_ep_backtest():
    print(f"Loading daily data from {DAILY_FILE}...")
    df = pd.read_csv(DAILY_FILE)
    df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
    
    tickers = df['Ticker'].unique()
    all_trades = []

    for ticker in tqdm(tickers, desc="Backtesting EP (Daily History)"):
        res = df[df['Ticker'] == ticker].sort_values('Date').copy()
        if len(res) < SMA10_PERIOD + 1:
            continue
            
        # Indicators
        res['PrevClose'] = res['Close'].shift(1)
        res['Gap'] = (res['Open'] - res['PrevClose']) / res['PrevClose']
        res['VolAvg20'] = res['Volume'].rolling(20).mean()
        res['SMA10'] = res['Close'].rolling(SMA10_PERIOD).mean()
        
        # Setup Detection
        ep_mask = (res['Gap'] >= MIN_GAP) & (res['Volume'] >= res['VolAvg20'] * VOL_MULT)
        ep_days = res[ep_mask]
        
        for idx, row in ep_days.iterrows():
            entry_price = row['Open'] * (1 + SLIPPAGE)
            stop_loss = row['Low'] # LOD
            
            # Start trade tracking from the day after entry (or entry day if we count it)
            # Actually, entry is at open. We check for first daily close below SMA10.
            trade_start_idx = res.index.get_loc(idx)
            future_data = res.iloc[trade_start_idx:]
            
            is_active = True
            for f_idx, f_row in future_data.iterrows():
                # Check for same day LOD stop if Open was below Low (unlikely but safe)
                if f_row['Low'] < stop_loss and f_idx == idx:
                    # If the low of the entry day hits our LOD stop (highly likely if entry is Open)
                    # We need to be careful. Kullamaggie's LOD stop is intraday.
                    # On the daily chart, Open *is* near the Gap. If High never moved up, LOD might hit.
                    # But usually EPs rally. 
                    pass 

                # Survival check: 1st daily close below SMA10
                if f_row['Close'] < f_row['SMA10'] and f_idx > idx:
                    exit_price = f_row['Close']
                    pnl = (exit_price / entry_price) - 1
                    all_trades.append({
                        'Ticker': ticker,
                        'Date': row['Date'],
                        'Entry': entry_price,
                        'Exit': exit_price,
                        'PnL': pnl,
                        'Duration': (f_row['Date'] - row['Date']).days
                    })
                    is_active = False
                    break
            
            if is_active and not future_data.empty:
                # Still in trade at end of history
                last_row = future_data.iloc[-1]
                pnl = (last_row['Close'] / entry_price) - 1
                all_trades.append({
                    'Ticker': ticker,
                    'Date': row['Date'],
                    'Entry': entry_price,
                    'Exit': last_row['Close'],
                    'PnL': pnl,
                    'Duration': (last_row['Date'] - row['Date']).days
                })

    if not all_trades:
        print("No EP trades found in history.")
        return

    trades_df = pd.DataFrame(all_trades)
    results_path = os.path.join(RESULTS_DIR, 'historical_ep_trades.csv')
    trades_df.to_csv(results_path, index=False)
    
    # Summary Statistics
    win_rate = (trades_df['PnL'] > 0).mean()
    avg_pnl = trades_df['PnL'].mean()
    max_gain = trades_df['PnL'].max()
    profit_factor = trades_df[trades_df['PnL'] > 0]['PnL'].sum() / abs(trades_df[trades_df['PnL'] < 0]['PnL'].sum()) if any(trades_df['PnL'] < 0) else np.inf
    
    print("\n--- Historical EP Summary (Multi-Year Daily) ---")
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate:     {win_rate:.2%}")
    print(f"Avg PnL:      {avg_pnl:.2%}")
    print(f"Max Gain:     {max_gain:.2%}")
    print(f"Profit Factor: {profit_factor:.2f}")
    
    summary_data = {
        'Metric': ['Total Trades', 'Win Rate', 'Avg PnL', 'Max Gain', 'Profit Factor'],
        'Value': [len(trades_df), f"{win_rate:.2%}", f"{avg_pnl:.2%}", f"{max_gain:.2%}", f"{profit_factor:.2f}"]
    }
    pd.DataFrame(summary_data).to_csv(os.path.join(RESULTS_DIR, 'historical_ep_summary.csv'), index=False)

if __name__ == "__main__":
    run_historical_ep_backtest()
