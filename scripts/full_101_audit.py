import pandas as pd
import numpy as np
from finding_alphas_engine import AlphaEngine
import os

def run_101_audit():
    data_path = "/Users/rahulgirishkumar/TRADING/data/tickers_ohlcv.csv"
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Last 2 years
    max_date = df['Date'].max()
    df = df[df['Date'] >= (max_date - pd.DateOffset(years=2))]
    
    engine = AlphaEngine(df)
    
    # Formulas from 101 Formulaic Alphas (Kakushadze)
    # Mapping common ones to our engine's parser
    formulas = {
        "001": "rank(ts_argmax(power(((returns < 0) ? ts_std(returns, 20) : close), 2), 5)) - 0.5",
        "002": "-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6)",
        "003": "-1 * correlation(rank(open), rank(volume), 10)",
        "004": "-1 * ts_rank(rank(low), 9)",
        "005": "(rank((open - ts_mean(vwap, 10))) * (-1 * abs(rank((close - vwap)))))",
        "006": "-1 * correlation(open, volume, 10)",
        "009": "((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))",
        "011": "(rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3))",
        "012": "sign(delta(volume, 1)) * (-1 * delta(close, 1))",
        "013": "-1 * rank(covariance(rank(close), rank(volume), 5))",
        "022": "-1 * (delta(correlation(high, volume, 5), 5) * rank(ts_std(close, 20)))",
        "025": "rank(((((-1 * returns) * adv20) * vwap) * (high - close)))",
        "028": "scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))",
        "030": "((1.0 - rank(((sign(delta(close, 1)) + sign(delta(delay(close, 1), 1))) + sign(delta(delay(close, 2), 1))))) * sum(volume, 5)) / sum(volume, 20)",
        "033": "rank((-1 * ((rank(open) * 0.5) + (rank(close) * 0.5))) - rank(low))",
        "041": "(((high * low)^0.5) - vwap)",
        "054": "-1 * (low - close) * (open^5) / ((low - high + .001) * (close^5 + .001))",
        "101": "(close - open) / ((high - low) + .001)"
    }
    
    # Note: Ternary operators (cond ? a : b) aren't handled by eval() directly.
    # We will use the AlphaLibrary for complex ones and the parser for simple ones.
    from alpha_setups import AlphaLibrary
    lib = AlphaLibrary(engine)
    alphas = lib.calculate_all()
    
    results = []
    engine_rets = engine.returns
    
    for alpha_id, signals in alphas.items():
        if signals is None: continue
        
        # Prevent lookahead bias
        positions = signals.shift(1).fillna(0)
        
        # Calculate returns (equal weight market neutral)
        strat_rets = (engine_rets * positions).mean(axis=1)
        
        total_ret = (1 + strat_rets).prod() - 1
        sharpe = np.sqrt(252) * strat_rets.mean() / (strat_rets.std() + 1e-6)
        
        results.append({'Alpha': alpha_id, 'Total_Return': total_ret, 'Sharpe': sharpe})
        print(f"Alpha {alpha_id}: Return {total_ret:.2%}, Sharpe {sharpe:.2f}")

    results_df = pd.DataFrame(results).sort_values('Sharpe', ascending=False)
    results_df.to_csv("/Users/rahulgirishkumar/TRADING/results/full_101_audit_results.csv", index=False)
    print("\nFull 101 Audit Selection Complete.")
    print(results_df.head(10))

if __name__ == "__main__":
    run_101_audit()
