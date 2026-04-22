from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import MetaTrader5 as mt5
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("MT5Bridge")

BRIDGE_START = time.time()
COMMON_TERMINAL_PATHS = [
    "C:/Program Files/MetaTrader 5 Terminal/terminal64.exe",
    "C:/Program Files/MetaTrader 5/terminal64.exe",
]
COMMON_SUFFIXES = ("$", "@", "$D", "$N", "@D", "@N")
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}

app = FastAPI(title="MetaTrader 5 Bridge API", description="Bridge between Docker and the local MT5 terminal")

_bridge_state: Dict[str, Any] = {
    "initialized": False,
    "connected": False,
    "terminal_name": None,
    "terminal_company": None,
    "account_login": None,
    "account_name": None,
    "last_error": None,
    "connected_at": None,
    "terminal_path": os.getenv("MT5_TERMINAL_PATH"),
}


class OrderRequest(BaseModel):
    symbol: str
    action: str = Field(..., description="buy or sell")
    volume: float
    type: str = Field(default="market", description="market or limit")
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    magic: int = 0
    comment: str = "IA_MT5_Order"
    deviation: Optional[int] = None


class ModifyPositionRequest(BaseModel):
    sl: Optional[float] = None
    tp: Optional[float] = None


def _build_initialize_kwargs() -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}

    terminal_path = os.getenv("MT5_TERMINAL_PATH")
    if terminal_path:
        kwargs["path"] = terminal_path

    login = os.getenv("MT5_LOGIN")
    password = os.getenv("MT5_PASSWORD")
    server = os.getenv("MT5_SERVER")

    if login:
        try:
            kwargs["login"] = int(login)
        except ValueError:
            logger.warning("MT5_LOGIN must be numeric. Ignoring login override.")
    if password:
        kwargs["password"] = password
    if server:
        kwargs["server"] = server

    return kwargs


def _refresh_bridge_state() -> bool:
    terminal = None
    account = None

    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
    except Exception as exc:
        _bridge_state["last_error"] = str(exc)

    connected = bool(terminal and getattr(terminal, "connected", False))
    _bridge_state.update(
        {
            "initialized": True,
            "connected": connected,
            "terminal_name": getattr(terminal, "name", None) if terminal else None,
            "terminal_company": getattr(terminal, "company", None) if terminal else None,
            "account_login": getattr(account, "login", None) if account else None,
            "account_name": getattr(account, "name", None) if account else None,
            "connected_at": _bridge_state.get("connected_at") if connected else None,
        }
    )

    if connected and not _bridge_state["connected_at"]:
        _bridge_state["connected_at"] = datetime.now(timezone.utc).isoformat()

    return connected


def ensure_mt5_connection(reconnect: bool = True) -> bool:
    if _refresh_bridge_state():
        return True

    if not reconnect:
        return False

    return initialize_mt5()


def initialize_mt5() -> bool:
    initialize_kwargs = _build_initialize_kwargs()
    candidates: List[Dict[str, Any]] = []

    if initialize_kwargs:
        candidates.append(initialize_kwargs)

    candidates.append({})

    for terminal_path in COMMON_TERMINAL_PATHS:
        if os.path.exists(terminal_path):
            candidate = dict(initialize_kwargs)
            candidate["path"] = terminal_path
            candidates.append(candidate)

    mt5.shutdown()

    for candidate in candidates:
        try:
            if mt5.initialize(**candidate):
                _refresh_bridge_state()
                logger.info(
                    "MetaTrader 5 connected: %s / account %s",
                    _bridge_state.get("terminal_name"),
                    _bridge_state.get("account_login"),
                )
                return True
        except Exception as exc:
            _bridge_state["last_error"] = str(exc)

    _bridge_state["last_error"] = str(mt5.last_error())
    _bridge_state["initialized"] = False
    _bridge_state["connected"] = False
    logger.error("Failed to initialize MT5: %s", _bridge_state["last_error"])
    return False


def _available_symbols() -> List[Any]:
    return list(mt5.symbols_get() or [])


def _is_tradeable_symbol(info: Any) -> bool:
    trade_mode = getattr(info, "trade_mode", 0)
    return trade_mode not in (None, 0)


def _candidate_symbols(requested: str) -> List[str]:
    normalized = requested.strip().upper()
    candidates = [normalized]

    if re.fullmatch(r"[A-Z0-9]+", normalized):
        candidates.extend(f"{normalized}{suffix}" for suffix in COMMON_SUFFIXES)

    if normalized.endswith("$") or normalized.endswith("@"):
        candidates.extend([f"{normalized}D", f"{normalized}N"])

    return list(dict.fromkeys(candidates))


