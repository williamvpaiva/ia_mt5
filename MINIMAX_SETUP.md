# MiniMax AI - Guia de Configuração

## Visão Geral

O IA_MT5 agora suporta **MiniMax AI** como alternativa ao Ollama local. MiniMax é uma API comercial de alta performance (similar à OpenAI) que oferece:

- ✅ Modelos mais potentes (até 256K tokens de contexto)
- ✅ Sem necessidade de GPU local
- ✅ API OpenAI-compatible
- ✅ Custo por uso (pay-as-you-go)
- ✅ Latência menor que modelos locais

## Configuração Rápida

### 1. Obter API Key

1. Acesse: https://platform.minimaxi.com/
2. Crie sua conta
3. Gere uma API Key em **API Keys**
4. Copie a chave (ex: `0a1b2c3d4e5f...`)

### 2. Atualizar .env

Edite `D:\PROJETOS\IA_MT5\.env`:

```env
# Mudar provedor de ollama para minimax
LLM_PROVIDER=minimax

# Adicionar API Key
MINIMAX_API_KEY=0a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p

# Configurações opcionais
MINIMAX_MODEL=abab6.5s-chat
MINIMAX_TIMEOUT=60
MINIMAX_MAX_TOKENS=1024
```

### 3. Reiniciar Backend

```powershell
docker restart ia_mt5_backend
```

### 4. Testar

```bash
curl http://localhost:8000/ai/analyze
```

## Modelos Disponíveis

| Modelo | Descrição | Contexto | Custo |
|--------|-----------|----------|-------|
| `abab6.5s-chat` | Balanceado (recomendado) | 256K | ¥0.005/1K tokens |
| `abab6.5t-chat` | Rápido | 8K | ¥0.003/1K tokens |
| `abab6.5g-chat` | Alta qualidade | 256K | ¥0.01/1K tokens |

## Comparação: Ollama vs MiniMax

| Recurso | Ollama (Local) | MiniMax (API) |
|---------|----------------|---------------|
| **Custo** | Grátis (seu hardware) | Pay-per-use |
| **GPU** | Requerida | Não |
| **Latência** | Baixa (local) | Média (rede) |
| **Contexto** | 4K-8K tokens | 256K tokens |
| **Privacidade** | Total | Dados na nuvem |
| **Setup** | Complexo | Simples |

## Quando Usar

### Use Ollama se:
- ✅ Tem GPU local (4GB+ VRAM)
- ✅ Precisa de privacidade total
- ✅ Quer custo zero
- ✅ Aceita modelos menores

### Use MiniMax se:
- ✅ Sem GPU ou hardware limitado
- ✅ Precisa de contexto longo (>8K tokens)
- ✅ Quer modelo mais inteligente
- ✅ Aceita custo por uso

## Exemplo de Uso no Código

```python
# O backend já suporta ambos provedores
from app.services.ai_orchestrator import ai_orchestrator

# Análise de sentimento (automático baseado no LLM_PROVIDER)
result = await ai_orchestrator.analyze_sentiment(texto_noticia)

# Análise de tendência
trend = await ai_orchestrator.analyze_trend(dados_mercado)
```

## Troubleshooting

### Erro: "API key not provided"
- Verifique se `MINIMAX_API_KEY` está no `.env`
- Reinicie o backend após alterar .env

### Erro: "Invalid API key"
- Verifique se a chave está correta (sem espaços)
- Confirme se a plano tem créditos

### Erro: "Rate limit exceeded"
- MiniMax tem limite de requisições por segundo
- Aumente `MINIMAX_TIMEOUT` no `.env`

## Custos Estimados

Para trading diário com IA:

| Cenário | Tokens/dia | Custo/dia | Custo/mês |
|---------|------------|-----------|-----------|
| Leve (10 análises) | ~5K | ¥0.025 | ¥0.75 |
| Médio (100 análises) | ~50K | ¥0.25 | ¥7.50 |
| Pesado (1000 análises) | ~500K | ¥2.50 | ¥75.00 |

*Valores aproximados em Yuan chinês (¥)*

## Links Úteis

- [MiniMax Platform](https://platform.minimaxi.com/)
- [Documentação da API](https://platform.minimaxi.com/docs)
- [Preços](https://platform.minimaxi.com/pricing)
- [Exemplos de código](https://platform.minimaxi.com/examples)

## Voltar para Ollama

Para voltar ao Ollama:

```env
LLM_PROVIDER=ollama
```

Reinicie o backend:
```bash
docker restart ia_mt5_backend
```
