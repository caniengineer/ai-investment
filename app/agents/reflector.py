"""Reflector — analyzes backtest results to identify helpful/harmful patterns.

Part of the ACE (Agentic Context Engineering) loop:
    Generator → [Backtest] → Reflector → Curator → Updated Playbook

The Reflector does NOT modify the playbook. It produces structured feedback
that the Curator uses to decide what to update.
"""

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.llm import LLMProvider
from app.core.playbook import Playbook
from app.observability.logger import log_llm_call, log_agent_action

logger = logging.getLogger("alphaagent.reflector")

REFLECTOR_PROMPT = Path("prompts/reflector.txt").read_text() if Path("prompts/reflector.txt").exists() else ""


def reflect(
    strategy: dict,
    metrics: dict,
    passed: bool,
    playbook: Playbook,
    llm: LLMProvider,
    db: Session,
    strategy_id: str | None = None,
) -> dict:
    """Analyze a backtest result and identify helpful/harmful playbook entries.

    Args:
        strategy: The strategy definition that was backtested.
        metrics: Backtest metrics (sharpe_ratio, max_drawdown, win_rate, etc.).
        passed: Whether the backtest passed thresholds.
        playbook: The Playbook instance (to render current state).
        llm: LLM provider for analysis.
        db: Database session.
        strategy_id: Optional strategy ID for logging.

    Returns:
        Reflection dict with analysis, bullet_tags, and new_insights.
    """
    log_agent_action(db, "reflector", "start",
                     f"Reflecting on {'PASSED' if passed else 'FAILED'} backtest", strategy_id)

    playbook_text = playbook.render()

    prompt = f"""Analyze this backtest result and identify which playbook entries helped or hurt.

Strategy:
{json.dumps(strategy, indent=2)}

Backtest Metrics:
{json.dumps(metrics, indent=2)}

Result: {"PASSED" if passed else "FAILED"}

Current Playbook:
{playbook_text}

Produce your reflection as JSON."""

    messages = [{"role": "user", "content": prompt}]
    response = llm.complete(messages, system=REFLECTOR_PROMPT)
    log_llm_call(db, response, tool_called="reflect")

    # Parse reflection output
    reflection = _parse_reflection(response.content)

    log_agent_action(db, "reflector", "complete",
                     f"Tagged {len(reflection.get('bullet_tags', {}).get('helpful', []))} helpful, "
                     f"{len(reflection.get('bullet_tags', {}).get('harmful', []))} harmful, "
                     f"{len(reflection.get('new_insights', []))} new insights",
                     strategy_id)

    return reflection


def _parse_reflection(text: str) -> dict:
    """Parse the reflector's JSON output."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            # Validate structure
            result.setdefault("analysis", "")
            result.setdefault("bullet_tags", {"helpful": [], "harmful": []})
            result.setdefault("new_insights", [])
            return result
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Could not parse reflector output: %s", e)

    return {
        "analysis": "Could not parse reflection output",
        "bullet_tags": {"helpful": [], "harmful": []},
        "new_insights": [],
    }
