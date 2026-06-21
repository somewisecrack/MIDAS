---
description: 55-day breakout long-term trend-following system.
---

# Turtle System 2 (S2)

Turtle System 2 is the "fail-safe" long-term trend-following component of the original Turtle Trading System. It is designed to capture major macro-trends that might have been filtered out by the more aggressive System 1 rules.

### 📊 Audit Performance
- **Primary Market**: **Micro-Cap (<$5)**
- **Profit Factor**: **1.55**
- **Win Rate**: **25.1%**
- **Verdict**: **APPROVED** (Elite for Penny Stock Power-Trends)

### 🛠️ Technical Rules

#### **1. Entry (The Breakout)**
- **Condition**: Buy/Short when price exceeds the high/low of the previous **55 days**.
- **Filter**: No filter exists for System 2. All signals must be taken.

#### **2. Position Sizing (N)**
- Calculate **N** (20-day Average True Range).
- **Unit Size** = `(1% Account Equity) / (N * Price_Scaling)`.

#### **3. Pyramiding**
- Add 1 unit at every **0.5N** price move.
- Maximum 4 units per ticker.

#### **4. Exit**
- **Condition**: Exit when price touches the **20-day** low (for longs) or high (for shorts).

### 💡 Best Practices
- **Volatility Reaping**: System 2 excels in hunting for explosive breakouts in stocks under $5. These stocks often have low historical volatility (N) but high latent kinetic energy; once they break a 55-day high, they often trend for months.
- **Patience**: S2 has the lowest win rate in the library (~25%). Expect a high number of break-even or small-loss trades compensated by massive multi-bagger runners.
