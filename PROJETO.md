Instruções ao Assistente de IA
Você deve gerar o código-fonte completo, organizado em pastas, de uma plataforma de trading automatizado conforme as especificações abaixo. O projeto deve ser funcional, robusto e pronto para implantação. Siga rigorosamente os requisitos.

1. Visão Geral do Sistema
Objetivo: Permitir que um usuário crie, configure, execute e monitore múltiplos bots de trading para o ativo WIN (Mini Índice B3) no MetaTrader 5.

Cada bot é uma instância independente com:

Timeframe próprio (M1, M5, M15, H1, etc.)

Pontos de entrada/saída baseados em dois motores: Analista Comprado (Bull) e Analista Vendido (Bear)

Orquestrador que decide compra/venda/neutro com base nos scores dos analistas

Gerenciamento de risco individual (stop loss, take profit, volume máximo, perda diária)

Opção de ativar IA local (via Ollama) para análise de sentimento de notícias e reforço das decisões

Horários ativos configuráveis

Dashboard web para:

Criar/editar/duplicar/excluir bots (parâmetros, pesos dos analistas, ativação de IA, stops, timeframes)

Visualizar performance em tempo real (PnL, drawdown, win rate, equity curve)

Ver lista de trades abertos e fechados, com filtros

Receber alertas (via WebSocket) sobre novos trades, alterações de equity, paradas de emergência

Backtesting integrado para simular uma configuração de bot sobre dados históricos.

Tudo containerizado com Docker (backend, frontend, banco de dados PostgreSQL, Redis, Ollama) – exceto o MetaTrader 5, que roda no Windows host e se comunica via HTTP/WebSocket.

2. Arquitetura Técnica
2.1. Componentes e Tecnologias
Backend: FastAPI (Python 3.11), SQLAlchemy, Alembic, Pydantic.

Banco de dados: PostgreSQL (container), com tabelas: bots, trades, performance_snapshots, ia_models (opcional).

Cache e filas: Redis (container), usado para pub/sub de eventos e cache de análises da IA.

Frontend: Streamlit (container) – dashboard interativo com gráficos (Plotly) e formulários.

IA local: Ollama (container oficial) rodando modelos como llama3.2:3b ou phi3:mini. O backend se comunica via HTTP.

Proxy reverso (opcional): Nginx (container) para servir frontend e backend na porta 80.

Comunicação com MT5: Um serviço bridge em Python executado fora do Docker (no Windows host) que expõe uma API REST para:

Enviar ordens (/order)

Buscar dados de mercado (/rates, /tick)

Obter posições e histórico (/positions, /history)

Este bridge se conecta ao MT5 via MetaTrader5 package.

2.2. Estrutura de Pastas do Projeto
text
bot_platform/
├── docker-compose.yml
├── .env
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── scripts/
│   │   └── entrypoint_backend.sh
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── bots.py
│   │   │   │   ├── trades.py
│   │   │   │   ├── dashboard.py
│   │   │   │   └── websocket.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py (opcional)
│   │   ├── models/
│   │   │   ├── bot.py
│   │   │   ├── trade.py
│   │   │   └── performance.py
│   │   ├── schemas/
│   │   │   ├── bot.py
│   │   │   └── trade.py
│   │   ├── services/
│   │   │   ├── bot_manager.py      # supervisor de threads dos bots
│   │   │   ├── mt5_client.py       # cliente HTTP para o bridge MT5
│   │   │   ├── ia_service.py       # chamadas ao Ollama com cache
│   │   │   ├── risk_global.py      # limites de exposição geral
│   │   │   └── trading_bot.py      # lógica do bot (bull, bear, orquestrador)
│   │   └── utils/
│   │       └── logging_config.py
│   └── alembic/ (migrations)
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── streamlit_app.py
│   └── pages/ (opcional)
├── nginx/
│   └── nginx.conf
├── scripts/
│   └── mt5_bridge.py   (código a ser executado no Windows host)
└── data/
    ├── postgres/   (volume)
    ├── redis/      (volume)
    └── ollama/     (volume)
3. Requisitos Detalhados por Módulo
3.1. Backend – FastAPI
3.1.1. Modelos de Dados (SQLAlchemy)

Bot: id, name, symbol="WIN", timeframe, active (bool), magic_number, config (JSON), created_at, updated_at.

Trade: id, bot_id, ticket, direction, volume, open_price, open_time, close_price, close_time, pnl, stop_loss, take_profit.

PerformanceSnapshot: id, bot_id, timestamp, equity, daily_pnl, drawdown, win_rate_24h.

3.1.2. Endpoints API (REST)

