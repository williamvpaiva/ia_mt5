from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from ..core.database import Base
from datetime import datetime

class Backtest(Base):
    """
    SessA?o de Backtest com mA?tricas agregadas e configuraA?A?es.
    """
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"))
    symbol = Column(String)
    timeframe = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    # ParA?metros da SimulaA?A?o
    initial_capital = Column(Float)
    final_capital = Column(Float)
    total_return_pct = Column(Float)
    
    # MA?tricas de Performance (Quandt)
    cagr = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    calmar_ratio = Column(Float)
    max_drawdown = Column(Float)
    recovery_factor = Column(Float)
    profit_factor = Column(Float)
    win_rate = Column(Float)
    payoff = Column(Float)
    
    # AnA?lise de Risco
    var_95 = Column(Float) # Value at Risk
    volatility_annual = Column(Float)
    
    # Dados Brutos para GrA?ficos
    equity_curve = Column(JSON) # Lista de [timestamp, equity]
    drawdown_curve = Column(JSON)
    metrics_json = Column(JSON) # Breakdown temporal, heatmap data, etc.
    
    timestamp = Column(DateTime, default=datetime.now)

class BacktestTrade(Base):
    """
    Registros individuais de cada trade simulado no backtest.
    """
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id", ondelete="CASCADE"), index=True)
    symbol = Column(String)
    type = Column(String) # BUY/SELL
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    entry_price = Column(Float)
    exit_price = Column(Float)
    lots = Column(Float)
    profit = Column(Float)
    duration_minutes = Column(Float)
    result_pct = Column(Float)
    
    # AtribuiA?A?o
    entry_reason = Column(String, nullable=True)
    exit_reason = Column(String, nullable=True)
