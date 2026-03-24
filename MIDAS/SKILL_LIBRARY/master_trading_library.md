# Master Trading Library

A comprehensive repository of all audited and formalized trading strategies.

## Table of Contents
- [Swing Trading Skills](#swing-trading-skills)
  - [Alpha 011: Volatility/Volume Expansion](#alpha-011:-volatility/volume-expansion)
  - [Alpha 022: Volatility-Volume Divergence](#alpha-022:-volatility-volume-divergence)
  - [Systematic Momentum Strategy](#systematic-momentum-strategy)
  - [Runaway Momentum Strategy](#runaway-momentum-strategy)
  - [The Holy Grail (ADX Pullback)](#the-holy-grail-(adx-pullback))
  - [Minervini SEPA Strategy](#minervini-sepa-strategy)
  - [CAN SLIM Technical Core Strategy](#can-slim-technical-core-strategy)
  - [Qullamaggie Breakout Strategy](#qullamaggie-breakout-strategy)
  - [Qullamaggie Episodic Pivot (EP) Strategy](#qullamaggie-episodic-pivot-(ep)-strategy)
  - [Qullamaggie Parabolic Short Strategy](#qullamaggie-parabolic-short-strategy)
  - [The Anti (Retracement Setup)](#the-anti-(retracement-setup))
  - [Three Little Indians (Climax Reversal)](#three-little-indians-(climax-reversal))
  - [Turtle Soup Master (Reversal Patterns)](#turtle-soup-master-(reversal-patterns))
  - [Turtle System 1 (S1)](#turtle-system-1-(s1))
  - [Turtle System 2 (S2)](#turtle-system-2-(s2))
  - [VPA Buying Climax (Exhaustion)](#vpa-buying-climax-(exhaustion))
  - [VPA Effort vs Result (Anomaly)](#vpa-effort-vs-result-(anomaly))
  - [VPA Selling Climax (Exhaustion)](#vpa-selling-climax-(exhaustion))
  - [VPA Stopping Volume (Absorption)](#vpa-stopping-volume-(absorption))
  - [VPA Topping Out Volume](#vpa-topping-out-volume)
  - [VSA Elite Strategy: Shakeout (Swing)](#vsa-elite-strategy:-shakeout-(swing))
- [Intraday Trading Skills](#intraday-trading-skills)
  - [4-Factor Overnight Model](#4-factor-overnight-model)
  - [80-20 Reversal (Intraday)](#80-20-reversal-(intraday))
  - [ADX Gapper (Intraday/Swing)](#adx-gapper-(intraday/swing))
  - [Alpha 041: Median-Price Mean Reversion](#alpha-041:-median-price-mean-reversion)
  - [Alpha 101: Price Velocity Scalper](#alpha-101:-price-velocity-scalper)
  - [Momentum Pinball (Intraday/Swing)](#momentum-pinball-(intraday/swing))
  - [Orderflow & Volume Profile Trading Setups](#orderflow-&-volume-profile-trading-setups)
  - [VPA Hanging Man (Intraday)](#vpa-hanging-man-(intraday))
  - [VPA No Demand Test (Intraday)](#vpa-no-demand-test-(intraday))
  - [VSA Approved Strategy: Bag Holding](#vsa-approved-strategy:-bag-holding)
  - [VSA Approved Strategy: Buying Climax](#vsa-approved-strategy:-buying-climax)
  - [VSA Approved Strategy: Hidden Upthrust](#vsa-approved-strategy:-hidden-upthrust)
  - [VSA Elite Strategy: Shakeout (Intraday)](#vsa-elite-strategy:-shakeout-(intraday))
  - [VSA Approved Strategy: Upthrust](#vsa-approved-strategy:-upthrust)
- [Meta Trading Skills](#meta-trading-skills)
  - [AI Regime Switching Meta-Strategy](#ai-regime-switching-meta-strategy)
  - [Stock Market Logic (Fosback)](#stock-market-logic-(fosback))

---

## Swing Trading Skills

# Alpha 011: Volatility/Volume Expansion

This alpha identifies stocks starting a high-conviction breakout by measuring where the market is most "active" relative to the volume delta.

## Strategy Logic

- **Formula**: `(rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3))`
- **Core Concept**: It captures the "Squeeze". If the distance between VWAP and Close is reaching local extremes while volume is increasing significantly over a 3-day window, a powerful swing move is imminent.
- **Regime**: Volatility Breakout.

## Performance Metrics (Audit)

- **Sharpe Ratio**: 0.80
- **Total Return**: 14.20%
- **Holding Period**: 3–7 Days

## Implementation Guidance

- **Screening**: Look for the highest-ranked tickers in your universe at the close.
- **Stop Loss**: Place stops at the 3-day Low.

---

# Alpha 022: Volatility-Volume Divergence

This alpha captures the "Exhaustion" phase of a trend. It looks for periods where the correlation between high prices and trading volume is changing rapidly, filtered by high-volatility price action.

## Strategy Logic

- **Formula**: `-1 * (delta(correlation(high, volume, 5), 5) * rank(ts_std(close, 20)))`
- **Core Concept**: A healthy trend should have high correlation between rising prices and rising volume. If this correlation starts to break down (delta is negative) while volatility is high (`rank(ts_std)`), it indicates a high-probability reversal.
- **Regime**: Ideal for Swing Trading in high-momentum stocks.

## Performance Metrics (Audit)

- **Sharpe Ratio**: 0.90
- **Total Return**: 4.21%
- **Holding Period**: 2–5 Days

## Implementation Guidance

- **Scanning**: Rank your universe by Alpha 022. The most negative values indicate the highest exhaustion risk (and thus the best short/reversal entries).
- **Confirmation**: Use in conjunction with a Meta Skill (like Chan AI Regime) to ensure you aren't fighting a major macro pump.

---

# Systematic Momentum Strategy

Derived from Andrew Ang's "Asset Management: A Systematic Approach to Factor Investing," this strategy shifts focus from individual "setups" to a diversified portfolio of factor leaders.

## Core Factor: 12-1 Momentum
*   **Ranking Window**: Total return over the last 12 months (approx. 252 trading days).
*   **The Reversal Bypass**: Exclude the most recent month (approx. 21 trading days) to avoid short-term "mean reversion" noise.
*   **Formula**: `(Price[t-21] / Price[t-252]) - 1`

## Implementation Rules
1.  **Universe**: Broad liquid stocks (e.g., S&P 1500 or similar filtered for liquidity).
2.  **Frequency**: Monthly rebalancing (approx. every 21 trading days).
3.  **Selection**: Top 10-20 stocks with the highest 12-1 momentum score.
4.  **Weighting**: Equal weight across all selected leaders.
5.  **Rebalance**: On each rebalance date, exit any stock no longer in the top rankings and replace with new leaders.

## Risk Management
*   **Diversification**: Systematic exposure to the momentum factor across multiple tickers reduces single-stock risk.
*   **Broad Exposure**: This is a "long-only" factor tilting strategy.
*   **Market Environment**: Momentum typically performs well in trending markets but can suffer during "momentum crashes" (sudden violent reversals).

## Vetted Performance
*   **Backtest Return**: 649.84% (4-year history).
*   **Market Context**: Captured extreme leaders (SMCI, NVDA, VRT) during their primary advances.

---

# Runaway Momentum Strategy

Derived from Mark Boucher's "The Hedge Fund Edge," this strategy identifies stocks enters an explosive "runaway" phase.

## 1. Setup Criteria
- **Runaway Spark**: Stock must have gained **30%+ in the last 40 trading days**.
- **The Tight Flag**: A 15-20 day consolidation period where the price fluctuates less than **25%** from high to low.
- **RS Rating**: Must be in the top 20% of the market (**RS Rating > 80**).

## 2. Entry Triggers (TBBLBG)
Enter on the first sign of the flag resolves to the upside:
- **Thrust**: Price closes above the flag's high.
- **Gap/Lap**: Opening price is above the flag's high or the previous day's high.

## 3. Risk Management
- **Initial Stop**: **7% Hard Stop** or the **Low of the Flag Base**, whichever is tighter.
- **Trailing Stop**: Exit on a daily close below the **10-day SMA** or after a **40% correction** from the peak of the new move.
- **Position Sizing**: Boucher recommends a maximum of 2% total portfolio risk per trade.

## 4. Backtest Performance Proof
Verified across 837 tickers over a 4-year daily history.

### Results by Price Range
| Price Category | Trade Count | Win Rate | Avg PnL | Max Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Mid-Price ($20-$100)** | 511 | **42.5%** | **+1.12%** | **+49.4%** |
| **High-Price (>$100)** | 546 | 41.0% | +0.57% | +42.2% |
| **Low-Price ($5-$20)** | 69 | 30.4% | +1.86% | +40.3% |

### Strategic Takeaways
- **Efficiency**: The strategy has a high win rate (>40%) in liquid stocks, making it a reliable trend-following component.
- **Institutional Alignment**: Best performance found in Mid and High-price tiers, aligning with Boucher's focus on quality institutional winners.
- **Explosive Potential**: Capable of single-trade gains near 50% within a medium-term swing timeframe.

---

# The Holy Grail (ADX Pullback)

**The Holy Grail** is a precise retracement method used to capture the first major pullback in a strongly trending market. It uses the ADX to filter for high-velocity environments where pullbacks are high-probability entries.

### 📊 Audit Performance
- **Win Rate**: **59.98%** (Optimized Entry)
- **Average PnL**: **1.03%**
- **Profit Factor**: **1.88** (Audit Initial)
- **Verdict**: **APPROVED** (Requires Manual Exit Management)

### 🛠️ Technical Rules

#### **Setup (Buy)**
1.  **Trend Filter**: 14-period ADX must be greater than 30 and rising.
2.  **Pullback**: Price retraces to touch the **20-period Exponential Moving Average (EMA)**.
3.  **The Trigger**: Place a buy stop above the high of the bar that touched the 20-EMA.
4.  **Initial Stop**: At the newly formed swing low.
5.  **Exit Strategy**: Target the most recent swing high (prior to the pullback). If the trend is exceptional, exit half at the high and trail the rest.

### 💡 Best Practices
- **First Pullback Only**: The highest probability is the *first* touch of the 20-EMA after the ADX crosses 30.
- **Re-Entry**: If stopped out but the ADX remains above 30 and rising, re-place the buy stop at the original trigger price.
- **Counter-Trend ADX**: Do not confuse a turndown in ADX with a trend reversal; it usually just signals the consolidation that creates the "Grail" setup.

---

# Minervini SEPA (Elite Technical Core)

Based on the methodology developed by Mark Minervini in *"Trade Like a Stock Market Wizard"* (2013). This version represents the **Elite Audit (2026)** which isolated "The Cheat" and "Deep VCP" setups.

## 📊 Audit Performance (2021-2026)
- **Primary Strategy (The Cheat)**: **+1.84% Mean Return** (1,198 trades).
- **Secondary Strategy (Deep VCP)**: **+2.64% Mean Return** (94 trades).
- **Core Strategy (Standard Base)**: +0.96% Mean Return.
- **Top Efficiency Tier**: **Mid-Price ($20-$100)** stocks with **+1.72% mean return**.
- **Regime Performance**: Effectively shielded capital in 2022 (-4.4% trade mean) and excelled in 2024 (+2.7% mean).
- **Verdict**: **ELITE** (Universal Stage 2 Qualifier)

## 🛠️ Technical Selection (The Trend Template)
Before any entry, the stock MUST meet these 8 criteria (Stage 2 Uptrend):
1. **Price > SMA150 and Price > SMA200**
2. **SMA150 > SMA200**
3. **SMA200 is trending up** (at least for 1 month).
4. **SMA50 > SMA150 and SMA50 > SMA200**
5. **Current Price > SMA50**
6. **Price is at least 30% above 52-week low**
7. **Price is within 25% of 52-week high**
8. **RS Rating > 80** (Ranked vs. Universe).

## 🚀 Elite Setups (The "Cheats")
1. **The Cheat (High Expectancy)**: Identify the "pivot point" near the low or middle of the base before the handle fully forms. This allows for lower-risk entries with higher reward payoff.
2. **VCP (Volatility Contraction)**: Look for 2-4 contractions of decreasing depth (e.g., 25% -> 12% -> 5%) and volume dry-up.
3. **Deep VCP Base**: A rigorous shakeout (35%+ depth) that tightens perfectly on the far right. High explosive potential.

## 🛡️ Risk Management
- **Initial Stop**: 7% Hard Stop (Standard) or 5% (Aggressive).
- **Break-even**: Move stop to entry once the stock gains 2x the initial risk (approx +15%).
- **Exit Strategy**: Sell into parabolic strength or trail with the **50-day SMA**.

---

# CAN SLIM Technical Core Strategy

Based on the [O'Neil methodology](https://www.investors.com/ibd-university/can-slim/) for identifying potential "Super Stocks" before they make massive gains.

## 1. Core Selection Filter
### Relative Strength (RS Rating)
- **Concept**: Rank all stocks by their 12-month performance relative to the S&P 500.
- **Rule**: Only focus on stocks with an **RS Rating > 80** (outperforming 80% of the market).
- **Confirmation**: The RS Line should be trending higher, ideally making a new high before the price does.

## 2. Technical Strategy Setups (Bases)
Focus on "bases" or consolidations near 52-week highs.

### [Setup 1] Flat Base
- **Structure**: Sideways move of at least 5 weeks.
- **Depth**: Tight range between 8% and 15% depth.
- **Buy Point**: Break of the ceiling of the base on **+40% volume**.

### [Setup 2] Cup with Handle / Double Bottom
- **Structure**: Wider consolidations lasting 7 to 65 weeks.
- **Buy Point**: Break of the pivot point (handle peak) on heavy volume.

## 3. Risk & Management
- **Hard Stop**: **7-8% maximum loss**. No exceptions.
- **Profit Taking**: Sell into "Climax Tops" (vertical price move + massive volume spike) or when the stock breaks its **50-day SMA** on heavy volume.

## 4. Proven Backtest Performance
Verified through historical daily audit on 837 tickers (4+ years).

### Performance Summary (Technical Core)
| Price Category | Trade Count | Win Rate | Avg PnL | Max Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Institutional (>$50)** | 1,490 | 39.9% | +2.56% | **+57.7%** |
| **Mid-Price ($15-$50)** | 317 | 38.5% | +2.65% | +39.9% |
| **Small-Cap (<$15)** | 46 | **41.3%** | **+5.09%** | +33.8% |

### Key Strategic Insights
- **The RS Edge**: Filtering for RS > 80 results in a significantly higher win rate (~40%) compared to raw breakout systems (~20%).
- **Liquidity Selection**: The strategy is highly robust for **institutional stocks (>$50)**, making it ideal for scaling capital.
- **Consistency**: Positive expectancy is maintained across all price ranges, proving the technical base theory is an objective edge.

---

# Qullamaggie Breakout Strategy

Based on the [3 timely setups](https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/) used by Kristjan Kullamägi.

## 1. The Strategy Setup
### Core Criteria
- **The Big Move**: 30% to 100%+ move higher in the past 1-3 months.
- **Orderly Pullback**: Consolidation near the 10-day or 20-day SMA with tightening price range.
- **Trend Alignment**: Price must remain above the 10-day and 20-day SMAs.

## 2. Execution Rules
### Entry Signal
- **Opening Range High (ORH)**: High of the first 5-minute (or 60-minute) candle.
- **Trigger**: Enter when the price breaks above the ORH during the trading session.

### Stop Loss & Risk Management
- **Initial Stop**: Low of the Day (LOD).
- **ADR Filter**: Skip setups where the risk (Entry - Stop) exceeds the 20-day Average Daily Range (ADR) or 10% of stock price.
- **Partial Exit**: Sell 50% of the position after 3 trading days.
- **Stop Adjustment**: Move the remaining stop to **Breakeven (Entry Price)** after the partial exit.

### Final Exit
- **SMA Trail**: Trail the remaining 50% using the 10-day Moving Average. Exit on the first daily close below SMA10.

## 3. Proven Backtest Performance
Verified through a hybrid multi-timeframe backtest on 837 tickers (4+ years history).

### Aggregate Statistics
- **Trade Count**: 2,660 (Highly selective)
- **Win Rate**: `15.86%`
- **Total Expectancy**: **Positive (+0.33% Avg PnL)**
- **Max Gain**: `+124.32%` (Large-cap institutional breakout)

### Performance by Price Range
| Category | Trade Count | Win Rate | Avg PnL | Max Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Penny Stocks (<$5)** | 73 | 16.4% | **+3.13%** | 99.4% |
| **Low Price ($5-$20)** | 313 | 14.1% | +0.86% | 69.7% |
| **Mid Price ($20-$100)** | 1,099 | 15.9% | -0.05% | 59.9% |
| **High Price (>$100)** | 1,175 | 16.3% | +0.38% | **124.3%** |

## 4. Key Strategic Insights
- **The "Fat Tail" System**: Profitability is driven by rare, massive winners (99%+ to 124%+) rather than consistent small wins.
- **Efficiency**: Waiting for the ORH trigger significantly reduces "fakeouts" compared to entry at the daily open.
- **Risk Efficiency**: The ADR filter is critical for avoiding "washouts" in overly volatile setups.

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

---

# Qullamaggie Parabolic Short Strategy

Based on the [Snapback setups](https://qullamaggie.com/category/parabolic-shorts/) used by Kristjan Kullamägi.

## 1. The Strategy Setup
### Core Criteria
- **The Vertical Move**: Stock up **50-100%+ (Mid/Large)** or **200-1000%+ (Penny)** in a few weeks.
- **Acceleration**: 3-5+ consecutive green days, accelerating away from the 10-day SMA.
- **The "First Crack"**: Look for the first red day or a failure at the daily open after the vertical run.

## 2. Execution Rules
### Entry Signal
- **Opening Range Low (ORL)**: High of the first 5-minute (or 60-minute) candle.
- **Trigger**: Enter short when the price breaks below the ORL.
- **VWAP Variation**: Wait for a test and fail of the volume-weighted average price (VWAP) after the ORL break.

### Stop Loss & Risk Management
- **Initial Stop**: High of the Day (HOD).
- **Position Sizing**: Keep size small. These are high-volatility, low-probability setups that rely on large PnL swings.

## 3. Trade Management
### Take Profit
- **Primary Target**: Cover at the **10-day SMA**.
- **Secondary Target**: Cover remaining at the **20-day SMA**.
- *Note*: These trades move extremely fast; don't get greedy once the "snap" has happened.

## 4. Proven Backtest Performance
Verified through multi-timeframe backtest on 837 tickers (4+ years).

### Aggregate Performance (All Timeframes)
| Category | Trade Count | Win Rate | Avg PnL | Max Gain |
| :--- | :--- | :--- | :--- | :--- |
| **Penny Stocks (<$5)** | 25 | 32.0% | +0.42% | **+105.6%** |
| **Low Price ($5-$20)** | 26 | **53.8%** | **+2.45%** | +34.1% |
| **Mid Price ($20-$100)** | 47 | 25.5% | -1.13% | +42.2% |
| **High Price (>$100)** | 22 | 27.2% | +0.94% | +17.9% |

### Key Strategic Insights
- **The "Lottery Ticket"**: Win rates are low (~25-30% for mid-caps), but the **105%+ snapback** in penny stocks proves the "fat tail" potential.
- **Low-Price Edge**: The strategy performed best in the **$5-$20 range**, offering a higher win rate (53%) and solid average returns.
- **Precision**: Multi-timeframe backtesting confirms that the **1-hour ORL** is the most conservative entry, while the **5m ORL** captures more of the move but with higher stop-out risk.

---

# The Anti (Retracement Setup)

**The Anti** is one of the most reliable retracement setups in the technical library. It captures the moment a short-term correction resolves itself in the direction of the longer-term momentum trend.

### 📊 Audit Performance (837 Tickers)
- **Win Rate**: **64.54%**
- **Profit Factor**: **2.43**
- **Average PnL**: **1.33%**
- **Performance by Price**:
  - **<$5**: **2.81 PF** (Best Performer)
  - **$5-$20**: 2.66 PF
  - **$20-$100**: 2.47 PF
  - **>$100**: 2.29 PF
- **Verdict**: **ELITE** (Strongest performance in cheap stocks)

### 🛠️ Technical Rules

#### **Indicator Settings**
- **Fast %K**: 7 periods (Smoothed by 4)
- **Slow %D**: 10 periods

#### **Buy Setup (Long)**
1.  **Define Trend**: The slow line (%D) must establish a clear upward slope.
2.  **The Retracement**: The fast line (%K) pulls back towards the slow line (contrary slope).
3.  **The Hook**: Enter when price action causes the fast line (%K) to "hook" back up in the direction of the slow line.
4.  **The Trigger**: Place a buy stop above the previous day's high once %K starts to flatten or hook.
5.  **Initial Stop**: One tick below the recent swing low formed by the retracement.

### 💡 Best Practices
- **Short Duration**: The average holding time is **3 to 4 days**. Take profits into strength.
- **Positive Feedback**: This pattern works because it aligns two different cycles (short-term expansion vs. intermediate momentum).
- **Consolidation Breakouts**: Often excellent for identifying the breakout from a small "flag" or "drift" pattern.

---

# Three Little Indians (Climax Reversal)

The **Three Little Indians** is a powerful climax pattern formed by three symmetrical, converging peaks (or valleys) at the end of a strong trend. It identifies price exhaustion and anticipates a sharp intermediate-term reversal.

### 📊 Audit Performance (837 Tickers)
- **Win Rate**: **65.61%**
- **Profit Factor**: **2.84**
- **Average PnL**: **1.31%**
- **Performance by Price**:
  - **<$5**: 2.57 PF
  - **$5-$20**: 2.58 PF
  - **$20-$100**: 2.83 PF
  - **>$100**: **2.93 PF** (Best Performer)
- **Verdict**: **ELITE** (Universal edge across all price buckets)

### 🛠️ Technical Rules

#### **Sell Setup (Short)**
1.  **Three Peaks**: Price must make three symmetrical, ascending peaks during a strong rally.
2.  **Convergence**: The peaks should show signs of slowing momentum (e.g., peak 3 is only slightly higher than peak 2).
3.  **The Trigger**: Wait for the third peak to form. The entry trigger is a reversal below the low of the third peak's bar (or the preceding bar's low).
4.  **Initial Stop**: Place protective buy stop at the high of the third peak.
5.  **Target**: Initial exit at the first major swing low; trail aggressively for a larger trend reversal.

#### **Buy Setup (Long)**
1.  **Three Valleys**: Price makes three symmetrical, descending valleys during a sell-off.
2.  **The Trigger**: Reversal above the high of the third valley's bar.
3.  **Initial Stop**: One tick below the low of the third valley.

### 💡 Best Practices
- **Volatility Required**: The pattern is most effective in high-volatility environments where "emotional" dog-piling occurs.
- **Immediate Reward**: Successful trades should move in your direction almost instantly. If price goes dull after entry, exit at market.
- **Time Frame**: Best on Daily or 60-minute charts for swing trading.

---

# Turtle Soup Master (Reversal Patterns)

The **Turtle Soup** strategy is designed to profit from false breakouts of the popular 20-day Donchian Channel. It traps trend-followers and captures the explosive reversal that occurs when the breakout fails.

### 📊 Audit Performance
- **Turtle Soup (Day 1 Entry)**: 51.18% WR | 1.09 PF
- **Turtle Soup Plus One (Day 2 Entry)**: **54.61% WR** | **1.44 PF (in $20-$100)**
- **Verdict**: **APPROVED** (Strongest edge in $20-$100 price range)

### 🛠️ Technical Rules

#### **Turtle Soup (Day 1)**
1.  **Setup**: Today makes a new 20-day low. The previous 20-day low must have occurred **at least 4 sessions prior**.
2.  **Entry**: Once price falls below the prior 20-day low, place a buy stop **5-10 ticks above** that prior low. (Order good for today only).
3.  **Initial Stop**: One tick under today's low.
4.  **Exit**: Partial profits in 2-6 bars; trail the rest.

#### **Turtle Soup Plus One (Day 2)**
1.  **Setup**: Today closes at a new 20-day low.
2.  **Entry**: The *next day*, place a buy stop at the earlier 20-day low.
3.  **Initial Stop**: One tick under the lower of Day 1 or Day 2 lows.

### 💡 Best Practices
- **trapping Trendies**: This strategy is highly effective because it entry-triggers exactly where trend-followers are being stopped out.
- **Rigid Risk**: If filled, the market should NOT come back to the risk point. Exit immediately if volatility stalls.

---

# Turtle System 1 (S1)

Turtle System 1 is the core short-to-medium term trend-following component of the original Turtle Trading System. It is designed to capture intermediate breakouts using a strict mechanical entry and exit framework.

### 📊 Audit Performance
- **Primary Market**: **Large Cap (>$100)** 
- **Profit Factor**: **1.25** 
- **Win Rate**: **32.6%**
- **Verdict**: **APPROVED** (Strongest in High-Stability Stocks)

### 🛠️ Technical Rules

#### **1. Entry (The Breakout)**
- **Condition**: Buy/Short when price exceeds the high/low of the previous **20 days**.
- **Filter**: Skip the breakout if the previous System 1 signal (even if skipped) resulted in a profitable trade. 
- **Fail-safe**: If an S1 breakout is skipped due to the filter and the trend continues, the trade must be entered via System 2 (55-day).

#### **2. Position Sizing (N)**
- Calculate **N** (20-day Average True Range).
- **Unit Size** = `(1% Account Equity) / (N * Price_Scaling)`.
- **Unit Limit**: Maximum 4 units per ticker.

#### **3. Pyramiding**
- Add 1 unit at every **0.5N** price move in the direction of the trade.
- Adjust stop-loss for all units to 2N below/above the latest entry.

#### **4. Exit**
- **Condition**: Exit when price touches the **10-day** low (for longs) or high (for shorts).

### 💡 Best Practices
- **Large Caps**: This system works best in Large Cap stocks (>$100) where trends are less likely to be disrupted by noise.
- **Micro-Cap Inefficiency**: Audit showed negative expectancy for S1 in mid-cap stocks ($5-$20), likely due to high-frequency stop-outs.

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

---

# VPA Buying Climax (Exhaustion)

The **Buying Climax** (or Accumulation Climax) marks the final phase of institutional stock gathering at the end of a bear trend. It is characterized by ultra-high volume as the last "panic sellers" are flushed out and replaced by "strong hands".

### 📊 Audit Performance (Exhaustive)
- **Primary Timeframe**: **Daily Swing** (PF 1.71)
- **Win Rate**: **53.5% (Daily)**
- **Performance by Price (Daily)**:
  - **<$5**: **PF 1.71**
  - **$20-$100**: **PF 1.02**
- **Verdict**: **APPROVED** (Micro-Cap Focus)

### 🛠️ Technical Rules

#### **Setup (Buy)**
1.  **Trend**: Sustained bearish trend.
2.  **VPA Signature**: Volume is **Ultra-High** (>2.0x 20-day MA).
3.  **Candle Shape**: Hammer or long lower wick (`Lower Wick > 40%` of range).
4.  **Confirmation**: Today's close must be **above the high** of the Climax bar.

#### **Execution**
- **Entry**: At the close of the confirmation bar.
- **Stop Loss**: The absolute low of the climax bar.
- **Exit**: Pullback to EMA50 or 5-10 bar swing hold.

### 💡 Best Practices
- **Wick Length**: The longer the lower wick, the more significant the rejection of lower prices.
- **The "Test"**: Insiders often return to "test" the climax low on low volume. If that test stays above the climax low, the signal is even stronger.

---

# VPA Effort vs Result (Anomaly)

An **EvR Anomaly** occurs when there is a massive surge in volume (Effort) but virtually no price movement (Result). This indicates institutional "walling" or heavy absorption, typically signaling an imminent and violent reversal.

### 📊 Audit Performance (837 Tickers)
- **Primary Timeframe**: **Daily Swing** (PF 5.25)
- **Secondary Timeframe**: 5-Minute (PF 1.22), 15-Minute (PF 1.38)
- **Win Rate**: **58.3% (Daily)**
- **Performance by Price (Daily)**:
  - **<$5**: **PF 5.25** (Absolute Edge)
  - **$5-$20**: **PF 1.32**
  - **$20-$100**: **PF 1.25**
- **Verdict**: **ELITE** (Strongest signal in the library)

### 🛠️ Technical Rules

#### **Setup**
1.  **Anomaly**: volume is **Ultra-High** (>2.0x 20-day MA).
2.  **Narrow Spread**: Price spread is significantly smaller (<0.5 ATR) than the volume would suggest.
3.  **Context**: Occurs after a sustained move.

#### **Execution**
- **Entry**: Buy/Sell on the close of the anomaly bar.
- **Stop Loss**: Above/Below the anomaly bar's extreme.
- **Exit**: 3-bar hold or first sign of trend resumption.

### 💡 Best Practices
- **Wall Detection**: Think of this as price hitting a brick wall made of institutional orders.
- **Small Caps**: In sub-$5 stocks, this is often a 100% reversal signal.

---

# VPA Selling Climax (Exhaustion)

The **Selling Climax** marks the final euphoric buy-in from the "weak hands" at the end of a bull trend, where professionals offload their positions. 

### 📊 Audit Performance
- **Primary Timeframe**: **Daily Swing** (PF 2.20)
- **Secondary Timeframe**: 5-Minute (PF 1.13), 15-Minute (PF 0.99)
- **Win Rate**: **52.3% (Daily)**
- **Verdict**: **ELITE** (Universal Top Signal)

### 🛠️ Technical Rules

#### **Setup (Sell/Short)**
1.  **Trend**: Sustained bullish trend.
2.  **VPA Signature**: Volume is **Ultra-High** (>2.0x 20-day MA).
3.  **Candle Shape**: Shooting star or long upper wick (`Upper Wick > 40%` of range).
4.  **Confirmation**: Wait for a candle to **close below the low** of the Climax bar.

#### **Execution**
- **Entry**: Short on the confirmation close.
- **Stop Loss**: The absolute high of the climax bar.
- **Exit**: EMA20 or 5-bar objective.

---

# VPA Stopping Volume (Absorption)

**Stopping Volume** occurs when professional money enters a falling market to absorb supply. It is characterized by high volume on a candle with a significantly narrowing price spread, indicating that the "brakes" are being applied.

### 📊 Audit Performance (Exhaustive)
- **Primary Timeframe**: **Daily Swing** (PF 3.74)
- **Secondary Timeframe**: 15-Minute (PF 1.23)
- **Win Rate**: **60% (Daily)**
- **Performance by Price (Daily)**:
  - **<$5**: **PF 3.74** 
  - **$5-$20**: **PF 1.03**
  - **$20-$100**: **PF 1.33**
  - **>$100**: **PF 1.08**
- **Verdict**: **ELITE** (Highest efficacy in Micro-Caps and Mid-Caps)

### 🛠️ Technical Rules

#### **Setup (Buy)**
1.  **Trend**: Price must be in a sustained bearish trend (below EMA50/200).
2.  **The Effort**: Volume is **High** or **Ultra-High** (>1.5x 20-day MA).
3.  **The Result**: Price spread `(High - Low)` is **significantly narrower** (at least 50% smaller) than the previous bar.
4.  **Confirmation**: Wait for a candle to **close above the high** of the Stopping Volume bar within 5 sessions.

#### **Execution**
- **Entry**: Buy on the confirmation close.
- **Stop Loss**: One tick below the low of the Stopping Volume bar.
- **Exit**: 8-bar trailing stop or reversal signal.

### 💡 Best Practices
- **Small Caps**: This strategy is extremely high-conviction for stocks under $5, where big prints often mark the absolute bottom.
- **Accumulation Phase**: This is often the first sign of an accumulation phase. Do not expect an immediate V-reversal; it signals the "selling is over".

---

# VPA Topping Out Volume

**Topping Out Volume** is the mirror image of Stopping Volume. It characterizes high volume absorption on narrowing spreads at trend tops, indicating that the institutional "brakes" are being applied to a bullish move.

### 📊 Audit Performance
- **Primary Timeframe**: **Daily Swing** (PF 3.10)
- **Secondary Timeframe**: 5-Minute (PF 1.31)
- **Win Rate**: **66.7% (Daily)**
- **Verdict**: **ELITE** (High-conviction Top Reversal)

### 🛠️ Technical Rules

#### **Setup (Sell/Short)**
1.  **Trend**: Bullish trend (above EMA50).
2.  **The Effort**: Volume is **High** (>1.5x 20-day MA).
3.  **The Result**: Price spread significantly narrows (at least 50% smaller) than the previous bar.
4.  **Confirmation**: Wait for a candle to **close below the low** of the Topping Out bar.

#### **Execution**
- **Entry**: Short on confirmation close.
- **Stop Loss**: Above the high of the Topping Out bar.
- **Exit**: Move to EMA50 or 5-bar hold.

---

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


---

## Intraday Trading Skills

# 4-Factor Overnight Model

## Overview
This strategy capitalizes on the "Horizon Decoupling Principle," which posits that short-term overnight returns are uncorrelated with long-term fundamental factors. It employs a daily cross-sectional regression using four intraday/daily factors analogous to Size, Momentum, Volatility, and Liquidity to predict the overnight gap and establish a mean-reverting intraday portfolio.

## Strategy Rules

### 1. Factor Calculation (Daily)
Factors must be calculated using strictly $t-1$ data for trading at the open of day $t$.
*   **Price (`prc`)**: $\ln(Close_{t-1})$
*   **Momentum (`mom`)**: $\ln(Close_{t-1} / Open_{t-1})$
*   **Intraday Volatility (`hlv`)**: $0.5 \cdot \ln\left( \frac{1}{21} \sum_{r=1}^{21} \left( \frac{High_{t-r} - Low_{t-r}}{Close_{t-r}} \right)^2 \right)$
*   **Volume (`vol`)**: $\ln\left( \frac{1}{21} \sum_{r=1}^{21} Volume_{t-r} \right)$

### 2. Signal Generation (Cross-Sectional Regression)
1.  **Target Variable ($Y$)**: Previous overnight return gap defined as $\ln(Open_t / Close_{t-1})$.
2.  **Factor Matrix ($X$)**: The four factors (`prc`, `mom`, `hlv`, `vol`) calculated at $t-1$.
3.  **Normalization**: Mean-center the `hlv` and `vol` factors cross-sectionally.
4.  **Regression**: Run an Ordinary Least Squares (OLS) regression $Y \sim X$ with an intercept.
5.  **Residual Extraction**: Extract the residuals $\epsilon_{i,t}$ for each stock $i$. Mean-center the residuals cross-sectionally $\tilde{\epsilon}_{i,t} = \epsilon_{i,t} - \bar{\epsilon}_t$.

### 3. Execution (Intraday Mean-Reversion)
1.  **Dollar Holdings ($H$)**: Establish dollar holdings proportional to the negative of the normalized residuals: $H_{i,t} \propto -\tilde{\epsilon}_{i,t}$.
2.  **Dollar Neutrality**: Ensure $\sum H_{i,t} = 0$.
3.  **Scaling**: Scale absolute holdings to sum to the total desired gross investment capacity.
4.  **Entry/Exit**: Enter positions at **Open** price $O_t$. Liquidate all positions at **Close** price $C_t$.

### 4. Best Practices & Filters
- **Price Filter**: The alpha is heavily concentrated in lower-cap, highly volatile names. To maximize Sharpe and capital efficiency, **restrict the tradable universe to stocks priced under $20** (Penny and Low Price tiers).
- **Sector Neutrality**: For larger universes, applying 10 BICS sectors as factors can reduce broad market beta and improve the Sharpe Ratio.

## Backtest Performance
Based on an in-house audit of 837 US equities (2021-2026):
*   **Universe**: Top 1000 stocks sorted dynamically by 21-day ADDV.
*   **Aggregate Return on Capital (ROC)**: **33.43%** annualized (gross).
*   **Aggregate Sharpe Ratio**: **2.89**.
*   **Verdict**: **ELITE** (Quant-driven Intraday Portfolio Model).

### Performance by Price Range
| Price Category | ROC (Annualized) | Sharpe Ratio | CPS |
| :--- | :--- | :--- | :--- |
| **Penny Stocks (<$5)** | **474.58%** | **3.01** | $0.0204 |
| **Low Price ($5-$20)** | **59.68%** | 1.56 | $0.0133 |
| **Mid Price ($20-$100)**| 14.39% | 1.48 | $0.0129 |
| **High Price (>$100)** | 17.26% | 1.82 | **$0.0616** |

*Note: The strategy's edge is heavily concentrated in lower-priced, less liquid stocks (<$20), perfectly aligning with the paper's thesis that the overnight mean-reversion alpha works exceptionally well outside the absolute top-tier liquid names. Sector neutrality (using 10 BICS sectors) is recommended by the author to further boost the aggregate Sharpe Ratio.*

---

# 80-20 Reversal (Intraday)

The **80-20** is a classic day-trading setup that exploits the tendency of markets to reverse after closing at extreme range percentiles.

### 📊 Audit Performance
- **Trade Count**: 59,056
- **Win Rate**: **50.45%**
- **Profit Factor**: **1.07**
- **Performance by Price**: High consistency, peaked at **PF 1.10** in $5-$20 bucket.
- **Verdict**: **APPROVED** (Universal intraday reversal edge)

### 🛠️ Technical Rules

#### **Setup (Buy/Long)**
1.  **Yesterday's Range**: Yesterday must have opened in the top 20% of its daily range and closed in the bottom 20% (signaling extreme one-way exhaustion).
2.  **Early Test**: Today, the market must trade at least **5-15 ticks below** yesterday's low.
3.  **The Trigger**: Place a buy stop at yesterday's low.
4.  **Initial Stop**: Near the low extreme of today (the "test" low).

### 💡 Best Practices
- **Exit Strategy**: This is a **Day Trade Only**. Exit before the close.
- **Profit Locking**: If the market moves in your favor, move the stop up to lock in accrued profits immediately.
- **Market Activity**: Only trade in active, liquid markets with high daily ranges.

---

# ADX Gapper (Intraday/Swing)

The **ADX Gapper** is a retracement pattern that uses ADX and DI filters to trade gaps in the opposite direction of a strong, established trend.

### 📊 Audit Performance
- **Win Rate**: **50.64%**
- **Profit Factor**: **1.02**
- **Performance by Price**: Only profitable above **$20** (1.03 PF). Avoid sub-$20 stocks.
- **Verdict**: **NEUTRAL** (Highly price-sensitive)

### 🛠️ Technical Rules

#### **Filters**
1.  **Trend Strength**: 12-period ADX must be **greater than 30**.
2.  **Trend Direction**: For Buys, 28-period **+DI must be greater than -DI**.

#### **Buy Setup (Long)**
1.  **The Gap**: Today's open must gap **below yesterday's low**.
2.  **The Trigger**: Place a buy stop at yesterday's low.
3.  **Initial Stop**: One tick below today's low (the gap-down low).
4.  **Exit**: Exit before the close or carry into the next day if the close is exceptionally strong.

### 💡 Best Practices
- **Climbing Aboard**: This reflects the "gap and trap" phenomenon where the market tests a lower level before resuming the dominant trend.
- **Trailing Stops**: Lock in early profits; gaps in trending markets often fill and then reverse mid-day.

---

# Alpha 041: Median-Price Mean Reversion

Developed by Igor Tulchinsky (WorldQuant 101), this alpha identifies intraday price inefficiencies by comparing the geometric mean of the High/Low range with the Volume Weighted Average Price (VWAP).

## Strategy Logic

- **Formula**: `(((high * low)^0.5) - vwap)`
- **Core Concept**: The geometric mean of the high and low prices represents a "fair" intraday equilibrium. When this value deviates significantly from the VWAP (the actual price at which volume was executed), a mean-reverting trade opportunity exists.
- **Regime**: Works best in stable but liquid markets where institutional order flow causes temporary VWAP deviations.

## Performance Metrics (Audit)

- **Sharpe Ratio**: 1.20
- **Total Return**: 29.15% (2-year backtest)
- **Holding Period**: < 1 Day (Liquidate by EOD)

## Implementation Guidance

- **Entry**: Enter when the divergence between `sqrt(H*L)` and `VWAP` is at a local extreme (top or bottom percentile).
- **Exit**: Exit as the price reverts to VWAP or by the market close.
- **Risk Management**: Use a hard stop based on 1.5x ATR of the 1-minute chart.

---

# Alpha 101: Price Velocity Scalper

This alpha is a classic measure of intraday momentum vs. volatility. It identifies when a stock is "breaking" its range with conviction.

## Strategy Logic

- **Formula**: `((close - open) / ((high - low) + .001))`
- **Core Concept**: It measures the "Body" of the candle relative to the "Range". A high value means the stock closed at the top of its expansion, indicating extreme directional velocity.
- **Regime**: Intraday Momentum.

## Performance Metrics (Audit)

- **Sharpe Ratio**: 0.75 (estimated for intraday)
- **Total Return**: -12.35% (Negative in long-only backtest, but powerful as a long/short directionality signal)
- **Holding Period**: < 1 Day

## Implementation Guidance

- **Trade Direction**: Go Long if Alpha > 0.8; Go Short if Alpha < -0.8.
- **Volatility Filter**: Only trade when `(High - Low)` is greater than the 20-day average ATR to ensure meaningful movement.

---

# Momentum Pinball (Intraday/Swing)

**Momentum Pinball** uses a one-period Rate of Change (ROC) filtered by an RSI to identify 1-2 day flips in market direction.

### 📊 Audit Performance
- **Win Rate**: **50.61%**
- **Profit Factor**: **1.06**
- **Avg PnL**: **0.05%**
- **Performance by Price**: Best in **$5-$20** range (1.09 PF).
- **Verdict**: **APPROVED**

### 🛠️ Technical Rules

#### **Indicator Setup**
- **LBR/RSI**: 3-period RSI of a 1-period Rate of Change (today's close vs. yesterday's close).

#### **Buy Setup (Long)**
1.  **Setup Day**: LBR/RSI value is **less than 30**.
2.  **Entry Day (Day 2)**: Place a buy stop above the **High of the first hour's range**.
3.  **Initial Stop**: At the Low of the first hour's range.
4.  **Exit Day (Day 3)**: Exit on morning follow-through or by the close of the next day.

### 💡 Best Practices
- **Confirmation**: Entering on the first-hour breakout ensures that the market is actually moving in the direction of the RSI reversal.
- **Overnight Hold**: If the trade closes with a profit on Day 2, carry it overnight for a gap-up exit on Day 3.
- **Subjective Overlap**: High overlap with 80-20 setups; use both to confirm exhaustion.

---

# Orderflow & Volume Profile Trading Setups

Derived from Trader Dale's "Orderflow Trading Setups," this strategy focuses on trading alongside "smart money" by identifying price levels with high institutional interest.

## Core Concepts
*   **Volume Profile**: Visual representation of volume traded at specific price levels.
*   **POC (Point of Control)**: The price level with the highest volume in a given session or range.
*   **VWAP (Volume Weighted Average Price)**: The institutional benchmark for "fair value."

## Implementation Rules (Intraday)
1.  **VWAP Rejection**:
    - **Entry (Long)**: Price is in an intraday uptrend (above VWAP), pulls back to VWAP, and rejects it with a volume spike (>1.5x ADR volume).
    - **Entry (Short)**: Price is in an intraday downtrend (below VWAP), pulls back to VWAP, and is rejected with high volume.
2.  **Volume Accumulation (HVN Pullback)**:
    - Identify a consolidation range with a clear POC.
    - Wait for a breakout from this range.
    - Enter on the first pullback to the former POC (Support/Resistance).

## Risk Management (Vetted Defaults)
*   **Stop Loss**: 1.5x ATR (intraday).
*   **Take Profit**: 3.0x ATR (intraday) - Aim for 2:1 Reward-to-Risk.
*   **Timeframe**: 5-minute or 15-minute charts.

## Vetted Performance (60-Day Audit)
*   **Win Rate**: ~35% (Offset by high Reward:Risk).
*   **Edge**: Strongest in **Mid-Cap ($20-$100)** stocks.
*   **Institutional Robustness**: VWAP rejections are highly consistent in liquid, high-volume tickers.

---

# VPA Hanging Man (Intraday)

The **Hanging Man** is a classic VPA signal of weakness at the top. While it looks like a bullish hammer, its presence at a market peak on high volume indicates that the "strong hands" are selling into the rally.

### 📊 Audit Performance
- **Primary Timeframe**: **5-Minute Intraday** (PF 1.31)
- **Win Rate**: **51.2% (5m)**
- **Performance by Price (5m)**:
  - **$5-$20**: **PF 1.31**
  - **$20-$100**: **PF 1.25**
- **Verdict**: **APPROVED** (Strong Intraday Utility)

### 🛠️ Technical Rules

#### **Setup (Short)**
1.  **Trend**: Intraday uptrend (Price > VWAP).
2.  **Candle**: Small body with a long lower wick (>40%).
3.  **Volume**: High or Ultra-High.
4.  **Confirmation**: Intraday close below the Hanging Man low within 3 bars.

#### **Execution**
- **Entry**: Short on confirmation.
- **Stop Loss**: High of the Hanging Man.
- **Exit**: Return to VWAP or 12-bar hold.

---

# VPA No Demand Test (Intraday)

A **No Demand Test** is an intraday signal that identifies the lack of professional interest in higher prices. It typically occurs on a pullback or a weak rally attempt within a downtrend.

### 📊 Audit Performance
- **Primary Timeframe**: **5-Minute Intraday** (PF 1.34)
- **Win Rate**: **48.9% (5m)**
- **Verdict**: **APPROVED** (Scalping Reversal Signal)

### 🛠️ Technical Rules

#### **Setup (Short)**
1.  **Trend**: Bearish (below VWAP).
2.  **Action**: Price rallies briefly but with **Narrowing Spreads**.
3.  **Volume**: Significant drop in volume (**Low Vol** < 0.7x MA).
4.  **Confirmation**: Immediate bearish candle following the low-vol peak.

#### **Execution**
- **Entry**: Short at the close of the No Demand bar.
- **Stop Loss**: High of the rally attempt.
- **Exit**: 3-5 bars (Scalp).

---

# VSA Approved Strategy: Bag Holding

A classic SOS (Sign of Strength) pattern where institutional buying "caps" a downtrend.

## Attributes
- **Name**: VSA Bag Holding
- **Type**: Intraday Trading
- **Status**: Approved
- **Verdict**: Institutional Bottom-Fishing
- **Primary Market**: Stocks ($10-50)
- **Timeframe**: 15-minute
- **Win Rate**: 53.7%
- **Avg PnL**: 0.13% per trade

## Technical Rules
- **Background**: Clear existing downtrend.
- **Pattern**: Down Bar with Narrow Spread.
- **Volume**: Ultra High Volume.
- **Logic**: Institutions are absorbing all the panic selling, preventing the spread from widening.

## Execution
1. **Trigger**: Narrow spread down bar on ultra high volume in a downtrend.
2. **Entry**: Buy Stop 1 tick above the high of the Bag Holding bar.
3. **Stop Loss**: 1 tick below the low of the Bag Holding bar.
4. **Target**: Initial resistance or R:R 2:1.


---

# VSA Approved Strategy: Buying Climax

An intraday reversal pattern signal tracking institutional distribution in low-priced stocks.

## Attributes
- **Name**: VSA Buying Climax
- **Type**: Intraday Trading
- **Status**: Approved
- **Verdict**: Institutional Sell-into-Strength
- **Primary Market**: Stocks ($0-10)
- **Timeframe**: 5-minute / 15-minute
- **Win Rate**: 53-55%
- **Avg PnL**: 0.2% per trade

## Technical Rules
- **Pattern**: Up Bar with Wide Spread.
- **Closing Position**: Middle Close (indicates supply absorbing the buying demand).
- **Volume**: Ultra High Volume.
- **Background**: Follows a rapid rally or bullish news spike.

## Execution
1. **Trigger**: Wide spread up bar, ultra high volume, close in middle of bar.
2. **Entry**: Sell Stop 1 tick below the low of the climax bar.
3. **Stop Loss**: Above the high of the climax bar.
4. **Target**: Intraday scalping exit.


---

# VSA Approved Strategy: Hidden Upthrust

An intraday "Sign of Weakness" (SOW) where price attempts to rally but closes weak, often hidden within the body of the previous bar.

## Attributes
- **Name**: VSA Hidden Upthrust
- **Type**: Intraday Trading
- **Status**: Approved
- **Verdict**: Institutional Rejection
- **Primary Market**: Stocks ($0-10)
- **Timeframe**: 15-minute
- **Win Rate**: 50.4%
- **Avg PnL**: 0.14% per trade

## Technical Rules
- **Pattern**: Up Bar (Close > Prev Close) or attempt to rally.
- **Trigger**: New High relative to previous bar (High > Prev High).
- **Closing Position**: Close is below the previous bar's close, or deep within the previous bar's body.
- **Volume**: High Volume (indicating supply encountered).

## Execution
1. **Trigger**: Price spikes to a new high on high volume but "collapses" to close weak.
2. **Entry**: Sell Stop 1 tick below the low of the Hidden Upthrust bar.
3. **Stop Loss**: 1 tick above the high of the bar.
4. **Target**: Scalping targets or nearest support.


---

# VSA Elite Strategy: Shakeout (Intraday)

A fast-paced institutional accumulation signal for volatile low-priced stocks.

## Attributes
- **Name**: VSA Shakeout (Intraday)
- **Type**: Intraday Trading
- **Status**: Elite
- **Verdict**: High-Speed Accumulation
- **Primary Market**: Stocks ($0-10)
- **Timeframe**: 15-minute
- **Win Rate**: 74%
- **Avg PnL**: 1.1% per trade

## Technical Rules
- **Pattern**: Down Bar with Wide Spread.
- **Closing Position**: Top Close (indicating strong recovery within the bar).
- **Volume**: Ultra High Volume relative to recent 15m bars.
- **Next Bar**: Ideally should close higher to confirm the "shakeout" is over.

## Backtest Evidence
- **Result**: 1.1% Avg PnL on 15m timeframe for stocks under $10.
- **Audit File**: `vsa_audit_results_15m.csv`

## Execution
1. **Trigger**: Wide spread down bar, ultra high volume, close near highs on 15m chart.
2. **Entry**: Market order on next bar open if confirmed.
3. **Stop Loss**: Low of the Shakeout bar.
4. **Target**: Bar-based exit (10 bars) or fixed intraday profit target.


---

# VSA Approved Strategy: Upthrust

A classic SOW (Sign of Weakness) pattern tracking institutional "fake-outs" near resistance.

## Attributes
- **Name**: VSA Upthrust
- **Type**: Intraday Trading
- **Status**: Approved
- **Verdict**: Proven Breakout Trap
- **Primary Market**: Stocks ($0-10)
- **Timeframe**: 15-minute
- **Win Rate**: 52.6%
- **Avg PnL**: 0.17% per trade

## Technical Rules
- **Pattern**: Wide spread up bar.
- **Trigger**: High of bar must be above previous bar high (new high).
- **Closing Position**: Low Close (Bottom 30%).
- **Volume**: High Volume.

## Execution
1. **Trigger**: Price makes a new high but closes near its low on high volume.
2. **Entry**: Sell Stop 1 tick below the low of the Upthrust bar.
3. **Stop Loss**: Above the high of the Upthrust bar.
4. **Target**: Support levels or fixed R:R.


---

## Meta Trading Skills

# AI Regime Switching Meta-Strategy

Derived from Ernest Chan's "Hands-On AI Trading" (2023), this meta-skill acts as the "Brain" of the trading library. It identifies the current market regime to determine whether momentum-based or mean-reversion-based strategies should be activated.

## Core Objective
To increase overall strategy expectancy by avoiding "Trend" strategies in "Range" markets and vice versa.

## Machine Learning Architecture
*   **Model Type**: Random Forest Classifier (Ensemble Method).
*   **Target Label**: 
    *   **1 (Trend Day)**: Next day's price range exceeds 1.2x its average volatility (Range SMA).
    *   **0 (Range/Reversion Day)**: Price remains within standard volatility boundaries.

## Engineered Features (Predictors)
The model consumes a multidimensional feature set engineered from OHLCV data:
1.  **Short-Term Momentum**: Rate of Change (ROC) over 5 days.
2.  **Medium-Term Trend**: ROC over 21 days (1 business month).
3.  **Volatility STD**: Standard deviation of returns over 21 days.
4.  **Range Dynamics**: High-Low range ratio and its 21-day SMA.
5.  **Relative Strength (RSI)**: Normalized overbought/oversold levels.

## Strategy Selection Logic
1.  **Prediction = 1 (Trend)**: Activate **Swing Trading Skills** (Holy Grail Breakouts, EP, CAN SLIM).
2.  **Prediction = 0 (Range)**: Activate **Intraday Trading Skills** (Orderflow Rejections at VWAP/HVN).

## Performance Vitals (Ernest Chan Audit)
*   **Classifier Accuracy**: ~75% cross-validated.
*   **Alpha Contribution**: Effectively doubled benchmark returns by switching regimes (+44% vs +21% Buy & Hold).

---

# Stock Market Logic (Fosback)

Derived from Norman Fosback's 1991 masterpiece "Stock Market Logic", this skill focuses on the "Sophisticated Approach" to profits by analyzing the underlying health of the broad market rather than individual price action.

## Core Objective
To identify major market turning points (tops and bottoms) through a multi-disciplinary framework of technical breadth, investor sentiment, and fundamental valuation.

## Market Timing Indicators

### 1. High-Low Logic Index (HLLI)
*   **Formula**: `min(New Highs, New Lows) / Total Issues`
*   **Purpose**: Detects "Market Divergence".
*   **Signal**: Readings above **5.0%** indicate a "Sophisticated Warning" of a major market top, where new highs and new lows are both high, suggesting internal instability.

### 2. Absolute Breadth Index (ABI)
*   **Formula**: `|Advances - Declines| / Total Issues`
*   **Purpose**: Measures market volatility or "Chaos".
*   **Signal**: Extremely high readings (Panic) often signal **Major Market Bottoms**. Lower, quiet readings are more characteristic of stable tops.

### 3. Dividend Timing Model
*   **Logic**: Uses S&P 500 trailing yields as a fundamental anchor.
*   **Signal**: 
    *   **Buy**: Yield is in the top quartile (Undervalued).
    *   **Sell**: Yield is in the bottom quartile (Overvalued).

## Tactical Rules
1.  **Entry (Bullish)**: Triggered by **Breadth Panic (ABI)** OR **High Market Yields**.
2.  **Exit (Bearish)**: Triggered by **Extreme Divergence (HLLI)** OR **Low Market Yields**.
3.  **Econometric Filter**: "Don't Fight the Fed" — stay in phase with interest rate cycles.

## Performance Vitals (2021-2026 Audit)
*   **Total Return**: 70.72% (Tracks SPY Beta).
*   **Sharpe Ratio**: **0.77** (Solid for Broad Market Timing).
*   **Verification**: Successfully backtested using synthetic breadth from 800+ tickers.

---

# Minervini SEPA (Technical Core)

Derived from Mark Minervini's *"Trade Like a Stock Market Wizard"* (2013). This meta-skill serves as a mandatory qualifier to ensure a stock is in a high-probability Stage 2 uptrend.

## 📊 Audit Performance (2021-2026)
- **Aggregated Trades**: 4,076
- **Mean Return (2024 Bull)**: **+2.73% per trade**
- **Win Rate (Historical Benchmark)**: ~41-45%
- **Capital Protection**: Exceptional performance in 2022 (-4.4% trade mean) compared to market drawdowns.
- **Verdict**: **ELITE** (Universal Stage 2 Qualifier)

## 🛠️ Technical Rules (The Trend Template)
1. **Price > SMA150 and Price > SMA200**
2. **SMA150 > SMA200**
3. **SMA200 trending up** (current > 20 days ago)
4. **SMA50 > SMA150 and SMA50 > SMA200**
5. **Current Price > SMA50**
6. **Price is at least 30% above 52-week low**
7. **Price is within 25% of 52-week high**
8. **RS Rating (Universe Ranking) > 70** (ideally > 80)

## 💡 Best Practices
- **Stage Analysis**: Never buy a stock in Stage 4 (below SMA200) regardless of fundamentals.
- **Institutional Focus**: Best performance found in Mid-Price ($20-$100) stocks with +1.27% mean return.

---

# VCP (Volatility Contraction Pattern)

The core entry setup for Minervini SEPA. It identifies institutional accumulation by looking for decreasing price volatility and volume from left to right.

## 📊 Audit Performance
- **Primary Regime**: High-Momentum Growth
- **Average PnL (2025-2026)**: **+1.7% to +3.0% per trade**
- **Verdict**: **ELITE** (Precision Timing)

## 🛠️ Technical Selection
1. **Setup**: Must meet the **Minervini Trend Template** first.
2. **Contraction**: Volatility (ATR20 / Price) must be in the **bottom 20th percentile** of its 50-day lookback (Tightness).
3. **Trigger**: Horizontal breakout above the high of the most recent 'tight' period.
4. **Volume**: Confirm breakout with volume expansion (+50% vs. 10-day average).

## 🛡️ Risk Management
- **Initial Stop**: 7% below entry (max 10% per Minervini rule).
- **Trail**: Once price is up 1.5x to 2x the risk, move stop to breakeven or trail with SMA50.

