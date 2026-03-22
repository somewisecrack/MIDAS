# Research: Toby Crabel's Day Trading Patterns

## 1. Core Concepts

### Opening Range Breakout (ORB)
- **Trade**: A breakout entry at a calculated distance from the opening range.
- **The Stretch**: A mathematical variable used to determine the breakout threshold.
  - **Calculation**: Average of the last 10 days' `min(High - Open, Open - Low)`.
- **Entry**: 
  - Buy at `Opening Range High + Stretch`.
  - Sell at `Opening Range Low - Stretch`.
- **ORBP (Preference)**: Entering only in the direction of the trend bias (e.g., after an Inside Day or Gap).

### Narrow Range Patterns
- **NR7**: The current day's high-low range is the narrowest of the last 7 trading days.
- **NR4**: The current day's high-low range is the narrowest of the last 4 trading days.
- **ID (Inside Day)**: Current High < Prev High AND Current Low > Prev Low.
- **IDnr4**: An Inside Day that is also an NR4.

### Hook Day
- **Definition**: Opens outside the previous day's range (above High or below Low), then reverses to close within the previous range/towards the close, but with a range narrower than the previous day.

## 2. Trading Rules

### Entry Timing
- "The earlier in the session the entry is taken the better."
- Ideal entry is within the first 10-30 minutes.

### Risk Management
- **Initial Stop**: The opposite side of the breakout (the other stop order).
- **Breakeven**: Move stop to breakeven within 1 hour if the trade is moving in your favor.
- **Scaling**: Adjust position size downward as the day progresses (late entries have lower probability).

### Exit Strategy
- **Intraday**: Exit at the end of the session if the profit is not "substantial."
- **Swing**: Hold for 2-3 days if a significant profit is realized by the end of the first day.

## 3. Implementation Strategy for Backtest
- We will focus on the **NR7 + ORB** and **Inside Day + ORB** combinations as they are the highest probability setups according to Crabel.
- **Stretch** will be calculated as a 10-day rolling average of the minimum distance from the open to the day's extreme.
