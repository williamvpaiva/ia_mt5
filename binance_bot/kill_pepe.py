import asyncio
import ccxt.pro as ccxt
import os
from dotenv import load_dotenv

load_dotenv()

async def kill_pepe():
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'options': {'defaultType': 'future'},
    })
    exchange.set_sandbox_mode(True)
    
    # Lista de possíveis variações de símbolo da PEPE
    symbols = ['1000PEPE/USDT', '1000PEPEUSDT', 'PEPE/USDT']
    
    print("Iniciando remoção forçada de ordens PEPE...")
    
    for symbol in symbols:
        try:
            # Cancela todas as ordens deste par especificamente
            await exchange.cancel_all_orders(symbol)
            print(f"Limpeza de ordens concluída para: {symbol}")
        except Exception:
            pass # Pares que não existem na Testnet são ignorados

    # Verifica se há qualquer ordem aberta sobrando na conta inteira e remove
    try:
        all_orders = await exchange.fetch_open_orders()
        for o in all_orders:
            if 'PEPE' in o['symbol']:
                await exchange.cancel_order(o['id'], o['symbol'])
                print(f"Ordem residual cancelada: {o['id']} em {o['symbol']}")
    except:
        pass

    await exchange.close()
    print("Processo concluído.")

if __name__ == "__main__":
    asyncio.run(kill_pepe())
