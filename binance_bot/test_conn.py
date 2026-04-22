import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_SECRET_KEY'),
    })
    exchange.set_sandbox_mode(True)
    
    try:
        balance = exchange.fetch_balance()
        print("CONEXÃO SUCESSO!")
        print(f"Saldo USDT: {balance['total'].get('USDT', 0)}")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    test_connection()
