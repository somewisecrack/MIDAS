-----
name: Alpha 041 (Median-VWAP Mean Reversion)
description: A high-precision intraday mean reversion strategy that exploits the divergence between the median price (sqrt(H*L)) and the VWAP.
---

# Alpha 041: Median-Price Mean Reversion

Developed by Igor Tulchinsky (WorldQuant 101), this alpha identifies intraday price inefficiencies by comparing the geometric mean of the High/Low range with the Volume Weighted Average Price (VWAP).

## Strategy Logic

- **Formula**: `(((high * low)^0.5) - vwap)`
- **Core Concept**: The geometric mean of the high and low prices represents a "fair" intraday equilibrium. When this value deviates significantly from the VWAP (the actual price at which volume was executed), a mean-reverting trade opportunity exists.
- **Regime**: Works best in stable but liquid markets where institutional order flow causes temporary VWAP deviations.

## Performance Metrics (Audit)

- **Sharpe Ratio**: 1.20
- **Total Return**: 29.15% (2-year backtest)
- **Holding Period**: < 1 Day (Liquidate by EOD)

## Implementation Guidance

- **Entry**: Enter when the divergence between `sqrt(H*L)` and `VWAP` is at a local extreme (top or bottom percentile).
- **Exit**: Exit as the price reverts to VWAP or by the market close.
- **Risk Management**: Use a hard stop based on 1.5x ATR of the 1-minute chart.
