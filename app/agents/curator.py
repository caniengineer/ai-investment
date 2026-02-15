"""Curator — converts reflection feedback into playbook updates.

Part of the ACE (Agentic Context Engineering) loop:
    Generator → [Backtest] → Reflector → Curator → Updated Playbook

The Curator receives reflection outputs and decides what to ADD to the playbook.
It also updates helpful/harmful counters on existing entries based on tags.
"""

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.llm import LLMProvider
from app.core.playbook import Playbook, DEFAULT_SECTIONS
from app.observability.logger import log_llm_call, log_agent_action

logger = logging.getLogger("alphaagent.curator")

CURATOR_PROMPT = Path("prompts/curator.txt").read_text() if Path("prompts/curator.txt").exists() else ""


def curate(
    reflections: list[dict],
    playbook: Playbook,
    llm: LLMProvider,
    db: Session,
) -> dict:
    """Process reflection feedback and update the playbook.

    Args:
        reflections: List of reflection outputs from the Reflector.
        playbook: The Playbook instance to update.
        llm: LLM provider for curation decisions.
        db: Database session.

    Returns:
        Summary of operations applied.
    """
    log_agent_action(db, "curator", "start",
                     f"Curating {len(reflections)} reflections")

    # Step 1: Apply counter updates from bullet_tags (deterministic, no LLM needed)
    counter_updates = _apply_counter_updates(reflections, playbook)

    # Step 2: Ask LLM to decide on new entries based on reflections
    playbook_text = playbook.render()
    stats = playbook.get_stats()

    reflections_text = "\n\n".join(
        f"Reflection {i+1}:\n{json.dumps(r, indent=2)}"
        for i, r in enumerate(reflections)
    )

    prompt = f"""Review these recent reflections and decide what to add to the playbook.

Current Playbook:
{playbook_text}

Playbook Statistics:
{json.dumps(stats, indent=2)}

Recent Reflections:
{reflections_text}

Produce your curation operations as JSON."""

    messages = [{"role": "user", "content": prompt}]
    response = llm.complete(messages, system=CURATOR_PROMPT)
    log_llm_call(db, response, tool_called="curate")

    # Parse and apply operations
    operations = _parse_operations(response.content)
    adds = _apply_operations(operations, playbook)

    summary = {
        "counter_updates": counter_updates,
        "entries_added": adds,
        "total_reflections_processed": len(reflections),
    }

    log_agent_action(db, "curator", "complete",
                     f"Updated {counter_updates} counters, added {adds} entries")

    return summary


def _apply_counter_updates(reflections: list[dict], playbook: Playbook) -> int:
    """Apply helpful/harmful counter updates from reflection bullet_tags."""
    count = 0
    for reflection in reflections:
        tags = reflection.get("bullet_tags", {})
        for entry_id in tags.get("helpful", []):
            if playbook.get_entry(entry_id):
                playbook.update_counts(entry_id, helpful_delta=1)
                count += 1
        for entry_id in tags.get("harmful", []):
            if playbook.get_entry(entry_id):
                playbook.update_counts(entry_id, harmful_delta=1)
                count += 1
    return count


def _parse_operations(text: str) -> list[dict]:
    """Parse curator JSON output into a list of operations."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            ops = result.get("operations", [])
            # Validate each operation
            valid = []
            for op in ops:
                if op.get("type") == "ADD" and op.get("section") and op.get("content"):
                    if op["section"] in DEFAULT_SECTIONS:
                        valid.append(op)
                    else:
                        logger.warning("Curator suggested unknown section: %s", op["section"])
            return valid
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Could not parse curator output: %s", e)
    return []


def _apply_operations(operations: list[dict], playbook: Playbook) -> int:
    """Apply curator operations to the playbook. Returns count of entries added."""
    added = 0
    for op in operations:
        if op["type"] == "ADD":
            playbook.add_entry(op["section"], op["content"])
            added += 1
    return added
