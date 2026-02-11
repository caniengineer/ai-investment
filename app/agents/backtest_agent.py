"""Sub-Agent 2 — Backtest & Self-Heal.

Takes the JSON strategy, runs a backtest, evaluates results,
and self-heals up to 3 times if thresholds aren't met.
"""

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.llm import LLMProvider
from app.core.tools import fetch_market_data, execute_backtest, evaluate_results
from app.core.backtest import run_backtest
from app.db.models import BacktestResult
from app.observability.logger import log_llm_call, log_agent_action

logger = logging.getLogger("alphaagent.backtest_agent")

MAX_HEAL_ATTEMPTS = 3

EVAL_PROMPT = Path("prompts/backtest_eval.txt").read_text() if Path("prompts/backtest_eval.txt").exists() else ""
HEAL_PROMPT = Path("prompts/self_heal.txt").read_text() if Path("prompts/self_heal.txt").exists() else ""


def run(strategy: dict, llm: LLMProvider, db: Session, strategy_id: str) -> dict:
    """Run backtest and self-heal loop.

    Returns dict with final strategy, metrics, iterations log, and pass/fail status.
    """
    log_agent_action(db, "backtest_agent", "start",
                     f"Backtesting {strategy.get('name', 'unknown')}", strategy_id)

    # Fetch market data
    asset = strategy.get("asset", "AAPL")
    lookback = strategy.get("lookback_months", 12)
    market_data = fetch_market_data(asset, lookback)
    prices = market_data.get("prices", [])

    if not prices:
        log_agent_action(db, "backtest_agent", "error", "No price data available", strategy_id)
        return {
            "strategy": strategy,
            "metrics": {},
            "passed": False,
            "iterations": [],
            "explanation": "No price data available for backtesting",
        }

    iterations = []
    current_strategy = strategy.copy()
    best_result = None

    for attempt in range(1, MAX_HEAL_ATTEMPTS + 1):
        log_agent_action(db, "backtest_agent", "backtest_iteration",
                         f"Iteration {attempt}/{MAX_HEAL_ATTEMPTS}", strategy_id)

        # Run backtest
        metrics = run_backtest(prices, current_strategy)
        metrics_summary = {k: v for k, v in metrics.items() if k != "trades"}

        # Evaluate
        evaluation = evaluate_results(metrics_summary)

        # Save to DB
        bt_result = BacktestResult(
            strategy_id=strategy_id,
            iteration=attempt,
            total_return=metrics_summary.get("total_return", 0),
            sharpe_ratio=metrics_summary.get("sharpe_ratio", 0),
            max_drawdown=metrics_summary.get("max_drawdown", 0),
            win_rate=metrics_summary.get("win_rate", 0),
            num_trades=metrics_summary.get("num_trades", 0),
            passed=evaluation["passed"],
            changes_made=current_strategy.get("adjustments", "Initial parameters"),
            metrics=metrics_summary,
        )
        db.add(bt_result)
        db.commit()

        iteration_log = {
            "attempt": attempt,
            "strategy_params": current_strategy.get("params", {}),
            "metrics": metrics_summary,
            "passed": evaluation["passed"],
            "explanation": evaluation["explanation"],
        }
        iterations.append(iteration_log)

        logger.info(
            "Iteration %d: return=%.2f%% sharpe=%.2f drawdown=%.2f%% win_rate=%.2f%% → %s",
            attempt,
            metrics_summary.get("total_return", 0),
            metrics_summary.get("sharpe_ratio", 0),
            metrics_summary.get("max_drawdown", 0),
            metrics_summary.get("win_rate", 0),
            "PASS" if evaluation["passed"] else "FAIL",
        )

        # Track best result
        if best_result is None or metrics_summary.get("sharpe_ratio", 0) > best_result["metrics"].get("sharpe_ratio", 0):
            best_result = {
                "strategy": current_strategy.copy(),
                "metrics": metrics_summary,
                "passed": evaluation["passed"],
            }

        if evaluation["passed"]:
            log_agent_action(db, "backtest_agent", "passed",
                             f"Strategy passed on iteration {attempt}", strategy_id)
            return {
                "strategy": current_strategy,
                "metrics": metrics_summary,
                "passed": True,
                "iterations": iterations,
                "explanation": f"Strategy passed all thresholds on iteration {attempt}.",
            }

        # Self-heal: ask LLM to diagnose and fix
        if attempt < MAX_HEAL_ATTEMPTS:
            log_agent_action(db, "backtest_agent", "self_heal",
                             f"Attempting self-heal (iteration {attempt})", strategy_id)
            current_strategy = _self_heal(current_strategy, metrics_summary, evaluation, llm, db)

    # Return best result after all attempts
    log_agent_action(db, "backtest_agent", "complete",
                     f"Max iterations reached. Best sharpe: {best_result['metrics'].get('sharpe_ratio', 0)}",
                     strategy_id)
    return {
        "strategy": best_result["strategy"],
        "metrics": best_result["metrics"],
        "passed": best_result["passed"],
        "iterations": iterations,
        "explanation": f"Best result after {MAX_HEAL_ATTEMPTS} iterations. "
                       f"Sharpe: {best_result['metrics'].get('sharpe_ratio', 0)}",
    }


def _self_heal(strategy: dict, metrics: dict, evaluation: dict, llm: LLMProvider, db: Session) -> dict:
    """Ask the LLM to diagnose and fix a failing strategy."""
    prompt = f"""The following strategy failed its backtest evaluation.

Strategy:
{json.dumps(strategy, indent=2)}

Backtest metrics:
{json.dumps(metrics, indent=2)}

Evaluation:
{json.dumps(evaluation, indent=2)}

Diagnose why it failed and produce an updated strategy with adjusted parameters.
Return ONLY the updated strategy as JSON."""

    messages = [{"role": "user", "content": prompt}]
    response = llm.complete(messages, system=HEAL_PROMPT)
    log_llm_call(db, response, tool_called="self_heal")

    # Parse updated strategy
    try:
        start = response.content.find("{")
        end = response.content.rfind("}") + 1
        if start >= 0 and end > start:
            updated = json.loads(response.content[start:end])
            # Merge with original to preserve required fields
            for key in ("name", "asset", "strategy_type", "indicator", "entry_rule", "exit_rule"):
                if key not in updated:
                    updated[key] = strategy.get(key)
            return updated
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Could not parse self-heal response: %s", e)

    # Fallback: make a simple adjustment
    fallback = strategy.copy()
    params = dict(fallback.get("params", {}))
    if "short_window" in params:
        params["short_window"] = min(params["short_window"] + 5, 30)
    if "long_window" in params:
        params["long_window"] = min(params["long_window"] + 10, 100)
    if "rsi_oversold" in params:
        params["rsi_oversold"] = min(params["rsi_oversold"] + 5, 40)
    fallback["params"] = params
    fallback["stop_loss_pct"] = min(fallback.get("stop_loss_pct", 5) + 1, 10)
    fallback["adjustments"] = "Fallback: widened windows / loosened stop loss"
    return fallback
