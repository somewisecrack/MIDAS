---
description: Vikram Prabhu — Supply Zone Reversal. Best on NIFTY 15m. Avoid BANKNIFTY.
---

# VP-22: Supply Zone Reversal
**Source**: Vikram Prabhu — 25 Day Trading Strategies PDF  
**Instruments**: NIFTY only (BANKNIFTY underperforms)  
**Timeframes**: 2m ✅ | 5m ⚠️ | 15m ✅✅  
**Direction**: Short only  

## 📊 Backtest Performance (60 days, yfinance)
| Symbol | TF | Trades | Win% | PF | Net Pts |
|---|---|---|---|---|---|
| NIFTY | 2m | 50 | 44.0% | **1.35** | **+577** |
| NIFTY | 5m | 45 | 46.7% | 1.04 | +63 |
| NIFTY | 15m | 11 | **54.5%** | **1.71** | **+216** |
| BANKNIFTY | 2m | 56 | 32.1% | 0.81 | -1120 |
| BANKNIFTY | 5m | 58 | 37.9% | 0.86 | -646 |
| BANKNIFTY | 15m | 17 | 41.2% | 0.98 | -15 |

**Best**: NIFTY 15m (PF 1.71, 54.5% WR) | NIFTY 2m (PF 1.35)  
**Avoid**: BANKNIFTY — all timeframes show PF < 1

## 🛠️ Setup Rules

### Zone Identification
1. In the last 40 bars (excluding the most recent 5), find all **swing highs** (local peaks).
2. The **Supply Zone** = top of the highest swing high ± 0.2%.

### Short Entry
3. Current price enters the supply zone (close within the zone, up to 0.2% below the top).
4. Current candle is **bearish** with upper wick > body (rejection at supply).
5. Entry = close. SL = zone top + 0.2%.
6. Target = 2× risk.

## 💡 Notes
- Supply zones represent areas where institutions previously sold aggressively — they tend to sell again when price returns.
- **Only systematic for NIFTY.** BANKNIFTY supply zones are frequently broken due to higher volatility.
- The 15m timeframe provides cleaner zone identification — fewer false signals.
- Avoid on strong trending up days (entire price structure making higher highs).
