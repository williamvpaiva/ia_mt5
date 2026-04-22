import sys
import os
import pandas as pd
import pandas_ta as ta
import httpx
import numpy as np

# Mocking parts of the app for diagnosis
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def diagnose_bot_2():
    print("--- Diagnóstico de Decisão: Bot 2 ---")
    
    # 1. Pegar dados do MT5 via Bridge
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("http://localhost:5000/rates/WINM26?timeframe=M1&count=200")
            rates = res.json()
    except Exception as e:
        print(f"Erro ao pegar dados: {e}")
        return

    df = pd.DataFrame(rates)
    
    # 2. Pegar Config do Bot no Banco
    from backend.app.core.database import SessionLocal
    from backend.app.models.bot import Bot
    db = SessionLocal()
    bot = db.query(Bot).filter(Bot.id == 2).first()
    
    print(f"Bot Config: Mode={bot.ai_config.get('mode')}, Magic={bot.magic_number}")
    print(f"Signals Active: {bot.signals_config}")

    # 3. Executar Lógica do Decisor
    from backend.app.engine.decisor import HybridDecisor
    decisor = HybridDecisor(bot, df)
    
    signals = decisor.calculate_signals()
    print(f"Sinais Técnicos Calculados: {signals}")
    
    ai_pred = decisor.get_ai_prediction(None) # Sem modelo
    print(f"Predição IA (Sem Modelo): {ai_pred}")
    
    decision = decisor.decide(None)
    print(f"Decisão Final: {decision} (1=Buy, -1=Sell, 0=Neutral)")
    
    db.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(diagnose_bot_2())
