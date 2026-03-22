import pandas as pd
import numpy as np
from finding_alphas_engine import AlphaEngine
from alpha_setups import AlphaLibrary
import os

def run_101_backtest():
    data_path = "/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv"
    print(f"Reading data from {data_path}...")
    
    # Load data
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Filter for last 2 years to keep memory manageable for initial run
    max_date = df['Date'].max()
    start_date = max_date - pd.DateOffset(years=2)
    df = df[df['Date'] >= start_date]
    print(f"Processing {len(df)} rows of data from {start_date.date()} to {max_date.date()}")

    # Initialize Engine and Library
    engine = AlphaEngine(df)
    library = AlphaLibrary(engine)
    
    # Calculate Alphas
    alphas = library.calculate_all()
    
    results = []
    
    # Performance Calculation per Alpha
    for alpha_id, signals in alphas.items():
        # Shift signals by 1 day to prevent look-ahead bias
        positions = signals.shift(1).fillna(0)
        
        # Calculate returns
        daily_returns = engine.returns * positions
        
        # Performance Metrics (Mean Return over all tickers)
        strategy_returns = daily_returns.mean(axis=1) # Market Neutral equal weight
        
        total_return = (1 + strategy_returns).prod() - 1
        sharpe = np.sqrt(252) * strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() != 0 else 0
        
        results.append({
            'Alpha': alpha_id,
            'Total_Return': total_return,
            'Sharpe': sharpe
        })
        print(f"Alpha {alpha_id}: Return {total_return:.2%}, Sharpe {sharpe:.2f}")

    # Result Summary
    results_df = pd.DataFrame(results).sort_values('Sharpe', ascending=False)
    output_path = "/Users/rahulgirishkumar/TRADING/results/finding_alphas_results.csv"
    results_df.to_csv(output_path, index=False)
    
    print(f"\nAudit Complete. Results saved to {output_path}")
    print("\nTop 5 Alphas:")
    print(results_df.head())

if __name__ == "__main__":
    run_101_backtest()
