import ccxt

def test_hardcoded():
    api = "fBTeOAxJJJBMeLsUI1vJ5Rdt42BJN8cD1QXaEGumYwsI264y4f4fnFXKc53eBP5m"
    sec = "7Xj42KMirUNm0WFTLDrxIba3HNFYfv83EedEuXUVjU6lU4F5qJ7dSZBpqm5SG4Dr"
    
    print(f"Testando com API iniciada em: {api[:5]}...")
    
    exchange = ccxt.binance({
        'apiKey': api,
        'secret': sec,
        'verbose': True,
    })
    exchange.set_sandbox_mode(True)
    
    try:
        # Tenta pegar o tempo do servidor antes (não precisa de auth)
        server_time = exchange.fetch_time()
        print(f"Conexão com servidor OK. Time: {server_time}")
        
        # Tenta autenticar
        balance = exchange.fetch_balance()
        print("AUTENTICAÇÃO SUCESSO!")
        print(f"Saldo USDT: {balance['total'].get('USDT', 0)}")
    except Exception as e:
        print(f"Erro detalhado: {e}")

if __name__ == "__main__":
    test_hardcoded()