GET /bots – lista todos os bots

POST /bots – cria um novo bot (recebe config JSON)

GET /bots/{id} – detalhes

PUT /bots/{id} – atualiza configuração

DELETE /bots/{id} – remove bot (e para sua thread)

POST /bots/{id}/start – ativa o bot

POST /bots/{id}/stop – desativa o bot

GET /trades – histórico de trades (filtros: bot_id, data_inicio, data_fim)

GET /dashboard/metrics – métricas agregadas (PnL total, win rate geral, drawdown máximo)

GET /backtest – executa backtest (recebe configuração de bot + período) e retorna equity curve e trades simulados

GET /ia/models – lista modelos disponíveis no Ollama

3.1.3. WebSocket

Endpoint /ws/dashboard – transmite em tempo real: novos trades, atualizações de equity por bot, alertas de risco.

3.1.4. Serviço de Gerenciamento de Bots (bot_manager.py)

Mantém um dicionário bot_id -> thread (ou asyncio.Task).

Ao iniciar um bot, carrega sua configuração do banco, instancia a classe TradingBot e inicia sua thread.

A thread executa um loop: a cada sleep(intervalo_do_timeframe) coleta dados do MT5 via bridge, executa os analistas e o orquestrador, envia ordens se necessário.

Garante que dois bots com o mesmo magic_number não sejam iniciados.

Implementa sinal de parada (threading.Event) para desligar bots.

3.1.5. Cliente MT5 Bridge (mt5_client.py)

Classe MT5BridgeClient com métodos assíncronos (httpx) para:

get_rates(symbol, timeframe, count)

get_tick(symbol)

place_order(symbol, action, volume, sl, tp, magic, comment)

get_positions()

close_position(ticket)

