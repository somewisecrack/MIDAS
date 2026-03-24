---
description: The single most powerful exhaustion signal in the VPA framework.
---

# VPA Effort vs Result (Anomaly)

An **EvR Anomaly** occurs when there is a massive surge in volume (Effort) but virtually no price movement (Result). This indicates institutional "walling" or heavy absorption, typically signaling an imminent and violent reversal.

### 📊 Audit Performance (837 Tickers)
- **Primary Timeframe**: **Daily Swing** (PF 5.25)
- **Secondary Timeframe**: 5-Minute (PF 1.22), 15-Minute (PF 1.38)
- **Win Rate**: **58.3% (Daily)**
- **Performance by Price (Daily)**:
  - **<$5**: **PF 5.25** (Absolute Edge)
  - **$5-$20**: **PF 1.32**
  - **$20-$100**: **PF 1.25**
- **Verdict**: **ELITE** (Strongest signal in the library)

### 🛠️ Technical Rules

#### **Setup**
1.  **Anomaly**: volume is **Ultra-High** (>2.0x 20-day MA).
2.  **Narrow Spread**: Price spread is significantly smaller (<0.5 ATR) than the volume would suggest.
3.  **Context**: Occurs after a sustained move.

#### **Execution**
- **Entry**: Buy/Sell on the close of the anomaly bar.
- **Stop Loss**: Above/Below the anomaly bar's extreme.
- **Exit**: 3-bar hold or first sign of trend resumption.

### 💡 Best Practices
- **Wall Detection**: Think of this as price hitting a brick wall made of institutional orders.
- **Small Caps**: In sub-$5 stocks, this is often a 100% reversal signal.
