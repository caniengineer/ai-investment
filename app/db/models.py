"""SQLAlchemy models for AlphaAgent."""

import datetime
import uuid

from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean
from pgvector.sqlalchemy import Vector

from app.db.database import Base


def _uuid():
    return str(uuid.uuid4())


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    asset = Column(String, nullable=False)
    strategy_type = Column(String, nullable=False)
    indicator = Column(String, nullable=False)
    params = Column(JSON, nullable=False)
    entry_rule = Column(Text, nullable=False)
    exit_rule = Column(Text, nullable=False)
    stop_loss_pct = Column(Float, nullable=False)
    lookback_months = Column(Integer, nullable=False)
    status = Column(String, default="created")  # created, backtested, deployed, paused
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(String, primary_key=True, default=_uuid)
    strategy_id = Column(String, nullable=False)
    iteration = Column(Integer, nullable=False)
    total_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    num_trades = Column(Integer)
    passed = Column(Boolean, default=False)
    changes_made = Column(Text)  # what changed from previous iteration
    metrics = Column(JSON)  # full metrics dict
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(String, primary_key=True, default=_uuid)
    strategy_id = Column(String, nullable=False)
    status = Column(String, default="active")  # active, paused, stopped
    entry_price = Column(Float)
    current_price = Column(Float)
    position = Column(String, default="flat")  # flat, long
    pnl = Column(Float, default=0.0)
    order_history = Column(JSON, default=list)
    last_check = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String, primary_key=True, default=_uuid)
    source = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # text-embedding-3-small outputs 1536 dims
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=_uuid)
    strategy_id = Column(String)
    agent = Column(String, nullable=False)  # strategy_agent, backtest_agent, deploy_agent
    action = Column(String, nullable=False)
    detail = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class LLMMetric(Base):
    __tablename__ = "llm_metrics"

    id = Column(String, primary_key=True, default=_uuid)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Float)
    tool_called = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
