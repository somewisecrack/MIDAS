import pandas as pd
import numpy as np
from tqdm import tqdm
import os
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = '/Users/rahulgirishkumar/TRADING/data/tickers_5m_ohlcv.csv'
RESULTS_PATH = '/Users/rahulgirishkumar/TRADING/results/wyckoff_vp_results.csv'

def calculate_vp(df):
    """
    Calculate prior session VAH, VAL, VPOC.
    To be fast, we use the Typical Price (H+L+C)/3 and assign volume to 50 bins.
    """
    if df.empty or df['volume'].sum() == 0:
        return pd.Series({'VPOC': np.nan, 'VAH': np.nan, 'VAL': np.nan})
        
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    # 50 bins between min TP and max TP
    min_tp = df['tp'].min()
    max_tp = df['tp'].max()
    
    if min_tp == max_tp:
        return pd.Series({'VPOC': min_tp, 'VAH': min_tp, 'VAL': min_tp})
        
    bins = np.linspace(min_tp, max_tp, 51)
    df['bin'] = pd.cut(df['tp'], bins=bins, labels=False, include_lowest=True)
    
    vol_profile = df.groupby('bin')['volume'].sum().sort_index()
    
    # Calculate VPOC
    vpoc_bin = vol_profile.idxmax()
    vpoc_price = bins[vpoc_bin] + (bins[vpoc_bin+1] - bins[vpoc_bin])/2
    
    # Calculate Value Area (70%)
    total_vol = vol_profile.sum()
    target_vol = total_vol * 0.70
    
    current_vol = vol_profile.loc[vpoc_bin] if vpoc_bin in vol_profile else 0
    upper_bin = vpoc_bin
    lower_bin = vpoc_bin
    
    while current_vol < target_vol:
        vol_up = vol_profile.loc[upper_bin + 1] if (upper_bin + 1) in vol_profile.index else 0
        vol_down = vol_profile.loc[lower_bin - 1] if (lower_bin - 1) in vol_profile.index else 0
        
        if vol_up == 0 and vol_down == 0:
            break
            
        if vol_up > vol_down:
            upper_bin += 1
            current_vol += vol_up
        else:
            lower_bin -= 1
            current_vol += vol_down
            
    vah_price = bins[upper_bin+1]
    val_price = bins[lower_bin]
    
    return pd.Series({'VPOC': vpoc_price, 'VAH': vah_price, 'VAL': val_price})

def run_backtest():
    print('Loading 5m data...')
    # Define dtypes to save memory
    dtypes = {
        'Ticker': 'category',
        'Open': 'float32',
        'High': 'float32',
        'Low': 'float32',
        'Close': 'float32',
        'Volume': 'float32'
    }
    df = pd.read_csv(DATA_PATH, dtype=dtypes, parse_dates=['Date'])
    df.columns = [c.lower() for c in df.columns]
    
    # After lowercasing, the column 'date' contains the datetime timestamps.
    df.rename(columns={'date': 'datetime'}, inplace=True)
    df['date'] = df['datetime'].dt.date
    df.sort_values(['ticker', 'datetime'], inplace=True)
    
    print('Calculating session volume profiles (this may take a few minutes)...')
    # Calculate daily profiles
    daily_vp = df.groupby(['ticker', 'date']).apply(calculate_vp).reset_index()
    
    # Shift profiles to next day for the 'Prior Session Profile'
    daily_vp['prev_VPOC'] = daily_vp.groupby('ticker')['VPOC'].shift(1)
    daily_vp['prev_VAH'] = daily_vp.groupby('ticker')['VAH'].shift(1)
    daily_vp['prev_VAL'] = daily_vp.groupby('ticker')['VAL'].shift(1)
    
    print('Merging profiles onto intraday data...')
    df = df.merge(daily_vp[['ticker', 'date', 'prev_VPOC', 'prev_VAH', 'prev_VAL']], on=['ticker', 'date'], how='left')
    
    print('Generating Reversion Signals...')
    # Spring (Long): Price goes below prev_VAL but closes above prev_VAL
    df['long_signal'] = (df['low'] < df['prev_VAL']) & (df['close'] > df['prev_VAL'])
    
    # Upthrust (Short): Price goes above prev_VAH but closes below prev_VAH
    df['short_signal'] = (df['high'] > df['prev_VAH']) & (df['close'] < df['prev_VAH'])
    
    # Simple holding logic: Evaluate exit at the end of the day or if target/stop is hit.
    # To vectorize simply: 
    # Entry at next bar's open. 
    # Exit at the same day's close for a basic intraday daytrading model.
    # We will compute forward returns to the end of the day.
    
    # Calculate EOD close for each date
    eod_close = df.groupby(['ticker', 'date'])['close'].last().reset_index()
    eod_close.rename(columns={'close': 'eod_close'}, inplace=True)
    df = df.merge(eod_close, on=['ticker', 'date'], how='left')
    
    # Shift open by -1 to get entry price
    df['entry_price'] = df.groupby('ticker')['open'].shift(-1)
    # Require entry to be on the same date
    df['next_date'] = df.groupby('ticker')['date'].shift(-1)
    df = df[df['date'] == df['next_date']] # valid intraday entries only
    
    df['long_return'] = np.where(df['long_signal'], (df['eod_close'] - df['entry_price']) / df['entry_price'], 0)
    df['short_return'] = np.where(df['short_signal'], (df['entry_price'] - df['eod_close']) / df['entry_price'], 0)
    
    # Aggregate results
    long_trades = df[df['long_signal']].copy()
    short_trades = df[df['short_signal']].copy()
    
    print(f'Total Long Reversion Trades: {len(long_trades)}')
    print(f'Total Short Reversion Trades: {len(short_trades)}')
    
    all_trades = pd.concat([
        pd.DataFrame({'ticker': long_trades['ticker'], 'type': 'LONG', 'return': long_trades['long_return']}),
        pd.DataFrame({'ticker': short_trades['ticker'], 'type': 'SHORT', 'return': short_trades['short_return']})
    ])
    
    if len(all_trades) == 0:
        print('No trades generated.')
        return
        
    summary = []
    tickers = all_trades['ticker'].unique()
    for t in tqdm(tickers, desc='Formatting summary'):
        t_trades = all_trades[all_trades['ticker'] == t]
        trades_count = len(t_trades)
        if trades_count == 0: continue
        win_rate = len(t_trades[t_trades['return'] > 0]) / trades_count
        avg_ret = t_trades['return'].mean()
        tot_ret = t_trades['return'].sum()
        summary.append({
            'strategy': 'Wyckoff_VP_Reversion',
            'ticker': t,
            'Total Return': tot_ret,
            'Win Rate': win_rate,
            'Trades': trades_count,
            'Avg Trade': avg_ret
        })
        
    res_df = pd.DataFrame(summary)
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    res_df.to_csv(RESULTS_PATH, index=False)
    print(f'Results saved to {RESULTS_PATH}')
    
    print("\n--- Strategy Performance Summary ---")
    print(res_df.mean(numeric_only=True))

if __name__ == '__main__':
    run_backtest()
