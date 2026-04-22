from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func

from ..core.config import settings
from ..core.database import SessionLocal
from ..models.bot import Bot
from ..models.historical_data import HistoricalData
from ..models.trade import Trade
from .mt5_client import mt5_client


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _trade_profit(trade: Trade) -> float:
    if trade.profit is not None:
        return float(trade.profit)
    return float(trade.pnl or 0)


def _serialize_trade(trade: Trade) -> Dict[str, Any]:
    return {
        "id": trade.id,
        "bot_id": trade.bot_id,
        "ticket": trade.ticket,
        "symbol": trade.symbol or settings.DEFAULT_SYMBOL,
        "direction": trade.direction,
        "volume": trade.volume,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "open_time": trade.open_time.isoformat() if trade.open_time else None,
        "close_time": trade.close_time.isoformat() if trade.close_time else None,
        "pnl": trade.pnl,
        "profit": trade.profit if trade.profit is not None else trade.pnl,
        "status": "closed" if trade.close_time else "open",
        "magic_number": trade.magic_number,
        "comment": trade.comment,
    }


def _serialize_position(position: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ticket": position.get("ticket"),
        "symbol": position.get("symbol"),
        "direction": position.get("type"),
        "volume": position.get("volume"),
        "price_open": position.get("price_open"),
        "sl": position.get("sl"),
        "tp": position.get("tp"),
        "profit": position.get("profit"),
        "magic": position.get("magic"),
        "comment": position.get("comment"),
        "time": position.get("time"),
    }


def _serialize_deal(deal: Dict[str, Any]) -> Dict[str, Any]:
    entry = str(deal.get("entry") or "").lower()
    trade_type = str(deal.get("type") or "").lower()
    is_close = entry in {"out", "out_by", "inout"}
    net_profit = _safe_float(deal.get("profit")) + _safe_float(deal.get("commission")) + _safe_float(deal.get("swap"))

    return {
        "id": deal.get("ticket") or deal.get("order"),
        "ticket": deal.get("ticket"),
        "order": deal.get("order"),
        "position_id": deal.get("position_id"),
        "symbol": deal.get("symbol") or settings.DEFAULT_SYMBOL,
        "direction": "buy" if trade_type == "buy" else "sell" if trade_type == "sell" else trade_type,
        "entry": entry or "unknown",
        "status": "closed" if is_close else "open",
        "volume": deal.get("volume"),
        "price": deal.get("price"),
        "profit": net_profit,
        "magic": deal.get("magic"),
        "comment": deal.get("comment"),
        "time": deal.get("time_iso") or deal.get("time"),
    }


def _calculate_drawdown(values: List[float]) -> float:
    peak = 0.0
    cumulative = 0.0
    max_drawdown = 0.0

    for value in values:
        cumulative += value
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return max_drawdown


