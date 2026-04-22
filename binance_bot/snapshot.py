import os
import ccxt
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_snapshot():
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'options': {'defaultType': 'future'}
    })
    exchange.set_sandbox_mode(True)

    try:
        balance = exchange.fetch_balance()
        total_balance = float(balance['total']['USDT'])
        initial_capital = 5000.0
        
        # Posições Ativas
        positions_info = exchange.fetch_positions()
        active_positions = [p for p in positions_info if float(p['contracts']) > 0]
        
        # Lucro Flutuante Total
        unrealized_pnl = sum(float(p['unrealizedPnl']) for p in active_positions)
        
        print("="*60)
        print("     RELATÓRIO MULTI-BOT SNIPER & GRID")
        print("="*60)
        print(f"SALDO CARTEIRA:   ${total_balance:.2f} USDT")
        print(f"LUCRO FLUTUANTE:  ${unrealized_pnl:+.4f} USDT")
        print(f"RESULTADO TOTAL:  ${(total_balance - initial_capital + unrealized_pnl):+.4f} USDT")
        
        print("\n--- POSIÇÕES ATIVAS ---")
        if active_positions:
            for p in active_positions:
                print(f"• {p['symbol']:<15} | Lado: {p['side'].upper():5} | Qtd: {p['contracts']:<10} | Entrada: {p['entryPrice']:<10} | PnL: ${float(p['unrealizedPnl']):+.2f}")
        else:
            print("Nenhuma posição aberta no momento.")

        print("\n--- ORDENS PENDENTES (LIVRO) ---")
        for sym in ['BTC/USDT', '1000PEPE/USDT']:
            orders = exchange.fetch_open_orders(sym)
            if orders:
                print(f"• {sym:<15}: {len(orders)} ordens ativas.")
        
        print("="*60)

    except Exception as e:
        print(f"Erro ao capturar snapshot: {e}")

if __name__ == "__main__":
    get_snapshot()
