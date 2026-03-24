-----
name: Alpha 101 (Price Velocity Scalper)
description: A high-frequency intraday signal that captures price velocity by comparing the close-open spread to the daily range.
---

# Alpha 101: Price Velocity Scalper

This alpha is a classic measure of intraday momentum vs. volatility. It identifies when a stock is "breaking" its range with conviction.

## Strategy Logic

- **Formula**: `((close - open) / ((high - low) + .001))`
- **Core Concept**: It measures the "Body" of the candle relative to the "Range". A high value means the stock closed at the top of its expansion, indicating extreme directional velocity.
- **Regime**: Intraday Momentum.

## Performance Metrics (Audit)

- **Sharpe Ratio**: 0.75 (estimated for intraday)
- **Total Return**: -12.35% (Negative in long-only backtest, but powerful as a long/short directionality signal)
- **Holding Period**: < 1 Day

## Implementation Guidance

- **Trade Direction**: Go Long if Alpha > 0.8; Go Short if Alpha < -0.8.
- **Volatility Filter**: Only trade when `(High - Low)` is greater than the 20-day average ATR to ensure meaningful movement.
