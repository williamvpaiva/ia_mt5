"""
Backtester Engine
CorreA?A?o: Removidos scores fixos, implementada lA?gica real de backtesting
Prioridade: MA?DIA
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .mt5_client import mt5_client
from .ai_orchestrator import AIOrchestrator  # Novo serviA?o

logger = logging.getLogger("Backtester")


@dataclass
class BacktestTrade:
    """Representa um trade no backtest"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    direction: str  # buy, sell
    volume: float
    pnl: float
    commission: float
    swap: float
    sl: Optional[float]
    tp: Optional[float]
    close_reason: str  # tp, sl, signal, manual


@dataclass
class BacktestMetrics:
    """MA?tricas calculadas do backtest"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_trade: float
    avg_win: float
    avg_loss: float
    total_pnl: float
    gross_profit: float
    gross_loss: float
    return_pct: float
    annualized_return: float
    avg_trade_duration: timedelta
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    expectancy: float  # Expected value per trade


class TechnicalIndicators:
    """CA?lculo de indicadores tA?cnicos para backtest"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcular RSI usando pandas"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_sma(prices: pd.Series, period: int = 20) -> pd.Series:
        """MA?dia mA?vel simples"""
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int = 20) -> pd.Series:
        """MA?dia mA?vel exponencial"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD: linha, sinal, histograma"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bandas de Bollinger: mA?dia, superior, inferior"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return sma, upper, lower
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Oscilador EstocA?stico: %K, %D"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d = k.rolling(window=d_period).mean()
        return k, d


class BacktestEngine:
    """
    Engine de backtesting com lA?gica real
    CorreA?A?o: ImplementaA?A?o completa sem scores fixos
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_balance: float = 10000.0,
        commission_per_trade: float = 2.5,
        spread: float = 2.0,
        use_real_ai: bool = False  # Se True, usa IA real; se False, simula
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = start_date or (datetime.now() - timedelta(days=30))
        self.end_date = end_date or datetime.now()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.commission_per_trade = commission_per_trade
        self.spread = spread
        self.use_real_ai = use_real_ai
        
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[float] = [initial_balance]
        self.positions: List[Dict] = []
        
        # MA?tricas
        self.metrics: Optional[BacktestMetrics] = None
        
        # Inicializar orquestrador de IA
        self.ai_orchestrator = AIOrchestrator() if use_real_ai else None
        
        logger.info(f"BacktestEngine inicializado: {symbol} {timeframe}")
    
    async def fetch_historical_data(self) -> Optional[pd.DataFrame]:
        """Buscar dados histA?ricos do MT5"""
        try:
            rates = await mt5_client.get_rates(
                self.symbol,
                self.timeframe,
                count=2000  # Suficiente para indicadores
            )
            
            if not rates:
                logger.error("Sem dados histA?ricos")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Filtrar por data
            df = df[(df['time'] >= self.start_date) & (df['time'] <= self.end_date)]
            
            logger.info(f"Dados histA?ricos: {len(df)} candles")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular todos os indicadores tA?cnicos"""
        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df['close'])
        
        # MA?dias mA?veis
        df['sma_20'] = TechnicalIndicators.calculate_sma(df['close'], 20)
        df['sma_50'] = TechnicalIndicators.calculate_sma(df['close'], 50)
        df['ema_12'] = TechnicalIndicators.calculate_ema(df['close'], 12)
        df['ema_26'] = TechnicalIndicators.calculate_ema(df['close'], 26)
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = TechnicalIndicators.calculate_macd(df['close'])
        
        # Bollinger Bands
        df['bb_middle'], df['bb_upper'], df['bb_lower'] = TechnicalIndicators.calculate_bollinger_bands(df['close'])
        
        # ATR
        df['atr'] = TechnicalIndicators.calculate_atr(df['high'], df['low'], df['close'])
        
        # EstocA?stico
        df['stoch_k'], df['stoch_d'] = TechnicalIndicators.calculate_stochastic(df['high'], df['low'], df['close'])
        
        return df
    
    async def analyze_signal(self, df_window: pd.DataFrame) -> Dict:
        """
        Analisar sinal de trading usando IA e indicadores
        CorreA?A?o: IntegraA?A?o com orquestrador de IA
        """
        current = df_window.iloc[-1]
        
        # Preparar dados para anA?lise
        market_data = {
            'close': current['close'],
            'high': current['high'],
            'low': current['low'],
            'open': current['open'],
            'volume': current.get('tick_volume', 0),
            'rsi': current.get('rsi', 50),
            'sma_20': current.get('sma_20', current['close']),
            'sma_50': current.get('sma_50', current['close']),
            'macd': current.get('macd', 0),
            'macd_signal': current.get('macd_signal', 0),
            'bb_upper': current.get('bb_upper', current['close'] * 1.01),
            'bb_lower': current.get('bb_lower', current['close'] * 0.99),
            'atr': current.get('atr', current['close'] * 0.01),
        }
        
        if self.use_real_ai and self.ai_orchestrator:
            # Usar orquestrador de IA real
            signal_result = await self.ai_orchestrator.analyze(
                symbol=self.symbol,
                timeframe=self.timeframe,
                market_data=market_data
            )
            return signal_result
        else:
            # SimulaA?A?o baseada em indicadores
            return self._simulate_signal(market_data)
    
    def _simulate_signal(self, market_data: Dict) -> Dict:
        """Simular sinal baseado em regras de indicadores"""
        signal = "neutral"
        confidence = 0.5
        
        # RSI
        rsi = market_data['rsi']
        if rsi < 30:
            signal = "buy"
            confidence = 0.7
        elif rsi > 70:
            signal = "sell"
            confidence = 0.7
        
        # MACD
        macd = market_data['macd']
        macd_signal = market_data['macd_signal']
        if macd > macd_signal and signal == "buy":
            confidence += 0.1
        elif macd < macd_signal and signal == "sell":
            confidence += 0.1
        
        # PreA?o vs Bandas de Bollinger
        close = market_data['close']
        bb_lower = market_data['bb_lower']
        bb_upper = market_data['bb_upper']
        
        if close < bb_lower and signal == "buy":
            confidence += 0.1
        elif close > bb_upper and signal == "sell":
            confidence += 0.1
        
        # Limitar confianA?a
        confidence = min(confidence, 0.95)
        
        return {
            "signal": signal,
            "confidence": confidence,
            "bull_score": 50 + (confidence * 50) if signal == "buy" else 50 - (confidence * 50),
            "bear_score": 50 + (confidence * 50) if signal == "sell" else 50 - (confidence * 50),
            "reason": "technical_indicators"
        }
    
    async def run_backtest(self, bot_config: dict) -> Dict:
        """
        Executar backtest completo
        CorreA?A?o: LA?gica real sem scores fixos
        """
        logger.info(f"Iniciando backtest: {self.symbol} {self.timeframe}")
        
        # 1. Buscar dados
        df = await self.fetch_historical_data()
        if df is None or len(df) < 100:
            return {"error": "Dados insuficientes para backtest"}
        
        # 2. Calcular indicadores
        df = self.calculate_indicators(df)
        
        # ConfiguraA?A?es do bot
        sl_pct = bot_config.get('stop_loss_pct', 2.0)
        tp_pct = bot_config.get('take_profit_pct', 4.0)
        trailing_stop = bot_config.get('trailing_stop', False)
        trailing_distance = bot_config.get('trailing_stop_distance', 1.0)
        volume = bot_config.get('volume', 1.0)
        min_confidence = bot_config.get('min_confidence', 0.6)
        
        # 3. Loop de backtest
        lookback = 50  # PerA?odo necessA?rio para indicadores
        position = None
        entry_price = 0
        sl_price = 0
        tp_price = 0
        trailing_sl = 0
        entry_time = None
        
        for i in range(lookback, len(df)):
            window = df.iloc[:i+1]
            current = window.iloc[-1]
            current_price = current['close']
            current_time = current['time']
            
            # --- VERIFICAA?A?O DE AGENDAMENTO ---
            # Converter horA?rios
            try:
                start_h, start_m = map(int, bot_config.get('start_time', '09:00').split(':'))
                end_h, end_m = map(int, bot_config.get('end_time', '17:50').split(':'))
                
                candle_time = current_time.time()
                is_within_hours = (candle_time >= datetime.strptime(f"{start_h}:{start_m}", "%H:%M").time()) and \
                                 (candle_time <= datetime.strptime(f"{end_h}:{end_m}", "%H:%M").time())
                
                # Dia da semana (Python 0=Monday, 6=Sunday)
                # Frontend D=0, S=1, T=2... S=6.
                # ConversA?o: (current_time.weekday() + 1) % 7
                current_day_js = (current_time.weekday() + 1) % 7
                is_excluded_day = current_day_js in bot_config.get('excluded_days', [])
            except:
                is_within_hours = True
                is_excluded_day = False

            can_open_new = is_within_hours and not is_excluded_day
            # ----------------------------------
            
            # Verificar stops se hA? posiA?A?o aberta
            if position:
                # Stop Loss
                hit_sl = (position == "buy" and current_price <= sl_price) or \
                        (position == "sell" and current_price >= sl_price)
                
                # Take Profit
                hit_tp = (position == "buy" and current_price >= tp_price) or \
                        (position == "sell" and current_price <= tp_price)
                
                # Trailing Stop
                if trailing_stop and not hit_sl and not hit_tp:
                    if position == "buy":
                        new_sl = current_price * (1 - trailing_distance / 100)
                        if new_sl > trailing_sl:
                            trailing_sl = new_sl
                            sl_price = trailing_sl
                    else:
                        new_sl = current_price * (1 + trailing_distance / 100)
                        if new_sl < trailing_sl or trailing_sl == 0:
                            trailing_sl = new_sl
                            sl_price = trailing_sl
                
                # Fechar posiA?A?o
                if hit_sl or hit_tp:
                    close_reason = "sl" if hit_sl else "tp"
                    await self._close_position(
                        position, entry_price, current_price, entry_time,
                        current_time, volume, close_reason
                    )
                    position = None
                    entry_price = 0
                    trailing_sl = 0
                    continue
            
            # Analisar sinal
            signal_result = await self.analyze_signal(window)
            signal = signal_result['signal']
            confidence = signal_result['confidence']
            
            # Abrir nova posiA?A?o
            if position is None and can_open_new and confidence >= min_confidence:
                if signal in ["buy", "sell"]:
                    position = signal
                    entry_price = current_price
                    entry_time = current_time
                    
                    # Calcular SL e TP
                    if position == "buy":
                        sl_price = entry_price * (1 - sl_pct / 100)
                        tp_price = entry_price * (1 + tp_pct / 100)
                        trailing_sl = sl_price if trailing_stop else 0
                    else:
                        sl_price = entry_price * (1 + sl_pct / 100)
                        tp_price = entry_price * (1 - tp_pct / 100)
                        trailing_sl = sl_price if trailing_stop else 0
        
        # Fechar posiA?A?o aberta no final
        if position:
            final_price = df['close'].iloc[-1]
            final_time = df['time'].iloc[-1]
            await self._close_position(
                position, entry_price, final_price, entry_time,
                final_time, volume, "end_of_data"
            )
        
        # 4. Calcular mA?tricas
        self.metrics = self._calculate_metrics()
        
        # 5. Retornar resultados
        return {
            "success": True,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "period": f"{df['time'].min()} to {df['time'].max()}",
            "initial_balance": self.initial_balance,
            "final_balance": self.balance,
            "total_pnl": self.balance - self.initial_balance,
            "return_pct": ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            "metrics": self._metrics_to_dict(self.metrics),
            "trades_count": len(self.trades),
            "equity_curve": self.equity_curve,
            "trades": [self._trade_to_dict(t) for t in self.trades]
        }
    
    async def _close_position(
        self, position: str, entry: float, exit_price: float,
        entry_time: datetime, exit_time: datetime, volume: float,
        reason: str
    ):
        """Fechar posiA?A?o e registrar trade"""
        # Calcular PnL bruto
        if position == "buy":
            pnl = (exit_price - entry) * volume
        else:
            pnl = (entry - exit_price) * volume
        
        # Aplicar comissA?o
        commission = self.commission_per_trade * 2  # Entrada + saA?da
        net_pnl = pnl - commission
        
        # Criar trade
        trade = BacktestTrade(
            entry_time=entry_time,
            exit_time=exit_time,
            entry_price=entry,
            exit_price=exit_price,
            direction=position,
            volume=volume,
            pnl=net_pnl,
            commission=commission,
            swap=0.0,
            sl=None,
            tp=None,
            close_reason=reason
        )
        
        self.trades.append(trade)
        self.balance += net_pnl
        self.equity_curve.append(self.balance)
        
        logger.debug(f"Trade fechado: {position} {entry} -> {exit_price}, PnL: {net_pnl}")
    
    def _calculate_metrics(self) -> BacktestMetrics:
        """Calcular todas as mA?tricas do backtest"""
        if not self.trades:
            return BacktestMetrics(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, profit_factor=0, sharpe_ratio=0,
                max_drawdown=0, max_drawdown_pct=0, avg_trade=0,
                avg_win=0, avg_loss=0, total_pnl=0, gross_profit=0,
                gross_loss=0, return_pct=0, annualized_return=0,
                avg_trade_duration=timedelta(0), largest_win=0,
                largest_loss=0, consecutive_wins=0, consecutive_losses=0,
                expectancy=0
            )
        
        total_trades = len(self.trades)
        
        # Trades vencedores/perdedores
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # PnL
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        total_pnl = gross_profit - gross_loss
        
        # Profit Factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit
        
        # Averages
        avg_trade = total_pnl / total_trades if total_trades > 0 else 0
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        
        # Max Drawdown
        max_drawdown = 0
        max_drawdown_pct = 0
        peak = self.initial_balance
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        # Sharpe Ratio (simplificado)
        pnl_values = [t.pnl for t in self.trades]
        if len(pnl_values) > 1:
            avg_return = np.mean(pnl_values)
            std_return = np.std(pnl_values)
            # Assumindo taxa livre de risco = 0
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Retorno anualizado (simplificado)
        if len(self.equity_curve) > 1:
            total_return = ((self.balance - self.initial_balance) / self.initial_balance)
            # Assumindo perA?odo de 1 ano para simplificar
            annualized_return = total_return * 100
        else:
            annualized_return = 0
        
        # DuraA?A?o mA?dia
        durations = [(t.exit_time - t.entry_time) for t in self.trades if t.exit_time and t.entry_time]
        avg_duration = sum(durations, timedelta(0)) / len(durations) if durations else timedelta(0)
        
        # Maior ganho/perda
        largest_win = max((t.pnl for t in winning_trades), default=0)
        largest_loss = min((t.pnl for t in losing_trades), default=0)
        
        # SequAancias
        consecutive_wins = 0
        consecutive_losses = 0
        current_streak = 0
        current_type = None
        for trade in self.trades:
            if trade.pnl > 0:
                if current_type == "win":
                    current_streak += 1
                else:
                    current_type = "win"
                    current_streak = 1
                consecutive_wins = max(consecutive_wins, current_streak)
            else:
                if current_type == "loss":
                    current_streak += 1
                else:
                    current_type = "loss"
                    current_streak = 1
                consecutive_losses = max(consecutive_losses, current_streak)
        
        # Expectancy
        win_prob = len(winning_trades) / total_trades if total_trades > 0 else 0
        loss_prob = len(losing_trades) / total_trades if total_trades > 0 else 0
        expectancy = (win_prob * avg_win) - (loss_prob * abs(avg_loss)) if total_trades > 0 else 0
        
        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            max_drawdown=round(max_drawdown, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            avg_trade=round(avg_trade, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            total_pnl=round(total_pnl, 2),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            return_pct=round(total_pnl / self.initial_balance * 100, 2),
            annualized_return=round(annualized_return, 2),
            avg_trade_duration=avg_duration,
            largest_win=round(largest_win, 2),
            largest_loss=round(largest_loss, 2),
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            expectancy=round(expectancy, 2)
        )
    
    def _metrics_to_dict(self, metrics: BacktestMetrics) -> dict:
        """Converter mA?tricas para dicionA?rio"""
        return {
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown": metrics.max_drawdown,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "avg_trade": metrics.avg_trade,
            "avg_win": metrics.avg_win,
            "avg_loss": metrics.avg_loss,
            "total_pnl": metrics.total_pnl,
            "gross_profit": metrics.gross_profit,
            "gross_loss": metrics.gross_loss,
            "return_pct": metrics.return_pct,
            "annualized_return": metrics.annualized_return,
            "avg_trade_duration_minutes": metrics.avg_trade_duration.total_seconds() / 60,
            "largest_win": metrics.largest_win,
            "largest_loss": metrics.largest_loss,
            "consecutive_wins": metrics.consecutive_wins,
            "consecutive_losses": metrics.consecutive_losses,
            "expectancy": metrics.expectancy
        }
    
    def _trade_to_dict(self, trade: BacktestTrade) -> dict:
        """Converter trade para dicionA?rio"""
        return {
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "direction": trade.direction,
            "volume": trade.volume,
            "pnl": trade.pnl,
            "commission": trade.commission,
            "close_reason": trade.close_reason
        }


# InstA?ncia global
backtest_engine = BacktestEngine(symbol="WIN", timeframe="M5")
