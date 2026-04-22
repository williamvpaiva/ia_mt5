"""
Configuracoes da Aplicacao
Correcao: Adicionadas configuracoes de modelos Ollama leves para producao
Prioridade: BAIXA

Modelos recomendados por ambiente:
- Producao (VPS modesta): llama3.2:1b (~1GB VRAM)
- Producao (balance): phi3:3.8b-mini (~2GB VRAM)
- Desenvolvimento: llama3.2:3b (~3GB VRAM)
- Alta qualidade: mistral:7b (~4GB VRAM)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


# Modelos Ollama prA?-configurados
OLLAMA_MODELS = {
    "light": "llama3.2:1b",        # 1B parA?metros, ~1GB VRAM
    "balanced": "phi3:3.8b-mini",  # 3.8B parA?metros, ~2GB VRAM
    "standard": "llama3.2:3b",     # 3B parA?metros, ~3GB VRAM
    "quality": "mistral:7b",       # 7B parA?metros, ~4GB VRAM
    "qwen": "qwen2.5:3b",          # 3B parA?metros, ~2GB VRAM
}


class Settings(BaseSettings):
    # ========== APP CONFIG ==========
    PROJECT_NAME: str = "IA_MT5_Platform"
    ENVIRONMENT: str = "development"  # development, production
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ia_mt5"
    
    # Se DATABASE_URL estiver no .env (como SQLite), pydantic settings pega automatico
    # mas se não, mantemos o default do postgres
    
    # ========== REDIS ==========
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    
    # ========== OLLAMA AI ==========
    # CorreA?A?o: Modelos configurA?veis por ambiente
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"  # Modelo leve para produA?A?o
    OLLAMA_MODEL_DEV: str = "llama3.2:3b"  # Modelo para desenvolvimento
    OLLAMA_TIMEOUT: int = 120  # segundos
    OLLAMA_MAX_TOKENS: int = 512
    
    # Modelo baseado no ambiente
    def get_model(self) -> str:
        """Obter modelo Ollama baseado no ambiente"""
        if self.ENVIRONMENT == "production":
            return self.OLLAMA_MODEL  # Modelo leve
        return self.OLLAMA_MODEL_DEV  # Modelo mais potente
    
    # ========== MT5 BRIDGE ==========
    MT5_BRIDGE_URL: str = "http://127.0.0.1:5001"
    MT5_BRIDGE_TIMEOUT: int = 30
    
    # ========== SECURITY ==========
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # ========== CORS ==========
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8501",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:5173",
    ]
    
    # ========== LOGGING ==========
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json ou text
    
    # ========== TRADING ==========
    DEFAULT_SYMBOL: str = "WINM26"
    DEFAULT_TIMEFRAME: str = "M5"
    MAX_POSITIONS_PER_BOT: int = 3
    MAX_DAILY_LOSS_PERCENT: float = 5.0
    
    # ========== CACHE ==========
    CACHE_TTL: int = 300  # segundos
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


# InstA?ncia global
settings = Settings()


def get_ollama_config() -> dict:
    """
    Obter configuracao Ollama otimizada
    Correcao: Retorna modelo adequado ao ambiente
    """
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        # ProduA?A?o: modelo leve
        model = os.getenv("OLLAMA_MODEL", OLLAMA_MODELS["light"])
    elif env == "development":
        # Desenvolvimento: modelo balanceado
        model = os.getenv("OLLAMA_MODEL", OLLAMA_MODELS["standard"])
    else:
        model = os.getenv("OLLAMA_MODEL", OLLAMA_MODELS["balanced"])
    
    return {
        "base_url": os.getenv("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL),
        "model": model,
        "timeout": int(os.getenv("OLLAMA_TIMEOUT", settings.OLLAMA_TIMEOUT)),
        "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", settings.OLLAMA_MAX_TOKENS)),
    }
