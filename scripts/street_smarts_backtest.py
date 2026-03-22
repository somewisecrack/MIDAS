import pandas as pd
import numpy as np
import os
from tqdm import tqdm

def calculate_indicators(df):
    """Calculate all technical indicators required for Street Smarts setups."""
    df = df.sort_values(['Ticker', 'Date']).reset_index(drop=True)
    
    # 1. EMA 20
    df['EMA20'] = df.groupby('Ticker')['Close'].transform(lambda x: x.ewm(span=20, adjust=False).mean())
    
    # 2. ADX 14 (Street Smarts standard)
    def get_adx_series(group, n=14):
        high, low, close = group['High'], group['Low'], group['Close']
        plus_dm = (high.diff().clip(lower=0))
        minus_dm = (low.diff().clip(upper=0)).abs()
        tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(n).mean()
        plus_di = 100 * (plus_dm.rolling(n).mean() / (atr + 1e-9))
        minus_di = 100 * (minus_dm.rolling(n).mean() / (atr + 1e-9))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
        adx = dx.rolling(n).mean()
        return pd.DataFrame({'ADX': adx, 'plus_di': plus_di, 'minus_di': minus_di}, index=group.index)

    adx_res = df.groupby('Ticker', group_keys=False).apply(get_adx_series, include_groups=False)
    df = pd.concat([df, adx_res], axis=1)
    
    # 3. ADX Gapper parameters (12-period ADX, 28-period DI)
    def get_adx_gapper_di(group, n=28):
        high, low, close = group['High'], group['Low'], group['Close']
        plus_dm = (high.diff().clip(lower=0))
        minus_dm = (low.diff().clip(upper=0)).abs()
        tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(n).mean()
        plus_di = 100 * (plus_dm.rolling(n).mean() / (atr + 1e-9))
        minus_di = 100 * (minus_dm.rolling(n).mean() / (atr + 1e-9))
        return pd.DataFrame({'plus_di_28': plus_di, 'minus_di_28': minus_di}, index=group.index)
        
    df = pd.concat([df, df.groupby('Ticker', group_keys=False).apply(get_adx_gapper_di, include_groups=False)], axis=1)

    # 4. LBR/RSI (Momentum Pinball)
    def get_rsi(series, n=3):
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(window=n).mean()
        loss = delta.clip(upper=0).abs().rolling(window=n).mean()
        rs = gain / (loss + 1e-9)
        return 100 - (100 / (1 + rs))
    
    df['Net_Change'] = df.groupby('Ticker')['Close'].diff()
    df['LBR_RSI'] = df.groupby('Ticker')['Net_Change'].transform(lambda x: get_rsi(x, 3))
    
    # 5. %K(7) & %D(10) for The Anti
    def get_stoch_k(group, k_n=7):
        low_min = group['Low'].rolling(k_n).min()
        high_max = group['High'].rolling(k_n).max()
        k = 100 * (group['Close'] - low_min) / (high_max - low_min + 1e-9)
        return pd.Series(k, index=group.index)

    df['Stoch_K'] = df.groupby('Ticker', group_keys=False).apply(get_stoch_k, include_groups=False)
    df['Stoch_D'] = df.groupby('Ticker')['Stoch_K'].transform(lambda x: x.rolling(10).mean())
    df['Stoch_D_Slope'] = df.groupby('Ticker')['Stoch_D'].diff()
    
    # 6. Range & 20-Day Extremes
    df['Day_Range'] = df['High'] - df['Low']
    df['Open_Pct'] = (df['Open'] - df['Low']) / (df['Day_Range'] + 1e-9)
    df['Close_Pct'] = (df['Close'] - df['Low']) / (df['Day_Range'] + 1e-9)
    df['Low20'] = df.groupby('Ticker')['Low'].transform(lambda x: x.rolling(20).min())
    df['High20'] = df.groupby('Ticker')['High'].transform(lambda x: x.rolling(20).max())
    df['PrevLow20'] = df.groupby('Ticker')['Low'].transform(lambda x: x.shift(1).rolling(20).min())
    df['PrevHigh20'] = df.groupby('Ticker')['High'].transform(lambda x: x.shift(1).rolling(20).max())
    
    return df

