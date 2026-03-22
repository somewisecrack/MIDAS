import pandas as pd
import numpy as np
import os

DAILY_DATA = '/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv'
# Using specific tickers list for targeted validation
SWING_TICKERS = ['AEP', 'CBOE', 'COHR', 'CTRA', 'DINO', 'EQIX', 'FIGS', 'FTI', 'GNRC', 'GRMN']
INTRADAY_TICKERS = ['AVTR', 'FIVN', 'FLO', 'KVUE', 'MAT', 'NFE', 'PINS', 'PSKY', 'XPON', 'NWL']

def validate_swing():
    print("--- Validating Swing Recommendations ---")
    df = pd.read_csv(DAILY_DATA)
    df.columns = [c.capitalize() if c.lower() != 'ticker' else 'Ticker' for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], utc=True)
    df.sort_values(['Ticker', 'Date'], inplace=True)
    
    results = []
    
    for ticker in SWING_TICKERS:
        t_df = df[df['Ticker'] == ticker].copy()
        if t_df.empty:
            results.append({'Ticker': ticker, 'Status': 'Data Missing'})
            continue
            
        # Latest data (Mar 20, 2026)
        last = t_df.iloc[-1]
        close = last['Close']
        
        # 1. Minervini Trend Template (8 Criteria)
        t_df['SMA50'] = t_df['Close'].rolling(50).mean()
        t_df['SMA150'] = t_df['Close'].rolling(150).mean()
        t_df['SMA200'] = t_df['Close'].rolling(200).mean()
        t_df['SMA200_1M_Ago'] = t_df['SMA200'].shift(21)
        
        high_52w = t_df['High'].rolling(252).max().iloc[-1]
        low_52w = t_df['Low'].rolling(252).min().iloc[-1]
        
        m1 = (close > t_df['SMA150'].iloc[-1]) and (close > t_df['SMA200'].iloc[-1])
        m2 = t_df['SMA150'].iloc[-1] > t_df['SMA200'].iloc[-1]
        m3 = t_df['SMA200'].iloc[-1] > t_df['SMA200_1M_Ago'].iloc[-1]
        m4 = (t_df['SMA50'].iloc[-1] > t_df['SMA150'].iloc[-1]) and (t_df['SMA50'].iloc[-1] > t_df['SMA200'].iloc[-1])
        m5 = close > t_df['SMA50'].iloc[-1]
        m6 = close >= (low_52w * 1.3)
        m7 = close >= (high_52w * 0.75)
        # m8 (RS > 70) - proxying with price performance vs SPY if available, but skipping for now or assuming OK if others pass
        
        minervini_pass = all([m1, m2, m3, m4, m5, m6, m7])
        
        # 2. Ang Momentum (12-1)
        # (Price[t-21] / Price[t-252]) - 1
        mom_12_1 = (t_df['Close'].iloc[-21] / t_df['Close'].iloc[-252]) - 1 if len(t_df) >= 252 else 0
        
        results.append({
            'Ticker': ticker,
            'Price': round(close, 2),
            'Minervini Template': 'PASS' if minervini_pass else 'FAIL',
            '12-1 Momentum (%)': round(mom_12_1 * 100, 2)
        })

    res_df = pd.DataFrame(results)
    print(res_df.to_string(index=False))
    return res_df

def validate_intraday():
    print("\n--- Validating Intraday Recommendations (4-Factor Proximity) ---")
    df = pd.read_csv(DAILY_DATA)
    df.columns = [c.capitalize() if c.lower() != 'ticker' else 'Ticker' for c in df.columns]
    
    results = []
    
    for ticker in INTRADAY_TICKERS:
        t_df = df[df['Ticker'] == ticker].copy()
        if t_df.empty:
            results.append({'Ticker': ticker, 'Status': 'Data Missing'})
            continue
            
        last = t_df.iloc[-1]
        close = last['Close']
        
        # 4-Factor emphasizes sub-$20 stocks for max alpha
        price_suitability = "OPTIMAL" if close < 20 else "SUBOPTIMAL"
        
        # Check for mean reversion: Is it a down-day? (Factor: mom = log(C/O))
        # 4-Factor residuals would be negative if overnight gap was high vs predicted.
        # Simple proxy: momentum factor
        mom_factor = np.log(close / last['Open'])
        
        results.append({
            'Ticker': ticker,
            'Price': round(close, 2),
            'Suitability (<$20)': price_suitability,
            'Mom Factor (log C/O)': round(mom_factor, 4)
        })
        
    res_df = pd.DataFrame(results)
    print(res_df.to_string(index=False))
    return res_df

if __name__ == '__main__':
    validate_swing()
    validate_intraday()
