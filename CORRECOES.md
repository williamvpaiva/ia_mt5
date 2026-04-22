# Correções e Recomendações - IA_MT5

## Visão Geral

Este documento lista todas as discrepâncias identificadas entre a especificação (`PROJETO.md`) e a implementação atual, com recomendações detalhadas de correção.

---

## 1. Frontend - Streamlit vs React Dashboard

### Problema
- **Especificação**: "Web dashboard React para gestão de bots" (linha ~60)
- **Implementação**: Streamlit (`frontend/streamlit_app.py`)

### Impacto
- Streamlit é limitado para dashboards interativos em tempo real
- Não suporta customização avançada de UI
- WebSocket limitado para alertas em tempo real

### Recomendação
Migrar para React/Next.js com:
- Dashboard em tempo real com WebSocket
- Gráficos TradingView ou Lightweight Charts
- Interface responsiva para gestão de bots

---

## 2. Backtester - Scores Fixos

### Problema
- **Arquivo**: `backend/app/services/backtester.py`
- **Implementação**: Scores fixos (ia_score=55, rsi=50) - apenas para teste

```python
# Linhas 62-63
ia_score = 55  # Simulação
rsi = 50  # Simulação
```

### Recomendação
Implementar lógica real de backtesting:
- Calcular RSI a partir dos dados históricos
- Integrar com IA Service para análise de sentimiento
- Calcular métricas: Sharpe Ratio, Drawdown, Win Rate
- Persistir resultados em banco de dados

---

## 3. AI Service - Arquitetura Simplificada

### Problema
- **Especificação**: "Motores Bull/Bear AI + Orquestrador para decisões buy/sell/neutral"
- **Implementação**: Serviço simples com apenas análise de sentimento

### Recomendação
Implementar arquitetura de orchestrator:
```
┌─────────────────┐
│   Orchestrator  │
├─────────────────┤
│ Bull AI Engine  │ ──► Buy signals
│ Bear AI Engine  │ ──► Sell signals
│ Consensus Layer │ ──► Neutral/hold
└─────────────────┘
```

Cada engine deve ter:
- Análise técnica独立
- Análise de sentimento
- scoring próprio

---

## 4. Modelo Ollama - Configuração

### Problema
- **Arquivo**: `backend/app/core/config.py`
- **Configuração atual**: `llama3.2:3b`

```python
OLLAMA_MODEL: str = "llama3.2:3b"  # 3B parâmetros
```

### Análise
- **llama3.2:3b**: ~3GB VRAM, bom para GPUs modernas
- Para VPS/servidores modestos:，推荐 modelos mais leves

### Recomendação
| Modelo | VRAM | Uso |
|--------|------|-----|
| `llama3.2:1b` | ~1GB | Produção (servidores modestos) |
| `phi3:3.8b` | ~2GB | Balance custo/qualidade |
| `llama3.2:3b` | ~3GB | Desenvolvimento |
| `mistral:7b` | ~4GB | Alta qualidade |

Para produção: usar `llama3.2:1b` ou `phi3:3.8b-mini`

---

## 5. Risk Management - Ausência de Risk por Bot

### Problema
- **Especificação**: "Risk Manager por bot + Global"
- **Implementação**: Apenas `risk_global.py` (gestão de risco global)

### Recomendação
Criar `risk_bot.py` para cada bot:
- Stop Loss por bot
- Take Profit por bot
- Max posições por bot
- Trailing stop

Estrutura sugerida:
```python
class RiskBot:
    stop_loss_pct: float
    take_profit_pct: float
    max_positions: int
    trailing_stop: bool
```

---

## 6. API Routes - Trades Incompleto

### Problema
- **Arquivo**: `backend/app/api/routes/trades.py`
- **Conteúdo**: Apenas 2 linhas (vazio)

### Recomendação
Implementar rotas completas:
```python
@router.get("/")           # Listar trades
@router.get("/{trade_id}") # Detalhar trade
@router.post("/")          # Criar trade (manual)
@router.delete("/{id}")    # Fechar trade
@router.get("/history")    # Histórico de trades
@router.get("/stats")     # Estatísticas
```

---

## 7. Data Collector - Intervalo de Sincronização

### Problema
- **Arquivo**: `backend/app/services/data_collector.py`
- **Intervalo**: 5 minutos fixos

```python
SYNC_INTERVAL = 300  # 5 minutos
```

### Recomendação
Tornar configurável:
- Timeframes menores (M1, M5): sincronização mais frequente
- Timeframes maiores (H1, D1): sincronização menos frequente
- Adicionar cache local para reduzir chamadas

---

## 8. Bot Manager - Horários de Trading

