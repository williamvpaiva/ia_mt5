import MetaTrader5 as mt5
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import uvicorn
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MT5Bridge")

app = FastAPI(title="MetaTrader 5 Bridge API", description="Ponte de comunicação entre Docker e MT5")

# Modelos de Dados
class OrderRequest(BaseModel):
    symbol: str
    action: str  # "buy" ou "sell"
    volume: float
    type: str = "market"  # market, limit
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    magic: int = 0
    comment: str = "IA_MT5_Order"

@app.on_event("startup")
def startup_event():
    # Caminhos comuns de instalação para facilitar
    common_paths = [
        "C:/Program Files/MetaTrader 5 Terminal/terminal64.exe",
        "C:/Program Files/MetaTrader 5/terminal64.exe"
    ]
    
    path = os.getenv("MT5_TERMINAL_PATH")
    
    success = False
    if path:
        if mt5.initialize(path=path):
            success = True
    else:
        # Tenta inicialização padrão (se já estiver aberto)
        if mt5.initialize():
            success = True
        else:
            # Tenta caminhos comuns
            for p in common_paths:
                if os.path.exists(p):
                    if mt5.initialize(path=p):
                        success = True
                        break

    if not success:
        logger.error(f"Falha ao inicializar MT5: {mt5.last_error()}")
        logger.info("Dica: Certifique-se de que o MT5 está aberto ou configure MT5_TERMINAL_PATH")
    else:
        logger.info("MetaTrader 5 inicializado com sucesso.")
        terminal_info = mt5.terminal_info()
        logger.info(f"Conectado ao terminal: {terminal_info.company} - {terminal_info.name}")

@app.on_event("shutdown")
def shutdown_event():
    mt5.shutdown()
    logger.info("Conexão com MT5 encerrada.")

@app.get("/health")
def health_check():
    connected = mt5.terminal_info().connected if mt5.initialize() else False
    return {"status": "ok", "mt5_connected": connected}

@app.get("/rates/{symbol}")
def get_rates(symbol: str, timeframe: str = "M5", count: int = 100):
    # Dicionário de Timeframes
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "D1": mt5.TIMEFRAME_D1
    }
    
    selected_tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_M5)
    
    rates = mt5.copy_rates_from_pos(symbol, selected_tf, 0, count)
    if rates is None:
        raise HTTPException(status_code=404, detail=f"Erro ao buscar rates para {symbol}: {mt5.last_error()}")
    
    # Converte record array para lista de dicts
    return [
        {
            "time": int(r['time']),
            "open": float(r['open']),
            "high": float(r['high']),
            "low": float(r['low']),
            "close": float(r['close']),
            "tick_volume": int(r['tick_volume'])
        } for r in rates
    ]

@app.get("/tick/{symbol}")
def get_tick(symbol: str):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Símbolo {symbol} não encontrado")
    return {
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last,
        "time": tick.time
    }

@app.post("/order")
def place_order(order: OrderRequest):
    symbol_info = mt5.symbol_info(order.symbol)
    if symbol_info is None:
        raise HTTPException(status_code=400, detail=f"Símbolo {order.symbol} não encontrado")
    
    if not symbol_info.visible:
        if not mt5.symbol_select(order.symbol, True):
            raise HTTPException(status_code=400, detail=f"Falha ao selecionar símbolo {order.symbol}")

    tick = mt5.symbol_info_tick(order.symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail="Não foi possível obter o tick atual")

    price = tick.ask if order.action.lower() == "buy" else tick.bid
    tick_size = symbol_info.trade_tick_size
    
    # Define o tipo de ordem
    type_dict = {
        "buy": mt5.ORDER_TYPE_BUY,
        "sell": mt5.ORDER_TYPE_SELL
    }

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": order.symbol,
        "volume": order.volume,
        "type": type_dict.get(order.action.lower()),
        "price": price,
        "magic": order.magic,
        "comment": order.comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Helper para normalizar preços ao tick_size
    def normalize_price(p):
        return round(p / tick_size) * tick_size

    # Se sl/tp vierem como pontos (ex: 100), converte para preço absoluto
    # Consideramos pontos se o valor for menor que 1/10 do preço atual (heurística segura para B3)
    if order.sl:
        if order.sl < (price / 10):
            # É pontos
            if order.action.lower() == "buy":
                request["sl"] = normalize_price(price - order.sl)
            else:
                request["sl"] = normalize_price(price + order.sl)
        else:
            # Já é preço absoluto
            request["sl"] = normalize_price(order.sl)

    if order.tp:
        if order.tp < (price / 10):
            # É pontos
            if order.action.lower() == "buy":
                request["tp"] = normalize_price(price + order.tp)
            else:
                request["tp"] = normalize_price(price - order.tp)
        else:
            # Já é preço absoluto
            request["tp"] = normalize_price(order.tp)

    logger.info(f"Enviando ordem {order.action} {order.volume} {order.symbol} @ {price} (SL: {request.get('sl')}, TP: {request.get('tp')})")

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Falha na ordem: {result.comment} (code: {result.retcode})")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar ordem: {result.comment} (code: {result.retcode})")

    return {
        "ticket": result.order,
        "retcode": result.retcode,
        "comment": result.comment,
        "price": result.price
    }

@app.get("/positions")
def get_positions():
    positions = mt5.positions_get()
    if positions is None:
        return []
    
    return [
        {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "buy" if p.type == 0 else "sell",
            "volume": p.volume,
            "price_open": p.price_open,
            "profit": p.profit,
            "magic": p.magic,
            "comment": p.comment
        } for p in positions
    ]

@app.delete("/position/{ticket}")
def close_position(ticket: int):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise HTTPException(status_code=404, detail="Posição não encontrada")
    
    pos = positions[0]
    symbol = pos.symbol
    type_close = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": pos.volume,
        "type": type_close,
        "position": ticket,
        "price": price,
        "magic": pos.magic,
        "comment": "IA_MT5_Close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(status_code=500, detail=f"Erro ao fechar posição: {result.comment}")

    return {"status": "closed", "ticket": ticket, "retcode": result.retcode}

if __name__ == "__main__":
    # Roda o bridge na porta 5000 acessível de fora (0.0.0.0)
    uvicorn.run(app, host="0.0.0.0", port=5000)
