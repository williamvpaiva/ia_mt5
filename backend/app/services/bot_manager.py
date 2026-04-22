"""
Bot Manager
CorreA?A?o: Adicionado TradingSchedule e verificaA?A?o de horA?rios de trading
Prioridade: MA?DIA
"""
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, time, timedelta
from dataclasses import dataclass

from ..core.database import SessionLocal
from ..models.bot import Bot
from .trading_bot import TradingBotInstance
from .mt5_client import mt5_client

logger = logging.getLogger("BotManager")


@dataclass
class TradingSchedule:
    """ConfiguraA?A?o de horA?rios de trading"""
    enabled: bool = True
    start_time: time = time(9, 0)  # 09:00
    end_time: time = time(17, 0)  # 17:00
    trading_days: List[int] = None  # [1, 2, 3, 4, 5] = Seg-Sex
    timezone: str = "America/Sao_Paulo"
    
    def __post_init__(self):
        if self.trading_days is None:
            self.trading_days = [1, 2, 3, 4, 5]  # Segunda a Sexta
    
    def is_trading_time(self, current_time: Optional[datetime] = None) -> bool:
        """Verificar se estA? dentro do horA?rio de trading"""
        if not self.enabled:
            return True  # Sem restriA?A?es

        now = current_time or datetime.now()
        current_day = (now.weekday() + 1) % 7

        # Verificar dia da semana
        if current_day not in self.trading_days:
            return False

        # Verificar horA?rio
        current = now.time()
        if self.start_time <= self.end_time:
            # Mesmo dia (ex: 09:00 - 17:00)
            return self.start_time <= current <= self.end_time
        else:
            # Passa da meia-noite (ex: 22:00 - 06:00)
            return current >= self.start_time or current <= self.end_time
    
    def time_until_next_session(self) -> timedelta:
        """Tempo atA? a prA?xima sessA?o de trading"""
        now = datetime.now()
        current_day = (now.weekday() + 1) % 7

        # Se estamos em dia de trading e antes do horA?rio de inA?cio
        if current_day in self.trading_days:
            if now.time() < self.start_time:
                next_start = datetime.combine(now.date(), self.start_time)
                return next_start - now

        # Encontrar prA?ximo dia de trading
        days_ahead = 1
        while days_ahead <= 7:
            next_date = now + timedelta(days=days_ahead)
            next_day = (next_date.weekday() + 1) % 7
            if next_day in self.trading_days:
                next_start = datetime.combine(next_date.date(), self.start_time)
                return next_start - now
            days_ahead += 1
        
        return timedelta(hours=24)  # Default


