import pandas as pd
import numpy as np
import os

DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/results/ang_factors'
os.makedirs(RESULTS_DIR, exist_ok=True)

DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')

LOOKBACK = 252
SKIP = 21
REBALANCE = 21 # Monthly
TOP_N = 10

def run_backtest():
    print("Loading daily data...")
    df = pd.read_csv(DAILY_FILE)
    print(f"Columns: {df.columns.tolist()}")
    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date', 'Close'])
    print(f"Rows after dropna: {len(df)}")
    if len(df) == 0:
        print("ERROR: Dataframe is empty after dropna. Checking first 5 rows...")
        print(pd.read_csv(DAILY_FILE).head())
        return
    
    df['Date'] = df['Date'].dt.normalize()
    
    print("Sorting by date (numpy bypass)...")
    # Use numpy to get sort indices to bypass pandas sorting bug
    sort_idx = np.argsort(df['Date'].values)
    df = df.iloc[sort_idx].copy()
    
    # Get all unique trading dates
    all_dates = sorted(df['Date'].unique())
    print(f"Total Trading Days: {len(all_dates)}")
    print(f"Date Range: {all_dates[0]} to {all_dates[-1]}")
    
    # We will sample dates for rebalancing
    rebalance_dates = all_dates[LOOKBACK::REBALANCE]
    print(f"Rotation Periods: {len(rebalance_dates)}")

    # To make it fast, we'll pivot just the necessary columns
    print("Preparing data...")
    # Use a simple dictionary for fast lookup if pivot fails
    ticker_data = {}
    for ticker, group in df.groupby('Ticker'):
        # Just store as a Series with Date as index
        ticker_data[ticker] = group.set_index('Date')['Close']

    history = []
    
    for i in range(len(rebalance_dates) - 1):
        d_now = rebalance_dates[i]
        d_next = rebalance_dates[i+1]
        d_lookback = all_dates[all_dates.index(d_now) - LOOKBACK]
        d_skip = all_dates[all_dates.index(d_now) - SKIP]
        
        # Calculate momentum for all tickers at d_now
        mom_scores = {}
        for ticker, series in ticker_data.items():
            try:
                p_now = series.get(d_now)
                p_skip = series.get(d_skip)
                p_look = series.get(d_lookback)
                
                if p_look and p_skip and p_look > 0:
                    # 12-1 momentum
                    mom_scores[ticker] = (p_skip / p_look) - 1
            except:
                continue
        
        if len(mom_scores) < TOP_N: continue
        
        # Rank
        sorted_mom = sorted(mom_scores.items(), key=lambda x: x[1], reverse=True)
        top_10 = [x[0] for x in sorted_mom[:TOP_N]]
        
        # Calculate returns
        rets = []
        for ticker in top_10:
            try:
                p0 = ticker_data[ticker].get(d_now)
                p1 = ticker_data[ticker].get(d_next)
                if p0 and p1 and p0 > 0:
                    rets.append((p1/p0)-1)
                else:
                    rets.append(0.0)
            except:
                rets.append(0.0)
                
        month_ret = np.mean(rets)
        history.append({
            'Date': d_now,
            'EndDate': d_next,
            'Return': month_ret,
            'Tickers': ",".join(top_10)
        })

    if not history:
        print("No trades generated.")
        return

    res = pd.DataFrame(history)
    res['Cumulative'] = (1 + res['Return']).cumprod()
    
    total = res['Cumulative'].iloc[-1] - 1
    print(f"\n--- Andrew Ang Factor Results (Manual Iteration) ---")
    print(f"Total Return: {total:.2%}")
    print(f"Rotation Periods: {len(res)}")
    print(f"End Selection: {res['Tickers'].iloc[-1]}")
    
    res.to_csv(os.path.join(RESULTS_DIR, 'ang_results_final.csv'), index=False)

if __name__ == "__main__":
    run_backtest()
