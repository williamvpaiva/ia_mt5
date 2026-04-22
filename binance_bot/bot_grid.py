import asyncio
import ccxt.pro as ccxt
import pandas as pd
import pandas_ta as ta
import os
import numpy as np
from loguru import logger
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

# Configuração de Log Persistente
logger.add("trading_log.txt", rotation="10 MB", retention="10 days", level="INFO")
console = Console()

class DynamicGridBotFutures:
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
        self.leverage = 3
        self.num_grids = 60
        self.active_range = 8
        self.order_size_usdt = 5.5
        
        # Segurança e Profit Taking
        self.TARGET_PROFIT_PCT = 0.007 # 0.7% lucro final sobre a banca
        self.STOP_LOSS_PCT = -0.025   # -2.5% stop global
        self.TRAILING_ACTIVATION_PCT = 0.005 # Ativa trailing com 0.5%
        self.TRAILING_CALLBACK_PCT = 0.0015  # Distância do trailing (0.15%)
        
        # --- NOVO: REEQUILÍBRIO DE LUCRO RÁPIDO ---
        self.POSITION_TP_PCT = 0.0035 # Realiza lucro total se a posição subir 0.35% da média
        self.entry_price_avg = 0.0
        
        # Estado do Bot
        self.grid_levels = []
        self.peak_roi = 0.0
        self.is_trailing = False
        self.grid_spacing = 0.0
        self.pivot_price = 0.0
        self.skew = 0.0
        self.last_rsi = 50.0
        self.bb_upper = 0.0
        self.bb_lower = 0.0
        
    async def setup_account(self):
        try:
            await self.exchange.load_markets()
            try:
                await self.exchange.set_leverage(self.leverage, self.symbol)
                logger.info(f"SET: Alavancagem {self.leverage}x em {self.symbol}")
            except Exception as e:
                logger.warning(f"Aviso Setup: {e}")
            try:
                await self.exchange.set_margin_mode('CROSSED', self.symbol)
                logger.info(f"SET: Margem Cruzada em {self.symbol}")
            except:
                pass
        except Exception as e:
            logger.error(f"ERRO CRÍTICO SETUP: {e}")

    async def calculate_market_intelligence(self):
        """Usa Bollinger Bands + RSI + ADX para definir a estratégia de entrada."""
        try:
            logger.info("IA: Analisando Bollinger Bands + RSI...")
            candles = await self.exchange.fetch_ohlcv(self.symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(candles, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
            
            # --- 1. Cálculo de Indicadores ---
            # Bollinger Bands (20, 2)
            bb = ta.bbands(df['c'], length=20, std=2)
            
            # Pegamos os últimos valores filtrando pelo prefixo (mais resiliente)
            last_bb = bb.iloc[-1]
            bbu = last_bb.filter(like='BBU').iloc[0]
            bbl = last_bb.filter(like='BBL').iloc[0]
            bbm = last_bb.filter(like='BBM').iloc[0]
            
            self.bb_upper = bbu
            self.bb_lower = bbl
            
            # RSI (14)
            df['rsi'] = ta.rsi(df['c'], length=14)
            
            # ADX para Força
            df['adx'] = ta.adx(df['h'], df['l'], df['c'], length=14)['ADX_14']
            
            # ATR para Base de Spacing
            df['atr'] = ta.atr(df['h'], df['l'], df['c'], length=14)
            
            last = df.iloc[-1]
            price = last['c']
            
            self.pivot_price = price
            self.last_rsi = last['rsi']
            
            # --- 2. Lógica de Skew (Bollinger + RSI) ---
            new_skew = 0.0
            
            # SOBRECOMPRA (REVERSÃO BAIXA)
            # Preço acima da banda superior ou RSI > 70
            if price >= bbu or last['rsi'] > 70:
                # Skew Negativo (Favorece Vendas/Short)
                new_skew = -0.5 if last['rsi'] > 75 else -0.3
                logger.info(f"IA: Mercado em SOBRECOMPRA (RSI: {last['rsi']:.1f}). Ajustando Skew para SELL.")
                
            # SOBREVENDA (REVERSÃO ALTA)
            # Preço abaixo da banda inferior ou RSI < 30
            elif price <= bbl or last['rsi'] < 30:
                # Skew Positivo (Favorece Compras/Long)
                new_skew = 0.5 if last['rsi'] < 25 else 0.3
                logger.info(f"IA: Mercado em SOBREVENDA (RSI: {last['rsi']:.1f}). Ajustando Skew para BUY.")
            
            # SEGUIMENTO DE TENDÊNCIA (Usa ADX se o preço estiver no meio das bandas)
            else:
                if last['adx'] > 25:
                    # Direção baseada na Média de Bollinger (Média Móvel 20)
                    if price > bbm:
                        new_skew = 0.2 # Viés leve de alta
                    else:
                        new_skew = -0.2 # Viés leve de baixa
                else:
                    new_skew = 0.0 # Lateralizado
            
            self.skew = new_skew
            
            # --- 3. Lógica de Spacing (Volatilidade BB vs ATR) ---
            # BB Width como fator de volatilidade
            bb_width = (bbu - bbl) / bbm
            
            # Se a banda estiver muito estreita (Squeeze), aumentamos o espaçamento para evitar falsos rompimentos.
            # Se estiver larga, usamos o ATR para scalping técnico.
            if bb_width < 0.005: # Squeeze de 0.5%
                potential_spacing = last['atr'] / 4 # Grid mais largo no squeeze
            else:
                potential_spacing = last['atr'] / 6
                
            min_profitable_spacing = price * 0.0012 # Aumentado de 0.08% para 0.12% para evitar ruído
            self.grid_spacing = max(potential_spacing, min_profitable_spacing)
            
            logger.info(f"IA V3 STATUS: Spacing: {self.grid_spacing:.8f} | Skew: {self.skew:.2f} | RSI: {last['rsi']:.1f} | BB Width: {bb_width*100:.2f}%")
            self.generate_grid_levels()
            
        except Exception as e:
            logger.error(f"ERRO IA MARKET: {e}")

    def generate_grid_levels(self):
        levels = []
        for i in range(-self.num_grids // 2, self.num_grids // 2 + 1):
            if i == 0: continue
            adj_factor = (1 + (self.skew if i > 0 else -self.skew))
            price = self.pivot_price + (i * self.grid_spacing) * adj_factor
            side = 'buy' if i < 0 else 'sell'
            levels.append({'price': price, 'side': side})
        self.grid_levels = sorted(levels, key=lambda x: x['price'])

    async def manage_active_orders(self, current_price):
        try:
            open_orders = await self.exchange.fetch_open_orders(self.symbol)
            buys = [l for l in self.grid_levels if l['side'] == 'buy' and l['price'] < current_price]
            sells = [l for l in self.grid_levels if l['side'] == 'sell' and l['price'] > current_price]
            
            target_buys = sorted(buys, key=lambda x: abs(x['price'] - current_price))[:self.active_range]
            target_sells = sorted(sells, key=lambda x: abs(x['price'] - current_price))[:self.active_range]
            targets = target_buys + target_sells
            
            for order in open_orders:
                # Tolerância aumentada para 60% do espaçamento para evitar cancelamentos bobos
                is_still_target = any(abs(float(order['price']) - t['price']) < (self.grid_spacing * 0.6) for t in targets)
                if not is_still_target:
                    await self.exchange.cancel_order(order['id'], self.symbol)

            for t in targets:
                # Verificação de existência com margem de 60%
                already_exists = any(abs(float(order['price']) - t['price']) < (self.grid_spacing * 0.6) for order in open_orders)
                if not already_exists:
                    amount = self.order_size_usdt / t['price']
                    p_amount = self.exchange.amount_to_precision(self.symbol, amount)
                    p_price = self.exchange.price_to_precision(self.symbol, t['price'])
                    await self.exchange.create_order(self.symbol, 'limit', t['side'], p_amount, p_price)
                    logger.info(f"GRID V3: {t['side'].upper()} @ {p_price}")
        except Exception as e:
            logger.error(f"ERRO GESTÃO ORDENS: {e}")

    async def check_global_safety(self):
        try:
            positions = await self.exchange.fetch_positions([self.symbol])
            active_pos = [p for p in positions if float(p['contracts']) > 0]
            
            if not active_pos:
                self.is_trailing = False
                self.peak_roi = 0.0
                self.entry_price_avg = 0.0
                return

            p = active_pos[0]
            self.entry_price_avg = float(p['entryPrice'])
            contracts = float(p['contracts'])
            unrealized_pnl = float(p['unrealizedPnl'])
            
            # 1. ROI sobre o Capital Inicial (Segurança Global)
            roi_current = unrealized_pnl / self.initial_balance
            
            # 2. ROI sobre a Posição (Reequilíbrio Rápido)
            # A posição longa ganha se o preço atual > preço médio
            ticker = await self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            pnl_pos_pct = (current_price / self.entry_price_avg - 1) if p['side'] == 'long' else (1 - current_price / self.entry_price_avg)
            
            # --- Lógica de Reequilíbrio Rápido ---
            if pnl_pos_pct >= self.POSITION_TP_PCT:
                logger.success(f"--- REEQUILÍBRIO: Lucro de {pnl_pos_pct*100:.2f}% atingido na posição! Resetando Grid... ---")
                await self.emergency_reset()
                return

            # --- Trailing e Stop Global ---
            if roi_current >= self.TRAILING_ACTIVATION_PCT:
                if not self.is_trailing:
                    self.is_trailing = True
                    logger.success(f"--- TRAILING ON: ROI {roi_current*100:.2f}% ---")
                if roi_current > self.peak_roi:
                    self.peak_roi = roi_current
                if roi_current < (self.peak_roi - self.TRAILING_CALLBACK_PCT):
                    logger.success(f"--- TRAILING EXIT: Lucro {roi_current*100:.2f}% ---")
                    await self.emergency_reset()
                    return
            if roi_current >= self.TARGET_PROFIT_PCT:
                await self.emergency_reset()
                return
            if roi_current <= self.STOP_LOSS_PCT:
                await self.emergency_reset()
                return
        except Exception as e:
            logger.error(f"ERRO SEGURANÇA: {e}")

    async def emergency_reset(self):
        logger.warning("BOT: Resetando e fechando posições...")
        try:
            await self.exchange.cancel_all_orders(self.symbol)
            positions = await self.exchange.fetch_positions([self.symbol])
            active_pos = [p for p in positions if float(p['contracts']) > 0]
            if active_pos:
                for p in active_pos:
                    side = 'sell' if float(p['contracts']) > 0 and p['side'] == 'long' else 'buy'
                    await self.exchange.create_order(self.symbol, 'market', side, abs(float(p['contracts'])), params={'reduceOnly': True})
            await asyncio.sleep(2)
            await self.calculate_market_intelligence()
        except Exception as e:
            logger.error(f"ERRO RESET: {e}")

    async def show_dashboard(self):
        while True:
            try:
                ticker = await self.exchange.fetch_ticker(self.symbol)
                price = ticker['last']
                table = Table(title=f"Bot Gradviti BB+RSI - {self.symbol}")
                table.add_column("DADO", style="cyan")
                table.add_column("VALOR", style="magenta")
                table.add_row("Preço", f"{price:.8f}")
                table.add_row("RSI (14)", f"{self.last_rsi:.1f}")
                table.add_row("Bollinger", f"U:{self.bb_upper:.8f} L:{self.bb_lower:.8f}")
                table.add_row("Skew (Enviesamento)", f"{self.skew:.2f}")
                table.add_row("Status", "TRAILING" if self.is_trailing else "NORMAL")
                console.clear()
                console.print(table)
            except: pass
            await asyncio.sleep(10)

    async def ia_scheduler(self):
        while True:
            await asyncio.sleep(600) 
            await self.calculate_market_intelligence()

    async def start(self):
        logger.info("--- INICIANDO BOT GRID V3 (BB + RSI) ---")
        await self.setup_account()
        await self.calculate_market_intelligence()
        asyncio.create_task(self.ia_scheduler())
        asyncio.create_task(self.show_dashboard())
        while True:
            try:
                await self.check_global_safety()
                ticker = await self.exchange.fetch_ticker(self.symbol)
                await self.manage_active_orders(ticker['last'])
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Erro Loop: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = DynamicGridBotFutures()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot finalizado.")
