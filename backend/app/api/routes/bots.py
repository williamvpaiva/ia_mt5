import logging
from copy import deepcopy
from datetime import time
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.bot import Bot
from ...schemas.bot import BotCreate, BotResponse, BotUpdate
from ...services.bot_log_service import get_bot_logs, write_bot_log
from ...services.bot_manager import TradingSchedule, bot_manager
from ...services.data_collector import data_collector
from ...services.progress_manager import progress_manager
from ...services.trainer import trainer

logger = logging.getLogger("BotsRoute")

router = APIRouter()


def _clone_value(value):
    if value is None:
        return None
    return deepcopy(value)


def _unique_name(db: Session, base_name: str) -> str:
    candidate = (base_name or "Bot").strip()
    if not db.query(Bot).filter(Bot.name == candidate).first():
        return candidate

    suffix = 2
    while suffix < 1000:
        next_name = f"{candidate} {suffix}"
        if not db.query(Bot).filter(Bot.name == next_name).first():
            return next_name
        suffix += 1

    return f"{candidate} {suffix}"


def _unique_magic_number(db: Session, preferred: int) -> int:
    magic = max(100000, int(preferred or 0))
    existing = {row[0] for row in db.query(Bot.magic_number).all() if row[0] is not None}
    while magic in existing:
        magic += 1
        if magic > 99999999:
            magic = 100000
    return magic


@router.get("/logs")
def list_bot_logs(
    bot_id: Optional[int] = Query(None, ge=1),
    context: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Texto livre para busca"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return get_bot_logs(db, bot_id=bot_id, context=context, level=level, query=q, limit=limit)


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
        raise HTTPException(status_code=400, detail=f"Erro ao criar robo: {e}")
    db.refresh(new_bot)
    write_bot_log(
        level="INFO",
        context="bot_admin",
        message=f"Robo criado: {new_bot.name}",
        details={
            "action": "create",
            "bot_id": new_bot.id,
            "bot_name": new_bot.name,
            "symbol": new_bot.symbol,
            "timeframe": new_bot.timeframe,
            "magic_number": new_bot.magic_number,
        },
    )
    return new_bot


@router.put("/{bot_id}", response_model=BotResponse)
def update_bot(bot_id: int, bot_update: BotUpdate, db: Session = Depends(get_db)):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="Robo nao encontrado")

    update_data = bot_update.model_dump(exclude_unset=True)
    original_values = {key: getattr(db_bot, key, None) for key in update_data.keys()}

    if "magic_number" in update_data:
        magic_number = update_data["magic_number"]
        if magic_number is None:
            raise HTTPException(status_code=400, detail="Magic number nao pode ficar vazio")
        if int(magic_number) <= 0:
            raise HTTPException(status_code=400, detail="Magic number invalido")

        conflict = (
            db.query(Bot.id)
            .filter(Bot.magic_number == int(magic_number), Bot.id != bot_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="Magic number ja esta em uso por outro robo")

    for key, value in update_data.items():
        setattr(db_bot, key, value)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Nao foi possivel salvar as configuracoes do robo. Verifique se o Magic Number ja esta em uso.",
        ) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar robo: {e}") from e

    db.refresh(db_bot)

    changed_values = {
        key: {"before": original_values.get(key), "after": getattr(db_bot, key, None)}
        for key in update_data.keys()
        if original_values.get(key) != getattr(db_bot, key, None)
    }
    if changed_values:
        write_bot_log(
            level="INFO",
            context="bot_admin",
            message=f"Robo atualizado: {db_bot.name}",
            details={
                "action": "update",
                "bot_id": db_bot.id,
                "bot_name": db_bot.name,
                "changes": changed_values,
            },
        )

    if db_bot.active:
        schedule = None
        if db_bot.trading_schedule:
            try:
                ts = db_bot.trading_schedule
                schedule = TradingSchedule(
                    enabled=ts.get("enabled", True),
                    start_time=time.fromisoformat(ts.get("start_time", db_bot.start_time or "09:00")),
                    end_time=time.fromisoformat(ts.get("end_time", db_bot.end_time or "17:50")),
                    trading_days=ts.get("trading_days", [0, 1, 2, 3, 4, 5, 6]),
                )
            except Exception as e:
                logger.warning("Falha ao sincronizar schedule do bot %s: %s", db_bot.id, e)

        if schedule is None and db_bot.start_time and db_bot.end_time:
            try:
                schedule = TradingSchedule(
                    enabled=True,
                    start_time=time.fromisoformat(db_bot.start_time),
                    end_time=time.fromisoformat(db_bot.end_time),
                    trading_days=[0, 1, 2, 3, 4, 5, 6],
                )
            except Exception as e:
                logger.warning("Falha ao criar schedule legado do bot %s: %s", db_bot.id, e)

        if schedule is not None:
            bot_manager.set_trading_schedule(db_bot.id, schedule)

    return db_bot


@router.delete("/{bot_id}")
def delete_bot(bot_id: int, db: Session = Depends(get_db)):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="Robo nao encontrado")

    write_bot_log(
        level="INFO",
        context="bot_admin",
        message=f"Robo removido: {db_bot.name}",
        details={
            "action": "delete",
            "bot_id": db_bot.id,
            "bot_name": db_bot.name,
            "symbol": db_bot.symbol,
            "timeframe": db_bot.timeframe,
            "magic_number": db_bot.magic_number,
        },
    )

    db.delete(db_bot)
    db.commit()
    return {"status": "deleted", "bot_id": bot_id}


