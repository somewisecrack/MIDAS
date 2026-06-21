import pandas as pd
import numpy as np
import os
from tqdm import tqdm

def calculate_vpa_indicators(df):
    """Calculate Relative Volume, Spread, and Candle Wick metrics for VPA."""
    df = df.sort_values(['Ticker', 'Date']).reset_index(drop=True)
    
    # 1. Volume Metrics
    # Relative Volume: Volume compared to 20-day moving average
    df['Vol_MA20'] = df.groupby('Ticker')['Volume'].transform(lambda x: x.rolling(20).mean())
    df['Rel_Vol'] = df['Volume'] / (df['Vol_MA20'] + 1e-9)
    
    # 2. Spread Metrics
    # Normalize spread by ATR(14)
    def get_atr(high, low, close, n=14):
        tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        return tr.rolling(n).mean()
        
    df['ATR14'] = df.groupby('Ticker').apply(lambda x: get_atr(x['High'], x['Low'], x['Close']), include_groups=False).reset_index(level=0, drop=True)
    df['Spread'] = (df['High'] - df['Low']) / (df['ATR14'] + 1e-9)
    df['Spread_Prev'] = df.groupby('Ticker')['Spread'].shift(1)
    
    # 3. Component Analysis (Wicks vs Body)
    df['Body'] = (df['Close'] - df['Open']).abs()
    df['Range'] = df['High'] - df['Low']
    df['Upper_Wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['Lower_Wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    
    # Wick Ratios
    df['Upper_Wick_Ratio'] = df['Upper_Wick'] / (df['Range'] + 1e-9)
    df['Lower_Wick_Ratio'] = df['Lower_Wick'] / (df['Range'] + 1e-9)
    df['Body_Ratio'] = df['Body'] / (df['Range'] + 1e-9)
    
    # 4. Moving Averages for Trend
    df['EMA50'] = df.groupby('Ticker')['Close'].transform(lambda x: x.ewm(span=50, adjust=False).mean())
    df['EMA200'] = df.groupby('Ticker')['Close'].transform(lambda x: x.ewm(span=200, adjust=False).mean())
    df['Trend'] = np.where(df['EMA50'] > df['EMA200'], 1, -1)
    
    return df

def simulate_vpa_trades(df, timeframe='Daily'):
    trades = []
    # Hold period depends on timeframe
    hold_period = 8 if timeframe == 'Daily' else 12 # 8 days vs 12 bars (1 hour of 5m)
    
    for ticker, group in tqdm(df.groupby('Ticker'), desc=f"Scanning {timeframe} VPA"):
        group = group.copy().reset_index(drop=True)
        
        for i in range(20, len(group)):
            row = group.iloc[i]
            prev = group.iloc[i-1]
            
            # --- VPA CLASSIFIERS ---
            is_ultra_vol = row['Rel_Vol'] > 2.0
            is_high_vol = row['Rel_Vol'] > 1.5
            is_low_vol = row['Rel_Vol'] < 0.7
            is_rising_vol = row['Volume'] > prev['Volume']
            
            # --- 1. Selling Climax (Top) ---
            if row['Trend'] == 1 and is_ultra_vol and row['Upper_Wick_Ratio'] > 0.4:
                climax_low = row['Low']
                for j in range(i+1, min(i+5, len(group))):
                    if group.iloc[j]['Close'] < climax_low:
                        entry = group.iloc[j]['Close']
                        exit_price = group.iloc[min(j+hold_period, len(group)-1)]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Selling Climax', 'PnL': (entry - exit_price)/entry, 'Price': entry})
                        break

            # --- 2. Buying Climax (Bottom) ---
            if row['Trend'] == -1 and is_ultra_vol and row['Lower_Wick_Ratio'] > 0.4:
                climax_high = row['High']
                for j in range(i+1, min(i+5, len(group))):
                    if group.iloc[j]['Close'] > climax_high:
                        entry = group.iloc[j]['Close']
                        exit_price = group.iloc[min(j+hold_period, len(group)-1)]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Buying Climax', 'PnL': (exit_price - entry)/entry, 'Price': entry})
                        break

            # --- 3. Stopping Volume ---
            if row['Trend'] == -1 and is_high_vol and row['Spread'] < 0.5 * row['Spread_Prev']:
                trigger_high = row['High']
                for j in range(i+1, min(i+5, len(group))):
                    if group.iloc[j]['Close'] > trigger_high:
                        entry = group.iloc[j]['Close']
                        exit_price = group.iloc[min(j+hold_period, len(group)-1)]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Stopping Volume', 'PnL': (exit_price - entry)/entry, 'Price': entry})
                        break

            # --- 4. No Demand Test (Retracement Up) ---
            if row['Trend'] == -1 and is_low_vol and row['Body_Ratio'] < 0.3 and row['Close'] > prev['High']:
                entry = row['Low']
                exit_price = group.iloc[min(i+3, len(group)-1)]['Close']
                trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'No Demand Test', 'PnL': (entry - exit_price)/entry, 'Price': entry})

            # --- 5. No Supply Test (Retracement Down) ---
            if row['Trend'] == 1 and is_low_vol and row['Body_Ratio'] < 0.3 and row['Close'] < prev['Low']:
                entry = row['High']
                exit_price = group.iloc[min(i+3, len(group)-1)]['Close']
                trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'No Supply Test', 'PnL': (exit_price - entry)/entry, 'Price': entry})

            # --- 6. The Hanging Man (Weakness at Peak) ---
            if row['Trend'] == 1 and is_high_vol and row['Lower_Wick_Ratio'] > 0.4:
                trigger_low = row['Low']
                for j in range(i+1, min(i+5, len(group))):
                    if group.iloc[j]['Close'] < trigger_low:
                        entry = group.iloc[j]['Close']
                        exit_price = group.iloc[min(j+5, len(group)-1)]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Hanging Man', 'PnL': (entry - exit_price)/entry, 'Price': entry})
                        break

            # --- 7. Topping Out Volume ---
            if row['Trend'] == 1 and is_high_vol and row['Spread'] < 0.5 * row['Spread_Prev']:
                # Bullish trend, volume surge, but spread narrowing
                trigger_low = row['Low']
                for j in range(i+1, min(i+3, len(group))):
                    if group.iloc[j]['Close'] < trigger_low:
                        entry = group.iloc[j]['Close']
                        exit_price = group.iloc[min(j+5, len(group)-1)]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Topping Out Volume', 'PnL': (entry - exit_price)/entry, 'Price': entry})
                        break

            # --- 8. Trap Up (Low Volume New High) ---
            if row['High'] > prev['High'] and is_low_vol:
                entry = row['Low']
                exit_price = group.iloc[min(i+3, len(group)-1)]['Close']
                trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Trap Up', 'PnL': (entry - exit_price)/entry, 'Price': entry})

            # --- 9. Trap Down (Low Volume New Low) ---
            if row['Low'] < prev['Low'] and is_low_vol:
                entry = row['High']
                exit_price = group.iloc[min(i+3, len(group)-1)]['Close']
                trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Trap Down', 'PnL': (exit_price - entry)/entry, 'Price': entry})

            # --- 10. Effort vs Result (Anomaly - Narrow Spread/High Vol) ---
            if row['Spread'] < 0.5 and is_ultra_vol:
                entry = row['High'] if row['Close'] > row['Open'] else row['Low']
                # Contradiction: Massive volume but no price movement
                trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'EvR Anomaly', 'PnL': (entry - group.iloc[min(i+3, len(group)-1)]['Close'])/entry if row['Close'] > row['Open'] else (group.iloc[min(i+3, len(group)-1)]['Close'] - entry)/entry, 'Price': entry})

            # --- 11. Effort vs Result (Agreement - Wide Spread/High Vol) ---
            if row['Spread'] > 2.0 and is_high_vol:
                entry = row['Close']
                direction = 1 if row['Close'] > row['Open'] else -1
                exit_price = group.iloc[min(i+hold_period, len(group)-1)]['Close']
                trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'EvR Agreement', 'PnL': direction * (exit_price - entry)/entry, 'Price': entry})

            # --- 12. Breakout Validation (Volume Surge) ---
            if i > 20 and row['Close'] > group.iloc[i-20:i]['High'].max() and is_high_vol:
                entry = row['Close']
                exit_price = group.iloc[min(i+hold_period, len(group)-1)]['Close']
                trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Breakout Validation', 'PnL': (exit_price - entry)/entry, 'Price': entry})

    return pd.DataFrame(trades)

