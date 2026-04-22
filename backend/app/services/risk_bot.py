"""
Risk Management per Bot
CorreA?A?o: ImplementaA?A?o do gerenciamento de risco por bot
Prioridade: ALTA
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.bot import Bot
from ..models.trade import Trade
from ..core.database import SessionLocal

logger = logging.getLogger("RiskBot")


class RiskBotConfig:
    """ConfiguraA?A?o de risco para cada bot"""
    def __init__(
        self,
        stop_loss_pct: float = 2.0,           # Stop loss percentual
        take_profit_pct: float = 4.0,       # Take profit percentual
        trailing_stop: bool = False,         # Trailing stop ativado
        trailing_stop_distance: float = 1.0, # DistA?ncia do trailing stop
        max_positions: int = 3,             # MA?ximo de posiA?A?es abertas
        max_daily_trades: int = 10,         # MA?ximo de trades por dia
        max_daily_loss: float = 5.0,        # Perda mA?xima diA?ria (%)
        max_position_size: float = 10.0,   # Tamanho mA?ximo da posiA?A?o
        min_position_size: float = 0.1,     # Tamanho mA?nimo da posiA?A?o
        risk_per_trade_pct: float = 1.0,   # Risco por trade (%)
        breakeven_enabled: bool = True,     # Mover para breakeven
        breakeven_trigger: float = 1.0,     # Quando mover para breakeven (%)
        partial_close: bool = False,          # Fechamento parcial
        partial_close_pct: float = 50.0,    # % do volume para fechar
        partial_close_trigger: float = 2.0, # Quando fechar parcialmente
    ):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop = trailing_stop
        self.trailing_stop_distance = trailing_stop_distance
        self.max_positions = max_positions
        self.max_daily_trades = max_daily_trades
        self.max_daily_loss = max_daily_loss
        self.max_position_size = max_position_size
        self.min_position_size = min_position_size
        self.risk_per_trade_pct = risk_per_trade_pct
        self.breakeven_enabled = breakeven_enabled
        self.breakeven_trigger = breakeven_trigger
        self.partial_close = partial_close
        self.partial_close_pct = partial_close_pct
        self.partial_close_trigger = partial_close_trigger


class RiskBot:
    """
    Gerenciamento de risco por bot individual
    CorreA?A?o: Criado serviA?o de risco especA?fico para cada bot
    """
    
    def __init__(self, bot: Bot, config: Optional[RiskBotConfig] = None):
        self.bot = bot
        self.config = config or self._load_config_from_bot(bot)
        self.db = SessionLocal()
    
    def _load_config_from_bot(self, bot: Bot) -> RiskBotConfig:
        """Carregar configuraA?A?o do bot ou usar padrA?es"""
        if bot.config and isinstance(bot.config, dict):
            config_data = bot.config.get('risk', {})
            return RiskBotConfig(**config_data)
        return RiskBotConfig()
    
    def __del__(self):
        """Fechar sessA?o do banco"""
        if hasattr(self, 'db'):
            self.db.close()
    
    # ========== VALIDAA?A?ES PRINCIPAIS ==========
    
    def validate_trade(self, direction: str, volume: float, entry_price: Optional[float] = None) -> tuple[bool, str]:
        """
        Validar se um trade pode ser executado
        Retorna: (permitido, mensagem)
        """
        # Verificar se bot estA? ativo
        if not self.bot.active:
            return False, "Bot is not active"
        
        # Verificar limite de posiA?A?es
        if not self.check_positions_limit():
            return False, f"Maximum positions ({self.config.max_positions}) reached for bot {self.bot.name}"
        
        # Verificar limite de trades diA?rios
        if not self.check_daily_trades_limit():
            return False, f"Maximum daily trades ({self.config.max_daily_trades}) reached"
        
        # Verificar limite de perda diA?ria
        if not self.check_daily_loss_limit():
            return False, f"Daily loss limit ({self.config.max_daily_loss}%) exceeded"
        
        # Verificar tamanho da posiA?A?o
        if not self.check_position_size(volume):
            return False, f"Position size {volume} outside limits ({self.config.min_position_size}-{self.config.max_position_size})"
        
        # Verificar spread
        if hasattr(self.bot, 'max_spread') and self.bot.max_spread:
            # VerificaA?A?o simulada - em produA?A?o virA? do MT5
            pass
        
        logger.info(f"Trade validated for bot {self.bot.name}: {direction} {volume}")
        return True, "Trade validated"
    
    def check_positions_limit(self) -> bool:
        """Verificar se bot atingiu limite de posiA?A?es abertas"""
        try:
            open_count = self.db.query(Trade).filter(
                Trade.bot_id == self.bot.id,
                Trade.close_time.is_(None)
            ).count()
            return open_count < self.config.max_positions
        except Exception as e:
            logger.error(f"Error checking positions limit: {e}")
            return True  # Fail safe
    
    def check_daily_trades_limit(self) -> bool:
        """Verificar limite de trades diA?rios"""
        try:
            today = datetime.utcnow().date()
            daily_count = self.db.query(Trade).filter(
                Trade.bot_id == self.bot.id,
                func.date(Trade.open_time) == today
            ).count()
            return daily_count < self.config.max_daily_trades
        except Exception as e:
            logger.error(f"Error checking daily trades limit: {e}")
            return True
    
    def check_daily_loss_limit(self) -> bool:
        """Verificar limite de perda diA?ria"""
        try:
            today = datetime.utcnow().date()
            daily_trades = self.db.query(Trade).filter(
                Trade.bot_id == self.bot.id,
                func.date(Trade.close_time) == today,
                Trade.close_time.isnot(None)
            ).all()
            
            daily_pnl = sum(t.pnl or 0 for t in daily_trades)
            
            # Calcular % de perda (simplificado - assumindo saldo fixo)
            # Em produA?A?o, usar saldo real da conta
            account_balance = 10000  # Placeholder
            daily_loss_pct = (abs(daily_pnl) / account_balance) * 100 if daily_pnl < 0 else 0
            
            return daily_loss_pct < self.config.max_daily_loss
        except Exception as e:
            logger.error(f"Error checking daily loss limit: {e}")
            return True
    
    def check_position_size(self, volume: float) -> bool:
        """Verificar se tamanho da posiA?A?o estA? dentro dos limites"""
        return self.config.min_position_size <= volume <= self.config.max_position_size
    
    # ========== CA?LCULO DE NA?VEIS ==========
    
    def calculate_stop_loss(self, entry_price: float, direction: str) -> float:
        """Calcular nA?vel de stop loss"""
        if direction == "buy":
            sl = entry_price * (1 - self.config.stop_loss_pct / 100)
        else:  # sell
            sl = entry_price * (1 + self.config.stop_loss_pct / 100)
        return round(sl, 2)
    
    def calculate_take_profit(self, entry_price: float, direction: str) -> float:
        """Calcular nA?vel de take profit"""
        if direction == "buy":
            tp = entry_price * (1 + self.config.take_profit_pct / 100)
        else:  # sell
            tp = entry_price * (1 - self.config.take_profit_pct / 100)
        return round(tp, 2)
    
    def calculate_position_size(self, account_balance: float, risk_pct: Optional[float] = None) -> float:
        """
        Calcular tamanho da posiA?A?o baseado no risco
        CorreA?A?o: Position sizing baseado em risco
        """
        risk = risk_pct or self.config.risk_per_trade_pct
        risk_amount = account_balance * (risk / 100)
        
        # Assumindo stop loss como referAancia
        stop_distance = self.config.stop_loss_pct / 100
        
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
        else:
            position_size = self.config.max_position_size
        
        # Limitar aos mA?ximos configurados
        position_size = min(position_size, self.config.max_position_size)
        position_size = max(position_size, self.config.min_position_size)
        
        return round(position_size, 2)
    
    # ========== TRAILING STOP ==========
    
    def update_trailing_stop(self, trade: Trade, current_price: float) -> Optional[float]:
        """
        Atualizar trailing stop se necessA?rio
        Retorna novo nA?vel de SL ou None
        """
        if not self.config.trailing_stop:
            return None
        
        if trade.close_time:
            return None  # Trade jA? fechado
        
        entry = trade.entry_price or 0
        current_sl = trade.sl
        
        if trade.direction == "buy":
            # Para compra: trailing stop sobe com o preA?o
            profit_pct = (current_price - entry) / entry * 100
            if profit_pct > self.config.trailing_stop_distance:
                new_sl = current_price * (1 - self.config.trailing_stop_distance / 100)
                if current_sl is None or new_sl > current_sl:
                    return round(new_sl, 2)
        else:  # sell
            # Para venda: trailing stop desce com o preA?o
            profit_pct = (entry - current_price) / entry * 100
            if profit_pct > self.config.trailing_stop_distance:
                new_sl = current_price * (1 + self.config.trailing_stop_distance / 100)
                if current_sl is None or new_sl < current_sl:
                    return round(new_sl, 2)
        
        return None
    
    # ========== BREAKEVEN ==========
    
    def check_breakeven(self, trade: Trade, current_price: float) -> bool:
        """
        Verificar se deve mover para breakeven
        """
        if not self.config.breakeven_enabled:
            return False
        
        if trade.close_time:
            return False
        
        entry = trade.entry_price or 0
        
        if trade.direction == "buy":
            profit_pct = (current_price - entry) / entry * 100
        else:
            profit_pct = (entry - current_price) / entry * 100
        
        return profit_pct >= self.config.breakeven_trigger
    
    # ========== FECHAMENTO PARCIAL ==========
    
    def check_partial_close(self, trade: Trade, current_price: float) -> tuple[bool, float]:
        """
        Verificar se deve fazer fechamento parcial
        Retorna: (deve_fechar, volume_a_fechar)
        """
        if not self.config.partial_close:
            return False, 0.0
        
        if trade.close_time:
            return False, 0.0
        
        entry = trade.entry_price or 0
        
        if trade.direction == "buy":
            profit_pct = (current_price - entry) / entry * 100
        else:
            profit_pct = (entry - current_price) / entry * 100
        
        if profit_pct >= self.config.partial_close_trigger:
            volume_to_close = trade.volume * (self.config.partial_close_pct / 100)
            return True, volume_to_close
        
        return False, 0.0
    
    # ========== ESTATA?STICAS ==========
    
    def get_risk_metrics(self) -> dict:
        """Obter mA?tricas de risco do bot"""
        try:
            # Trades abertos
            open_trades = self.db.query(Trade).filter(
                Trade.bot_id == self.bot.id,
                Trade.close_time.is_(None)
            ).all()
            
            # Trades de hoje
            today = datetime.utcnow().date()
            today_trades = self.db.query(Trade).filter(
                Trade.bot_id == self.bot.id,
                func.date(Trade.open_time) == today
            ).count()
            
            # PnL diA?rio
            daily_pnl = self.db.query(Trade).filter(
                Trade.bot_id == self.bot.id,
                func.date(Trade.close_time) == today,
                Trade.close_time.isnot(None)
            ).all()
            daily_pnl_total = sum(t.pnl or 0 for t in daily_pnl)
            
            # PnL total
            all_closed = self.db.query(Trade).filter(
                Trade.bot_id == self.bot.id,
                Trade.close_time.isnot(None)
            ).all()
            total_pnl = sum(t.pnl or 0 for t in all_closed)
            
            # Win rate
            winning = len([t for t in all_closed if (t.pnl or 0) > 0])
            total_closed = len(all_closed)
            win_rate = (winning / total_closed * 100) if total_closed > 0 else 0
            
            return {
                "bot_id": self.bot.id,
                "bot_name": self.bot.name,
                "open_positions": len(open_trades),
                "max_positions": self.config.max_positions,
                "daily_trades": today_trades,
                "max_daily_trades": self.config.max_daily_trades,
                "daily_pnl": round(daily_pnl_total, 2),
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 2),
                "total_closed_trades": total_closed,
                "stop_loss_pct": self.config.stop_loss_pct,
                "take_profit_pct": self.config.take_profit_pct,
                "trailing_stop": self.config.trailing_stop,
            }
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return {}
    
    def should_trade(self, signal: str, confidence: float) -> tuple[bool, str]:
        """
        DecisA?o final se deve executar trade baseado em risco
        """
        # Verificar todas as condiA?A?es
        checks = [
            ("Bot active", self.bot.active),
            ("Positions limit", self.check_positions_limit()),
            ("Daily trades limit", self.check_daily_trades_limit()),
            ("Daily loss limit", self.check_daily_loss_limit()),
        ]
        
        for name, passed in checks:
            if not passed:
                logger.warning(f"Risk check failed for bot {self.bot.name}: {name}")
                return False, f"Risk check failed: {name}"
        
        # Verificar confianA?a mA?nima
        min_confidence = self.bot.config.get('min_confidence', 0.6) if self.bot.config else 0.6
        if confidence < min_confidence:
            return False, f"Confidence {confidence} below threshold {min_confidence}"
        
        return True, "All risk checks passed"


class RiskBotManager:
    """Gerenciador centralizado de risco para todos os bots"""
    
    def __init__(self):
        self.risk_configs: Dict[int, RiskBotConfig] = {}
    
    def get_or_create_config(self, bot: Bot) -> RiskBot:
        """Obter ou criar gerenciador de risco para bot"""
        return RiskBot(bot)
    
    def get_all_bots_risk_summary(self) -> List[dict]:
        """Resumo de risco de todos os bots"""
        db = SessionLocal()
        try:
            bots = db.query(Bot).filter(Bot.active == True).all()
            summaries = []
            for bot in bots:
                risk_bot = RiskBot(bot)
                metrics = risk_bot.get_risk_metrics()
                if metrics:
                    summaries.append(metrics)
            return summaries
        finally:
            db.close()
