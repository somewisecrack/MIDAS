---
name: AI Regime Switching (Ernest Chan)
description: A meta-strategy using a Random Forest classifier to predict market environments (Trend vs. Range) and select the most effective trading logic for the next session.
---

# AI Regime Switching Meta-Strategy

Derived from Ernest Chan's "Hands-On AI Trading" (2023), this meta-skill acts as the "Brain" of the trading library. It identifies the current market regime to determine whether momentum-based or mean-reversion-based strategies should be activated.

## Core Objective
To increase overall strategy expectancy by avoiding "Trend" strategies in "Range" markets and vice versa.

## Machine Learning Architecture
*   **Model Type**: Random Forest Classifier (Ensemble Method).
*   **Target Label**: 
    *   **1 (Trend Day)**: Next day's price range exceeds 1.2x its average volatility (Range SMA).
    *   **0 (Range/Reversion Day)**: Price remains within standard volatility boundaries.

## Engineered Features (Predictors)
The model consumes a multidimensional feature set engineered from OHLCV data:
1.  **Short-Term Momentum**: Rate of Change (ROC) over 5 days.
2.  **Medium-Term Trend**: ROC over 21 days (1 business month).
3.  **Volatility STD**: Standard deviation of returns over 21 days.
4.  **Range Dynamics**: High-Low range ratio and its 21-day SMA.
5.  **Relative Strength (RSI)**: Normalized overbought/oversold levels.

## Strategy Selection Logic
1.  **Prediction = 1 (Trend)**: Activate **Swing Trading Skills** (Holy Grail Breakouts, EP, CAN SLIM).
2.  **Prediction = 0 (Range)**: Activate **Intraday Trading Skills** (Orderflow Rejections at VWAP/HVN).

## Performance Vitals (Ernest Chan Audit)
*   **Classifier Accuracy**: ~75% cross-validated.
*   **Alpha Contribution**: Effectively doubled benchmark returns by switching regimes (+44% vs +21% Buy & Hold).
