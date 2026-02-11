"""Strategy endpoints — list, detail, and live trading status."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Strategy, BacktestResult, PaperTrade, AgentLog

router = APIRouter()


@router.get("/strategies")
def list_strategies(db: Session = Depends(get_db)):
    """List all generated strategies."""
    strategies = db.query(Strategy).order_by(Strategy.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "asset": s.asset,
            "strategy_type": s.strategy_type,
            "indicator": s.indicator,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in strategies
    ]


@router.get("/strategies/{strategy_id}")
def get_strategy(strategy_id: str, db: Session = Depends(get_db)):
    """Get strategy detail including backtest history and self-heal log."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    backtest_results = (
        db.query(BacktestResult)
        .filter(BacktestResult.strategy_id == strategy_id)
        .order_by(BacktestResult.iteration)
        .all()
    )

    agent_logs = (
        db.query(AgentLog)
        .filter(AgentLog.strategy_id == strategy_id)
        .order_by(AgentLog.created_at)
        .all()
    )

    return {
        "id": strategy.id,
        "name": strategy.name,
        "asset": strategy.asset,
        "strategy_type": strategy.strategy_type,
        "indicator": strategy.indicator,
        "params": strategy.params,
        "entry_rule": strategy.entry_rule,
        "exit_rule": strategy.exit_rule,
        "stop_loss_pct": strategy.stop_loss_pct,
        "lookback_months": strategy.lookback_months,
        "status": strategy.status,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
        "backtest_history": [
            {
                "iteration": bt.iteration,
                "total_return": bt.total_return,
                "sharpe_ratio": bt.sharpe_ratio,
                "max_drawdown": bt.max_drawdown,
                "win_rate": bt.win_rate,
                "num_trades": bt.num_trades,
                "passed": bt.passed,
                "changes_made": bt.changes_made,
            }
            for bt in backtest_results
        ],
        "agent_log": [
            {
                "agent": log.agent,
                "action": log.action,
                "detail": log.detail,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in agent_logs
        ],
    }


@router.get("/strategies/{strategy_id}/live")
def get_live_status(strategy_id: str, db: Session = Depends(get_db)):
    """Get paper trading status for a strategy."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    trade = (
        db.query(PaperTrade)
        .filter(PaperTrade.strategy_id == strategy_id)
        .order_by(PaperTrade.created_at.desc())
        .first()
    )

    if not trade:
        return {
            "strategy_id": strategy_id,
            "status": "not_deployed",
            "message": "No paper trade found for this strategy",
        }

    return {
        "strategy_id": strategy_id,
        "trade_id": trade.id,
        "status": trade.status,
        "position": trade.position,
        "entry_price": trade.entry_price,
        "current_price": trade.current_price,
        "pnl": trade.pnl,
        "order_history": trade.order_history,
        "last_check": trade.last_check.isoformat() if trade.last_check else None,
        "created_at": trade.created_at.isoformat() if trade.created_at else None,
    }
