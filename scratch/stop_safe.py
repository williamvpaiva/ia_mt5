import httpx
import subprocess
import time
import os

BASE_URL = "http://localhost:8000"

def stop_mt5_bots():
    print(">>> Parando robôs do MetaTrader 5...")
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{BASE_URL}/bots/")
            if response.status_code == 200:
                bots = response.json()
                active_ids = [b['id'] for b in bots if b['active']]
                for bot_id in active_ids:
                    print(f"Parando Bot {bot_id}...")
                    client.post(f"{BASE_URL}/bots/{bot_id}/stop")
                    time.sleep(0.5)
            else:
                print(f"Erro ao buscar bots: {response.status_code}")
    except Exception as e:
        print(f"Erro ao conectar com a API: {e}")

def stop_binance_bots():
    print("\n>>> Parando robôs da Binance...")
    bots_to_stop = ["bot_grid.py", "bot_sniper_binance.py", "bot_directional_sniper.py"]
    
    for bot_file in bots_to_stop:
        print(f"Buscando e parando processos de {bot_file}...")
        # Usando wmic para matar o processo específico sem derrubar o backend
        cmd = f'wmic process where "CommandLine like \'%{bot_file}%\'" get processid'
        try:
            output = subprocess.check_output(cmd, shell=True).decode()
            pids = [line.strip() for line in output.split('\n')[1:] if line.strip()]
            for pid in pids:
                print(f"Matando PID {pid} ({bot_file})...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
        except Exception:
            print(f"Nenhum processo encontrado para {bot_file}")

if __name__ == "__main__":
    stop_mt5_bots()
    stop_binance_bots()
    print("\n--- Todos os robôs foram parados! ---")