### Problema
- **Especificação**: "Horários de trading ativos configuráveis"
- **Implementação**: Não implementado

### Recomendação
Adicionar config de horário:
```python
class TradingSchedule:
    enabled: bool
    start_time: str  # "09:00"
    end_time: str    # "17:00"
    trading_days: list  # [1,2,3,4,5] # Seg-Sex
```

Verificar horário antes de executar trades.

---

## 9. Docker Compose - Bridge MT5

### Problema
- **Especificação**: "Bridge MT5 rodando no host Windows"
- **Implementação**: `scripts/mt5_bridge.py` existe mas não está integrado ao compose

### Recomendação
Ou:
1. Documentar que bridge deve rodar no host Windows
2. Ou criar container Docker separado para bridge

---

## 10. Modelos de Dados - Campos Faltantes

### Trade Model
**Arquivo**: `backend/app/models/trade.py`

Campos necessários adicionais:
```python
class Trade(Base):
    # ... campos existentes ...
    symbol: str
    entry_price: float
    exit_price: Optional[float]
    volume: float
    profit: Optional[float]
    commission: Optional[float]
    swap: Optional[float]
    magic_number: int  # Identificador do bot
    comment: Optional[str]
    ticket: Optional[int]  # Ticket MT5
```

### Bot Model
**Arquivo**: `backend/app/models/bot.py`

Adicionar campos:
```python
class Bot(Base):
    # ... campos existentes ...
    magic_number: int  # Única identificação
    max_spread: float
    max_slippage: float
    allowed_symbols: list[str]
```

---

## 11. WebSocket - Alertas em Tempo Real

### Problema
- **Especificação**: "Alertas WebSocket"
- **Implementação**: Não implementado

### Recomendação
Adicionar endpoint WebSocket:
```python
# backend/app/main.py
from fastapi import WebSocket

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    # Enviar alertas de trades, risco, etc.
```

Eventos:
- `trade_opened`
- `trade_closed`
- `risk_warning`
- `bot_error`

---

## 12. Backtesting - Métricas Faltantes

### Problema
- **Especificação**: "Métricas: Sharpe, Drawdown, Win Rate"
- **Implementação**: Não calculado

### Recomendação
Adicionar cálculo:
```python
def calculate_metrics(trades: list[Trade]) -> BacktestMetrics:
    return BacktestMetrics(
        total_trades=len(trades),
        win_rate=wins/total,
        profit_factor=gross_profit/gross_loss,
        sharpe_ratio=sharpe(returns),
        max_drawdown=max(drawdowns),
        avg_trade_duration=avg_duration,
        total_return=pct_return
    )
```

---

## 13. Docker - Estrutura

### Problema Atual
```yaml
# docker-compose.yml - resumido
services:
  backend:
    build: ./backend
  frontend:
    build: ./frontend
  redis:
    image: redis
  postgres:
    image: postgres
```

### Recomendação
```yaml
services:
  backend:
    build: ./backend
    depends_on: [postgres, redis]
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
  frontend:
    build: ./frontend  # Mudar para React
  redis:
    image: redis:alpine
  postgres:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
  ollama:
    image: ollama/ollama
    volumes:
      - ollama:/root/.ollama

volumes:
  pgdata:
  ollama:
```

---

## 14. Logging e Monitoramento

### Problema
- **Especificação**: "Logs detalhados + métricas"
- **Implementação**: logging básico

### Recomendação
Adicionar:
- structured logging (JSON)
- métricas Prometheus
- health checks

---

## 15. Testes Unitários

### Problema
- Nenhum teste encontrado

### Recomendação
Adicionar testes para:
- risk_calculator
- backtester
- ai_service
- bot_manager

---

## 16. Segurança

### Problema
- Não há autenticação/autorização

### Recomendação
Adicionar:
- JWT tokens
- API key para MT5 bridge
- Rate limiting
- CORS config

---

## Priorização

| Prioridade | Item | Esforço |
|------------|------|----------|
| 🔴 Alta | API Trades | Baixo |
| 🔴 Alta | Risk por Bot | Médio |
| 🟡 Média | Backtester real | Médio |
| 🟡 Média | AI Orchestrator | Alto |
| 🟢 Baixa | React Dashboard | Alto |
| 🟢 Baixa | WebSocket | Médio |

---

## Conclusão

O projeto tem uma base sólida mas precisa de várias correções para atender à especificação original. As prioridades são:

1. **API Trades** -Funcionalidade core faltando
2. **Risk por Bot** - Gestão de risco incompleta  
3. **Backtester** - Implementação atual é apenas simulação
4. **AI Orchestrator** - Arquitetura diferente da especificação

Recomendo começar pelas items de alta prioridade para ter uma plataforma funcional.