class BotManager:
    """Gerenciador de bots com verificaA?A?o de horA?rios"""
    
    def __init__(self):
        self.active_bots: Dict[int, TradingBotInstance] = {}
        self.tasks: Dict[int, asyncio.Task] = {}
        self.trading_schedules: Dict[int, TradingSchedule] = {}
        self.trading_paused: Dict[int, bool] = {}
        self.pause_until: Dict[int, datetime] = {}
        self.pause_reasons: Dict[int, str] = {}
        logger.info("BotManager inicializado com TradingSchedule")
    
    def set_trading_schedule(self, bot_id: int, schedule: TradingSchedule):
        """Configurar horA?rio de trading para um bot"""
        self.trading_schedules[bot_id] = schedule
        logger.info(f"Trading schedule configurado para bot {bot_id}: {schedule.start_time}-{schedule.end_time}")
    
    def get_trading_schedule(self, bot_id: int) -> Optional[TradingSchedule]:
        """Obter horA?rio de trading de um bot"""
        return self.trading_schedules.get(bot_id)

    def _schedule_from_bot(self, bot: Bot) -> Optional[TradingSchedule]:
        """Converter o JSON persistido em TradingSchedule."""
        if not bot.trading_schedule:
            return None

        try:
            ts = bot.trading_schedule
            return TradingSchedule(
                enabled=ts.get("enabled", True),
                start_time=time.fromisoformat(ts.get("start_time", "09:00")),
                end_time=time.fromisoformat(ts.get("end_time", "17:00")),
                trading_days=ts.get("trading_days", [1, 2, 3, 4, 5]),
            )
        except Exception as e:
            logger.warning("Falha ao parsear schedule do bot %s: %s", bot.id, e)
            return None
    
    def can_trade(self, bot_id: int) -> bool:
        """Verificar se o bot pode executar trades no momento"""
        if self.trading_paused.get(bot_id, False):
            pause_until = self.pause_until.get(bot_id)
            if pause_until and datetime.now() >= pause_until:
                self.resume_trading(bot_id)
            else:
                return False
        
        # Verificar horA?rio de trading
        schedule = self.trading_schedules.get(bot_id)
        if schedule:
            return schedule.is_trading_time()
        
        return True  # Sem restriA?A?es
    
    async def start_bot(self, bot_id: int, trading_schedule: Optional[TradingSchedule] = None):
        """Iniciar bot com verificaA?A?o de horA?rios"""
        if bot_id in self.tasks:
            logger.warning(f"Bot {bot_id} jA? estA? em execuA?A?o.")
            return False
        
        # Configurar horA?rio de trading
        if trading_schedule:
            self.set_trading_schedule(bot_id, trading_schedule)
        
        instance = TradingBotInstance(bot_id)
        await instance.load_config()
        self.active_bots[bot_id] = instance
        
        # Cria uma tarefa asyncio para o loop do robA?
        task = asyncio.create_task(self._bot_loop(bot_id, instance))
        self.tasks[bot_id] = task
        
        logger.info(f"Bot {bot_id} iniciado pelo Manager.")
        return True

    async def restore_active_bots(self) -> List[int]:
        """Recriar tarefas para robos marcados como ativos no banco."""
        db = SessionLocal()
        restored: List[int] = []
        try:
            bots = db.query(Bot).filter(Bot.active.is_(True)).all()
            for bot in bots:
                if bot.id in self.tasks:
                    continue

                schedule = self._schedule_from_bot(bot)
                success = await self.start_bot(bot.id, trading_schedule=schedule)
                if success:
                    restored.append(bot.id)
                    logger.info("Bot %s restaurado no startup.", bot.id)
                else:
                    logger.warning("Bot %s nao foi restaurado no startup.", bot.id)
        finally:
            db.close()

        return restored
    
    async def _bot_loop(self, bot_id: int, instance: TradingBotInstance):
        """Loop principal do bot com verificaA?A?o de horA?rios"""
        try:
            while True:
                # Verificar se pode trading
                if self.can_trade(bot_id):
                    # Executar ciclo do bot
                    await instance.run_cycle()
                else:
                    if self.trading_paused.get(bot_id, False):
                        pause_until = self.pause_until.get(bot_id)
                        if pause_until:
                            remaining = (pause_until - datetime.now()).total_seconds()
                            if remaining <= 0:
                                self.resume_trading(bot_id)
                                continue
                            await asyncio.sleep(min(max(remaining, 1.0), 60.0))
                        else:
                            await asyncio.sleep(60)
                    else:
                        schedule = self.trading_schedules.get(bot_id)
                        if schedule:
                            wait_time = schedule.time_until_next_session()
                            logger.info(f"Bot {bot_id} aguardando prA?xima sessA?o: {wait_time}")
                            await asyncio.sleep(min(wait_time.total_seconds(), 60))  # Max 1 min
                
                await asyncio.sleep(5)  # Intervalo entre ciclos
        except asyncio.CancelledError:
            logger.info(f"Loop do bot {bot_id} cancelado.")
            raise
        except Exception as e:
            logger.error(f"Erro no loop do bot {bot_id}: {e}")
    
    async def stop_bot(self, bot_id: int):
        """Parar bot"""
        if bot_id not in self.tasks:
            logger.warning(f"Bot {bot_id} jA? estA? parado ou nA?o foi iniciado.")
            return True
        
        instance = self.active_bots[bot_id]
        magic = instance.magic_number
        
        # --- FECHAR TODAS AS OPERAA?A?ES DESTE ROBA? ---
        try:
            logger.info(f"Limpando operaA?A?es abertas para o Bot {bot_id} (Magic: {magic})")
            positions = await mt5_client.get_positions()
            for pos in positions:
                if pos.get('magic') == magic:
                    logger.info(f"Fechando posiA?A?o {pos['ticket']} do Bot {bot_id}")
                    await mt5_client.close_position(pos['ticket'])
        except Exception as e:
            logger.error(f"Erro ao fechar operaA?A?es do Bot {bot_id} ao parar: {e}")
        # --------------------------------------------

        instance.stop()
        
        task = self.tasks[bot_id]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        del self.tasks[bot_id]
        del self.active_bots[bot_id]
        if bot_id in self.trading_paused:
            del self.trading_paused[bot_id]
        
        logger.info(f"Bot {bot_id} parado e ordens limpas.")
        return True
    
    
    def pause_trading(self, bot_id: int, reason: Optional[str] = None, until: Optional[datetime] = None):
        """Pausar trading temporariamente"""
        self.trading_paused[bot_id] = True
        if reason:
            self.pause_reasons[bot_id] = reason
        if until:
            self.pause_until[bot_id] = until
        logger.info(f"Trading pausado para bot {bot_id}")
    
    def resume_trading(self, bot_id: int):
        """Retomar trading"""
        self.trading_paused[bot_id] = False
        self.pause_reasons.pop(bot_id, None)
        self.pause_until.pop(bot_id, None)
        logger.info(f"Trading retomado para bot {bot_id}")
    
    def get_status(self, bot_id: int) -> Dict:
        """Obter status completo do bot"""
        is_running = bot_id in self.tasks
        schedule = self.trading_schedules.get(bot_id)
        
        status = {
            "bot_id": bot_id,
            "running": is_running,
            "can_trade": self.can_trade(bot_id) if is_running else False,
            "paused": self.trading_paused.get(bot_id, False),
            "pause_reason": self.pause_reasons.get(bot_id),
            "pause_until": self.pause_until.get(bot_id).isoformat() if self.pause_until.get(bot_id) else None,
            "has_schedule": schedule is not None,
        }
        
        if schedule:
            status["schedule"] = {
                "enabled": schedule.enabled,
                "start_time": schedule.start_time.isoformat(),
                "end_time": schedule.end_time.isoformat(),
                "trading_days": schedule.trading_days,
                "in_trading_hours": schedule.is_trading_time()
            }
        
        return status
    
    def get_all_status(self) -> Dict[int, Dict]:
        """Obter status de todos os bots"""
        return {bot_id: self.get_status(bot_id) for bot_id in self.active_bots}


# InstA?ncia Singleton
bot_manager = BotManager()
