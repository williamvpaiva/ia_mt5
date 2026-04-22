import asyncio
import logging
import httpx
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.system_event import SystemEvent, AutomationLog
from ..models.bot import Bot
from .data_collector import data_collector
from .trainer import trainer

# ConfiguraA?A?es de Logs Estruturados Rotativos
LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_file = os.path.join(LOG_DIR, "automation.log")
handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[handler, logging.StreamHandler()]
)

logger = logging.getLogger("AutomationService")

class AutomationService:
    def __init__(self, interval_minutes: int = 15):
        self.interval = interval_minutes * 60
        self.is_running = False
        self.max_retries = 5
        self.initial_backoff = 30 # segundos
        self.backoff_factor = 2

    async def check_connectivity(self) -> bool:
        """Verifica se hA? conexA?o com internet bA?sica"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get("http://www.google.com")
                return response.status_code < 400
        except Exception:
            return False

    def log_to_db(self, db: Session, level: str, context: str, msg: str, details: str = None):
        """Salva log no banco para auditoria via UI"""
        try:
            new_log = AutomationLog(
                level=level,
                context=context,
                message=msg,
                details=details
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar log no DB: {e}")

    def create_event(self, db: Session, evt_type: str, message: str, data: dict = None):
        """Cria notificaA?A?o persistente para o Frontend"""
        try:
            # Remove eventos antigos do mesmo tipo que ainda nA?o foram lidos para colapsar
            db.query(SystemEvent).filter(
                SystemEvent.type == evt_type, 
                SystemEvent.is_read == False
            ).delete()
            
            new_evt = SystemEvent(
                type=evt_type,
                message=message,
                data=data,
                persistent=True
            )
            db.add(new_evt)
            db.commit()
        except Exception as e:
            logger.error(f"Erro ao criar evento: {e}")

    async def execute_automation_cycle(self):
        """Executa a sequAancia estrita Sync Delta -> Load Local -> Train"""
        db: Session = SessionLocal()
        logger.info("--- Iniciando Ciclo de AutomaA?A?o ---")
        
        try:
            # 1. Verificar Conectividade (Informativo)
            if not await self.check_connectivity():
                logger.warning("VerificaA?A?o de internet externa falhou. Prosseguindo com tentativa local...")
                # NA?o retornamos False aqui para permitir que o Sync tente falar com o Bridge

            # 2. Orquestrar para todos os bots ativos
            bots = db.query(Bot).all()
            total_new_global = 0

            for bot in bots:
                logger.info(f"Processando Bot: {bot.name}")
                
                # Passo A: Sync Delta
                data_collector.symbol = bot.config.get('symbol', 'WIN$')
                data_collector.timeframe = bot.config.get('timeframe', 'M5')
                
                sync_res = await data_collector.sync_data(incremental=True)
                new_records = sync_res.get('new_records', 0)

                if new_records > 0:
                    total_new_global += new_records
                    logger.info(f"[SYNC] {new_records} novos dados para {bot.name}")
                    
                    # Passo B e C: Load Local -> Train (Garantido apA?s sync OK com dados)
                    logger.info(f"[TRAIN] Iniciando treinamento para {bot.name}...")
                    train_res = await trainer.train_bot(bot.id)
                    
                    if train_res.get('success'):
                        timestamp = datetime.now().strftime("%H:%M")
                        self.create_event(db, "SYNC_TRAIN_SUCCESS", 
                            f"IntegraA?A?o ConcluA?da ({bot.name}): {new_records} novos dados A?s {timestamp}. Clique para arquivar.",
                            {"bot_id": bot.id, "new_records": new_records, "time": timestamp}
                        )
                        self.log_to_db(db, "INFO", "automation", f"Ciclo Completo com Sucesso: {bot.name}")
                else:
                    logger.debug(f"Sem novos dados para {bot.name}. Treinamento pulado.")

            return True

        except Exception as e:
            logger.error(f"Erro fatal no ciclo de automaA?A?o: {e}")
            self.log_to_db(db, "ERROR", "automation", str(e))
            return False
        finally:
            db.close()

    async def start(self):
        """Loop principal com backoff exponencial"""
        self.is_running = True
        logger.info(f"ServiA?o de AutomaA?A?o Iniciado (Intervalo: {self.interval/60} min)")

        while self.is_running:
            success = False
            for attempt in range(1, self.max_retries + 1):
                success = await self.execute_automation_cycle()
                
                if success:
                    break
                
                # Se falhou, aplica backoff
                wait_time = self.initial_backoff * (self.backoff_factor ** (attempt - 1))
                logger.warning(f"Tentativa {attempt}/{self.max_retries} falhou. Aguardando {wait_time}s...")
                await asyncio.sleep(wait_time)

            if not success:
                logger.error("Falha persistente apA?s 5 tentativas. Aguardando prA?ximo ciclo de 15min.")

            # Aguardar prA?ximo intervalo configurado
            await asyncio.sleep(self.interval)

    def stop(self):
        self.is_running = False
        logger.info("ServiA?o de AutomaA?A?o parado.")

# InstA?ncia Singleton
automation_service = AutomationService()
