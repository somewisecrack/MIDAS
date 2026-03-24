import pandas as pd
import numpy as np
import statsmodels.api as sm
from tqdm import tqdm
import os
from datetime import datetime

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/results/4factor/'
TICKERS_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')

if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

def calculate_factors(df):
    """Calculate the 4 factors for the model."""
    print("Calculating factors...")
    
    # Sort chronologically
    df = df.sort_values(by=['Ticker', 'Date']).reset_index(drop=True)
    
    # prc: log(unadjusted close)
    df['prc'] = np.log(df['Close']).groupby(df['Ticker']).shift(1)
    
    # mom: log(unadjusted close / unadjusted open)
    df['mom'] = np.log(df['Close'] / df['Open']).groupby(df['Ticker']).shift(1)
    
    # hlv: intraday volatility over 21 days
    hl_sq = ((df['High'] - df['Low']) / df['Close']) ** 2
    U_is = hl_sq.groupby(df['Ticker']).rolling(window=21).mean().reset_index(level=0, drop=True)
    df['hlv'] = (0.5 * np.log(U_is)).groupby(df['Ticker']).shift(1)
    
    # vol: volume over 21 days
    V_is = df['Volume'].groupby(df['Ticker']).rolling(window=21).mean().reset_index(level=0, drop=True)
    df['vol'] = np.log(V_is).groupby(df['Ticker']).shift(1)
    
    # Calculate Overnight Return R_{t+1}
    # R_{t+1} = ln(Open_{t+1} / Close_{t})
    df['Prev_Close'] = df.groupby('Ticker')['Close'].shift(1)
    df['Overnight_Ret'] = np.log(df['Open'] / df['Prev_Close'])
    
    # Intraday return for PnL calculation
    df['Intraday_Ret'] = (df['Close'] / df['Open']) - 1
    
    # Volume for liquidity filtering
    df['ADDV_21'] = (df['Volume'] * df['Close']).groupby(df['Ticker']).rolling(window=21).mean().reset_index(level=0, drop=True)
    
    return df.dropna(subset=['prc', 'mom', 'hlv', 'vol', 'Overnight_Ret', 'Intraday_Ret', 'ADDV_21'])

def normalize(series):
    """Normalize a series to N(0, sd) cross-sectionally."""
    sd = series.std()
    mean = series.mean()
    if pd.isna(sd) or sd == 0:
        return series - mean
    return (series - mean) # The paper normalizes to N(0, sd). Let's just mean center and scale if desired.
    # The paper says "conforming them to a normal distribution with zero mean and standard deviation equal to the 
    # standard deviation of the unnormalized factor beta."
    # A standard cross-sectional z-score (scaled by sd) would make standard deviation 1.
    # To keep same sd, we just mean center or rank-normalize to a normal distribution.
    # For simplicity, we just mean center (z-score * sd is just mean centering).

def run_backtest(df, top_n=1000):
    print(f"Running backtest on top {top_n} liquid stocks...")
    dates = sorted(df['Date'].unique())
    
    pnl_history = []
    
    for date in tqdm(dates):
        daily_df = df[df['Date'] == date].copy()
        
        # Select top N by ADDV
        if len(daily_df) > top_n:
            daily_df = daily_df.nlargest(top_n, 'ADDV_21')
            
        if len(daily_df) < 50:
            pnl_history.append({'Date': date, 'PnL': 0.0, 'Traded_Shares': 0})
            continue
            
        # Target
        Y = daily_df['Overnight_Ret']
        
        # Factors
        X = daily_df[['prc', 'mom', 'hlv', 'vol']]
        
        # Normalize hlv and vol cross-sectionally
        X.loc[:, 'hlv'] = X['hlv'] - X['hlv'].mean()
        X.loc[:, 'vol'] = X['vol'] - X['vol'].mean()
        
        X = sm.add_constant(X)
        
        try:
            model = sm.OLS(Y, X).fit()
            residuals = model.resid
            
            # Normalize residuals cross-sectionally
            eps = residuals - residuals.mean()
            
            # Holdings
            total_abs_eps = np.abs(eps).sum()
            if total_abs_eps == 0:
                continue
                
            I_dollar = 10000000  # $10M total investment level
            H = -eps * (I_dollar / total_abs_eps)
            
            # PnL per stock
            pnl_series = H * daily_df['Intraday_Ret']
            shares_series = np.abs(H) * 2 / daily_df['Open']
            price_series = daily_df['Open']
            
            # Bucketing
            for b_name, b_mask in [
                ('<$5', price_series < 5),
                ('$5-$20', (price_series >= 5) & (price_series < 20)),
                ('$20-$100', (price_series >= 20) & (price_series < 100)),
                ('>$100', price_series >= 100)
            ]:
                b_pnl = pnl_series[b_mask].sum()
                b_shares = shares_series[b_mask].sum()
                b_inv = np.abs(H[b_mask]).sum() # total gross investment in this bucket
                pnl_history.append({
                    'Date': date,
                    'Bucket': b_name,
                    'PnL': b_pnl,
                    'Traded_Shares': b_shares,
                    'Gross_Inv': b_inv
                })
            
            # Total PnL for Sharpe calculation
            daily_pnl = pnl_series.sum()
            pnl_history.append({
                'Date': date,
                'Bucket': 'Total',
                'PnL': daily_pnl,
                'Traded_Shares': shares_series.sum(),
                'Gross_Inv': I_dollar
            })
            
        except Exception as e:
            pass
            
    pnl_df = pd.DataFrame(pnl_history)
    
    print(f"\n--- Results for Top {top_n} ---")
    
    for bucket in ['Total', '<$5', '$5-$20', '$20-$100', '>$100']:
        b_df = pnl_df[pnl_df['Bucket'] == bucket].groupby('Date').sum().reset_index()
        
        avg_daily_inv = b_df['Gross_Inv'].mean()
        if avg_daily_inv == 0:
            continue
            
        annual_pnl = b_df['PnL'].mean() * 252
        roc = annual_pnl / avg_daily_inv
        
        daily_returns = b_df['PnL'] / b_df['Gross_Inv'].replace(0, np.nan)
        sr = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        total_pnl = b_df['PnL'].sum()
        total_shares = b_df['Traded_Shares'].sum()
        cps = total_pnl / total_shares if total_shares > 0 else 0
        
        print(f"[{bucket}] ROC: {roc:.2%} | SR: {sr:.2f} | CPS: ${cps:.4f}")
    
    pnl_df.to_csv(os.path.join(RESULTS_DIR, f'4factor_pnl_top{top_n}.csv'), index=False)
    
    return roc, sr, cps

def main():
    print("Loading data...")
    df = pd.read_csv(TICKERS_FILE, parse_dates=['Date'])
    
    # Convert timezone if needed
    if df['Date'].dt.tz is not None:
        df['Date'] = df['Date'].dt.tz_localize(None)
    
    df = calculate_factors(df)
    
    run_backtest(df, top_n=1000)
    run_backtest(df, top_n=2000)

if __name__ == "__main__":
    main()
