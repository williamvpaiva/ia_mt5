import logging
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from ..core.database import SessionLocal
from .data_collector import data_collector
from .bot_log_service import write_bot_log
from ..models.bot import Bot
from ..models.historical_data import HistoricalData
from .progress_manager import progress_manager

logger = logging.getLogger("Trainer")

class Trainer:
    def __init__(self):
        self.is_training = {}

    async def train_bot(self, bot_id: int):
        if self.is_training.get(bot_id):
            logger.warning(f"Treinamento jA? em curso para o bot {bot_id}")
            return
        
        self.is_training[bot_id] = True
        progress_manager.update_progress(bot_id, "train", 5, "Iniciando treinamento...")
        logger.info(f"Iniciando treinamento do bot {bot_id}...")
        
        db: Session = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == bot_id).first()
            if not bot:
                logger.error(f"Bot {bot_id} nA?o encontrado")
                progress_manager.clear_progress(bot_id)
                return

            write_bot_log(
                level="INFO",
                context="train",
                message=f"Treinamento iniciado para {bot.name}",
                details={
                    "action": "train_start",
                    "bot_id": bot.id,
                    "bot_name": bot.name,
                    "symbol": bot.symbol,
                    "timeframe": bot.timeframe,
                },
            )

            # Passo 1: SincronizaA?A?o Incremental
            progress_manager.update_progress(bot_id, "train", 15, "Sincronizando dados histA?ricos...")
            symbol = bot.symbol or 'WIN$'
            timeframe = bot.timeframe or 'M5'
            
            data_collector.symbol = symbol
            data_collector.timeframe = timeframe
            
            await data_collector.sync_data(incremental=True)
            progress_manager.update_progress(bot_id, "train", 40, "Processando candles...")

            import pandas as pd
            import pandas_ta as ta
            from stable_baselines3 import PPO
            from ..engine.rl_env import TradingEnv
            import os

            # Passo 2: Carga e PreparaA?A?o de Dados
            records = db.query(HistoricalData).filter(
                HistoricalData.symbol == symbol,
                HistoricalData.timeframe == timeframe
            ).order_by(HistoricalData.time.asc()).all()

            if not records:
                raise Exception("Sem dados histA?ricos para treinar.")

            df = pd.DataFrame([{
                'time': r.time, 'open': r.open, 'high': r.high, 
                'low': r.low, 'close': r.close, 'tick_volume': r.tick_volume
            } for r in records])

            # CA?lculo de Indicadores para ObservaA?A?o da IA
            progress_manager.update_progress(bot_id, "train", 50, "Processando indicadores matemA?ticos...")
            df['EMA_9'] = ta.ema(df['close'], length=9)
            df['EMA_21'] = ta.ema(df['close'], length=21)
            df['RSI'] = ta.rsi(df['close'], length=14)
            df['ATR'] = ta.atr(df.high, df.low, df.close, length=14)
            df.fillna(0, inplace=True)
            
            # Remover coluna temporal para o obs_space
            train_df = df.drop(columns=['time'])

            progress_manager.update_progress(bot_id, "train", 60, "Treinando Rede Neural (PPO)...")

            # Passo 3: Treinamento Real
            env = TradingEnv(train_df, lot_size=bot.risk_config.get('lot_size', 1))
            
            model_dir = "models"
            if not os.path.exists(model_dir): os.makedirs(model_dir)
            model_path = f"{model_dir}/bot_{bot_id}_ppo"
            
            model = PPO("MlpPolicy", env, verbose=0, learning_rate=0.0003, n_steps=2048)
            
            # Executa 10000 timesteps de aprendizado (ajustA?vel)
            model.learn(total_timesteps=10000)
            model.save(model_path)

            # Atualiza metadados do bot
            from sqlalchemy.orm.attributes import flag_modified
            bot.ai_config['model_path'] = model_path
            bot.ai_config['last_training'] = datetime.now().isoformat()
            bot.ai_config['training_samples'] = len(records)
            flag_modified(bot, "ai_config")
            db.commit()
            
            progress_manager.update_progress(bot_id, "train", 100, "IA OTIMIZADA!")
            logger.info(f"Modelo RL para o bot {bot_id} salvo em {model_path}")
            
            progress_manager.update_progress(bot_id, "train", 100, "ConcluA?do!")
            logger.info(f"Treinamento do bot {bot_id} ({bot.name}) concluA?do com sucesso!")
            
            # Limpa apA?s 5 segundos
            await asyncio.sleep(5)
            progress_manager.clear_progress(bot_id)

            write_bot_log(
                level="INFO",
                context="train",
                message=f"Treinamento concluido para {bot.name}",
                details={
                    "action": "train_complete",
                    "bot_id": bot.id,
                    "bot_name": bot.name,
                    "symbol": bot.symbol,
                    "timeframe": bot.timeframe,
                    "samples": len(records),
                    "model_path": model_path,
                },
            )
            
            return {"success": True, "samples": len(records)}

        except Exception as e:
            db.rollback()
            logger.error(f"Erro no treinamento do bot {bot_id}: {e}")
            progress_manager.update_progress(bot_id, "train", 0, f"Erro: {str(e)}")
            bot_name = bot.name if "bot" in locals() and bot else f"Bot {bot_id}"
            write_bot_log(
                level="ERROR",
                context="train",
                message=f"Erro no treinamento para {bot_name}",
                details={
                    "action": "train_error",
                    "bot_id": bot_id,
                    "bot_name": bot_name,
                    "error": str(e),
                },
            )
            return {"success": False, "error": str(e)}
        finally:
            db.close()
            self.is_training[bot_id] = False

trainer = Trainer()
