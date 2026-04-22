import numpy as np
import pandas as pd
import pandas_ta as ta
from typing import Dict, Optional

from ..models.bot import Bot


class HybridDecisor:
    """
    Motor de decisao hibrido: sinais tecnicos + RL + modo espiao.
    """

    def __init__(self, bot: Bot, df: pd.DataFrame):
        self.bot = bot
        self.df = df
        self.config = bot.signals_config or {}
        self.risk = bot.risk_config or {}
        self.ai = bot.ai_config or {}
        self.spy = bot.spy_config or {}

    def calculate_signals(self) -> Dict[str, int]:
        """
        Calcula cada sinal de forma independente.
        Retorno: 1 (Buy), -1 (Sell), 0 (Neutral)
        """
        signals: Dict[str, int] = {}
        if len(self.df) < 2:
            return signals

        # 1. Direcao de medias
        if self.config.get("ma_cross", {}).get("active"):
            fast = self.config["ma_cross"]["fast_period"]
            slow = self.config["ma_cross"]["slow_period"]
            ma_f = ta.ema(self.df["close"], length=fast)
            ma_s = ta.ema(self.df["close"], length=slow)
            if ma_f.iloc[-1] > ma_s.iloc[-1]:
                signals["ma_cross"] = 1
            elif ma_f.iloc[-1] < ma_s.iloc[-1]:
                signals["ma_cross"] = -1
            else:
                signals["ma_cross"] = 0

        # 2. RSI
        if self.config.get("rsi", {}).get("active"):
            period = self.config["rsi"]["period"]
            rsi = ta.rsi(self.df["close"], length=period)
            if rsi.iloc[-1] < self.config["rsi"]["oversold"]:
                signals["rsi"] = 1
            elif rsi.iloc[-1] > self.config["rsi"]["overbought"]:
                signals["rsi"] = -1
            else:
                signals["rsi"] = 0

        # 3. ATR como confirmacao de rompimento
        if self.config.get("atr", {}).get("active"):
            period = self.config["atr"].get("period", 14)
            multiplier = float(self.config["atr"].get("multiplier", 2.0))
            atr = ta.atr(self.df["high"], self.df["low"], self.df["close"], length=period)
            if not atr.empty and not pd.isna(atr.iloc[-1]):
                atr_value = float(atr.iloc[-1])
                last_close = float(self.df["close"].iloc[-1])
                prev_close = float(self.df["close"].iloc[-2])
                upper_break = prev_close + (atr_value * multiplier)
                lower_break = prev_close - (atr_value * multiplier)
                if last_close > upper_break:
                    signals["atr"] = 1
                elif last_close < lower_break:
                    signals["atr"] = -1
                else:
                    signals["atr"] = 0

        # 4. Price Action: pinbar e engulfing
        price_action = self.config.get("price_action", {})
        if price_action.get("active"):
            enabled_patterns = {str(p).lower() for p in (price_action.get("patterns") or [])}
            last = self.df.iloc[-1]
            prev = self.df.iloc[-2]
            body = abs(float(last["close"]) - float(last["open"]))
            upper_shadow = float(last["high"]) - max(float(last["open"]), float(last["close"]))
            lower_shadow = min(float(last["open"]), float(last["close"])) - float(last["low"])

            bullish = False
            bearish = False

            if "pinbar" in enabled_patterns:
                bullish_pin = lower_shadow > (body * 2) and upper_shadow <= max(body, 1e-9) and float(last["close"]) > float(last["open"])
                bearish_pin = upper_shadow > (body * 2) and lower_shadow <= max(body, 1e-9) and float(last["close"]) < float(last["open"])
                bullish = bullish or bullish_pin
                bearish = bearish or bearish_pin

            if "engulfing" in enabled_patterns:
                prev_bear = float(prev["close"]) < float(prev["open"])
                prev_bull = float(prev["close"]) > float(prev["open"])
                curr_bull = float(last["close"]) > float(last["open"])
                curr_bear = float(last["close"]) < float(last["open"])
                bullish_engulf = prev_bear and curr_bull and float(last["close"]) >= float(prev["open"]) and float(last["open"]) <= float(prev["close"])
                bearish_engulf = prev_bull and curr_bear and float(last["open"]) >= float(prev["close"]) and float(last["close"]) <= float(prev["open"])
                bullish = bullish or bullish_engulf
                bearish = bearish or bearish_engulf

            if bullish and not bearish:
                signals["price_action"] = 1
            elif bearish and not bullish:
                signals["price_action"] = -1
            else:
                signals["price_action"] = 0

        return signals

    def get_spy_signal(self, target_status: Dict) -> int:
        """
        Consulta o sinal do bot espiao.
        """
        if not self.spy.get("active") or not target_status:
            return 0

        if not self.spy.get("follow_signals") and not self.spy.get("follow_trades"):
            return 0

        if self.spy.get("follow_signals"):
            signal = target_status.get("signal")
            if signal in (1, -1):
                return int(signal)

        if not self.spy.get("follow_trades"):
            return 0

        if target_status.get("position") == "buy":
            return 1
        if target_status.get("position") == "sell":
            return -1
        return 0

    def get_ai_prediction(self, model) -> int:
        """
        Consulta o modelo de reinforcement learning.
        """
        if not self.ai.get("rl_active") or model is None:
            return 0

        print(f"DEBUG IA [{self.bot.name}]: Verificando IA...")
        cols = ["open", "high", "low", "close", "tick_volume", "EMA_9", "EMA_21", "RSI", "ATR"]

        try:
            obs_df = self.df[cols].iloc[-1]
            obs = obs_df.values.astype(np.float32)
            action, _states = model.predict(obs, deterministic=True)
            action_idx = int(np.asarray(action).item())

            threshold = float(self.ai.get("confidence_threshold", 0) or 0)
            if threshold > 0:
                try:
                    obs_tensor, _ = model.policy.obs_to_tensor(obs)
                    distribution = model.policy.get_distribution(obs_tensor)
                    probs = getattr(getattr(distribution, "distribution", None), "probs", None)
                    if probs is not None:
                        confidence = float(probs[0, action_idx].detach().cpu().item())
                        if confidence < threshold:
                            print(
                                f"DEBUG IA [{self.bot.name}]: Confiança {confidence:.3f} abaixo do limiar {threshold:.3f}"
                            )
                            return 0
                except Exception as exc:
                    print(f"DEBUG IA: nao foi possivel calcular confianca: {exc}")

            if action_idx == 1:
                return 1
            if action_idx == 2:
                return -1
        except Exception as e:
            print(f"DEBUG IA: Erro ao prever com PPO: {e}")
            return 0

        return 0

    def decide(self, rl_model=None, spy_status=None) -> int:
        """
        Consolida todos os sinais ativos em uma decisao final.
        """
        tech_signals = self.calculate_signals()
        ai_signal = self.get_ai_prediction(rl_model)
        spy_signal = self.get_spy_signal(spy_status)

        print(f"DEBUG [{self.bot.name}]: Tech={tech_signals} | AI={ai_signal} | Spy={spy_signal}")

        if self.ai.get("rl_active") and self.ai.get("mode") == "pure_ia":
            return ai_signal

        final_vote = 0
        active_votes = 0

        for _, val in tech_signals.items():
            if val != 0:
                final_vote += val
                active_votes += 1

        if self.spy.get("active") and spy_signal != 0:
            final_vote += spy_signal
            active_votes += 1

        if self.ai.get("rl_active") and ai_signal != 0:
            final_vote += ai_signal
            active_votes += 1

        if active_votes == 0:
            return 0

        if self.ai.get("rl_active") and self.ai.get("mode") == "pure_signals":
            return 1 if final_vote > 0 else -1 if final_vote < 0 else 0

        if final_vote > 0:
            print(f"DEBUG [{self.bot.name}]: VOTO FINAL COMPRA (+{final_vote})")
            return 1
        if final_vote < 0:
            print(f"DEBUG [{self.bot.name}]: VOTO FINAL VENDA ({final_vote})")
            return -1
        return 0
