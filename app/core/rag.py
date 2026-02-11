"""RAG pipeline: embed, store, and retrieve from pgvector."""

import os
import logging
from pathlib import Path

import openai
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk

logger = logging.getLogger("alphaagent.rag")

_openai_client = None


def _get_openai():
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for embeddings")
        _openai_client = openai.OpenAI(api_key=api_key)
    return _openai_client


def embed_text(text_input: str) -> list[float]:
    """Generate an embedding for a text string using OpenAI text-embedding-3-small."""
    client = _get_openai()
    response = client.embeddings.create(model="text-embedding-3-small", input=text_input)
    return response.data[0].embedding


def split_into_chunks(content: str, source: str) -> list[dict]:
    """Split a document into chunks by paragraph. Simple — no fancy chunking."""
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) > 50:  # skip very short fragments
            chunks.append({"content": para, "source": source})
    return chunks


def ingest_document(db: Session, content: str, source: str) -> int:
    """Embed and store a document's chunks in pgvector. Returns number of chunks stored."""
    chunks = split_into_chunks(content, source)
    count = 0
    for chunk in chunks:
        embedding = embed_text(chunk["content"])
        kc = KnowledgeChunk(
            source=chunk["source"],
            content=chunk["content"],
            embedding=embedding,
        )
        db.add(kc)
        count += 1
    db.commit()
    logger.info("Ingested %d chunks from %s", count, source)
    return count


def search(db: Session, query: str, top_k: int = 3) -> list[dict]:
    """Semantic search: embed the query, find top-k similar chunks by cosine similarity."""
    query_embedding = embed_text(query)

    # pgvector cosine distance operator: <=>
    results = db.execute(
        text(
            """
            SELECT id, source, content,
                   1 - (embedding <=> :embedding::vector) AS similarity
            FROM knowledge_chunks
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
            """
        ),
        {"embedding": str(query_embedding), "limit": top_k},
    ).fetchall()

    return [
        {"source": r.source, "content": r.content, "similarity": round(r.similarity, 4)}
        for r in results
    ]


def seed_knowledge_base(db: Session, seed_dir: str = "seed_data"):
    """Load all markdown files from seed_dir into the knowledge base."""
    seed_path = Path(seed_dir)
    if not seed_path.exists():
        logger.warning("Seed directory %s not found, skipping", seed_dir)
        return

    # Check if already seeded
    count = db.query(KnowledgeChunk).count()
    if count > 0:
        logger.info("Knowledge base already has %d chunks, skipping seed", count)
        return

    for md_file in sorted(seed_path.glob("*.md")):
        logger.info("Seeding from %s", md_file.name)
        content = md_file.read_text()
        ingest_document(db, content, source=md_file.name)

    total = db.query(KnowledgeChunk).count()
    logger.info("Knowledge base seeded with %d total chunks", total)
