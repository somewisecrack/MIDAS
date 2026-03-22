import pandas as pd
import numpy as np
import os
from tqdm import tqdm

def calculate_fosback_indicators(df, window=252):
    """
    Implements Norman Fosback's 'Stock Market Logic' indicators.
    - HLLI: High-Low Logic Index
    - ABI: Absolute Breadth Index
    """
    # Ensure Date is datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Sort for rolling calculations
    df = df.sort_values(['Ticker', 'Date'])
    
    print("Calculating Advancing/Declining Status...")
    df['PrevClose'] = df.groupby('Ticker')['Close'].shift(1)
    df['IsAdvance'] = df['Close'] > df['PrevClose']
    df['IsDecline'] = df['Close'] < df['PrevClose']
    
    print(f"Calculating {window}-day Highs and Lows...")
    # Using window to identify new extreme highs/lows
    df['Rolling_High'] = df.groupby('Ticker')['High'].transform(lambda x: x.rolling(window=window, min_periods=window).max())
    df['Rolling_Low'] = df.groupby('Ticker')['Low'].transform(lambda x: x.rolling(window=window, min_periods=window).min())
    
    df['IsNewHigh'] = df['High'] >= df['Rolling_High']
    df['IsNewLow'] = df['Low'] <= df['Rolling_Low']
    
    print("Aggregating Market Breadth Data...")
    breadth = df.groupby('Date').agg(
        Advances=('IsAdvance', 'sum'),
        Declines=('IsDecline', 'sum'),
        NewHighs=('IsNewHigh', 'sum'),
        NewLows=('IsNewLow', 'sum'),
        TotalIssues=('Ticker', 'nunique')
    ).reset_index()
    
    # --- Fosback's High-Low Logic Index (HLLI) ---
    # Formula: min(New Highs, New Lows) / Total Issues
    # Note: Traditional threshold > 5% as a major warning.
    breadth['HLLI'] = breadth[['NewHighs', 'NewLows']].min(axis=1) / breadth['TotalIssues']
    
    # --- Absolute Breadth Index (ABI) ---
    # Formula: |Advances - Declines|
    # Note: High values signal panic/bottoms.
    breadth['ABI'] = (breadth['Advances'] - breadth['Declines']).abs()
    breadth['ABI_Ratio'] = breadth['ABI'] / breadth['TotalIssues']
    
    # --- Absolute Breadth Thrust Proxy ---
    breadth['ABI_MA_10'] = breadth['ABI_Ratio'].rolling(10).mean()
    
    return breadth

def generate_signals(breadth):
    """
    Generates actionable signals based on Fosback's thresholds.
    """
    signals = breadth.copy()
    
    # Bearish Signal: Extreme Divergence (HLLI > 5%)
    signals['Bearish_Divergence'] = signals['HLLI'] > 0.05
    
    # Bullish Signal: Breadth Panic (ABI_Ratio > 40%)
    signals['Bullish_Panic'] = signals['ABI_Ratio'] > 0.40
    
    return signals

if __name__ == "__main__":
    INPUT_PATH = "/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv"
    OUTPUT_PATH = "/Users/rahulgirishkumar/TRADING/results/fosback_analysis.csv"
    
    if not os.path.exists(INPUT_PATH):
        print(f"Error: {INPUT_PATH} not found.")
    else:
        print(f"Loading data from {INPUT_PATH}...")
        df = pd.read_csv(INPUT_PATH)
        
        # Filter for recent years if needed to speed up, otherwise process all
        # df = df[pd.to_datetime(df['Date']).dt.year >= 2021]
        
        indicators = calculate_fosback_indicators(df)
        signals = generate_signals(indicators)
        
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        signals.to_csv(OUTPUT_PATH, index=False)
        print(f"Fosback indicators and signals saved to {OUTPUT_PATH}")
        
        # Summary of triggered signals
        print("\nSignal Trigger Summary:")
        print(f"Bearish High-Low Divergence instances: {signals['Bearish_Divergence'].sum()}")
        print(f"Bullish Breadth Panic instances: {signals['Bullish_Panic'].sum()}")
        
        print("\nRecent Indicators & Signals:")
        print(signals.tail(10)[['Date', 'HLLI', 'ABI_Ratio', 'Bearish_Divergence', 'Bullish_Panic']])
