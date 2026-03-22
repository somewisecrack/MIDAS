import pandas as pd
import numpy as np
import os

INTRADAY_5M = '/Users/rahulgirishkumar/TRADING/data/gold_5m.csv'
RESULTS_PATH = '/Users/rahulgirishkumar/TRADING/results/gold_audit_intraday.csv'

def audit_intraday():
    print("Loading Gold 5m data...")
    # yfinance multi-header format fix
    df = pd.read_csv(INTRADAY_5M, skiprows=3, names=['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume'])
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    df.sort_values('Datetime', inplace=True)

    # Pre-calculate Intraday Indicators
    df['Date'] = df['Datetime'].dt.date
    df['Range'] = df['High'] - df['Low']
    
    # 1. 80/20 Reversal logic
    # Day 1: Range > 80% of total range at one extreme (Open/Close in extreme 20%).
    # Day 2: Fade the extreme if it breaches and fails.
    # Simplified intraday proxy: if Bar(t-1) is a 80/20 candle, fade it on Bar(t).
    
    # 2. Daily Pivots for Intraday (CPR)
    # We'll calculate daily pivots from previous day's data
    daily = df.groupby('Date').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'})
    daily['P'] = (daily['High'] + daily['Low'] + daily['Close']) / 3
    daily['H3'] = daily['Close'] + (daily['High'] - daily['Low']) * 1.1 / 4
    daily['L3'] = daily['Close'] - (daily['High'] - daily['Low']) * 1.1 / 4
    
    df = df.merge(daily[['P', 'H3', 'L3']].shift(1), left_on='Date', right_index=True, how='left')

    results = []

    # Strategy: Intraday Pivot Reversal (H3/L3)
    # Long at L3, Short at H3
    long_piv = (df['Low'] <= df['L3'])
    long_rets = df['Close'].shift(-12) / df['Close'] - 1 # 1-hour hold
    results.append({'Category': 'Intraday', 'Strategy': 'Camarilla L3 (Mean Reversion)', 'Trades': long_piv.sum(),
                    'Win Rate': (long_rets[long_piv] > 0).mean()*100, 'Avg 1h Return': long_rets[long_piv].mean()*100})

    short_piv = (df['High'] >= df['H3'])
    short_rets = 1 - df['Close'].shift(-12) / df['Close']
    results.append({'Category': 'Intraday', 'Strategy': 'Camarilla H3 (Mean Reversion)', 'Trades': short_piv.sum(),
                    'Win Rate': (short_rets[short_piv] > 0).mean()*100, 'Avg 1h Return': short_rets[short_piv].mean()*100})

    # Strategy: Simple Momentum (3 consecutive bars in same direction)
    df['Color'] = np.sign(df['Close'] - df['Open'])
    mom_long = (df['Color'] == 1) & (df['Color'].shift(1) == 1) & (df['Color'].shift(2) == 1)
    mom_rets = df['Close'].shift(-6) / df['Close'] - 1 # 30-min hold
    results.append({'Category': 'Intraday', 'Strategy': '3-Bar Bullish Momentum', 'Trades': mom_long.sum(),
                    'Win Rate': (mom_rets[mom_long] > 0).mean()*100, 'Avg 30m Return': mom_rets[mom_long].mean()*100})

    res_df = pd.DataFrame(results).round(2)
    print("\n--- Gold Intraday (5m) Audit Results ---")
    print(res_df.to_string(index=False))
    
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    res_df.to_csv(RESULTS_PATH, index=False)

if __name__ == '__main__':
    audit_intraday()
