import logging
from typing import Dict
from ..models.bot import Bot
from ..models.trade import Trade
from ..core.database import SessionLocal

logger = logging.getLogger("RiskGlobal")

class RiskGlobal:
    def __init__(self):
        # These could be loaded from config or environment variables
        self.max_daily_loss_percent = 5.0  # 5% max daily loss
        self.max_open_positions = 10       # Max total open positions across all bots
        self.max_volume_per_symbol = 50.0  # Max volume for WIN symbol
        
    def check_daily_loss_limit(self) -> bool:
        """Check if the daily loss is within limits"""
        db = SessionLocal()
        try:
            # This would typically check today's PnL against account balance
            # For now, we'll return True as a placeholder
            # In a real implementation, you'd calculate today's PnL from trades
            return True
        except Exception as e:
            logger.error(f"Error checking daily loss limit: {e}")
            return True  # Fail safe
        finally:
            db.close()
            
    def check_open_positions_limit(self) -> bool:
        """Check if total open positions are within limits"""
        db = SessionLocal()
        try:
            # Count open positions (trades without close_time)
            open_trades_count = db.query(Trade).filter(Trade.close_time.is_(None)).count()
            return open_trades_count < self.max_open_positions
        except Exception as e:
            logger.error(f"Error checking open positions limit: {e}")
            return True  # Fail safe
        finally:
            db.close()
            
    def check_volume_limit(self, symbol: str, requested_volume: float) -> bool:
        """Check if adding requested volume would exceed symbol limits"""
        db = SessionLocal()
        try:
            # Sum volume of open trades for this symbol
            open_trades = db.query(Trade).filter(
                Trade.symbol == symbol,
                Trade.close_time.is_(None)
            ).all()
            
            current_volume = sum(trade.volume for trade in open_trades)
            return (current_volume + requested_volume) <= self.max_volume_per_symbol
        except Exception as e:
            logger.error(f"Error checking volume limit: {e}")
            return True  # Fail safe
        finally:
            db.close()
            
    def validate_trade(self, bot: Bot, direction: str, volume: float) -> tuple[bool, str]:
        """Validate a trade against all risk limits"""
        # Check if bot is active
        if not bot.active:
            return False, "Bot is not active"
            
        # Check daily loss limit
        if not self.check_daily_loss_limit():
            return False, "Daily loss limit exceeded"
            
        # Check open positions limit
        if not self.check_open_positions_limit():
            return False, "Maximum open positions limit exceeded"
            
        # Check volume limit
        if not self.check_volume_limit(bot.symbol, volume):
            return False, f"Volume limit exceeded for {bot.symbol}"
            
        return True, "Trade validated"