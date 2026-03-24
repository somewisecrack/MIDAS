import pandas as pd
import numpy as np
import os
from tqdm import tqdm

DAILY_DATA = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
RESULTS_PATH = '/Users/rahulgirishkumar/TRADING/results/pivot_boss_daily_results.csv'

def evaluate_pivot_daily():
    print("Loading daily data...")
    df = pd.read_csv(DAILY_DATA)
    # Standardize column names
    df.columns = [c.capitalize() if c.lower() != 'ticker' else 'Ticker' for c in df.columns]
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values(['Ticker', 'Date'], inplace=True)

    print("Calculating Pivots...")
    def apply_pivots(g):
        # Shifted pivots (Yesterday's OHLC determines Today's levels)
        h = g['High'].shift(1)
        l = g['Low'].shift(1)
        c = g['Close'].shift(1)
        r = h - l
        
        # Central Pivot Range (CPR)
        g['P'] = (h + l + c) / 3
        g['BC'] = (h + l) / 2
        g['TC'] = (g['P'] - g['BC']) + g['P']
        
        # Normalize TC/BC (TC is always > BC in many platforms, but formulaically it depends)
        # Ochoa uses TC = top, BC = bottom.
        g['TopC'] = np.where(g['TC'] > g['BC'], g['TC'], g['BC'])
        g['BotC'] = np.where(g['TC'] > g['BC'], g['BC'], g['TC'])
        
        # Camarilla Levels
        g['H3'] = c + r * 1.1 / 4
        g['H4'] = c + r * 1.1 / 2
        g['L3'] = c - r * 1.1 / 4
        g['L4'] = c - r * 1.1 / 2
        
        # Returns for holds
        g['Ret_EOD'] = g['Close'] / g['Open'] - 1
        g['Ret_3d'] = g['Close'].shift(-3) / g['Open'] - 1
        g['Ret_1d_Next'] = g['Close'].shift(-1) / g['Open'] - 1 # Entry Open, Exit Next Close
        
        # Relationship - Current vs Prior CPR
        g['Prev_P'] = g['P'].shift(1)
        g['Higher_Value'] = g['P'] > g['Prev_P']
        g['Lower_Value'] = g['P'] < g['Prev_P']
        
        return g

    df = df.groupby('Ticker', group_keys=False).apply(apply_pivots)

    print("Identifying Setups...")
    
    # 1. CPR Magnet Trade: 
    # Gap in direction of trend (Higher Value -> Gap Up), then return to Pivot
    # Bullish Magnet: Higher Value AND Open > TopC AND Open < H3. Target P.
    # We'll proxy "return to Pivot" as if Price Low <= P during the day.
    bull_magnet = (df['Higher_Value']) & (df['Open'] > df['TopC']) & (df['Open'] < df['H3'])
    bear_magnet = (df['Lower_Value']) & (df['Open'] < df['BotC']) & (df['Open'] > df['L3'])
    
    # 2. Camarilla Breakout:
    # Close today > H4 (Long) or < L4 (Short)
    bull_break = (df['Close'] > df['H4'])
    bear_break = (df['Close'] < df['L4'])

    results = []

    # Evaluate Magnets (Intraday reversion to pivot)
    # For Magnet, the 'Return' is (P - Open)/Open for shorts, (P - Open)/Open for longs? 
    # Actually Magnet is a reversal setup.
    # Bullish Magnet (Expect drop to P): Short at Open, Exit at P or EOD.
    # Bearish Magnet (Expect rise to P): Long at Open, Exit at P or EOD.
    
    # Bull Magnet Returns
    m_bull_trades = df[bull_magnet].copy()
    m_bull_trades['Success'] = m_bull_trades['Low'] <= m_bull_trades['P']
    # If success, return is (Open - P)/Open. If fail, return is (Open - Close)/Open (EOD exit)
    m_bull_trades['Ret'] = np.where(m_bull_trades['Success'], 
                                   (m_bull_trades['Open'] - m_bull_trades['P']) / m_bull_trades['Open'],
                                   (m_bull_trades['Open'] - m_bull_trades['Close']) / m_bull_trades['Open'])
    results.append({'Strategy': 'CPR Magnet (Bullish-Trend Reversion)', 'Trades': len(m_bull_trades), 
                    'Win Rate': round(m_bull_trades['Success'].mean()*100, 2), 
                    'Avg Return': round(m_bull_trades['Ret'].mean()*100, 2)})

    # Bear Magnet Returns
    m_bear_trades = df[bear_magnet].copy()
    m_bear_trades['Success'] = m_bear_trades['High'] >= m_bear_trades['P']
    m_bear_trades['Ret'] = np.where(m_bear_trades['Success'],
                                   (m_bear_trades['P'] - m_bear_trades['Open']) / m_bear_trades['Open'],
                                   (m_bear_trades['Close'] - m_bear_trades['Open']) / m_bear_trades['Open'])
    results.append({'Strategy': 'CPR Magnet (Bearish-Trend Reversion)', 'Trades': len(m_bear_trades), 
                    'Win Rate': round(m_bear_trades['Success'].mean()*100, 2), 
                    'Avg Return': round(m_bear_trades['Ret'].mean()*100, 2)})

    # Evaluate Camarilla Breakouts (Trend continuation)
    # Bull Break: Buy at close, hold 3 days
    b_bull_trades = df[bull_break].copy()
    b_bull_trades['Ret'] = b_bull_trades['Close'].shift(-3) / b_bull_trades['Close'] - 1
    results.append({'Strategy': 'Camarilla H4 Breakout (3-day Hold)', 'Trades': len(b_bull_trades),
                    'Win Rate': round((b_bull_trades['Ret'] > 0).mean()*100, 2),
                    'Avg Return': round(b_bull_trades['Ret'].mean()*100, 2)})

    b_bear_trades = df[bear_break].copy()
    b_bear_trades['Ret'] = 1 - b_bear_trades['Close'].shift(-3) / b_bear_trades['Close']
    results.append({'Strategy': 'Camarilla L4 Breakout (3-day Hold)', 'Trades': len(b_bear_trades),
                    'Win Rate': round((b_bear_trades['Ret'] > 0).mean()*100, 2),
                    'Avg Return': round(b_bear_trades['Ret'].mean()*100, 2)})

    res_df = pd.DataFrame(results)
    print("\n--- Pivot Boss Daily Strategy Results ---")
    print(res_df.to_string(index=False))
    
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    res_df.to_csv(RESULTS_PATH, index=False)
    print(f"\nResults saved to {RESULTS_PATH}")

if __name__ == '__main__':
    evaluate_pivot_daily()
