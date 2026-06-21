---
description: 20-day breakout trend-following system.
---

# Turtle System 1 (S1)

Turtle System 1 is the core short-to-medium term trend-following component of the original Turtle Trading System. It is designed to capture intermediate breakouts using a strict mechanical entry and exit framework.

### 📊 Audit Performance
- **Primary Market**: **Large Cap (>$100)** 
- **Profit Factor**: **1.25** 
- **Win Rate**: **32.6%**
- **Verdict**: **APPROVED** (Strongest in High-Stability Stocks)

### 🛠️ Technical Rules

#### **1. Entry (The Breakout)**
- **Condition**: Buy/Short when price exceeds the high/low of the previous **20 days**.
- **Filter**: Skip the breakout if the previous System 1 signal (even if skipped) resulted in a profitable trade. 
- **Fail-safe**: If an S1 breakout is skipped due to the filter and the trend continues, the trade must be entered via System 2 (55-day).

#### **2. Position Sizing (N)**
- Calculate **N** (20-day Average True Range).
- **Unit Size** = `(1% Account Equity) / (N * Price_Scaling)`.
- **Unit Limit**: Maximum 4 units per ticker.

#### **3. Pyramiding**
- Add 1 unit at every **0.5N** price move in the direction of the trade.
- Adjust stop-loss for all units to 2N below/above the latest entry.

#### **4. Exit**
- **Condition**: Exit when price touches the **10-day** low (for longs) or high (for shorts).

### 💡 Best Practices
- **Large Caps**: This system works best in Large Cap stocks (>$100) where trends are less likely to be disrupted by noise.
- **Micro-Cap Inefficiency**: Audit showed negative expectancy for S1 in mid-cap stocks ($5-$20), likely due to high-frequency stop-outs.
