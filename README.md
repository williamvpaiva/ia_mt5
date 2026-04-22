# IA_MT5 - Plataforma de Trading Inteligente

Bem-vindo à sua plataforma de trading automatizado com integração de IA (Ollama) e MetaTrader 5.

## 🚀 Como Iniciar

Siga este passo a passo para colocar o sistema em funcionamento:

### 1. Pré-requisitos
*   **Docker Desktop** instalado (com backend WSL2).
*   **Python 3.11+** instalado no Windows.
*   **MetaTrader 5** instalado, logado na sua conta e com a opção "Permitir Trading Algorítmico" ativa.

### 2. Configurando o Windows (Host)
O MetaTrader 5 roda nativamente no Windows, por isso precisamos de uma "ponte" (bridge).
1.  Abra o terminal (PowerShell ou CMD) na pasta do projeto.
2.  Instale as dependências necessárias no seu Windows:
    ```bash
    pip install -r requirements_windows.txt
    ```
3.  Inicie a ponte:
    ```bash
    python scripts/mt5_bridge.py
    ```
    *Mantenha este terminal aberto.*

### 3. Iniciando a Infraestrutura (Docker)
Em outro terminal, na raiz do projeto, execute:
```bash
docker-compose up --build -d
```
Isso iniciará:
*   **PostgreSQL**: Onde seus robôs e trades são salvos.
*   **Redis**: Cache ultrarrápido para a IA.
*   **Ollama**: O servidor de IA local.
*   **Backend (FastAPI)**: O cérebro da operação (Docker Otimizado).
*   **Frontend (React)**: Interface moderna e rápida servida via Nginx (Docker Otimizado).

### 4. Acessando o Dashboard
Abra seu navegador e acesse:
👉 **[http://localhost:8501](http://localhost:8501)** (Agora com React 19 + Tailwind CSS)

---

## 🛠️ Componentes do Projeto

### IA Local (Ollama)
O sistema está configurado para usar o modelo `llama3.2:3b`. 
Na primeira vez que o container subir, você pode precisar baixar o modelo manualmente dentro do container:
```bash
docker exec -it ia_mt5_ollama ollama run llama3.2:3b
```

### Motores Bull/Bear
Localizados em `backend/app/services/trading_bot.py`. Você pode ajustar a lógica técnica (RSI, Médias Móveis) diretamente no código.

---

## ⚠️ Avisos de Segurança
*   Nunca compartilhe seu arquivo `.env` ou `SECRET_KEY`.
*   O Trading Automatizado envolve riscos. Teste sempre em conta **DEMO** antes de ir para conta Real.
*   Este projeto foi desenvolvido como uma estrutura base robusta, sinta-se à vontade para expandir as estratégias.

---
**Desenvolvido com IA_MT5 Framework.**