@router.post("/{bot_id}/clone", response_model=BotResponse, status_code=201)
def clone_bot(bot_id: int, db: Session = Depends(get_db)):
    source = db.query(Bot).filter(Bot.id == bot_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Robo nao encontrado")

    cloned_bot = Bot(
        name=_unique_name(db, f"{source.name} - Copia"),
        symbol=source.symbol,
        timeframe=source.timeframe,
        active=False,
        magic_number=_unique_magic_number(db, int(source.magic_number or 0) + 1),
        config=_clone_value(source.config),
        max_spread=source.max_spread,
        max_slippage=source.max_slippage,
        allowed_symbols=_clone_value(source.allowed_symbols) or [],
        trading_schedule=_clone_value(source.trading_schedule),
        excluded_days=_clone_value(source.excluded_days) or [],
        start_time=source.start_time,
        end_time=source.end_time,
        signals_config=_clone_value(source.signals_config),
        risk_config=_clone_value(source.risk_config),
        ai_config=_clone_value(source.ai_config),
        spy_config=_clone_value(source.spy_config),
        last_run=source.last_run,
        last_error=source.last_error,
        total_trades=source.total_trades,
        winning_trades=source.winning_trades,
        losing_trades=source.losing_trades,
        total_pnl=source.total_pnl,
    )

    db.add(cloned_bot)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erro ao clonar robo: {e}")

    db.refresh(cloned_bot)
    write_bot_log(
        level="INFO",
        context="bot_admin",
        message=f"Robo clonado: {source.name} -> {cloned_bot.name}",
        details={
            "action": "clone",
            "source_bot_id": source.id,
            "source_bot_name": source.name,
            "bot_id": cloned_bot.id,
            "bot_name": cloned_bot.name,
            "symbol": cloned_bot.symbol,
            "timeframe": cloned_bot.timeframe,
            "magic_number": cloned_bot.magic_number,
        },
    )
    return cloned_bot


@router.post("/{bot_id}/start")
async def start_bot(bot_id: int, db: Session = Depends(get_db)):
    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not db_bot:
        raise HTTPException(status_code=404, detail="Robo nao encontrado")

    from ...services.bot_manager import TradingSchedule

    schedule = None
    if db_bot.trading_schedule:
        try:
            ts = db_bot.trading_schedule
            schedule = TradingSchedule(
                enabled=ts.get("enabled", True),
                start_time=time.fromisoformat(ts.get("start_time", "09:00")),
                end_time=time.fromisoformat(ts.get("end_time", "17:00")),
                trading_days=ts.get("trading_days", [1, 2, 3, 4, 5]),
            )
        except Exception as e:
            logger.warning("Falha ao parsear schedule do bot %s: %s", bot_id, e)

    success = await bot_manager.start_bot(bot_id, trading_schedule=schedule)
    if not success:
        raise HTTPException(status_code=400, detail="Falha ao iniciar robo")

    db_bot.active = True
    db.commit()

    write_bot_log(
        level="INFO",
        context="bot_admin",
        message=f"Robo iniciado: {db_bot.name}",
        details={
            "action": "start",
            "bot_id": db_bot.id,
            "bot_name": db_bot.name,
            "symbol": db_bot.symbol,
            "timeframe": db_bot.timeframe,
            "magic_number": db_bot.magic_number,
        },
    )

    return {"status": "started", "bot_id": bot_id}


@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: int, db: Session = Depends(get_db)):
    success = await bot_manager.stop_bot(bot_id)
    if not success:
        raise HTTPException(status_code=400, detail="Falha ao parar robo")

    db_bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if db_bot:
        db_bot.active = False
        db.commit()

        write_bot_log(
            level="INFO",
            context="bot_admin",
            message=f"Robo parado: {db_bot.name}",
            details={
                "action": "stop",
                "bot_id": db_bot.id,
                "bot_name": db_bot.name,
                "symbol": db_bot.symbol,
                "timeframe": db_bot.timeframe,
                "magic_number": db_bot.magic_number,
            },
        )

    return {"status": "stopped", "bot_id": bot_id}


@router.post("/{bot_id}/train")
async def train_bot(bot_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Iniciar treinamento da IA em background."""
    print(f"DEBUG: Recebida requisicao de TREINO para bot {bot_id}")
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Robo nao encontrado")

    progress_manager.update_progress(bot_id, "train", 1, "Fila de treinamento...")
    write_bot_log(
        level="INFO",
        context="train",
        message=f"Treinamento enfileirado para {bot.name}",
        details={
            "action": "train_queue",
            "bot_id": bot.id,
            "bot_name": bot.name,
            "symbol": bot.symbol,
            "timeframe": bot.timeframe,
        },
    )
    background_tasks.add_task(trainer.train_bot, bot_id=bot_id)
    return {"status": "training_started", "bot_id": bot_id}


@router.post("/{bot_id}/sync")
async def sync_bot_data(bot_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Forcar sincronizacao de dados historicos."""
    print(f"DEBUG: Recebida requisicao de SYNC para bot {bot_id}")
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Robo nao encontrado")

    progress_manager.update_progress(bot_id, "sync", 1, "Fila de sincronizacao...")
    write_bot_log(
        level="INFO",
        context="sync",
        message=f"Sincronizacao enfileirada para {bot.name}",
        details={
            "action": "sync_queue",
            "bot_id": bot.id,
            "bot_name": bot.name,
            "symbol": bot.symbol,
            "timeframe": bot.timeframe,
        },
    )
    background_tasks.add_task(data_collector.sync_data, count=2000, force=True, bot_id=bot_id)
    return {"status": "sync_started", "bot_id": bot_id}


@router.get("/progress")
def get_bots_progress():
    return progress_manager.get_all_progress()
