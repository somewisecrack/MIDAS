import pandas as pd
import numpy as np
import os

DAILY_DATA = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
RESULTS_PATH = '/Users/rahulgirishkumar/TRADING/results/pivot_boss_price_bucket_summary.csv'

def classify_by_price():
    print("Loading daily data for price classification...")
    df = pd.read_csv(DAILY_DATA)
    df.columns = [c.capitalize() if c.lower() != 'ticker' else 'Ticker' for c in df.columns]
    df.sort_values(['Ticker', 'Date'], inplace=True)

    print("Calculating Pivots & Buckets...")
    def apply_logic(g):
        h = g['High'].shift(1)
        l = g['Low'].shift(1)
        c = g['Close'].shift(1)
        r = h - l
        
        # CPR
        p = (h + l + c) / 3
        bc = (h + l) / 2
        tc = (p - bc) + p
        g['P'] = p
        g['TopC'] = np.where(tc > bc, tc, bc)
        g['BotC'] = np.where(tc > bc, bc, tc)
        
        # Camarilla
        g['H3'] = c + r * 1.1 / 4
        g['H4'] = c + r * 1.1 / 2
        g['L3'] = c - r * 1.1 / 4
        g['L4'] = c - r * 1.1 / 2
        
        # Trend
        g['Higher_Value'] = p > p.shift(1)
        g['Lower_Value'] = p < p.shift(1)
        
        return g

    df = df.groupby('Ticker', group_keys=False).apply(apply_logic)
    
    # Define buckets
    bins = [0, 5, 20, 50, np.inf]
    labels = ['<5', '5-20', '20-50', '>=50']
    df['PriceBucket'] = pd.cut(df['Open'], bins=bins, labels=labels)

    # Strategy Masks
    bull_magnet = (df['Higher_Value']) & (df['Open'] > df['TopC']) & (df['Open'] < df['H3'])
    bear_magnet = (df['Lower_Value']) & (df['Open'] < df['BotC']) & (df['Open'] > df['L3'])
    bull_break = (df['Close'] > df['H4'])
    bear_break = (df['Close'] < df['L4'])

    summary = []

    # Helper to calculate and append
    def add_to_summary(mask, name, is_reversion=False, direction='bull'):
        subset = df[mask].dropna(subset=['PriceBucket']).copy()
        if is_reversion:
            if direction == 'bull': # Short at open, exit at P
                subset['Success'] = subset['Low'] <= subset['P']
                subset['Ret'] = np.where(subset['Success'], (subset['Open'] - subset['P'])/subset['Open'], (subset['Open']-subset['Close'])/subset['Open'])
            else: # Long at open, exit at P
                subset['Success'] = subset['High'] >= subset['P']
                subset['Ret'] = np.where(subset['Success'], (subset['P'] - subset['Open'])/subset['Open'], (subset['Close']-subset['Open'])/subset['Open'])
        else: # Trend 3-day hold
            if direction == 'bull':
                subset['Ret'] = df['Close'].shift(-3).reindex(subset.index) / subset['Close'] - 1
            else:
                subset['Ret'] = 1 - df['Close'].shift(-3).reindex(subset.index) / subset['Close']
            subset['Success'] = subset['Ret'] > 0

        # Group by bucket
        gb = subset.groupby('PriceBucket', observed=False).agg(
            Trades=('Ret', 'count'),
            WinRate=('Success', 'mean'),
            AvgReturn=('Ret', 'mean')
        )
        for bucket, row in gb.iterrows():
            summary.append({
                'Strategy': name,
                'PriceBucket': bucket,
                'Trades': int(row['Trades']),
                'Win Rate %': round(row['WinRate']*100, 2),
                'Avg Return %': round(row['AvgReturn']*100, 2)
            })

    add_to_summary(bull_magnet, 'CPR Magnet (Bull Trend Reversion)', is_reversion=True, direction='bull')
    add_to_summary(bear_magnet, 'CPR Magnet (Bear Trend Reversion)', is_reversion=True, direction='bear')
    add_to_summary(bull_break, 'Camarilla H4 Breakout (3d)', is_reversion=False, direction='bull')
    add_to_summary(bear_break, 'Camarilla L4 Breakout (3d)', is_reversion=False, direction='bear')

    summary_df = pd.DataFrame(summary)
    print(summary_df.to_string(index=False))
    
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    summary_df.to_csv(RESULTS_PATH, index=False)
    print(f"\nResults saved to {RESULTS_PATH}")

if __name__ == '__main__':
    classify_by_price()
