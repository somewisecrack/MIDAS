import pandas as pd
import numpy as np
import os
import argparse
from tqdm import tqdm

def calculate_vsa_indicators(df):
    """
    Calculates mechanical VSA indicators based on Gavin Holmes' book.
    """
    # 1. Volume Analysis
    df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
    df['Rel_Vol'] = df['Volume'] / df['Volume_MA']
    
    # 2. Spread Analysis (High - Low)
    df['Spread'] = df['High'] - df['Low']
    df['Spread_MA'] = df['Spread'].rolling(window=20).mean()
    df['Rel_Spread'] = df['Spread'] / df['Spread_MA']
    
    # 3. Closing Position (0=Low, 1=High)
    df['Close_Pos'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
    df['Close_Pos'] = df['Close_Pos'].fillna(0.5)
    
    # 4. Trend (Simple 50-day SMA slope proxy)
    df['Trend_MA'] = df['Close'].rolling(window=50).mean()
    df['Trend'] = np.where(df['Close'] > df['Trend_MA'], 'Up', 'Down')
    
    # 5. Volatility Thresholds
    ultra_high_vol = 2.0
    high_vol = 1.5
    low_vol_threshold = 1.0 # Less than MA
    wide_spread = 1.5
    narrow_spread = 0.8

    # Patterns Initialization
    df['SOW_Upthrust'] = (df['High'] > df['High'].shift(1)) & (df['Close_Pos'] < 0.3) & (df['Rel_Vol'] > 1.0)
    df['SOW_Hidden_Upthrust'] = (df['High'] > df['High'].shift(1)) & (df['Close'] < df['Close'].shift(1)) & (df['Rel_Vol'] > 1.0)
    df['SOW_Buying_Climax'] = (df['Close'] > df['Close'].shift(1)) & (df['Rel_Spread'] > wide_spread) & (df['Close_Pos'] >= 0.3) & (df['Close_Pos'] <= 0.7) & (df['Rel_Vol'] > ultra_high_vol)
    
    # No Demand: Up bar, Narrow Spread, Volume < prev 2 bars
    df['SOW_No_Demand'] = (df['Close'] > df['Close'].shift(1)) & (df['Rel_Spread'] < narrow_spread) & \
                          (df['Volume'] < df['Volume'].shift(1)) & (df['Volume'] < df['Volume'].shift(2))
    
    # Supply Coming In: Up bar, Wide Spread, Ultra High Vol, Next Bar Down (we look at current and prev)
    df['SOW_Supply_Coming_In'] = (df['Close'].shift(1) > df['Close'].shift(2)) & (df['Rel_Spread'].shift(1) > wide_spread) & \
                                 (df['Rel_Vol'].shift(1) > ultra_high_vol) & (df['Close'] < df['Close'].shift(1))
    
    # End of Rising Market: Up bar, Narrow Spread, Ultra High Vol, 500-bar High
    df['SOW_End_Rising_Market'] = (df['Close'] > df['Close'].shift(1)) & (df['Rel_Spread'] < narrow_spread) & \
                                  (df['Rel_Vol'] > ultra_high_vol) & (df['High'] == df['High'].rolling(250).max()) # Using 250 as proxy for 500 (1 year)

    # SOS Patterns
    df['SOS_Shakeout'] = (df['Close'] < df['Close'].shift(1)) & (df['Rel_Spread'] > wide_spread) & (df['Close_Pos'] > 0.7) & (df['Rel_Vol'] > ultra_high_vol)
    
    # No Supply: Down Bar, Narrow Spread, Volume < prev 2 bars
    df['SOS_No_Supply'] = (df['Close'] < df['Close'].shift(1)) & (df['Rel_Spread'] < narrow_spread) & \
                          (df['Volume'] < df['Volume'].shift(1)) & (df['Volume'] < df['Volume'].shift(2))
    
    # Stopping Volume: Down bar, Narrow Spread, Ultra High Vol, Next Bar Up
    df['SOS_Stopping_Volume'] = (df['Close'].shift(1) < df['Close'].shift(2)) & (df['Rel_Spread'].shift(1) < narrow_spread) & \
                                (df['Rel_Vol'].shift(1) > ultra_high_vol) & (df['Close'] > df['Close'].shift(1))
    
    df['SOS_Selling_Climax'] = (df['Close'] < df['Close'].shift(1)) & (df['Rel_Spread'] > wide_spread) & (df['Close_Pos'] >= 0.3) & (df['Close_Pos'] <= 0.7) & (df['Rel_Vol'] > ultra_high_vol)
    
    df['SOS_Bag_Holding'] = (df['Close'] < df['Close'].shift(1)) & (df['Rel_Spread'] < narrow_spread) & (df['Rel_Vol'] > ultra_high_vol) & (df['Trend'] == 'Down')
    
    # Test: Down bar, Narrow Spread, Low Volume, Next bar Up
    df['SOS_Test'] = (df['Close'].shift(1) < df['Close'].shift(2)) & (df['Rel_Spread'].shift(1) < narrow_spread) & \
                     (df['Volume'].shift(1) < df['Volume'].shift(2)) & (df['Volume'].shift(1) < df['Volume'].shift(3)) & \
                     (df['Close'] > df['Close'].shift(1))

    return df

def simulate_vsa_trades(df, pattern_col, trade_type='long'):
    """
    Simulates trades based on VSA patterns.
    Entry: Next bar open.
    Exit: 5-day trailing stop or N-bars.
    """
    trades = []
    in_trade = False
    entry_price = 0
    entry_date = None
    
    for i in range(len(df)):
        if not in_trade:
            if df[pattern_col].iloc[i]:
                if i + 1 < len(df):
                    in_trade = True
                    entry_price = df['Open'].iloc[i+1]
                    entry_date = df['Date'].iloc[i+1]
                    exit_countdown = 10 # Hold for 10 bars or simple exit
        else:
            exit_countdown -= 1
            if exit_countdown == 0 or i == len(df) - 1:
                exit_price = df['Close'].iloc[i]
                pnl = (exit_price - entry_price) / entry_price if trade_type == 'long' else (entry_price - exit_price) / entry_price
                trades.append(pnl)
                in_trade = False
    return trades

def get_price_range(price):
    if price < 10: return "$0-10"
    if price < 50: return "$10-50"
    if price < 100: return "$50-100"
    return "$100+"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_file", default="/Users/rahulgirishkumar/TRADING/tickers_ohlcv.csv")
    parser.add_argument("--timeframe", default="Daily")
    args = parser.parse_args()
    
    if not os.path.exists(args.data_file):
        print(f"File not found: {args.data_file}")
        return

    print(f"Loading data from {args.data_file}...")
    df_all = pd.read_csv(args.data_file)
    
    patterns = [
        ('SOW_Upthrust', 'short'), ('SOW_Hidden_Upthrust', 'short'), ('SOW_Buying_Climax', 'short'),
        ('SOW_No_Demand', 'short'), ('SOW_Supply_Coming_In', 'short'), ('SOW_End_Rising_Market', 'short'),
        ('SOS_Shakeout', 'long'), ('SOS_No_Supply', 'long'), ('SOS_Stopping_Volume', 'long'),
        ('SOS_Selling_Climax', 'long'), ('SOS_Bag_Holding', 'long'), ('SOS_Test', 'long')
    ]
    
    results = []
    
    tickers = df_all['Ticker'].unique()
    for ticker in tqdm(tickers, desc="Processing Tickers"):
        df = df_all[df_all['Ticker'] == ticker].copy()
        if len(df) < 50: continue
        
        df = calculate_vsa_indicators(df)
        avg_price = df['Close'].mean()
        price_range = get_price_range(avg_price)
        
        for pattern, t_type in patterns:
            trades = simulate_vsa_trades(df, pattern, t_type)
            if trades:
                win_rate = len([t for t in trades if t > 0]) / len(trades)
                avg_pnl = np.mean(trades)
                results.append({
                    'Ticker': ticker,
                    'PriceRange': price_range,
                    'Timeframe': args.timeframe,
                    'Pattern': pattern,
                    'Trades': len(trades),
                    'WinRate': win_rate,
                    'AvgPnL': avg_pnl
                })
    
    res_df = pd.DataFrame(results)
    if not res_df.empty:
        summary = res_df.groupby(['Pattern', 'PriceRange', 'Timeframe']).agg({
            'Trades': 'sum',
            'WinRate': 'mean',
            'AvgPnL': 'mean'
        }).reset_index()
        
        output_file = f"/Users/rahulgirishkumar/TRADING/results/vsa/vsa_audit_results_{args.timeframe}.csv"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        summary.to_csv(output_file, index=False)
        print(f"Audit results saved to {output_file}")
        print("\nTop Performing VSA Patterns:")
        print(summary.sort_values(by='AvgPnL', ascending=False).head(10))
    else:
        print("No trades found for any pattern.")

if __name__ == "__main__":
    main()
