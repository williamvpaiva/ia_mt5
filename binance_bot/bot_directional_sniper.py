import asyncio
import ccxt.pro as ccxt
import pandas as pd
import importlib.metadata
import importlib
importlib.metadata = importlib.metadata
import pandas_ta as ta
import os
import numpy as np
from loguru import logger
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

# Configuração de Log
logger.add("directional_log.txt", rotation="10 MB", retention="10 days", level="INFO")
console = Console()

class DirectionalSniperBot:
    def __init__(self):
        # Configurações da Exchange
        self.exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
            },
            'enableRateLimit': True
        })
        # MODO SANDBOX - Mudar para False em produção
        self.exchange.set_sandbox_mode(True)
        
        # Parâmetros Editáveis
        self.symbol = '1000PEPE/USDT'
        self.initial_balance = 5000.0
        self.leverage = 5 # Um pouco mais de alavancagem para trades direcionais
        self.order_size_usdt = 100.0 # Trade único de $100
        
        # Config de Saída (Take Profit / Stop Loss)
        self.STOP_LOSS_PCT = -0.015    # -1.5% Stop Loss Fixo
        self.TRAILING_ACT_PCT = 0.008 # Inicia trailing com 0.8% de lucro
        self.TRAILING_CALL_PCT = 0.002 # Distância de 0.2% do topo
        
        # Estado
        self.peak_roi = 0.0
        self.is_trailing = False
        self.last_rsi = 50.0
        self.bb_upper = 0.0
        self.bb_lower = 0.0
        self.bb_mid = 0.0
        
    async def setup_account(self):
        try:
            await self.exchange.load_markets()
            await self.exchange.set_leverage(self.leverage, self.symbol)
            try:
                await self.exchange.set_margin_mode('CROSSED', self.symbol)
            except: pass
            logger.info(f"SET: Alavancagem {self.leverage}x em {self.symbol}")
        except Exception as e:
            logger.error(f"Erro Setup: {e}")

    async def get_market_data(self):
        """Calcula os indicadores técnicos (os mesmos do Grid V3)."""
        try:
            candles = await self.exchange.fetch_ohlcv(self.symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(candles, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            
            # BB
            bb = ta.bbands(df['c'], length=20, std=2)
            last_bb = bb.iloc[-1]
            self.bb_upper = last_bb.filter(like='BBU').iloc[0]
            self.bb_lower = last_bb.filter(like='BBL').iloc[0]
            self.bb_mid = last_bb.filter(like='BBM').iloc[0]
            
            # RSI
            df['rsi'] = ta.rsi(df['c'], length=14)
            self.last_rsi = df['rsi'].iloc[-1]
            
            # ADX
            adx = ta.adx(df['h'], df['l'], df['c'], length=14)
            last_adx = adx['ADX_14'].iloc[-1]
            
            return {
                'price': df['c'].iloc[-1],
                'rsi': self.last_rsi,
                'adx': last_adx,
                'bbu': self.bb_upper,
                'bbl': self.bb_lower,
                'bbm': self.bb_mid
            }
        except Exception as e:
            logger.error(f"Erro Dados: {e}")
            return None

    async def check_entry(self, data):
        """Lógica de entrada baseada em BB + RSI."""
        positions = await self.exchange.fetch_positions([self.symbol])
        active_pos = [p for p in positions if float(p['contracts']) > 0]
        
        if active_pos:
            return # Já estamos em um trade
            
        price = data['price']
        rsi = data['rsi']
        
        # --- ENTRADA COMPRA (LONG) ---
        # Preço abaixo da banda inferior + RSI sobrevendido
        if price <= data['bbl'] and rsi < 35:
            logger.info(f"SINAL COMPRA: Preço {price} <= BBL {data['bbl']:.8f} | RSI: {rsi:.1f}")
            await self.execute_order('buy')
            
        # --- ENTRADA VENDA (SHORT) ---
        # Preço acima da banda superior + RSI sobrecomprado
        elif price >= data['bbu'] and rsi > 65:
            logger.info(f"SINAL VENDA: Preço {price} >= BBU {data['bbu']:.8f} | RSI: {rsi:.1f}")
            await self.execute_order('sell')

    async def execute_order(self, side):
        try:
            ticker = await self.exchange.fetch_ticker(self.symbol)
            amount = self.order_size_usdt / ticker['last']
            p_amount = self.exchange.amount_to_precision(self.symbol, amount)
            
            order = await self.exchange.create_order(
                symbol=self.symbol,
                type='market',
                side=side,
                amount=p_amount
            )
            logger.success(f"ORDEM EXECUTADA: {side.upper()} {p_amount} {self.symbol}")
            self.peak_roi = 0.0
            self.is_trailing = False
        except Exception as e:
            logger.error(f"Erro Execução: {e}")

    async def manage_position(self):
        """Gerencia saída por Stop Loss e Trailing Gain."""
        try:
            positions = await self.exchange.fetch_positions([self.symbol])
            active_pos = [p for p in positions if float(p['contracts']) > 0]
            
            if not active_pos:
                return
            
            p = active_pos[0]
            side = p['side'] # 'long' ou 'short'
            unrealized_pnl = float(p['unrealizedPnl'])
            roi_current = unrealized_pnl / self.initial_balance
            
            # 1. Stop Loss Fixo
            if roi_current <= self.STOP_LOSS_PCT:
                logger.error(f"STOP LOSS ATINGIDO: {roi_current*100:.2f}%")
                await self.close_position(p)
                return

            # 2. Trailing Gain
            if roi_current >= self.TRAILING_ACT_PCT:
                if not self.is_trailing:
                    self.is_trailing = True
                    logger.success(f"TRAILING ATIVADO: ROI {roi_current*100:.2f}%")
                
                if roi_current > self.peak_roi:
                    self.peak_roi = roi_current
                
                # Gatilho de saída se recuar do pico
                if roi_current < (self.peak_roi - self.TRAILING_CALL_PCT):
                    logger.success(f"REALIZANDO LUCRO (Trailing): {roi_current*100:.2f}%")
                    await self.close_position(p)
        except Exception as e:
            logger.error(f"Erro Gestão: {e}")

    async def close_position(self, p):
        try:
            side = 'sell' if p['side'] == 'long' else 'buy'
            await self.exchange.create_order(
                symbol=self.symbol,
                type='market',
                side=side,
                amount=abs(float(p['contracts'])),
                params={'reduceOnly': True}
            )
            logger.info("POSIÇÃO ENCERRADA.")
        except Exception as e:
            logger.error(f"Erro ao fechar: {e}")

    async def show_status(self, data):
        table = Table(title=f"Sniper Direcional V2 - {self.symbol}")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="magenta")
        table.add_row("Preço Atual", f"{data['price']:.8f}")
        table.add_row("RSI (14)", f"{data['rsi']:.1f}")
        table.add_row("BBU / BBL", f"{data['bbu']:.8f} / {data['bbl']:.8f}")
        table.add_row("Status", "TRAILING" if self.is_trailing else "AGUARDANDO SINAL")
        if self.is_trailing:
            table.add_row("Pico ROI", f"{self.peak_roi*100:.2f}%")
        
        console.clear()
        console.print(table)

    async def start(self):
        logger.info("--- INICIANDO BOT SNIPER DIRECIONAL V2 ---")
        await self.setup_account()
        
        while True:
            try:
                data = await self.get_market_data()
                if data:
                    await self.show_status(data)
                    await self.check_entry(data)
                    await self.manage_position()
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Erro Loop: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = DirectionalSniperBot()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot finalizado.")
