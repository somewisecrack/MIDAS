import pandas as pd
import numpy as np
from typing import Optional


def SMA(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def EMA(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def ATR(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def ADR(close: pd.Series, high: pd.Series, low: pd.Series, period: int = 20) -> pd.Series:
    daily_range = (high - low) / close
    return daily_range.rolling(window=period).mean() * close


def RSI(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def ADX(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.DataFrame:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0)
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10))
    adx = dx.rolling(window=period).mean()
    
    return pd.DataFrame({"ADX": adx, "+DI": plus_di, "-DI": minus_di})


def VWAP(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()


def VolumeSMA(volume: pd.Series, period: int = 20) -> pd.Series:
    return volume.rolling(window=period).mean()


def VolumeRatio(volume: pd.Series, period: int = 20) -> pd.Series:
    sma = VolumeSMA(volume, period)
    return volume / sma


def Stochastic(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    k_period: int = 14, 
    d_period: int = 3
) -> pd.DataFrame:
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
    d = k.rolling(window=d_period).mean()
    return pd.DataFrame({"K": k, "D": d})


def ROC(series: pd.Series, period: int) -> pd.Series:
    return series.pct_change(periods=period) * 100


def ROC_12_1(close: pd.Series) -> pd.Series:
    return (close.shift(21) / close.shift(252) - 1) * 100


def High52Week(high: pd.Series, period: int = 252) -> pd.Series:
    return high.rolling(window=period).max()


def Low52Week(low: pd.Series, period: int = 252) -> pd.Series:
    return low.rolling(window=period).min()


def ClosePosition(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    spread = high - low
    return (close - low) / (spread + 1e-10)


def SpreadRatio(high: pd.Series, low: pd.Series, period: int = 20) -> pd.Series:
    spread = high - low
    avg_spread = spread.rolling(window=period).mean()
    return spread / (avg_spread + 1e-10)


def UpperWickRatio(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    spread = high - low
    upper_wick = high - np.maximum(open_, close)
    return upper_wick / (spread + 1e-10)


def LowerWickRatio(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    spread = high - low
    lower_wick = np.minimum(open_, close) - low
    return lower_wick / (spread + 1e-10)


def MedianPrice(high: pd.Series, low: pd.Series) -> pd.Series:
    return np.sqrt(high * low)


def CalculateRSRating(
    ticker_returns: pd.Series, 
    market_returns: pd.Series, 
    lookback: int = 252
) -> pd.Series:
    ticker_roc = ticker_returns.rolling(window=lookback).sum()
    market_roc = market_returns.rolling(window=lookback).sum()
    rs_rating = (ticker_roc / (market_roc + 1e-10)) * 100
    return rs_rating.rank(pct=True) * 100


def CorrelationSeries(
    series1: pd.Series, 
    series2: pd.Series, 
    period: int = 20
) -> pd.Series:
    return series1.rolling(window=period).corr(series2)


def RollingStd(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(window=period).std()


def ts_rank(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) == period else np.nan
    )


def ts_max(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).max()


def ts_min(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).min()


def DonchianHigh(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).max()


def DonchianLow(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).min()


def DetectFlag(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    flag_period: int = 20,
    max_depth: float = 0.25
) -> pd.Series:
    flag_high = high.rolling(window=flag_period).max().shift(1)
    flag_low = low.rolling(window=flag_period).min().shift(1)
    flag_range = (flag_high - flag_low) / flag_high
    return (flag_range < max_depth) & (flag_range.shift(1) > max_depth)


def DetectBase(
    high: pd.Series,
    low: pd.Series,
    weeks: int = 5,
    min_depth: float = 0.08,
    max_depth: float = 0.15
) -> pd.Series:
    period = weeks * 5
    base_high = high.rolling(window=period).max()
    base_low = low.rolling(window=period).min()
    depth = (base_high - base_low) / base_high
    return (depth >= min_depth) & (depth <= max_depth)


def DetectVCP(
    high: pd.Series,
    low: pd.Series,
    lookback: int = 50,
    contractions: int = 3
) -> pd.Series:
    result = pd.Series(False, index=high.index)
    for i in range(lookback, len(high)):
        window = high.iloc[i-lookback:i] - low.iloc[i-lookback:i]
        ranges = window.rolling(10).apply(lambda x: (x.max() - x.min()) / x.mean())
        contractions_found = (ranges.diff() < 0).sum()
        if contractions_found >= contractions:
            result.iloc[i] = True
    return result


def DetectThreePeaks(
    high: pd.Series,
    lookback: int = 20
) -> pd.Series:
    result = pd.Series(False, index=high.index)
    for i in range(lookback * 2, len(high)):
        window = high.iloc[i-lookback*2:i]
        peaks = window.rolling(5).apply(
            lambda x: 1 if (x.iloc[2] == x.max() and x.iloc[2] > x.iloc[0] and x.iloc[2] > x.iloc[4]) else 0
        )
        peak_count = (peaks == 1).sum()
        if peak_count >= 3:
            result.iloc[i] = True
    return result
