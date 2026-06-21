import pandas as pd
import numpy as np
import os
from tqdm import tqdm

# Constants
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/results/'
TICKERS_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')
SPY_FILE = os.path.join(DATA_DIR, 'SPY_ohlcv.csv')

def load_data():
    print("Loading data...")
    df = pd.read_csv(TICKERS_FILE)
    df['Date'] = pd.to_datetime(df['Date'])
    spy = pd.read_csv(SPY_FILE)
    spy['Date'] = pd.to_datetime(spy['Date'])
    spy = spy.rename(columns={'Close': 'SPY_Close'})
    return df, spy[['Date', 'SPY_Close']]

def calculate_technical_vitals(group):
    group = group.sort_values('Date').copy()
    
    # Moving Averages
    group['SMA50'] = group['Close'].rolling(window=50).mean()
    group['SMA150'] = group['Close'].rolling(window=150).mean()
    group['SMA200'] = group['Close'].rolling(window=200).mean()
    group['SMA200_slope'] = (group['SMA200'] - group['SMA200'].shift(20)) > 0
    
    # 52-Week Ranges
    group['Low_52w'] = group['Low'].rolling(window=252).min()
    group['High_52w'] = group['High'].rolling(window=252).max()
    
    # Trend Template
    c1 = (group['Close'] > group['SMA150']) & (group['Close'] > group['SMA200'])
    c2 = group['SMA150'] > group['SMA200']
    c3 = group['SMA200_slope']
    c4 = (group['SMA50'] > group['SMA150']) & (group['SMA50'] > group['SMA200'])
    c5 = group['Close'] > group['SMA50']
    c6 = group['Close'] >= (group['Low_52w'] * 1.30)
    c7 = group['Close'] >= (group['High_52w'] * 0.75)
    group['Trend_Template'] = c1 & c2 & c3 & c4 & c5 & c6 & c7
    
    # Volatility / ATR
    high_low = group['High'] - group['Low']
    tr = pd.concat([high_low, (group['High'] - group['Close'].shift(1)).abs()], axis=1).max(axis=1)
    group['ATR20'] = tr.rolling(window=20).mean()
    group['Vol_Ratio'] = group['ATR20'] / group['Close']
    group['Tightness'] = group['Vol_Ratio'] < group['Vol_Ratio'].rolling(window=60).quantile(0.25)
    
    # Performance Proxies
    group['Pct_Change_40'] = (group['Close'] / group['Close'].shift(40)) - 1
    
    return group

def detect_setups(row, prev_row, group_slice):
    """
    Classifies the trade setup type based on historical price action in the group slice.
    """
    # 1. Power Play (High Tight Flag)
    # 100% price increase in < 8 weeks (approx 40 days)
    # Consolidation < 25%, duration 3-6 weeks
    if row['Pct_Change_40'] >= 0.8: # Adjusted to 80% to be slightly more inclusive for audit
        # Check flag depth in the last 20 days
        flag_high = group_slice['High'].max()
        flag_low = group_slice['Low'].min()
        flag_depth = (flag_high - flag_low) / flag_high
        if flag_depth < 0.25:
            return "Power Play"

    # Standard SEPA Setups (Must meet Trend Template)
    if not row['Trend_Template']:
        return None
    
    # Analyze Base Structure (Last 60 days)
    base_high = group_slice['High'].max()
    base_low = group_slice['Low'].min()
    base_depth = (base_high - base_low) / base_high
    
    # The Cheat (Breakout in mid-base)
    # If price is breaking above a local high but still 15% below the 52w High
    if row['Close'] > prev_row['High'] and row['Close'] < (row['High_52w'] * 0.9):
        return "The Cheat"

    if base_depth < 0.15:
        return "Flat Base / Box"
    elif base_depth < 0.40:
        return "Cup with Handle / Saucer"
    else:
        return "Deep VCP Base"

def run_comprehensive_backtest():
    df, spy = load_data()
    tickers = df['Ticker'].unique()
    results = []
    
    print("Auditing 8 Minervini Setups...")
    for ticker in tqdm(tickers):
        group = df[df['Ticker'] == ticker].copy()
        if len(group) < 252: continue
        
        group = calculate_technical_vitals(group)
        group = pd.merge(group, spy, on='Date', how='left')
        
        in_trade = False
        entry_price = 0
        entry_date = None
        stop_loss = 0
        current_setup = None
        
        for i in range(60, len(group)):
            row = group.iloc[i]
            prev_row = group.iloc[i-1]
            
            if not in_trade:
                # Screen for setup
                setup_type = detect_setups(row, prev_row, group.iloc[i-60:i])
                
                # Entry: Setup detected + Pivot Breakout (Close > Prev High)
                if setup_type and row['Close'] > prev_row['High']:
                    in_trade = True
                    entry_price = row['Close']
                    entry_date = row['Date']
                    current_setup = setup_type
                    stop_loss = entry_price * 0.93 # 7% Hard Stop
            else:
                pnl = (row['Close'] / entry_price) - 1
                exit_signal = False
                exit_reason = ""
                
                # EXIT RULES
                if row['Low'] <= stop_loss:
                    exit_signal = True
                    exit_reason = "Stopped Out"
                    exit_price = stop_loss
                elif pnl >= 0.20:
                    # Move stop to breakeven or trail
                    stop_loss = max(stop_loss, entry_price)
                    if row['Close'] < row['SMA50']:
                        exit_signal = True
                        exit_reason = "SMA50 Trail"
                        exit_price = row['Close']
                elif row['Date'] > entry_date + pd.Timedelta(days=90):
                    exit_signal = True
                    exit_reason = "Time Exit"
                    exit_price = row['Close']

                if exit_signal:
                    results.append({
                        'Ticker': ticker,
                        'Entry Date': entry_date,
                        'Exit Date': row['Date'],
                        'Setup': current_setup,
                        'Return': (exit_price / entry_price) - 1,
                        'Price Range': 'Low' if entry_price < 20 else ('Mid' if entry_price < 100 else 'High')
                    })
                    in_trade = False

    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df['Year'] = pd.to_datetime(results_df['Exit Date']).dt.year
        results_df.to_csv(os.path.join(RESULTS_DIR, 'minervini_comprehensive_trades.csv'), index=False)
        
        # Summary 1: By Setup
        setup_summary = results_df.groupby('Setup')['Return'].agg(['count', 'mean', 'sum']).reset_index()
        print("\nSummary by Setup:")
        print(setup_summary)
        setup_summary.to_csv(os.path.join(RESULTS_DIR, 'summary_by_setup.csv'), index=False)
        
        # Summary 2: By Price Range
        price_summary = results_df.groupby('Price Range')['Return'].agg(['count', 'mean', 'sum']).reset_index()
        print("\nSummary by Price Range:")
        print(price_summary)
        price_summary.to_csv(os.path.join(RESULTS_DIR, 'summary_by_price.csv'), index=False)
    else:
        print("No trades found.")

if __name__ == "__main__":
    run_comprehensive_backtest()
