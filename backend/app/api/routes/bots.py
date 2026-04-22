from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from ...core.database import get_db
from ...models.bot import Bot
from ...schemas.bot import BotCreate, BotUpdate, BotResponse
from ...services.bot_manager import bot_manager
from ...services.data_collector import data_collector

router = APIRouter()

@router.get("/", response_model=List[BotResponse])
def list_bots(db: Session = Depends(get_db)):
    return db.query(Bot).all()

@router.post("/", response_model=BotResponse)
def create_bot(bot: BotCreate, db: Session = Depends(get_db)):
    new_bot = Bot(**bot.model_dump())
    db.add(new_bot)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao criar robA?: {e}")
    db.refresh(new_bot)
    return new_bot

@router.put("/{bot_id}", response_model=BotResponse)
def update_bot(bot_id: int, bot_update: BotUpdate, db: Session = Depends(get_db)):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="RobA? nA?o encontrado")
    
    update_data = bot_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_bot, key, value)
    
    db.commit()
    db.refresh(db_bot)
    return db_bot

@router.delete("/{bot_id}")
def delete_bot(bot_id: int, db: Session = Depends(get_db)):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="RobA? nA?o encontrado")
    
    db.delete(db_bot)
    db.commit()
    return {"status": "deleted", "bot_id": bot_id}

from datetime import time

@router.post("/{bot_id}/start")
async def start_bot(bot_id: int, db: Session = Depends(get_db)):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="RobA? nA?o encontrado")
    
    from ...services.bot_manager import TradingSchedule
    
    # Carrega schedule se existir no JSON do bot
    schedule = None
    if db_bot.trading_schedule:
        try:
            ts = db_bot.trading_schedule
            schedule = TradingSchedule(
                enabled=ts.get('enabled', True),
                start_time=time.fromisoformat(ts.get('start_time', '09:00')),
                end_time=time.fromisoformat(ts.get('end_time', '17:00')),
                trading_days=ts.get('trading_days', [1,2,3,4,5])
            )
        except Exception as e:
            logger.warning(f"Falha ao parsear schedule do bot {bot_id}: {e}")

    success = await bot_manager.start_bot(bot_id, trading_schedule=schedule)
    if not success:
        raise HTTPException(status_code=400, detail="Falha ao iniciar robA?")
    
    db_bot.active = True
    db.commit()
    
    return {"status": "started", "bot_id": bot_id}

@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: int, db: Session = Depends(get_db)):
    success = await bot_manager.stop_bot(bot_id)
    if not success:
        raise HTTPException(status_code=400, detail="Falha ao parar robA?")
    
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if db_bot:
        db_bot.active = False
        db.commit()
        
    return {"status": "stopped", "bot_id": bot_id}

from ...services.trainer import trainer

@router.post("/{bot_id}/train")
async def train_bot(bot_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Iniciar treinamento da IA em background"""
    print(f"DEBUG: Recebida requisiA?A?o de TREINO para bot {bot_id}")
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="RobA? nA?o encontrado")
    
    # Adiciona tarefa de treinamento em background
    background_tasks.add_task(trainer.train_bot, bot_id=bot_id)
    return {"status": "training_started", "bot_id": bot_id}

@router.post("/{bot_id}/sync")
async def sync_bot_data(bot_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """ForA?ar sincronizaA?A?o de dados histA?ricos"""
    print(f"DEBUG: Recebida requisiA?A?o de SYNC para bot {bot_id}")
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="RobA? nA?o encontrado")
    
    # Dispara sincronizaA?A?o incremental
    background_tasks.add_task(data_collector.sync_data, count=2000, force=True, bot_id=bot_id)
    return {"status": "sync_started", "bot_id": bot_id}

from ...services.progress_manager import progress_manager

@router.get("/progress")
def get_bots_progress():
    return progress_manager.get_all_progress()
