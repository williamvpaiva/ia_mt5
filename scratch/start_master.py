import httpx
import subprocess
import time
import os

BASE_URL = "http://localhost:8000"

def start_mt5_bots():
    print(">>> Iniciando robôs do MetaTrader 5...")
    try:
        with httpx.Client(timeout=10.0) as client:
            # Pega a lista de bots
            response = client.get(f"{BASE_URL}/bots/")
            if response.status_code != 200:
                print(f"Erro ao buscar bots: {response.status_code}")
                return
            
            bots = response.json()
            for bot in bots:
                bot_id = bot['id']
                print(f"Iniciando Bot {bot_id} ({bot['name']})...")
                res = client.post(f"{BASE_URL}/bots/{bot_id}/start")
                if res.status_code == 200:
                    print(f"Bot {bot_id} iniciado com sucesso!")
                else:
                    print(f"Falha ao iniciar Bot {bot_id}: {res.text}")
                time.sleep(1)
    except Exception as e:
        print(f"Erro ao conectar com a API: {e}")

def start_binance_bots():
    print("\n>>> Iniciando robôs da Binance...")
    binance_dir = "binance_bot"
    bots_to_start = ["bot_grid.py", "bot_sniper_binance.py", "bot_directional_sniper.py"]
    
    for bot_file in bots_to_start:
        file_path = os.path.join(binance_dir, bot_file)
        if os.path.exists(file_path):
            print(f"Iniciando Binance {bot_file} em background...")
            # Usando 'start' no Windows para abrir em nova janela e não travar o script
            # Ou apenas subprocess.Popen se quiser em background silencioso
            # Vou usar start para que o usuário possa ver a execução se desejar
            subprocess.Popen(["cmd", "/c", "start", "python", bot_file], cwd=binance_dir, shell=True)
            time.sleep(1)
        else:
            print(f"Arquivo não encontrado: {file_path}")

if __name__ == "__main__":
    start_mt5_bots()
    start_binance_bots()
    print("\n--- Todos os robôs foram processados! ---")
