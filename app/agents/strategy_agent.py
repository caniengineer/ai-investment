"""Sub-Agent 1 — Strategy Generator.

Takes the user's natural language input, uses RAG and market data tools
via function calling, and outputs a JSON strategy.
"""

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.llm import LLMProvider, LLMResponse
from app.core.tools import TOOL_SCHEMAS, execute_tool
from app.core.playbook import Playbook
from app.observability.logger import log_llm_call, log_agent_action

logger = logging.getLogger("alphaagent.strategy_agent")

# Only expose the tools this agent needs
STRATEGY_TOOLS = [t for t in TOOL_SCHEMAS if t["name"] in ("fetch_market_data", "search_knowledge_base")]

SYSTEM_PROMPT = Path("prompts/strategy_gen.txt").read_text() if Path("prompts/strategy_gen.txt").exists() else ""


def run(user_message: str, llm: LLMProvider, db: Session) -> dict:
    """Run the strategy generation agent.

    Uses function calling to let the LLM decide which tools to invoke.
    Injects playbook insights into the system prompt for context-aware generation.
    Returns the generated strategy as a dict.
    """
    log_agent_action(db, "strategy_agent", "start", f"User request: {user_message}")

    # Build system prompt with playbook context
    playbook = Playbook(db)
    playbook_context = playbook.render(sections=["STRATEGIES & INSIGHTS", "PARAMETER GUIDANCE"])
    system = SYSTEM_PROMPT
    if playbook_context:
        system = f"{SYSTEM_PROMPT}\n\n{playbook_context}"

    messages = [{"role": "user", "content": user_message}]

    # Allow up to 5 tool-calling rounds
    for round_num in range(5):
        response: LLMResponse = llm.function_call(messages, STRATEGY_TOOLS, system=system)
        log_llm_call(db, response, tool_called=response.tool_calls[0]["name"] if response.tool_calls else None)

        if not response.tool_calls:
            # No more tool calls — the LLM is done and should have returned the strategy
            break

        # Process each tool call
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["arguments"]
            log_agent_action(db, "strategy_agent", "tool_call", f"{tool_name}({json.dumps(tool_args)[:200]})")

            result = execute_tool(tool_name, tool_args, db)

            # Feed the tool result back to the LLM (Anthropic format)
            messages.append({"role": "assistant", "content": [
                {"type": "tool_use", "id": tc["id"], "name": tool_name, "input": tool_args}
            ]})
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tc["id"], "content": json.dumps(result, default=str)[:3000]}
            ]})

    # Parse the strategy JSON from the final response
    strategy = _extract_strategy(response.content)
    log_agent_action(
        db, "strategy_agent", "complete",
        f"Generated strategy: {strategy.get('name', 'unknown')} for {strategy.get('asset', 'unknown')}"
    )
    return strategy


def _extract_strategy(text: str) -> dict:
    """Extract JSON strategy from LLM response text."""
    # Try to find JSON in the response
    try:
        # Look for JSON block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    # Fallback: return a default strategy structure
    logger.warning("Could not parse strategy JSON from LLM response, using fallback")
    return {
        "name": "SMA Crossover Strategy",
        "asset": "AAPL",
        "strategy_type": "momentum",
        "indicator": "SMA_crossover",
        "params": {"short_window": 20, "long_window": 50},
        "entry_rule": "Buy when 20-day SMA crosses above 50-day SMA",
        "exit_rule": "Sell when 20-day SMA crosses below 50-day SMA",
        "stop_loss_pct": 5.0,
        "lookback_months": 12,
    }
