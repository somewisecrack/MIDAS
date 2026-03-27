from typing import Dict, Optional
import pandas as pd
import numpy as np
from agent.indicators import (
    EMA, ATR, RSI, ADX, VWAP, VolumeSMA, VolumeRatio,
    Stochastic, ROC, ClosePosition, SpreadRatio, UpperWickRatio, 
    LowerWickRatio, MedianPrice, RollingStd
)


def four_factor_overnight(df: pd.DataFrame, ticker: str, market_df: Optional[pd.DataFrame] = None) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(30).copy()
    if len(df) < 25:
        return None
    
    df["prc"] = np.log(df["Close"].shift(1))
    df["mom"] = np.log(df["Close"].shift(1) / df["Open"].shift(1))
    hlv = 0.5 * np.log((((df["High"] - df["Low"]) / df["Close"]).shift(1).rolling(21).mean() ** 2 + 1e-10))
    df["vol"] = np.log(df["Volume"].shift(1).rolling(21).mean())
    
    last = df.iloc[-1]
    price = last["Close"]
    
    if price < 20:
        score = -(last["prc"] * 0.3 + last["mom"] * 0.3 + hlv.iloc[-1] * 0.2 + last["vol"] * 0.2)
        if abs(score) > 0.02:
            stop = price - ATR(df["High"], df["Low"], df["Close"], 14).iloc[-1]
            return {
                "ticker": ticker,
                "strategy": "4-Factor Overnight Model",
                "type": "LONG",
                "entry_price": price,
                "stop_loss": stop,
                "take_profit": price + (price - stop) * 2,
                "holding_period": "Same day",
                "confidence": 88,
                "signal": f"Mean reversion alpha detected (sub-$20 stocks)",
                "reasoning": f"4-Factor quant model signal for mean reversion. Elite performance in sub-$20 stocks with 474% ROC historically.",
                "price_ranges": ["penny", "low"],
                "win_rate": "N/A",
                "priority": "ELITE"
            }
    return None


