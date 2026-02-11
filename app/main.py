"""FastAPI application — entry point for AlphaAgent."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import init_db, SessionLocal
from app.core.rag import seed_knowledge_base
from app.routes import chat, strategies, rag, metrics

# Configure logging — print everything to console for demo visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("alphaagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init database, seed RAG knowledge base."""
    logger.info("=" * 60)
    logger.info("AlphaAgent starting up")
    logger.info("=" * 60)

    # Initialize database tables
    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready.")

    # Seed knowledge base from markdown files
    logger.info("Seeding knowledge base...")
    try:
        db = SessionLocal()
        seed_knowledge_base(db, seed_dir="seed_data")
        db.close()
        logger.info("Knowledge base ready.")
    except Exception as e:
        logger.warning("Could not seed knowledge base: %s", e)
        logger.warning("RAG features will work once OPENAI_API_KEY is set (needed for embeddings).")

    logger.info("=" * 60)
    logger.info("AlphaAgent ready — open /docs for Swagger UI")
    logger.info("=" * 60)

    yield

    logger.info("AlphaAgent shutting down")


app = FastAPI(
    title="AlphaAgent",
    description=(
        "Autonomous agentic investment platform. "
        "Send a natural language investment idea and three AI sub-agents "
        "will generate, backtest, and deploy a trading strategy."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Mount routes
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(strategies.router, prefix="/api/v1", tags=["Strategies"])
app.include_router(rag.router, prefix="/api/v1", tags=["RAG"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    return {
        "status": "healthy",
        "service": "AlphaAgent",
        "llm_provider": provider,
    }
