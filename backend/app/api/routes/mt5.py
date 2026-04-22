from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...core.config import settings
from ...services.mt5_client import mt5_client


router = APIRouter(prefix="/mt5", tags=["MT5"])


@router.get("/health")
async def health():
    status = await mt5_client.get_status()
    if not status:
        return {
            "status": "degraded",
            "bridge_url": settings.MT5_BRIDGE_URL,
            "bridge_timeout": settings.MT5_BRIDGE_TIMEOUT,
            "mt5_connected": False,
        }

    return {
        "bridge_url": settings.MT5_BRIDGE_URL,
        "bridge_timeout": settings.MT5_BRIDGE_TIMEOUT,
        **status,
    }


@router.get("/status")
async def status():
    return await health()


@router.get("/account")
async def account():
    result = await mt5_client.get_account()
    if not result:
        raise HTTPException(status_code=503, detail="MT5 account information is unavailable")
    return result


@router.get("/symbols")
async def symbols(
    prefix: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    visible_only: bool = Query(default=False),
):
    return await mt5_client.list_symbols(prefix=prefix, limit=limit, visible_only=visible_only)


@router.get("/resolve/{symbol}")
async def resolve_symbol(symbol: str):
    result = await mt5_client.resolve_symbol(symbol)
    if not result:
        raise HTTPException(status_code=503, detail="Unable to resolve symbol")
    return result


@router.get("/rates/{symbol}")
async def rates(symbol: str, timeframe: str = "M5", count: int = Query(default=100, ge=1, le=10000)):
    data = await mt5_client.get_rates(symbol, timeframe=timeframe, count=count)
    if not data:
        raise HTTPException(status_code=503, detail="Unable to fetch MT5 rates")
    return data


@router.get("/tick/{symbol}")
async def tick(symbol: str):
    data = await mt5_client.get_tick(symbol)
    if not data:
        raise HTTPException(status_code=503, detail="Unable to fetch MT5 tick")
    return data


@router.get("/positions")
async def positions(
    magic: Optional[int] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
):
    return await mt5_client.get_positions(magic=magic, symbol=symbol)
