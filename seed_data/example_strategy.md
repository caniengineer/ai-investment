# Example Strategy: AAPL Moving Average Crossover

This document describes an example strategy that was generated, backtested, and deployed by the AlphaAgent system.

## Strategy Parameters

Asset: AAPL (Apple Inc.)
Type: Momentum / Trend Following
Indicator: Simple Moving Average Crossover
Short window: 20 days
Long window: 50 days
Entry rule: Buy when 20-day SMA crosses above 50-day SMA (golden cross)
Exit rule: Sell when 20-day SMA crosses below 50-day SMA (death cross)
Stop loss: 5% below entry price
Lookback period: 12 months

## Backtest Results

Period: January 2024 to January 2025
Total return: 18.5%
Sharpe ratio: 1.2
Maximum drawdown: -8.3%
Win rate: 62%
Number of trades: 8
Average holding period: 15 days

## Self-Heal History

Iteration 1: Initial parameters (short=10, long=30). Sharpe was 0.4 (below threshold). The agent identified the short window was too reactive, causing whipsaws.

Iteration 2: Adjusted to short=20, long=50. Sharpe improved to 1.2, max drawdown improved from 15% to 8.3%. Strategy passed all thresholds.

## Deployment Notes

Deployed to paper trading on Jan 15, 2025. After 2 weeks, simulated PnL tracked within 2% of backtest expectations. No intervention needed.
