# Research: Trader Dale Orderflow & Volume Profile Setups

Trader Dale's methodology revolves around institutional activity tracking using Volume Profile and Orderflow (Footprint). Given our 5m and 1h OHLCV data, we focus on the **Volume Profile** and **VWAP** setups.

## Core Setups (adapted for OHLCV)

### 1. Volume Accumulation Setup
- **Logic**: Institutions accumulate positions in a ranging market, creating a high-volume node (HVN).
- **Trigger**: Price breaks out of the range.
- **Entry**: Trade the first pullback to the HVN (Support/Resistance).
- **Backtest Implementation**: Use 5m data to identify the POC (Point of Control) of a previous consolidation range.

### 2. Trend Setup
- **Logic**: During a trend, volume clusters form where institutions add to positions.
- **Trigger**: A significant volume cluster forms within a strong trend.
- **Entry**: Trade the test of this cluster.
- **Backtest Implementation**: Use a rolling Volume Profile to identify local HVNs in trending periods.

### 3. Rejection Setup
- **Logic**: Aggressive rejection of high/low prices, often seen as "buying/selling tails."
- **Trigger**: Price hits a level and is quickly rejected with high volume.
- **Entry**: Trade the continuation after the rejection candle.
- **Backtest Implementation**: Identify 5m candles with long wicks + volume spike (>2x ADV).

### 4. VWAP Bounce/Rejection
- **Logic**: VWAP is a key institutional benchmark.
- **Trigger**: Price touches VWAP after being extended.
- **Entry**: Rejection at VWAP or first touch in a trend.

---

## Data Sufficiency & Constraints
- **Orderflow (Delta/Imbalance)**: **Insufficient**. We do not have Bid/Ask volume breakdown.
- **Volume Profile (HVN/POC)**: **Sufficient**. Can be calculated from 5m/1h OHLCV.
- **VWAP**: **Sufficient**. Standard calculation using 5m data.

## Backtest Strategy
We will implement an intraday backtester using the **5m data** (60-day window) to test the **Volume Accumulation Pullback** and **VWAP Rejection** setups. 
- **Timeframe**: 5-minute charts.
- **Universe**: High-volume, liquid tickers (top 100).
- **Risk Management**: Fixed Stop Loss and Take Profit based on ATR or predefined multiples.
