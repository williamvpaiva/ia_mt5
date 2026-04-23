from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...services.dashboard_snapshot_service import build_dashboard_snapshot


router = APIRouter()


def _parse_bot_ids(websocket: WebSocket) -> list[int]:
    raw_values = websocket.query_params.getlist("bot_ids")
    bot_ids: list[int] = []
    for raw_value in raw_values:
        for token in str(raw_value).split(","):
            token = token.strip()
            if not token:
                continue
            try:
                bot_id = int(token)
            except ValueError:
                continue
            if bot_id not in bot_ids:
                bot_ids.append(bot_id)
    return bot_ids


@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    bot_ids = _parse_bot_ids(websocket)

    try:
        while True:
            snapshot = await build_dashboard_snapshot(bot_ids=bot_ids)
            await websocket.send_json({
                "type": "dashboard_snapshot",
                "data": snapshot,
            })
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
