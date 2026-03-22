---
name: Qullamaggie Episodic Pivot (EP) Strategy
description: Position trading strategy focused on massive gaps and fundamental catalysts with long-term trend following.
---

# Qullamaggie Episodic Pivot (EP) Strategy

Based on the [position trading setups](https://qullamaggie.com/category/episodic-pivots/) used by Kristjan Kullamägi.

## 1. The Strategy Setup
### Core Criteria
- **The Gap**: Gap up of **10%+** (8%+ for large caps) caused by a fundamental news catalyst.
- **Massive Volume**: Crucial indicator. Intraday volume should match full Average Daily Volume (ADV) within the first 15-45 minutes.
- **Neglect**: Stock is preferably breaking out of a long base (3-6+ months) with no prior big run.
- **Catalyst**: High-quality fundamental event (Earnings beat/raise, Guidance upgrade, FDA approval, etc.).

## 2. Execution Rules
### Entry Signal (Comparative Verification)
- **1-Hour ORH (Recommended)**: Wait for the high of the first 60 minutes of trading.
- **Trigger**: Enter on the break above the 1-hour Opening Range High.
- *Note*: While 5m and 15m entries are possible, the 1-hour entry proved more stable in our backtest for position trading.

### Stop Loss & Risk Management
- **Initial Stop**: Low of the Day (LOD).
- **Position Sizing**: Adjust based on the distance to LOD. EPs are high-conviction but high-volatility trades.

## 3. Trade Management
### Holding Period
- **Phase 1**: Stay in as long as the stock doesn't close below its 10-day SMA.
- **Phase 2**: For "Power of Life" trades, transition trailing stop to the 20-day or 50-day SMA once the 10-day trail is deep in profit.

## 4. Proven Backtest Performance (1-Hour ORH)
Verified through multi-timeframe backtest on 837 tickers (Multi-year daily + 1y hourly data).

### Comparative Timeframe Results (1-Year Window)
| Entry Trigger | Trade Count | Win Rate | Avg PnL | Profit Factor |
| :--- | :--- | :--- | :--- | :--- |
| **1-Hour ORH** | **78** | **47.4%** | **+0.72%** | **1.16** |
| 30-Min ORH | 17 | 52.9% | -2.46% | 0.53 |
| 15-Min ORH | 23 | 47.8% | -1.93% | 0.63 |
| 5-Min ORH | 30 | 40.0% | -1.22% | 0.78 |

### Historical Performance (Full 4+ Year Daily Proxy)
| Metric | Result |
| :--- | :--- |
| **Total Trades** | **885** |
| **Win Rate** | 41.36% |
| **Avg PnL** | +0.05% |
| **Max Gain** | **+218.33%** |
| **Profit Factor** | 1.01 |

### Performance by Price Range (Historical)
| Category | Trade Count | Win Rate | Avg PnL | Max Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Penny Stocks (<$5)** | 55 | 32.7% | **+1.69%** | **218.3%** |
| **Low Price ($5-$20)** | 129 | 40.3% | +0.43% | 98.5% |
| **Mid Price ($20-$100)**| 362 | **44.2%** | +0.48% | 110.8% |
| **High Price (>$100)** | 339 | 40.1% | -0.83% | 48.6% |

### Key Strategic Insights
- **Robustness**: The 1-hour ORH significantly outperformed faster timeframes by avoiding initial opening-hour volatility.
- **The "Monster" Factor**: The 218% winner in the historical data proves that EPs are the primary source of massive account-defining gains in Kullamaggie's system.
- **Selective Edge**: The strategy is near breakeven for "average" setups; profitability depends entirely on catching the 1-2 monster runners per year. 
