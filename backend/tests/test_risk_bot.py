"""
Testes para Risk Bot
Correção #2 - Gerenciamento de risco por bot
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from app.services.risk_bot import RiskBot, RiskBotConfig, RiskBotManager
from app.models.bot import Bot
from app.models.trade import Trade


@pytest.fixture
def sample_bot():
    """Bot de teste"""
    bot = Mock(spec=Bot)
    bot.id = 1
    bot.name = "Test Bot"
    bot.symbol = "WIN"
    bot.active = True
    bot.config = {
        'risk': {
            'stop_loss_pct': 2.0,
            'take_profit_pct': 4.0,
            'max_positions': 3,
            'max_daily_trades': 10
        }
    }
    return bot


@pytest.fixture
def sample_config():
    """Configuração de risco padrão"""
    return RiskBotConfig(
        stop_loss_pct=2.0,
        take_profit_pct=4.0,
        max_positions=3,
        max_daily_trades=10,
        max_daily_loss=5.0,
        max_position_size=10.0,
        min_position_size=0.1
    )


class TestRiskBotConfig:
    """Testes para configuração de risco"""
    
    def test_default_config(self):
        """Testar configuração padrão"""
        config = RiskBotConfig()
        assert config.stop_loss_pct == 2.0
        assert config.take_profit_pct == 4.0
        assert config.max_positions == 3
        assert config.trailing_stop is False
    
    def test_custom_config(self):
        """Testar configuração customizada"""
        config = RiskBotConfig(
            stop_loss_pct=3.0,
            take_profit_pct=6.0,
            max_positions=5
        )
        assert config.stop_loss_pct == 3.0
        assert config.take_profit_pct == 6.0
        assert config.max_positions == 5


class TestRiskBot:
    """Testes para RiskBot"""
    
    def test_validate_trade_bot_inactive(self, sample_bot, sample_config):
        """Testar validação quando bot está inativo"""
        sample_bot.active = False
        risk_bot = RiskBot(sample_bot, sample_config)
        
        allowed, message = risk_bot.validate_trade(direction="buy", volume=1.0)
        assert allowed is False
        assert "not active" in message
    
    def test_validate_trade_success(self, sample_bot, sample_config, monkeypatch):
        """Testar validação de trade bem-sucedida"""
        # Mock das verificações
        monkeypatch.setattr(RiskBot, 'check_positions_limit', lambda self: True)
        monkeypatch.setattr(RiskBot, 'check_daily_trades_limit', lambda self: True)
        monkeypatch.setattr(RiskBot, 'check_daily_loss_limit', lambda self: True)
        
        risk_bot = RiskBot(sample_bot, sample_config)
        allowed, message = risk_bot.validate_trade(direction="buy", volume=1.0)
        
        assert allowed is True
        assert "validated" in message
    
    def test_check_position_size(self, sample_bot, sample_config):
        """Testar verificação de tamanho de posição"""
        risk_bot = RiskBot(sample_bot, sample_config)
        
        # Dentro dos limites
        assert risk_bot.check_position_size(1.0) is True
        assert risk_bot.check_position_size(5.0) is True
        
        # Fora dos limites
        assert risk_bot.check_position_size(0.05) is False  # Abaixo do mínimo
        assert risk_bot.check_position_size(15.0) is False  # Acima do máximo
    
    def test_calculate_stop_loss_buy(self, sample_bot, sample_config):
        """Testar cálculo de stop loss para compra"""
        risk_bot = RiskBot(sample_bot, sample_config)
        entry_price = 100.0
        
        # Stop loss de 2% para compra
        sl = risk_bot.calculate_stop_loss(entry_price, "buy")
        assert sl == 98.0  # 100 - 2%
    
    def test_calculate_stop_loss_sell(self, sample_bot, sample_config):
        """Testar cálculo de stop loss para venda"""
        risk_bot = RiskBot(sample_bot, sample_config)
        entry_price = 100.0
        
        # Stop loss de 2% para venda
        sl = risk_bot.calculate_stop_loss(entry_price, "sell")
        assert sl == 102.0  # 100 + 2%
    
    def test_calculate_take_profit_buy(self, sample_bot, sample_config):
        """Testar cálculo de take profit para compra"""
        risk_bot = RiskBot(sample_bot, sample_config)
        entry_price = 100.0
        
        # Take profit de 4% para compra
        tp = risk_bot.calculate_take_profit(entry_price, "buy")
        assert tp == 104.0  # 100 + 4%
    
    def test_calculate_take_profit_sell(self, sample_bot, sample_config):
        """Testar cálculo de take profit para venda"""
        risk_bot = RiskBot(sample_bot, sample_config)
        entry_price = 100.0
        
        # Take profit de 4% para venda
        tp = risk_bot.calculate_take_profit(entry_price, "sell")
        assert tp == 96.0  # 100 - 4%
    
    def test_calculate_position_size(self, sample_bot, sample_config):
        """Testar cálculo de tamanho de posição"""
        risk_bot = RiskBot(sample_bot, sample_config)
        account_balance = 10000.0
        
        # 1% de risco em conta de 10k = 100
        # Com stop de 2%, posição = 100 / 0.02 = 5000
        size = risk_bot.calculate_position_size(account_balance, risk_pct=1.0)
        assert size <= sample_config.max_position_size
        assert size >= sample_config.min_position_size


class TestRiskBotManager:
    """Testes para RiskBotManager"""
    
    def test_get_or_create_config(self, sample_bot):
        """Testar obtenção/criação de config"""
        manager = RiskBotManager()
        risk_bot = manager.get_or_create_config(sample_bot)
        
        assert isinstance(risk_bot, RiskBot)
        assert risk_bot.bot == sample_bot
    
    def test_get_all_bots_risk_summary(self):
        """Testar resumo de risco de todos os bots"""
        manager = RiskBotManager()
        # Este teste requer banco de dados configurado
        # Por enquanto, apenas verifica se o método existe e retorna lista
        summaries = manager.get_all_bots_risk_summary()
        assert isinstance(summaries, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
