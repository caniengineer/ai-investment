"""Metrics endpoint — LLM usage, latency, and tool call stats."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import LLMMetric, AgentLog

router = APIRouter()


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """Get a JSON summary of LLM usage, latency, and tool call stats."""
    # LLM usage stats
    llm_stats = db.query(
        LLMMetric.provider,
        LLMMetric.model,
        func.count(LLMMetric.id).label("total_calls"),
        func.sum(LLMMetric.prompt_tokens).label("total_prompt_tokens"),
        func.sum(LLMMetric.completion_tokens).label("total_completion_tokens"),
        func.avg(LLMMetric.latency_ms).label("avg_latency_ms"),
    ).group_by(LLMMetric.provider, LLMMetric.model).all()

    # Tool call breakdown
    tool_stats = db.query(
        LLMMetric.tool_called,
        func.count(LLMMetric.id).label("count"),
    ).filter(LLMMetric.tool_called.isnot(None)).group_by(LLMMetric.tool_called).all()

    # Agent action breakdown
    agent_stats = db.query(
        AgentLog.agent,
        AgentLog.action,
        func.count(AgentLog.id).label("count"),
    ).group_by(AgentLog.agent, AgentLog.action).all()

    return {
        "llm_usage": [
            {
                "provider": s.provider,
                "model": s.model,
                "total_calls": s.total_calls,
                "total_prompt_tokens": s.total_prompt_tokens or 0,
                "total_completion_tokens": s.total_completion_tokens or 0,
                "avg_latency_ms": round(s.avg_latency_ms or 0, 1),
            }
            for s in llm_stats
        ],
        "tool_calls": [
            {"tool": t.tool_called, "count": t.count}
            for t in tool_stats
        ],
        "agent_actions": [
            {"agent": a.agent, "action": a.action, "count": a.count}
            for a in agent_stats
        ],
    }
