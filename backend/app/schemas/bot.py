from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class BotBase(BaseModel):
    name: str
    symbol: str = "WINM26"
    timeframe: str = "M5"
    magic_number: int
    max_spread: float = 5.0
    max_slippage: float = 3.0
    allowed_symbols: List[str] = Field(default_factory=lambda: ["WINM26"])
    trading_schedule: Optional[Dict] = None
    excluded_days: Optional[List[int]] = Field(default_factory=list)
    start_time: Optional[str] = "09:00"
    end_time: Optional[str] = "17:50"
    config: Optional[Dict] = None
    signals_config: Optional[Dict] = None
    risk_config: Optional[Dict] = None
    ai_config: Optional[Dict] = None
    spy_config: Optional[Dict] = None

class BotCreate(BotBase):
    pass

class BotUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    active: Optional[bool] = None
    magic_number: Optional[int] = None
    max_spread: Optional[float] = None
    max_slippage: Optional[float] = None
    allowed_symbols: Optional[List[str]] = None
    trading_schedule: Optional[Dict] = None
    excluded_days: Optional[List[int]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    config: Optional[Dict] = None
    signals_config: Optional[Dict] = None
    risk_config: Optional[Dict] = None
    ai_config: Optional[Dict] = None
    spy_config: Optional[Dict] = None

class BotResponse(BotBase):
    id: int
    active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_run: Optional[datetime]
    last_error: Optional[str]
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    closed_trades: Optional[int] = None
    open_trades: Optional[int] = None
    win_rate: Optional[float] = None
    metrics_source: Optional[str] = None
    metrics_updated_at: Optional[datetime] = None
    signals_config: Optional[Dict]
    risk_config: Optional[Dict]
    ai_config: Optional[Dict]
    spy_config: Optional[Dict]

    class Config:
        from_attributes = True
