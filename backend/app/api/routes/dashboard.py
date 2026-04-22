from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services.dashboard_service import build_dashboard_snapshot


router = APIRouter()


@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """
    Retorna o snapshot vivo do dashboard.
    O db dependency é mantido para compatibilidade com o router.
    """
    _ = db
    return await build_dashboard_snapshot()


@router.get("/live")
async def get_live_dashboard(db: Session = Depends(get_db)):
    """
    Snapshot completo usado pelo frontend em tempo real.
    """
    _ = db
    return await build_dashboard_snapshot()
