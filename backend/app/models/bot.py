"""
Bot Model
Correcao: Adicionados campos faltantes conforme especificacao
Prioridade: ALTA
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Float
from sqlalchemy.sql import func
from ..core.database import Base


class Bot(Base):
    __tablename__ = "bots"
    
    # ========== CAMPOS ORIGINAIS ==========
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    symbol = Column(String, default="WINM26")
    timeframe = Column(String, default="M5")
    active = Column(Boolean, default=False)
    magic_number = Column(Integer, unique=True, index=True)
    config = Column(JSON, nullable=True)  # Pesos, indicadores, etc
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # ========== NOVOS CAMPOS (CORREA?A?O) ==========
    # Trading limits
    max_spread = Column(Float, default=5.0)          # Spread mA?ximo aceitA?vel (pontos)
    max_slippage = Column(Float, default=3.0)        # Slippage mA?ximo aceitA?vel (pontos)
    allowed_symbols = Column(JSON, default=list)    # Lista de sA?mbolos permitidos
    
    # Trading schedule
    trading_schedule = Column(JSON, nullable=True)   # Config de horA?rios legada
    excluded_days = Column(JSON, default=list)       # Dias da semana excluA?dos [0, 6]
    start_time = Column(String, default="09:00")    # HH:MM
    end_time = Column(String, default="17:50")      # HH:MM
    
    # ========== NOVOS CAMPOS ESTRATA?GICOS (MA?DULOS INDEPENDENTES) ==========
    signals_config = Column(JSON, default=lambda: {
        "ma_cross": {"active": False, "fast_period": 9, "slow_period": 21},
        "rsi": {"active": False, "period": 14, "overbought": 70, "oversold": 30},
        "atr": {"active": False, "period": 14, "multiplier": 2.0},
        "price_action": {"active": False, "patterns": ["pinbar", "engulfing"]}
    })
    
    risk_config = Column(JSON, default=lambda: {
        "stop_loss": 200,
        "take_profit": 500,
        "trailing_stop": {"active": False, "distance": 150, "step": 10},
        "daily_loss_limit": 500.0,
        "daily_profit_limit": 1000.0,
        "max_positions": 3,
        "max_daily_trades": 10,
        "max_risk_per_trade": 0.02 # 2% da banca
    })
    
    ai_config = Column(JSON, default=lambda: {
        "rl_active": True,
        "model_path": None,
        "last_reward": 0.0,
        "mode": "hybrid" # hybrid, pure_ia, pure_signals
    })
    
    spy_config = Column(JSON, default=lambda: {
        "active": False,
        "target_magic": None, # NAomero mA?gico do bot a ser espiado
        "follow_signals": True,
        "follow_trades": False
    })
    
    # Status e MA?tricas
    last_run = Column(DateTime, nullable=True)      
    last_error = Column(String, nullable=True)       
    total_trades = Column(Integer, default=0)        
    winning_trades = Column(Integer, default=0)       
    losing_trades = Column(Integer, default=0)        
    total_pnl = Column(Float, default=0.0)
