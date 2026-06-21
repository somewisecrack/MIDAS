import pandas as pd
import numpy as np
import os

# Paths
RESULTS_PATH = '/Users/rahulgirishkumar/TRADING/results/connors_evaluation_results.csv'
DAILY_DATA = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
OUTPUT_PATH = '/Users/rahulgirishkumar/TRADING/results/connors_price_bucket_summary.csv'

# Load backtest results (per‑trade summary already aggregated per strategy)
# We'll need per‑trade data to map price, so we re‑load the full daily data and recompute masks

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

def load_data():
    df = pd.read_csv(DAILY_DATA)
    df.columns = [c.capitalize() if c.lower() != 'ticker' else 'Ticker' for c in df.columns]
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values(['Ticker', 'Date'], inplace=True)
    return df

def apply_indicators(g):
    # Basic technicals needed for the strategies (same as evaluation script)
    g['TR'] = np.maximum((g['High'] - g['Low']), np.maximum(abs(g['High'] - g['Close'].shift(1)), abs(g['Low'] - g['Close'].shift(1))) )
    g['ATR14'] = g['TR'].rolling(14).mean()
    g['Daily_Range'] = g['High'] - g['Low']
    g['Close_Pos'] = (g['Close'] - g['Low']) / g['Daily_Range'].replace(0, 1e-5)
    g['SMA20'] = g['Close'].rolling(20).mean()
    g['Vol_SMA20'] = g['Volume'].rolling(20).mean()
    g['Return_5d'] = g['Close'].shift(-5) / g['Close'] - 1
    g['High8'] = g['High'].rolling(8).max()
    g['Low8'] = g['Low'].rolling(8).min()
    g['High20'] = g['High'].rolling(20).max()
    g['RSI2'] = calc_rsi(g['Close'], 2)
    try:
        g['ADX'], g['PDI'], g['MDI'] = calc_adx(g)
    except Exception:
        g['ADX'], g['PDI'], g['MDI'] = 0, 0, 0
    g['LowerLow1'] = g['Low'] < g['Low'].shift(1)
    g['LowerLow2'] = g['Low'].shift(1) < g['Low'].shift(2)
    g['LowerLow3'] = g['Low'].shift(2) < g['Low'].shift(3)
    g['1234_Setup'] = g['LowerLow1'] & g['LowerLow2'] & g['LowerLow3'] & (g['ADX'] > 30) & (g['PDI'] > g['MDI'])
    g['UpClose'] = g['Close'] > g['Close'].shift(1)
    g['5_Up'] = g['UpClose'].rolling(5).sum() == 5
    return g

def build_strategies(df):
    # Simple placeholders for TRIN/PADI – set neutral values if missing
    df['TRIN_SMA3'] = 1.0
    df['PADI'] = 0.5
    strats = {}
    strats['TRIN_Thrusts'] = (df['TRIN_SMA3'] > 1.20)
    strats['PADI'] = (df['PADI'] < 0.30) & (df['PADI'].shift(1) < 0.30)
    strats['1-2-3-4 Pattern'] = df['1234_Setup']
    strats['Runaway Moves'] = (df['ADX'] > 40) & ((df['Open'] / df['Close'].shift(1) - 1) > 0.01)
    strats['Large-Range Days'] = (df['Daily_Range'] > 1.5 * df['ATR14']) & (df['Close'] > df['Open'])
    strats['8-Day Reversal Long'] = (df['Low'] == df['Low8']) & (df['Close_Pos'] >= 0.75)
    strats['8-Day Reversal Short'] = (df['High'] == df['High8']) & (df['Close_Pos'] <= 0.25)
    strats['SMTP Short'] = df['5_Up'].shift(1) & (df['Open'] > df['Close'].shift(1)) & (df['Volume'] < 0.8 * df['Vol_SMA20'])
    strats['Double Vol Top Short'] = (df['High'] == df['High20']) & (df['Volume'] > 2 * df['Vol_SMA20']) & (df['Close_Pos'] <= 0.50)
    strats['Crash, Burn (RSI2<5)'] = (df['RSI2'] < 5) & (df['RSI2'].shift(1) < 5)
    strats['Gipsons'] = (df['Close'] < df['SMA20'] * 0.90)
    strats['10% OOPS'] = (df['Open'] < df['Low'].shift(1) * 0.90) & (df['Close'] > df['Low'].shift(1))
    strats['Torpedoes'] = (df['Open'] < df['Close'].shift(1) * 0.80) & (df['Close'] > df['Open'])
    strats['Morning Call Short'] = (df['Open'] > df['Close'].shift(1) * 1.02) & (df['Close'] < df['Open'])
    strats['Exhaustion Gap Short'] = (df['Open'] > df['High'].shift(1)) & (df['Daily_Range'] > 2 * df['ATR14']) & (df['Close'] < df['Open'])
    return strats

def price_bucket(price):
    if price < 5:
        return '<5'
    elif price < 20:
        return '5-20'
    elif price < 50:
        return '20-50'
    else:
        return '>=50'

def main():
    df = load_data()
    df = df.groupby('Ticker', group_keys=False).apply(apply_indicators)
    strats = build_strategies(df)
    # Determine a representative price per ticker – use the most recent close price
    latest = df.groupby('Ticker').apply(lambda g: g.iloc[-1])
    latest_prices = latest['Close']
    price_bins = latest_prices.apply(price_bucket)
    summary_rows = []
    for name, mask in strats.items():
        trades = df[mask.fillna(False)]
        if trades.empty:
            continue
        # Attach price bucket per trade via ticker lookup
        trades = trades.copy()
        trades['PriceBucket'] = trades['Ticker'].map(price_bins)
        # Compute metrics per bucket
        for bucket, grp in trades.groupby('PriceBucket'):
            num = len(grp)
            if num == 0:
                continue
            is_short = 'Short' in name
            ret = -grp['Return_5d'] if is_short else grp['Return_5d']
            win = (ret > 0).mean()
            avg_ret = ret.mean()
            summary_rows.append({
                'Strategy': name,
                'PriceBucket': bucket,
                'Trades': num,
                'WinRate%': round(win * 100, 2),
                'Avg5DayReturn%': round(avg_ret * 100, 2)
            })
    out = pd.DataFrame(summary_rows)
    out.to_csv(OUTPUT_PATH, index=False)
    print('Price‑bucket summary written to', OUTPUT_PATH)
    # Also pretty‑print to console for quick view (top 20 rows)
    if not out.empty:
        print(out.head(20).to_string(index=False))

if __name__ == '__main__':
    main()