def simulate_trades(daily_df):
    trades = []
    
    for ticker, group in tqdm(daily_df.groupby('Ticker'), desc="Executing Complete Audit"):
        group = group.copy().reset_index(drop=True)
        
        for i in range(30, len(group)):
            row = group.iloc[i]
            prev = group.iloc[i-1]
            prev2 = group.iloc[i-2]
            
            # --- 1. Turtle Soup ---
            if row['Low'] < row['PrevLow20']:
                entry_price = row['PrevLow20'] + 0.01
                if row['High'] >= entry_price:
                    if i + 1 < len(group):
                        exit_price = group.iloc[i+1]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Turtle Soup', 'PnL': (exit_price - entry_price)/entry_price, 'Price': entry_price})

            # --- 2. Turtle Soup Plus One ---
            if prev['Close'] <= prev['PrevLow20']:
                entry_price = prev['PrevLow20'] + 0.01
                if row['High'] >= entry_price:
                    if i + 1 < len(group):
                        exit_price = group.iloc[i+1]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Turtle Soup+1', 'PnL': (exit_price - entry_price)/entry_price, 'Price': entry_price})

            # --- 3. 80-20's ---
            if prev['Open_Pct'] > 0.8 and prev['Close_Pct'] < 0.2:
                if row['Low'] < prev['Low']:
                    entry_price = prev['Low']
                    if row['High'] >= entry_price:
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': '80-20', 'PnL': (row['Close'] - entry_price)/entry_price, 'Price': entry_price})

            # --- 4. Momentum Pinball ---
            if prev['LBR_RSI'] < 30:
                # Buy stop above 1st hour High. We use 1/3 of the day's range as proxy for 1st hour high.
                first_hour_high = row['Open'] + (row['High'] - row['Low']) * 0.3
                if row['High'] >= first_hour_high:
                    entry_price = first_hour_high
                    if i + 1 < len(group):
                        exit_price = group.iloc[i+1]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Pinball', 'PnL': (exit_price - entry_price)/entry_price, 'Price': entry_price})

            # --- 5. The Anti ---
            if prev['Stoch_D_Slope'] > 0 and prev['Stoch_K'] < prev['Stoch_D']: 
                if row['Stoch_K'] > prev['Stoch_K']: 
                    entry_price = row['Open']
                    if i + 3 < len(group):
                        exit_price = group.iloc[i+3]['Close']
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'The Anti', 'PnL': (exit_price - entry_price)/entry_price, 'Price': entry_price})

            # --- 6. Holy Grail ---
            if prev['ADX'] > 30 and row['Low'] <= row['EMA20'] and row['High'] >= row['EMA20']:
                entry_price = prev['High'] + 0.01 # Restore original logic
                if i + 4 < len(group):
                    exit_val = group.iloc[i+4]['Close']
                    trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Holy Grail', 'PnL': (exit_val - entry_price)/entry_price, 'Price': entry_price})

            # --- 7. ADX Gapper ---
            if prev['ADX'] > 30 and prev['plus_di_28'] > prev['minus_di_28']:
                if row['Open'] < prev['Low']: # Gapped below yesterday's low
                    entry_price = prev['Low']
                    if row['High'] >= entry_price:
                        trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'ADX Gapper', 'PnL': (row['Close'] - entry_price)/entry_price, 'Price': entry_price})

            # --- 8. Spike and Ledge ---
            # Buying climax spike (top 5% of ranges) + ledge (4 bars narrow)
            if i > 10:
                if prev['Day_Range'] > group.iloc[i-10:i]['Day_Range'].mean() * 2:
                    ledge = group.iloc[i-4:i]
                    if (ledge['High'].max() - ledge['Low'].min()) < (prev['Day_Range'] * 0.4):
                        entry_price = ledge['High'].max()
                        if row['High'] >= entry_price:
                            if i + 2 < len(group):
                                trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': 'Spike/Ledge', 'PnL': (group.iloc[i+2]['Close'] - entry_price)/entry_price, 'Price': entry_price})

            # --- 9. Three Little Indians ---
            if i > 20:
                if prev['High'] > prev2['High'] > group.iloc[i-3]['High']:
                    if row['Close'] < prev['Low']:
                        entry_price = prev['Low']
                        if i + 2 < len(group):
                            trades.append({'Ticker': ticker, 'Date': row['Date'], 'Strategy': '3 Little Indians', 'PnL': (entry_price - group.iloc[i+2]['Close'])/entry_price, 'Price': entry_price})

    return pd.DataFrame(trades)

def main():
    print("Loading Data...")
    df = pd.read_csv('/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    print("Calculating COMPLETE INDICATOR SET...")
    df = calculate_indicators(df)
    
    print("RUNNING TOTAL AUDIT (9 STRATEGIES)...")
    trades_df = simulate_trades(df)
    
    if trades_df.empty:
        print("No trades found.")
        return

    # Price classification
    trades_df['Price_Range'] = pd.cut(trades_df['Price'], [0, 5, 20, 100, 10000], labels=['<$5', '$5-$20', '$20-$100', '>$100'])
    
    print("\n--- STREET SMARTS: THE COMPLETE EVIDENCE MATRIX ---")
    matrix = trades_df.groupby(['Strategy', 'Price_Range'], observed=False).agg(
        Trades=('PnL', 'count'),
        WinRate=('PnL', lambda x: (x > 0).mean()),
        AvgPnL=('PnL', 'mean'),
        PF=('PnL', lambda x: x[x>0].sum() / abs(x[x<0].sum()) if len(x[x<0]) > 0 else 0)
    ).sort_values(['Strategy', 'Price_Range'])
    pd.set_option('display.max_rows', None)
    print(matrix)
    
    output_path = '/Users/rahulgirishkumar/TRADING/results/street_smarts/absolute_audit.csv'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    trades_df.to_csv(output_path, index=False)
    print(f"\nFinal results saved to {output_path}")

if __name__ == "__main__":
    main()
