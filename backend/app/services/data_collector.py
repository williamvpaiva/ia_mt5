"""
Data Collector
CorreA?A?o: Intervalo de sincronizaA?A?o configurA?vel por timeframe
Prioridade: MA?DIA
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy.orm import Session

from .mt5_client import mt5_client
from ..models.historical_data import HistoricalData
from ..core.database import SessionLocal
from .bot_log_service import write_bot_log
from .progress_manager import progress_manager

logger = logging.getLogger("DataCollector")


# ConfiguraA?A?o de intervalos por timeframe
TIMEFRAME_INTERVALS: Dict[str, int] = {
    "M1": 60,      # 1 minuto
    "M5": 300,     # 5 minutos
    "M15": 900,    # 15 minutos
    "M30": 1800,   # 30 minutos
    "H1": 3600,    # 1 hora
    "H4": 14400,   # 4 horas
    "D1": 86400,   # 1 dia
    "W1": 604800,  # 1 semana
    "MN1": 2592000 # 1 mAas
}

# Cache local para reduzir chamadas
class DataCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Dict]:
        if key in self.cache:
            if datetime.now().timestamp() - self.cache[key]['timestamp'] < self.ttl:
                return self.cache[key]['data']
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Dict):
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now().timestamp()
        }
    
    def clear(self):
        self.cache.clear()


class DataCollector:
    """
    Coletor de dados histA?ricos com intervalo configurA?vel
    CorreA?A?o: Intervalo baseado no timeframe e cache local
    """
    
    def __init__(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        sync_interval: Optional[int] = None,
        cache_ttl: int = 300
    ):
        self.symbol = symbol or os.getenv("COLLECTOR_SYMBOL", "WIN$")
        self.timeframe = timeframe or os.getenv("COLLECTOR_TIMEFRAME", "M5")
        
        # Intervalo baseado no timeframe (configurA?vel)
        if sync_interval:
            self.sync_interval = sync_interval
        else:
            # Intervalo padrA?o = 10x o timeframe (mA?nimo 60s, mA?ximo 1 hora)
            base_interval = TIMEFRAME_INTERVALS.get(timeframe, 300)
            self.sync_interval = min(max(base_interval, 60), 3600)
        
        self.is_running = False
        self.cache = DataCache(cache_ttl)
        self.records_processed = 0
        self.last_sync = None
        
        logger.info(f"DataCollector inicializado: {symbol} {timeframe} (intervalo: {self.sync_interval}s)")
    
    def get_sync_interval(self) -> int:
        """Obter intervalo de sincronizaA?A?o atual"""
        return self.sync_interval
    
    def set_sync_interval(self, interval: int):
        """Configurar novo intervalo de sincronizaA?A?o"""
        self.sync_interval = max(60, interval)  # MA?nimo 60 segundos
        logger.info(f"Intervalo de sincronizaA?A?o alterado para {self.sync_interval}s")
    
    def get_timeframe_multiplier(self) -> int:
        """Obter multiplicador do timeframe em minutos"""
        tf_map = {
            "M1": 1, "M5": 5, "M15": 15, "M30": 30,
            "H1": 60, "H4": 240, "D1": 1440,
            "W1": 10080, "MN1": 43200
        }
        return tf_map.get(self.timeframe, 5)
    
    def get_last_timestamp(self, db: Session, symbol: str, timeframe: str) -> Optional[datetime]:
        """Obter o timestamp do Aoltimo registro no banco para este sA?mbolo/timeframe"""
        last_record = db.query(HistoricalData).filter(
            HistoricalData.symbol == symbol,
            HistoricalData.timeframe == timeframe
        ).order_by(HistoricalData.time.desc()).first()
        return last_record.time if last_record else None

    async def sync_data(self, count: Optional[int] = None, force: bool = False, incremental: bool = True, bot_id: Optional[int] = None) -> Dict:
        """
        Sincronizar dados histA?ricos de forma inteligente (incremental por padrA?o)
        """
        start_time = datetime.now()
        db: Session = SessionLocal()
        
        try:
            # Se for incremental, calcula quanto falta
            if incremental and not force:
                last_ts = self.get_last_timestamp(db, self.symbol, self.timeframe)
                if last_ts:
                    # Calcula diferenA?a em minutos
                    diff_minutes = (datetime.now() - last_ts).total_seconds() / 60
                    tf_mult = self.get_timeframe_multiplier()
                    needed_count = int(diff_minutes / tf_mult) + 1 # +1 para seguranA?a de overlap
                    
                    if needed_count <= 1:
                        logger.debug(f"Base local jA? estA? atualizada para {self.symbol} {self.timeframe}")
                        return {"success": True, "new_records": 0, "message": "Already up to date"}
                    
                    count = min(needed_count, 5000) # Limita a 5000 por lote incremental
                    logger.info(f"Modo Incremental: Baixando {count} candles faltantes para {self.symbol}")
            
            # Fallback para o count padrA?o se nA?o definido
            count = count or 2000
            
            if bot_id:
                progress_manager.update_progress(bot_id, "sync", 10, "Conectando ao MT5...")
                write_bot_log(
                    level="INFO",
                    context="sync",
                    message=f"Sincronizacao iniciada para {self.symbol}",
                    details={
                        "action": "sync_start",
                        "bot_id": bot_id,
                        "symbol": self.symbol,
                        "timeframe": self.timeframe,
                        "count": count,
                    },
                )
            
            logger.info(f"Sincronizando {count} candles: {self.symbol} ({self.timeframe})")
            rates = await mt5_client.get_rates(self.symbol, self.timeframe, count=count)
            
            if not rates:
                if bot_id:
                    progress_manager.update_progress(bot_id, "sync", 0, "Erro: Sem dados do MT5")
                return {"success": False, "error": "No data from bridge", "new_records": 0}
            
            if bot_id:
                progress_manager.update_progress(bot_id, "sync", 30, f"Processando {len(rates)} registros...")

            new_records = 0
            total_rates = len(rates)
            
            for i, rate in enumerate(rates):
                dt_time = datetime.fromtimestamp(rate['time'])
                
                # Reporta progresso a cada 10%
                if bot_id and i % (total_rates // 10 or 1) == 0:
                    perc = 30 + int((i / total_rates) * 60)
                    progress_manager.update_progress(bot_id, "sync", perc, f"Sincronizando: {i}/{total_rates}")

                # Verifica se A? duplicado
                if not force:
                    last_ts = self.get_last_timestamp(db, self.symbol, self.timeframe)
                    if last_ts and dt_time <= last_ts:
                        continue

                new_data = HistoricalData(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    time=dt_time,
                    open=rate['open'],
                    high=rate['high'],
                    low=rate['low'],
                    close=rate['close'],
                    tick_volume=rate.get('tick_volume', 0),
                    spread=rate.get('spread', 0),
                    real_volume=rate.get('real_volume', 0)
                )
                db.add(new_data)
                new_records += 1
            
            if new_records > 0:
                db.commit()
                self.records_processed += new_records
            
            self.last_sync = datetime.now()
            
            if bot_id:
                progress_manager.update_progress(bot_id, "sync", 100, "Concluido!")
                # Limpa apA?s um tempo
                asyncio.create_task(self._delayed_clear_progress(bot_id))
                write_bot_log(
                    level="INFO",
                    context="sync",
                    message=f"Sincronizacao concluida para {self.symbol}",
                    details={
                        "action": "sync_complete",
                        "bot_id": bot_id,
                        "symbol": self.symbol,
                        "timeframe": self.timeframe,
                        "new_records": new_records,
                        "total_processed": self.records_processed,
                    },
                )
            
            result = {
                "success": True,
                "new_records": new_records,
                "total_processed": self.records_processed,
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "sync_time_ms": (datetime.now() - start_time).total_seconds() * 1000
            }
            
            logger.info(f"SincronizaA?A?o OK: {new_records} novos registros em {result['sync_time_ms']:.0f}ms")
            return result
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro na sincronizaA?A?o: {e}")
            if bot_id:
                write_bot_log(
                    level="ERROR",
                    context="sync",
                    message=f"Erro na sincronizacao para {self.symbol}",
                    details={
                        "action": "sync_error",
                        "bot_id": bot_id,
                        "symbol": self.symbol,
                        "timeframe": self.timeframe,
                        "error": str(e),
                    },
                )
            return {"success": False, "error": str(e), "new_records": 0}
        finally:
            db.close()
    
    async def _delayed_clear_progress(self, bot_id: int):
        await asyncio.sleep(5)
        progress_manager.clear_progress(bot_id)

    async def sync_range(
        self,
        start_date: datetime,
        end_date: datetime,
        batch_size: int = 1000
    ) -> Dict:
        """
        Sincronizar dados em um intervalo especA?fico
        """
        logger.info(f"Sincronizando perA?odo: {start_date} atA? {end_date}")
        
        total_added = 0
        current = start_date
        
        while current < end_date:
            result = await self.sync_data(count=batch_size)
            if result.get('success'):
                total_added += result.get('new_records', 0)
            
            # AvanA?ar no tempo
            tf_minutes = self.get_timeframe_multiplier()
            current += timedelta(minutes=batch_size * tf_minutes)
        
        return {
            "success": True,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_records": total_added
        }
    
    async def start_loop(self):
        """Iniciar loop de sincronizaA?A?o contA?nua"""
        self.is_running = True
        logger.info(f"Iniciando loop de sincronizaA?A?o (intervalo: {self.sync_interval}s)")
        
        while self.is_running:
            try:
                await self.sync_data(count=100)
            except Exception as e:
                logger.error(f"Erro no loop do DataCollector: {e}")
                await asyncio.sleep(10)  # Aguarda antes de retentar
            
            await asyncio.sleep(self.sync_interval)
    
    def stop_loop(self):
        """Parar loop de sincronizaA?A?o"""
        self.is_running = False
        logger.info("Loop de sincronizaA?A?o parado")
    
    def get_status(self) -> Dict:
        """Obter status do coletor"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "is_running": self.is_running,
            "sync_interval": self.sync_interval,
            "records_processed": self.records_processed,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "timeframe_multiplier": self.get_timeframe_multiplier()
        }
    
    def clear_cache(self):
        """Limpar cache local"""
        self.cache.clear()
        logger.info("Cache limpo")


# InstA?ncia Singleton
data_collector = DataCollector()
