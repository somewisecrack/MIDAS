import pandas as pd
import numpy as np
import os
from tqdm import tqdm

INTRADAY_DATA = '/Users/rahulgirishkumar/TRADING/data/tickers_5m_ohlcv.csv'
RESULTS_PATH = '/Users/rahulgirishkumar/TRADING/results/pivot_boss_intraday_results.csv'

def evaluate_pivot_intraday():
    print("Loading 5m data (first 5 million rows for speed)...")
    # EPUB indicated many strategies work on liquid stocks. 
    # We will sample or take a large chunk to keep it manageable.
    df = pd.read_csv(INTRADAY_DATA, nrows=5000000)
    
    # Standardize
    df.columns = [c.capitalize() if c.lower() != 'ticker' else 'Ticker' for c in df.columns]
    if 'Datetime' in df.columns:
        df['Date'] = pd.to_datetime(df['Datetime'])
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        
    df.sort_values(['Ticker', 'Date'], inplace=True)

    print("Calculating Intraday Indicators...")
    def apply_intraday_indicators(g):
        g['Range'] = g['High'] - g['Low']
        g['Body'] = (g['Open'] - g['Close']).abs()
        g['ATR20'] = g['Range'].rolling(20).mean()
        
        # Wick Reversal Components
        # Top Wick (Bearish Reversal):
        g['TopWick'] = g['High'] - g[['Open', 'Close']].max(axis=1)
        g['BotWick'] = g[['Open', 'Close']].min(axis=1) - g['Low']
        
        # Wick to Body Ratios (Avoid div by zero)
        safe_body = g['Body'].replace(0, 1e-5)
        g['TopWickRatio'] = g['TopWick'] / safe_body
        g['BotWickRatio'] = g['BotWick'] / safe_body
        
        # Close location: 0 = Low, 1 = High
        g['CloseLoc'] = (g['Close'] - g['Low']) / g['Range'].replace(0, 1e-5)
        
        # Extreme Reversal Components
        g['IsExtreme'] = g['Range'] > 1.8 * g['ATR20'].shift(1)
        g['Color'] = np.sign(g['Close'] - g['Open']) # 1 for green, -1 for red
        
        # Forward returns for evaluation (1 bar = 5m, 12 bars = 1 hour, 78 bars = typical day)
        g['Ret_1h'] = g['Close'].shift(-12) / g['Close'] - 1
        g['Ret_EOD'] = g.groupby(g['Date'].dt.date)['Close'].transform('last') / g['Close'] - 1
        
        return g

    df = df.groupby('Ticker', group_keys=False).apply(apply_intraday_indicators)

    print("Identifying Setups...")
    
    # 1. Wick Reversals (3:1 ratio, close in extreme 20%)
    bull_wick = (g_bot_wick := (df['BotWickRatio'] >= 3.0) & (df['CloseLoc'] >= 0.80))
    bear_wick = (g_top_wick := (df['TopWickRatio'] >= 3.0) & (df['CloseLoc'] <= 0.20))
    
    # 2. Extreme Reversals
    # Bar 1 extreme, Bar 2 opposite color
    df['Prev_IsExtreme'] = df['IsExtreme'].shift(1)
    df['Prev_Color'] = df['Color'].shift(1)
    bull_extreme = (df['Prev_IsExtreme']) & (df['Prev_Color'] == -1) & (df['Color'] == 1)
    bear_extreme = (df['Prev_IsExtreme']) & (df['Prev_Color'] == 1) & (df['Color'] == -1)

    results = []
    
    strats = {
        'Bullish Wick Reversal (5m)': bull_wick,
        'Bearish Wick Reversal (5m)': bear_wick,
        'Bullish Extreme Reversal (5m)': bull_extreme,
        'Bearish Extreme Reversal (5m)': bear_extreme
    }

    for name, mask in strats.items():
        is_short = 'Bearish' in name
        trades = df[mask].copy()
        if len(trades) == 0: continue
        
        # Use 1-hour hold as a baseline for intraday setups
        rets = -trades['Ret_1h'] if is_short else trades['Ret_1h']
        
        results.append({
            'Strategy': name,
            'Trades': len(trades),
            'Win Rate': round((rets > 0).mean() * 100, 2),
            'Avg 1h Return (%)': round(rets.mean() * 100, 2)
        })

    res_df = pd.DataFrame(results)
    print("\n--- Pivot Boss Intraday Strategy Results (1-Hour Hold) ---")
    print(res_df.to_string(index=False))
    
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    res_df.to_csv(RESULTS_PATH, index=False)
    print(f"\nResults saved to {RESULTS_PATH}")

if __name__ == '__main__':
    evaluate_pivot_intraday()
