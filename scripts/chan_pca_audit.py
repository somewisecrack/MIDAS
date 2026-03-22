import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

def run_chan_pca_audit(data_path, lookback=252, num_factors=5, top_n=50):
    print("Loading data...")
    df = pd.read_csv(data_path)
    print(f"Initial row count: {len(df)}")
    
    # Keep as datetime and NORMALIZE to remove intraday time components
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()
    df = df.dropna(subset=['Date', 'Close', 'Ticker'])
    
    # Deduplicate based on NORMALISED date and Ticker
    print("Deduplicating and pivoting...")
    df = df.drop_duplicates(['Date', 'Ticker'])
    
    # Use unstack to broaden the dataframe
    prices = df.set_index(['Date', 'Ticker'])['Close'].unstack()
    prices = prices.sort_index().ffill()
    
    # Force index uniqueness if somehow set_index didn't do it
    if prices.index.duplicated().any():
        print(f"Duplicates found in index! Count: {prices.index.duplicated().sum()}")
        prices = prices[~prices.index.duplicated(keep='first')]
        
    returns = prices.pct_change().dropna(how='all')
    print(f"Returns matrix shape: {returns.shape}")
    print(f"Index unique: {returns.index.is_unique}")
    print(f"Unique dates in returns: {len(returns.index)}")
    
    # Verify we didn't collapse the index again
    if len(returns.index) < 10:
        print(f"CRITICAL: Index still collapsed! Length: {len(returns.index)}")
        print(f"Sample index: {returns.index[:5]}")
        return
    
    dates = returns.index
    num_stocks = returns.shape[1]
    
    # Initialize results series using the actual return dates index
    strat_returns = pd.Series(0.0, index=dates, dtype=float)
    
    print(f"Running rolling PCA audit (Lookback: {lookback}, Factors: {num_factors})...")
    
    counts = []
    for t in tqdm(range(lookback, len(dates) - 1)):
        # t is the index for current_date (end of window)
        current_date = dates[t]
        next_date = dates[t+1]
        
        # Window: [t-lookback : t] (lookback+1 rows)
        window_rets = returns.loc[dates[t-lookback]:current_date]
        
        # Clean stocks in window
        valid_stocks = window_rets.columns[window_rets.notna().all()]
        counts.append(len(valid_stocks))
        
        if len(valid_stocks) < 2 * top_n:
            continue
            
        R = window_rets[valid_stocks]
        
        try:
            # 1. Extract Statistical Factors
            pca = PCA(n_components=num_factors)
            factors = pca.fit_transform(R) # (lookback + 1, num_factors)
            
            # 2. Predictive Regression: R[i] ~ Factors[i-1]
            X_train = factors[:-1]
            y_train = R.values[1:] 
            
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            # 3. Forecast Tomorrow's Returns
            current_factors = factors[-1].reshape(1, -1)
            pred_rets = model.predict(current_factors).flatten()
            
            # 4. Signal Generation (Ranking)
            res = pd.Series(pred_rets, index=valid_stocks)
            res = res.sort_values()
            
            shorts = res.head(top_n).index
            longs = res.tail(top_n).index
            
            # 5. Calculate Realized Return for T+1
            realized_rets = returns.loc[next_date]
            
            buy_ret = realized_rets.reindex(longs).fillna(0).mean()
            sell_ret = realized_rets.reindex(shorts).fillna(0).mean()
            
            daily_ret = (buy_ret - sell_ret) / 2.0
            strat_returns.loc[next_date] = daily_ret
            
        except Exception as e:
            continue
            
    # Performance Evaluation
    non_zero = strat_returns[strat_returns != 0]
    print(f"\nAverage valid stocks per window: {np.mean(counts) if counts else 0:.2f}")
    print(f"Non-zero return days: {len(non_zero)}")
    
    if len(non_zero) > 0:
        print(f"Mean daily return (trading days): {non_zero.mean():.6f}")
        
        # Calculate CAGR using product of (1 + r)
        valid_strat_rets = strat_returns.fillna(0)
        cum_ret = (1 + valid_strat_rets).prod()
        print(f"Total Cumulative Return: {cum_ret:.6f}")
        
        # Number of years in backtest
        num_years = len(strat_returns) / 252.0
        cagr = (cum_ret ** (1.0 / num_years)) - 1
        vol = valid_strat_rets.std() * np.sqrt(252)
        sharpe = (valid_strat_rets.mean() * 252) / vol if vol > 0 else 0
        
        print("\n--- PCA Audit Results ---")
        print(f"CAGR: {cagr:.2%}")
        print(f"Sharpe: {sharpe:.2f}")
    else:
        print("\nNo trades executed or all returns were exactly zero.")
    
    # Save results
    strat_returns.to_csv('chan_pca_audit_returns.csv')
    
if __name__ == "__main__":
    run_chan_pca_audit('/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv')
