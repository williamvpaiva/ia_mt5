from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TradeBase(BaseModel):
    ticket: int
    direction: str  # "buy" or "sell"
    volume: float
    open_price: float
    close_price: Optional[float] = None
    open_time: datetime
    close_time: Optional[datetime] = None
    pnl: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class TradeCreate(TradeBase):
    bot_id: int

class TradeUpdate(BaseModel):
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    pnl: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class TradeInDBBase(TradeBase):
    id: int
    bot_id: int

    class Config:
        orm_mode = True

class Trade(TradeInDBBase):
    pass