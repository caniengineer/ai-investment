"""RAG endpoints — ingest documents and query the knowledge base."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.rag import ingest_document, search

router = APIRouter()


class IngestRequest(BaseModel):
    content: str
    source: str = "user_upload"

    model_config = {"json_schema_extra": {
        "examples": [{"content": "RSI below 30 is an oversold signal...", "source": "my_notes.md"}]
    }}


class QueryRequest(BaseModel):
    query: str
    top_k: int = 3

    model_config = {"json_schema_extra": {
        "examples": [{"query": "momentum strategies using moving averages", "top_k": 3}]
    }}


@router.post("/rag/ingest")
def ingest(request: IngestRequest, db: Session = Depends(get_db)):
    """Add a document to the knowledge base."""
    try:
        count = ingest_document(db, request.content, request.source)
        return {"message": f"Ingested {count} chunks from {request.source}", "chunks": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@router.post("/rag/query")
def query(request: QueryRequest, db: Session = Depends(get_db)):
    """Search the knowledge base with a natural language query."""
    try:
        results = search(db, request.query, top_k=request.top_k)
        return {"query": request.query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
