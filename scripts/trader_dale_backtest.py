import pandas as pd
import numpy as np
import os
from tqdm import tqdm

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/results/trader_dale'
os.makedirs(RESULTS_DIR, exist_ok=True)

INTRADAY_5M_FILE = os.path.join(DATA_DIR, 'tickers_5m_ohlcv.csv')
DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')

# Parameters
TOP_N_TICKERS = 50
POC_BINS = 50 
VOLUME_SPIKE_THRESHOLD = 1.5 # Volume/ADV
STOP_LOSS_ATR = 1.5
TAKE_PROFIT_ATR = 3.0

def calculate_vwap(df):
    """Calculate anchored VWAP for each day."""
    df['Date'] = pd.to_datetime(df['Date'])
    df['Day'] = df['Date'].dt.date
    
    # VWAP = sum(Price * Volume) / sum(Volume)
    df['PV'] = df['Close'] * df['Volume']
    grouped = df.groupby(['Ticker', 'Day'])
    df['Cum_PV'] = grouped['PV'].cumsum()
    df['Cum_Vol'] = grouped['Volume'].cumsum()
    df['VWAP'] = df['Cum_PV'] / df['Cum_Vol']
    return df

def calculate_poc(df, window=50):
    """Calculate the Point of Control (POC) for a rolling window of 5m bars."""
    # This is compute intensive. Let's simplify.
    # POC is the price level with maximum volume. 
    # We'll use a 20-bar lookback (approx 1.5h) to identify 'local' POCs.
    pass

def run_backtest():
    print("Loading daily data to find liquid tickers...")
    daily_df = pd.read_csv(DAILY_FILE)
    liquidity = daily_df.groupby('Ticker')['Volume'].mean() * daily_df.groupby('Ticker')['Close'].mean()
    top_tickers = liquidity.sort_values(ascending=False).head(TOP_N_TICKERS).index.tolist()
    
    print(f"Loading 5m data for {len(top_tickers)} tickers...")
    # Read in chunks to manage memory
    chunks = pd.read_csv(INTRADAY_5M_FILE, chunksize=100000)
    df_list = []
    for chunk in chunks:
        df_list.append(chunk[chunk['Ticker'].isin(top_tickers)])
    df = pd.concat(df_list)
    
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(['Ticker', 'Date'])
    
    print("Calculating VWAP...")
    df = calculate_vwap(df)
    
    all_trades = []
    
    for ticker in tqdm(top_tickers, desc="Backtesting Tickers"):
        ticker_df = df[df['Ticker'] == ticker].copy()
        ticker_df['ATR'] = calculate_atr(ticker_df)
        
        pos = 0 # 1: Long, -1: Short
        entry_price = 0
        sl = 0
        tp = 0
        
        # Trader Dale Setups:
        # A. VWAP Rejection: Price hits VWAP and shows rejection candle
        # B. POC (Local HVN) Pullback: Harder to automate without a full profile engine, 
        #    but we can look for high-volume consolidation zones.
        
        for i in range(2, len(ticker_df)):
            row = ticker_df.iloc[i]
            prev = ticker_df.iloc[i-1]
            
            # Simple VWAP Rejection Strategy:
            # 1. Price is above VWAP (uptrending intraday)
            # 2. Price pulls back to VWAP
            # 3. Candle rejects VWAP (Low < VWAP, Close > VWAP) with Volume spike
            
            if pos == 0:
                # Long Setup (VWAP Support)
                if row['Low'] <= row['VWAP'] < row['Close'] and row['Volume'] > VOLUME_SPIKE_THRESHOLD * ticker_df['Volume'].rolling(20).mean().iloc[i]:
                    pos = 1
                    entry_price = row['Close']
                    sl = entry_price - (STOP_LOSS_ATR * row['ATR'])
                    tp = entry_price + (TAKE_PROFIT_ATR * row['ATR'])
                    entry_date = row['Date']
                
                # Short Setup (VWAP Resistance)
                elif row['High'] >= row['VWAP'] > row['Close'] and row['Volume'] > VOLUME_SPIKE_THRESHOLD * ticker_df['Volume'].rolling(20).mean().iloc[i]:
                    pos = -1
                    entry_price = row['Close']
                    sl = entry_price + (STOP_LOSS_ATR * row['ATR'])
                    tp = entry_price - (TAKE_PROFIT_ATR * row['ATR'])
                    entry_date = row['Date']
                    
            else:
                # Exit Logic
                if pos == 1:
                    if row['High'] >= tp:
                        ret = (tp - entry_price) / entry_price
                        all_trades.append({'Ticker': ticker, 'Entry': entry_date, 'Exit': row['Date'], 'Type': 'Long', 'Return': ret})
                        pos = 0
                    elif row['Low'] <= sl:
                        ret = (sl - entry_price) / entry_price
                        all_trades.append({'Ticker': ticker, 'Entry': entry_date, 'Exit': row['Date'], 'Type': 'Long', 'Return': ret})
                        pos = 0
                elif pos == -1:
                    if row['Low'] <= tp:
                        ret = (entry_price - tp) / entry_price
                        all_trades.append({'Ticker': ticker, 'Entry': entry_date, 'Exit': row['Date'], 'Type': 'Short', 'Return': ret})
                        pos = 0
                    elif row['High'] >= sl:
                        ret = (entry_price - sl) / entry_price
                        all_trades.append({'Ticker': ticker, 'Entry': entry_date, 'Exit': row['Date'], 'Type': 'Short', 'Return': ret})
                        pos = 0
                        
        # End of session force close? Not for now, let it ride.
        
    if all_trades:
        results_df = pd.DataFrame(all_trades)
        
        # Add Price Category
        avg_prices = daily_df.groupby('Ticker')['Close'].mean()
        def get_cat(p):
            if p < 5: return 'Penny (<$5)'
            if p < 20: return 'Low ($5-$20)'
            if p < 100: return 'Mid ($20-$100)'
            return 'High (>$100)'
            
        results_df['Price'] = results_df['Ticker'].map(avg_prices)
        results_df['Category'] = results_df['Price'].apply(get_cat)
        
        print(f"\n--- Trader Dale Strategy Summary ---")
        print(f"Total Trades: {len(results_df)}")
        print(f"Win Rate: {(results_df['Return'] > 0).mean():.2%}")
        print(f"Average Return: {results_df['Return'].mean():.2%}")
        
        print("\n--- Performance by Price Category ---")
        cat_summary = results_df.groupby('Category').agg({
            'Return': ['count', 'mean', 'sum'],
            'Ticker': 'nunique'
        })
        print(cat_summary)
        
        results_df.to_csv(os.path.join(RESULTS_DIR, 'trader_dale_results.csv'), index=False)
    else:
        print("No trades triggered.")

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

if __name__ == "__main__":
    run_backtest()
