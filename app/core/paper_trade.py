"""Simulated paper trading engine.

Monitors a strategy in real-time using latest yfinance prices.
Tracks open positions, simulated PnL, and order history.
"""

import datetime
import logging
import threading
import time
import os

import yfinance as yf
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import PaperTrade, Strategy
from app.core.backtest import compute_sma, compute_rsi

logger = logging.getLogger("alphaagent.paper_trade")

# Keep track of running paper trade threads
_active_trades: dict[str, threading.Event] = {}


def get_latest_price(ticker: str) -> float | None:
    """Get the latest price for a ticker from yfinance."""
    try:
        data = yf.download(ticker, period="5d", progress=False)
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except Exception as e:
        logger.error("Failed to fetch price for %s: %s", ticker, e)
        return None


def get_recent_prices(ticker: str, days: int = 60) -> list[float]:
    """Get recent closing prices for signal generation."""
    try:
        data = yf.download(ticker, period=f"{days}d", progress=False)
        if data.empty:
            return []
        return data["Close"].values.flatten().tolist()
    except Exception as e:
        logger.error("Failed to fetch recent prices for %s: %s", ticker, e)
        return []


def check_signal(prices: list[float], strategy_params: dict) -> str:
    """Check current signal based on strategy indicator. Returns 'buy', 'sell', or 'hold'."""
    indicator = strategy_params.get("indicator", "SMA_crossover")
    params = strategy_params.get("params", {})

    if len(prices) < 2:
        return "hold"

    if indicator == "SMA_crossover":
        short_w = params.get("short_window", 20)
        long_w = params.get("long_window", 50)
        if len(prices) < long_w + 1:
            return "hold"
        short_sma = compute_sma(prices, short_w)
        long_sma = compute_sma(prices, long_w)
        if short_sma[-1] is not None and long_sma[-1] is not None:
            if short_sma[-2] is not None and long_sma[-2] is not None:
                if short_sma[-1] > long_sma[-1] and short_sma[-2] <= long_sma[-2]:
                    return "buy"
                elif short_sma[-1] < long_sma[-1] and short_sma[-2] >= long_sma[-2]:
                    return "sell"

    elif indicator == "RSI":
        period = params.get("rsi_period", 14)
        oversold = params.get("rsi_oversold", 30)
        overbought = params.get("rsi_overbought", 70)
        rsi_values = compute_rsi(prices, period)
        if rsi_values[-1] is not None:
            if rsi_values[-1] <= oversold:
                return "buy"
            elif rsi_values[-1] >= overbought:
                return "sell"

    return "hold"


def start_paper_trade(strategy_id: str) -> str:
    """Start paper trading for a strategy. Returns the paper trade ID."""
    db = SessionLocal()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        trade = PaperTrade(
            strategy_id=strategy_id,
            status="active",
            position="flat",
            pnl=0.0,
            order_history=[],
        )
        db.add(trade)
        db.commit()
        trade_id = trade.id

        # Start monitoring in background thread
        stop_event = threading.Event()
        _active_trades[trade_id] = stop_event

        thread = threading.Thread(
            target=_monitor_loop,
            args=(trade_id, strategy_id, stop_event),
            daemon=True,
        )
        thread.start()
        logger.info("Started paper trade %s for strategy %s", trade_id, strategy_id)
        return trade_id
    finally:
        db.close()


def _monitor_loop(trade_id: str, strategy_id: str, stop_event: threading.Event):
    """Background loop that checks prices and executes paper trades."""
    interval = int(os.getenv("PAPER_TRADE_INTERVAL", "30"))

    while not stop_event.is_set():
        db = SessionLocal()
        try:
            trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()
            strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
            if not trade or not strategy or trade.status != "active":
                break

            asset = strategy.asset
            current_price = get_latest_price(asset)
            if current_price is None:
                logger.warning("Could not fetch price for %s, skipping check", asset)
                time.sleep(interval)
                continue

            trade.current_price = current_price
            trade.last_check = datetime.datetime.utcnow()

            # Get recent prices for signal generation
            prices = get_recent_prices(asset)
            strategy_params = {
                "indicator": strategy.indicator,
                "params": strategy.params,
            }
            signal = check_signal(prices, strategy_params)

            order_history = list(trade.order_history or [])

            if signal == "buy" and trade.position == "flat":
                trade.position = "long"
                trade.entry_price = current_price
                order_history.append({
                    "action": "buy",
                    "price": current_price,
                    "time": datetime.datetime.utcnow().isoformat(),
                })
                logger.info("Paper trade %s: BUY %s @ %.2f", trade_id, asset, current_price)

            elif signal == "sell" and trade.position == "long":
                pnl = (current_price - trade.entry_price) / trade.entry_price * 100
                trade.pnl = round(trade.pnl + pnl, 2)
                trade.position = "flat"
                order_history.append({
                    "action": "sell",
                    "price": current_price,
                    "time": datetime.datetime.utcnow().isoformat(),
                    "pnl": round(pnl, 2),
                })
                logger.info(
                    "Paper trade %s: SELL %s @ %.2f (PnL: %.2f%%)",
                    trade_id, asset, current_price, pnl,
                )

            # Check stop loss
            if trade.position == "long" and trade.entry_price:
                stop_loss_pct = strategy.stop_loss_pct / 100.0
                pct_change = (current_price - trade.entry_price) / trade.entry_price
                if pct_change <= -stop_loss_pct:
                    pnl = pct_change * 100
                    trade.pnl = round(trade.pnl + pnl, 2)
                    trade.position = "flat"
                    order_history.append({
                        "action": "stop_loss",
                        "price": current_price,
                        "time": datetime.datetime.utcnow().isoformat(),
                        "pnl": round(pnl, 2),
                    })
                    logger.warning(
                        "Paper trade %s: STOP LOSS %s @ %.2f (PnL: %.2f%%)",
                        trade_id, asset, current_price, pnl,
                    )

            trade.order_history = order_history
            db.commit()

        except Exception as e:
            logger.error("Paper trade monitor error: %s", e)
        finally:
            db.close()

        stop_event.wait(timeout=interval)


def stop_paper_trade(trade_id: str):
    """Stop a running paper trade."""
    if trade_id in _active_trades:
        _active_trades[trade_id].set()
        del _active_trades[trade_id]

    db = SessionLocal()
    try:
        trade = db.query(PaperTrade).filter(PaperTrade.id == trade_id).first()
        if trade:
            trade.status = "stopped"
            db.commit()
        logger.info("Stopped paper trade %s", trade_id)
    finally:
        db.close()
