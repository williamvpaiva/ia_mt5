from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...services.dashboard_service import build_dashboard_snapshot


router = APIRouter()


@router.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            snapshot = await build_dashboard_snapshot()
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
