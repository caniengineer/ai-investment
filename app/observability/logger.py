"""Structured logging for every LLM call and agent decision."""

import logging
import datetime

from sqlalchemy.orm import Session

from app.db.models import AgentLog, LLMMetric
from app.core.llm import LLMResponse

logger = logging.getLogger("alphaagent")


def log_llm_call(db: Session, response: LLMResponse, tool_called: str | None = None):
    """Log an LLM API call to the database and console."""
    metric = LLMMetric(
        provider=response.provider,
        model=response.model,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        latency_ms=response.latency_ms,
        tool_called=tool_called,
    )
    db.add(metric)
    db.commit()

    logger.info(
        "LLM call | provider=%s model=%s tokens=%d+%d latency=%.0fms tool=%s",
        response.provider,
        response.model,
        response.prompt_tokens,
        response.completion_tokens,
        response.latency_ms,
        tool_called or "none",
    )


def log_agent_action(
    db: Session, agent: str, action: str, detail: str, strategy_id: str | None = None
):
    """Log an agent decision to the database and console."""
    entry = AgentLog(
        strategy_id=strategy_id,
        agent=agent,
        action=action,
        detail=detail,
    )
    db.add(entry)
    db.commit()

    logger.info("Agent [%s] %s | %s (strategy=%s)", agent, action, detail, strategy_id or "n/a")
