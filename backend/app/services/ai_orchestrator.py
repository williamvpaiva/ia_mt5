"""
AI Orchestrator - Bull/Bear Engines + Consensus
CorreA?A?o: ImplementaA?A?o da arquitetura especificada
Prioridade: MA?DIA
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("AIOrchestrator")


@dataclass
class AnalysisResult:
    signal: str
    confidence: float
    score: float
    reasoning: str
    indicators: Dict
    timestamp: datetime


@dataclass  
class ConsensusResult:
    signal: str
    confidence: float
    consensus_score: float
    bull_contribution: float
    bear_contribution: float
    reasoning: str
    recommendation: str


class BullEngine:
    """Motor de anA?lise Bull (tendAancia de alta)"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.weights = {
            'trend': 0.25, 'momentum': 0.20, 'volume': 0.15,
            'sentiment': 0.20, 'support_resistance': 0.20
        }
    
    def analyze(self, symbol: str, timeframe: str, market_data: Dict) -> AnalysisResult:
        scores = {}
        reasoning_parts = []
        
        # AnA?lise de tendAancia
        close = market_data.get('close', 0)
        sma_20 = market_data.get('sma_20', close)
        sma_50 = market_data.get('sma_50', close)
        trend_score = 50
        if close > sma_20 > sma_50:
            trend_score += 30
            reasoning_parts.append("Uptrend detected")
        elif close > sma_20:
            trend_score += 15
        scores['trend'] = trend_score
        
        # Momento (RSI)
        rsi = market_data.get('rsi', 50)
        momentum_score = 50
        if 30 <= rsi <= 50:
            momentum_score += 25
            reasoning_parts.append(f"RSI recovering from oversold ({rsi:.1f})")
        scores['momentum'] = momentum_score
        
        # Volume
        volume_score = 50
        if market_data.get('volume', 0) > 1000:
            volume_score += 20
        scores['volume'] = volume_score
        
        # Score ponderado
        weighted_score = sum(scores.get(k, 0) * self.weights.get(k, 0) for k in self.weights)
        
        if weighted_score >= 70:
            signal = "buy"
            confidence = min(weighted_score / 100, 0.95)
        elif weighted_score >= 50:
            signal = "weak_buy"
            confidence = weighted_score / 100
        else:
            signal = "neutral"
            confidence = 1 - (weighted_score / 100)
        
        return AnalysisResult(
            signal=signal, confidence=confidence, score=weighted_score,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No clear bullish signal",
            indicators=scores, timestamp=datetime.utcnow()
        )


