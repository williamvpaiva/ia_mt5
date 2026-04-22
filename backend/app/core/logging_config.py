"""
Logging Estruturado e MA?tricas
CorreA?A?o: ImplementaA?A?o de logging JSON e mA?tricas Prometheus
Prioridade: BAIXA
"""
import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Formatador de logs em JSON"""
    
    def __init__(self, service_name: str = "ia_mt5"):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "file": f"{record.filename}:{record.lineno}",
        }
        
        # Adicionar contexto extra se existir
        if hasattr(record, 'context'):
            log_data["context"] = record.context
        
        # Adicionar exceA?A?o se existir
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class StructuredLogger:
    """Logger estruturado com mA?tricas"""
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_format: str = "json",
        log_file: str = "logs/app.log"
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Limpar handlers existentes
        self.logger.handlers.clear()
        
        # Handler de console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if log_format == "json":
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        
        self.logger.addHandler(console_handler)
        
        # Handler de arquivo (opcional)
        if log_file:
            Path(log_file).parent.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)
    
    def get_logger(self) -> logging.Logger:
        return self.logger
    
    def log_with_context(self, level: str, message: str, context: Dict[str, Any] = None):
        """Log com contexto adicional"""
        extra = {'context': context} if context else {}
        self.logger.log(getattr(logging, level.upper()), message, extra=extra)


# MA?tricas simples (Prometheus-style)
class MetricsCollector:
    """Coletor de mA?tricas simples"""
    
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = {}
    
    def inc(self, name: str, value: int = 1):
        """Incrementar contador"""
        self.counters[name] = self.counters.get(name, 0) + value
    
    def set_gauge(self, name: str, value: float):
        """Setar gauge"""
        self.gauges[name] = value
    
    def observe(self, name: str, value: float):
        """Observar valor para histograma"""
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obter todas as mA?tricas"""
        return {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "histograms": {
                name: {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                }
                for name, values in self.histograms.items()
            }
        }
    
    def to_prometheus(self) -> str:
        """Exportar em formato Prometheus"""
        lines = []
        
        for name, value in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        for name, value in self.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        return "\n".join(lines)


# InstA?ncia global
metrics = MetricsCollector()


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: str = "logs/app.log"
):
    """Configurar logging para toda a aplicaA?A?o"""
    logging_level = getattr(logging, level.upper(), logging.INFO)
    
    root_logger = StructuredLogger(
        name="ia_mt5",
        level=logging_level,
        log_format=log_format,
        log_file=log_file
    )
    
    # Configurar loggers especA?ficos
    loggers = {
        "uvicorn": logging.getLogger("uvicorn"),
        "sqlalchemy": logging.getLogger("sqlalchemy"),
        "bot_manager": logging.getLogger("BotManager"),
        "risk": logging.getLogger("RiskGlobal"),
        "backtest": logging.getLogger("Backtester"),
    }
    
    for logger_name, logger in loggers.items():
        logger.setLevel(logging_level)
        if log_format == "json":
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JSONFormatter())
            logger.handlers = [handler]
    
    return root_logger.get_logger()
