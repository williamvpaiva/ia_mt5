import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from ..core.config import settings
from ..core.database import SessionLocal
from ..models.bot import Bot
from ..models.trade import Trade
from .bot_log_service import write_bot_log
from .mt5_client import mt5_client

logger = logging.getLogger("TradingBot")


class TradingBotInstance:
    def __init__(self, bot_id: int):
        self.bot_id = bot_id
        self.is_running = False
        self.config: Dict[str, Any] = {}
        self.magic_number = 0
        self.bot_name = f"Bot {bot_id}"
        self.symbol = settings.DEFAULT_SYMBOL
        self.timeframe = settings.DEFAULT_TIMEFRAME
        self.allowed_symbols: list[str] = []
        self.max_spread = 0.0
        self.max_slippage = 0.0
        self.signals_config: Dict[str, Any] = {}
        self.risk_config: Dict[str, Any] = {}
        self.ai_config: Dict[str, Any] = {}
        self.excluded_days: list[int] = []
        self.start_time = "09:00"
        self.end_time = "17:50"
        self._last_market_log_signature: Optional[str] = None

    async def load_config(self):
        db = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == self.bot_id).first()
            if not bot:
                return

            allowed_raw = bot.allowed_symbols or [self.symbol]
            if isinstance(allowed_raw, str):
                allowed_raw = [allowed_raw]

            self.config = bot.config or {}
            self.magic_number = bot.magic_number
            self.bot_name = bot.name or self.bot_name
            self.symbol = bot.symbol or settings.DEFAULT_SYMBOL
            self.timeframe = bot.timeframe or settings.DEFAULT_TIMEFRAME
            self.allowed_symbols = [str(s).upper() for s in allowed_raw if s]
            self.max_spread = float(bot.max_spread or 0)
            self.max_slippage = float(bot.max_slippage or 0)
            self.signals_config = bot.signals_config or {}
            self.risk_config = bot.risk_config or {}
            self.ai_config = bot.ai_config or {}
            self.excluded_days = list(getattr(bot, "excluded_days", []) or [])
            self.start_time = getattr(bot, "start_time", "09:00")
            self.end_time = getattr(bot, "end_time", "17:50")
        finally:
            db.close()

    async def _get_account_balance(self) -> float:
        account = await mt5_client.get_account()
        if not account:
            return 0.0

        for key in ("equity", "balance", "free_margin"):
            value = account.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue

        return 0.0

    async def _build_risk_snapshot(self, trade_symbol: str, positions: list[Dict[str, Any]]) -> Dict[str, Any]:
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        deals = await mt5_client.get_history_deals(
            start_of_day,
            now,
            magic=self.magic_number,
        )

        open_positions = [
            pos for pos in positions
            if pos.get("magic") == self.magic_number
        ]
        opened_today = [deal for deal in deals if deal.get("entry") == "in" and deal.get("type") in {"buy", "sell"}]
        closed_today = [deal for deal in deals if deal.get("entry") in {"out", "out_by", "inout"}]

        def _safe_float(value: Any) -> float:
            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0

        realized_pnl = sum(
            _safe_float(deal.get("profit"))
            + _safe_float(deal.get("commission"))
            + _safe_float(deal.get("swap"))
            for deal in closed_today
        )
        unrealized_pnl = sum(_safe_float(pos.get("profit")) for pos in open_positions)

        return {
            "open_positions_count": len(open_positions),
            "daily_trades": len(opened_today),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "daily_pnl": round(realized_pnl + unrealized_pnl, 2),
            "account_balance": round(await self._get_account_balance(), 2),
            "max_positions": int(self.risk_config.get("max_positions", settings.MAX_POSITIONS_PER_BOT) or 0),
            "max_daily_trades": int(self.risk_config.get("max_daily_trades", 10) or 0),
            "daily_profit_limit": float(self.risk_config.get("daily_profit_limit", 1000.0) or 0),
            "daily_loss_limit": float(self.risk_config.get("daily_loss_limit", 500.0) or 0),
            "max_risk_per_trade": float(self.risk_config.get("max_risk_per_trade", 0.02) or 0),
        }

    def _risk_allows_entry(self, snapshot: Dict[str, Any], lot: float, stop_loss: Any) -> tuple[bool, str]:
        max_positions = int(snapshot.get("max_positions") or 0)
        open_positions = int(snapshot.get("open_positions_count") or 0)
        if max_positions > 0 and open_positions >= max_positions:
            return False, f"máximo de posições atingido ({open_positions}/{max_positions})"

        max_daily_trades = int(snapshot.get("max_daily_trades") or 0)
        daily_trades = int(snapshot.get("daily_trades") or 0)
        if max_daily_trades > 0 and daily_trades >= max_daily_trades:
            return False, f"máximo de trades diários atingido ({daily_trades}/{max_daily_trades})"

        daily_profit_limit = float(snapshot.get("daily_profit_limit") or 0)
        daily_pnl = float(snapshot.get("daily_pnl") or 0)
        if daily_profit_limit > 0 and daily_pnl >= daily_profit_limit:
            return False, f"meta diária atingida ({daily_pnl:.2f} >= {daily_profit_limit:.2f})"

        daily_loss_limit = float(snapshot.get("daily_loss_limit") or 0)
        if daily_loss_limit > 0 and daily_pnl <= -abs(daily_loss_limit):
            return False, f"stop diário atingido ({daily_pnl:.2f} <= -{abs(daily_loss_limit):.2f})"

        max_risk_per_trade = float(snapshot.get("max_risk_per_trade") or 0)
        account_balance = float(snapshot.get("account_balance") or 0)
        if max_risk_per_trade > 0 and account_balance > 0:
            try:
                stop_loss_points = abs(float(stop_loss or 0))
                estimated_risk = stop_loss_points * max(float(lot), 0.0)
                allowed_risk = account_balance * max_risk_per_trade
                if stop_loss_points > 0 and estimated_risk > allowed_risk:
                    return False, (
                        f"risco estimado {estimated_risk:.2f} acima do limite "
                        f"{allowed_risk:.2f}"
                    )
            except (TypeError, ValueError):
                logger.warning("Não foi possível validar max_risk_per_trade para o bot %s", self.bot_id)

        return True, ""

    def is_trading_allowed(self) -> bool:
        now = datetime.now()

        current_day_js = (now.weekday() + 1) % 7
        if current_day_js in self.excluded_days:
            return False

        try:
            current_time = now.time()
            start = datetime.strptime(self.start_time, "%H:%M").time()
            end = datetime.strptime(self.end_time, "%H:%M").time()
            if not (start <= current_time <= end):
                return False
        except Exception:
            return True

        return True

    async def _resolve_trade_symbol(self) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        resolved = await mt5_client.resolve_symbol(self.symbol)
        if not resolved:
            return None, None

        trade_symbol = (resolved.get("resolved") or self.symbol or "").upper()
        symbol_info = resolved.get("symbol") or {}

        allowed = {s.upper() for s in self.allowed_symbols if s}
        if allowed and trade_symbol not in allowed and (self.symbol or "").upper() not in allowed:
            logger.info(
                "Bot %s bloqueado: símbolo %s não está em allowed_symbols=%s",
                self.bot_id,
                trade_symbol,
                sorted(allowed),
            )
            return None, None

        spread = symbol_info.get("spread")
        if self.max_spread and spread is not None:
            try:
                if float(spread) > self.max_spread:
                    logger.info(
                        "Bot %s bloqueado: spread %s acima do máximo %s em %s",
                        self.bot_id,
                        spread,
                        self.max_spread,
                        trade_symbol,
                    )
                    return None, None
            except (TypeError, ValueError):
                logger.warning("Não foi possível validar spread para %s", trade_symbol)

        return trade_symbol, symbol_info

    async def get_data(self, symbol: Optional[str] = None):
        rates = await mt5_client.get_rates(symbol or self.symbol, self.timeframe, count=200)
        if not rates:
            return None

        df = pd.DataFrame(rates)
        import pandas_ta as ta

        df["EMA_9"] = ta.ema(df["close"], length=9)
        df["EMA_21"] = ta.ema(df["close"], length=21)
        df["RSI"] = ta.rsi(df["close"], length=14)
        df["ATR"] = ta.atr(df.high, df.low, df.close, length=14)
        df.fillna(0, inplace=True)
        return df

    async def _apply_trailing_stop(self, trade_symbol: str, symbol_info: Dict[str, Any], positions: list[Dict[str, Any]]):
        trailing = self.risk_config.get("trailing_stop") or {}
        if not trailing.get("active"):
            return

        distance = float(trailing.get("distance", 0) or 0)
        step = float(trailing.get("step", 0) or 0)
        if distance <= 0:
            return

        tick = await mt5_client.get_tick(trade_symbol)
        if not tick:
            return

        point = float(symbol_info.get("point") or 1.0)
        current_bid = float(tick.get("bid") or tick.get("last") or 0)
        current_ask = float(tick.get("ask") or tick.get("last") or 0)
        if current_bid <= 0 or current_ask <= 0:
            return

        for pos in positions:
            if pos.get("magic") != self.magic_number:
                continue

            entry = float(pos.get("price_open") or 0)
            ticket = pos.get("ticket")
            if not ticket or entry <= 0:
                continue

            pos_type = pos.get("type")
            current_price = current_bid if pos_type == "buy" else current_ask
            current_sl = pos.get("sl")
            current_tp = pos.get("tp")

            if pos_type == "buy":
                profit_points = (current_price - entry) / point
                if profit_points >= distance:
                    new_sl = current_price - (distance * point)
                    if current_sl is None or new_sl > float(current_sl) + (step * point):
                        await mt5_client.modify_position(ticket, sl=round(new_sl, 2), tp=current_tp)
            else:
                profit_points = (entry - current_price) / point
                if profit_points >= distance:
                    new_sl = current_price + (distance * point)
                    if current_sl is None or new_sl < float(current_sl) - (step * point):
                        await mt5_client.modify_position(ticket, sl=round(new_sl, 2), tp=current_tp)

    @staticmethod
    def _signal_label(value: int) -> str:
        if value > 0:
            return "buy"
        if value < 0:
            return "sell"
        return "neutral"

    @staticmethod
    def _market_bias(vote: int, active_votes: int) -> str:
        if active_votes <= 0:
            return "idle"
        if vote > 0:
            return "bullish"
        if vote < 0:
            return "bearish"
        return "neutral"

    def _should_log_market_state(self, signature: str, force: bool = False) -> bool:
        if force:
            self._last_market_log_signature = signature
            return True
        if signature == self._last_market_log_signature:
            return False
        self._last_market_log_signature = signature
        return True

    async def run_cycle(self):
        """Executa um ciclo único de decisão e trading."""
        await self.load_config()

        if not self.is_trading_allowed():
            return

        trade_symbol, symbol_info = await self._resolve_trade_symbol()
        if not trade_symbol or symbol_info is None:
            return

        positions = await mt5_client.get_positions(magic=self.magic_number)
        await self._apply_trailing_stop(trade_symbol, symbol_info, positions)

        lot = float(self.risk_config.get("lot_size", 1.0))
        sl = self.risk_config.get("stop_loss", 200)
        tp = self.risk_config.get("take_profit", 400)
        risk_snapshot = await self._build_risk_snapshot(trade_symbol, positions)
        entry_allowed, entry_block_reason = self._risk_allows_entry(risk_snapshot, lot=lot, stop_loss=sl)

        df = await self.get_data(trade_symbol)
        if df is None:
            return

        from stable_baselines3 import PPO
        import os

        model = None
        model_path = f"models/bot_{self.bot_id}_ppo"
        if os.path.exists(model_path + ".zip"):
            model = PPO.load(model_path)

        spy_status = None
        db = SessionLocal()
        try:
            bot = db.query(Bot).filter(Bot.id == self.bot_id).first()
            if not bot:
                return

            if bot.spy_config.get("active") and bot.spy_config.get("target_magic"):
                import redis
                import json

                r_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
                target_data = r_client.get(f"spy:{bot.spy_config['target_magic']}")
                if target_data:
                    spy_status = json.loads(target_data)

            from ..engine.decisor import HybridDecisor

            decisor = HybridDecisor(bot, df)
            tech_signals = decisor.calculate_signals()
            ai_signal = decisor.get_ai_prediction(model)
            spy_signal = decisor.get_spy_signal(spy_status)

            final_vote = 0
            active_votes = 0
            for value in tech_signals.values():
                if value != 0:
                    final_vote += value
                    active_votes += 1

            if bot.spy_config.get("active") and spy_signal != 0:
                final_vote += spy_signal
                active_votes += 1

            if self.ai_config.get("rl_active") and ai_signal != 0:
                final_vote += ai_signal
                active_votes += 1

            if self.ai_config.get("rl_active") and self.ai_config.get("mode") == "pure_ia":
                decision = ai_signal
            elif self.ai_config.get("rl_active") and self.ai_config.get("mode") == "pure_signals":
                decision = 1 if final_vote > 0 else -1 if final_vote < 0 else 0
            elif active_votes == 0:
                decision = 0
            elif final_vote > 0:
                decision = 1
            elif final_vote < 0:
                decision = -1
            else:
                decision = 0

            my_positions = [p for p in positions if p.get("magic") == self.magic_number]
            deviation = int(round(self.max_slippage)) if self.max_slippage else None

            last_close = float(df["close"].iloc[-1]) if "close" in df.columns and not df.empty else 0.0
            ema_9 = float(df["EMA_9"].iloc[-1]) if "EMA_9" in df.columns and not df.empty else 0.0
            ema_21 = float(df["EMA_21"].iloc[-1]) if "EMA_21" in df.columns and not df.empty else 0.0
            rsi = float(df["RSI"].iloc[-1]) if "RSI" in df.columns and not df.empty else 0.0
            atr = float(df["ATR"].iloc[-1]) if "ATR" in df.columns and not df.empty else 0.0
            market_state = self._market_bias(final_vote, active_votes)
            signal_details = {
                "action": "market_snapshot",
                "bot_id": self.bot_id,
                "bot_name": self.bot_name,
                "symbol": trade_symbol,
                "timeframe": self.timeframe,
                "decision": self._signal_label(decision),
                "final_vote": final_vote,
                "active_votes": active_votes,
                "market_state": market_state,
                "technical_signals": {key: self._signal_label(value) for key, value in tech_signals.items()},
                "ai_signal": self._signal_label(ai_signal),
                "spy_signal": self._signal_label(spy_signal),
                "spread": symbol_info.get("spread"),
                "last_close": round(last_close, 2),
                "ema_9": round(ema_9, 2),
                "ema_21": round(ema_21, 2),
                "rsi": round(rsi, 2),
                "atr": round(atr, 2),
                "open_positions": len(my_positions),
                "daily_pnl": risk_snapshot.get("daily_pnl", 0),
                "daily_trades": risk_snapshot.get("daily_trades", 0),
                "entry_allowed": entry_allowed,
                "entry_block_reason": entry_block_reason if not entry_allowed else None,
            }
            signal_signature = json.dumps(
                {
                    "bot_id": signal_details["bot_id"],
                    "symbol": signal_details["symbol"],
                    "timeframe": signal_details["timeframe"],
                    "decision": signal_details["decision"],
                    "final_vote": signal_details["final_vote"],
                    "active_votes": signal_details["active_votes"],
                    "market_state": signal_details["market_state"],
                    "technical_signals": signal_details["technical_signals"],
                    "ai_signal": signal_details["ai_signal"],
                    "spy_signal": signal_details["spy_signal"],
                    "entry_allowed": signal_details["entry_allowed"],
                    "entry_block_reason": signal_details["entry_block_reason"],
                },
                sort_keys=True,
                ensure_ascii=False,
            )

            if active_votes > 0 or decision != 0 or not entry_allowed:
                if self._should_log_market_state(signal_signature):
                    write_bot_log(
                        level="INFO",
                        context="signal",
                        message=(
                            f"{self.bot_name} | {trade_symbol} | {market_state} | "
                            f"vote={final_vote} | decision={signal_details['decision']}"
                        ),
                        details=signal_details,
                    )

            if not my_positions:
                if not entry_allowed:
                    logger.info("Bot %s sem nova entrada: %s", self.bot_id, entry_block_reason)
                    write_bot_log(
                        level="WARN",
                        context="trade_block",
                        message=f"Entrada bloqueada para {self.bot_name}",
                        details={
                            **signal_details,
                            "accepted": False,
                            "reason": entry_block_reason,
                            "action": "trade_block",
                        },
                    )
                elif decision == 1:
                    logger.info("Bot %s decidindo COMPRA para %s", self.bot_id, trade_symbol)
                    order_result = await mt5_client.place_order(
                        trade_symbol,
                        "buy",
                        lot,
                        sl=sl,
                        tp=tp,
                        magic=self.magic_number,
                        deviation=deviation,
                    )
                    accepted = bool(order_result)
                    write_bot_log(
                        level="INFO" if accepted else "ERROR",
                        context="trade_accept" if accepted else "trade_error",
                        message=(
                            f"Entrada aceita: BUY em {trade_symbol} para {self.bot_name}"
                            if accepted
                            else f"Falha ao executar BUY em {trade_symbol} para {self.bot_name}"
                        ),
                        details={
                            **signal_details,
                            "accepted": accepted,
                            "action": "buy",
                            "order_result": order_result or {},
                        },
                    )
                elif decision == -1:
                    logger.info("Bot %s decidindo VENDA para %s", self.bot_id, trade_symbol)
                    order_result = await mt5_client.place_order(
                        trade_symbol,
                        "sell",
                        lot,
                        sl=sl,
                        tp=tp,
                        magic=self.magic_number,
                        deviation=deviation,
                    )
                    accepted = bool(order_result)
                    write_bot_log(
                        level="INFO" if accepted else "ERROR",
                        context="trade_accept" if accepted else "trade_error",
                        message=(
                            f"Entrada aceita: SELL em {trade_symbol} para {self.bot_name}"
                            if accepted
                            else f"Falha ao executar SELL em {trade_symbol} para {self.bot_name}"
                        ),
                        details={
                            **signal_details,
                            "accepted": accepted,
                            "action": "sell",
                            "order_result": order_result or {},
                        },
                    )
            else:
                pos = my_positions[0]
                if (pos["type"] == "buy" and decision == -1) or (pos["type"] == "sell" and decision == 1):
                    logger.info("Bot %s fechando posição devido a inversão de sinal", self.bot_id)
                    closed = await mt5_client.close_position(pos["ticket"])
                    write_bot_log(
                        level="INFO",
                        context="trade_close",
                        message=f"Posicao fechada por inversao de sinal em {trade_symbol} para {self.bot_name}",
                        details={
                            **signal_details,
                            "accepted": bool(closed),
                            "action": "close",
                            "position_ticket": pos.get("ticket"),
                            "position_type": pos.get("type"),
                        },
                    )

            import redis
            import json

            r_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
            published_signal = int(decision or 0) if (entry_allowed or my_positions) else 0
            my_status = {
                "position": my_positions[0]["type"] if my_positions else "none",
                "signal": published_signal,
                "open_positions": len(my_positions),
                "pnl": sum(p.get("profit", 0) for p in my_positions),
                "symbol": trade_symbol,
                "magic": self.magic_number,
                "spread": symbol_info.get("spread"),
                "daily_pnl": risk_snapshot.get("daily_pnl", 0),
                "daily_trades": risk_snapshot.get("daily_trades", 0),
                "risk_blocked": entry_block_reason if not entry_allowed else None,
            }
            r_client.set(f"spy:{self.magic_number}", json.dumps(my_status), ex=60)
        finally:
            db.close()

    async def run(self):
        """Loop mantido para compatibilidade, mas agora controlado pelo Manager."""
        self.is_running = True
        logger.info("Iniciando loop do Bot %s (Híbrido)", self.bot_id)

        while self.is_running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error("Erro no ciclo do Bot %s: %s", self.bot_id, e)

            await asyncio.sleep(5)

    def stop(self):
        self.is_running = False
        logger.info("Parando Bot %s", self.bot_id)
