import pandas as pd
import os

# --- Configuration ---
RESULTS_FILE = '/Users/rahulgirishkumar/TRADING/backtests_strict/breakout_strict_results.csv'
SUMMARY_FILE = '/Users/rahulgirishkumar/TRADING/backtests_strict/breakout_price_analysis.csv'

def analyze_by_price():
    if not os.path.exists(RESULTS_FILE):
        print(f"Error: Results file {RESULTS_FILE} not found.")
        return

    df = pd.read_csv(RESULTS_FILE)
    
    # Define Price Ranges
    def classify_price(price):
        if price < 5: return 'Penny Stocks (<$5)'
        if price < 20: return 'Low Price ($5-$20)'
        if price < 100: return 'Mid Price ($20-$100)'
        return 'High Price (>$100 / S&P Proxy)'

    df['PriceCategory'] = df['EntryPrice'].apply(classify_price)
    
    # Aggregate Metrics
    summary = df.groupby('PriceCategory').agg(
        TradeCount=('PnL', 'count'),
        WinRate=('PnL', lambda x: (x > 0).mean()),
        AvgPnL=('PnL', 'mean'),
        MaxGain=('PnL', 'max'),
        TotalPnLSum=('PnL', 'sum')
    ).reset_index()
    
    # Sort for logical presentation
    cat_order = ['Penny Stocks (<$5)', 'Low Price ($5-$20)', 'Mid Price ($20-$100)', 'High Price (>$100 / S&P Proxy)']
    summary['PriceCategory'] = pd.Categorical(summary['PriceCategory'], categories=cat_order, ordered=True)
    summary = summary.sort_values('PriceCategory')

    print("\n--- Strategy Performance by Stock Price Range ---")
    print(summary.to_string(index=False))
    
    summary.to_csv(SUMMARY_FILE, index=False)
    print(f"\nAnalysis saved to {SUMMARY_FILE}")

if __name__ == "__main__":
    analyze_by_price()
