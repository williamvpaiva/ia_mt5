"""
Testes para Backtester
Correção #3 - Lógica real de backtesting sem scores fixos
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.services.backtester import (
    BacktestEngine, 
    TechnicalIndicators,
    BacktestTrade,
    BacktestMetrics
)


@pytest.fixture
def sample_market_data():
    """Dados de mercado de exemplo"""
    return {
        'close': 100.0,
        'high': 102.0,
        'low': 98.0,
        'open': 99.0,
        'volume': 1000,
        'rsi': 45.0,
        'sma_20': 98.0,
        'sma_50': 95.0,
        'macd': 1.5,
        'macd_signal': 1.2,
        'bb_upper': 105.0,
        'bb_lower': 95.0,
        'atr': 2.0
    }


@pytest.fixture
def sample_dataframe():
    """DataFrame de exemplo para backtest"""
    dates = pd.date_range(start='2024-01-01', periods=200, freq='H')
    np.random.seed(42)
    
    # Gerar preços aleatórios com tendência
    returns = np.random.randn(200).cumsum()
    prices = 100 + returns
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices,
        'high': prices + np.random.rand(200) * 2,
        'low': prices - np.random.rand(200) * 2,
        'close': prices,
        'tick_volume': np.random.randint(100, 1000, 200)
    })
    
    return df


class TestTechnicalIndicators:
    """Testes para indicadores técnicos"""
    
    def test_calculate_rsi(self, sample_dataframe):
        """Testar cálculo de RSI"""
        prices = sample_dataframe['close']
        rsi = TechnicalIndicators.calculate_rsi(prices, 14)
        
        assert len(rsi) == len(prices)
        assert rsi.dropna().between(0, 100).all()
    
    def test_calculate_sma(self, sample_dataframe):
        """Testar cálculo de SMA"""
        prices = sample_dataframe['close']
        sma = TechnicalIndicators.calculate_sma(prices, 20)
        
        assert len(sma) == len(prices)
        # Primeiros 19 valores são NaN (período da SMA)
        assert sma.iloc[:19].isna().all()
    
    def test_calculate_ema(self, sample_dataframe):
        """Testar cálculo de EMA"""
        prices = sample_dataframe['close']
        ema = TechnicalIndicators.calculate_ema(prices, 20)
        
        assert len(ema) == len(prices)
        assert not ema.isna().all()
    
    def test_calculate_macd(self, sample_dataframe):
        """Testar cálculo de MACD"""
        prices = sample_dataframe['close']
        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)
        
        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)
        assert len(histogram) == len(prices)
    
    def test_calculate_bollinger_bands(self, sample_dataframe):
        """Testar cálculo de Bandas de Bollinger"""
        prices = sample_dataframe['close']
        middle, upper, lower = TechnicalIndicators.calculate_bollinger_bands(prices)
        
        assert len(middle) == len(prices)
        assert len(upper) == len(prices)
        assert len(lower) == len(prices)
        
        # Banda superior > média > banda inferior
        assert (upper >= middle).all()
        assert (middle >= lower).all()
    
    def test_calculate_atr(self, sample_dataframe):
        """Testar cálculo de ATR"""
        df = sample_dataframe
        atr = TechnicalIndicators.calculate_atr(df['high'], df['low'], df['close'], 14)
        
        assert len(atr) == len(df)
        assert (atr > 0).all()
    
    def test_calculate_stochastic(self, sample_dataframe):
        """Testar cálculo do Estocástico"""
        df = sample_dataframe
        k, d = TechnicalIndicators.calculate_stochastic(df['high'], df['low'], df['close'])
        
        assert len(k) == len(df)
        assert len(d) == len(df)
        # %K e %D devem estar entre 0 e 100
        assert k.dropna().between(0, 100).all()


class TestBacktestEngine:
    """Testes para BacktestEngine"""
    
    def test_initialization(self):
        """Testar inicialização do engine"""
        engine = BacktestEngine(
            symbol="WIN",
            timeframe="M5",
            initial_balance=10000.0
        )
        
        assert engine.symbol == "WIN"
        assert engine.timeframe == "M5"
        assert engine.initial_balance == 10000.0
        assert engine.balance == 10000.0
    
    def test_fetch_historical_data(self):
        """Testar busca de dados históricos"""
        # Mock do mt5_client
        with patch('app.services.backtester.mt5_client') as mock_mt5:
            mock_mt5.get_rates = AsyncMock(return_value=[
                {'time': 1704067200, 'open': 100, 'high': 102, 'low': 98, 'close': 101, 'tick_volume': 1000}
            ])
            
            engine = BacktestEngine(symbol="WIN", timeframe="M5")
            # Teste assíncrono seria necessário aqui
    
    def test_calculate_indicators(self):
        """Testar cálculo de indicadores"""
        engine = BacktestEngine(symbol="WIN", timeframe="M5")
        dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
        
        df = pd.DataFrame({
            'time': dates,
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 100 + np.random.randn(100).cumsum() + 1,
            'low': 100 + np.random.randn(100).cumsum() - 1,
            'close': 100 + np.random.randn(100).cumsum(),
            'tick_volume': np.random.randint(100, 1000, 100)
        })
        
        df_with_indicators = engine.calculate_indicators(df)
        
        # Verificar se indicadores foram adicionados
        assert 'rsi' in df_with_indicators.columns
        assert 'sma_20' in df_with_indicators.columns
        assert 'macd' in df_with_indicators.columns
        assert 'bb_upper' in df_with_indicators.columns
    
    async def test_analyze_signal_no_ai(self):
        """Testar análise de sinal sem IA real"""
        engine = BacktestEngine(
            symbol="WIN",
            timeframe="M5",
            use_real_ai=False
        )
        
        # Simular dados de mercado
        market_data = {
            'close': 100.0,
            'rsi': 35.0,  # Oversold
            'sma_20': 98.0,
            'sma_50': 95.0,
            'macd': 1.5,
            'macd_signal': 1.2,
            'bb_upper': 105.0,
            'bb_lower': 95.0,
            'volume': 1500
        }
        
        # Adicionar dados ao DataFrame mock
        df = pd.DataFrame([market_data])
        df['close'] = [100.0]
        df['high'] = [102.0]
        df['low'] = [98.0]
        df['open'] = [99.0]
        df['tick_volume'] = [1500]
        
        # Calcular indicadores
        df = engine.calculate_indicators(df)
        df['time'] = pd.to_datetime(['2024-01-01'])
        
        signal_result = await engine.analyze_signal(df)
        
        assert 'signal' in signal_result
        assert 'confidence' in signal_result
        assert 'bull_score' in signal_result
        assert 'bear_score' in signal_result
    
    def test_metrics_calculation(self):
        """Testar cálculo de métricas"""
        engine = BacktestEngine(symbol="WIN", timeframe="M5")
        
        # Adicionar trades fictícios
        engine.trades = [
            BacktestTrade(
                entry_time=datetime(2024, 1, 1, 10, 0),
                exit_time=datetime(2024, 1, 1, 12, 0),
                entry_price=100.0,
                exit_price=102.0,
                direction="buy",
                volume=1.0,
                pnl=200.0,
                commission=2.0,
                swap=0.0,
                sl=None,
                tp=None,
                close_reason="tp"
            ),
            BacktestTrade(
                entry_time=datetime(2024, 1, 1, 14, 0),
                exit_time=datetime(2024, 1, 1, 16, 0),
                entry_price=102.0,
                exit_price=100.0,
                direction="buy",
                volume=1.0,
                pnl=-200.0,
                commission=2.0,
                swap=0.0,
                sl=None,
                tp=None,
                close_reason="sl"
            )
        ]
        
        engine.equity_curve = [10000.0, 10200.0, 10000.0]
        
        metrics = engine._calculate_metrics()
        
        assert isinstance(metrics, BacktestMetrics)
        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.win_rate == 50.0


class TestBacktestMetrics:
    """Testes para métricas de backtest"""
    
    def test_empty_metrics(self):
        """Testar métricas vazias"""
        engine = BacktestEngine(symbol="WIN", timeframe="M5")
        metrics = engine._calculate_metrics()
        
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0
        assert metrics.total_pnl == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
