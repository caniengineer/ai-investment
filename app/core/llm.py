"""Provider-agnostic LLM abstraction.

Supports Anthropic Claude and OpenAI as a swappable fallback.
A single config flag (LLM_PROVIDER env var) switches between them.
"""

import json
import os
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger("alphaagent.llm")


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""
    content: str
    tool_calls: list  # list of {"name": str, "arguments": dict}
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    model: str
    provider: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, messages: list, system: str = "", max_tokens: int = 4096) -> LLMResponse:
        """Send messages and get a text response."""
        ...

    @abstractmethod
    def function_call(self, messages: list, tools: list, system: str = "") -> LLMResponse:
        """Send messages with tool definitions and get a response that may include tool calls."""
        ...


class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation."""

    def __init__(self):
        import anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
        self.provider_name = "anthropic"

    def complete(self, messages: list, system: str = "", max_tokens: int = 4096) -> LLMResponse:
        start = time.time()
        kwargs = {"model": self.model, "max_tokens": max_tokens, "messages": messages}
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(**kwargs)
        latency = (time.time() - start) * 1000

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            tool_calls=[],
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            latency_ms=latency,
            model=self.model,
            provider=self.provider_name,
        )

    def function_call(self, messages: list, tools: list, system: str = "") -> LLMResponse:
        start = time.time()
        # Convert tool definitions to Anthropic format
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],
            })

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
            "tools": anthropic_tools,
        }
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(**kwargs)
        latency = (time.time() - start) * 1000

        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            latency_ms=latency,
            model=self.model,
            provider=self.provider_name,
        )


class OpenAIProvider(LLMProvider):
    """OpenAI implementation (swappable fallback)."""

    def __init__(self):
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.provider_name = "openai"

    def complete(self, messages: list, system: str = "", max_tokens: int = 4096) -> LLMResponse:
        start = time.time()
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        for msg in messages:
            oai_messages.append({"role": msg["role"], "content": msg["content"]})

        response = self.client.chat.completions.create(
            model=self.model, messages=oai_messages, max_tokens=max_tokens
        )
        latency = (time.time() - start) * 1000

        return LLMResponse(
            content=response.choices[0].message.content or "",
            tool_calls=[],
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_ms=latency,
            model=self.model,
            provider=self.provider_name,
        )

    def function_call(self, messages: list, tools: list, system: str = "") -> LLMResponse:
        start = time.time()
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        for msg in messages:
            oai_messages.append({"role": msg["role"], "content": msg["content"]})

        # Convert tool definitions to OpenAI format
        oai_tools = []
        for tool in tools:
            oai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            })

        response = self.client.chat.completions.create(
            model=self.model, messages=oai_messages, tools=oai_tools, max_tokens=4096
        )
        latency = (time.time() - start) * 1000

        content = response.choices[0].message.content or ""
        tool_calls = []
        if response.choices[0].message.tool_calls:
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_ms=latency,
            model=self.model,
            provider=self.provider_name,
        )


def get_llm_provider() -> LLMProvider:
    """Factory function. Returns the configured LLM provider."""
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        logger.info("Using Anthropic Claude as LLM provider")
        return AnthropicProvider()
    elif provider == "openai":
        logger.info("Using OpenAI as LLM provider")
        return OpenAIProvider()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'anthropic' or 'openai'.")
