import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd

class TradingEnv(gym.Env):
    """
    Ambiente customizado para Treinamento por ReforA?o em Trading.
    """
    def __init__(self, df, initial_balance=10000, lot_size=1):
        super(TradingEnv, self).__init__()
        
        # Garante que o DF tenha apenas as colunas necessarias e sem indices extras
        cols_to_keep = ['open', 'high', 'low', 'close', 'tick_volume', 'EMA_9', 'EMA_21', 'RSI', 'ATR']
        existing_cols = [c for c in cols_to_keep if c in df.columns]
        self.df = df[existing_cols].reset_index(drop=True)
        
        print(f"DEBUG RL_ENV: FINAL SHAPE {self.df.shape}")
        print(f"DEBUG RL_ENV: COLUMNS {self.df.columns.tolist()}")
        
        self.initial_balance = initial_balance
        self.lot_size = lot_size
        
        # Acoes: 0=Ficar fora, 1=Comprar, 2=Vender
        self.action_space = spaces.Discrete(3)
        
        # Observacao: Baseado no tamanho real do DF apos filtragem
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.df.shape[1],), dtype=np.float32
        )
        
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.balance = self.initial_balance
        self.current_step = 0
        self.position = 0 # 0: none, 1: buy, 2: sell
        self.entry_price = 0
        self.total_pnl = 0
        
        return self._get_observation(), {}

    def _get_observation(self):
        return self.df.iloc[self.current_step].values.astype(np.float32)

    def step(self, action):
        done = False
        reward = 0
        
        current_price = self.df.iloc[self.current_step]['close']
        
        # LA?gica de Recompensa e PosiA?A?o
        if action == 1: # Comprar
            if self.position == 0:
                self.position = 1
                self.entry_price = current_price
            elif self.position == 2: # Fecha venda e abre compra
                pnl = (self.entry_price - current_price) * self.lot_size
                reward += pnl
                self.position = 1
                self.entry_price = current_price
                
        elif action == 2: # Vender
            if self.position == 0:
                self.position = 2
                self.entry_price = current_price
            elif self.position == 1: # Fecha compra e abre venda
                pnl = (current_price - self.entry_price) * self.lot_size
                reward += pnl
                self.position = 2
                self.entry_price = current_price
                
        elif action == 0: # Sair/Ficar fora
            if self.position != 0:
                pnl = (current_price - self.entry_price) * self.lot_size if self.position == 1 else (self.entry_price - current_price) * self.lot_size
                reward += pnl
                self.position = 0
                self.entry_price = 0

        self.current_step += 1
        
        if self.current_step >= len(self.df) - 1:
            done = True
            
        # PuniA?A?o por tempo se nA?o estiver ganhando
        reward -= 0.01 
        
        self.total_pnl += reward
        self.balance += reward
        
        # Penalidade de morte se o balanA?o cair muito
        if self.balance < self.initial_balance * 0.5:
            done = True
            reward -= 100
            
        return self._get_observation(), reward, done, False, {}
# TESTE DE ESCRITA
