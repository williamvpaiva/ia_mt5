from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import desc, func

from ..core.config import settings
from ..core.database import SessionLocal
from ..models.bot import Bot
from ..models.historical_data import HistoricalData
from ..models.trade import Trade
from .bot_metrics_service import collect_bot_metrics
from .bot_manager import bot_manager
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


def _safe_optional_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _trade_profit(trade: Trade) -> float:
    if trade.profit is not None:
        return float(trade.profit)
    return float(trade.pnl or 0)


def _resolve_bot_name(
    bot_id: Optional[int],
    magic_number: Optional[int],
    symbol: Optional[str],
    bot_name_by_id: Optional[Dict[int, str]] = None,
    bot_name_by_magic: Optional[Dict[int, str]] = None,
) -> Optional[str]:
    if bot_id is not None and bot_name_by_id and bot_id in bot_name_by_id:
        return bot_name_by_id[bot_id]

    if magic_number is not None and bot_name_by_magic and magic_number in bot_name_by_magic:
        return bot_name_by_magic[magic_number]

    if symbol:
        return symbol

    if bot_id is not None:
        return f"Bot #{bot_id}"

    if magic_number is not None:
        return f"MG {magic_number}"

    return None


def _build_bot_lookup(bots: Sequence[Bot]) -> Dict[str, Any]:
    bot_name_by_id: Dict[int, str] = {}
    bot_name_by_magic: Dict[int, str] = {}
    bot_magic_by_id: Dict[int, int] = {}
    bot_symbol_by_id: Dict[int, str] = {}
    bot_ids: List[int] = []
    bot_names: List[str] = []
    bot_symbols: List[str] = []

    for bot in bots:
        if bot.id is not None:
            bot_id = int(bot.id)
            bot_ids.append(bot_id)
            bot_name_by_id[bot_id] = bot.name
            bot_names.append(bot.name)
            magic = _safe_optional_int(bot.magic_number)
            if magic is not None:
                bot_magic_by_id[bot_id] = magic
            if bot.symbol:
                bot_symbol_by_id[bot_id] = bot.symbol.upper()
        if bot.magic_number is not None:
            magic = _safe_optional_int(bot.magic_number)
            if magic is not None:
                bot_name_by_magic[magic] = bot.name
        if bot.symbol:
            bot_symbols.append(bot.symbol.upper())

    return {
        "bot_name_by_id": bot_name_by_id,
        "bot_name_by_magic": bot_name_by_magic,
        "bot_magic_by_id": bot_magic_by_id,
        "bot_symbol_by_id": bot_symbol_by_id,
        "bot_ids": bot_ids,
        "bot_names": bot_names,
        "bot_symbols": sorted(set(bot_symbols)),
    }


