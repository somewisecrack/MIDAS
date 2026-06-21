import pandas as pd
import numpy as np
from tqdm import tqdm
import os
import warnings

warnings.filterwarnings('ignore')

def run_minervini_backtest(data_path, output_dir='results/minervini'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print("Loading data...")
    df = pd.read_csv(data_path)
    
    # 1. Standardize and clean
    df['Date_dt'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date_dt', 'Ticker', 'Close'])
    df['Date_dt'] = df['Date_dt'].dt.normalize()
    
    # 2. Factorize Dates to ensure absolute uniqueness
    # Map each unique Date to an integer. This is foolproof.
    unique_dates = sorted(df['Date_dt'].unique())
    date_map = {d: i for i, d in enumerate(unique_dates)}
    df['Date_ID'] = df['Date_dt'].map(date_map)
    
    print(f"Unique dates count: {len(unique_dates)}")
    
    # 3. Create Matrices
    print("Creating matrices using Date IDs...")
    pivot_df = df.pivot_table(index='Date_ID', columns='Ticker', values=['Close', 'High', 'Low'], aggfunc='first')
    
    prices = pivot_df['Close']
    highs = pivot_df['High']
    lows = pivot_df['Low']
    
    # Map back to Timestamp index for logic
    prices.index = unique_dates
    highs.index = unique_dates
    lows.index = unique_dates
    
    print(f"Matrix shape: {prices.shape}")
    print(f"Index unique: {prices.index.is_unique}")
    
    # Ensure index is sorted
    prices = prices.sort_index()
    highs = highs.sort_index()
    lows = lows.sort_index()
    
    prices = prices.ffill()
    highs = highs.ffill()
    lows = lows.ffill()
    
    prices = prices.ffill()
    highs = highs.ffill()
    lows = lows.ffill()
    
    print("Pre-calculating indicators...")
    sma50 = prices.rolling(50).mean()
    sma150 = prices.rolling(150).mean()
    sma200 = prices.rolling(200).mean()
    high52 = highs.rolling(252).max()
    low52 = lows.rolling(252).min()
    
    # RS Rating Calculation
    print("Calculating RS Ratings...")
    rs_score = (prices / prices.shift(252)) - 1
    rs_rank = rs_score.rank(axis=1, pct=True) * 100
    
    # Trend Template Boolean Matrix
    print("Generating Trend Template Matrix...")
    c1 = (prices > sma150) & (prices > sma200)
    c2 = (sma150 > sma200)
    c3 = (sma200 > sma200.shift(20))
    c4 = (sma50 > sma150) & (sma50 > sma200)
    c5 = (prices > sma50)
    c6 = (prices >= 1.3 * low52)
    c7 = (prices >= 0.75 * high52)
    c8 = (rs_rank >= 70)
    
    print(f"c1 shape: {c1.shape}, index unique: {c1.index.is_unique}")
    print(f"c3 shape: {c3.shape}, index unique: {c3.index.is_unique}")
    print(f"c6 shape: {c6.shape}, index unique: {c6.index.is_unique}")
    print(f"c8 shape: {c8.shape}, index unique: {c8.index.is_unique}")
    
    stage2 = c1 & c2 & c3 & c4 & c5 & c6 & c7 & c8
    print(f"Stage 2 matrix shape (before dedupe): {stage2.shape}")
    
    # FINAL SAFETY: Ensure index is strictly unique
    if not stage2.index.is_unique:
        print(f"Deduplicating stage2 index. Original: {len(stage2)}")
        stage2 = stage2[~stage2.index.duplicated(keep='first')]
    
    print(f"Prices shape: {prices.shape}")
    print(f"Stage 2 matrix shape: {stage2.shape}")
    print(f"Stage 2 matrix True count: {stage2.sum().sum()}")
    
    dates = prices.index
    trades = []
    active_positions = {} 
    
    print("Executing Backtest...")
    vcp_attempts = 0
    vcp_success = 0
    
    for i in tqdm(range(252, len(dates))):
        dt = dates[i]
        today_prices = prices.loc[dt]
        
        # 1. Check Stops and Exits
        # to_remove logic remains
        to_remove = []
        for ticker, pos in active_positions.items():
            curr_price = today_prices.get(ticker, np.nan)
            if pd.isna(curr_price): continue
            
            if curr_price < pos['stop_loss']:
                pnl = (curr_price / pos['entry_price']) - 1
                trades.append({'Ticker': ticker, 'Entry': pos['entry_date'], 'Exit': dt, 'PnL': pnl, 'Type': 'Stop'})
                to_remove.append(ticker)
            elif curr_price < sma50.loc[dt, ticker]:
                pnl = (curr_price / pos['entry_price']) - 1
                trades.append({'Ticker': ticker, 'Entry': pos['entry_date'], 'Exit': dt, 'PnL': pnl, 'Type': 'SMA50'})
                to_remove.append(ticker)
        
        for t in to_remove:
            del active_positions[t]
            
        # 2. Look for new entries
        if len(active_positions) < 10:
            potential_tickers = stage2.loc[dt]
            if isinstance(potential_tickers, pd.DataFrame):
                print(f"ERROR: potential_tickers is a DataFrame for {dt}! Index count: {len(potential_tickers)}")
                continue
                
            candidates = potential_tickers[potential_tickers == True].index
            
            for ticker in candidates:
                if ticker in active_positions: continue
                if len(active_positions) >= 10: break
                
                vcp_attempts += 1
                # Check VCP
                ticker_highs = highs[ticker]
                ticker_lows = lows[ticker]
                
                window_h = ticker_highs.loc[:dt].tail(50)
                window_l = ticker_lows.loc[:dt].tail(50)
                
                if len(window_h) < 50: continue
                
                # Heuristic: Volatility contraction (r1 = last 10d, r2 = 10-30d)
                r1 = (window_h.tail(10).max() - window_l.tail(10).min()) / window_l.tail(10).min()
                r2 = (window_h.iloc[10:30].max() - window_l.iloc[10:30].min()) / window_l.iloc[10:30].min()
                
                # Check for contraction (r1 < r2) and reasonable tightness (r1 < 10%)
                if r1 < 0.10 and r1 < r2:
                    vcp_success += 1
                    entry_price = today_prices[ticker]
                    active_positions[ticker] = {
                        'entry_price': entry_price,
                        'stop_loss': entry_price * 0.93,
                        'entry_date': dt
                    }
    
    print(f"VCP Total Attempts: {vcp_attempts}")
    print(f"VCP Success: {vcp_success}")
        
    if trades:
        trade_df = pd.DataFrame(trades)
        win_rate = (trade_df['PnL'] > 0).mean()
        avg_win = trade_df[trade_df['PnL'] > 0]['PnL'].mean()
        avg_loss = trade_df[trade_df['PnL'] < 0]['PnL'].mean()
        
        print(f"\n--- Minervini Audit Results ---")
        print(f"Total Trades: {len(trade_df)}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Avg PnL: {trade_df['PnL'].mean():.2%}")
        print(f"Profit Factor: {abs(trade_df[trade_df['PnL']>0]['PnL'].sum() / trade_df[trade_df['PnL']<0]['PnL'].sum()):.2f}")
        
        trade_df.to_csv(f"{output_dir}/minervini_trades.csv")
    else:
        print("No trades executed.")

if __name__ == "__main__":
    run_minervini_backtest('/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv')
