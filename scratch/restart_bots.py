import httpx
import time

BASE_URL = "http://localhost:8000"

def restart_all_bots():
    with httpx.Client(timeout=10.0) as client:
        # Pega a lista de bots
        bots = client.get(f"{BASE_URL}/bots/").json()
        active_ids = [b['id'] for b in bots if b['active']]
        
        print(f">>> Reiniciando {len(active_ids)} bots para aplicar as novas regras relaxadas...")
        
        for bot_id in active_ids:
            # Para o bot
            print(f"Parando Bot {bot_id}...")
            client.post(f"{BASE_URL}/bots/{bot_id}/stop")
            time.sleep(1)
            
            # Inicia o bot (isso carregará a nova config do DB)
            print(f"Iniciando Bot {bot_id}...")
            client.post(f"{BASE_URL}/bots/{bot_id}/start")
            time.sleep(1)
            
        print("\nTodos os bots foram reiniciados com as regras agressivas!")

if __name__ == "__main__":
    restart_all_bots()
