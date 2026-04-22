import asyncio
import ccxt.pro as ccxt
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

async def cleanup():
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'options': {'defaultType': 'future'},
    })
    exchange.set_sandbox_mode(True)
    
    symbol = 'BTC/USDT'
    logger.info(f"Iniciando captura de dados de {symbol}...")
    
    # 2. Fechar Posição
        await exchange.cancel_all_orders(symbol)
        logger.info("Ordens canceladas.")
        
        # Fechar Posição
        positions = await exchange.fetch_positions([symbol])
        active = [p for p in positions if float(p['contracts']) > 0]
        if active:
            p = active[0]
            side = 'sell' if p['side'] == 'long' else 'buy'
            await exchange.create_order(symbol, 'market', side, p['contracts'], params={'reduceOnly': True})
            logger.info(f"Posição de {p['contracts']} fechada.")
        
        await exchange.close()
        logger.success("Limpeza concluída! Pronto para o BTC.")
    except Exception as e:
        logger.error(f"Erro na limpeza: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup())
