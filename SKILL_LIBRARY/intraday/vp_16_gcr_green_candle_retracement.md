---
description: Vikram Prabhu — GCR (Green Candle Retracement). 50% pullback re-entry after a power green candle.
---

# VP-16: GCR — Green Candle Retracement
**Source**: Vikram Prabhu — 25 Day Trading Strategies PDF  
**Instruments**: NIFTY, BANKNIFTY  
**Timeframes**: 2m ⚠️ | 5m ❌ | 15m ⚠️  
**Direction**: Long only  

## 📊 Backtest Performance (60 days, yfinance)
| Symbol | TF | Trades | Win% | PF | Net Pts |
|---|---|---|---|---|---|
| NIFTY | 2m | 71 | 32.4% | 1.16 | +154 |
| NIFTY | 5m | 41 | 22.0% | 0.43 | -570 |
| NIFTY | 15m | 10 | 40.0% | 0.58 | -160 |
| BANKNIFTY | 2m | 61 | 37.7% | 1.16 | +447 |
| BANKNIFTY | 5m | 46 | 34.8% | 0.85 | -403 |
| BANKNIFTY | 15m | 14 | 28.6% | 1.07 | +72 |

**Verdict**: Only marginally positive on 2m. Avoid 5m and 15m.

## 🛠️ Setup Rules

### Long Entry
1. A **bullish Power Candle** appeared in the last 10 bars (body >75% of range, large range).
2. Price retraces and **touches the 50% level** of that green candle's body (midpoint of open-to-close).
3. Current candle is **bullish** and closes above that 50% level.
4. Price must be **above EMA20**.
5. Entry = close. SL = low of the Power Candle.
6. Target = 2× risk.

## 💡 Notes
- Concept: The power green candle is an institutional buy order. The 50% retracement is where remaining buy orders are likely sitting.
- Works better as a concept than a systematic strategy. 5m results are notably poor.
- Best combined with a Pivot or EMA support at the 50% level for higher probability.
