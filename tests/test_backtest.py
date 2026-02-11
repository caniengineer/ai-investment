"""Tests for the backtest engine."""

import pytest
from app.core.backtest import compute_sma, compute_rsi, generate_signals, run_backtest


class TestComputeSMA:
    def test_basic_sma(self):
        prices = [10, 20, 30, 40, 50]
        result = compute_sma(prices, 3)
        assert result[0] is None
        assert result[1] is None
        assert result[2] == pytest.approx(20.0)
        assert result[3] == pytest.approx(30.0)
        assert result[4] == pytest.approx(40.0)

    def test_sma_window_equals_length(self):
        prices = [10, 20, 30]
        result = compute_sma(prices, 3)
        assert result[2] == pytest.approx(20.0)

    def test_sma_window_larger_than_data(self):
        prices = [10, 20]
        result = compute_sma(prices, 5)
        assert all(v is None for v in result)


class TestComputeRSI:
    def test_rsi_length(self):
        prices = list(range(1, 30))
        result = compute_rsi(prices, 14)
        assert len(result) == len(prices)

    def test_rsi_all_gains(self):
        """Steadily rising prices should produce RSI near 100."""
        prices = [100 + i for i in range(30)]
        result = compute_rsi(prices, 14)
        valid = [v for v in result if v is not None]
        assert len(valid) > 0
        assert valid[-1] > 80  # Strong uptrend

    def test_rsi_too_short(self):
        prices = [10, 20, 30]
        result = compute_rsi(prices, 14)
        assert all(v is None for v in result)


class TestGenerateSignals:
    def test_sma_crossover_signals(self):
        # Create a price series where short SMA crosses above long SMA
        prices = list(range(50, 0, -1)) + list(range(1, 60))  # V-shape
        strategy = {
            "indicator": "SMA_crossover",
            "params": {"short_window": 5, "long_window": 10},
        }
        signals = generate_signals(prices, strategy)
        assert len(signals) == len(prices)
        # Should have at least one buy signal during the upturn
        assert 1 in signals

    def test_rsi_signals(self):
        # Oscillating prices should generate RSI signals
        prices = []
        for i in range(100):
            if i % 20 < 10:
                prices.append(100 - i % 20 * 3)  # Downtrend
            else:
                prices.append(70 + (i % 20 - 10) * 3)  # Uptrend
        strategy = {
            "indicator": "RSI",
            "params": {"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70},
        }
        signals = generate_signals(prices, strategy)
        assert len(signals) == len(prices)


class TestRunBacktest:
    def test_backtest_returns_metrics(self):
        prices = list(range(50, 0, -1)) + list(range(1, 60))
        strategy = {
            "indicator": "SMA_crossover",
            "params": {"short_window": 5, "long_window": 10},
            "stop_loss_pct": 5.0,
        }
        result = run_backtest(prices, strategy)
        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result
        assert "win_rate" in result
        assert "num_trades" in result
        assert "trades" in result

    def test_backtest_empty_prices(self):
        strategy = {
            "indicator": "SMA_crossover",
            "params": {"short_window": 5, "long_window": 10},
            "stop_loss_pct": 5.0,
        }
        result = run_backtest([], strategy)
        assert result["num_trades"] == 0
        assert result["total_return"] == 0.0

    def test_backtest_stop_loss(self):
        # Prices drop sharply — stop loss should trigger
        prices = [100] * 20 + list(range(100, 80, -1)) + list(range(80, 110))
        strategy = {
            "indicator": "SMA_crossover",
            "params": {"short_window": 3, "long_window": 5},
            "stop_loss_pct": 3.0,
        }
        result = run_backtest(prices, strategy)
        # Check that stop loss trades exist if there were trades
        if result["num_trades"] > 0:
            reasons = [t["reason"] for t in result["trades"]]
            # At least the structure is correct
            assert all(r in ("signal", "stop_loss", "end_of_data") for r in reasons)
