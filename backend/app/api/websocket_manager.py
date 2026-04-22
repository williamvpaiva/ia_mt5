"""
WebSocket Manager para Alertas em Tempo Real
CorreA?A?o: ImplementaA?A?o de WebSocket para alertas
Prioridade: BAIXA
"""
import logging
import json
from typing import Dict, List, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

logger = logging.getLogger("WebSocketManager")


class ConnectionManager:
    """Gerenciador de conexA?es WebSocket"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}  # connection -> channels
    
    async def connect(self, websocket: WebSocket):
        """Aceitar nova conexA?o"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = {"*"}  # Subscribe to all by default
        logger.info(f"Nova conexA?o WebSocket aceita. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remover conexA?o"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"ConexA?o WebSocket removida. Total: {len(self.active_connections)}")
    
    def subscribe(self, websocket: WebSocket, channels: List[str]):
        """Inscrever em canais especA?ficos"""
        self.subscriptions[websocket] = set(channels)
        logger.info(f"WebSocket assinou canais: {channels}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Enviar mensagem para conexA?o especA?fica"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem WebSocket: {e}")
    
    async def broadcast(self, message: dict, channel: str = "*"):
        """
        Transmitir mensagem para assinantes do canal
        channel: "*" para todos, ou nome especA?fico
        """
        message["timestamp"] = datetime.utcnow().isoformat()
        
        disconnected = []
        
        for connection in self.active_connections:
            # Verificar assinatura
            user_channels = self.subscriptions.get(connection, {"*"})
            if channel != "*" and channel not in user_channels and "*" not in user_channels:
                continue
            
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Erro ao transmitir para WebSocket: {e}")
                disconnected.append(connection)
        
        # Limpar conexA?es desconectadas
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_alert(self, alert_type: str, data: dict, channel: str = "alerts"):
        """Enviar alerta formatado"""
        message = {
            "type": "alert",
            "alert_type": alert_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message, channel)
    
    # ========== ALERTAS ESPECA?FICOS ==========
    
    async def trade_opened(self, trade_data: dict):
        """Alerta: Trade aberto"""
        await self.send_alert("trade_opened", trade_data, "trades")
    
    async def trade_closed(self, trade_data: dict):
        """Alerta: Trade fechado"""
        await self.send_alert("trade_closed", trade_data, "trades")
    
    async def trade_updated(self, trade_data: dict):
        """Alerta: Trade atualizado"""
        await self.send_alert("trade_updated", trade_data, "trades")
    
    async def risk_warning(self, bot_id: int, message: str, level: str = "warning"):
        """Alerta: Aviso de risco"""
        await self.send_alert("risk_warning", {
            "bot_id": bot_id,
            "message": message,
            "level": level
        }, "risk")
    
    async def bot_error(self, bot_id: int, error: str):
        """Alerta: Erro no bot"""
        await self.send_alert("bot_error", {
            "bot_id": bot_id,
            "error": error
        }, "errors")
    
    async def bot_started(self, bot_id: int):
        """Alerta: Bot iniciado"""
        await self.send_alert("bot_started", {"bot_id": bot_id}, "bots")
    
    async def bot_stopped(self, bot_id: int):
        """Alerta: Bot parado"""
        await self.send_alert("bot_stopped", {"bot_id": bot_id}, "bots")
    
    async def price_alert(self, symbol: str, price: float, threshold: float):
        """Alerta: PreA?o atingiu threshold"""
        await self.send_alert("price_alert", {
            "symbol": symbol,
            "price": price,
            "threshold": threshold
        }, "prices")
    
    async def system_status(self, status: str, details: dict = None):
        """Alerta: Status do sistema"""
        await self.send_alert("system_status", {
            "status": status,
            "details": details or {}
        }, "system")


# InstA?ncia global
ws_manager = ConnectionManager()


# ========== WEBSOCKET ENDPOINT ==========

from fastapi import APIRouter, Query

router = APIRouter()


@router.websocket("/ws/alerts")
async def websocket_endpoint(
    websocket: WebSocket,
    channels: str = Query(default="*")  # ex: "trades,risk,bots"
):
    """
    Endpoint WebSocket para alertas em tempo real
    CorreA?A?o: ImplementaA?A?o de WebSocket conforme especificaA?A?o
    """
    channel_list = channels.split(",") if channels else ["*"]
    
    await ws_manager.connect(websocket)
    ws_manager.subscribe(websocket, channel_list)
    
    try:
        while True:
            # Manter conexA?o viva
            data = await websocket.receive_text()
            
            # Processar mensagem do cliente (se necessA?rio)
            try:
                message = json.loads(data)
                logger.debug(f"Mensagem recebida: {message}")
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("Cliente WebSocket desconectado")
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        ws_manager.disconnect(websocket)
