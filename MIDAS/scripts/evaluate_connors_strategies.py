import pandas as pd
import numpy as np
import os
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

DAILY_DATA = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
BREADTH_DATA = '/Users/rahulgirishkumar/TRADING/data/market_breadth_derived.csv'
RESULTS_PATH = '/Users/rahulgirishkumar/TRADING/results/connors_evaluation_results.csv'

def calc_adx(df, window=14):
    up = df['High'] - df['High'].shift(1)
    down = df['Low'].shift(1) - df['Low']
    
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window).mean()
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(window).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(window).mean() / atr)
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(window).mean()
    return adx, plus_di, minus_di

def calc_rsi(series, window):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def evaluate_connors():
    print("Loading data...")
    df = pd.read_csv(DAILY_DATA)
    # Ensure standard names
    df.columns = [c.capitalize() if c.lower() != 'ticker' else 'Ticker' for c in df.columns]
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values(['Ticker', 'Date'], inplace=True)
    
    try:
        breadth = pd.read_csv(BREADTH_DATA)
        breadth['Date'] = pd.to_datetime(breadth['Date'])
        # TRIN = (Adv/Dec) / (UpVol/DownVol)
        breadth['AD_Ratio'] = breadth['Advances'] / breadth['Declines'].replace(0, 1)
        breadth['Vol_Ratio'] = breadth['Up_Volume'] / breadth['Down_Volume'].replace(0, 1)
        breadth['TRIN'] = breadth['AD_Ratio'] / breadth['Vol_Ratio'].replace(0, 1)
        breadth['TRIN_SMA3'] = breadth['TRIN'].rolling(3).mean()
        breadth['PADI'] = breadth['Advances'] / (breadth['Advances'] + breadth['Declines']).replace(0, 1)
        
        df = df.merge(breadth[['Date', 'TRIN_SMA3', 'PADI']], on='Date', how='left')
    except Exception as e:
        print("Breadth merge failed:", e)
        df['TRIN_SMA3'] = 1.0
        df['PADI'] = 0.5

    results = []

    # Vectorized logic per ticker grouping
    # Because of Pandas complexity, calculating ATR, ADX, RSI dynamically per ticker:
    print("Calculating technical indicators...")
    
    def apply_indicators(g):
        g['TR'] = np.maximum((g['High'] - g['Low']), 
                             np.maximum(abs(g['High'] - g['Close'].shift(1)), 
                                        abs(g['Low'] - g['Close'].shift(1))))
        g['ATR14'] = g['TR'].rolling(14).mean()
        
        # Ranges
        g['Daily_Range'] = g['High'] - g['Low']
        g['Close_Pos'] = (g['Close'] - g['Low']) / g['Daily_Range'].replace(0, 1e-5)
        
        # Moving Averages & Volume
        g['SMA20'] = g['Close'].rolling(20).mean()
        g['Vol_SMA20'] = g['Volume'].rolling(20).mean()
        g['Return_3d'] = g['Close'].shift(-3) / g['Close'] - 1  # 3-day hold
        g['Return_5d'] = g['Close'].shift(-5) / g['Close'] - 1  # 5-day hold
        
        # Highs/Lows
        g['High8'] = g['High'].rolling(8).max()
        g['Low8'] = g['Low'].rolling(8).min()
        g['High20'] = g['High'].rolling(20).max()
        
        # RSI
        g['RSI2'] = calc_rsi(g['Close'], 2)
        
        # 1-2-3-4 ADX
        try:
            g['ADX'], g['PDI'], g['MDI'] = calc_adx(g)
        except:
            g['ADX'], g['PDI'], g['MDI'] = 0, 0, 0
            
        g['LowerLow1'] = g['Low'] < g['Low'].shift(1)
        g['LowerLow2'] = g['Low'].shift(1) < g['Low'].shift(2)
        g['LowerLow3'] = g['Low'].shift(2) < g['Low'].shift(3)
        g['1234_Setup'] = g['LowerLow1'] & g['LowerLow2'] & g['LowerLow3'] & (g['ADX'] > 30) & (g['PDI'] > g['MDI'])
        
        # SMTP
        g['UpClose'] = g['Close'] > g['Close'].shift(1)
        g['5_Up'] = g['UpClose'].rolling(5).sum() == 5
        
        return g

    # Optimize to run only on a subset if testing or run all if capable
    # Using groupby transform/apply
    df = df.groupby('Ticker', group_keys=False).apply(apply_indicators)
    
    print("Evaluating Strategies...")
    
    strats = {}
    
    # 1. TRIN Thrusts: Market timing so we assume SPY or proxy. We buy the stock when TRIN > 1.2
    strats['TRIN_Thrusts'] = (df['TRIN_SMA3'] > 1.20)
    
    # 2. PADI: PADI < 0.3 for 2 days
    strats['PADI'] = (df['PADI'] < 0.30) & (df['PADI'].shift(1) < 0.30)
    
    # 3. 1-2-3-4 Pattern
    strats['1-2-3-4 Pattern'] = df['1234_Setup']
    
    # 4. Runaway Moves: Gap up > 1% in ADX>40
    strats['Runaway Moves'] = (df['ADX'] > 40) & ((df['Open'] / df['Close'].shift(1) - 1) > 0.01)
    
    # 5. Large-Range Days
    strats['Large-Range Days'] = (df['Daily_Range'] > 1.5 * df['ATR14']) & (df['Close'] > df['Open'])
    
    # 6. 8-Day High/Low Reversal (Short & Long)
    # Long: 8 day low, close in top 25%
    strats['8-Day Reversal Long'] = (df['Low'] == df['Low8']) & (df['Close_Pos'] >= 0.75)
    # Short: 8 day high, close in bottom 25%
    strats['8-Day Reversal Short'] = (df['High'] == df['High8']) & (df['Close_Pos'] <= 0.25)
    
    # 7. Spent Market Trading Pattern
    strats['SMTP Short'] = df['5_Up'].shift(1) & (df['Open'] > df['Close'].shift(1)) & (df['Volume'] < 0.8 * df['Vol_SMA20'])
    
    # 8. Double Volume Market Top
    strats['Double Vol Top Short'] = (df['High'] == df['High20']) & (df['Volume'] > 2 * df['Vol_SMA20']) & (df['Close_Pos'] <= 0.50)
    
    # 9. Crash, Burn, and Profit
    strats['Crash, Burn (RSI2<5)'] = (df['RSI2'] < 5) & (df['RSI2'].shift(1) < 5)
    
    # 10. Gipsons (3 std dev is roughly BB, we'll proxy with 10% below SMA20 for speed)
    strats['Gipsons'] = (df['Close'] < df['SMA20'] * 0.90)
    
    # 11. The 10% OOPS
    strats['10% OOPS'] = (df['Open'] < df['Low'].shift(1) * 0.90) & (df['Close'] > df['Low'].shift(1))
    
    # 12. Torpedoes
    strats['Torpedoes'] = (df['Open'] < df['Close'].shift(1) * 0.80) & (df['Close'] > df['Open'])
    
    # 13. Reversals off Morning Call
    strats['Morning Call Short'] = (df['Open'] > df['Close'].shift(1) * 1.02) & (df['Close'] < df['Open'])
    
    # 14. Wide Range Exhaustion Gap
    strats['Exhaustion Gap Short'] = (df['Open'] > df['High'].shift(1)) & (df['Daily_Range'] > 2 * df['ATR14']) & (df['Close'] < df['Open'])

    summary = []
    
    for name, mask in strats.items():
        # Long strategies use Next Open to Close(+3/+5) returns
        # Short strategies use the inverse
        is_short = 'Short' in name
        
        trades = df[mask.fillna(False)]
        num_trades = len(trades)
        if num_trades == 0:
            continue
            
        ret_col = 'Return_5d'  # Standard 5-day hold
        
        if is_short:
            rets = -trades[ret_col]
        else:
            rets = trades[ret_col]
            
        win_rate = (rets > 0).mean()
        avg_ret = rets.mean()
        
        summary.append({
            'Strategy': name,
            'Trades': num_trades,
            'Win Rate': round(win_rate * 100, 2),
            'Avg 5-Day Return (%)': round(avg_ret * 100, 2)
        })
        
    res_df = pd.DataFrame(summary).sort_values('Avg 5-Day Return (%)', ascending=False)
    print("\n--- Larry Connors Daily Strategies Panel Evaluation ---")
    print(res_df.to_string(index=False))
    
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    res_df.to_csv(RESULTS_PATH, index=False)
    print(f"\nSaved to {RESULTS_PATH}")

if __name__ == '__main__':
    evaluate_connors()
