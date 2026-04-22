import pandas as pd
import numpy as np
import ta
import asyncio
import logging
from datetime import datetime
from .mt5_client import mt5_client
from .ia_service import ia_service
from ..models.bot import Bot
from ..models.trade import Trade
from ..core.database import SessionLocal

logger = logging.getLogger("TradingBot")

class TradingBotInstance:
    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self.is_running = False
        self.config = {}
        self.magic_number = 0
        self.symbol = "WIN"
        self.timeframe = "M5"

    async def load_config(self):
        db = SessionLocal()
        bot = db.query(Bot).filter(Bot.id == self.bot_id).first()
        if bot:
            self.config = bot.config or {}
            self.magic_number = bot.magic_number
            self.symbol = bot.symbol
            self.timeframe = bot.timeframe
            self.excluded_days = getattr(bot, 'excluded_days', [])
            self.start_time = getattr(bot, 'start_time', '09:00')
            self.end_time = getattr(bot, 'end_time', '17:50')
        db.close()

    def is_trading_allowed(self) -> bool:
        """Verifica se o bot pode operar no momento atual"""
        now = datetime.now()
        
        # 1. Dia da semana (JS 0=Sun, 1=Mon... / Python 0=Mon, 6=Sun)
        current_day_js = (now.weekday() + 1) % 7
        if current_day_js in self.excluded_days:
            return False
            
        # 2. Janela de HorA?rio
        try:
            current_time = now.time()
            start = datetime.strptime(self.start_time, "%H:%M").time()
            end = datetime.strptime(self.end_time, "%H:%M").time()
            if not (start <= current_time <= end):
                return False
        except:
            return True # Falha na conversA?o permite por seguranA?a
            
        return True

    async def get_data(self):
        rates = await mt5_client.get_rates(self.symbol, self.timeframe, count=200)
        if not rates: return None
        df = pd.DataFrame(rates)
        # Sincronizar com indicadores usados no treino
        import pandas_ta as ta
        df['EMA_9'] = ta.ema(df['close'], length=9)
        df['EMA_21'] = ta.ema(df['close'], length=21)
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['ATR'] = ta.atr(df.high, df.low, df.close, length=14)
        df.fillna(0, inplace=True)
        return df

    async def run_cycle(self):
        """Executa um ciclo único de decisão e trading"""
        if not self.config:
            await self.load_config()

        if not self.is_trading_allowed():
            return

        df = await self.get_data()
        if df is None: return

        # 1. Carregar modelo RL se disponível
        from stable_baselines3 import PPO
        import os
        model = None
        model_path = f"models/bot_{self.bot_id}_ppo"
        if os.path.exists(model_path + ".zip"):
            model = PPO.load(model_path)

        # 2. Consultar Redis para Modo Espião (se ativo)
        spy_status = None
        db = SessionLocal()
        bot = db.query(Bot).filter(Bot.id == self.bot_id).first()
        
        if bot.spy_config.get("active") and bot.spy_config.get("target_magic"):
            import redis, json
            r_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            target_data = r_client.get(f"spy:{bot.spy_config['target_magic']}")
            if target_data:
                spy_status = json.loads(target_data)

        # 3. Decisão Híbrida
        from ..engine.decisor import HybridDecisor
        decisor = HybridDecisor(bot, df)
        decision = decisor.decide(rl_model=model, spy_status=spy_status)

        # 4. Execução de Ordens e Gestão de Risco
        positions = await mt5_client.get_positions()
        my_positions = [p for p in positions if p.get('magic') == self.magic_number]
        
        lot = bot.risk_config.get("lot_size", 1.0)
        sl = bot.risk_config.get("stop_loss", 200)
        tp = bot.risk_config.get("take_profit", 400)

        if not my_positions:
            if decision == 1: # BUY
                logger.info(f"Bot {self.bot_id} decidindo COMPRA para {self.symbol}")
                await mt5_client.place_order(self.symbol, "buy", lot, sl=sl, tp=tp, magic=self.magic_number)
            elif decision == -1: # SELL
                logger.info(f"Bot {self.bot_id} decidindo VENDA para {self.symbol}")
                await mt5_client.place_order(self.symbol, "sell", lot, sl=sl, tp=tp, magic=self.magic_number)
        else:
            # Fechamento se sinal inverter
            pos = my_positions[0]
            if (pos['type'] == 'buy' and decision == -1) or (pos['type'] == 'sell' and decision == 1):
                logger.info(f"Bot {self.bot_id} fechando posição devido a inversão de sinal")
                await mt5_client.close_position(pos['ticket'])

        # 5. Publicar Estado no Redis para outros espiões
        import redis, json
        r_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
        my_status = {
            "position": my_positions[0]['type'] if my_positions else "none",
            "pnl": sum(p.get('profit', 0) for p in my_positions),
            "symbol": self.symbol,
            "magic": self.magic_number
        }
        r_client.set(f"spy:{self.magic_number}", json.dumps(my_status), ex=60)
        
        db.close()

    async def run(self):
        """Loop mantido para compatibilidade, mas agora controlado pelo Manager"""
        self.is_running = True
        logger.info(f"Iniciando loop do Bot {self.bot_id} (Híbrido)")
        
        while self.is_running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Erro no ciclo do Bot {self.bot_id}: {e}")
            
            await asyncio.sleep(5)

    def stop(self):
        self.is_running = False
        logger.info(f"Parando Bot {self.bot_id}")
