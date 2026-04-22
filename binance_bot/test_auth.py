import ccxt
import time

def test_auth_only():
    api = "fBTeOAxJJJBMeLsUI1vJ5Rdt42BJN8cD1QXaEGumYwsI264y4f4fnFXKc53eBP5m"
    sec = "7Xj42KMirUNm0WFTLDrxIba3HNFYfv83EedEuXUVjU6lU4F5qJ7dSZBpqm5SG4Dr"
    
    exchange = ccxt.binance({
        'apiKey': api,
        'secret': sec,
        'options': {'defaultType': 'future'}
    })
    exchange.set_sandbox_mode(True)
    
    # Adicionando um timestamp manual para evitar erro de sincronia de relógio
    exchange.options['adjustForTimeDifference'] = True
    
    try:
        print("Tentando autenticar saldo...")
        balance = exchange.fetch_balance()
        print(f"SUCESSO! Saldo USDT: {balance['total'].get('USDT', 0)}")
    except Exception as e:
        print(f"RESULTADO: {e}")

if __name__ == "__main__":
    test_auth_only()
