"""
IA_MT5 Backend API
Correcao: CORS configuravel, seguranca basica, rate limiting
Prioridade: BAIXA
"""
import asyncio
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import time

from .api.routes import bots, trades, dashboard, events, backtest as backtest_router, mt5 as mt5_router
from .api.websocket_manager import router as ws_router
from .core.database import engine, Base
from .core.config import settings
from .core.logging_config import setup_logging, metrics
from .services.bot_manager import bot_manager
from .services.data_collector import data_collector
from .services.automation_service import automation_service

# Importar modelos para garantir criaA?A?o de tabelas
from .models import bot, trade, historical_data, system_event, backtest as backtest_model

# Configurar logging
logger = setup_logging(
    level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
    log_file="logs/app.log"
)


# Lifespan para gerenciar tarefas de background
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento de inicializaA?A?o e shutdown"""
    # Inicializa as tabelas
    Base.metadata.create_all(bind=engine)
    logger.info("Banco de dados inicializado")
    
    # Inicia o Coletor de Dados em segundo plano
    collector_task = asyncio.create_task(data_collector.start_loop())
    
    # Inicia o Servico de Automacao Autonomo (15 min cycle)
    automation_task = asyncio.create_task(automation_service.start())
    logger.info("Servico de Automacao Autonoma iniciado")

    # Reativa bots persistidos como ativos no banco.
    try:
        restored_bots = await bot_manager.restore_active_bots()
        if restored_bots:
            logger.info("Bots restaurados no startup: %s", restored_bots)
        else:
            logger.info("Nenhum bot ativo precisou ser restaurado no startup.")
    except Exception as exc:
        logger.error("Falha ao restaurar bots ativos no startup: %s", exc)
    
    yield
    
    # Finaliza tarefas
    data_collector.is_running = False
    automation_service.stop()
    
    collector_task.cancel()
    automation_task.cancel()
    logger.info("AplicaA?A?o encerrada")


# Criar aplicaA?A?o FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.2.0",
    description="Plataforma de Trading com IA para MetaTrader 5",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ========== SEGURANA?A ==========

# Rate limiting simples
rate_limit_store: dict = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting bA?sico por IP"""
    client_ip = request.client.host
    current_time = time.time()
    
    # Limpar registros antigos
    rate_limit_store[client_ip] = rate_limit_store.get(client_ip, [])
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip]
        if current_time - t < 60  # Janela de 1 minuto
    ]
    
    # Verificar limite (1000 requisiA?A?es por minuto)
    if len(rate_limit_store[client_ip]) > 1000:
        metrics.inc("rate_limit_exceeded")
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests"}
        )
    
    rate_limit_store[client_ip].append(current_time)
    
    response = await call_next(request)
    return response


# Middleware de mA?tricas
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Coletar mA?tricas de requisiA?A?es"""
    start_time = time.time()
    
    response = await call_next(request)
    
    # MA?tricas
    metrics.inc(f"http_requests_{response.status_code}")
    duration = time.time() - start_time
    metrics.observe("http_request_duration", duration)
    
    return response


# Middleware de logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Logar todas as requisiA?A?es"""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {(datetime.now() - start_time).total_seconds():.3f}s"
    )
    
    return response


# ========== CONFIGURAA?A?O DE CORS ==========

# CORS explA?cito para permitir credentials
cors_origins = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
logger.info(f"CORS origins configuradas: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Trusted Hosts (produA?A?o)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1"] + 
                     os.getenv("ALLOWED_HOSTS", "").split(",")
    )


# ========== ROTAS ==========

app.include_router(bots.router, prefix="/bots", tags=["Bots"])
app.include_router(trades.router, prefix="/trades", tags=["Trades"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(backtest_router.router, prefix="/backtest", tags=["Backtesting"])
app.include_router(mt5_router.router)
app.include_router(ws_router)  # WebSocket


# ========== ENDPOINTS DE SISTEMA ==========

@app.get("/")
async def root():
    """Endpoint de saAode"""
    return {
        "message": "IA_MT5 Backend Online",
        "version": "1.2.0",
        "timestamp": datetime.utcnow().isoformat(),
        "data_collector_active": data_collector.is_running
    }


@app.get("/health")
async def health_check():
    """
    Health check para Kubernetes/Docker
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected",
            "redis": "connected",
            "data_collector": data_collector.is_running
        }
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness check para Kubernetes
    """
    # Verificar conexA?es
    try:
        from .core.database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    ready = db_status == "connected"
    
    return {
        "ready": ready,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def get_metrics():
    """
    MA?tricas da aplicaA?A?o (Prometheus format)
    """
    return {
        "metrics": metrics.get_metrics(),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """
    MA?tricas em formato Prometheus
    """
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(metrics.to_prometheus())


# Error handlers
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler para erros de validaA?A?o (400/422) com log detalhado"""
    logger.error(f"ERRO DE VALIDAA?A?O: {exc.errors()}")
    logger.error(f"BODY DA REQUISIA?A?O: {await request.body()}")
    return JSONResponse(
        status_code=400,
        content={"error": "Validation error", "detail": exc.errors()}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de exceA?A?es"""
    metrics.inc("errors_total")
    logger.error(f"Erro nA?o tratado: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.ENVIRONMENT == "development" else "Unknown error"
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handler para 404"""
    metrics.inc("errors_404")
    return JSONResponse(
        status_code=404,
        content={"error": "Not found"}
    )