class BearEngine:
    """Motor de anA?lise Bear (tendAancia de baixa)"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.weights = {
            'trend': 0.25, 'momentum': 0.20, 'volume': 0.15,
            'sentiment': 0.20, 'support_resistance': 0.20
        }
    
    def analyze(self, symbol: str, timeframe: str, market_data: Dict) -> AnalysisResult:
        scores = {}
        reasoning_parts = []
        
        # AnA?lise de tendAancia
        close = market_data.get('close', 0)
        sma_20 = market_data.get('sma_20', close)
        sma_50 = market_data.get('sma_50', close)
        trend_score = 50
        if close < sma_20 < sma_50:
            trend_score += 30
            reasoning_parts.append("Downtrend detected")
        elif close < sma_20:
            trend_score += 15
        scores['trend'] = trend_score
        
        # Momento (RSI)
        rsi = market_data.get('rsi', 50)
        momentum_score = 50
        if 60 <= rsi <= 70:
            momentum_score += 25
            reasoning_parts.append(f"RSI approaching overbought ({rsi:.1f})")
        scores['momentum'] = momentum_score
        
        # Volume
        volume_score = 50
        if market_data.get('volume', 0) > 1000:
            volume_score += 20
        scores['volume'] = volume_score
        
        # Score ponderado
        weighted_score = sum(scores.get(k, 0) * self.weights.get(k, 0) for k in self.weights)
        
        if weighted_score >= 70:
            signal = "sell"
            confidence = min(weighted_score / 100, 0.95)
        elif weighted_score >= 50:
            signal = "weak_sell"
            confidence = weighted_score / 100
        else:
            signal = "neutral"
            confidence = 1 - (weighted_score / 100)
        
        return AnalysisResult(
            signal=signal, confidence=confidence, score=weighted_score,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No clear bearish signal",
            indicators=scores, timestamp=datetime.utcnow()
        )


class ConsensusLayer:
    """Camada de consenso entre Bull e Bear"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.min_confidence_buy = config.get('min_confidence_buy', 0.65)
        self.min_confidence_sell = config.get('min_confidence_sell', 0.65)
        self.consensus_threshold = config.get('consensus_threshold', 20.0)
    
    def calculate_consensus(self, bull_result: AnalysisResult, bear_result: AnalysisResult) -> ConsensusResult:
        bull_score = bull_result.score
        bear_score = bear_result.score
        score_diff = abs(bull_score - bear_score)
        
        total_score = bull_score + bear_score
        if total_score > 0:
            bull_contribution = (bull_score / total_score) * 100
            bear_contribution = (bear_score / total_score) * 100
        else:
            bull_contribution = 50
            bear_contribution = 50
        
        consensus_score = bull_score - bear_score
        
        # Determinar sinal final
        if bull_score >= 70 and bear_score < 50:
            signal = "buy"
            confidence = bull_result.confidence
            recommendation = "Execute BUY order"
            reasoning = f"Strong bullish: {bull_result.reasoning}"
        elif bear_score >= 70 and bull_score < 50:
            signal = "sell"
            confidence = bear_result.confidence
            recommendation = "Execute SELL order"
            reasoning = f"Strong bearish: {bear_result.reasoning}"
        elif score_diff < self.consensus_threshold:
            signal = "neutral"
            confidence = 0.5
            recommendation = "No action"
            reasoning = "Market in equilibrium"
        else:
            signal = "hold"
            confidence = max(bull_result.confidence, bear_result.confidence)
            recommendation = "Wait for confirmation"
            reasoning = "Wait for clearer signal"
        
        return ConsensusResult(
            signal=signal, confidence=round(confidence, 2),
            consensus_score=consensus_score,
            bull_contribution=bull_contribution, bear_contribution=bear_contribution,
            reasoning=reasoning, recommendation=recommendation
        )
    
    def should_execute_trade(self, consensus: ConsensusResult) -> Tuple[bool, str]:
        if consensus.signal in ["buy", "weak_buy"]:
            if consensus.confidence < self.min_confidence_buy:
                return False, f"Buy confidence {consensus.confidence:.2f} below min {self.min_confidence_buy}"
        elif consensus.signal in ["sell", "weak_sell"]:
            if consensus.confidence < self.min_confidence_sell:
                return False, f"Sell confidence {consensus.confidence:.2f} below min {self.min_confidence_sell}"
        elif consensus.signal == "neutral":
            return False, "Neutral signal"
        elif consensus.signal == "hold":
            return False, consensus.recommendation
        
        return True, f"Execute {consensus.signal} with confidence {consensus.confidence:.2f}"


class AIOrchestrator:
    """Orquestrador principal"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.bull_engine = BullEngine(self.config.get('bull_config', {}))
        self.bear_engine = BearEngine(self.config.get('bear_config', {}))
        self.consensus = ConsensusLayer(self.config.get('consensus_config', {}))
        self.analysis_history: List[ConsensusResult] = []
        self.max_history = 100
        logger.info("AIOrchestrator initialized")
    
    def analyze(self, symbol: str, timeframe: str, market_data: Dict) -> Dict:
        bull_result = self.bull_engine.analyze(symbol, timeframe, market_data)
        bear_result = self.bear_engine.analyze(symbol, timeframe, market_data)
        consensus = self.consensus.calculate_consensus(bull_result, bear_result)
        
        self.analysis_history.append(consensus)
        if len(self.analysis_history) > self.max_history:
            self.analysis_history.pop(0)
        
        should_trade, reason = self.consensus.should_execute_trade(consensus)
        
        logger.info(f"Analysis {symbol}: {consensus.signal} (bull:{bull_result.score:.1f}, bear:{bear_result.score:.1f})")
        
        return {
            "signal": consensus.signal,
            "confidence": consensus.confidence,
            "bull_score": bull_result.score,
            "bear_score": bear_result.score,
            "consensus_score": consensus.consensus_score,
            "bull_confidence": bull_result.confidence,
            "bear_confidence": bear_result.confidence,
            "bull_reasoning": bull_result.reasoning,
            "bear_reasoning": bear_result.reasoning,
            "consensus_reasoning": consensus.reasoning,
            "recommendation": consensus.recommendation,
            "should_trade": should_trade,
            "trade_reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "indicators": {
                "bull": bull_result.indicators,
                "bear": bear_result.indicators
            }
        }


# InstA?ncia global
ai_orchestrator = AIOrchestrator()
