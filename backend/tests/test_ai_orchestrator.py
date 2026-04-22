"""
Testes para AI Orchestrator
Correção #4 - Arquitetura Bull/Bear + Consensus
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app.services.ai_orchestrator import (
    AIOrchestrator,
    BullEngine,
    BearEngine,
    ConsensusLayer,
    AnalysisResult,
    ConsensusResult
)


@pytest.fixture
def sample_market_data():
    """Dados de mercado de exemplo"""
    return {
        'close': 11500.0,
        'high': 11550.0,
        'low': 11450.0,
        'open': 11480.0,
        'volume': 1000,
        'rsi': 45.0,
        'sma_20': 11400.0,
        'sma_50': 11300.0,
        'macd': 50.0,
        'macd_signal': 45.0,
        'bb_upper': 11600.0,
        'bb_lower': 11400.0,
        'atr': 100.0
    }


@pytest.fixture
def bearish_market_data():
    """Dados de mercado em tendência de baixa"""
    return {
        'close': 11300.0,
        'high': 11350.0,
        'low': 11250.0,
        'open': 11320.0,
        'volume': 1500,
        'rsi': 65.0,
        'sma_20': 11400.0,
        'sma_50': 11500.0,
        'macd': -50.0,
        'macd_signal': -40.0,
        'bb_upper': 11400.0,
        'bb_lower': 11200.0,
        'atr': 100.0
    }


@pytest.fixture
def neutral_market_data():
    """Dados de mercado em lateralização"""
    return {
        'close': 11400.0,
        'high': 11420.0,
        'low': 11380.0,
        'open': 11400.0,
        'volume': 800,
        'rsi': 50.0,
        'sma_20': 11400.0,
        'sma_50': 11400.0,
        'macd': 0.0,
        'macd_signal': 0.0,
        'bb_upper': 11450.0,
        'bb_lower': 11350.0,
        'atr': 50.0
    }


class TestBullEngine:
    """Testes para Bull Engine"""
    
    def test_initialization(self):
        """Testar inicialização do Bull Engine"""
        engine = BullEngine()
        assert 'trend' in engine.weights
        assert 'momentum' in engine.weights
        assert 'volume' in engine.weights
    
    def test_analyze_bullish_signal(self, sample_market_data):
        """Testar análise de sinal bullish"""
        engine = BullEngine()
        result = engine.analyze("WIN", "M5", sample_market_data)
        
        assert result.signal in ["buy", "weak_buy", "neutral"]
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.score, float)
        assert isinstance(result.timestamp, datetime)
    
    def test_analyze_with_rsi_oversold(self):
        """Testar análise com RSI oversold"""
        engine = BullEngine()
        market_data = {
            'close': 11300.0,
            'rsi': 25.0,  # Oversold
            'sma_20': 11400.0,
            'sma_50': 11500.0,
            'macd': 10.0,
            'macd_signal': 5.0,
            'bb_upper': 11600.0,
            'bb_lower': 11200.0,
            'volume': 2000
        }
        
        result = engine.analyze("WIN", "M5", market_data)
        
        # Deve identificar oportunidade de compra (RSI oversold)
        assert result.score >= 50  # Score deve ser razoável
    
    def test_analyze_with_uptrend(self, sample_market_data):
        """Testar análise em tendência de alta"""
        engine = BullEngine()
        # Preço acima das médias
        sample_market_data['close'] = 11600.0
        sample_market_data['sma_20'] = 11500.0
        sample_market_data['sma_50'] = 11400.0
        
        result = engine.analyze("WIN", "M5", sample_market_data)
        
        assert result.score >= 50


class TestBearEngine:
    """Testes para Bear Engine"""
    
    def test_initialization(self):
        """Testar inicialização do Bear Engine"""
        engine = BearEngine()
        assert 'trend' in engine.weights
        assert 'momentum' in engine.weights
    
    def test_analyze_bearish_signal(self, bearish_market_data):
        """Testar análise de sinal bearish"""
        engine = BearEngine()
        result = engine.analyze("WIN", "M5", bearish_market_data)
        
        assert result.signal in ["sell", "weak_sell", "neutral"]
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.score, float)
    
    def test_analyze_with_rsi_overbought(self):
        """Testar análise com RSI overbought"""
        engine = BearEngine()
        market_data = {
            'close': 11700.0,
            'rsi': 75.0,  # Overbought
            'sma_20': 11600.0,
            'sma_50': 11500.0,
            'macd': -10.0,
            'macd_signal': -5.0,
            'bb_upper': 11650.0,
            'bb_lower': 11550.0,
            'volume': 2000
        }
        
        result = engine.analyze("WIN", "M5", market_data)
        
        # Deve identificar oportunidade de venda (RSI overbought)
        assert result.score >= 50


class TestConsensusLayer:
    """Testes para Consensus Layer"""
    
    def test_initialization(self):
        """Testar inicialização do Consensus Layer"""
        consensus = ConsensusLayer()
        assert hasattr(consensus, 'min_confidence_buy')
        assert hasattr(consensus, 'min_confidence_sell')
    
    def test_calculate_consensus_strong_buy(self):
        """Testar consenso para compra forte"""
        consensus = ConsensusLayer()
        
        bull_result = AnalysisResult(
            signal="buy",
            confidence=0.85,
            score=80.0,
            reasoning="Strong bullish trend",
            indicators={'trend': 80},
            timestamp=datetime.now()
        )
        
        bear_result = AnalysisResult(
            signal="neutral",
            confidence=0.4,
            score=30.0,
            reasoning="No bearish signals",
            indicators={'trend': 30},
            timestamp=datetime.now()
        )
        
        result = consensus.calculate_consensus(bull_result, bear_result)
        
        assert result.signal == "buy"
        assert result.confidence >= 0.65
        assert "bullish" in result.reasoning.lower()
    
    def test_calculate_consensus_strong_sell(self):
        """Testar consenso para venda forte"""
        consensus = ConsensusLayer()
        
        bull_result = AnalysisResult(
            signal="neutral",
            confidence=0.4,
            score=30.0,
            reasoning="No bullish signals",
            indicators={'trend': 30},
            timestamp=datetime.now()
        )
        
        bear_result = AnalysisResult(
            signal="sell",
            confidence=0.85,
            score=80.0,
            reasoning="Strong bearish trend",
            indicators={'trend': 80},
            timestamp=datetime.now()
        )
        
        result = consensus.calculate_consensus(bull_result, bear_result)
        
        assert result.signal == "sell"
        assert result.confidence >= 0.65
    
    def test_calculate_consensus_neutral(self):
        """Testar consenso neutro"""
        consensus = ConsensusLayer()
        
        bull_result = AnalysisResult(
            signal="neutral",
            confidence=0.5,
            score=50.0,
            reasoning="Mixed signals",
            indicators={'trend': 50},
            timestamp=datetime.now()
        )
        
        bear_result = AnalysisResult(
            signal="neutral",
            confidence=0.5,
            score=50.0,
            reasoning="Mixed signals",
            indicators={'trend': 50},
            timestamp=datetime.now()
        )
        
        result = consensus.calculate_consensus(bull_result, bear_result)
        
        assert result.signal in ["neutral", "hold"]
    
    def test_should_execute_trade(self):
        """Testar decisão de execução de trade"""
        consensus = ConsensusLayer(min_confidence_buy=0.65, min_confidence_sell=0.65)
        
        # Trade de compra com confiança suficiente
        buy_consensus = ConsensusResult(
            signal="buy",
            confidence=0.75,
            consensus_score=30.0,
            bull_contribution=65.0,
            bear_contribution=35.0,
            reasoning="Strong buy signal",
            recommendation="Execute BUY"
        )
        
        should_trade, reason = consensus.should_execute_trade(buy_consensus)
        assert should_trade is True
        assert "buy" in reason.lower()
        
        # Trade de compra com confiança insuficiente
        weak_buy_consensus = ConsensusResult(
            signal="buy",
            confidence=0.50,  # Abaixo do mínimo
            consensus_score=20.0,
            bull_contribution=55.0,
            bear_contribution=45.0,
            reasoning="Weak buy signal",
            recommendation="Wait"
        )
        
        should_trade, reason = consensus.should_execute_trade(weak_buy_consensus)
        assert should_trade is False
        assert "confiança" in reason.lower() or "confidence" in reason.lower()


class TestAIOrchestrator:
    """Testes para AI Orchestrator principal"""
    
    def test_initialization(self):
        """Testar inicialização do Orchestrator"""
        orchestrator = AIOrchestrator()
        
        assert orchestrator.bull_engine is not None
        assert orchestrator.bear_engine is not None
        assert orchestrator.consensus is not None
    
    def test_analyze_bullish_market(self, sample_market_data):
        """Testar análise de mercado bullish"""
        orchestrator = AIOrchestrator()
        result = orchestrator.analyze("WIN", "M5", sample_market_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'bull_score' in result
        assert 'bear_score' in result
        assert 'should_trade' in result
        assert result['signal'] in ["buy", "sell", "neutral", "hold", "weak_buy", "weak_sell"]
    
    def test_analyze_bearish_market(self, bearish_market_data):
        """Testar análise de mercado bearish"""
        orchestrator = AIOrchestrator()
        result = orchestrator.analyze("WIN", "M5", bearish_market_data)
        
        assert 'signal' in result
        assert 'confidence' in result
        assert 'bull_score' in result
        assert 'bear_score' in result
    
    def test_analysis_history(self, sample_market_data):
        """Testar histórico de análises"""
        orchestrator = AIOrchestrator()
        orchestrator.max_history = 5
        
        # Realizar múltiplas análises
        for _ in range(10):
            orchestrator.analyze("WIN", "M5", sample_market_data)
        
        # Histórico não deve ultrapassar max_history
        assert len(orchestrator.analysis_history) <= 5
    
    def test_get_trend_strength(self, sample_market_data):
        """Testar cálculo de força da tendência"""
        orchestrator = AIOrchestrator()
        
        # Realizar algumas análises
        for _ in range(10):
            orchestrator.analyze("WIN", "M5", sample_market_data)
        
        trend_data = orchestrator.get_trend_strength(lookback=5)
        
        assert 'trend' in trend_data
        assert 'strength' in trend_data
        assert trend_data['trend'] in ["bullish", "bearish", "neutral", "insufficient_data"]
    
    def test_get_last_signals(self, sample_market_data):
        """Testar obtenção de últimos sinais"""
        orchestrator = AIOrchestrator()
        
        # Realizar análises
        for _ in range(10):
            orchestrator.analyze("WIN", "M5", sample_market_data)
        
        signals = orchestrator.get_last_signals(count=5)
        
        assert len(signals) <= 5
        for signal in signals:
            assert 'signal' in signal
            assert 'confidence' in signal


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
