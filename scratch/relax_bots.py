import httpx

BASE_URL = "http://localhost:8000"

def relax_rules():
    with httpx.Client(timeout=10.0) as client:
        print(">>> Relaxando as regras de entrada para aumentar a frequência de trades...")
        
        # Otimização agressiva para o Bot 2
        relaxed_config = {
            "signals_config": {
                "ma_cross": {"active": True, "fast_period": 3, "slow_period": 8}, # Cruzamento ultra rápido
                "rsi": {"active": True, "period": 7, "overbought": 85, "oversold": 15}, # Quase ignorando RSI
                "atr": {"active": True, "period": 10, "multiplier": 0.8}, # Extremamente sensível à volatilidade
                "price_action": {"active": False} # Removido para liberar mais entradas
            },
            "ai_config": {
                "rl_active": True,
                "mode": "hybrid" 
            },
            "risk_config": {
                "max_risk_per_trade": 0.05 # Aumentado risco para 5%
            }
        }
        
        res = client.put(f"{BASE_URL}/bots/2", json=relaxed_config)
        if res.status_code == 200:
            print("Regras relaxadas! O robô agora está em modo AGRESSIVO.")
        else:
            print(f"Erro ao relaxar regras: {res.text}")

if __name__ == "__main__":
    relax_rules()
