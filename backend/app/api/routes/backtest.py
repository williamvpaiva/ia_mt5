from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from ...core.database import SessionLocal
from ...models.backtest import Backtest
from ...services.backtest_service import backtest_service

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class BacktestRequest(BaseModel):
    bot_id: int
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float = 10000.0

@router.post("/run")
async def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    """Executa um novo backtest baseado em parA?metros personalizados"""
    print(f"\n[BACKTEST_DEBUG] Iniciando simulaA?A?o para Bot ID: {req.bot_id}")
    print(f"[BACKTEST_DEBUG] ParA?metros: {req.dict()}")
    try:
        result = await backtest_service.run_backtest(req.dict(), db)
        
        if "error" in result:
            print(f"[BACKTEST_DEBUG] Erro no serviA?o: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
            
        print(f"[BACKTEST_DEBUG] SimulaA?A?o concluA?da e gravada (ID: {result.get('id')})")
        return result
    except Exception as e:
        print(f"[BACKTEST_DEBUG] EXCEA?A?O CRA?TICA: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_backtests(db: Session = Depends(get_db)):
    """Lista o histA?rico de backtests realizados com nomes dos robA?s"""
    from ...models.bot import Bot
    results = db.query(Backtest, Bot.name).join(Bot, Backtest.bot_id == Bot.id).order_by(Backtest.timestamp.desc()).limit(20).all()
    
    return [
        {
            **json.loads(json.dumps(bt.__dict__, default=str)),
            "bot_name": name
        } for bt, name in results
    ]

import json

@router.get("/{backtest_id}")
async def get_backtest_details(backtest_id: int, db: Session = Depends(get_db)):
    """ObtA?m o relatA?rio completo de um backtest especA?fico"""
    bt = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest nA?o encontrado")
    return bt
