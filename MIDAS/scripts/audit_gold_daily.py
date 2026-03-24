import pandas as pd
import numpy as np
import os

DAILY_DATA = '/Users/rahulgirishkumar/TRADING/data/gold_daily.csv'
RESULTS_PATH = '/Users/rahulgirishkumar/TRADING/results/gold_audit_daily.csv'

def audit_daily():
    print("Loading Gold Daily data...")
    # yfinance multi-header format fix
    df = pd.read_csv(DAILY_DATA, skiprows=3, names=['Date', 'Close', 'High', 'Low', 'Open', 'Volume'])
    df['Date'] = pd.to_datetime(df['Date'])
    df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    df.sort_values('Date', inplace=True)

    # Pre-calculate Indicators
    df['Range'] = df['High'] - df['Low']
    df['Prev_High'] = df['High'].shift(1)
    df['Prev_Low'] = df['Low'].shift(1)
    df['Prev_Close'] = df['Close'].shift(1)
    df['Prev_Range'] = df['Range'].shift(1)
    
    # 1. Turtle System 1 (20-day breakout)
    df['Turtle_H20'] = df['High'].rolling(20).max().shift(1)
    df['Turtle_L10'] = df['Low'].rolling(10).min().shift(1)
    
    # 2. Camarilla Levels
    df['H4'] = df['Prev_Close'] + df['Prev_Range'] * 1.1 / 2
    df['L4'] = df['Prev_Close'] - df['Prev_Range'] * 1.1 / 2
    
    # 3. Alpha 101 (Example: Alpha 1)
    # alpha001: (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2), 5)) - 0.5)
    df['Returns'] = df['Close'].pct_change()
    df['Std20'] = df['Returns'].rolling(20).std()
    df['A1_Base'] = np.where(df['Returns'] < 0, df['Std20'], df['Close'])
    # simplified A1 proxy
    
    results = []

    # --- SWING STRATEGY EVALUATION ---
    
    # Strategy: Turtle S1 Long
    t_long = (df['Close'] > df['Turtle_H20'])
    t_long_rets = df['Close'].shift(-5) / df['Close'] - 1 # 5-day hold
    results.append({'Category': 'Swing', 'Strategy': 'Turtle System 1 (20d Breakout)', 'Trades': t_long.sum(),
                    'Win Rate': (t_long_rets[t_long] > 0).mean()*100, 'Avg Return': t_long_rets[t_long].mean()*100})

    # Strategy: Camarilla H4 Breakout
    c_h4 = (df['Close'] > df['H4'])
    c_h4_rets = df['Close'].shift(-3) / df['Close'] - 1
    results.append({'Category': 'Swing', 'Strategy': 'Camarilla H4 Breakout', 'Trades': c_h4.sum(),
                    'Win Rate': (c_h4_rets[c_h4] > 0).mean()*100, 'Avg Return': c_h4_rets[c_h4].mean()*100})
                    
    # Strategy: Mean Reversion (RSI 2)
    df['RSI2'] = 100 - (100 / (1 + (df['Returns'].clip(lower=0).rolling(2).mean() / df['Returns'].clip(upper=0).abs().rolling(2).mean())))
    rsi_long = (df['RSI2'] < 10)
    rsi_rets = df['Close'].shift(-2) / df['Close'] - 1
    results.append({'Category': 'Swing', 'Strategy': 'RSI(2) Oversold (<10)', 'Trades': rsi_long.sum(),
                    'Win Rate': (rsi_rets[rsi_long] > 0).mean()*100, 'Avg Return': rsi_rets[rsi_long].mean()*100})

    res_df = pd.DataFrame(results).round(2)
    print("\n--- Gold Daily Audit Results ---")
    print(res_df.to_string(index=False))
    
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    res_df.to_csv(RESULTS_PATH, index=False)

if __name__ == '__main__':
    audit_daily()
