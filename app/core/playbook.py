"""Playbook — evolving context for LLM agents.

Implements the ACE (Agentic Context Engineering) pattern: structured knowledge
entries with helpful/harmful counters that evolve based on execution feedback.

Each entry follows the format:
    [section_prefix-00001] helpful=N harmful=M :: content text

Sections organize entries by concern (strategies, mistakes, parameters, etc.).
Counters track which entries actually help vs hurt agent performance.
"""

import re
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import PlaybookEntry

logger = logging.getLogger("alphaagent.playbook")

# Default sections for the trading strategy domain
DEFAULT_SECTIONS = [
    "STRATEGIES & INSIGHTS",
    "PARAMETER GUIDANCE",
    "COMMON MISTAKES",
    "EVALUATION PATTERNS",
]

# Section prefix mapping
SECTION_PREFIXES = {
    "STRATEGIES & INSIGHTS": "str",
    "PARAMETER GUIDANCE": "prm",
    "COMMON MISTAKES": "err",
    "EVALUATION PATTERNS": "evl",
}

# Pattern to parse a playbook line
BULLET_PATTERN = re.compile(
    r"\[(?P<id>[a-z]+-\d+)\]\s+helpful=(?P<helpful>\d+)\s+harmful=(?P<harmful>\d+)\s+::\s+(?P<content>.+)"
)


def parse_playbook_line(line: str) -> dict | None:
    """Parse a single playbook bullet line into its components."""
    m = BULLET_PATTERN.match(line.strip())
    if not m:
        return None
    return {
        "id": m.group("id"),
        "helpful": int(m.group("helpful")),
        "harmful": int(m.group("harmful")),
        "content": m.group("content"),
    }


def format_playbook_line(entry_id: str, helpful: int, harmful: int, content: str) -> str:
    """Format a playbook entry as a bullet line."""
    return f"[{entry_id}] helpful={helpful} harmful={harmful} :: {content}"


class Playbook:
    """Manages the evolving playbook for LLM agents."""

    def __init__(self, db: Session):
        self.db = db

    def load_all(self) -> list[PlaybookEntry]:
        """Load all playbook entries from DB."""
        return self.db.query(PlaybookEntry).order_by(PlaybookEntry.section, PlaybookEntry.entry_id).all()

    def load_section(self, section: str) -> list[PlaybookEntry]:
        """Load entries for a specific section."""
        return (
            self.db.query(PlaybookEntry)
            .filter(PlaybookEntry.section == section)
            .order_by(PlaybookEntry.entry_id)
            .all()
        )

    def render(self, sections: list[str] | None = None) -> str:
        """Render the playbook as formatted text for LLM prompts.

        Args:
            sections: Specific sections to include (None = all).
        """
        entries = self.load_all()
        if not entries:
            return ""

        # Group by section
        by_section: dict[str, list[PlaybookEntry]] = {}
        for entry in entries:
            by_section.setdefault(entry.section, []).append(entry)

        # Filter to requested sections
        if sections:
            by_section = {k: v for k, v in by_section.items() if k in sections}

        lines = ["# PLAYBOOK — Learned Insights", ""]
        for section_name in DEFAULT_SECTIONS:
            if section_name not in by_section:
                continue
            lines.append(f"## {section_name}")
            for entry in by_section[section_name]:
                lines.append(format_playbook_line(
                    entry.entry_id, entry.helpful_count, entry.harmful_count, entry.content
                ))
            lines.append("")

        # Include any non-default sections
        for section_name, section_entries in by_section.items():
            if section_name in DEFAULT_SECTIONS:
                continue
            lines.append(f"## {section_name}")
            for entry in section_entries:
                lines.append(format_playbook_line(
                    entry.entry_id, entry.helpful_count, entry.harmful_count, entry.content
                ))
            lines.append("")

        return "\n".join(lines)

    def get_next_id(self, section: str) -> str:
        """Generate the next sequential ID for a section."""
        prefix = SECTION_PREFIXES.get(section, "gen")
        entries = self.load_section(section)
        if not entries:
            return f"{prefix}-00001"

        # Find highest existing number
        max_num = 0
        for entry in entries:
            parts = entry.entry_id.split("-")
            if len(parts) == 2:
                try:
                    max_num = max(max_num, int(parts[1]))
                except ValueError:
                    pass
        return f"{prefix}-{max_num + 1:05d}"

    def add_entry(self, section: str, content: str) -> PlaybookEntry:
        """Add a new entry to a section."""
        entry_id = self.get_next_id(section)
        entry = PlaybookEntry(
            entry_id=entry_id,
            section=section,
            content=content,
            helpful_count=0,
            harmful_count=0,
        )
        self.db.add(entry)
        self.db.commit()
        logger.info("Added playbook entry %s to %s", entry_id, section)
        return entry

    def update_counts(self, entry_id: str, helpful_delta: int = 0, harmful_delta: int = 0):
        """Increment helpful/harmful counters on an entry."""
        entry = self.db.query(PlaybookEntry).filter(PlaybookEntry.entry_id == entry_id).first()
        if entry:
            entry.helpful_count += helpful_delta
            entry.harmful_count += harmful_delta
            entry.updated_at = datetime.now(timezone.utc)
            self.db.commit()

    def get_entry(self, entry_id: str) -> PlaybookEntry | None:
        """Get a specific entry by ID."""
        return self.db.query(PlaybookEntry).filter(PlaybookEntry.entry_id == entry_id).first()

    def get_stats(self) -> dict:
        """Get playbook statistics for curator context."""
        entries = self.load_all()
        by_section: dict[str, list] = {}
        for e in entries:
            by_section.setdefault(e.section, []).append(e)

        stats = {
            "total_entries": len(entries),
            "sections": {},
        }
        for section, section_entries in by_section.items():
            stats["sections"][section] = {
                "count": len(section_entries),
                "avg_helpful": sum(e.helpful_count for e in section_entries) / max(len(section_entries), 1),
                "avg_harmful": sum(e.harmful_count for e in section_entries) / max(len(section_entries), 1),
            }
        return stats

    def reset(self):
        """Clear all playbook entries."""
        self.db.query(PlaybookEntry).delete()
        self.db.commit()
        logger.info("Playbook reset — all entries cleared")


