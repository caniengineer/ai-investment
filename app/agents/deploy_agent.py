"""Sub-Agent 3 — Deploy to Paper Trading.

Takes the approved strategy and starts a simulated paper trade.
"""

import logging

from sqlalchemy.orm import Session

from app.core.llm import LLMProvider
from app.core.paper_trade import start_paper_trade
from app.db.models import Strategy, PaperTrade
from app.observability.logger import log_agent_action

logger = logging.getLogger("alphaagent.deploy_agent")


def run(strategy_dict: dict, strategy_id: str, backtest_passed: bool,
        llm: LLMProvider, db: Session) -> dict:
    """Deploy strategy to paper trading.

    If backtest didn't pass, deploys with a warning flag.
    Returns deployment status.
    """
    log_agent_action(db, "deploy_agent", "start",
                     f"Deploying strategy {strategy_id} (backtest_passed={backtest_passed})",
                     strategy_id)

    # Update strategy status
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if strategy:
        strategy.status = "deployed"
        db.commit()

    # Start paper trading
    try:
        trade_id = start_paper_trade(strategy_id)

        result = {
            "trade_id": trade_id,
            "strategy_id": strategy_id,
            "status": "active",
            "backtest_passed": backtest_passed,
            "message": (
                f"Strategy '{strategy_dict.get('name', 'unknown')}' is now paper trading."
                if backtest_passed
                else f"Strategy '{strategy_dict.get('name', 'unknown')}' deployed with WARNING: "
                     "backtest did not pass all thresholds. Monitoring closely."
            ),
        }

        log_agent_action(db, "deploy_agent", "deployed",
                         f"Paper trade {trade_id} started", strategy_id)
        return result

    except Exception as e:
        logger.error("Failed to deploy strategy %s: %s", strategy_id, e)
        log_agent_action(db, "deploy_agent", "error", str(e), strategy_id)
        return {
            "strategy_id": strategy_id,
            "status": "error",
            "message": f"Deployment failed: {e}",
        }
