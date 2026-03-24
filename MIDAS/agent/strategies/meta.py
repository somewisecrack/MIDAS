from typing import Dict, Optional, Literal
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from agent.indicators import ATR, ROC, RollingStd


def detect_regime(df: pd.DataFrame, market_df: Optional[pd.DataFrame] = None) -> Literal["TREND", "RANGE", "UNKNOWN"]:
    if len(df) < 60:
        return "UNKNOWN"
    
    df = df.tail(60).copy()
    df["Daily_Range"] = (df["High"] - df["Low"]) / df["Close"]
    df["ROC_5"] = ROC(df["Close"], 5)
    df["ROC_21"] = ROC(df["Close"], 21)
    df["Volatility_21"] = RollingStd(df["Close"].pct_change(), 21) * 100
    
    avg_volatility = df["Daily_Range"].rolling(21).mean().iloc[-1]
    current_range = df["Daily_Range"].iloc[-1]
    
    if current_range > avg_volatility * 1.2:
        return "TREND"
    elif current_range < avg_volatility * 0.8:
        return "RANGE"
    else:
        if df["ROC_5"].iloc[-1] > 2:
            return "TREND"
        elif df["ROC_5"].iloc[-1] < -2:
            return "RANGE"
        return "RANGE"


def fosback_market_logic(df: pd.DataFrame, market_df: Optional[pd.DataFrame] = None) -> Dict:
    if len(df) < 30:
        return {"signal": "NEUTRAL", "confidence": 50}
    
    df = df.tail(30).copy()
    df["ROC_5"] = ROC(df["Close"], 5)
    df["ROC_21"] = ROC(df["Close"], 21)
    df["Volatility"] = RollingStd(df["Close"].pct_change(), 5) * 100
    
    roc_5 = df["ROC_5"].iloc[-5:].mean()
    roc_21 = df["ROC_21"].iloc[-1]
    volatility = df["Volatility"].iloc[-5:].mean()
    
    bullish_score = 0
    bearish_score = 0
    
    if roc_21 > 5:
        bullish_score += 1
    elif roc_21 < -5:
        bearish_score += 1
    
    if volatility > df["Volatility"].mean() * 1.5:
        if roc_21 < 0:
            bullish_score += 1
        else:
            bearish_score += 1
    
    if abs(roc_5) > 3:
        if roc_5 > 0:
            bullish_score += 1
        else:
            bearish_score += 1
    
    if bullish_score > bearish_score + 1:
        signal = "BULLISH"
        confidence = min(50 + (bullish_score * 10), 90)
    elif bearish_score > bullish_score + 1:
        signal = "BEARISH"
        confidence = min(50 + (bearish_score * 10), 90)
    else:
        signal = "NEUTRAL"
        confidence = 50
    
    return {
        "signal": signal,
        "confidence": confidence,
        "roc_5": roc_5,
        "roc_21": roc_21,
        "volatility": volatility
    }


def apply_meta_filters(
    ticker: str,
    df: pd.DataFrame,
    strategy_type: str,
    regime: str
) -> Dict:
    meta_result = {
        "apply_strategy": True,
        "weight_modifier": 1.0,
        "reason": ""
    }
    
    fosback = fosback_market_logic(df, None)
    
    if strategy_type == "SWING":
        if regime == "RANGE" and fosback["signal"] == "BEARISH":
            meta_result["weight_modifier"] = 0.7
            meta_result["reason"] = "Reduced weight: Range market with bearish bias"
        
        if regime == "TREND" and fosback["signal"] == "BULLISH":
            meta_result["weight_modifier"] = 1.3
            meta_result["reason"] = "Enhanced weight: Trend market with bullish bias"
    
    elif strategy_type == "INTRADAY":
        if regime == "TREND":
            if fosback["signal"] == "BULLISH":
                meta_result["weight_modifier"] = 0.8
                meta_result["reason"] = "Reduced: Intraday reversals less effective in strong trend"
            else:
                meta_result["weight_modifier"] = 1.2
        
        if regime == "RANGE":
            meta_result["weight_modifier"] *= 1.2
            meta_result["reason"] = (meta_result["reason"] + " Range market favors mean reversion. " if meta_result["reason"] else "Range market favors mean reversion. ")
    
    return meta_result


META_STRATEGIES = [
    {"name": "AI Regime Switching", "func": detect_regime},
    {"name": "Fosback Market Logic", "func": fosback_market_logic},
]
