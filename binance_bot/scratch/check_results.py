import ccxt, os
from dotenv import load_dotenv
load_dotenv()

def get_results():
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
        'options': {'defaultType': 'future'},
        'enableRateLimit': True
    })
    exchange.set_sandbox_mode(True)
    
    balance = exchange.fetch_balance()
    wallet_balance = float(balance['total']['USDT'])
    initial_capital = 5000.0
    total_pnl = wallet_balance - initial_capital
    
    positions = exchange.fetch_positions(['1000PEPE/USDT'])
    pos = None
    if positions:
        pos = positions[0]
        unrealized = float(pos['unrealizedPnl'])
    else:
        unrealized = 0.0

    print(f"--- STATUS CONSOLIDADO ---")
    print(f"Saldo em Carteira: ${wallet_balance:.2f}")
    print(f"Lucro/Prejuízo Total (Sessão): ${total_pnl:+.4f} ({(total_pnl/initial_capital)*100:+.3f}%)")
    
    if pos and float(pos['contracts']) > 0:
        print(f"Posição Aberta ({pos['side'].upper()}): {pos['contracts']} cont")
        print(f"PnL Flutuante: ${unrealized:+.4f}")
    else:
        print("Nenhuma posição aberta no momento.")

    # Analisando logs para separar contribuições (Simplificado)
    print("\n--- PERFORMANCE POR BOT (ESTIMADA) ---")
    print("Nota: Ambos operam no mesmo par. O Sniper é mais seletivo.")

if __name__ == "__main__":
    get_results()
