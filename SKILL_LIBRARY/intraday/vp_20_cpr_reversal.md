---
description: Vikram Prabhu — CPR (Central Pivot Range) Reversal. Works best on BANKNIFTY 2m.
---

# VP-20: CPR Reversal
**Source**: Vikram Prabhu — 25 Day Trading Strategies PDF  
**Instruments**: NIFTY, BANKNIFTY  
**Timeframes**: 2m ✅✅ | 5m ⚠️ | 15m ⚠️  
**Direction**: Both Long & Short  

## 📊 Backtest Performance (60 days, yfinance)
| Symbol | TF | Trades | Win% | PF | Net Pts |
|---|---|---|---|---|---|
| NIFTY | 2m | 16 | **50.0%** | 1.13 | +134 |
| NIFTY | 5m | 39 | 51.3% | 0.91 | -180 |
| NIFTY | 15m | 26 | 46.2% | 0.69 | -517 |
| BANKNIFTY | 2m | 19 | **52.6%** | **1.75** | **+2126** |
| BANKNIFTY | 5m | 45 | 40.0% | 0.84 | -974 |
| BANKNIFTY | 15m | 38 | 52.6% | 0.96 | -211 |

**Best**: BANKNIFTY 2m (PF 1.75, 52.6% WR). Low frequency — only ~19 trades / 30 days.

## 🛠️ Setup Rules

### CPR Calculation (Previous Day)
- **TC (Top Central Pivot)** = (Yesterday's Pivot + Yesterday's High) / 2  
- **BC (Bottom Central Pivot)** = (Yesterday's Pivot + Yesterday's Low) / 2  
- **Pivot** = (Yesterday's H + L + C) / 3

### Short Entry (Rejection at TC)
1. Price approaches the **TC level** (within 50% of the CPR width as tolerance).
2. Current candle is **bearish** with upper wick > body (rejection candle).
3. Entry = close. SL = TC + (TC - BC).
4. Target = 2× risk.

### Long Entry (Bounce at BC)
1. Price approaches the **BC level** (within 50% of CPR width).
2. Current candle is **bullish** with lower wick > body (support bounce).
3. Entry = close. SL = BC - (TC - BC).
4. Target = 2× risk.

## 💡 Notes
- CPR is most powerful on **Narrow CPR days** (CPR width < 50% of 10-day average) — high trending potential.
- On Wide CPR days, the zone becomes congestion and is less reliable.
- BANKNIFTY 2m is the only combination worth systematically trading. Other TFs are losers.
- Very low signal frequency on 2m (~19 trades/30 days) — treat as a premium setup.
