from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...core.database import SessionLocal
from ...models.system_event import SystemEvent

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[dict])
async def get_active_events(db: Session = Depends(get_db)):
    """Listar todos os eventos persistentes nA?o lidos"""
    events = db.query(SystemEvent).filter(SystemEvent.is_read == False).order_by(SystemEvent.timestamp.desc()).all()
    return [
        {
            "id": e.id,
            "type": e.type,
            "message": e.message,
            "timestamp": e.timestamp.isoformat(),
            "data": e.data
        } for e in events
    ]

@router.post("/{event_id}/dismiss")
async def dismiss_event(event_id: int, db: Session = Depends(get_db)):
    """Marcar evento como lido / arquivado"""
    event = db.query(SystemEvent).filter(SystemEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.is_read = True
    db.commit()
    return {"success": True}

@router.delete("/clear-all")
async def clear_all_events(db: Session = Depends(get_db)):
    """Limpar todas as notificaA?A?es nA?o lidas"""
    db.query(SystemEvent).filter(SystemEvent.is_read == False).update({SystemEvent.is_read: True})
    db.commit()
    return {"success": True}

@router.post("/trigger")
async def trigger_automation():
    """Gatilho manual para o ciclo de automaA?A?o"""
    from ...services.automation_service import automation_service
    # Executa o ciclo fora do loop principal
    success = await automation_service.execute_automation_cycle()
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao executar ciclo manual. Verifique conectividade.")
    return {"success": True, "message": "Ciclo de integridade concluA?do com sucesso."}
