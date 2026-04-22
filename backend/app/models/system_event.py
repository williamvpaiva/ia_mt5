from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from ..core.database import Base
from datetime import datetime

class SystemEvent(Base):
    """
    Eventos persistentes para notificaA?A?o do usuA?rio no Frontend.
    """
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String) # 'SYNC_SUCCESS', 'TRAINING_COMPLETE', 'AUTO_FAILURE'
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    data = Column(JSON, nullable=True) # Metadados adicionais (ex: symbol, new_records)
    is_read = Column(Boolean, default=False)
    persistent = Column(Boolean, default=True) # Se deve ficar visA?vel atA? clique

class AutomationLog(Base):
    """
    Log estruturado para auditoria interna da automaA?A?o (alA?m do arquivo de log)
    """
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String) # INFO, WARN, ERROR
    context = Column(String) # sync, train, connectivity
    message = Column(String)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