def main():
    timeframes = ['Daily', '5m', '15m']
    data_files = {
        'Daily': '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv',
        '5m': '/Users/rahulgirishkumar/TRADING/data/tickers_5m_ohlcv.csv',
        '15m': '/Users/rahulgirishkumar/TRADING/data/tickers_15m_ohlcv.csv'
    }
    
    all_results = []
    
    for tf in timeframes:
        if not os.path.exists(data_files[tf]): continue
        
        print(f"\nProcessing {tf} Timeframe...")
        df = pd.read_csv(data_files[tf])
        df['Date'] = pd.to_datetime(df['Date'])
        
        df = calculate_vpa_indicators(df)
        trades_df = simulate_vpa_trades(df, timeframe=tf)
        
        if not trades_df.empty:
            trades_df['Timeframe'] = tf
            all_results.append(trades_df)

    if not all_results:
        print("No trades found.")
        return
        
    final_df = pd.concat(all_results)
    final_df['Price_Range'] = pd.cut(final_df['Price'], [0, 5, 20, 100, 10000], labels=['<$5', '$5-$20', '$20-$100', '>$100'])
    
    print("\n--- EXHAUSTIVE VPA AUDIT: THE COMPLETE MATRIX ---")
    matrix = final_df.groupby(['Strategy', 'Timeframe', 'Price_Range'], observed=False).agg(
        Trades=('PnL', 'count'),
        WinRate=('PnL', lambda x: (x > 0).mean()),
        PF=('PnL', lambda x: x[x>0].sum() / abs(x[x<0].sum()) if (x<0).any() else np.inf)
    ).sort_values(['Strategy', 'Timeframe'])
    
    pd.set_option('display.max_rows', None)
    print(matrix)
    
    output_path = '/Users/rahulgirishkumar/TRADING/results/vpa/exhaustive_audit.csv'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_df.to_csv(output_path, index=False)
    print(f"\nFinal report saved to {output_path}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
