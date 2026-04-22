from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ...core.database import get_db
from ...models.trade import Trade
from ...models.bot import Bot
from ...models.historical_data import HistoricalData

router = APIRouter()

@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """
    Calcula as métricas reais do dashboard baseadas nos trades executados.
    """
    # 1. PnL Total e Número de Trades
    trades_stats = db.query(
        func.sum(Trade.profit).label("total_pnl"),
        func.count(Trade.id).label("total_trades")
    ).all()[0]
    
    # 2. Win Rate
    winning_trades = db.query(func.count(Trade.id)).filter(Trade.profit > 0).scalar() or 0
    total_trades = trades_stats.total_trades or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # 3. Bots Ativos
    active_bots = db.query(func.count(Bot.id)).filter(Bot.status == "active").scalar() or 0
    
    # 4. Total de Velas no Banco
    total_candles = db.query(func.count(HistoricalData.id)).scalar() or 0

    return {
        "total_pnl": float(trades_stats.total_pnl or 0),
        "win_rate": round(win_rate, 2),
        "max_drawdown": 0.0, # TODO: Implementar lógica de drawdown histórico
        "active_bots": active_bots,
        "total_candles": total_candles,
        "total_trades": total_trades
    }
