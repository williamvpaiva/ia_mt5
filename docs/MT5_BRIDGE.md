# MT5 Bridge - Documentação

Correção: Documentação da Bridge MT5 conforme especificação
Prioridade: BAIXA

## Visão Geral

A Bridge MT5 conecta o MetaTrader 5 (rodando no Windows) com a plataforma IA_MT5 (rodando em Docker/Linux).

## Arquitetura

```
┌─────────────────┐      HTTP/REST       ┌─────────────────┐
│   MetaTrader 5  │ ◄─────────────────►  │   IA_MT5 Backend│
│   (Windows)     │      WebSocket       │   (Docker)      │
└─────────────────┘                      └─────────────────┘
        │                                      │
        │ MT5 Python API                       │ FastAPI
        │                                      │
        ▼                                      ▼
┌─────────────────┐                      ┌─────────────────┐
│  mt5_bridge.py  │                      │  API Routes     │
│  (Host Windows) │                      │  (Container)    │
└─────────────────┘                      └─────────────────┘
```

## Instalação no Host Windows

### 1. Pré-requisitos

```bash
# Python 3.9+
pip install MetaTrader5 fastapi uvicorn pydantic
```

### 2. Configurar Bridge

```bash
# Copiar script para local adequado
cp scripts/mt5_bridge.py C:/ia_mt5_bridge/

# Configurar variáveis de ambiente
set MT5_LOGIN=12345678
set MT5_PASSWORD=sua_senha
set MT5_SERVER=Sua_Corretora
set BRIDGE_PORT=5000
```

### 3. Iniciar Bridge

```bash
# PowerShell (como Administrador)
cd C:/ia_mt5_bridge
python mt5_bridge.py

# Ou como serviço Windows
python mt5_bridge.py --service
```

## Comandos da Bridge

### Health Check
```bash
curl http://localhost:5000/health
```

### Obter Cotações
```bash
curl http://localhost:5000/rates?symbol=WIN&timeframe=M5&count=100
```

### Executar Ordem
```bash
curl -X POST http://localhost:5000/order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "WIN",
    "action": "BUY",
    "volume": 1.0,
    "price": 0.0,
    "sl": 11500,
    "tp": 11700
  }'
```

### Fechar Ordem
```bash
curl -X POST http://localhost:5000/close \
  -H "Content-Type: application/json" \
  -d '{
    "ticket": 123456,
    "volume": 1.0
  }'
```

### Obter Posições
```bash
curl http://localhost:5000/positions
```

### Obter Histórico
```bash
curl http://localhost:5000/history?days=30
```

## Configuração Docker Compose

A bridge roda no host Windows, não em container:

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - MT5_BRIDGE_URL=http://host.docker.internal:5000
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Segurança

### API Key (Recomendado)

```bash
# .env da bridge
BRIDGE_API_KEY=sua_chave_secreta

# Backend
MT5_BRIDGE_API_KEY=sua_chave_secreta
```

### Firewall Windows

```powershell
# Permitir porta da bridge
New-NetFirewallRule -DisplayName "MT5 Bridge" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

## Troubleshooting

### Bridge não conecta ao MT5

```bash
# Verificar se MT5 está aberto
# Verificar conta logada
# Verificar permissões de API no MT5
```

### Docker não acessa bridge

```bash
# Verificar se host.docker.internal está acessível
curl http://host.docker.internal:5000/health

# Reiniciar bridge no host
```

## Scripts Úteis

### Iniciar Bridge (Windows)

```powershell
# start_bridge.ps1
$env:MT5_LOGIN = "12345678"
$env:MT5_PASSWORD = "senha"
$env:MT5_SERVER = "Corretora"
python mt5_bridge.py
```

### Testar Conexão

```bash
# test_bridge.sh
curl http://localhost:5000/health
curl http://localhost:5000/info
```

## Métricas

A bridge expõe métricas em `/metrics`:

```json
{
  "uptime": 3600,
  "orders_sent": 150,
  "orders_failed": 2,
  "last_order_time": "2024-01-15T10:30:00Z",
  "mt5_connected": true,
  "mt5_account": "12345678"
}
```
