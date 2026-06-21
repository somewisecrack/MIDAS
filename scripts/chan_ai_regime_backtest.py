import pandas as pd
import numpy as np
import os
from tqdm import tqdm
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# --- Configuration ---
DATA_DIR = '/Users/rahulgirishkumar/TRADING/data/'
RESULTS_DIR = '/Users/rahulgirishkumar/TRADING/results/chan_ai'
os.makedirs(RESULTS_DIR, exist_ok=True)

DAILY_FILE = os.path.join(DATA_DIR, 'tickers_ohlcv.csv')

# Parameters
TOP_N_TICKERS = 100
TRAIN_WINDOW_YEARS = 3
TARGET_PCT_THRESHOLD = 0.015 # Target moves > 1.5% to define 'Trend' day

def engineer_features(df):
    """Generates technical indicators as features for the regime classifier."""
    # Price Momentum
    df['Returns'] = df['Close'].pct_change()
    df['ROC_5'] = df['Close'].pct_change(5)
    df['ROC_21'] = df['Close'].pct_change(21)
    
    # Volatility
    df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
    df['Vol_STD'] = df['Returns'].rolling(21).std()
    
    # Range Metrics
    df['Range_Ratio'] = (df['High'] - df['Low']) / df['Close']
    df['Range_SMA'] = df['Range_Ratio'].rolling(21).mean()
    
    # Indicators
    df['RSI'] = 100 - (100 / (1 + df['Returns'].apply(lambda x: x if x > 0 else 0).rolling(14).mean() / 
                             df['Returns'].apply(lambda x: -x if x < 0 else 0).rolling(14).mean()))
    
    # Labels for Regime: 1 if Next Day High-Low range > Threshold * Close, else 0 (Range/Reversion)
    df['Next_Range'] = (df['High'].shift(-1) - df['Low'].shift(-1)) / df['Close'].shift(-1)
    df['Label'] = (df['Next_Range'] > (df['Range_SMA'] * 1.2)).astype(int)
    
    # Only drop rows where essential features or labels are NaN
    essential_cols = ['ROC_5', 'ROC_21', 'Vol_STD', 'Range_Ratio', 'Range_SMA', 'RSI', 'Label']
    return df.dropna(subset=essential_cols)

def run_meta_backtest():
    print("Loading daily data...")
    df = pd.read_csv(DAILY_FILE)
    df['Ticker'] = df['Ticker'].astype(str).str.strip()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.dropna(subset=['Date', 'Ticker', 'Close'])
    
    # Select high-volume assets
    liquidity = df.groupby('Ticker')['Volume'].mean() * df.groupby('Ticker')['Close'].mean()
    top_tickers = liquidity.sort_values(ascending=False).head(TOP_N_TICKERS).index.tolist()
    
    print(f"Top 5 tickers to process: {top_tickers[:5]}")
    all_results = []
    
    for ticker in tqdm(top_tickers, desc="Training AI Regime Switcher"):
        ticker_df = df[df['Ticker'] == ticker].copy().sort_values('Date')
        if len(ticker_df) < 300: 
            continue
        
        ticker_df = engineer_features(ticker_df)
        
        if len(ticker_df) < 50:
            continue
            
        # Split features and labels
        features = ['ROC_5', 'ROC_21', 'Vol_STD', 'Range_Ratio', 'Range_SMA', 'RSI']
        X = ticker_df[features]
        y = ticker_df['Label']
        
        # Split into Train and Test (Temporal Split)
        train_size = int(len(ticker_df) * 0.80)
        X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
        y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
        
        if len(X_train) < 30 or len(X_test) < 5:
            continue
            
        # Train Classifier
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X_train, y_train)
        
        # Predictions
        y_pred = model.predict(X_test)
        if len(y_test) == 0: continue
        
        acc = accuracy_score(y_test, y_pred)
        
        # Local Meta-Backtest logic:
        test_df = ticker_df.iloc[train_size:].copy()
        test_df['AI_Prediction'] = y_pred
        
        test_df['Mom_Return'] = np.where(test_df['AI_Prediction'] == 1, test_df['Returns'].shift(-1), 0)
        test_df['SMA5'] = test_df['Close'].rolling(5).mean()
        test_df['Rev_Target'] = (test_df['SMA5'] - test_df['Close']) / test_df['Close']
        test_df['Rev_Return'] = np.where(test_df['AI_Prediction'] == 0, test_df['Rev_Target'].abs() * 0.1, 0)
        
        test_df['Combined_Return'] = test_df['Mom_Return'].fillna(0) + test_df['Rev_Return'].fillna(0)
        
        all_results.append({
            'Ticker': ticker,
            'Accuracy': acc,
            'Total_Combined_Return': test_df['Combined_Return'].sum(),
            'Buy_Hold_Return': test_df['Returns'].sum()
        })
        
    if not all_results:
        print("\nError: No tickers passed the data filters. Training failed.")
        return

    results_summary = pd.DataFrame(all_results)
    print(f"\n--- Ernest Chan AI Regime Summary ---")
    print(f"Average Classifier Accuracy: {results_summary['Accuracy'].mean():.2%}")
    print(f"Avg AI-Switched Return: {results_summary['Total_Combined_Return'].mean():.2%}")
    print(f"Avg Buy & Hold Return: {results_summary['Buy_Hold_Return'].mean():.2%}")
    
    results_summary.to_csv(os.path.join(RESULTS_DIR, 'chan_ai_regime_results.csv'), index=False)

if __name__ == "__main__":
    run_meta_backtest()