# ---------------------------------------------------------------------------
# Seed data — initial playbook entries derived from domain knowledge
# ---------------------------------------------------------------------------

SEED_ENTRIES = [
    # STRATEGIES & INSIGHTS
    ("STRATEGIES & INSIGHTS", "SMA crossover strategies work best with short_window=20 and long_window=50 for daily timeframes"),
    ("STRATEGIES & INSIGHTS", "RSI strategies should use period=14, oversold=30, overbought=70 as starting parameters"),
    ("STRATEGIES & INSIGHTS", "Momentum strategies perform better on trending assets like tech stocks (AAPL, MSFT, GOOGL)"),
    ("STRATEGIES & INSIGHTS", "Mean reversion strategies work better on range-bound assets and indices (SPY, QQQ)"),
    ("STRATEGIES & INSIGHTS", "Always combine entry signals with a stop loss to limit downside risk"),

    # PARAMETER GUIDANCE
    ("PARAMETER GUIDANCE", "Short SMA windows below 10 cause excessive whipsaws — prefer 15-25 range"),
    ("PARAMETER GUIDANCE", "Long SMA windows above 100 are too slow to react — prefer 40-60 range"),
    ("PARAMETER GUIDANCE", "Stop loss between 3-7% balances risk management with avoiding noise-triggered exits"),
    ("PARAMETER GUIDANCE", "Lookback period of 12 months provides sufficient data for most indicator-based strategies"),
    ("PARAMETER GUIDANCE", "RSI oversold below 25 generates too few signals; above 35 generates too many false positives"),

    # COMMON MISTAKES
    ("COMMON MISTAKES", "Setting short_window too close to long_window produces almost no crossover signals"),
    ("COMMON MISTAKES", "Stop loss below 2% gets triggered by normal daily volatility — avoid"),
    ("COMMON MISTAKES", "Backtesting on less than 6 months of data produces unreliable results"),
    ("COMMON MISTAKES", "Ignoring drawdown in favor of total return leads to strategies that blow up in practice"),

    # EVALUATION PATTERNS
    ("EVALUATION PATTERNS", "Sharpe ratio below 0.5 typically indicates the strategy adds no value over buy-and-hold"),
    ("EVALUATION PATTERNS", "Win rate alone is misleading — a 30% win rate with high reward:risk ratio can still be profitable"),
    ("EVALUATION PATTERNS", "Drawdown above 25% makes a strategy psychologically difficult to stick with"),
    ("EVALUATION PATTERNS", "If a strategy makes fewer than 5 trades in a 12-month backtest, the sample size is too small to trust"),
]


def seed_playbook(db: Session):
    """Seed the playbook with initial entries if empty."""
    existing = db.query(PlaybookEntry).count()
    if existing > 0:
        logger.info("Playbook already has %d entries, skipping seed", existing)
        return

    playbook = Playbook(db)
    for section, content in SEED_ENTRIES:
        playbook.add_entry(section, content)
    logger.info("Seeded playbook with %d entries", len(SEED_ENTRIES))
