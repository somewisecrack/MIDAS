# Skill: Camarilla H4 Breakout (Pivot Boss)

## Overview
A momentum-based continuation strategy that identifies strong breakout conviction beyond the H4 Camarilla level. This setup is highly effective in trending markets.

## Setup Criteria
1. **Level Calculation**:
   - **Range** = High - Low (from the previous session).
   - **H4 Resistance** = Close(prev) + Range * 1.1 / 2.
2. **Trigger**:
   - A Daily **Close** above the H4 level.
3. **Context**:
   - Most robust when coming out of a narrow value range or a multi-day consolidation.

## Performance Profile (Backtest Results)
- **Win Rate**: 60.16%
- **Average 3-Day Return**: +2.40%
- **Data Source**: Tested across all available tickers in `tickers_ohlcv.csv`.

## Execution Rules
- **Entry**: Buy at the market close on the breakout day (Day 0).
- **Exit**: End-of-Day (EOD) on the 3rd following session (Day 3).
- **Note**: Avoid shorting the L4 breakout (Bearish counter-part) which historically shows a negative edge (-3.04% average 3-day return).

## Backtest Logic (Python Snippet)
```python
prev_range = High.shift(1) - Low.shift(1)
H4 = Close.shift(1) + prev_range * 1.1 / 2
Is_Breakout = Close > H4
Forward_Return = Close.shift(-3) / Close - 1
```