def resolve_symbol_name(symbol: str) -> str:
    requested = (symbol or "").strip().upper()
    if not requested:
        raise HTTPException(status_code=400, detail="symbol is required")

    if not ensure_mt5_connection():
        raise HTTPException(status_code=503, detail="MT5 terminal is not connected")

    available_symbols = _available_symbols()
    lookup = {s.name.upper(): s for s in available_symbols}

    exact = mt5.symbol_info(requested)
    if exact is not None and _is_tradeable_symbol(exact):
        mt5.symbol_select(requested, True)
        return requested

    candidates: List[str] = []
    if requested in lookup:
        candidates.append(lookup[requested].name)
    candidates.extend(_candidate_symbols(requested))
    candidates.extend(s.name for s in available_symbols if s.name.upper().startswith(requested))
    candidates = list(dict.fromkeys(candidates))

    for candidate in candidates:
        info = mt5.symbol_info(candidate)
        if info is not None and _is_tradeable_symbol(info):
            mt5.symbol_select(candidate, True)
            return candidate

    if exact is not None:
        mt5.symbol_select(requested, True)
        return requested

    if len(candidates) > 1:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "symbol is ambiguous",
                "requested": requested,
                "matches": candidates[:20],
            },
        )

    raise HTTPException(
        status_code=404,
        detail={
            "error": "symbol not found",
            "requested": requested,
        },
    )


def _normalize_price(price: float, tick_size: float, digits: int) -> float:
    if not tick_size or tick_size <= 0:
        return round(price, digits if digits >= 0 else 6)

    normalized = round(round(price / tick_size) * tick_size, digits if digits >= 0 else 6)
    return normalized


def _serialize_symbol(info: Any) -> Dict[str, Any]:
    return {
        "name": getattr(info, "name", None),
        "description": getattr(info, "description", None),
        "visible": getattr(info, "visible", None),
        "digits": getattr(info, "digits", None),
        "point": getattr(info, "point", None),
        "spread": getattr(info, "spread", None),
        "trade_mode": getattr(info, "trade_mode", None),
        "trade_tick_size": getattr(info, "trade_tick_size", None),
        "filling_mode": getattr(info, "filling_mode", None),
    }


def _serialize_tick(tick: Any) -> Dict[str, Any]:
    return {
        "bid": getattr(tick, "bid", None),
        "ask": getattr(tick, "ask", None),
        "last": getattr(tick, "last", None),
        "time": getattr(tick, "time", None),
    }


def _parse_datetime_query(value: Optional[str], default: datetime) -> datetime:
    if not value:
        return default

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {value}")

    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


def _serialize_deal_entry(entry: Any) -> str:
    mapping = {
        getattr(mt5, "DEAL_ENTRY_IN", object()): "in",
        getattr(mt5, "DEAL_ENTRY_OUT", object()): "out",
        getattr(mt5, "DEAL_ENTRY_INOUT", object()): "inout",
        getattr(mt5, "DEAL_ENTRY_OUT_BY", object()): "out_by",
    }
    return mapping.get(entry, str(entry))


def _serialize_deal_type(deal_type: Any) -> str:
    mapping = {
        getattr(mt5, "DEAL_TYPE_BUY", object()): "buy",
        getattr(mt5, "DEAL_TYPE_SELL", object()): "sell",
        getattr(mt5, "DEAL_TYPE_BALANCE", object()): "balance",
        getattr(mt5, "DEAL_TYPE_CREDIT", object()): "credit",
        getattr(mt5, "DEAL_TYPE_CHARGE", object()): "charge",
        getattr(mt5, "DEAL_TYPE_COMMISSION", object()): "commission",
        getattr(mt5, "DEAL_TYPE_COMMISSION_DAILY", object()): "commission_daily",
        getattr(mt5, "DEAL_TYPE_COMMISSION_MONTHLY", object()): "commission_monthly",
        getattr(mt5, "DEAL_TYPE_COMMISSION_AGENT_DAILY", object()): "commission_agent_daily",
        getattr(mt5, "DEAL_TYPE_COMMISSION_AGENT_MONTHLY", object()): "commission_agent_monthly",
    }
    return mapping.get(deal_type, str(deal_type))