def _serialize_trade(
    trade: Trade,
    *,
    bot_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": trade.id,
        "bot_id": trade.bot_id,
        "bot_name": bot_name,
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


def _serialize_position(
    position: Dict[str, Any],
    *,
    bot_name: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "ticket": position.get("ticket"),
        "symbol": position.get("symbol"),
        "bot_name": bot_name,
        "bot_id": position.get("bot_id"),
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


def _serialize_deal(
    deal: Dict[str, Any],
    *,
    bot_name: Optional[str] = None,
) -> Dict[str, Any]:
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
        "bot_name": bot_name,
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


def _normalize_bot_ids(bot_ids: Optional[List[int]]) -> List[int]:
    normalized: List[int] = []
    for bot_id in bot_ids or []:
        parsed = _safe_optional_int(bot_id)
        if parsed is None or parsed <= 0 or parsed in normalized:
            continue
        normalized.append(parsed)
    return normalized


async def build_dashboard_snapshot(symbol: Optional[str] = None, bot_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    requested_bot_ids = _normalize_bot_ids(bot_ids)
    filter_active = bool(requested_bot_ids)
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    db = SessionLocal()
    try:
        all_bots = db.query(Bot).order_by(Bot.id.asc()).all()
        bot_lookup = _build_bot_lookup(all_bots)
        scope_bots = [bot for bot in all_bots if int(bot.id) in requested_bot_ids] if filter_active else list(all_bots)
        scope_bot_ids = [int(bot.id) for bot in scope_bots if bot.id is not None]
        scope_names = [bot.name for bot in scope_bots]
        scope_symbols = sorted({(bot.symbol or settings.DEFAULT_SYMBOL).upper() for bot in scope_bots if bot.symbol})
        scope_magics = sorted(
            {
                parsed_magic
                for parsed_magic in (_safe_optional_int(bot.magic_number) for bot in scope_bots)
                if parsed_magic is not None
            }
        )

        metrics_by_bot = await collect_bot_metrics(db, scope_bots if filter_active else all_bots)
        aggregate_total_trades = sum(_safe_int(item.get("total_trades")) for item in metrics_by_bot.values())
        aggregate_closed_trades = sum(_safe_int(item.get("closed_trades")) for item in metrics_by_bot.values())
        aggregate_open_trades = sum(_safe_int(item.get("open_trades")) for item in metrics_by_bot.values())
        aggregate_winning_trades = sum(_safe_int(item.get("winning_trades")) for item in metrics_by_bot.values())
        aggregate_losing_trades = sum(_safe_int(item.get("losing_trades")) for item in metrics_by_bot.values())
        aggregate_total_pnl = round(sum(_safe_float(item.get("total_pnl")) for item in metrics_by_bot.values()), 2)
        aggregate_win_rate = (aggregate_winning_trades / aggregate_closed_trades * 100) if aggregate_closed_trades > 0 else 0.0

        live_symbol = (symbol or (scope_symbols[0] if scope_symbols else settings.DEFAULT_SYMBOL)).upper()

        trade_query = db.query(Trade)
        if filter_active:
            if scope_bot_ids:
                trade_query = trade_query.filter(Trade.bot_id.in_(scope_bot_ids))
            else:
                trade_query = trade_query.filter(Trade.id == -1)

        closed_trades = trade_query.filter(Trade.close_time.isnot(None)).all()
        open_db_trades = trade_query.filter(Trade.close_time.is_(None)).all()
        recent_db_trades = trade_query.order_by(desc(Trade.open_time)).limit(5).all()

        total_trades = aggregate_total_trades if aggregate_total_trades > 0 else len(closed_trades) + len(open_db_trades)
        total_pnl = aggregate_total_pnl if aggregate_total_trades > 0 else sum(_trade_profit(trade) for trade in closed_trades)
        winning_trades = aggregate_winning_trades if aggregate_total_trades > 0 else len([trade for trade in closed_trades if _trade_profit(trade) > 0])
        closed_count = aggregate_closed_trades if aggregate_total_trades > 0 else len(closed_trades)
        win_rate = aggregate_win_rate if aggregate_total_trades > 0 else ((winning_trades / closed_count * 100) if closed_count > 0 else 0)
        closed_series = [_trade_profit(trade) for trade in sorted(closed_trades, key=lambda t: t.close_time or t.open_time or now)]
        max_drawdown = _calculate_drawdown(closed_series)

        if filter_active:
            active_bots = len([bot for bot in scope_bots if bot.active])
            running_bots = sum(1 for bot_id in scope_bot_ids if bot_id in bot_manager.active_bots)
            paused_bots = sum(1 for bot_id in scope_bot_ids if bot_manager.trading_paused.get(bot_id))
        else:
            active_bots = db.query(func.count(Bot.id)).filter(Bot.active.is_(True)).scalar() or 0
            running_bots = len(bot_manager.active_bots)
            paused_bots = sum(1 for value in bot_manager.trading_paused.values() if value)

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

    if filter_active:
        selected_magics = set(scope_magics)
        if selected_magics:
            positions = [position for position in positions if _safe_optional_int(position.get("magic")) in selected_magics]
            deals = [deal for deal in deals if _safe_optional_int(deal.get("magic")) in selected_magics]
        else:
            positions = []
            deals = []

    account_balance = _safe_float(account.get("balance"))
    account_equity = _safe_float(account.get("equity"))
    account_profit = _safe_float(account.get("profit"))
    account_margin = _safe_float(account.get("margin"))
    account_free_margin = _safe_float(account.get("free_margin"))

    floating_pnl = sum(_safe_float(position.get("profit")) for position in positions)
    if account_equity <= 0 and account_balance > 0:
        account_equity = account_balance + account_profit

    closed_live_deals = [
        deal
        for deal in deals
        if str(deal.get("entry") or "").lower() in {"out", "out_by", "inout"}
    ]
    live_realized_series = [
        _safe_float(deal.get("profit"))
        + _safe_float(deal.get("commission"))
        + _safe_float(deal.get("swap"))
        for deal in closed_live_deals
    ]
    today_realized = sum(live_realized_series)
    live_closed_count = len(closed_live_deals)
    live_winning_trades = len(
        [
            deal
            for deal in closed_live_deals
            if (_safe_float(deal.get("profit")) + _safe_float(deal.get("commission")) + _safe_float(deal.get("swap"))) > 0
        ]
    )
    live_win_rate = (live_winning_trades / live_closed_count * 100) if live_closed_count > 0 else 0
    live_max_drawdown = _calculate_drawdown(live_realized_series)
    live_trade_keys = {
        deal.get("position_id") or deal.get("order") or deal.get("ticket")
        for deal in deals
        if deal.get("position_id") is not None or deal.get("order") is not None or deal.get("ticket") is not None
    }
    live_trade_keys.discard(None)
    live_total_trades = len(live_trade_keys)

    current_spread = _safe_float(tick.get("spread")) if tick else 0.0
    recent_deals = sorted(deals, key=lambda item: _safe_int(item.get("time")), reverse=True)[:5]

    db_has_closed_history = closed_count > 0
    display_total_pnl = total_pnl if db_has_closed_history else today_realized
    display_win_rate = win_rate if db_has_closed_history else live_win_rate
    display_max_drawdown = max_drawdown if db_has_closed_history else live_max_drawdown
    display_total_trades = total_trades if db_has_closed_history else live_total_trades
    display_closed_trades = closed_count if db_has_closed_history else live_closed_count
    display_open_trades = aggregate_open_trades if db_has_closed_history and aggregate_total_trades > 0 else len(open_db_trades) if db_has_closed_history else len(positions)
    display_historical_daily_pnl = today_db_profit if db_has_closed_history and today_db_profit != 0 else today_realized
    live_total_pnl = display_total_pnl + floating_pnl
    daily_total_pnl = today_realized + floating_pnl
    bridge_connected = bool(status.get("mt5_connected")) if status else False
    terminal_connected = bool((status or {}).get("terminal", {}).get("connected"))

    bot_scope = {
        "mode": "selected" if filter_active else "all",
        "selected": filter_active,
        "requested_bot_ids": requested_bot_ids,
        "selected_bot_ids": scope_bot_ids if filter_active else [],
        "selected_bot_names": scope_names if filter_active else [],
        "selected_symbols": scope_symbols if filter_active else [],
        "selected_magic_numbers": scope_magics if filter_active else [],
        "scope_count": len(scope_bots) if filter_active else len(all_bots),
        "total_bots": len(all_bots),
    }

    recent_trades = [
        _serialize_deal(
            deal,
            bot_name=_resolve_bot_name(
                None,
                _safe_optional_int(deal.get("magic")),
                deal.get("symbol"),
                bot_lookup["bot_name_by_id"],
                bot_lookup["bot_name_by_magic"],
            ),
        )
        for deal in recent_deals
    ] if recent_deals else [
        _serialize_trade(
            trade,
            bot_name=_resolve_bot_name(
                _safe_optional_int(trade.bot_id),
                _safe_optional_int(trade.magic_number),
                trade.symbol,
                bot_lookup["bot_name_by_id"],
                bot_lookup["bot_name_by_magic"],
            ),
        )
        for trade in recent_db_trades
    ]

    return {
        "timestamp": now.isoformat(),
        "symbol": live_symbol,
        "mt5_connected": bridge_connected,
        "terminal_connected": terminal_connected,
        "bridge_status": (status or {}).get("status"),
        "bridge_last_error": (status or {}).get("last_error"),
        "bridge_uptime_seconds": _safe_int(status.get("bridge_uptime_seconds")) if status else 0,
        "terminal_name": (status or {}).get("terminal", {}).get("name"),
        "account_login": _safe_int(account.get("login")) if account.get("login") is not None else None,
        "account_name": account.get("name"),
        "account_server": account.get("server"),
        "total_pnl": round(display_total_pnl, 2),
        "live_total_pnl": round(live_total_pnl, 2),
        "daily_pnl": round(daily_total_pnl, 2),
        "daily_realized_pnl": round(today_realized, 2),
        "historical_daily_pnl": round(display_historical_daily_pnl, 2),
        "floating_pnl": round(floating_pnl, 2),
        "win_rate": round(display_win_rate, 2),
        "max_drawdown": round(display_max_drawdown, 2),
        "active_bots": int(active_bots),
        "running_bots": int(running_bots),
        "paused_bots": int(paused_bots),
        "total_candles": int(total_candles),
        "total_trades": int(display_total_trades),
        "open_trades": int(display_open_trades),
        "closed_trades": int(display_closed_trades),
        "open_positions": len(positions),
        "account_balance": round(account_balance, 2),
        "account_equity": round(account_equity, 2),
        "account_margin": round(account_margin, 2),
        "account_free_margin": round(account_free_margin, 2),
        "account_profit": round(account_profit, 2),
        "symbol_spread": round(current_spread, 2),
        "recent_trades": recent_trades,
        "open_positions_detail": [
            _serialize_position(
                position,
                bot_name=_resolve_bot_name(
                    None,
                    _safe_optional_int(position.get("magic")),
                    position.get("symbol"),
                    bot_lookup["bot_name_by_id"],
                    bot_lookup["bot_name_by_magic"],
                ),
            )
            for position in positions[:10]
        ],
        "metrics_source": "mt5_live" if not db_has_closed_history else "mt5_live+db",
        "selected_bot_ids": bot_scope["selected_bot_ids"],
        "selected_bot_names": bot_scope["selected_bot_names"],
        "selected_symbols": bot_scope["selected_symbols"],
        "selected_magic_numbers": bot_scope["selected_magic_numbers"],
        "bot_scope": bot_scope,
        "equity_point": {
            "time": now.isoformat(),
            "equity": round(account_equity, 2),
            "balance": round(account_balance, 2),
            "floating_pnl": round(floating_pnl, 2),
        },
        "indicator_options": [
            {"id": "live_total_pnl", "label": "PnL ao vivo"},
            {"id": "daily_pnl", "label": "PnL diario"},
            {"id": "account_equity", "label": "Equity"},
            {"id": "account_balance", "label": "Saldo"},
            {"id": "account_margin", "label": "Margem usada"},
            {"id": "account_free_margin", "label": "Margem livre"},
            {"id": "account_profit", "label": "Lucro aberto"},
            {"id": "floating_pnl", "label": "PnL flutuante"},
            {"id": "open_positions", "label": "Posicoes abertas"},
            {"id": "symbol_spread", "label": "Spread"},
            {"id": "bridge_uptime_seconds", "label": "Uptime bridge"},
            {"id": "daily_realized_pnl", "label": "PnL realizado hoje"},
            {"id": "historical_daily_pnl", "label": "PnL historico"},
            {"id": "mt5_connected", "label": "Conexao MT5"},
        ],
    }
