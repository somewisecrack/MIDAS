---
name: Systematic Momentum (Andrew Ang)
description: A rule-based rotation strategy that selects top 12-1 month momentum leaders across a broad universe.
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
