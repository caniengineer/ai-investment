"""Tests for the LLM abstraction layer."""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.core.llm import LLMResponse, get_llm_provider, AnthropicProvider, OpenAIProvider


class TestLLMResponse:
    def test_response_fields(self):
        resp = LLMResponse(
            content="test response",
            tool_calls=[],
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=150.5,
            model="test-model",
            provider="test",
        )
        assert resp.content == "test response"
        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 20
        assert resp.latency_ms == 150.5
        assert resp.model == "test-model"
        assert resp.provider == "test"

    def test_response_with_tool_calls(self):
        resp = LLMResponse(
            content="",
            tool_calls=[{"name": "fetch_market_data", "arguments": {"ticker": "AAPL"}}],
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=100.0,
            model="test",
            provider="test",
        )
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0]["name"] == "fetch_market_data"


class TestGetLLMProvider:
    @patch.dict(os.environ, {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key"})
    def test_returns_anthropic(self):
        with patch("anthropic.Anthropic"):
            provider = get_llm_provider()
            assert isinstance(provider, AnthropicProvider)

    @patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"})
    def test_returns_openai(self):
        with patch("openai.OpenAI"):
            provider = get_llm_provider()
            assert isinstance(provider, OpenAIProvider)

    @patch.dict(os.environ, {"LLM_PROVIDER": "unknown"})
    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            get_llm_provider()


class TestAnthropicProvider:
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_missing_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                AnthropicProvider()


class TestOpenAIProvider:
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_missing_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIProvider()
