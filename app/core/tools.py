"""Function-calling tools for the LLM agents.

Each tool is a plain Python function. Tool schemas are defined for the LLM
to choose which tool to call. The agent picks the tool — we don't hard-code the flow.
"""

import json
import logging
from datetime import datetime, timedelta

import yfinance as yf
from sqlalchemy.orm import Session

from app.core import rag
from app.core.backtest import run_backtest
from app.core.paper_trade import start_paper_trade
from app.db.models import Strategy, BacktestResult

logger = logging.getLogger("alphaagent.tools")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def fetch_market_data(ticker: str, period_months: int = 12) -> dict:
    """Fetch historical price data for a ticker from yfinance.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT)
        period_months: Number of months of history to fetch

    Returns:
        Dictionary with dates and closing prices
    """
    logger.info("Fetching market data for %s (%d months)", ticker, period_months)
    try:
        end = datetime.now()
        start = end - timedelta(days=period_months * 30)
        data = yf.download(ticker, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False)
        if data.empty:
            return {"error": f"No data found for {ticker}", "prices": [], "dates": []}

        prices = data["Close"].values.flatten().tolist()
        dates = [d.strftime("%Y-%m-%d") for d in data.index]
        return {
            "ticker": ticker,
            "period_months": period_months,
            "num_points": len(prices),
            "prices": prices,
            "dates": dates,
            "latest_price": prices[-1] if prices else None,
        }
    except Exception as e:
        logger.error("yfinance error for %s: %s", ticker, e)
        return {"error": str(e), "prices": [], "dates": []}


def search_knowledge_base(query: str, db: Session) -> list[dict]:
    """Search the RAG knowledge base for relevant strategy patterns.

    Args:
        query: Natural language search query

    Returns:
        List of relevant knowledge chunks with similarity scores
    """
    logger.info("Searching knowledge base: %s", query)
    results = rag.search(db, query, top_k=3)
    return results


def execute_backtest(strategy_dict: dict, prices: list[float]) -> dict:
    """Run a backtest on historical price data using the given strategy.

    Args:
        strategy_dict: Strategy definition with indicator, params, stop_loss_pct
        prices: List of historical closing prices

    Returns:
        Backtest metrics (total_return, sharpe_ratio, max_drawdown, win_rate, num_trades)
    """
    logger.info("Running backtest for %s strategy", strategy_dict.get("indicator", "unknown"))
    metrics = run_backtest(prices, strategy_dict)
    # Remove the raw trades list for the LLM response (too verbose)
    summary = {k: v for k, v in metrics.items() if k != "trades"}
    return summary


def evaluate_results(metrics: dict) -> dict:
    """Evaluate backtest results against pass/fail thresholds.

    Thresholds: Sharpe > 0.5, max_drawdown < 25%, win_rate > 40%

    Args:
        metrics: Backtest metrics dict

    Returns:
        Evaluation with passed flag and explanation
    """
    sharpe = metrics.get("sharpe_ratio", 0)
    drawdown = metrics.get("max_drawdown", 100)
    win_rate = metrics.get("win_rate", 0)

    issues = []
    if sharpe <= 0.5:
        issues.append(f"Sharpe ratio {sharpe} is below threshold of 0.5")
    if drawdown >= 25:
        issues.append(f"Max drawdown {drawdown}% exceeds threshold of 25%")
    if win_rate <= 40:
        issues.append(f"Win rate {win_rate}% is below threshold of 40%")

    passed = len(issues) == 0
    return {
        "passed": passed,
        "sharpe_ok": sharpe > 0.5,
        "drawdown_ok": drawdown < 25,
        "win_rate_ok": win_rate > 40,
        "issues": issues,
        "explanation": "All thresholds passed." if passed else "Failed: " + "; ".join(issues),
    }


def deploy_strategy(strategy_id: str) -> dict:
    """Deploy a strategy to paper trading.

    Args:
        strategy_id: The ID of the strategy to deploy

    Returns:
        Paper trade details including trade_id and status
    """
    logger.info("Deploying strategy %s to paper trading", strategy_id)
    trade_id = start_paper_trade(strategy_id)
    return {
        "trade_id": trade_id,
        "strategy_id": strategy_id,
        "status": "active",
        "message": f"Strategy {strategy_id} is now paper trading",
    }


# ---------------------------------------------------------------------------
# Tool schemas for LLM function calling
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "name": "fetch_market_data",
        "description": "Fetch historical price data for a stock ticker from yfinance. Returns dates and closing prices.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol, e.g. AAPL, MSFT, GOOGL, SPY",
                },
                "period_months": {
                    "type": "integer",
                    "description": "Number of months of historical data to fetch (default 12)",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": "Search the RAG knowledge base for relevant strategy patterns, indicators, and risk management advice.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query about trading strategies or indicators",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "run_backtest",
        "description": "Run a backtest on historical price data. Returns total return, Sharpe ratio, max drawdown, win rate.",
        "parameters": {
            "type": "object",
            "properties": {
                "strategy": {
                    "type": "object",
                    "description": "Strategy definition with fields: indicator, params, stop_loss_pct",
                },
                "prices": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "List of historical closing prices",
                },
            },
            "required": ["strategy", "prices"],
        },
    },
    {
        "name": "evaluate_results",
        "description": "Evaluate backtest results against pass/fail thresholds (Sharpe > 0.5, drawdown < 25%, win rate > 40%).",
        "parameters": {
            "type": "object",
            "properties": {
                "metrics": {
                    "type": "object",
                    "description": "Backtest metrics with sharpe_ratio, max_drawdown, win_rate fields",
                },
            },
            "required": ["metrics"],
        },
    },
    {
        "name": "deploy_strategy",
        "description": "Deploy an approved strategy to simulated paper trading. Starts monitoring prices and executing trades.",
        "parameters": {
            "type": "object",
            "properties": {
                "strategy_id": {
                    "type": "string",
                    "description": "The ID of the strategy to deploy",
                },
            },
            "required": ["strategy_id"],
        },
    },
]


def execute_tool(tool_name: str, arguments: dict, db: Session) -> dict:
    """Execute a tool by name with the given arguments. Central dispatch."""
    if tool_name == "fetch_market_data":
        return fetch_market_data(
            ticker=arguments["ticker"],
            period_months=arguments.get("period_months", 12),
        )
    elif tool_name == "search_knowledge_base":
        return search_knowledge_base(query=arguments["query"], db=db)
    elif tool_name == "run_backtest":
        return execute_backtest(
            strategy_dict=arguments["strategy"],
            prices=arguments["prices"],
        )
    elif tool_name == "evaluate_results":
        return evaluate_results(metrics=arguments["metrics"])
    elif tool_name == "deploy_strategy":
        return deploy_strategy(strategy_id=arguments["strategy_id"])
    else:
        return {"error": f"Unknown tool: {tool_name}"}
