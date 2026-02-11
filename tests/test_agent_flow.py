"""End-to-end tests for the agent flow.

Tests the full pipeline: input → strategy → backtest → deploy,
using mocked LLM and database.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.core.llm import LLMResponse
from app.core.tools import execute_tool, evaluate_results, fetch_market_data


class TestEvaluateResults:
    def test_passing_strategy(self):
        metrics = {"sharpe_ratio": 1.5, "max_drawdown": 10.0, "win_rate": 60.0}
        result = evaluate_results(metrics)
        assert result["passed"] is True

    def test_failing_sharpe(self):
        metrics = {"sharpe_ratio": 0.3, "max_drawdown": 10.0, "win_rate": 60.0}
        result = evaluate_results(metrics)
        assert result["passed"] is False
        assert not result["sharpe_ok"]

    def test_failing_drawdown(self):
        metrics = {"sharpe_ratio": 1.0, "max_drawdown": 30.0, "win_rate": 60.0}
        result = evaluate_results(metrics)
        assert result["passed"] is False
        assert not result["drawdown_ok"]

    def test_failing_win_rate(self):
        metrics = {"sharpe_ratio": 1.0, "max_drawdown": 10.0, "win_rate": 35.0}
        result = evaluate_results(metrics)
        assert result["passed"] is False
        assert not result["win_rate_ok"]

    def test_all_failing(self):
        metrics = {"sharpe_ratio": 0.1, "max_drawdown": 50.0, "win_rate": 20.0}
        result = evaluate_results(metrics)
        assert result["passed"] is False
        assert len(result["issues"]) == 3


class TestExecuteTool:
    def test_unknown_tool(self):
        result = execute_tool("nonexistent_tool", {}, MagicMock())
        assert "error" in result

    @patch("app.core.tools.rag")
    def test_search_knowledge_base(self, mock_rag):
        mock_rag.search.return_value = [
            {"content": "test chunk", "source": "test.md", "similarity": 0.9}
        ]
        db = MagicMock()
        result = execute_tool("search_knowledge_base", {"query": "momentum"}, db)
        assert len(result) == 1
        assert result[0]["content"] == "test chunk"


class TestFetchMarketData:
    @patch("app.core.tools.yf")
    def test_fetch_returns_data(self, mock_yf):
        """Test that fetch_market_data returns the expected structure."""
        import numpy as np

        # Create a mock that behaves like a pandas DataFrame
        mock_close = MagicMock()
        mock_close.values.flatten.return_value.tolist.return_value = [150.0, 151.0, 152.0, 153.0, 154.0]

        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.__getitem__ = MagicMock(return_value=mock_close)

        class MockDate:
            def __init__(self, s):
                self._s = s
            def strftime(self, fmt):
                return self._s

        mock_df.index = [MockDate(f"2024-01-0{i}") for i in range(1, 6)]
        mock_yf.download.return_value = mock_df

        result = fetch_market_data("AAPL", 1)
        assert result["ticker"] == "AAPL"
        assert len(result["prices"]) == 5
        assert result["latest_price"] == 154.0

    @patch("app.core.tools.yf")
    def test_fetch_empty_data(self, mock_yf):
        mock_df = MagicMock()
        mock_df.empty = True
        mock_yf.download.return_value = mock_df

        result = fetch_market_data("INVALID", 1)
        assert result["prices"] == []


class TestStrategyAgent:
    """Test strategy agent with mocked LLM."""

    @patch("app.agents.strategy_agent.SYSTEM_PROMPT", "test prompt")
    def test_strategy_agent_run(self):
        """Test that strategy agent produces a valid strategy dict."""
        mock_llm = MagicMock()
        mock_db = MagicMock()

        # First call: LLM requests a tool
        tool_response = LLMResponse(
            content="",
            tool_calls=[{
                "id": "call_1",
                "name": "search_knowledge_base",
                "arguments": {"query": "momentum strategies"},
            }],
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=200,
            model="test",
            provider="test",
        )

        # Second call: LLM returns the strategy
        strategy_json = json.dumps({
            "name": "Test SMA Strategy",
            "asset": "AAPL",
            "strategy_type": "momentum",
            "indicator": "SMA_crossover",
            "params": {"short_window": 20, "long_window": 50},
            "entry_rule": "Buy on golden cross",
            "exit_rule": "Sell on death cross",
            "stop_loss_pct": 5.0,
            "lookback_months": 12,
        })
        final_response = LLMResponse(
            content=strategy_json,
            tool_calls=[],
            prompt_tokens=200,
            completion_tokens=100,
            latency_ms=300,
            model="test",
            provider="test",
        )

        mock_llm.function_call.side_effect = [tool_response, final_response]

        with patch("app.agents.strategy_agent.execute_tool") as mock_exec:
            mock_exec.return_value = [{"content": "momentum info", "source": "test.md", "similarity": 0.9}]

            from app.agents.strategy_agent import run
            result = run("Build me a momentum strategy for AAPL", mock_llm, mock_db)

        assert result["asset"] == "AAPL"
        assert result["indicator"] == "SMA_crossover"
        assert "short_window" in result["params"]
