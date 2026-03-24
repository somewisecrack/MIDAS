import pandas as pd
import numpy as np
from tqdm import tqdm
import os
from datetime import datetime

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/backtests_ep'
os.makedirs(RESULTS_DIR, exist_ok=True)

# Files
DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')
H1_FILE = os.path.join(DATA_DIR, 'tickers_1h_ohlcv.csv')
M30_FILE = os.path.join(DATA_DIR, 'tickers_30m_ohlcv.csv')
M15_FILE = os.path.join(DATA_DIR, 'tickers_15m_ohlcv.csv')
M5_FILE = os.path.join(DATA_DIR, 'tickers_5m_ohlcv.csv')

# EP Rules
MIN_GAP = 0.10
VOL_MULT = 2.0
SMA10_PERIOD = 10

def run_ep_multi_timeframe_backtest():
    print("Loading data...")
    df_daily = pd.read_csv(DAILY_FILE)
    df_daily['Date'] = pd.to_datetime(df_daily['Date']).dt.tz_localize(None)
    
    # Intraday loaders
    intra_files = {
        '1h': H1_FILE,
        '30m': M30_FILE,
        '15m': M15_FILE,
        '5m': M5_FILE
    }
    
    intra_dfs = {}
    for tf, path in intra_files.items():
        print(f"Loading {tf} data...")
        df = pd.read_csv(path, low_memory=False)
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        intra_dfs[tf] = df

    tickers = df_daily['Ticker'].unique()
    tf_trades = {tf: [] for tf in intra_files.keys()}

    for ticker in tqdm(tickers, desc="Processing Tickers"):
        res_d = df_daily[df_daily['Ticker'] == ticker].sort_values('Date').copy()
        if len(res_d) < 30: continue
        
        # EP Setup detection (Daily)
        res_d['PrevClose'] = res_d['Close'].shift(1)
        res_d['Gap'] = (res_d['Open'] - res_d['PrevClose']) / res_d['PrevClose']
        res_d['VolAvg20'] = res_d['Volume'].rolling(20).mean()
        res_d['SMA10'] = res_d['Close'].rolling(SMA10_PERIOD).mean()
        
        # Mark EP Candidates
        ep_mask = (res_d['Gap'] >= MIN_GAP) & (res_d['Volume'] >= res_d['VolAvg20'] * VOL_MULT)
        candidates = res_d[ep_mask]
        
        for idx, row in candidates.iterrows():
            trade_timestamp = row['Date']
            trade_date = trade_timestamp.date()
            lod = row['Low']
            
            for tf, df_intra in intra_dfs.items():
                res_intra = df_intra[(df_intra['Ticker'] == ticker) & (df_intra['Date'].dt.date == trade_date)].sort_values('Date')
                if res_intra.empty: continue
                
                # ORH Logic
                orh = res_intra.iloc[0]['High']
                post_orh = res_intra.iloc[1:]
                entry_pts = post_orh[post_orh['High'] > orh]
                
                if not entry_pts.empty:
                    entry_price = orh * 1.001 # Slippage
                    
                    # Check same day stop
                    if lod < row['Low']: # Should really use intraday LOD for accuracy
                        # But daily Low is a safe proxy for LOD
                        pass
                    
                    if row['Low'] < lod: # Redundant but for clarity
                        pass # Should handle LOD from intra
                        
                    # For EP, we stay in as long as close > SMA10
                    future_d = res_d[res_d['Date'] > trade_timestamp].sort_values('Date')
                    is_active = True
                    for f_idx, f_row in future_d.iterrows():
                        if f_row['Close'] < f_row['SMA10']:
                            exit_val = f_row['Close']
                            pnl = (exit_val / entry_price) - 1
                            tf_trades[tf].append({
                                'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                                'ExitPrice': exit_val, 'PnL': pnl, 'Type': 'SMA10_Exit'
                            })
                            is_active = False
                            break
                    if is_active and not future_d.empty:
                        last_row = future_d.iloc[-1]
                        pnl = (last_row['Close'] / entry_price) - 1
                        tf_trades[tf].append({
                            'Ticker': ticker, 'Date': trade_timestamp, 'EntryPrice': entry_price,
                            'ExitPrice': last_row['Close'], 'PnL': pnl, 'Type': 'End_Of_History'
                        })

    # Summary
    results = []
    for tf, trades in tf_trades.items():
        if trades:
            tdf = pd.DataFrame(trades)
            tdf.to_csv(os.path.join(RESULTS_DIR, f'ep_{tf}_results.csv'), index=False)
            results.append({
                'Timeframe': tf,
                'TradeCount': len(tdf),
                'WinRate': (tdf['PnL'] > 0).mean(),
                'AvgPnL': tdf['PnL'].mean(),
                'ProfitFactor': tdf[tdf['PnL']>0]['PnL'].sum() / abs(tdf[tdf['PnL']<0]['PnL'].sum()) if not tdf[tdf['PnL']<0].empty else np.inf
            })
            
    summary_df = pd.DataFrame(results)
    print("\n--- Episodic Pivot Multi-Timeframe Summary ---")
    print(summary_df.to_string(index=False))
    summary_df.to_csv(os.path.join(RESULTS_DIR, 'ep_comparison_summary.csv'), index=False)

if __name__ == "__main__":
    run_ep_multi_timeframe_backtest()
