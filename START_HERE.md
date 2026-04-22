# Guia de Inicialização - IA MT5

## Status Atual

✅ **Backend**: 14/16 correções implementadas  
✅ **Banco de Dados**: Schema atualizado com todas as colunas  
✅ **Frontend**: Streamlit rodando sem erros  
✅ **MT5 Bridge**: Configurada e pronta para inicializar  
⚠️ **MT5 Terminal**: Requer inicialização manual

## Passo a Passo para Inicializar

### 1. Abrir MetaTrader 5

1. Abra o **MetaTrader 5** em `C:\Program Files\MetaTrader 5 Terminal\terminal64.exe`
2. Faça login na sua conta da corretora
3. Certifique-se de que o terminal está conectado

### 2. Iniciar MT5 Bridge

Abra um terminal PowerShell e execute:

```powershell
cd D:\PROJETOS\IA_MT5\scripts
python -m uvicorn mt5_bridge:app --host 0.0.0.0 --port 5000 --reload
```

**Ou use o script batch:**

```powershell
cd D:\PROJETOS\IA_MT5\scripts
.\start_mt5_bridge.bat
```

### 3. Verificar MT5 Bridge

Em outro terminal, teste:

```powershell
curl http://localhost:5000/health
```

Deve retornar:
```json
{"status": "ok", "mt5_connected": true}
```

### 4. Iniciar Docker (se não estiver rodando)

```powershell
cd D:\PROJETOS\IA_MT5
docker-compose --profile full up -d
```

### 5. Acessar o Dashboard

Acesse: **http://localhost:8501**

## Estrutura Atual

### Backend (Docker)
- ✅ API de Trades completa
- ✅ Risk Bot (gerenciamento de risco por bot)
- ✅ Backtester com lógica real
- ✅ AI Orchestrator (Bull/Bear Engine)
- ✅ Bot Manager com Trading Schedule
- ✅ Data Collector configurável
- ✅ WebSocket para alertas
- ✅ Logging estruturado

### Frontend (Docker)
- ✅ Streamlit Dashboard
- ✅ Listagem de bots
- ✅ Controle de status (start/stop)

### Banco de Dados (PostgreSQL)
- ✅ Tabela `bots` com todas as colunas
- ✅ Tabela `trades` completa
- ✅ Tabela `historical_data`
- ✅ Índices de performance

### MT5 Bridge (Windows - Requer ação manual)
- ⚠️ Precisa ser inicializada manualmente
- ⚠️ Requer MT5 Terminal aberto
- ✅ Scripts prontos em `D:\PROJETOS\IA_MT5\scripts\`

## Comandos Úteis

### Verificar status dos containers

```powershell
docker ps -a --filter "name=ia_mt5"
```

### Logs do backend

```powershell
docker logs ia_mt5_backend --tail 50
```

### Logs do frontend

```powershell
docker logs ia_mt5_frontend --tail 50
```

### Reiniciar backend

```powershell
docker restart ia_mt5_backend
```

### Parar tudo

```powershell
docker-compose --profile full down
```

## Próximos Passos Sugeridos

1. **Testar MT5 Bridge manualmente** para validar conexão
2. **Criar primeiro bot** via API ou frontend
3. **Configurar símbolos** (WIN$, IND$, etc.)
4. **Testar backtester** com dados históricos
5. **Configurar Ollama** para IA local (opcional)

## Problemas Conhecidos

### MT5 Bridge não inicia
- Verifique se MT5 Terminal está aberto
- Verifique se está logado em uma conta
- Teste: `python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.last_error())"`

### Backend não conecta na Bridge
- Verifique se `host.docker.internal` está acessível
- Teste: `curl http://host.docker.internal:5000/health`
- Reinicie o backend: `docker restart ia_mt5_backend`

### Erro de colunas faltantes
- Já resolvido com migration aplicada
- Se persistir, reinicie o backend

## Arquivos Importantes

- `scripts/mt5_bridge.py` - Ponte MT5
- `scripts/start_mt5_bridge.bat` - Script de inicialização
- `scripts/README_MT5_BRIDGE.md` - Documentação completa da Bridge
- `backend/app/services/mt5_client.py` - Cliente MT5 do backend
- `CORRECOES.md` - Lista de correções implementadas
- `PROJETO.md` - Especificação original do projeto

## Contato e Suporte

- Documentação: `D:\PROJETOS\IA_MT5\docs\`
- Logs: `D:\PROJETOS\IA_MT5\logs\`
- Backups: `D:\PROJETOS\IA_MT5\backups\`
