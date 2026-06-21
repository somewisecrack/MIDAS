import pandas as pd
import numpy as np
from tqdm import tqdm
import os

def calculate_turtle_indicators(df):
    def per_ticker(group):
        group = group.sort_values('Date')
        # N = 20-day ATR
        group['High_Low'] = group['High'] - group['Low']
        group['High_PC'] = abs(group['High'] - group['Close'].shift(1))
        group['Low_PC'] = abs(group['Low'] - group['Close'].shift(1))
        group['TR'] = group[['High_Low', 'High_PC', 'Low_PC']].max(axis=1)
        group['N'] = group['TR'].rolling(window=20).mean()
        
        # Donchian Channels
        group['High_20'] = group['High'].shift(1).rolling(window=20).max()
        group['Low_20'] = group['Low'].shift(1).rolling(window=20).min()
        group['High_55'] = group['High'].shift(1).rolling(window=55).max()
        group['Low_55'] = group['Low'].shift(1).rolling(window=55).min()
        group['High_10'] = group['High'].shift(1).rolling(window=10).max()
        group['Low_10'] = group['Low'].shift(1).rolling(window=10).min()
        return group

    tqdm.pandas(desc="Calculating Indicators")
    return df.groupby('Ticker', group_keys=False).progress_apply(per_ticker)

def simulate_turtle_system(df, system='S1'):
    trades = []
    
    for ticker, group in tqdm(df.groupby('Ticker'), desc=f"Backtesting Turtle {system}"):
        group = group.copy().reset_index(drop=True)
        if len(group) < 60: continue
        
        in_position = False
        units = 0
        entry_price = 0
        stop_loss = 0
        last_s1_win = False # Tracking S1 filter rule
        
        for i in range(55, len(group)):
            row = group.iloc[i]
            
            if not in_position:
                # --- ENTRY LOGIC ---
                triggered = False
                if system == 'S1':
                    # Only take S1 if last S1 wasn't a winner
                    if not last_s1_win:
                        if row['High'] > row['High_20']: # Long
                            entry_price = row['High_20'] + 0.01
                            side = 1
                            triggered = True
                        elif row['Low'] < row['Low_20']: # Short
                            entry_price = row['Low_20'] - 0.01
                            side = -1
                            triggered = True
                else: # S2
                    if row['High'] > row['High_55']: # Long
                        entry_price = row['High_55'] + 0.01
                        side = 1
                        triggered = True
                    elif row['Low'] < row['Low_55']: # Short
                        entry_price = row['Low_55'] - 0.01
                        side = -1
                        triggered = True
                
                if triggered:
                    in_position = True
                    units = 1
                    stop_loss = entry_price - (side * 2 * row['N'])
                    start_idx = i
                    current_n = row['N']
            
            else:
                # --- EXIT & PYRAMIDING LOGIC ---
                # Check Stop Loss (2N)
                if (side == 1 and row['Low'] < stop_loss) or (side == -1 and row['High'] > stop_loss):
                    exit_price = stop_loss
                    pnl = side * (exit_price - entry_price) / entry_price
                    trades.append({'Ticker': ticker, 'Date': row['Date'], 'System': system, 'PnL': pnl, 'Price': entry_price, 'Exit_Type': 'Stop'})
                    in_position = False
                    if system == 'S1': last_s1_win = False
                    continue
                
                # Check Profit Exit (10-day / 20-day)
                exit_trigger = row['Low_10'] if system == 'S1' else row['Low_20']
                if side == -1: exit_trigger = row['High_10'] if system == 'S1' else row['High_20']
                
                if (side == 1 and row['Low'] < exit_trigger) or (side == -1 and row['High'] > exit_trigger):
                    exit_price = exit_trigger
                    pnl = side * (exit_price - entry_price) / entry_price
                    trades.append({'Ticker': ticker, 'Date': row['Date'], 'System': system, 'PnL': pnl, 'Price': entry_price, 'Exit_Type': 'Target'})
                    in_position = False
                    if system == 'S1': last_s1_win = pnl > 0
                    continue

                # Pyramiding (Add 1 unit every 0.5N move, max 4 units)
                if units < 4:
                    if side == 1 and row['High'] > entry_price + (units * 0.5 * current_n):
                        units += 1
                        stop_loss += (0.5 * current_n)
                    elif side == -1 and row['Low'] < entry_price - (units * 0.5 * current_n):
                        units += 1
                        stop_loss -= (0.5 * current_n)

    return pd.DataFrame(trades)

def main():
    data_path = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
    if not os.path.exists(data_path):
        print("Data not found.")
        return
        
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    print("Calculating Turtle Indicators...")
    df = calculate_turtle_indicators(df)
    
    results = []
    for sys in ['S1', 'S2']:
        trades_df = simulate_turtle_system(df, system=sys)
        if not trades_df.empty:
            results.append(trades_df)
            
    if not results:
        print("No trades found.")
        return
        
    final_df = pd.concat(results)
    final_df['Price_Range'] = pd.cut(final_df['Price'], [0, 5, 20, 100, 10000], labels=['<$5', '$5-$20', '$20-$100', '>$100'])
    
    print("\n--- MICHAEL COVEL: THE COMPLETE TURTLETRADER AUDIT ---")
    matrix = final_df.groupby(['System', 'Price_Range'], observed=False).agg(
        Trades=('PnL', 'count'),
        WinRate=('PnL', lambda x: (x > 0).mean()),
        PF=('PnL', lambda x: x[x>0].sum() / abs(x[x<0].sum()) if (x<0).any() else np.inf)
    )
    print(matrix)
    
    output_dir = '/Users/rahulgirishkumar/TRADING/results/turtle'
    os.makedirs(output_dir, exist_ok=True)
    final_df.to_csv(f"{output_dir}/turtle_audit_results.csv", index=False)
    print(f"\nFinal audit saved to {output_dir}/turtle_audit_results.csv")

if __name__ == "__main__":
    main()
