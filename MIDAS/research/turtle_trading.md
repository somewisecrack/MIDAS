# Research: Michael Covel "The Complete TurtleTrader"

The Turtle Trading System is a comprehensive trend-following strategy developed by Richard Dennis and William Eckhardt. It is entirely mechanical, covering what to buy, how much to buy, and when to get out.

## 5-Stage Audit Targets

### Stage 1: Strategy Extraction
1. **Turtle System 1 (S1)**: 20-day breakout entry. 10-day breakout exit.
   - *Filter Rule*: Skip S1 if the previous S1 breakout was a winner (theoretical or real).
2. **Turtle System 2 (S2)**: 55-day breakout entry. 20-day breakout exit. 
   - *Fail-safe*: No filter; captures trends missed by S1.
3. **Volatility (N)**: 20-day ATR (Average True Range).
4. **Position Sizing**: 1% risk per N per unit.
5. **Pyramiding**: Max 4 units added at 0.5N intervals.

### Stage 2: Technical Engine
- **Donchian Channels**: 20, 55, 10, and 20 day lookbacks.
- **N-Unit Logic**: Dynamic position sizing based on ATR14 or ATR20.
- **Pyramiding Engine**: Tracking multiple entries and trailing stops.

### Stage 3: Backtesting execution
- **Ticker Universe**: `tickers_ohlcv.csv` (837 tickers).
- **Metric Emphasis**: CAGR, Max Drawdown, and Sharpe Ratio (Trend-following metrics).

### Stage 4: Classification by Stock Price Range
- Audit results classified across `<$5`, `$5-$20`, `$20-$100`, `>$100`.

### Stage 5: Skill Formalization
- Formalize S1 and S2 into the `swing_trading_skills` library.

## Core Formula: Turtle Position Sizing (The "N")
`N = (19 * Previous_N + True_Range) / 20`
`Unit = (Account * 0.01) / (N * Price_Scaling)`

## Backtest Constraints
- Entries only on breakouts.
- Stops at 2N.
- Pyramiding enabled up to 4 units.
