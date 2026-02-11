"""Chat endpoint — main entry point for the agent pipeline."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.llm import get_llm_provider
from app.agents.orchestrator import process_message

logger = logging.getLogger("alphaagent.routes.chat")
router = APIRouter()


class ChatRequest(BaseModel):
    message: str

    model_config = {"json_schema_extra": {
        "examples": [{"message": "Build me a simple moving average crossover strategy for AAPL"}]
    }}


class ChatResponse(BaseModel):
    strategy_id: str
    strategy: dict
    backtest: dict
    deployment: dict
    summary: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a natural language investment idea. The agent pipeline will generate,
    backtest, and deploy a strategy autonomously."""
    try:
        llm = get_llm_provider()
        result = process_message(request.message, llm, db)
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Chat endpoint error")
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {e}")
