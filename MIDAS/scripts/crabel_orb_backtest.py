import pandas as pd
import numpy as np
import os
from tqdm import tqdm

def run_crabel_orb_audit(daily_path, intraday_path):
    print("Loading Daily data for pattern detection...")
    daily_df = pd.read_csv(daily_path)
    daily_df['Date'] = pd.to_datetime(daily_df['Date'])
    daily_df = daily_df.sort_values(['Ticker', 'Date'])

    # 1. Calculate Patterns
    print("Calculating NR7, NR4, WS7, WS4, Inside Days, Hook Days, and Stretch...")
    daily_df['Range'] = daily_df['High'] - daily_df['Low']
    
    # NR7/NR4 (Standard)
    daily_df['NR7'] = daily_df.groupby('Ticker')['Range'].transform(lambda x: x < x.shift(1).rolling(6).min())
    daily_df['NR4'] = daily_df.groupby('Ticker')['Range'].transform(lambda x: x < x.shift(1).rolling(3).min())
    
    # WS7/WS4 (Wide Range 7/4)
    daily_df['WS7'] = daily_df.groupby('Ticker')['Range'].transform(lambda x: x > x.shift(1).rolling(6).max())
    daily_df['WS4'] = daily_df.groupby('Ticker')['Range'].transform(lambda x: x > x.shift(1).rolling(3).max())
    
    # Inside Day & Hook Day
    daily_df['InsideDay'] = daily_df.groupby('Ticker').apply(
        lambda x: (x['High'] < x['High'].shift(1)) & (x['Low'] > x['Low'].shift(1))
    ).reset_index(level=0, drop=True)
    
    # Hook Day: Open outside prev range, reverses prev close, narrowing range
    daily_df['Hook'] = daily_df.groupby('Ticker').apply(
        lambda x: ((x['Open'] > x['High'].shift(1)) | (x['Open'] < x['Low'].shift(1))) & 
                  (((x['Open'] > x['Close'].shift(1)) & (x['Close'] < x['Open'])) | 
                   ((x['Open'] < x['Close'].shift(1)) & (x['Close'] > x['Open']))) &
                  (x['Range'] < x['Range'].shift(1))
    ).reset_index(level=0, drop=True)
    
    # Price Grouping (using prev day close)
    def get_price_group(price):
        if price < 5: return '<$5'
        if price < 20: return '$5-$20'
        if price < 100: return '$20-$100'
        return '>$100'

    daily_df['PriceGroup'] = daily_df['Close'].shift(1).apply(get_price_group)
    
    # Calculate Stretch
    daily_df['Dist'] = daily_df[['High', 'Low', 'Open']].apply(
        lambda x: min(x['High'] - x['Open'], x['Open'] - x['Low']), axis=1
    )
    daily_df['Stretch'] = daily_df.groupby('Ticker')['Dist'].transform(lambda x: x.shift(1).rolling(10).mean())

    # Map signals to Entry Day
    daily_df['prev_NR7'] = daily_df.groupby('Ticker')['NR7'].shift(1).fillna(False)
    daily_df['prev_NR4'] = daily_df.groupby('Ticker')['NR4'].shift(1).fillna(False)
    daily_df['prev_WS7'] = daily_df.groupby('Ticker')['WS7'].shift(1).fillna(False)
    daily_df['prev_WS4'] = daily_df.groupby('Ticker')['WS4'].shift(1).fillna(False)
    daily_df['prev_ID'] = daily_df.groupby('Ticker')['InsideDay'].shift(1).fillna(False)
    daily_df['prev_Hook'] = daily_df.groupby('Ticker')['Hook'].shift(1).fillna(False)
    
    daily_df['EntryDay'] = daily_df['prev_NR7'] | daily_df['prev_ID'] | daily_df['prev_NR4'] | \
                           daily_df['prev_WS7'] | daily_df['prev_WS4'] | daily_df['prev_Hook']

    # Filter to only relevant setup days
    setups = daily_df[daily_df['EntryDay'] == True][['Date', 'Ticker', 'Stretch', 'PriceGroup', 
                                                     'prev_NR7', 'prev_NR4', 'prev_WS7', 'prev_WS4', 'prev_ID', 'prev_Hook']]
    setups = setups.rename(columns={'Date': 'Daily_Date'})
    setups['Date_only'] = setups['Daily_Date'].dt.date
    
    del daily_df # Save memory

    # 2. Load Intraday Data
    print(f"Loading Intraday data ({os.path.basename(intraday_path)})...")
    intraday_df = pd.read_csv(intraday_path)
    intraday_df['Timestamp'] = pd.to_datetime(intraday_df['Date'])
    intraday_df['Date_only'] = intraday_df['Timestamp'].dt.date
    
    # Filter intraday to only tickers/dates that had a setup
    print("Filtering intraday data to setup days...")
    relevant_intraday = pd.merge(intraday_df, setups, on=['Date_only', 'Ticker'], how='inner')
    
    if relevant_intraday.empty:
        print("No matches found between Daily setups and Intraday data periods.")
        return

    # 3. Simulate ORB
    print("Executing ORB Simulation...")
    # Define Opening Range (First 30 Minutes: 14:30 to 15:00 UTC)
    relevant_intraday['Time'] = relevant_intraday['Timestamp'].dt.time
    
    # Opening Range bars (14:30 to 14:55 UTC)
    or_mask = (relevant_intraday['Timestamp'].dt.hour == 14) & (relevant_intraday['Timestamp'].dt.minute <= 55)
    or_data = relevant_intraday[or_mask]
    
    if or_data.empty:
        print("No matches after time filtering. Check if intraday timestamps match 14:30-15:00 UTC.")
        return

    or_levels = or_data.groupby(['Date_only', 'Ticker']).agg(
        OR_High=('High', 'max'),
        OR_Low=('Low', 'min')
    ).reset_index()
    
    # Merge OR levels back
    sim_data = pd.merge(relevant_intraday, or_levels, on=['Date_only', 'Ticker'])
    sim_data = sim_data.sort_values(['Ticker', 'Timestamp'])
    
    # Post-OR data (after 15:00 UTC)
    post_or = sim_data[sim_data['Timestamp'].dt.time >= pd.to_datetime('15:00:00').time()]
    
    trades = []
    
    # Process each (Ticker, Date) group efficiently
    # Instead of row iteration, we pre-calculate triggers
    post_or['Long_Trigger'] = post_or['OR_High'] + post_or['Stretch']
    post_or['Short_Trigger'] = post_or['OR_Low'] - post_or['Stretch']
    
    # Track first breach per day/ticker
    groups = post_or.groupby(['Ticker', 'Date_only'])
    
    print("Vectorizing trade detection...")
    for (ticker, dt_only), group in tqdm(groups):
        stretch = group['Stretch'].iloc[0]
        
        # Vectorized check for first entry
        # Find first bar where High > Long_Trigger or Low < Short_Trigger
        long_breaches = group[group['High'] > group['Long_Trigger']]
        short_breaches = group[group['Low'] < group['Short_Trigger']]
        
        first_long = long_breaches['Timestamp'].min() if not long_breaches.empty else pd.NaT
        first_short = short_breaches['Timestamp'].min() if not short_breaches.empty else pd.NaT
        
        if pd.isna(first_long) and pd.isna(first_short):
            continue
            
        # Determine which direction triggered first
        entry_type = None
        entry_time = None
        entry_price = None
        stop_price = None
        
        if pd.notna(first_long) and (pd.isna(first_short) or first_long < first_short):
            entry_type = 'Long'
            entry_time = first_long
            entry_price = group['Long_Trigger'].iloc[0]
            stop_price = group['Short_Trigger'].iloc[0]
        else:
            entry_type = 'Short'
            entry_time = first_short
            entry_price = group['Short_Trigger'].iloc[0]
            stop_price = group['Long_Trigger'].iloc[0]
            
        # Check for Stop Out or EOD Exit
        # Only look at bars AFTER entry_time
        remaining_bars = group[group['Timestamp'] >= entry_time]
        
        pnl = 0
        exit_time = remaining_bars['Timestamp'].iloc[-1]
        exit_reason = 'EOD'
        
        if entry_type == 'Long':
            stops = remaining_bars[remaining_bars['Low'] < stop_price]
            if not stops.empty:
                exit_time = stops['Timestamp'].iloc[0]
                exit_reason = 'Stop'
                pnl = (stop_price - entry_price) / entry_price
            else:
                pnl = (remaining_bars['Close'].iloc[-1] - entry_price) / entry_price
        else: # Short
            stops = remaining_bars[remaining_bars['High'] > stop_price]
            if not stops.empty:
                exit_time = stops['Timestamp'].iloc[0]
                exit_reason = 'Stop'
                pnl = (entry_price - stop_price) / entry_price
            else:
                pnl = (entry_price - remaining_bars['Close'].iloc[-1]) / entry_price
        
        # Get setup flags
        nr7 = group['prev_NR7'].iloc[0]
        nr4 = group['prev_NR4'].iloc[0]
        ws7 = group['prev_WS7'].iloc[0]
        ws4 = group['prev_WS4'].iloc[0]
        id_flag = group['prev_ID'].iloc[0]
        hook = group['prev_Hook'].iloc[0]
        price_group = group['PriceGroup'].iloc[0]
                
        trades.append([ticker, dt_only, entry_time, exit_time, pnl, exit_reason, price_group, nr7, nr4, ws7, ws4, id_flag, hook])

    # 4. Results Export
    results_df = pd.DataFrame(trades, columns=['Ticker', 'Date', 'EntryTime', 'ExitTime', 'PnL', 'ExitReason', 'PriceGroup', 
                                               'NR7', 'NR4', 'WS7', 'WS4', 'ID', 'Hook'])
    os.makedirs('results/crabel', exist_ok=True)
    results_df.to_csv('results/crabel/crabel_trades.csv', index=False)
    
    print(f"\n--- Crabel Audit Results ---")
    print(f"Total Trades: {len(results_df)}")
    if len(results_df) > 0:
        print(f"Win Rate: {(results_df['PnL'] > 0).mean():.2%}")
        print(f"Avg PnL: {results_df['PnL'].mean():.2%}")
        
        print("\n--- Performance by Price Range ---")
        for pg in ['<$5', '$5-$20', '$20-$100', '>$100']:
            pg_trades = results_df[results_df['PriceGroup'] == pg]
            if not pg_trades.empty:
                wr = (pg_trades['PnL'] > 0).mean()
                avg_pnl = pg_trades['PnL'].mean()
                print(f"{pg:10}: {len(pg_trades)} trades | WR: {wr:.2%} | Avg PnL: {avg_pnl:.2%}")

        print("\n--- Performance by Pattern (Yesterday's Setup) ---")
        for pat in ['NR7', 'NR4', 'WS7', 'WS4', 'ID', 'Hook']:
            pat_trades = results_df[results_df[pat] == True]
            if not pat_trades.empty:
                wr = (pat_trades['PnL'] > 0).mean()
                avg_pnl = pat_trades['PnL'].mean()
                pf = abs(pat_trades[pat_trades['PnL']>0]['PnL'].sum() / pat_trades[pat_trades['PnL']<0]['PnL'].sum()) if pat_trades[pat_trades['PnL']<0]['PnL'].sum() != 0 else 0
                print(f"{pat:6}: {len(pat_trades)} trades | WR: {wr:.2%} | Avg PnL: {avg_pnl:.2%} | PF: {pf:.2f}")

if __name__ == "__main__":
    run_crabel_orb_audit(
        '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv',
        '/Users/rahulgirishkumar/TRADING/data/tickers_5m_ohlcv.csv'
    )
