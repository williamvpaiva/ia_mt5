import asyncio
import ccxt.pro as ccxt
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

async def cleanup_all():
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'options': {'defaultType': 'future'},
    })
    exchange.set_sandbox_mode(True)
    
    logger.info("Iniciando LIMPEZA GLOBAL (Todas as ordens e posições)...")
    
    try:
        # 1. Pega todas as posições abertas
        account_info = await exchange.fetch_positions()
        active_positions = [p for p in account_info if float(p['contracts']) > 0]
        
        # 2. Fecha todas as posições a mercado
        for p in active_positions:
            symbol = p['symbol']
            side = 'sell' if p['side'] == 'long' else 'buy'
            await exchange.cancel_all_orders(symbol) # Cancela ordens do par primeiro
            await exchange.create_order(symbol, 'market', side, p['contracts'], params={'reduceOnly': True})
            logger.warning(f"Posição FECHADA: {symbol} | Qtd: {p['contracts']}")

        # 3. Garante que qualquer ordem solta seja cancelada (nos símbolos principais)
        for s in ['BTC/USDT', '1000PEPE/USDT']:
             await exchange.cancel_all_orders(s)
             
        logger.success("CONTA ZERADA! Tudo fechado e cancelado.")
        await exchange.close()
        
    except Exception as e:
        logger.error(f"Erro na limpeza global: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_all())
