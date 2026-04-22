"""
Trade Model
CorreA?A?o: Adicionados campos faltantes conforme especificaA?A?o
Prioridade: ALTA
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from ..core.database import Base


class Trade(Base):
    __tablename__ = "trades"
    
    # ========== CAMPOS ORIGINAIS ==========
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"))
    ticket = Column(Integer, unique=True, index=True, nullable=True)
    direction = Column(String)  # buy, sell
    volume = Column(Float)
    open_price = Column(Float, nullable=True)
    open_time = Column(DateTime)
    close_price = Column(Float, nullable=True)
    close_time = Column(DateTime, nullable=True)
    pnl = Column(Float, default=0.0)
    sl = Column(Float, nullable=True)
    tp = Column(Float, nullable=True)
    
    # ========== NOVOS CAMPOS (CORREA?A?O) ==========
    symbol = Column(String, index=True, nullable=True)          # SA?mbolo do ativo
    entry_price = Column(Float, nullable=True)                 # PreA?o de entrada
    exit_price = Column(Float, nullable=True)                  # PreA?o de saA?da
    profit = Column(Float, nullable=True)                     # Lucro lA?quido (pnl - commission + swap)
    commission = Column(Float, default=0.0)                  # ComissA?o
    swap = Column(Float, default=0.0)                         # Swap/overnight
    magic_number = Column(Integer, index=True, nullable=True) # Identificador Aonico do bot
    comment = Column(Text, nullable=True)                     # ComentA?rio

    @property
    def status(self) -> str:
        return "closed" if self.close_time else "open"
