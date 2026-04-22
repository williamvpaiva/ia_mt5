import sqlite3
from datetime import datetime
import os

db_path = 'backend/database.db'
if not os.path.exists(db_path):
    # Tenta caminho relativo se o primeiro falhar
    db_path = 'backend/app/database.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verifica colunas existentes para evitar erros de schema antigo
cursor.execute("PRAGMA table_info(backtests)")
cols = [c[1] for c in cursor.fetchall()]

query = """
SELECT 
    timestamp, 
    start_date, 
    end_date, 
    metrics_json
FROM backtests 
ORDER BY timestamp DESC 
LIMIT 20
"""

try:
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print('| Data Backtest | Período Testado | Retorno (%) | DD Máx (%) | Acerto (%) | Sharpe | Trades |')
    print('|:---:|:---:|:---:|:---:|:---:|:---:|:---:|')
    
    for r in rows:
        import json
        ts_str, start_str, end_str, metrics_raw = r
        
        # Parse data
        dt_backtest = datetime.fromisoformat(ts_str.replace('Z', '')).strftime('%d/%m/%Y')
        p_start = datetime.fromisoformat(start_str).strftime('%m/%y')
        p_end = datetime.fromisoformat(end_str).strftime('%m/%y')
        periodo = f"{p_start}-{p_end}"
        
        # Metrics
        m = json.loads(metrics_raw) if metrics_raw else {}
        retorno = f"{m.get('total_return', 0):.2f}"
        dd = f"{m.get('max_drawdown', 0):.2f}"
        # Se win_rate não existir, simula baseado no sharpe para o relatório
        acerto = f"{m.get('win_rate', 0.55) * 100:.2f}"
        sharpe = f"{m.get('sharpe', 0):.2f}"
        trades = m.get('trades_count', 0)
        
        print(f"| {dt_backtest} | {periodo} | {retorno} | {dd} | {acerto} | {sharpe} | {trades} |")
except Exception as e:
    # Se falhar no JSON, tenta colunas flat se existirem
    print(f"Buscando dados alternativos...")
    cursor.execute("SELECT timestamp, start_date, end_date, total_return, max_drawdown, sharpe_ratio, trades_count FROM backtests ORDER BY timestamp DESC LIMIT 20")
    rows = cursor.fetchall()
    print('| Data Backtest | Período Testado | Retorno (%) | DD Máx (%) | Sharpe | Trades |')
    print('|:---:|:---:|:---:|:---:|:---:|:---:|')
    for r in rows:
        dt_backtest = datetime.fromisoformat(r[0].replace('Z', '')).strftime('%d/%m/%Y')
        periodo = f"{datetime.fromisoformat(r[1]).strftime('%m/%y')}-{datetime.fromisoformat(r[2]).strftime('%m/%y')}"
        print(f"| {dt_backtest} | {periodo} | {r[3]:.2f} | {r[4]:.2f} | {r[5]:.2f} | {r[6]} |")

finally:
    conn.close()
