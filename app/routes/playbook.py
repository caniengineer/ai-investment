"""Playbook endpoints — view and manage the evolving playbook."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.playbook import Playbook, seed_playbook

router = APIRouter()


@router.get("/playbook")
def get_playbook(db: Session = Depends(get_db)):
    """View the current playbook state."""
    playbook = Playbook(db)
    entries = playbook.load_all()
    return {
        "stats": playbook.get_stats(),
        "rendered": playbook.render(),
        "entries": [
            {
                "entry_id": e.entry_id,
                "section": e.section,
                "content": e.content,
                "helpful_count": e.helpful_count,
                "harmful_count": e.harmful_count,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in entries
        ],
    }


@router.post("/playbook/reset")
def reset_playbook(db: Session = Depends(get_db)):
    """Reset the playbook to seed state."""
    playbook = Playbook(db)
    playbook.reset()
    seed_playbook(db)
    return {"status": "reset", "message": "Playbook reset to seed entries"}
