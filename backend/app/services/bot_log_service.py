from __future__ import annotations

import logging
import json
from copy import deepcopy
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.system_event import AutomationLog


logger = logging.getLogger("BotLogService")


def _parse_details(details: Any) -> Dict[str, Any]:
    if details is None:
        return {}
    if isinstance(details, dict):
        return deepcopy(details)
    if isinstance(details, str):
        raw = details.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        except Exception:
            return {"raw": raw}
    return {"value": details}


def _safe_json(details: Any) -> Optional[str]:
    payload = _parse_details(details)
    if not payload:
        return None
    return json.dumps(payload, ensure_ascii=False, default=str)


def write_bot_log(
    *,
    level: str,
    context: str,
    message: str,
    details: Any = None,
    db: Optional[Session] = None,
) -> int:
    session = db or SessionLocal()
    close_session = db is None
    try:
        record = AutomationLog(
            level=(level or "INFO").upper(),
            context=context or "general",
            message=message,
            details=_safe_json(details),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return int(record.id)
    except Exception as exc:
        session.rollback()
        logger.error("Failed to persist bot log (%s/%s): %s", level, context, exc)
        return 0
    finally:
        if close_session:
            session.close()


def serialize_log_entry(entry: AutomationLog) -> Dict[str, Any]:
    details = _parse_details(entry.details)
    bot_id = details.get("bot_id")
    bot_name = details.get("bot_name")
    signal = details.get("signal")
    if signal is None and "final_signal" in details:
        signal = details.get("final_signal")
    decision = details.get("decision")
    if signal is None and decision is not None:
        signal = decision
    if decision is None and signal is not None:
        decision = signal

    return {
        "id": entry.id,
        "level": entry.level,
        "context": entry.context,
        "message": entry.message,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "details": details,
        "bot_id": bot_id,
        "bot_name": bot_name,
        "symbol": details.get("symbol"),
        "timeframe": details.get("timeframe"),
        "action": details.get("action"),
        "signal": signal,
        "decision": decision,
        "market_state": details.get("market_state") or details.get("market_bias"),
        "accepted": details.get("accepted"),
        "reason": details.get("reason") or details.get("entry_block_reason"),
        "entry_block_reason": details.get("entry_block_reason"),
        "technical_summary": details.get("technical_summary"),
        "market_summary": details.get("market_summary"),
        "pnl": details.get("pnl"),
    }


def _log_matches(entry: Dict[str, Any], bot_id: Optional[int], context: Optional[str], level: Optional[str], query: Optional[str]) -> bool:
    if bot_id is not None and str(entry.get("bot_id")) != str(bot_id):
        return False
    if context and entry.get("context") != context:
        return False
    if level and str(entry.get("level", "")).upper() != str(level).upper():
        return False
    if query:
        haystack = " ".join(
            str(entry.get(field) or "")
            for field in ("message", "context", "bot_name", "symbol", "reason", "market_state", "action")
        ).lower()
        if query.lower() not in haystack:
            return False
    return True


def get_bot_logs(
    db: Session,
    *,
    bot_id: Optional[int] = None,
    context: Optional[str] = None,
    level: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    raw_limit = max(1, min(int(limit or 200), 500))
    rows = (
        db.query(AutomationLog)
        .order_by(desc(AutomationLog.timestamp))
        .limit(raw_limit * 4)
        .all()
    )

    items: List[Dict[str, Any]] = []
    for row in rows:
        entry = serialize_log_entry(row)
        if _log_matches(entry, bot_id, context, level, query):
            items.append(entry)
        if len(items) >= raw_limit:
            break

    accepted = sum(1 for item in items if bool(item.get("accepted")))
    rejected = sum(1 for item in items if item.get("accepted") is False)
    signal_logs = sum(1 for item in items if item.get("context") in {"signal", "trade_accept", "trade_block", "trade_close", "dynamic_stop"})
    train_logs = sum(1 for item in items if item.get("context") == "train")
    sync_logs = sum(1 for item in items if item.get("context") == "sync")
    market_logs = sum(1 for item in items if item.get("context") in {"market", "signal", "dynamic_stop"})

    latest = items[0] if items else None
    latest_market = None
    for item in items:
        if item.get("market_state") or item.get("signal") or item.get("context") == "dynamic_stop":
            latest_market = item
            break

    return {
        "items": items,
        "summary": {
            "total": len(items),
            "accepted": accepted,
            "rejected": rejected,
            "signal_logs": signal_logs,
            "train_logs": train_logs,
            "sync_logs": sync_logs,
            "market_logs": market_logs,
            "latest_timestamp": latest.get("timestamp") if latest else None,
            "latest_market": latest_market,
        },
    }
