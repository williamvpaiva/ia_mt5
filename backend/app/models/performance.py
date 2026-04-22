from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base

class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    equity = Column(Float)
    daily_pnl = Column(Float)
    drawdown = Column(Float)
    win_rate_24h = Column(Float)