async def build_dashboard_snapshot(symbol: Optional[str] = None) -> Dict[str, Any]:
    live_symbol = (symbol or settings.DEFAULT_SYMBOL).upper()
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    db = SessionLocal()
    try:
        closed_trades = db.query(Trade).filter(Trade.close_time.isnot(None)).all()
        open_db_trades = db.query(Trade).filter(Trade.close_time.is_(None)).all()
        recent_db_trades = db.query(Trade).order_by(desc(Trade.open_time)).limit(5).all()

        total_trades = len(closed_trades) + len(open_db_trades)
        total_pnl = sum(_trade_profit(trade) for trade in closed_trades)
        winning_trades = len([trade for trade in closed_trades if _trade_profit(trade) > 0])
        closed_count = len(closed_trades)
        win_rate = (winning_trades / closed_count * 100) if closed_count > 0 else 0
        closed_series = [_trade_profit(trade) for trade in sorted(closed_trades, key=lambda t: t.close_time or t.open_time or now)]
        max_drawdown = _calculate_drawdown(closed_series)

        active_bots = db.query(func.count(Bot.id)).filter(Bot.active.is_(True)).scalar() or 0
        total_candles = db.query(func.count(HistoricalData.id)).scalar() or 0
        today_db_profit = sum(
            _trade_profit(trade)
            for trade in closed_trades
            if trade.close_time and trade.close_time.date() == now.date()
        )
    finally:
        db.close()

    status_task = mt5_client.get_status()
    account_task = mt5_client.get_account()
    positions_task = mt5_client.get_positions()
    tick_task = mt5_client.get_tick(live_symbol)
    deals_task = mt5_client.get_history_deals(day_start, now)

    status, account, positions, tick, deals = await asyncio.gather(
        status_task,
        account_task,
        positions_task,
        tick_task,
        deals_task,
    )

    account = account or {}
    positions = positions or []
    deals = deals or []

    account_balance = _safe_float(account.get("balance"))
    account_equity = _safe_float(account.get("equity"))
    account_profit = _safe_float(account.get("profit"))
    account_margin = _safe_float(account.get("margin"))
    account_free_margin = _safe_float(account.get("free_margin"))

    floating_pnl = sum(_safe_float(position.get("profit")) for position in positions)
    if account_equity <= 0 and account_balance > 0:
        account_equity = account_balance + account_profit

    today_realized = sum(
        _safe_float(deal.get("profit"))
        + _safe_float(deal.get("commission"))
        + _safe_float(deal.get("swap"))
        for deal in deals
        if str(deal.get("entry") or "").lower() in {"out", "out_by", "inout"}
    )

    current_spread = _safe_float(tick.get("spread")) if tick else 0.0
    recent_deals = sorted(deals, key=lambda item: _safe_int(item.get("time")), reverse=True)[:5]

    live_total_pnl = total_pnl + floating_pnl
    daily_total_pnl = today_realized + floating_pnl
    bridge_connected = bool(status.get("mt5_connected")) if status else False

    return {
        "timestamp": now.isoformat(),
        "symbol": live_symbol,
        "mt5_connected": bridge_connected,
        "bridge_uptime_seconds": _safe_int(status.get("bridge_uptime_seconds")) if status else 0,
        "terminal_name": (status or {}).get("terminal", {}).get("name"),
        "account_login": _safe_int(account.get("login")) if account.get("login") is not None else None,
        "account_name": account.get("name"),
        "account_server": account.get("server"),
        "total_pnl": round(total_pnl, 2),
        "live_total_pnl": round(live_total_pnl, 2),
        "daily_pnl": round(daily_total_pnl, 2),
        "daily_realized_pnl": round(today_realized, 2),
        "historical_daily_pnl": round(today_db_profit, 2),
        "floating_pnl": round(floating_pnl, 2),
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(max_drawdown, 2),
        "active_bots": int(active_bots),
        "total_candles": int(total_candles),
        "total_trades": int(total_trades),
        "open_trades": len(open_db_trades),
        "closed_trades": len(closed_trades),
        "open_positions": len(positions),
        "account_balance": round(account_balance, 2),
        "account_equity": round(account_equity, 2),
        "account_margin": round(account_margin, 2),
        "account_free_margin": round(account_free_margin, 2),
        "account_profit": round(account_profit, 2),
        "symbol_spread": round(current_spread, 2),
        "recent_trades": [_serialize_deal(deal) for deal in recent_deals] if recent_deals else [_serialize_trade(trade) for trade in recent_db_trades],
        "open_positions_detail": [_serialize_position(position) for position in positions[:10]],
        "equity_point": {
            "time": now.isoformat(),
            "equity": round(account_equity, 2),
            "balance": round(account_balance, 2),
            "floating_pnl": round(floating_pnl, 2),
        },
        "indicator_options": [
            {"id": "live_total_pnl", "label": "PnL ao vivo"},
            {"id": "daily_pnl", "label": "PnL diário"},
            {"id": "account_equity", "label": "Equity"},
            {"id": "account_balance", "label": "Saldo"},
            {"id": "account_margin", "label": "Margem usada"},
            {"id": "account_free_margin", "label": "Margem livre"},
            {"id": "account_profit", "label": "Lucro aberto"},
            {"id": "floating_pnl", "label": "PnL flutuante"},
            {"id": "open_positions", "label": "Posições abertas"},
            {"id": "symbol_spread", "label": "Spread"},
            {"id": "bridge_uptime_seconds", "label": "Uptime bridge"},
            {"id": "daily_realized_pnl", "label": "PnL realizado hoje"},
            {"id": "historical_daily_pnl", "label": "PnL histórico"},
            {"id": "mt5_connected", "label": "Conexão MT5"},
        ],
    }
