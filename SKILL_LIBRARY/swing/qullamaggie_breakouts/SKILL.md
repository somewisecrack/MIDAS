---
name: Qullamaggie Breakout Strategy
description: Long-only strategy focused on High Tight Flags and breakout setups using ADR-based risk and multi-tier triggers.
---

# Qullamaggie Breakout Strategy

Based on the [3 timely setups](https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/) used by Kristjan Kullamägi.

## 1. The Strategy Setup
### Core Criteria
- **The Big Move**: 30% to 100%+ move higher in the past 1-3 months.
- **Orderly Pullback**: Consolidation near the 10-day or 20-day SMA with tightening price range.
- **Trend Alignment**: Price must remain above the 10-day and 20-day SMAs.

## 2. Execution Rules
### Entry Signal
- **Opening Range High (ORH)**: High of the first 5-minute (or 60-minute) candle.
- **Trigger**: Enter when the price breaks above the ORH during the trading session.

### Stop Loss & Risk Management
- **Initial Stop**: Low of the Day (LOD).
- **ADR Filter**: Skip setups where the risk (Entry - Stop) exceeds the 20-day Average Daily Range (ADR) or 10% of stock price.
- **Partial Exit**: Sell 50% of the position after 3 trading days.
- **Stop Adjustment**: Move the remaining stop to **Breakeven (Entry Price)** after the partial exit.

### Final Exit
- **SMA Trail**: Trail the remaining 50% using the 10-day Moving Average. Exit on the first daily close below SMA10.

## 3. Proven Backtest Performance
Verified through a hybrid multi-timeframe backtest on 837 tickers (4+ years history).

### Aggregate Statistics
- **Trade Count**: 2,660 (Highly selective)
- **Win Rate**: `15.86%`
- **Total Expectancy**: **Positive (+0.33% Avg PnL)**
- **Max Gain**: `+124.32%` (Large-cap institutional breakout)

### Performance by Price Range
| Category | Trade Count | Win Rate | Avg PnL | Max Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Penny Stocks (<$5)** | 73 | 16.4% | **+3.13%** | 99.4% |
| **Low Price ($5-$20)** | 313 | 14.1% | +0.86% | 69.7% |
| **Mid Price ($20-$100)** | 1,099 | 15.9% | -0.05% | 59.9% |
| **High Price (>$100)** | 1,175 | 16.3% | +0.38% | **124.3%** |

## 4. Key Strategic Insights
- **The "Fat Tail" System**: Profitability is driven by rare, massive winners (99%+ to 124%+) rather than consistent small wins.
- **Efficiency**: Waiting for the ORH trigger significantly reduces "fakeouts" compared to entry at the daily open.
- **Risk Efficiency**: The ADR filter is critical for avoiding "washouts" in overly volatile setups.
