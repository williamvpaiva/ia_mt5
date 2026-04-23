from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from ..models.bot import Bot
from ..models.trade import Trade
from .mt5_client import mt5_client


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_datetime(value: Optional[datetime]) -> datetime:
    if value is None:
        return datetime.now() - timedelta(days=365)
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _is_closed_deal(deal: Dict[str, Any]) -> bool:
    entry = str(deal.get("entry") or "").lower()
    return entry in {"out", "out_by", "inout"}


def _deal_net_profit(deal: Dict[str, Any]) -> float:
    return _safe_float(deal.get("profit")) + _safe_float(deal.get("commission")) + _safe_float(deal.get("swap"))


def _summarize_closed_items(items: Sequence[Dict[str, Any]], open_count: int = 0, source: str = "db") -> Dict[str, Any]:
    closed_items = [item for item in items if _is_closed_deal(item)]
    total_pnl = sum(_deal_net_profit(item) for item in closed_items)
    winning = len([item for item in closed_items if _deal_net_profit(item) > 0])
    losing = len(closed_items) - winning
    closed_count = len(closed_items)
    total_trades = closed_count + max(0, int(open_count or 0))
    win_rate = (winning / closed_count * 100) if closed_count > 0 else 0.0

    return {
        "total_trades": total_trades,
        "closed_trades": closed_count,
        "open_trades": max(0, int(open_count or 0)),
        "winning_trades": winning,
        "losing_trades": losing,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 2),
        "metrics_source": source,
    }


def _summarize_db_trade_models(trades: Sequence[Trade], open_count: int = 0, source: str = "db") -> Dict[str, Any]:
    closed_trades = [trade for trade in trades if trade.close_time is not None]
    total_pnl = sum(float((trade.profit if trade.profit is not None else trade.pnl) or 0) for trade in closed_trades)
    winning = len([trade for trade in closed_trades if float((trade.profit if trade.profit is not None else trade.pnl) or 0) > 0])
    losing = len(closed_trades) - winning
    closed_count = len(closed_trades)
    total_trades = closed_count + max(0, int(open_count or 0))
    win_rate = (winning / closed_count * 100) if closed_count > 0 else 0.0

    return {
        "total_trades": total_trades,
        "closed_trades": closed_count,
        "open_trades": max(0, int(open_count or 0)),
        "winning_trades": winning,
        "losing_trades": losing,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 2),
        "metrics_source": source,
    }


def _group_db_trades_by_bot(trades: Sequence[Trade]) -> Dict[int, List[Trade]]:
    grouped: Dict[int, List[Trade]] = defaultdict(list)
    for trade in trades:
        if trade.bot_id is None:
            continue
        grouped[int(trade.bot_id)].append(trade)
    return grouped


def _group_live_deals_by_magic(deals: Sequence[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for deal in deals:
        magic = _safe_int(deal.get("magic"))
        if magic is None:
            continue
        grouped[magic].append(deal)
    return grouped


def _group_live_positions_by_magic(positions: Sequence[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for position in positions:
        magic = _safe_int(position.get("magic"))
        if magic is None:
            continue
        grouped[magic].append(position)
    return grouped


async def collect_bot_metrics(db: Session, bots: Sequence[Bot]) -> Dict[int, Dict[str, Any]]:
    if not bots:
        return {}

    now = datetime.now()
    earliest_created_at = min((_normalize_datetime(bot.created_at) for bot in bots), default=now - timedelta(days=365))
    start_date = min(earliest_created_at, now - timedelta(days=365 * 3))

    positions_task = mt5_client.get_positions()
    deals_task = mt5_client.get_history_deals(start_date, now)
    positions, deals = await asyncio.gather(positions_task, deals_task)

    positions = positions or []
    deals = deals or []

    live_positions_by_magic = _group_live_positions_by_magic(positions)
    live_deals_by_magic = _group_live_deals_by_magic(deals)

    bot_ids = [int(bot.id) for bot in bots if bot.id is not None]
    db_closed_trades = (
        db.query(Trade)
        .filter(Trade.bot_id.in_(bot_ids), Trade.close_time.isnot(None))
        .all()
        if bot_ids
        else []
    )
    db_open_trades = (
        db.query(Trade)
        .filter(Trade.bot_id.in_(bot_ids), Trade.close_time.is_(None))
        .all()
        if bot_ids
        else []
    )
    db_closed_by_bot = _group_db_trades_by_bot(db_closed_trades)
    db_open_count_by_bot = Counter(trade.bot_id for trade in db_open_trades if trade.bot_id is not None)

    metrics: Dict[int, Dict[str, Any]] = {}

    for bot in bots:
        bot_magic = _safe_int(bot.magic_number)
        bot_live_deals = live_deals_by_magic.get(bot_magic, []) if bot_magic is not None else []
        bot_live_open_positions = live_positions_by_magic.get(bot_magic, []) if bot_magic is not None else []

        if bot_live_deals:
            summary = _summarize_closed_items(
                bot_live_deals,
                open_count=len(bot_live_open_positions),
                source="mt5_live",
            )
        else:
            summary = _summarize_db_trade_models(
                db_closed_by_bot.get(int(bot.id), []),
                open_count=db_open_count_by_bot.get(int(bot.id), 0),
                source="db",
            )

        summary["metrics_updated_at"] = now.isoformat()
        metrics[int(bot.id)] = summary

    return metrics
