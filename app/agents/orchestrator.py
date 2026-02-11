"""Orchestrator — runs sub-agents 1 → 2 → 3 in sequence.

This is the main entry point for processing a user's chat message.
"""

import logging

from sqlalchemy.orm import Session

from app.core.llm import LLMProvider
from app.db.models import Strategy
from app.agents import strategy_agent, backtest_agent, deploy_agent
from app.observability.logger import log_agent_action

logger = logging.getLogger("alphaagent.orchestrator")


def process_message(user_message: str, llm: LLMProvider, db: Session) -> dict:
    """Process a user message through the 3-agent pipeline.

    1. Strategy Generator → produces a strategy
    2. Backtest & Self-Heal → validates and refines
    3. Deploy to Paper Trading → starts simulated trading

    Returns a complete result with strategy, backtest, and deployment info.
    """
    log_agent_action(db, "orchestrator", "start", f"Processing: {user_message[:100]}")

    # --- Sub-Agent 1: Strategy Generator ---
    logger.info("=" * 60)
    logger.info("SUB-AGENT 1: Strategy Generator")
    logger.info("=" * 60)

    strategy_dict = strategy_agent.run(user_message, llm, db)

    # Save strategy to database
    strategy = Strategy(
        name=strategy_dict.get("name", "Unnamed Strategy"),
        asset=strategy_dict.get("asset", "AAPL"),
        strategy_type=strategy_dict.get("strategy_type", "momentum"),
        indicator=strategy_dict.get("indicator", "SMA_crossover"),
        params=strategy_dict.get("params", {}),
        entry_rule=strategy_dict.get("entry_rule", ""),
        exit_rule=strategy_dict.get("exit_rule", ""),
        stop_loss_pct=strategy_dict.get("stop_loss_pct", 5.0),
        lookback_months=strategy_dict.get("lookback_months", 12),
        status="created",
    )
    db.add(strategy)
    db.commit()
    strategy_id = strategy.id

    log_agent_action(db, "orchestrator", "strategy_created",
                     f"Strategy {strategy_id}: {strategy.name}", strategy_id)

    # --- Sub-Agent 2: Backtest & Self-Heal ---
    logger.info("=" * 60)
    logger.info("SUB-AGENT 2: Backtest & Self-Heal")
    logger.info("=" * 60)

    backtest_result = backtest_agent.run(strategy_dict, llm, db, strategy_id)

    # Update strategy with any parameter changes from self-healing
    if backtest_result.get("strategy"):
        final_strategy = backtest_result["strategy"]
        strategy.params = final_strategy.get("params", strategy.params)
        strategy.stop_loss_pct = final_strategy.get("stop_loss_pct", strategy.stop_loss_pct)
        strategy.status = "backtested"
        db.commit()

    log_agent_action(db, "orchestrator", "backtest_complete",
                     f"Passed: {backtest_result.get('passed', False)}", strategy_id)

    # --- Sub-Agent 3: Deploy to Paper Trading ---
    logger.info("=" * 60)
    logger.info("SUB-AGENT 3: Deploy to Paper Trading")
    logger.info("=" * 60)

    deploy_result = deploy_agent.run(
        strategy_dict=backtest_result.get("strategy", strategy_dict),
        strategy_id=strategy_id,
        backtest_passed=backtest_result.get("passed", False),
        llm=llm,
        db=db,
    )

    log_agent_action(db, "orchestrator", "complete",
                     f"Pipeline complete for strategy {strategy_id}", strategy_id)

    # --- Assemble final response ---
    return {
        "strategy_id": strategy_id,
        "strategy": {
            "name": strategy.name,
            "asset": strategy.asset,
            "strategy_type": strategy.strategy_type,
            "indicator": strategy.indicator,
            "params": strategy.params,
            "entry_rule": strategy.entry_rule,
            "exit_rule": strategy.exit_rule,
            "stop_loss_pct": strategy.stop_loss_pct,
        },
        "backtest": {
            "passed": backtest_result.get("passed", False),
            "metrics": backtest_result.get("metrics", {}),
            "iterations": backtest_result.get("iterations", []),
            "explanation": backtest_result.get("explanation", ""),
        },
        "deployment": deploy_result,
        "summary": _build_summary(strategy, backtest_result, deploy_result),
    }


def _build_summary(strategy, backtest_result, deploy_result) -> str:
    """Build a human-readable summary of the full pipeline result."""
    metrics = backtest_result.get("metrics", {})
    parts = [
        f"Strategy '{strategy.name}' for {strategy.asset}:",
        f"  - Type: {strategy.strategy_type} ({strategy.indicator})",
        f"  - Entry: {strategy.entry_rule}",
        f"  - Exit: {strategy.exit_rule}",
        f"  - Stop loss: {strategy.stop_loss_pct}%",
        "",
        "Backtest Results:",
        f"  - Total return: {metrics.get('total_return', 'N/A')}%",
        f"  - Sharpe ratio: {metrics.get('sharpe_ratio', 'N/A')}",
        f"  - Max drawdown: {metrics.get('max_drawdown', 'N/A')}%",
        f"  - Win rate: {metrics.get('win_rate', 'N/A')}%",
        f"  - Trades: {metrics.get('num_trades', 'N/A')}",
        f"  - Status: {'PASSED' if backtest_result.get('passed') else 'DID NOT PASS'}",
        f"  - Self-heal iterations: {len(backtest_result.get('iterations', []))}",
        "",
        f"Deployment: {deploy_result.get('status', 'unknown')}",
        f"  {deploy_result.get('message', '')}",
    ]
    return "\n".join(parts)
