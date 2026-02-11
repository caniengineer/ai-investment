"""Simple backtest engine — plain Python loops over price data.

No external backtest library. Calculates total return, Sharpe ratio,
max drawdown, and win rate.
"""

import logging
import numpy as np

logger = logging.getLogger("alphaagent.backtest")


def compute_sma(prices: list[float], window: int) -> list[float | None]:
    """Compute simple moving average."""
    result = [None] * len(prices)
    for i in range(window - 1, len(prices)):
        result[i] = np.mean(prices[i - window + 1 : i + 1])
    return result


def compute_rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """Compute RSI (Relative Strength Index)."""
    result = [None] * len(prices)
    if len(prices) < period + 1:
        return result

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(deltas)):
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100 - (100 / (1 + rs))
        # Smoothed averages
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    return result


def generate_signals(prices: list[float], strategy: dict) -> list[int]:
    """Generate buy(1)/sell(-1)/hold(0) signals based on strategy.

    Supported indicators: SMA_crossover, RSI
    """
    indicator = strategy.get("indicator", "SMA_crossover")
    params = strategy.get("params", {})
    n = len(prices)
    signals = [0] * n

    if indicator == "SMA_crossover":
        short_w = params.get("short_window", 20)
        long_w = params.get("long_window", 50)
        short_sma = compute_sma(prices, short_w)
        long_sma = compute_sma(prices, long_w)

        for i in range(1, n):
            if short_sma[i] is not None and long_sma[i] is not None:
                if short_sma[i - 1] is not None and long_sma[i - 1] is not None:
                    # Golden cross — buy
                    if short_sma[i] > long_sma[i] and short_sma[i - 1] <= long_sma[i - 1]:
                        signals[i] = 1
                    # Death cross — sell
                    elif short_sma[i] < long_sma[i] and short_sma[i - 1] >= long_sma[i - 1]:
                        signals[i] = -1

    elif indicator == "RSI":
        period = params.get("rsi_period", 14)
        oversold = params.get("rsi_oversold", 30)
        overbought = params.get("rsi_overbought", 70)
        rsi_values = compute_rsi(prices, period)

        for i in range(1, n):
            if rsi_values[i] is not None and rsi_values[i - 1] is not None:
                # Buy when RSI crosses below oversold
                if rsi_values[i] <= oversold and rsi_values[i - 1] > oversold:
                    signals[i] = 1
                # Sell when RSI crosses above overbought
                elif rsi_values[i] >= overbought and rsi_values[i - 1] < overbought:
                    signals[i] = -1

    elif indicator in ("MACD", "bollinger_bands"):
        # Fallback to SMA crossover for simplicity in the demo
        short_w = params.get("short_window", 12)
        long_w = params.get("long_window", 26)
        short_sma = compute_sma(prices, short_w)
        long_sma = compute_sma(prices, long_w)

        for i in range(1, n):
            if short_sma[i] is not None and long_sma[i] is not None:
                if short_sma[i - 1] is not None and long_sma[i - 1] is not None:
                    if short_sma[i] > long_sma[i] and short_sma[i - 1] <= long_sma[i - 1]:
                        signals[i] = 1
                    elif short_sma[i] < long_sma[i] and short_sma[i - 1] >= long_sma[i - 1]:
                        signals[i] = -1

    return signals


def run_backtest(prices: list[float], strategy: dict) -> dict:
    """Run a backtest over historical prices using the given strategy.

    Returns metrics: total_return, sharpe_ratio, max_drawdown, win_rate, num_trades, trades.
    """
    stop_loss_pct = strategy.get("stop_loss_pct", 5.0) / 100.0
    signals = generate_signals(prices, strategy)

    trades = []
    position = None  # {"entry_price": float, "entry_idx": int}
    daily_returns = []

    for i in range(len(prices)):
        # Check stop loss if in position
        if position is not None:
            pct_change = (prices[i] - position["entry_price"]) / position["entry_price"]
            if pct_change <= -stop_loss_pct:
                # Stop loss triggered
                ret = -stop_loss_pct
                trades.append({
                    "entry_idx": position["entry_idx"],
                    "exit_idx": i,
                    "entry_price": position["entry_price"],
                    "exit_price": prices[i],
                    "return": ret,
                    "reason": "stop_loss",
                })
                daily_returns.append(ret)
                position = None
                continue

        if signals[i] == 1 and position is None:
            # Open position
            position = {"entry_price": prices[i], "entry_idx": i}
        elif signals[i] == -1 and position is not None:
            # Close position
            ret = (prices[i] - position["entry_price"]) / position["entry_price"]
            trades.append({
                "entry_idx": position["entry_idx"],
                "exit_idx": i,
                "entry_price": position["entry_price"],
                "exit_price": prices[i],
                "return": ret,
                "reason": "signal",
            })
            daily_returns.append(ret)
            position = None

    # Close any open position at end
    if position is not None:
        ret = (prices[-1] - position["entry_price"]) / position["entry_price"]
        trades.append({
            "entry_idx": position["entry_idx"],
            "exit_idx": len(prices) - 1,
            "entry_price": position["entry_price"],
            "exit_price": prices[-1],
            "return": ret,
            "reason": "end_of_data",
        })
        daily_returns.append(ret)

    # Calculate metrics
    num_trades = len(trades)
    if num_trades == 0:
        return {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "num_trades": 0,
            "trades": [],
        }

    total_return = sum(daily_returns)
    wins = [r for r in daily_returns if r > 0]
    win_rate = len(wins) / num_trades if num_trades > 0 else 0.0

    # Sharpe ratio (simplified: mean return / std of returns, annualized)
    if len(daily_returns) > 1 and np.std(daily_returns) > 0:
        sharpe = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252 / max(num_trades, 1))
    else:
        sharpe = 0.0

    # Max drawdown from cumulative returns
    cumulative = np.cumsum(daily_returns)
    peak = np.maximum.accumulate(cumulative)
    drawdowns = cumulative - peak
    max_drawdown = abs(float(np.min(drawdowns))) if len(drawdowns) > 0 else 0.0

    metrics = {
        "total_return": round(float(total_return) * 100, 2),  # percentage
        "sharpe_ratio": round(float(sharpe), 2),
        "max_drawdown": round(float(max_drawdown) * 100, 2),  # percentage
        "win_rate": round(float(win_rate) * 100, 2),  # percentage
        "num_trades": num_trades,
        "trades": trades,
    }

    logger.info(
        "Backtest complete | return=%.2f%% sharpe=%.2f drawdown=%.2f%% win_rate=%.2f%% trades=%d",
        metrics["total_return"],
        metrics["sharpe_ratio"],
        metrics["max_drawdown"],
        metrics["win_rate"],
        metrics["num_trades"],
    )
    return metrics