def _serialize_account(info: Any) -> Dict[str, Any]:
    return {
        "login": getattr(info, "login", None),
        "name": getattr(info, "name", None),
        "server": getattr(info, "server", None),
        "company": getattr(info, "company", None),
        "currency": getattr(info, "currency", None),
        "balance": getattr(info, "balance", None),
        "equity": getattr(info, "equity", None),
        "margin": getattr(info, "margin", None),
        "free_margin": getattr(info, "margin_free", None),
        "profit": getattr(info, "profit", None),
        "leverage": getattr(info, "leverage", None),
    }


def _get_filling_mode(symbol_info: Any) -> int:
    mode = getattr(symbol_info, "filling_mode", None)
    if mode in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
        return mode
    return mt5.ORDER_FILLING_IOC


def _build_status_payload() -> Dict[str, Any]:
    connected = ensure_mt5_connection(reconnect=True)
    terminal = mt5.terminal_info() if connected else None
    account = mt5.account_info() if connected else None

    return {
        "status": "ok" if connected else "degraded",
        "mt5_connected": connected,
        "bridge_uptime_seconds": int(time.time() - BRIDGE_START),
        "terminal": {
            "name": getattr(terminal, "name", None) if terminal else None,
            "company": getattr(terminal, "company", None) if terminal else None,
            "path": getattr(terminal, "path", None) if terminal else None,
            "connected": getattr(terminal, "connected", None) if terminal else False,
        },
        "account": _serialize_account(account) if account else None,
        "last_error": _bridge_state.get("last_error"),
        "terminal_path": _bridge_state.get("terminal_path"),
    }


@app.on_event("startup")
def startup_event() -> None:
    if initialize_mt5():
        logger.info("MT5 bridge ready.")
    else:
        logger.warning("MT5 bridge started without an active terminal connection.")


@app.on_event("shutdown")
def shutdown_event() -> None:
    mt5.shutdown()
    logger.info("MT5 connection closed.")


@app.get("/health")
def health_check():
    payload = _build_status_payload()
    return payload


@app.get("/status")
def get_status():
    return _build_status_payload()


@app.get("/account")
def get_account():
    if not ensure_mt5_connection():
        raise HTTPException(status_code=503, detail="MT5 terminal is not connected")

    account = mt5.account_info()
    if account is None:
        raise HTTPException(status_code=503, detail="Unable to read account information")

    return _serialize_account(account)


@app.get("/symbols")
def list_symbols(
    prefix: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    visible_only: bool = Query(default=False),
):
    if not ensure_mt5_connection():
        raise HTTPException(status_code=503, detail="MT5 terminal is not connected")

    symbols = _available_symbols()
    if prefix:
        prefix_upper = prefix.strip().upper()
        symbols = [s for s in symbols if s.name.upper().startswith(prefix_upper)]
    if visible_only:
        symbols = [s for s in symbols if getattr(s, "visible", False)]

    return [_serialize_symbol(symbol) for symbol in symbols[:limit]]


@app.get("/resolve/{symbol}")
def resolve_symbol(symbol: str):
    resolved = resolve_symbol_name(symbol)
    symbol_info = mt5.symbol_info(resolved)
    return {
        "requested": symbol,
        "resolved": resolved,
        "symbol": _serialize_symbol(symbol_info) if symbol_info else None,
    }


@app.get("/rates/{symbol}")
def get_rates(symbol: str, timeframe: str = "M5", count: int = Query(default=100, ge=1, le=10000)):
    resolved_symbol = resolve_symbol_name(symbol)
    tf = TIMEFRAME_MAP.get(timeframe.upper(), mt5.TIMEFRAME_M5)

    rates = mt5.copy_rates_from_pos(resolved_symbol, tf, 0, count)
    if rates is None:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch rates for {resolved_symbol}: {mt5.last_error()}",
        )

    return [
        {
            "time": int(rate["time"]),
            "open": float(rate["open"]),
            "high": float(rate["high"]),
            "low": float(rate["low"]),
            "close": float(rate["close"]),
            "tick_volume": int(rate["tick_volume"]),
            "spread": int(rate["spread"]) if "spread" in rate.dtype.names else 0,
            "real_volume": int(rate["real_volume"]) if "real_volume" in rate.dtype.names else 0,
        }
        for rate in rates
    ]


