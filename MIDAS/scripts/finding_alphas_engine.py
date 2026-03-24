import pandas as pd
import numpy as np

class AlphaEngine:
    def __init__(self, df):
        """
        Expects a MultiIndex DataFrame with levels (Date, Ticker) or a 
        pivoted DataFrame where columns are Tickers and index is Date.
        For WorldQuant-style vectorized ops, pivoted is more efficient.
        """
        self.open = df.pivot(index='Date', columns='Ticker', values='Open')
        self.high = df.pivot(index='Date', columns='Ticker', values='High')
        self.low = df.pivot(index='Date', columns='Ticker', values='Low')
        self.close = df.pivot(index='Date', columns='Ticker', values='Close')
        self.volume = df.pivot(index='Date', columns='Ticker', values='Volume')
        
        # Approximated VWAP
        self.vwap = (self.high + self.low + self.close) / 3
        
        # Returns
        self.returns = self.close.pct_change()
        
        # Cap/Ind/Sector placeholders (can be expanded if data exists)
        self.adv20 = self.volume.rolling(window=20).mean()
        
    # --- Basic Operators ---
    
    def rank(self, x):
        """Cross-sectional rank (normalized to [0, 1])"""
        return x.rank(axis=1, pct=True)

    def delay(self, x, n):
        """Value of x n days ago"""
        return x.shift(n)

    def correlation(self, x, y, n):
        """Time-series correlation between x and y over n days"""
        return x.rolling(window=n).corr(y).replace([np.inf, -np.inf], 0).fillna(0)

    def covariance(self, x, y, n):
        """Time-series covariance between x and y over n days"""
        return x.rolling(window=n).cov(y).replace([np.inf, -np.inf], 0).fillna(0)

    def delta(self, x, n):
        """Today's value minus value n days ago"""
        return x.diff(n)

    def ts_mean(self, x, n):
        """Time-series mean over n days"""
        return x.rolling(window=n).mean()

    def ts_std(self, x, n):
        """Time-series standard deviation over n days"""
        return x.rolling(window=n).std()

    def ts_rank(self, x, n):
        """Time-series rank over n days (normalized to [0, 1])"""
        return x.rolling(window=n).apply(lambda row: pd.Series(row).rank(pct=True).iloc[-1])

    def ts_argmax(self, x, n):
        """Day index of maximum value over last n days"""
        return x.rolling(window=n).apply(np.argmax) + 1

    def ts_argmin(self, x, n):
        """Day index of minimum value over last n days"""
        return x.rolling(window=n).apply(np.argmin) + 1

    def ts_max(self, x, n):
        return x.rolling(window=n).max()

    def ts_min(self, x, n):
        return x.rolling(window=n).min()

    # --- Meta Operators ---
    
    def ts_sum(self, x, n):
        return x.rolling(window=n).sum()

    def scale(self, x):
        """Standardizes x such that sum(abs(x)) = 1"""
        return x.div(x.abs().sum(axis=1), axis=0)

    # --- Parser ---
    
    def evaluate(self, formula_str):
        """
        A basic parser that maps WorldQuant-style strings to engine methods.
        Note: This is a simplified version for common 101 patterns.
        """
        # Cleanup string
        s = formula_str.replace(" ", "").lower()
        
        # Mapping table for simple regex or string replacement
        # In a real scenario, we'd use a proper grammar parser (like ply or lark)
        # For our audit, we'll implement the most common ones directly in get_alpha_*
        # but for 'all the alphas', we can use this logic.
        
        # Replace keywords with object calls
        s = s.replace("rank(", "self.rank(")
        s = s.replace("delay(", "self.delay(")
        s = s.replace("correlation(", "self.correlation(")
        s = s.replace("delta(", "self.delta(")
        s = s.replace("ts_rank(", "self.ts_rank(")
        s = s.replace("ts_argmax(", "self.ts_argmax(")
        s = s.replace("ts_std(", "self.ts_std(")
        s = s.replace("stddev(", "self.ts_std(")
        s = s.replace("sum(", "self.ts_sum(")
        s = s.replace("log(", "self.log(")
        s = s.replace("abs(", "self.abs(")
        s = s.replace("sign(", "self.sign(")
        
        # Variables
        s = s.replace("close", "self.close")
        s = s.replace("open", "self.open")
        s = s.replace("high", "self.high")
        s = s.replace("low", "self.low")
        s = s.replace("volume", "self.volume")
        s = s.replace("vwap", "self.vwap")
        s = s.replace("adv20", "self.adv20")
        s = s.replace("returns", "self.returns")
        
        try:
            return eval(s)
        except Exception as e:
            print(f"Error evaluating formula: {formula_str}\n{e}")
            return None

    # --- Math Utilities ---
    
    def log(self, x):
        return np.log(x.replace(0, np.nan))

    def abs(self, x):
        return x.abs()

    def sign(self, x):
        return np.sign(x)

    def power(self, x, n):
        return x ** n