Configuração via variável de ambiente MT5_BRIDGE_URL (ex: http://host.docker.internal:5000).

3.1.6. Serviço de IA (ia_service.py)

Classe IAService com cache Redis (TTL configurável).

Método analyze_news(headlines: str) -> dict contendo sentiment (bullish/bearish/neutral) e score (0-100).

Usa Ollama API: POST /api/generate com prompt estruturado para retornar JSON.

Se o Ollama estiver indisponível, retorna score neutro (50) e log de erro.

3.1.7. Lógica do TradingBot (trading_bot.py)

Implementa os 3 motores:

BullEngine: calcula score com base em indicadores técnicos (RSI, MACD, preço vs média) e IA (se ativada).

BearEngine: análogo para detecção de força vendedora.

Orchestrator: recebe os dois scores, aplica limites (ex: bull > 70 e bear < 30 → compra; bear > 70 e bull < 30 → venda; caso contrário neutro). Gerencia tamanho da posição baseado no net score e risco.

O bot deve registrar cada decisão em log e, se gerar ordem, enviar via MT5BridgeClient e salvar o trade no banco (com bot_id).

O loop do bot também atualiza a performance (equity, PnL do dia) periodicamente e armazena snapshots.

3.2. Frontend – Streamlit Dashboard
Página inicial (Dashboard):

Cards com PnL total (R$), win rate (%), drawdown máximo (%), número de bots ativos.

Gráfico de equity curve (últimas 24h) com selector de bot.

Tabela de trades recentes (últimos 20).

WebSocket para atualização automática.

Página "Meus Bots":

Lista de bots com status (ativo/inativo), botões Start/Stop, editar, deletar.

Botão "Novo Bot" que abre um formulário com:

Nome, timeframe (dropdown)

Seção de pesos dos analistas (sliders para cada indicador)

Ativação de IA (checkbox) e seleção de modelo Ollama

Stop loss (pontos), take profit (pontos), volume máximo (lotes)

Horário de início e fim (time picker)

Ao salvar, chama POST /bots e depois POST /bots/{id}/start.

Página "Resultados":

Tabela completa de trades, com filtros (bot, data, direção).

Botão para exportar CSV.

Página "Backtest":

Seleciona um bot existente ou cria uma configuração temporária.

Define período (data início/fim).

Executa e exibe equity curve, trades simulados, métricas (Sharpe, máximo drawdown).

3.3. Integração com MetaTrader 5 (Bridge no Windows)
mt5_bridge.py (fornecido como script separado):

Usa FastAPI e uvicorn.

Inicializa o MT5 no início (mt5.initialize()).

Expõe endpoints:

POST /order (recebe JSON: symbol, action, volume, sl, tp, magic, comment)

GET /rates/{symbol}?timeframe=M5&count=100

GET /positions

DELETE /position/{ticket}

Deve ser executado manualmente no Windows (ou como serviço do Windows).

Endereço padrão: http://0.0.0.0:5000.

3.4. Docker e Containerização
docker-compose.yml (conforme fornecido no início da resposta) com serviços: postgres, redis, ollama, backend, frontend, nginx (opcional).

Os containers devem se comunicar em uma rede interna (bot_network).

O backend deve usar host.docker.internal para alcançar o bridge MT5 rodando no Windows host (funciona no Docker Desktop com WSL2).

Variáveis de ambiente gerenciadas via .env.

Volumes para persistência: ./data/postgres, ./data/redis, ./data/ollama, ./logs.

3.5. Funcionalidades Adicionais
Backtesting: O backend deve implementar uma rota /backtest que, dada uma configuração de bot, baixa dados históricos do MT5 bridge (ou de um arquivo CSV) e simula as decisões sem enviar ordens reais. Retorna a lista de trades simulados e a curva de equity.

Otimização de parâmetros (bônus): Uma rota /optimize que executa grid search sobre os pesos dos analistas e stops, retornando a combinação com melhor Sharpe.

Alertas por Telegram: Opção no dashboard de enviar notificações para um chat do Telegram quando um bot opera, quando atinge perda diária, etc. (Implementar com python-telegram-bot).

4. Instruções de Implementação (Passo a Passo)
Siga a ordem abaixo para construir o sistema. Para cada etapa, gere o código completo e as instruções de uso.

Crie a estrutura de pastas conforme a seção 2.2.

Configure o ambiente Docker:

Escreva o docker-compose.yml completo.

Escreva os Dockerfile para backend e frontend.

Escreva o .env com valores padrão.

Desenvolva o backend:

Implemente os modelos SQLAlchemy e as migrações Alembic.

Implemente as rotas API (CRUD de bots, trades, dashboard).

Implemente o WebSocket.

Implemente o MT5BridgeClient.

Implemente o IAService com cache Redis.

Implemente a lógica do TradingBot (BullEngine, BearEngine, Orchestrator).

Implemente o BotSupervisor.

Implemente o backtesting.

Desenvolva o frontend com Streamlit (todas as páginas mencionadas).

Escreva o script mt5_bridge.py para Windows.

Forneça um README.md detalhado com:

Pré‑requisitos (Docker Desktop, Python 3.11 no Windows, MT5 instalado e logado).

Passos para subir os containers (docker-compose up --build).

Como executar o bridge MT5 no Windows (python mt5_bridge.py).

Como acessar o dashboard (http://localhost:8501 ou http://localhost).

Exemplo de criação de um bot simples.

Forneça um script de inicialização para o Windows que inicie o bridge MT5 automaticamente (opcional, mas recomendado).

5. Exemplos de Código Obrigatórios
O assistente deve gerar, no mínimo, os seguintes trechos completos:

docker-compose.yml (com todos os serviços)

backend/Dockerfile e frontend/Dockerfile

backend/app/main.py (setup do FastAPI, inclusão de rotas, WebSocket)

backend/app/services/trading_bot.py (classe TradingBot com os 3 motores)

backend/app/services/bot_manager.py (supervisor de threads)

backend/app/services/ia_service.py (integração com Ollama)

frontend/streamlit_app.py (dashboard completo)

mt5_bridge.py (script para Windows)

6. Critérios de Aceitação
O sistema deve ser capaz de rodar em um ambiente Windows 10/11 com Docker Desktop (WSL2).

Deve ser possível criar um bot via dashboard, ativá-lo, e ver ele tomar decisões baseadas em dados reais do MT5 (usando o bridge).

O bot deve registrar trades no banco e o dashboard deve mostrar a performance.

A IA local (Ollama) deve ser opcional e, quando ativada, influenciar os scores (via análise de notícias fictícias ou reais – o usuário poderá fornecer notícias manualmente no dashboard para teste).

O backtest deve rodar e exibir resultados consistentes.

Todos os containers devem subir sem erros e se comunicar.

7. Observações Finais
O código gerado deve ser pronto para copiar e colar, organizado em arquivos conforme a estrutura.

Use type hints e docstrings em todo o código.

Inclua tratamento de erros (ex: falha de conexão com MT5, timeout do Ollama).

Para simplificação, o bridge MT5 pode inicialmente simular ordens (paper trading) se o MT5 não estiver disponível, mas deve ser fácil trocar para o modo real.

O projeto deve ser auto‑contido – o usuário não precisará escrever nenhum código adicional além de seguir o README. METATRADER ESTA NA PASTA - C:\Program Files\MetaTrader 5 Terminal