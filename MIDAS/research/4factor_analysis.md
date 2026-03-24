# Research Note: 4-Factor Model for Overnight Returns

Based on the paper by Zura Kakushadze (2015).

## Core Philosophy
The model is based on the **Horizon Decoupling Principle**, which states that short-term returns (like overnight) are uncorrelated with long-term factors (like Value or Growth). Therefore, factors are constructed using only short-term intraday and daily price/volume data.

## Model Factors
The model uses 4 factors analogus to Size, Momentum, Volatility, and Liquidity.

1.  **Price (Size proxy) - `prc`**:
    *   $\beta_{is}^{prc} = \ln(P_{i,s+1}^{AC})$
    *   *Definition*: Log of previous day's adjusted close.
2.  **Momentum - `mom`**:
    *   $\beta_{is}^{mom} = \ln(P_{i,s+1}^{C} / P_{i,s+1}^{O})$
    *   *Definition*: Previous day's intraday (open-to-close) return.
3.  **Intraday Volatility - `hlv`**:
    *   $\beta_{is}^{hlv} = \frac{1}{2}\ln(U_{is})$
    *   $U_{is} = \frac{1}{d} \sum_{r=1}^{d} \left( \frac{P_{i,s+r}^{H} - P_{i,s+r}^{L}}{P_{i,s+r}^{C}} \right)^2$
    *   *Lookback*: $d = 21$ days.
4.  **Volume (Liquidity proxy) - `vol`**:
    *   $\beta_{is}^{vol} = \ln(\tilde{V}_{is})$
    *   $\tilde{V}_{is} = \frac{1}{d} \sum_{r=1}^{d} V_{i,s+r} \frac{P_{i,s+r}^{C}}{P_{i,s+r}^{AC}}$
    *   *Definition*: 21-day average volume, adjusted for splits.

## Regression Model
The target variable is the **Overnight Return** ($R_{is}$):
$R_{is} = \ln(P_{is}^{AO} / P_{i,s+1}^{AC})$

A cross-sectional regression is run daily:
$R_{is} \sim \sum_{A=1}^{K} \beta_{iAs} f_{As} + \epsilon_{is}$
where $\beta_{is}^{int} = 1$ is the intercept.

## Trading Strategy (Intraday Alpha)
1.  Calculate factors daily for a universe of liquid stocks.
2.  Run the regression and extract residuals $\epsilon_{is}$.
3.  **Signal**: $H_{is} \propto -\epsilon_{is}$ (Mean-reversion).
4.  **Execution**: Establish dollar-neutral positions at the **Open** and liquidate at the **Close**.
