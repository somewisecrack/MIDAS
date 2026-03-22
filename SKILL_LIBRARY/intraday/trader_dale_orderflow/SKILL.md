---
name: Orderflow & Volume Profile (Trader Dale)
description: An institutional tracking strategy using intraday Volume Profile POC and VWAP to identify high-probability reversal and continuation levels.
---

# Orderflow & Volume Profile Trading Setups

Derived from Trader Dale's "Orderflow Trading Setups," this strategy focuses on trading alongside "smart money" by identifying price levels with high institutional interest.

## Core Concepts
*   **Volume Profile**: Visual representation of volume traded at specific price levels.
*   **POC (Point of Control)**: The price level with the highest volume in a given session or range.
*   **VWAP (Volume Weighted Average Price)**: The institutional benchmark for "fair value."

## Implementation Rules (Intraday)
1.  **VWAP Rejection**:
    - **Entry (Long)**: Price is in an intraday uptrend (above VWAP), pulls back to VWAP, and rejects it with a volume spike (>1.5x ADR volume).
    - **Entry (Short)**: Price is in an intraday downtrend (below VWAP), pulls back to VWAP, and is rejected with high volume.
2.  **Volume Accumulation (HVN Pullback)**:
    - Identify a consolidation range with a clear POC.
    - Wait for a breakout from this range.
    - Enter on the first pullback to the former POC (Support/Resistance).

## Risk Management (Vetted Defaults)
*   **Stop Loss**: 1.5x ATR (intraday).
*   **Take Profit**: 3.0x ATR (intraday) - Aim for 2:1 Reward-to-Risk.
*   **Timeframe**: 5-minute or 15-minute charts.

## Vetted Performance (60-Day Audit)
*   **Win Rate**: ~35% (Offset by high Reward:Risk).
*   **Edge**: Strongest in **Mid-Cap ($20-$100)** stocks.
*   **Institutional Robustness**: VWAP rejections are highly consistent in liquid, high-volume tickers.
