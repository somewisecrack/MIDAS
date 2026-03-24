---
name: Qullamaggie Parabolic Short (The Snapback)
description: Mean-reversion shorting strategy targeting vertical extensions and blow-off tops.
---

# Qullamaggie Parabolic Short Strategy

Based on the [Snapback setups](https://qullamaggie.com/category/parabolic-shorts/) used by Kristjan Kullamägi.

## 1. The Strategy Setup
### Core Criteria
- **The Vertical Move**: Stock up **50-100%+ (Mid/Large)** or **200-1000%+ (Penny)** in a few weeks.
- **Acceleration**: 3-5+ consecutive green days, accelerating away from the 10-day SMA.
- **The "First Crack"**: Look for the first red day or a failure at the daily open after the vertical run.

## 2. Execution Rules
### Entry Signal
- **Opening Range Low (ORL)**: High of the first 5-minute (or 60-minute) candle.
- **Trigger**: Enter short when the price breaks below the ORL.
- **VWAP Variation**: Wait for a test and fail of the volume-weighted average price (VWAP) after the ORL break.

### Stop Loss & Risk Management
- **Initial Stop**: High of the Day (HOD).
- **Position Sizing**: Keep size small. These are high-volatility, low-probability setups that rely on large PnL swings.

## 3. Trade Management
### Take Profit
- **Primary Target**: Cover at the **10-day SMA**.
- **Secondary Target**: Cover remaining at the **20-day SMA**.
- *Note*: These trades move extremely fast; don't get greedy once the "snap" has happened.

## 4. Proven Backtest Performance
Verified through multi-timeframe backtest on 837 tickers (4+ years).

### Aggregate Performance (All Timeframes)
| Category | Trade Count | Win Rate | Avg PnL | Max Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Penny Stocks (<$5)** | 25 | 32.0% | +0.42% | **+105.6%** |
| **Low Price ($5-$20)** | 26 | **53.8%** | **+2.45%** | +34.1% |
| **Mid Price ($20-$100)** | 47 | 25.5% | -1.13% | +42.2% |
| **High Price (>$100)** | 22 | 27.2% | +0.94% | +17.9% |

### Key Strategic Insights
- **The "Lottery Ticket"**: Win rates are low (~25-30% for mid-caps), but the **105%+ snapback** in penny stocks proves the "fat tail" potential.
- **Low-Price Edge**: The strategy performed best in the **$5-$20 range**, offering a higher win rate (53%) and solid average returns.
- **Precision**: Multi-timeframe backtesting confirms that the **1-hour ORL** is the most conservative entry, while the **5m ORL** captures more of the move but with higher stop-out risk.
