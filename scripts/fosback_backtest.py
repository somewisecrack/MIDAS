import pandas as pd
import numpy as np
import os

def normalize_date(df):
    """Ensures Date column is in consistent YYYY-MM-DD string format."""
    df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.strftime('%Y-%m-%d')
    return df

def run_fosback_backtest():
    breadth_path = "/Users/rahulgirishkumar/TRADING/results/fosback_analysis.csv"
    spy_path = "/Users/rahulgirishkumar/TRADING/data/SPY_ohlcv.csv"
    yield_path = "/Users/rahulgirishkumar/TRADING/data/SPY_yield.csv"
    
    # Load and Normalize Data
    print("Loading datasets...")
    breadth = pd.read_csv(breadth_path)
    breadth = normalize_date(breadth)
    print(f"Breadth data: {len(breadth)} rows, Date range: {breadth['Date'].min()} to {breadth['Date'].max()}")
    
    spy = pd.read_csv(spy_path)
    spy = normalize_date(spy)
    print(f"SPY price data: {len(spy)} rows, Date range: {spy['Date'].min()} to {spy['Date'].max()}")
    
    yields = pd.read_csv(yield_path)
    yields = normalize_date(yields)
    print(f"SPY yield data: {len(yields)} rows, Date range: {yields['Date'].min()} to {yields['Date'].max()}")
    
    # Merge Step 1: Benchmarks
    print("\nMerging datasets...")
    data = pd.merge(spy[['Date', 'Close']], yields[['Date', 'Yield']], on='Date', how='inner')
    print(f"After SPY-Yield merge: {len(data)} rows")
    
    # Merge Step 2: Breadth
    data = pd.merge(data, breadth[['Date', 'HLLI', 'ABI_Ratio', 'Bearish_Divergence', 'Bullish_Panic']], on='Date', how='inner')
    print(f"After Breadth merge: {len(data)} rows")
    
    if len(data) == 0:
        print("CRITICAL ERROR: Merged dataset is empty. Check overlapping date ranges.")
        return
        
    data = data.sort_values('Date').dropna(subset=['Close'])
    
    # --- Strategy Logic ---
    # Entry: Bullish Panic (ABI > 40%) OR High Yield (Top 25% of history to that point)
    data['Yield_Threshold'] = data['Yield'].expanding().quantile(0.75)
    data['Bullish_Signal'] = (data['Bullish_Panic'] == 'True') | (data['Bullish_Panic'] == True) | (data['Yield'] > data['Yield_Threshold'])
    
    # Exit: Bearish Divergence (HLLI > 5%) OR Low Yield (Bottom 25% of history)
    data['Low_Yield_Threshold'] = data['Yield'].expanding().quantile(0.25)
    data['Bearish_Signal'] = (data['Bearish_Divergence'] == 'True') | (data['Bearish_Divergence'] == True) | (data['Yield'] < data['Low_Yield_Threshold'])
    
    # Position Management
    position = 0
    signals = []
    
    for i, row in data.iterrows():
        if row['Bullish_Signal']:
            position = 1
        elif row['Bearish_Signal']:
            position = 0
        signals.append(position)
    
    data['Position'] = signals
    
    # --- Performance Calculation ---
    data['Market_Return'] = data['Close'].pct_change()
    data['Strategy_Return'] = data['Market_Return'] * data['Position'].shift(1)
    
    data['Market_Cum'] = (1 + data['Market_Return'].fillna(0)).cumprod()
    data['Strategy_Cum'] = (1 + data['Strategy_Return'].fillna(0)).cumprod()
    
    # Metrics
    total_return = data['Strategy_Cum'].iloc[-1] - 1
    market_return = data['Market_Cum'].iloc[-1] - 1
    
    sharpe = np.sqrt(252) * data['Strategy_Return'].mean() / data['Strategy_Return'].std()
    market_sharpe = np.sqrt(252) * data['Market_Return'].mean() / data['Market_Return'].std()
    
    print("\n--- Fosback Stock Market Logic Backtest Results ---")
    print(f"Period: {data['Date'].min()} to {data['Date'].max()}")
    print(f"Strategy Total Return: {total_return:.2%}")
    print(f"Market (SPY) Total Return: {market_return:.2%}")
    print(f"Strategy Sharpe Ratio: {sharpe:.2f}")
    print(f"Market Sharpe Ratio: {market_sharpe:.2f}")
    
    # Save results
    output_path = "/Users/rahulgirishkumar/TRADING/results/fosback_backtest_results.csv"
    data.to_csv(output_path, index=False)
    print(f"\nDetailed results saved to {output_path}")

if __name__ == "__main__":
    run_fosback_backtest()