def vsa_hidden_upthrust(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(25).copy()
    if len(df) < 20:
        return None
    
    df["Volume_SMA20"] = VolumeSMA(df["Volume"], 20)
    df["Volume_Ratio"] = VolumeRatio(df["Volume"], 20)
    df["Spread"] = df["High"] - df["Low"]
    df["Close_Position"] = ClosePosition(df["High"], df["Low"], df["Close"])
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    if (
        last["High"] > prev["High"] and
        last["Close"] < prev["Close"] and
        last["Volume_Ratio"] > 1.0
    ):
        price = last["Close"]
        stop = last["High"] * 1.01
        return {
            "ticker": ticker,
            "strategy": "VSA Hidden Upthrust",
            "type": "SHORT",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": last["Low"] * 0.99,
            "holding_period": "Intraday",
            "confidence": 68,
            "signal": "New high followed by weak close on high volume",
            "reasoning": f"Hidden upthrust pattern. Price made new high but closed weak on volume. Institutional rejection signal.",
            "price_ranges": ["penny"],
            "win_rate": "50.4%",
            "priority": "MEDIUM"
        }
    return None


def vsa_bag_holding(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(25).copy()
    if len(df) < 20:
        return None
    
    df["Volume_SMA20"] = VolumeSMA(df["Volume"], 20)
    df["Volume_Ratio"] = VolumeRatio(df["Volume"], 20)
    df["Spread"] = df["High"] - df["Low"]
    df["Spread_SMA20"] = df["Spread"].rolling(20).mean()
    df["SMA20"] = EMA(df["Close"], 20)
    
    last = df.iloc[-1]
    
    if (
        last["Close"] < last["SMA20"] and
        last["Close"] < last["Open"] and
        last["Spread"] < last["Spread_SMA20"] * 0.5 and
        last["Volume_Ratio"] > 2.0
    ):
        price = last["High"] + 0.01
        stop = last["Low"] * 0.99
        return {
            "ticker": ticker,
            "strategy": "VSA Bag Holding",
            "type": "LONG",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": price + (price - stop) * 2,
            "holding_period": "Intraday",
            "confidence": 72,
            "signal": "Narrow spread down bar with ultra-high volume in downtrend",
            "reasoning": f"Bag holding pattern. Narrow spread ({last['Spread']:.2f}) with 2x avg volume indicates institutional absorption.",
            "price_ranges": ["mid"],
            "win_rate": "53.7%",
            "priority": "HIGH"
        }
    return None


def vsa_upthrust(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(25).copy()
    if len(df) < 20:
        return None
    
    df["Volume_SMA20"] = VolumeSMA(df["Volume"], 20)
    df["Volume_Ratio"] = VolumeRatio(df["Volume"], 20)
    df["Spread"] = df["High"] - df["Low"]
    df["Spread_SMA20"] = df["Spread"].rolling(20).mean()
    df["Close_Position"] = ClosePosition(df["High"], df["Low"], df["Close"])
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    if (
        last["Close"] > last["Open"] and
        last["High"] > prev["High"] and
        last["Close_Position"] < 0.3 and
        last["Volume_Ratio"] > 1.0 and
        last["Spread"] > last["Spread_SMA20"] * 1.5
    ):
        price = last["Close"]
        stop = last["High"] * 1.01
        return {
            "ticker": ticker,
            "strategy": "VSA Upthrust",
            "type": "SHORT",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": last["Low"] * 0.99,
            "holding_period": "Intraday",
            "confidence": 70,
            "signal": "Wide spread up bar to new high but closes near low on volume",
            "reasoning": f"VSA upthrust. Wide spread with weak close indicates institutional distribution into strength.",
            "price_ranges": ["penny"],
            "win_rate": "52.6%",
            "priority": "HIGH"
        }
    return None


def vsa_buying_climax_intraday(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(25).copy()
    if len(df) < 20:
        return None
    
    df["Volume_SMA20"] = VolumeSMA(df["Volume"], 20)
    df["Volume_Ratio"] = VolumeRatio(df["Volume"], 20)
    df["Spread"] = df["High"] - df["Low"]
    df["Spread_SMA20"] = df["Spread"].rolling(20).mean()
    df["Close_Position"] = ClosePosition(df["High"], df["Low"], df["Close"])
    df["Momentum_5"] = df["Close"].pct_change(5)
    
    last = df.iloc[-1]
    
    if (
        last["Close"] > last["Open"] and
        last["Spread"] > last["Spread_SMA20"] * 1.5 and
        0.4 <= last["Close_Position"] <= 0.6 and
        last["Volume_Ratio"] > 2.0 and
        last["Momentum_5"] > 0.05
    ):
        price = last["Close"]
        stop = last["High"] * 1.01
        return {
            "ticker": ticker,
            "strategy": "VSA Buying Climax (Intraday)",
            "type": "SHORT",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": last["Low"] * 0.99,
            "holding_period": "Intraday",
            "confidence": 75,
            "signal": "Climax bar after rapid rally with ultra-high volume",
            "reasoning": f"Buying climax. Wide spread up bar with middle close on 2x volume. Institutional distribution pattern.",
            "price_ranges": ["penny"],
            "win_rate": "53-55%",
            "priority": "HIGH"
        }
    return None


def vsa_shakeout_intraday(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(25).copy()
    if len(df) < 20:
        return None
    
    df["Volume_SMA20"] = VolumeSMA(df["Volume"], 20)
    df["Volume_Ratio"] = VolumeRatio(df["Volume"], 20)
    df["Spread"] = df["High"] - df["Low"]
    df["Spread_SMA20"] = df["Spread"].rolling(20).mean()
    df["Close_Position"] = ClosePosition(df["High"], df["Low"], df["Close"])
    
    last = df.iloc[-1]
    
    if (
        last["Close"] < last["Open"] and
        last["Spread"] > last["Spread_SMA20"] * 1.5 and
        last["Close_Position"] > 0.7 and
        last["Volume_Ratio"] > 2.5
    ):
        price = last["Close"] * 1.01
        stop = last["Low"] * 0.99
        return {
            "ticker": ticker,
            "strategy": "VSA Shakeout (Intraday)",
            "type": "LONG",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": price + (price - stop) * 2,
            "holding_period": "Intraday",
            "confidence": 85,
            "signal": "Wide spread down bar with top close and extreme volume",
            "reasoning": f"Elite shakeout pattern. Wide spread with top close on 2.5x volume indicates successful absorption. 74% win rate historically.",
            "price_ranges": ["penny"],
            "win_rate": "74%",
            "priority": "ELITE"
        }
    return None


def vpa_no_demand(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(25).copy()
    if len(df) < 20:
        return None
    
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (typical * df["Volume"]).rolling(20).sum() / df["Volume"].rolling(20).sum()
    df["Volume_SMA20"] = VolumeSMA(df["Volume"], 20)
    df["Volume_Ratio"] = VolumeRatio(df["Volume"], 20)
    df["Spread"] = df["High"] - df["Low"]
    
    last = df.iloc[-1]
    
    if (
        last["Close"] < last["VWAP"] and
        last["High"] > df["High"].iloc[-2] and
        last["Spread"] < df["Spread"].iloc[-2] * 0.8 and
        last["Volume_Ratio"] < 0.7
    ):
        price = last["Close"]
        stop = last["High"]
        return {
            "ticker": ticker,
            "strategy": "VPA No Demand",
            "type": "SHORT",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": last["Low"] * 0.98,
            "holding_period": "Scalp (3-5 bars)",
            "confidence": 70,
            "signal": "Rally attempt with narrowing spread and collapsing volume",
            "reasoning": f"No demand signal. Price attempted rally but spread narrowed and volume collapsed. Bearish short-term.",
            "price_ranges": ["low"],
            "win_rate": "48.9%",
            "priority": "HIGH"
        }
    return None


def vpa_hanging_man(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(25).copy()
    if len(df) < 20:
        return None
    
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (typical * df["Volume"]).rolling(20).sum() / df["Volume"].rolling(20).sum()
    df["Volume_SMA20"] = VolumeSMA(df["Volume"], 20)
    df["Volume_Ratio"] = VolumeRatio(df["Volume"], 20)
    df["Lower_Wick"] = LowerWickRatio(df["Open"], df["High"], df["Low"], df["Close"])
    df["Spread"] = df["High"] - df["Low"]
    df["Body"] = abs(df["Close"] - df["Open"])
    
    last = df.iloc[-1]
    
    if (
        last["Close"] > last["VWAP"] and
        last["Body"] < last["Spread"] * 0.4 and
        last["Lower_Wick"] > 0.40 and
        last["Volume_Ratio"] > 1.2
    ):
        price = last["Close"]
        stop = last["High"] * 1.01
        return {
            "ticker": ticker,
            "strategy": "VPA Hanging Man",
            "type": "SHORT",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": last["VWAP"],
            "holding_period": "Intraday",
            "confidence": 68,
            "signal": "Small body with 40%+ lower wick in uptrend on volume",
            "reasoning": f"Hanging man pattern. Long lower wick ({last['Lower_Wick']*100:.0f}%) in uptrend on volume. Rejection signal.",
            "price_ranges": ["low"],
            "win_rate": "51.2%",
            "priority": "HIGH"
        }
    return None


def adx_gapper(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(30).copy()
    if len(df) < 20:
        return None
    
    adx_df = ADX(df["High"], df["Low"], df["Close"], 12)
    df["ADX"] = adx_df["ADX"]
    df["+DI"] = adx_df["+DI"]
    df["-DI"] = adx_df["-DI"]
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    if (
        last["ADX"] > 30 and
        last["+DI"] > last["-DI"] and
        last["Open"] < prev["Low"]
    ):
        price = prev["Low"]
        stop = last["Low"] * 0.99
        return {
            "ticker": ticker,
            "strategy": "ADX Gapper",
            "type": "LONG",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": price + (price - stop) * 2,
            "holding_period": "Intraday/Swing",
            "confidence": 68,
            "signal": f"Gap down in strong uptrend (ADX={last['ADX']:.1f})",
            "reasoning": f"ADX={last['ADX']:.1f} confirms strong trend. Gap down is trap entry. Best above $20.",
            "price_ranges": ["mid", "high"],
            "win_rate": "50.64%",
            "priority": "MEDIUM"
        }
    return None


def momentum_pinball(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(30).copy()
    if len(df) < 20:
        return None
    
    df["ROC_1"] = ROC(df["Close"], 1)
    delta = df["ROC_1"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=3).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=3).mean()
    rs = gain / (loss + 1e-10)
    df["LBR_RSI"] = 100 - (100 / (1 + rs))
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    if prev["LBR_RSI"] < 30 and last["Close"] > df["High"].iloc[-2]:
        price = df["High"].iloc[-2]
        stop = df["Low"].iloc[-2]
        return {
            "ticker": ticker,
            "strategy": "Momentum Pinball",
            "type": "LONG",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": price + (price - stop) * 2,
            "holding_period": "1-2 days",
            "confidence": 68,
            "signal": f"LBR/RSI oversold at {prev['LBR_RSI']:.1f} with breakout confirmation",
            "reasoning": f"Momentum pinball setup. RSI of ROC below 30 with first hour breakout. Best in $5-20 range.",
            "price_ranges": ["low"],
            "win_rate": "50.61%",
            "priority": "HIGH"
        }
    return None


def eighty_twenty_reversal(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(10).copy()
    if len(df) < 5:
        return None
    
    prev = df.iloc[-2]
    last = df.iloc[-1]
    
    prev_range = prev["High"] - prev["Low"]
    prev_open_pos = (prev["Open"] - prev["Low"]) / (prev_range + 1e-10)
    prev_close_pos = (prev["Close"] - prev["Low"]) / (prev_range + 1e-10)
    
    if (
        prev_open_pos > 0.8 and
        prev_close_pos < 0.2 and
        last["Low"] < prev["Low"] - 0.01
    ):
        price = prev["Low"]
        stop = last["Low"] * 0.99
        return {
            "ticker": ticker,
            "strategy": "80-20 Reversal",
            "type": "LONG",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": price + (price - stop) * 2,
            "holding_period": "Day trade only",
            "confidence": 72,
            "signal": "Yesterday O/H top 20%, C/L bottom 20%, today testing below",
            "reasoning": f"Classic 80-20 setup. Yesterday's exhaustion followed by today's test. Day trade only - exit before close.",
            "price_ranges": ["low"],
            "win_rate": "50.45%",
            "priority": "HIGH"
        }
    return None


def alpha_101(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(30).copy()
    if len(df) < 25:
        return None
    
    df["Daily_Range"] = df["High"] - df["Low"]
    df["ATR_20"] = ATR(df["High"], df["Low"], df["Close"], 20)
    df["Alpha101"] = (df["Close"] - df["Open"]) / (df["Daily_Range"] + 0.001)
    
    last = df.iloc[-1]
    
    if last["Daily_Range"] > last["ATR_20"] and abs(last["Alpha101"]) > 0.8:
        direction = "LONG" if last["Alpha101"] > 0 else "SHORT"
        price = last["Close"]
        atr = last["ATR_20"]
        stop = price - (atr * 1.5) if direction == "LONG" else price + (atr * 1.5)
        tp = price + (atr * 3) if direction == "LONG" else price - (atr * 3)
        
        return {
            "ticker": ticker,
            "strategy": "Alpha 101 (Price Velocity)",
            "type": direction,
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": tp,
            "holding_period": "Intraday",
            "confidence": 65,
            "signal": f"Strong directional velocity (Alpha={last['Alpha101']:.2f})",
            "reasoning": f"Price velocity scalper. Alpha={last['Alpha101']:.2f} indicates extreme directional conviction. Best as directional signal.",
            "price_ranges": ["all"],
            "win_rate": "N/A",
            "priority": "MEDIUM"
        }
    return None


def alpha_041(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(30).copy()
    if len(df) < 25:
        return None
    
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (typical * df["Volume"]).rolling(20).sum() / df["Volume"].rolling(20).sum()
    df["Median_Price"] = MedianPrice(df["High"], df["Low"])
    df["Alpha041"] = df["Median_Price"] - df["VWAP"]
    df["Alpha041_Pct"] = df["Alpha041"].pct_change()
    
    last = df.iloc[-1]
    
    if abs(last["Alpha041_Pct"]) > df["Alpha041_Pct"].std() * 2:
        direction = "LONG" if last["Alpha041_Pct"] < 0 else "SHORT"
        price = last["Close"]
        atr = ATR(df["High"], df["Low"], df["Close"], 14).iloc[-1]
        stop = price - (atr * 1.5) if direction == "LONG" else price + (atr * 1.5)
        tp = df["VWAP"].iloc[-1]
        
        return {
            "ticker": ticker,
            "strategy": "Alpha 041 (Median-VWAP)",
            "type": direction,
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": tp,
            "holding_period": "Intraday",
            "confidence": 70,
            "signal": f"Median-VWAP divergence at {last['Alpha041_Pct']*100:.2f}%",
            "reasoning": f"Median-VWAP mean reversion. Price deviated from fair value by {last['Alpha041_Pct']*100:.2f}%. Target VWAP.",
            "price_ranges": ["all"],
            "win_rate": "N/A",
            "priority": "MEDIUM"
        }
    return None


def orderflow_volume_profile(df: pd.DataFrame, ticker: str) -> Optional[Dict]:
    df = df[df["Ticker"] == ticker].sort_values("Date").tail(30).copy()
    if len(df) < 20:
        return None
    
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    df["VWAP"] = (typical * df["Volume"]).rolling(20).sum() / df["Volume"].rolling(20).sum()
    df["Volume_SMA20"] = VolumeSMA(df["Volume"], 20)
    df["Volume_Ratio"] = VolumeRatio(df["Volume"], 20)
    df["ATR_14"] = ATR(df["High"], df["Low"], df["Close"], 14)
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    above_vwap = last["Close"] > last["VWAP"]
    rejected = last["Close"] > prev["Close"] and last["Volume_Ratio"] > 1.5
    
    if above_vwap and rejected:
        price = last["Close"]
        atr = last["ATR_14"]
        stop = price - (atr * 1.5)
        tp = price + (atr * 3.0)
        return {
            "ticker": ticker,
            "strategy": "Orderflow/Volume Profile",
            "type": "LONG",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": tp,
            "holding_period": "Intraday",
            "confidence": 70,
            "signal": "VWAP rejection with volume spike",
            "reasoning": f"VWAP rejection long setup. Price rejected at VWAP with {last['Volume_Ratio']:.1f}x avg volume. 2:1 R:R target.",
            "price_ranges": ["mid"],
            "win_rate": "35%",
            "priority": "HIGH"
        }
    
    below_vwap = last["Close"] < last["VWAP"]
    if below_vwap and rejected:
        price = last["Close"]
        atr = last["ATR_14"]
        stop = price + (atr * 1.5)
        tp = price - (atr * 3.0)
        return {
            "ticker": ticker,
            "strategy": "Orderflow/Volume Profile",
            "type": "SHORT",
            "entry_price": price,
            "stop_loss": stop,
            "take_profit": tp,
            "holding_period": "Intraday",
            "confidence": 70,
            "signal": "VWAP rejection with volume spike (bearish)",
            "reasoning": f"VWAP rejection short setup. Price rejected at VWAP from below with volume. 2:1 R:R target.",
            "price_ranges": ["mid"],
            "win_rate": "35%",
            "priority": "HIGH"
        }
    return None


INTRADAY_STRATEGIES = [
    {"name": "4-Factor Overnight Model", "func": four_factor_overnight},
    {"name": "VSA Hidden Upthrust", "func": vsa_hidden_upthrust},
    {"name": "VSA Bag Holding", "func": vsa_bag_holding},
    {"name": "VSA Upthrust", "func": vsa_upthrust},
    {"name": "VSA Buying Climax (Intraday)", "func": vsa_buying_climax_intraday},
    {"name": "VSA Shakeout (Intraday)", "func": vsa_shakeout_intraday},
    {"name": "VPA No Demand", "func": vpa_no_demand},
    {"name": "VPA Hanging Man", "func": vpa_hanging_man},
    {"name": "ADX Gapper", "func": adx_gapper},
    {"name": "Momentum Pinball", "func": momentum_pinball},
    {"name": "80-20 Reversal", "func": eighty_twenty_reversal},
    {"name": "Alpha 101", "func": alpha_101},
    {"name": "Alpha 041", "func": alpha_041},
    {"name": "Orderflow/Volume Profile", "func": orderflow_volume_profile},
]