@app.get("/tick/{symbol}")
def get_tick(symbol: str):
    resolved_symbol = resolve_symbol_name(symbol)
    tick = mt5.symbol_info_tick(resolved_symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Symbol {resolved_symbol} not found")
    return _serialize_tick(tick)


@app.get("/history/deals")
def get_history_deals(
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    magic: Optional[int] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
):
    if not ensure_mt5_connection():
        raise HTTPException(status_code=503, detail="MT5 terminal is not connected")

    start = _parse_datetime_query(from_date, datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    end = _parse_datetime_query(to_date, datetime.now())
    if end < start:
        raise HTTPException(status_code=400, detail="to_date must be greater than or equal to from_date")

    deals = mt5.history_deals_get(start, end)
    if deals is None:
        return []

    symbol_filter = symbol.strip().upper() if symbol else None
    payload: List[Dict[str, Any]] = []

    for deal in deals:
        if magic is not None and getattr(deal, "magic", None) != magic:
            continue
        if symbol_filter and getattr(deal, "symbol", "").upper() != symbol_filter:
            continue

        deal_time = getattr(deal, "time", None)
        payload.append(
            {
                "ticket": getattr(deal, "ticket", None),
                "order": getattr(deal, "order", None),
                "position_id": getattr(deal, "position_id", None),
                "symbol": getattr(deal, "symbol", None),
                "type": _serialize_deal_type(getattr(deal, "type", None)),
                "entry": _serialize_deal_entry(getattr(deal, "entry", None)),
                "volume": getattr(deal, "volume", None),
                "price": getattr(deal, "price", None),
                "profit": getattr(deal, "profit", None),
                "commission": getattr(deal, "commission", None),
                "swap": getattr(deal, "swap", None),
                "magic": getattr(deal, "magic", None),
                "comment": getattr(deal, "comment", None),
                "time": deal_time,
                "time_iso": datetime.fromtimestamp(deal_time).isoformat() if deal_time is not None else None,
            }
        )

    return payload


@app.post("/order")
def place_order(order: OrderRequest):
    resolved_symbol = resolve_symbol_name(order.symbol)
    symbol_info = mt5.symbol_info(resolved_symbol)
    if symbol_info is None:
        raise HTTPException(status_code=400, detail=f"Symbol {resolved_symbol} not found")

    if not symbol_info.visible and not mt5.symbol_select(resolved_symbol, True):
        raise HTTPException(status_code=400, detail=f"Failed to select symbol {resolved_symbol}")

    tick = mt5.symbol_info_tick(resolved_symbol)
    if tick is None:
        raise HTTPException(status_code=503, detail="Unable to get current tick")

    action = order.action.strip().lower()
    order_type = order.type.strip().lower()
    digits = int(getattr(symbol_info, "digits", 6) or 6)
    tick_size = float(getattr(symbol_info, "trade_tick_size", 0) or getattr(symbol_info, "point", 0) or 0)
    price = float(tick.ask if action == "buy" else tick.bid)

    type_dict = {
        "buy": mt5.ORDER_TYPE_BUY,
        "sell": mt5.ORDER_TYPE_SELL,
    }
    limit_type_dict = {
        "buy": mt5.ORDER_TYPE_BUY_LIMIT,
        "sell": mt5.ORDER_TYPE_SELL_LIMIT,
    }

    if action not in type_dict:
        raise HTTPException(status_code=400, detail="action must be buy or sell")

    if order_type == "market":
        mt5_order_type = type_dict[action]
        requested_price = price
        trade_action = mt5.TRADE_ACTION_DEAL
    elif order_type == "limit":
        if order.price is None:
            raise HTTPException(status_code=400, detail="price is required for limit orders")
        mt5_order_type = limit_type_dict[action]
        requested_price = float(order.price)
        trade_action = mt5.TRADE_ACTION_PENDING
    else:
        raise HTTPException(status_code=400, detail="type must be market or limit")

    request: Dict[str, Any] = {
        "action": trade_action,
        "symbol": resolved_symbol,
        "volume": float(order.volume),
        "type": mt5_order_type,
        "price": _normalize_price(requested_price, tick_size, digits),
        "magic": int(order.magic),
        "comment": order.comment or "IA_MT5_Order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _get_filling_mode(symbol_info),
    }

    if order.sl is not None:
        if order.sl < (price / 10):
            if action == "buy":
                request["sl"] = _normalize_price(price - order.sl, tick_size, digits)
            else:
                request["sl"] = _normalize_price(price + order.sl, tick_size, digits)
        else:
            request["sl"] = _normalize_price(order.sl, tick_size, digits)

    if order.tp is not None:
        if order.tp < (price / 10):
            if action == "buy":
                request["tp"] = _normalize_price(price + order.tp, tick_size, digits)
            else:
                request["tp"] = _normalize_price(price - order.tp, tick_size, digits)
        else:
            request["tp"] = _normalize_price(order.tp, tick_size, digits)

    if order.deviation is not None:
        request["deviation"] = max(0, int(order.deviation))

    logger.info(
        "Sending order %s %s %s @ %s (SL: %s, TP: %s)",
        action,
        order.volume,
        resolved_symbol,
        request["price"],
        request.get("sl"),
        request.get("tp"),
    )

    result = mt5.order_send(request)
    if result is None:
        raise HTTPException(status_code=500, detail=f"Order send failed: {mt5.last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error("Order failed: %s (code: %s)", result.comment, result.retcode)
        raise HTTPException(
            status_code=500,
            detail=f"Error sending order: {result.comment} (code: {result.retcode})",
        )

    return {
        "ticket": result.order,
        "retcode": result.retcode,
        "comment": result.comment,
        "price": result.price,
        "symbol": resolved_symbol,
    }


@app.get("/positions")
def get_positions(
    magic: Optional[int] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
):
    if not ensure_mt5_connection():
        raise HTTPException(status_code=503, detail="MT5 terminal is not connected")

    positions = mt5.positions_get()
    if positions is None:
        return []

    payload = []
    symbol_filter = symbol.strip().upper() if symbol else None

    for position in positions:
        if magic is not None and getattr(position, "magic", None) != magic:
            continue
        if symbol_filter and getattr(position, "symbol", "").upper() != symbol_filter:
            continue

        payload.append(
            {
                "ticket": position.ticket,
                "symbol": position.symbol,
                "type": "buy" if position.type == 0 else "sell",
                "volume": position.volume,
                "price_open": position.price_open,
                "sl": getattr(position, "sl", None),
                "tp": getattr(position, "tp", None),
                "profit": position.profit,
                "magic": position.magic,
                "comment": position.comment,
                "time": position.time,
            }
        )

    return payload


@app.patch("/position/{ticket}")
def modify_position(ticket: int, request: ModifyPositionRequest):
    if not ensure_mt5_connection():
        raise HTTPException(status_code=503, detail="MT5 terminal is not connected")

    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise HTTPException(status_code=404, detail="Position not found")

    pos = positions[0]
    symbol = pos.symbol
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} not found")

    if not symbol_info.visible and not mt5.symbol_select(symbol, True):
        raise HTTPException(status_code=400, detail=f"Failed to select symbol {symbol}")

    if request.sl is None and request.tp is None:
        raise HTTPException(status_code=400, detail="sl or tp must be provided")

    digits = int(getattr(symbol_info, "digits", 6) or 6)
    tick_size = float(getattr(symbol_info, "trade_tick_size", 0) or getattr(symbol_info, "point", 0) or 0)

    modify_request: Dict[str, Any] = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": ticket,
        "magic": pos.magic,
        "comment": "IA_MT5_Modify",
    }

    if request.sl is not None:
        modify_request["sl"] = _normalize_price(float(request.sl), tick_size, digits)
    if request.tp is not None:
        modify_request["tp"] = _normalize_price(float(request.tp), tick_size, digits)

    result = mt5.order_send(modify_request)
    if result is None:
        raise HTTPException(status_code=500, detail=f"Modify order failed: {mt5.last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(status_code=500, detail=f"Error modifying position: {result.comment}")

    return {"status": "modified", "ticket": ticket, "retcode": result.retcode}


@app.delete("/position/{ticket}")
def close_position(ticket: int):
    if not ensure_mt5_connection():
        raise HTTPException(status_code=503, detail="MT5 terminal is not connected")

    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise HTTPException(status_code=404, detail="Position not found")

    pos = positions[0]
    symbol = pos.symbol
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} not found")

    if not symbol_info.visible and not mt5.symbol_select(symbol, True):
        raise HTTPException(status_code=400, detail=f"Failed to select symbol {symbol}")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=503, detail="Unable to get current tick")

    type_close = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = float(tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask)
    digits = int(getattr(symbol_info, "digits", 6) or 6)
    tick_size = float(getattr(symbol_info, "trade_tick_size", 0) or getattr(symbol_info, "point", 0) or 0)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": pos.volume,
        "type": type_close,
        "position": ticket,
        "price": _normalize_price(price, tick_size, digits),
        "magic": pos.magic,
        "comment": "IA_MT5_Close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _get_filling_mode(symbol_info),
    }

    result = mt5.order_send(request)
    if result is None:
        raise HTTPException(status_code=500, detail=f"Close order failed: {mt5.last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(status_code=500, detail=f"Error closing position: {result.comment}")

    return {"status": "closed", "ticket": ticket, "retcode": result.retcode}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("MT5_BRIDGE_HOST", "0.0.0.0"),
        port=int(os.getenv("MT5_BRIDGE_PORT", "5001")),
    )
