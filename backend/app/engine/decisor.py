import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, Optional
from ..models.bot import Bot

class HybridDecisor:
    """
    Motor de DecisA?o HA?brido: Sinais TA?cnicos + RL + Modo EspiA?o.
    """
    def __init__(self, bot: Bot, df: pd.DataFrame):
        self.bot = bot
        self.df = df
        self.config = bot.signals_config
        self.risk = bot.risk_config
        self.ai = bot.ai_config
        self.spy = bot.spy_config
        
    def calculate_signals(self) -> Dict[str, int]:
        """
        Calcula cada sinal de forma independente.
        Retorno: 1 (Buy), -1 (Sell), 0 (Neutral)
        """
        signals = {}
        
        # 1. Direção de Médias (MA Cross adaptado para maior frequência)
        if self.config.get("ma_cross", {}).get("active"):
            fast = self.config["ma_cross"]["fast_period"]
            slow = self.config["ma_cross"]["slow_period"]
            ma_f = ta.ema(self.df['close'], length=fast)
            ma_s = ta.ema(self.df['close'], length=slow)
            
            # Relaxamento: Se a rápida estiver acima da lenta, sinal de compra (estado, não evento)
            if ma_f.iloc[-1] > ma_s.iloc[-1]:
                signals["ma_cross"] = 1
            elif ma_f.iloc[-1] < ma_s.iloc[-1]:
                signals["ma_cross"] = -1
            else:
                signals["ma_cross"] = 0
                
        # 2. RSI
        if self.config.get("rsi", {}).get("active"):
            period = self.config["rsi"]["period"]
            rsi = ta.rsi(self.df['close'], length=period)
            if rsi.iloc[-1] < self.config["rsi"]["oversold"]:
                signals["rsi"] = 1
            elif rsi.iloc[-1] > self.config["rsi"]["overbought"]:
                signals["rsi"] = -1
            else:
                signals["rsi"] = 0

        # ... Adicionar outros sinais tA?cnicos aqui ...
        
        return signals

    def get_spy_signal(self, target_status: Dict) -> int:
        """
        Consulta o sinal do bot espiado.
        """
        if not self.spy.get("active") or not target_status:
            return 0
            
        # O bot espiado estA? comprado?
        if target_status.get("position") == "buy":
            return 1
        elif target_status.get("position") == "sell":
            return -1
        return 0

    def get_ai_prediction(self, model) -> int:
        """
        Consulta o modelo de Reinforcement Learning.
        """
        if not self.ai.get("rl_active") or model is None:
            return 0
            
        print(f"DEBUG IA [{self.bot.name}]: Verificando IA...")
        # Preparar observaA?A?o atual filtrando apenas as colunas que o modelo espera
        cols = ['open', 'high', 'low', 'close', 'tick_volume', 'EMA_9', 'EMA_21', 'RSI', 'ATR']
        try:
            obs_df = self.df[cols].iloc[-1]
            obs = obs_df.values.astype(np.float32)
            action, _states = model.predict(obs, deterministic=True)
            
            # Mapeamento do nosso TradingEnv: 0=Stay, 1=Buy, 2=Sell
            if action == 1: return 1
            if action == 2: return -1
        except Exception as e:
            print(f"DEBUG IA: Erro ao prever com PPO: {e}")
            return 0
            
        return 0

    def decide(self, rl_model=None, spy_status=None) -> int:
        """
        Consolida todos os sinais ativos em uma decisA?o final.
        MecA?nica: Voto MajoritA?rio ou Filtro IA.
        """
        tech_signals = self.calculate_signals()
        ai_signal = self.get_ai_prediction(rl_model)
        spy_signal = self.get_spy_signal(spy_status)
        
        # DEBUG: Logar sinais para depuração (visto no terminal de automação)
        print(f"DEBUG [{self.bot.name}]: Tech={tech_signals} | AI={ai_signal} | Spy={spy_signal}")

        # Filtro de IA se habilitado
        if self.ai.get("rl_active") and self.ai.get("mode") == "pure_ia":
            return ai_signal
            
        # LA?gica HA?brida:
        # Se algum sinal tA?cnico estiver contra a IA, nA?o opera.
        final_vote = 0
        active_votes = 0
        
        for s_name, val in tech_signals.items():
            if val != 0:
                final_vote += val
                active_votes += 1
        
        if self.spy.get("active") and spy_signal != 0:
            final_vote += spy_signal
            active_votes += 1
            
        if self.ai.get("rl_active") and ai_signal != 0:
            final_vote += ai_signal
            active_votes += 1
            
        if active_votes == 0: return 0
        
        # Retorna BUY se a maioria for positiva, SELL se for negativa
        if final_vote > 0: 
            print(f"DEBUG [{self.bot.name}]: VOTO FINAL COMPRA (+{final_vote})")
            return 1
        if final_vote < 0: 
            print(f"DEBUG [{self.bot.name}]: VOTO FINAL VENDA ({final_vote})")
            return -1
        return 0
