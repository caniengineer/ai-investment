# Mean Reversion Strategies

Mean reversion is based on the idea that asset prices tend to return to their historical average over time. When a price deviates significantly from its mean, it is likely to revert back.

## How Mean Reversion Works

These strategies identify when an asset is overbought or oversold relative to its historical norm, then trade in the opposite direction expecting a correction back toward the average.

## Common Mean Reversion Indicators

**RSI (Relative Strength Index):** Measures the speed and magnitude of recent price changes on a scale of 0-100. RSI below 30 suggests oversold conditions (buy signal). RSI above 70 suggests overbought conditions (sell signal).

**Bollinger Bands:** A moving average with upper and lower bands set at 2 standard deviations. Price touching the lower band suggests oversold; touching the upper band suggests overbought.

**Z-Score:** Measures how many standard deviations the current price is from the mean. A Z-score below -2 suggests a buying opportunity; above +2 suggests selling.

## Simple Mean Reversion Strategy Example

Entry rule: Buy when RSI drops below 30 (oversold).
Exit rule: Sell when RSI rises above 70 (overbought) or when price returns to the 20-day moving average.
Stop loss: 3% below entry price.
Typical lookback: 14 periods for RSI calculation.

## Risks

Mean reversion fails when a genuine trend is underway. A stock dropping due to fundamental deterioration may not revert to its mean. Always combine with stop losses.
