-----
name: Alpha 022 (Volatility-Volume Divergence)
description: A swing trading strategy that identifies exhaustion in price trends by measuring the delta of the high-price/volume correlation.
---

# Alpha 022: Volatility-Volume Divergence

This alpha captures the "Exhaustion" phase of a trend. It looks for periods where the correlation between high prices and trading volume is changing rapidly, filtered by high-volatility price action.

## Strategy Logic

- **Formula**: `-1 * (delta(correlation(high, volume, 5), 5) * rank(ts_std(close, 20)))`
- **Core Concept**: A healthy trend should have high correlation between rising prices and rising volume. If this correlation starts to break down (delta is negative) while volatility is high (`rank(ts_std)`), it indicates a high-probability reversal.
- **Regime**: Ideal for Swing Trading in high-momentum stocks.

## Performance Metrics (Audit)

- **Sharpe Ratio**: 0.90
- **Total Return**: 4.21%
- **Holding Period**: 2–5 Days

## Implementation Guidance

- **Scanning**: Rank your universe by Alpha 022. The most negative values indicate the highest exhaustion risk (and thus the best short/reversal entries).
- **Confirmation**: Use in conjunction with a Meta Skill (like Chan AI Regime) to ensure you aren't fighting a major macro pump.
