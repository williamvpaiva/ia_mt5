import os
import time
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# CARREGA CHAVES
load_dotenv()

class SniperBotBinance:
    def __init__(self):
        # CONFIGURAÇÕES TÉCNICAS
        self.symbol = 'BTC/USDT'  # MUDADO PARA BTC
        self.heavyweights = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        self.timeframe = '1m'
        self.leverage = 10  # Aumentado para lidar com BTC
        self.order_size_usdt = 12.0 # Conforme solicitado ($12)
        
        # PARÂMETROS TRAILING GAIN (DNA V21)
        self.tg_activation_pct = 0.5
        self.tg_distance_pct = 0.1
        self.tg_step_pct = 0.05
        
        # GESTÃO FINANCEIRA
        self.daily_loss_limit = 50.0
        self.daily_profit_goal = 100.0
        
        # PARÂMETROS ESTRATÉGIA
        self.adx_threshold = 26
        self.rsi_buy_limit = 31
        self.rsi_sell_limit = 69
        
        # ESTADO
        self.pause_until = 0
        self.exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        self.exchange.set_sandbox_mode(True)

    def log(self, msg, level="INFO"):
        fmt = f"[{self.symbol}] {msg}"
        if level == "INFO": logger.info(fmt)
        elif level == "WARNING": logger.warning(fmt)
        elif level == "ERROR": logger.error(fmt)
        elif level == "SUCCESS": logger.success(fmt)

    # --- INDICADORES NATIVOS (DNA V21) ---
    def calc_rma(self, series, period):
        return series.ewm(alpha=1/period, adjust=False).mean()

    def calculate_indicators(self, df):
        period = 14
        # RSI
        delta = df['c'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = self.calc_rma(gain, period)
        avg_loss = self.calc_rma(loss, period)
        rs = avg_gain / (avg_loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))

        # ADX
        high_low = df['h'] - df['l']
        high_close = np.abs(df['h'] - df['c'].shift(1))
        low_close = np.abs(df['l'] - df['c'].shift(1))
        df['tr'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = self.calc_rma(df['tr'], period)
        plus_dm = np.where((df['h'].diff() > df['l'].diff()) & (df['h'].diff() > 0), df['h'].diff(), 0.0)
        minus_dm = np.where((df['l'].diff() > df['h'].diff()) & (df['l'].diff() > 0), df['l'].diff(), 0.0)
        df['plus_di'] = 100 * (self.calc_rma(pd.Series(plus_dm), period) / (df['atr'] + 1e-10))
        df['minus_di'] = 100 * (self.calc_rma(pd.Series(minus_dm), period) / (df['atr'] + 1e-10))
        dx = 100 * np.abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'] + 1e-10)
        df['adx'] = self.calc_rma(dx, period)

        # Médias e Bandas
        df['sma20'] = df['c'].rolling(20).mean()
        df['sma50'] = df['c'].rolling(50).mean()
        std = df['c'].rolling(20).std()
        df['bb_up'] = df['sma20'] + (2 * std)
        df['bb_low'] = df['sma20'] - (2 * std)
        
        # VWAP
        df['vwap'] = (df['v'] * (df['h'] + df['l'] + df['c']) / 3).cumsum() / df['v'].cumsum()
        
        return df

    def get_market_sentiment(self):
        score = 0
        for sym in self.heavyweights:
            try:
                # Usar 5m para sentimento evita ruído excessivo de 1m
                ohlcv = self.exchange.fetch_ohlcv(sym, timeframe='5m', limit=10)
                df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
                # Média de fechamento vs abertura do período
                change = ((df['c'].iloc[-1] / df['o'].iloc[0]) - 1) * 100
                if change > 0.1: score += 1      # Mais agressivo no filtro
                elif change < -0.1: score -= 1
            except: continue
        return score

    def update_sl(self, side, price):
        try:
            # Precisão do mercado
            market = self.exchange.market(self.symbol)
            price_str = self.exchange.price_to_precision(self.symbol, price)
            
            # Buscar ordens abertas para evitar duplicidade ou cancelamento desnecessário
            open_orders = self.exchange.fetch_open_orders(self.symbol)
            stop_orders = [o for o in open_orders if o['type'].upper() in ['STOP_MARKET', 'STOP']]
            
            # Se já houver uma ordem de stop próxima, não precisamos atualizar (evita spam de API)
            if stop_orders:
                last_stop = float(stop_orders[0]['stopPrice'])
                diff = abs((price / last_stop) - 1)
                if diff < 0.0001: # 0.01% de diferença ignorável
                    return

            params = {'stopPrice': price_str, 'reduceOnly': True}
            order_side = 'sell' if side == 'long' else 'buy'
            self.exchange.cancel_all_orders(self.symbol, params={'unfilledOnly': True})
            self.exchange.create_order(self.symbol, 'STOP_MARKET', order_side, 0, None, params)
            self.log(f"Trailing Gain Ativo: SL ajustado para {price_str}", "WARNING")
        except Exception as e:
            self.log(f"Erro SL: {e}", "ERROR")

    def open_trade(self, side):
        try:
            self.exchange.set_leverage(self.leverage, self.symbol)
            ticker = self.exchange.fetch_ticker(self.symbol)
            price = ticker['ask'] if side == 'buy' else ticker['bid']
            
            # Cálculo de Qtd mínima
            market = self.exchange.market(self.symbol)
            amount = self.order_size_usdt / price
            amount_str = self.exchange.amount_to_precision(self.symbol, amount)
            
            order = self.exchange.create_order(self.symbol, 'market', side, amount_str)
            self.log(f"SNIPER {side.upper()} ADENTRADO! @ {price}", "SUCCESS")
            
            # SL Inicial (ATR)
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe='1m', limit=20)
            df = self.calculate_indicators(pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v']))
            atr = df['atr'].iloc[-1]
            sl_p = price - (atr * 2.5) if side == 'buy' else price + (atr * 2.5)
            self.update_sl('long' if side == 'buy' else 'short', sl_p)
        except Exception as e:
            self.log(f"Erro Entrada: {e}", "ERROR")

    def run(self):
        self.log("Sniper Pulse v21.2 Nativo Ligado!")
        while True:
            try:
                # Radar de Sentimento
                sentiment = self.get_market_sentiment()
                
                # Dados e Indicadores
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe=self.timeframe, limit=100)
                df = self.calculate_indicators(pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v']))
                m = df.iloc[-2]
                curr = df['c'].iloc[-1]
                
                # Posições
                positions = self.exchange.fetch_positions([self.symbol])
                pos = [p for p in positions if float(p['contracts']) > 0]
                
                if pos:
                    # Trailing Gain
                    p = pos[0]
                    entry = float(p['entryPrice'])
                    pnl_pct = ((curr/entry)-1)*100 if p['side'] == 'long' else ((entry/curr)-1)*100
                    if pnl_pct > self.tg_activation_pct:
                        dist = self.tg_distance_pct / 100
                        new_sl = curr * (1-dist) if p['side'] == 'long' else curr * (1+dist)
                        self.update_sl(p['side'], new_sl)
                else:
                    # Lógica Sniper
                    regime = "TREND" if m['adx'] > self.adx_threshold else "RANGE"
                    
                    if regime == "TREND" and m['sma20'] > m['sma50'] and sentiment >= 0:
                        if curr <= m['sma20'] and m['rsi'] < 65:
                            self.open_trade('buy')
                    elif regime == "TREND" and m['sma20'] < m['sma50'] and sentiment <= 0:
                        if curr >= m['sma20'] and m['rsi'] > 35:
                            self.open_trade('sell')
                    elif regime == "RANGE":
                        if m['rsi'] < self.rsi_buy_limit and sentiment >= 0 and curr < m['bb_low']:
                            self.open_trade('buy')
                        elif m['rsi'] > self.rsi_sell_limit and sentiment <= 0 and curr > m['bb_up']:
                            self.open_trade('sell')

                time.sleep(2)
            except Exception as e:
                self.log(f"Pulse Error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    bot = SniperBotBinance()
    bot.run()
