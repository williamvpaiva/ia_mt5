import httpx
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
BRIDGE_URL = "http://localhost:5000"

def monitor():
    print(f"--- Monitoramento de Trades Iniciado ({datetime.now().strftime('%H:%M:%S')}) ---")
    print("Aguardando novas operações dos bots otimizados...")
    
    known_tickets = set()
    
    # Pegar tickets atuais para não repetir
    try:
        initial_pos = httpx.get(f"{BRIDGE_URL}/positions").json()
        known_tickets = {p['ticket'] for p in initial_pos}
        if known_tickets:
            print(f"Monitorando (ignorando {len(known_tickets)} posições já abertas)")
    except:
        print("Aviso: Não foi possível ler posições iniciais (Bridge offline?)")

    start_time = time.time()
    query_count = 0
    
    try:
        while time.time() - start_time < 300:  # Monitorar por 5 minutos
            query_count += 1
            if query_count % 12 == 0: # A cada minuto aprox (5s * 12)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Monitorando sinais e posições...")

            # 1. Checar Posições no Bridge
            try:
                positions = httpx.get(f"{BRIDGE_URL}/positions", timeout=5.0).json()
                for p in positions:
                    if p['ticket'] not in known_tickets:
                        print(f"\n🔔 NOVO TRADE DETECTADO!")
                        print(f"Bot (Magic): {p.get('magic')}")
                        print(f"Símbolo: {p['symbol']}")
                        print(f"Direção: {'COMPRA' if p['type'] == 0 else 'VENDA'}")
                        print(f"Volume: {p['volume']}")
                        print(f"Preço: {p['price_open']}")
                        print(f"SL/TP: {p.get('sl')} / {p.get('tp')}")
                        known_tickets.add(p['ticket'])
            except:
                pass

            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nMonitoramento encerrado pelo usuário.")
    
    print("\nFim do período de monitoramento de 5 minutos.")

if __name__ == "__main__":
    monitor()
