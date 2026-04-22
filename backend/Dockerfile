# Stage 1: Build dependências
FROM python:3.12-slim AS builder

WORKDIR /app

# Instala ferramentas de build
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install pandas-ta
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Instala apenas dependências de runtime (libpq para postgres)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia wheels do estágio anterior
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*

# RUN useradd -m appuser && chown -R appuser:appuser /app
# USER appuser

# Copia o código da aplicação
COPY . .

# Limpeza de arquivos desnecessários no container
RUN find . -type d -name "__pycache__" -exec rm -rf {} + \
    && rm -rf logs/* data/*

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
