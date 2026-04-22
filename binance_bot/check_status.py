import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

def check_status():
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'options': {'defaultType': 'future'}
    })
    exchange.set_sandbox_mode(True)
    
    try:
        # 1. Saldo
        balance = exchange.fetch_balance()
        usdt_total = balance['total'].get('USDT', 0)
        usdt_free = balance['free'].get('USDT', 0)
        
        # 2. Ordens Abertas
        orders = exchange.fetch_open_orders('1000PEPE/USDT')
        
        # 3. Posições Abertas
        positions = exchange.fetch_positions(['1000PEPE/USDT'])
        active_pos = [p for p in positions if float(p['contracts']) > 0]
        
        print("--- STATUS ATUAL (FUTUROS TESTNET) ---")
        print(f"Saldo Total: {usdt_total:.2f} USDT")
        print(f"Saldo Disponível: {usdt_free:.2f} USDT")
        print(f"Número de Ordens na Grade: {len(orders)}")
        
        if len(orders) > 0:
            print("\nÚltimas 3 Ordens na Grade:")
            for o in orders[:3]:
                print(f" - {o['side'].upper()} | Preço: {o['price']} | Quantidade: {o['amount']}")
        
        if active_pos:
            print("\nPosições Ativas:")
            for p in active_pos:
                print(f" - Lado: {p['side']} | Tamanho: {p['contracts']} | Lucro Não-Realizado: {p['unrealizedPnl']} USDT")
        else:
            print("\nNenhuma posição aberta ainda (aguardando execução da grade).")
            
    except Exception as e:
        print(f"Erro ao buscar status: {e}")

if __name__ == "__main__":
    check_status()
