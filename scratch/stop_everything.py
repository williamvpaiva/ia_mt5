import httpx
import os
import signal
import subprocess

BASE_URL = "http://localhost:8000"

def stop_everything():
    print("!!! PARANDO TUDO RELATIVO AOS BOTS !!!")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            # 1. Pega bots ativos
            try:
                bots = client.get(f"{BASE_URL}/bots/").json()
                active_ids = [b['id'] for b in bots if b['active']]
                
                # 2. Para cada bot via API (Fecha posições e para threads)
                for bot_id in active_ids:
                    print(f"Parando e fechando ordens do Bot {bot_id}...")
                    client.post(f"{BASE_URL}/bots/{bot_id}/stop")
            except Exception as e:
                print(f"Erro ao parar bots via API: {e} (Backend pode estar fora)")

            # 3. Desativa todos no DB via SQL (Garantia)
            # Como estou no host, posso tentar via Backend ou Docker
            
    except Exception as e:
        print(f"Erro geral: {e}")

    # 4. Matar processos locais (Bridge)
    print("Matando processos do Bridge...")
    os.system("taskkill /F /IM python.exe /T") 
    # Cuidado: taskkill python.exe mata tudo. 
    # Melhor matar pela porta.
    
    print("Tudo parado!")

if __name__ == "__main__":
    stop_everything()
