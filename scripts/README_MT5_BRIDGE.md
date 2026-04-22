# MT5 Bridge - Guia de Inicialização

## Visão Geral

A **MT5 Bridge** é a ponte de comunicação entre o backend (Docker) e o terminal MetaTrader 5 (Windows). Ela precisa rodar **fora do Docker** porque o MT5 é uma aplicação desktop Windows.

## Pré-requisitos

1. **MetaTrader 5 instalado** em `C:\Program Files\MetaTrader 5 Terminal`
2. **Python 3.11+** instalado no Windows
3. **Conta corretora** configurada no MT5
4. **MT5 Terminal aberto e logado** na sua conta

## Instalação

### 1. Instalar dependências Python

```bash
cd D:\PROJETOS\IA_MT5
pip install MetaTrader5 fastapi uvicorn pydantic
```

### 2. Verificar instalação do MT5

```bash
python -c "import MetaTrader5 as mt5; print(mt5.initialize())"
```

Se retornar `True`, a MT5 está acessível.

## Inicialização

### Opção 1: Script Batch (Recomendado)

```bash
cd D:\PROJETOS\IA_MT5\scripts
start_mt5_bridge.bat
```

### Opção 2: Comando direto

```bash
cd D:\PROJETOS\IA_MT5\scripts
python -m uvicorn mt5_bridge:app --host 0.0.0.0 --port 5000 --reload
```

### Opção 3: PowerShell com Python path absoluto

```powershell
cd D:\PROJETOS\IA_MT5\scripts
py -m uvicorn mt5_bridge:app --host 0.0.0.0 --port 5000 --reload
```

## Verificação

Após iniciar, teste a bridge:

```bash
# Health check
curl http://localhost:5000/health

# Deve retornar:
# {"status":"ok","mt5_connected":true}
```

## Endpoints da API

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health` | GET | Verifica saúde da conexão MT5 |
| `/rates/{symbol}` | GET | Busca cotações históricas |
| `/tick/{symbol}` | GET | Cotação em tempo real |
| `/order` | POST | Envia ordem de compra/venda |
| `/positions` | GET | Lista posições abertas |
| `/position/{ticket}` | DELETE | Fecha posição |

## Exemplos de Uso

### Buscar cotações WIN$

```bash
curl "http://localhost:5000/rates/WIN$?timeframe=M5&count=100"
```

### Buscar tick atual

```bash
curl "http://localhost:5000/tick/WIN$"
```

### Criar ordem de compra

```bash
curl -X POST "http://localhost:5000/order" \
  -H "Content-Type: application/json" \
  -d "{
    \"symbol\": \"WIN$\",
    \"action\": \"buy\",
    \"volume\": 0.10,
    \"sl\": 95000,
    \"tp\": 97000,
    \"magic\": 12345,
    \"comment\": \"Teste IA_MT5\"
  }"
```

### Listar posições

```bash
curl "http://localhost:5000/positions"
```

## Configuração no Docker

O docker-compose já está configurado para conectar na bridge:

```yaml
services:
  backend:
    environment:
      - MT5_BRIDGE_URL=http://host.docker.internal:5000
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Isso permite que o container acesse `host.docker.internal:5000` que aponta para `localhost:5000` no Windows.

## Troubleshooting

### Erro: "Failed to initialize MT5"

- Verifique se o MT5 Terminal está aberto
- Verifique se está logado em uma conta
- Reinicie o terminal MT5

### Erro: "Module MetaTrader5 not found"

```bash
pip install MetaTrader5
# ou
py -m pip install MetaTrader5
```

### Erro: "All connection attempts failed" (Backend)

- Verifique se a bridge está rodando (`curl http://localhost:5000/health`)
- Verifique se o container consegue acessar o host (`host.docker.internal`)
- Reinicie o container: `docker restart ia_mt5_backend`

### Bridge não inicia

1. Verifique se a porta 5000 não está em uso
2. Tente outra porta: `--port 5001`
3. Atualize o `.env`: `MT5_BRIDGE_URL=http://host.docker.internal:5001`

## Fluxo de Inicialização

1. **Abrir MT5 Terminal** e logar na conta
2. **Iniciar MT5 Bridge**: `start_mt5_bridge.bat`
3. **Verificar saúde**: `curl http://localhost:5000/health`
4. **Iniciar Docker**: `docker-compose --profile full up -d`
5. **Acessar frontend**: `http://localhost:8501`

## Segurança

- A bridge roda apenas em `localhost` (não exponha para rede externa)
- Use firewall para bloquear acesso externo à porta 5000
- Em produção, implemente autenticação na API

## Próximos Passos

1. ✅ Instalar dependências
2. ✅ Iniciar bridge
3. ✅ Verificar saúde
4. ✅ Testar endpoints
5. ✅ Conectar backend

## Documentação Relacionada

- [MT5 Bridge API](./MT5_BRIDGE.md)
- [Backend Setup](../backend/README.md)
- [Docker Setup](../README.md)
