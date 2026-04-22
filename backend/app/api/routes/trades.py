"""
API Routes for Trade Management
CorreA?A?o: ImplementaA?A?o completa das rotas de trades
Prioridade: ALTA
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from ...core.database import get_db
from ...models.trade import Trade
from ...models.bot import Bot
from ...services.risk_bot import RiskBot
from ...services.risk_global import RiskGlobal
from ...services.bot_manager import BotManager

router = APIRouter(tags=["trades"])

# ========== SCHEMAS ==========
from pydantic import BaseModel
from typing import Optional

class TradeCreate(BaseModel):
    bot_id: int
    direction: str  # buy, sell
    volume: float
    symbol: str
    entry_price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: Optional[str] = None

class TradeClose(BaseModel):
    exit_price: float
    ticket: Optional[int] = None

class TradeResponse(BaseModel):
    id: int
    bot_id: int
    ticket: Optional[int]
    direction: str
    volume: float
    symbol: str
    entry_price: Optional[float]
    exit_price: Optional[float]
    profit: Optional[float]
    open_time: datetime
    close_time: Optional[datetime]
    pnl: float
    sl: Optional[float]
    tp: Optional[float]
    commission: Optional[float]
    swap: Optional[float]
    magic_number: Optional[int]
    comment: Optional[str]
    status: str

    class Config:
        from_attributes = True

class TradeStats(BaseModel):
    total_trades: int
    open_trades: int
    closed_trades: int
    total_pnl: float
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float

# ========== ROTAS ==========

@router.get("/", response_model=List[TradeResponse])
async def list_trades(
    bot_id: Optional[int] = Query(None, description="Filter by bot ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    status: Optional[str] = Query(None, description="Filter by status: open, closed, all"),
    direction: Optional[str] = Query(None, description="Filter by direction: buy, sell"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Listar trades com filtros opcionais
    CorreA?A?o: ImplementaA?A?o completa da listagem
    """
    query = db.query(Trade)
    
    if bot_id:
        query = query.filter(Trade.bot_id == bot_id)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    if direction:
        query = query.filter(Trade.direction == direction)
    if status == "open":
        query = query.filter(Trade.close_time.is_(None))
    elif status == "closed":
        query = query.filter(Trade.close_time.isnot(None))
    
    # Ordenar por mais recente
    query = query.order_by(desc(Trade.open_time))
    
    # PaginaA?A?o
    trades = query.offset(offset).limit(limit).all()
    
    return trades


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade_detail(trade_id: int, db: Session = Depends(get_db)):
    """
    Obter detalhes de um trade especA?fico
    CorreA?A?o: ImplementaA?A?o do detalhamento
    """
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("/", response_model=TradeResponse)
async def create_trade(
    trade_data: TradeCreate,
    db: Session = Depends(get_db)
):
    """
    Criar trade manualmente
    CorreA?A?o: ImplementaA?A?o da criaA?A?o com validaA?A?o de risco
    """
    # Buscar bot
    bot = db.query(Bot).filter(Bot.id == trade_data.bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Verificar se bot estA? ativo
    if not bot.active:
        raise HTTPException(status_code=400, detail="Bot is not active")
    
    # ValidaA?A?o de risco por bot
    risk_bot = RiskBot(bot)
    allowed, message = risk_bot.validate_trade(
        direction=trade_data.direction,
        volume=trade_data.volume
    )
    if not allowed:
        raise HTTPException(status_code=400, detail=f"Risk check failed: {message}")
    
    # ValidaA?A?o de risco global
    risk_global = RiskGlobal()
    allowed, message = risk_global.validate_trade(bot, trade_data.direction, trade_data.volume)
    if not allowed:
        raise HTTPException(status_code=400, detail=f"Global risk check failed: {message}")
    
    # Criar trade
    trade = Trade(
        bot_id=trade_data.bot_id,
        direction=trade_data.direction,
        volume=trade_data.volume,
        symbol=trade_data.symbol or bot.symbol,
        entry_price=trade_data.entry_price,
        sl=trade_data.sl,
        tp=trade_data.tp,
        comment=trade_data.comment,
        magic_number=bot.magic_number,
        open_time=datetime.utcnow(),
        ticket=None,  # SerA? atualizado pelo MT5
    )
    
    db.add(trade)
    db.commit()
    db.refresh(trade)
    
    return trade


@router.post("/{trade_id}/close", response_model=TradeResponse)
async def close_trade(
    trade_id: int,
    close_data: TradeClose,
    db: Session = Depends(get_db)
):
    """
    Fechar um trade
    CorreA?A?o: ImplementaA?A?o do fechamento com cA?lculo de PnL
    """
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.close_time:
        raise HTTPException(status_code=400, detail="Trade already closed")
    
    # Calcular PnL
    exit_price = close_data.exit_price
    entry_price = trade.entry_price or 0
    
    if trade.direction == "buy":
        pnl = (exit_price - entry_price) * trade.volume
    else:  # sell
        pnl = (entry_price - exit_price) * trade.volume
    
    # Adicionar comissA?o e swap (valores padrA?o)
    commission = trade.volume * 0.1  # SimulaA?A?o
    swap = 0.0
    
    # Atualizar trade
    trade.close_price = exit_price
    trade.exit_price = exit_price
    trade.close_time = datetime.utcnow()
    trade.pnl = pnl
    trade.profit = pnl - commission + swap
    trade.commission = commission
    trade.swap = swap
    
    if close_data.ticket:
        trade.ticket = close_data.ticket
    
    db.commit()
    db.refresh(trade)
    
    return trade


@router.delete("/{trade_id}")
async def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """
    Deletar trade (apenas se nA?o estiver executando)
    CorreA?A?o: ImplementaA?A?o da exclusA?o
    """
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if not trade.close_time:
        raise HTTPException(status_code=400, detail="Cannot delete open trade. Close it first.")
    
    db.delete(trade)
    db.commit()
    
    return {"message": "Trade deleted successfully"}


@router.get("/history/all")
async def get_trade_history(
    bot_id: Optional[int] = Query(None),
    symbol: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    HistA?rico de trades
    CorreA?A?o: ImplementaA?A?o do histA?rico com filtros
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Trade).filter(Trade.open_time >= since)
    
    if bot_id:
        query = query.filter(Trade.bot_id == bot_id)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    
    trades = query.order_by(desc(Trade.open_time)).all()
    
    return {
        "total": len(trades),
        "since": since.isoformat(),
        "trades": trades
    }


@router.get("/stats/summary")
async def get_trade_statistics(
    bot_id: Optional[int] = Query(None),
    symbol: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    EstatA?sticas de trades
    CorreA?A?o: ImplementaA?A?o das mA?tricas calculadas
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Trade).filter(Trade.open_time >= since)
    
    if bot_id:
        query = query.filter(Trade.bot_id == bot_id)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    
    trades = query.all()
    
    total_trades = len(trades)
    open_trades = len([t for t in trades if t.close_time is None])
    closed_trades = total_trades - open_trades
    
    # PnL
    total_pnl = sum(t.pnl or 0 for t in trades)
    
    # Win rate
    winning_trades = [t for t in trades if t.close_time and (t.pnl or 0) > 0]
    losing_trades = [t for t in trades if t.close_time and (t.pnl or 0) <= 0]
    
    win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades > 0 else 0
    
    # MA?dias
    avg_profit = sum(t.pnl or 0 for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t.pnl or 0 for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    # Profit factor
    gross_profit = sum(t.pnl or 0 for t in winning_trades)
    gross_loss = abs(sum(t.pnl or 0 for t in losing_trades))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
    
    # Max drawdown (simplificado)
    pnl_values = [t.pnl or 0 for t in trades if t.close_time]
    max_drawdown = 0
    peak = 0
    cumulative = 0
    for pnl in pnl_values:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # Sharpe ratio (simplificado - assumindo retorno diA?rio)
    if len(pnl_values) > 1:
        import statistics
        try:
            avg_return = statistics.mean(pnl_values)
            std_return = statistics.stdev(pnl_values)
            sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
        except statistics.StatisticsError:
            sharpe_ratio = 0
    else:
        sharpe_ratio = 0
    
    return TradeStats(
        total_trades=total_trades,
        open_trades=open_trades,
        closed_trades=closed_trades,
        total_pnl=total_pnl,
        win_rate=round(win_rate, 2),
        avg_profit=round(avg_profit, 2),
        avg_loss=round(avg_loss, 2),
        profit_factor=round(profit_factor, 2),
        max_drawdown=round(max_drawdown, 2),
        sharpe_ratio=round(sharpe_ratio, 2)
    )


@router.get("/by-bot/{bot_id}", response_model=List[TradeResponse])
async def get_trades_by_bot(
    bot_id: int,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Listar trades de um bot especA?fico
    CorreA?A?o: Endpoint dedicado para trades por bot
    """
    query = db.query(Trade).filter(Trade.bot_id == bot_id)
    
    if status == "open":
        query = query.filter(Trade.close_time.is_(None))
    elif status == "closed":
        query = query.filter(Trade.close_time.isnot(None))
    
    trades = query.order_by(desc(Trade.open_time)).all()
    return trades


@router.get("/open/all", response_model=List[TradeResponse])
async def get_open_trades(
    bot_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Listar todos os trades abertos
    CorreA?A?o: Endpoint para trades abertos
    """
    query = db.query(Trade).filter(Trade.close_time.is_(None))
    
    if bot_id:
        query = query.filter(Trade.bot_id == bot_id)
    
    trades = query.all()
    return trades
