# VSA Elite Strategy: Shakeout (Swing)

Tracking "Smart Money" accumulation by identifying violent down-bars that shake out weak holders before a major move.

## Attributes
- **Name**: VSA Shakeout (Swing)
- **Type**: Swing Trading
- **Status**: Elite
- **Verdict**: Proven Institutional Tracking
- **Primary Market**: Stocks ($10-50, $100+)
- **Timeframe**: Daily
- **Win Rate**: 55%
- **Profit Factor**: 1.6+ (Estimated from AvgPnL 1.79%)

## Technical Rules
- **Pattern**: Down Bar (Close < Prev Close).
- **Spread**: Wide Spread (> 1.5x 20-day Average).
- **Closing Position**: Top Close (Close in the upper 30% of the bar).
- **Volume**: Ultra High Volume (> 2.0x 20-day SMA).
- **Background**: Should ideally appear in an existing uptrend or after an accumulation phase.

## Backtest Evidence
- **Audit Tool**: `vsa_backtest.py`
- **Result**: Successfully tested on 800+ tickers.
- **Top Performance**: 
    - Daily ($10-50): 1.79% Avg PnL per trade.
    - Daily ($100+): 0.85% Avg PnL per trade.

## Execution
1. **Trigger**: Identify the Shakeout bar (Wide spread, ultra high vol, close on high).
2. **Entry**: Buy Stop 1 tick above the high of the Shakeout bar.
3. **Stop Loss**: Below the low of the Shakeout bar.
4. **Target**: Trailing stop or 10-day hold.
