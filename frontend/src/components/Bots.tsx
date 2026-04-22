import React, { useEffect, useState } from 'react';
import {
  Play,
  Square,
  Settings,
  Plus,
  Activity,
  Trash2,
  RefreshCw,
  Copy,
  X,
  Layers,
  Zap,
  BrainCircuit,
  Shield,
} from 'lucide-react';

interface Bot {
  id: number;
  name: string;
  symbol: string;
  timeframe: string;
  active: boolean;
  magic_number: number;
  max_spread?: number;
  max_slippage?: number;
  allowed_symbols?: string[];
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  excluded_days?: number[];
  start_time?: string;
  end_time?: string;
  config?: any;
  signals_config?: any;
  risk_config?: any;
  ai_config?: any;
  spy_config?: any;
  trading_schedule?: any;
}

interface ProgressData {
  type: 'train' | 'sync';
  progress: number;
  status: string;
}

const DAYS_OF_WEEK = [
  { id: 0, label: 'D' },
  { id: 1, label: 'S' },
  { id: 2, label: 'T' },
  { id: 3, label: 'Q' },
  { id: 4, label: 'Q' },
  { id: 5, label: 'S' },
  { id: 6, label: 'S' },
];

const DEFAULT_SIGNALS_CONFIG = {
  ma_cross: { active: false, fast_period: 9, slow_period: 21 },
  rsi: { active: false, period: 14, overbought: 70, oversold: 30 },
  atr: { active: false, period: 14, multiplier: 2.0 },
  price_action: { active: false, patterns: ['pinbar', 'engulfing'] as string[] }
};

const DEFAULT_RISK_CONFIG = {
  lot_size: 1,
  max_positions: 3,
  max_daily_trades: 10,
  max_risk_per_trade: 0.02,
  stop_loss: 200,
  take_profit: 500,
  trailing_stop: { active: false, distance: 20, loss_distance: 10, step: 10 },
  daily_loss_limit: 500.0,
  daily_profit_limit: 1000.0,
};

const DEFAULT_AI_CONFIG = {
  rl_active: true,
  confidence_threshold: 0.7,
  mode: 'hybrid'
};

const DEFAULT_SPY_CONFIG = {
  active: false,
  target_magic: null as number | null,
  follow_signals: true,
  follow_trades: false
};

const buildTradingSchedule = (start_time: string, end_time: string, excluded_days: number[]) => ({
  enabled: true,
  start_time,
  end_time,
  trading_days: DAYS_OF_WEEK.map((day) => day.id).filter((day) => !excluded_days.includes(day))
});

const createFormData = (bot: Bot | null = null) => {
  const botSignals = bot?.signals_config || {};
  const botRisk = bot?.risk_config || {};
  const botAi = bot?.ai_config || {};
  const botSpy = bot?.spy_config || {};

  return {
    name: bot?.name || '',
    symbol: bot?.symbol || 'WINM26',
    timeframe: bot?.timeframe || 'M5',
    magic_number: bot?.magic_number || 0,
    max_spread: bot?.max_spread ?? 5.0,
    max_slippage: bot?.max_slippage ?? 3.0,
    allowed_symbols: (bot?.allowed_symbols && bot.allowed_symbols.length > 0)
      ? bot.allowed_symbols.join(', ')
      : (bot?.symbol || 'WINM26'),
    start_time: bot?.start_time || '09:00',
    end_time: bot?.end_time || '17:50',
    excluded_days: bot?.excluded_days || [],
    signals_config: {
      ma_cross: {
        ...DEFAULT_SIGNALS_CONFIG.ma_cross,
        ...(botSignals.ma_cross || {})
      },
      rsi: {
        ...DEFAULT_SIGNALS_CONFIG.rsi,
        ...(botSignals.rsi || {})
      },
      atr: {
        ...DEFAULT_SIGNALS_CONFIG.atr,
        ...(botSignals.atr || {})
      },
      price_action: {
        ...DEFAULT_SIGNALS_CONFIG.price_action,
        ...(botSignals.price_action || {}),
        patterns: botSignals.price_action?.patterns?.length
          ? botSignals.price_action.patterns
          : DEFAULT_SIGNALS_CONFIG.price_action.patterns
      }
    },
    risk_config: {
      ...DEFAULT_RISK_CONFIG,
      ...botRisk,
      trailing_stop: {
        ...DEFAULT_RISK_CONFIG.trailing_stop,
        ...(botRisk.trailing_stop || {})
      }
    },
    ai_config: {
      ...DEFAULT_AI_CONFIG,
      ...botAi
    },
    spy_config: {
      ...DEFAULT_SPY_CONFIG,
      ...botSpy
    }
  };
};

const parseAllowedSymbols = (value: string) =>
  value
    .split(',')
    .map((symbol) => symbol.trim().toUpperCase())
    .filter(Boolean);

const extractApiError = async (response: Response, fallback: string) => {
  const raw = await response.text();

  if (!raw) {
    return fallback;
  }

  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.detail === 'string') return parsed.detail;
    if (typeof parsed?.message === 'string') return parsed.message;
    return typeof parsed === 'string' ? parsed : raw;
  } catch {
    return raw;
  }
};

const cloneProgress = (progress: ProgressData) => ({
  type: progress.type,
  progress: progress.progress,
  status: progress.status,
});

export const Bots: React.FC = () => {
  const [bots, setBots] = useState<Bot[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedBot, setSelectedBot] = useState<Bot | null>(null);
  const [progressMap, setProgressMap] = useState<Record<string, ProgressData>>({});
  const [formData, setFormData] = useState(createFormData());
  const [saving, setSaving] = useState(false);

  const api_url = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

  const fetchBots = async () => {
    try {
      const response = await fetch(`${api_url}/bots/`);
      const data = await response.json();
      setBots(data);
    } catch (error) {
      console.error('Erro ao buscar bots:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchProgress = async () => {
    try {
      const response = await fetch(`${api_url}/bots/progress`);
      if (response.ok) {
        const data = await response.json();
        setProgressMap((prev) => {
          const next: Record<string, ProgressData> = {};

          for (const [botId, progress] of Object.entries(data || {})) {
            next[botId] = cloneProgress(progress as ProgressData);
          }

          for (const [botId, progress] of Object.entries(prev)) {
            if (!next[botId] && progress.progress < 100) {
              next[botId] = progress;
            }
          }

          return next;
        });
      }
    } catch (error) {
      console.error('Erro ao buscar progresso:', error);
    }
  };

  useEffect(() => {
    fetchBots();
    fetchProgress();

    const interval = setInterval(() => {
      fetchProgress();
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const openCreateModal = () => {
    setSelectedBot(null);
    setSaving(false);
    const existingMagics = bots.map((bot) => bot.magic_number);
    let nextMagic = Math.floor(Math.random() * 900000) + 100000;
    while (existingMagics.includes(nextMagic)) {
      nextMagic = nextMagic < 999999 ? nextMagic + 1 : 100000;
    }
    setFormData({
      ...createFormData(),
      magic_number: nextMagic,
    });
    setShowModal(true);
  };

  const openEditModal = (bot: Bot) => {
    setSelectedBot(bot);
    setSaving(false);
    setFormData(createFormData(bot));
    setShowModal(true);
  };

  const handleSave = async () => {
    if (saving) {
      return;
    }

    setSaving(true);

    const payload = {
      name: formData.name,
      symbol: formData.symbol,
      timeframe: formData.timeframe,
      magic_number: Number(formData.magic_number),
      max_spread: Number(formData.max_spread),
      max_slippage: Number(formData.max_slippage),
      allowed_symbols: parseAllowedSymbols(formData.allowed_symbols),
      trading_schedule: buildTradingSchedule(
        formData.start_time,
        formData.end_time,
        formData.excluded_days
      ),
      excluded_days: formData.excluded_days,
      start_time: formData.start_time,
      end_time: formData.end_time,
      signals_config: formData.signals_config,
      risk_config: formData.risk_config,
      ai_config: formData.ai_config,
      spy_config: formData.spy_config,
      config: {
        last_train: new Date().toISOString(),
      },
    };

    try {
      const method = selectedBot ? 'PUT' : 'POST';
      const url = selectedBot ? `${api_url}/bots/${selectedBot.id}` : `${api_url}/bots/`;

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setShowModal(false);
        await fetchBots();
      } else {
        const errorMessage = await extractApiError(response, 'Nao foi possivel salvar o robo.');
        alert(errorMessage);
        console.error('Falha ao salvar bot:', errorMessage);
      }
    } catch (error) {
      alert('Erro ao salvar as configuracoes do robo. Verifique a conexao com o backend.');
      console.error('Erro ao salvar:', error);
    } finally {
      setSaving(false);
    }
  };

  const deleteBot = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir?')) return;

    try {
      const response = await fetch(`${api_url}/bots/${id}`, { method: 'DELETE' });
      if (response.ok) {
        fetchBots();
        setShowModal(false);
      } else {
        alert('Erro ao excluir robô. Verifique se há ordens abertas.');
      }
    } catch (error) {
      console.error('Erro:', error);
    }
  };

  const cloneBot = async (bot: Bot) => {
    try {
      const response = await fetch(`${api_url}/bots/${bot.id}/clone`, { method: 'POST' });
      if (response.ok) {
        await fetchBots();
      } else {
        console.error('Falha ao clonar bot:', await response.text());
      }
    } catch (error) {
      console.error('Erro ao clonar bot:', error);
    }
  };

  const toggleBot = async (botId: number, currentStatus: boolean) => {
    const action = currentStatus ? 'stop' : 'start';
    try {
      const response = await fetch(`${api_url}/bots/${botId}/${action}`, { method: 'POST' });
      if (response.ok) {
        fetchBots();
      }
    } catch (error) {
      console.error('Erro:', error);
    }
  };

  const setImmediateProgress = (botId: number, type: 'train' | 'sync', status: string) => {
    setProgressMap((prev) => ({
      ...prev,
      [String(botId)]: {
        type,
        progress: 1,
        status,
      },
    }));
  };

  const clearProgress = (botId: number) => {
    setProgressMap((prev) => {
      const next = { ...prev };
      delete next[String(botId)];
      return next;
    });
  };

  const trainBot = async (botId: number) => {
    setImmediateProgress(botId, 'train', 'Iniciando treinamento...');
    try {
      const response = await fetch(`${api_url}/bots/${botId}/train`, { method: 'POST' });
      if (response.ok) {
        fetchProgress();
      } else {
        clearProgress(botId);
        console.error(`[ERROR] Falha ao disparar treino: ${response.status}`);
      }
    } catch (error) {
      clearProgress(botId);
      console.error('Erro no fetch train:', error);
    }
  };

  const syncBot = async (botId: number) => {
    setImmediateProgress(botId, 'sync', 'Iniciando sincronização...');
    try {
      const response = await fetch(`${api_url}/bots/${botId}/sync`, { method: 'POST' });
      if (response.ok) {
        fetchProgress();
      } else {
        clearProgress(botId);
        console.error(`[ERROR] Falha ao disparar sync: ${response.status}`);
      }
    } catch (error) {
      clearProgress(botId);
      console.error('Erro no fetch sync:', error);
    }
  };

  const renderProgress = (botId: number) => {
    const progress = progressMap[String(botId)];
    if (!progress) return null;

    return (
      <div className="mb-4">
        <div className="flex justify-between items-end mb-1">
          <span className="text-[10px] font-black text-brand-secondary animate-pulse uppercase tracking-wider flex items-center gap-1">
            {progress.type === 'train' ? <BrainCircuit size={12} /> : <RefreshCw size={12} className="animate-spin" />}
            {progress.status}
          </span>
          <span className="text-[10px] font-black text-white">{progress.progress}%</span>
        </div>
        <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden border border-white/5">
          <div
            className={`h-full transition-all duration-500 ${progress.type === 'train' ? 'bg-brand-primary' : 'bg-brand-secondary'}`}
            style={{ width: `${progress.progress}%` }}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start gap-4 mb-8">
        <div>
          <h2 className="text-3xl font-black text-white flex items-center gap-3">
            <Activity className="text-brand-primary h-8 w-8" />
            Meus Robôs
          </h2>
          <p className="text-gray-400">Cadastro, parâmetros e execução em tempo real.</p>
        </div>
        <button
          onClick={openCreateModal}
          className="bg-brand-primary hover:bg-brand-primary-dark text-bg-dark font-black px-6 py-3 rounded-2xl flex items-center gap-2 transition-all active:scale-95 shadow-lg shadow-brand-primary/20"
        >
          <Plus size={20} />
          NOVO ROBÔ
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center p-20">
          <RefreshCw className="animate-spin text-brand-primary" size={40} />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {bots.map((bot) => {
            const winRate = bot.total_trades > 0 ? (bot.winning_trades / bot.total_trades) * 100 : 0;
            const progress = progressMap[String(bot.id)];
            const maxSpread = bot.max_spread ?? 0;
            const maxSlippage = bot.max_slippage ?? 0;
            const allowedSymbols = bot.allowed_symbols?.join(', ') || bot.symbol;

            return (
              <div
                key={bot.id}
                className="bg-bg-card border border-border-card rounded-[32px] p-6 hover:border-brand-primary/50 transition-all group relative overflow-hidden flex flex-col h-full"
              >
                <div className={`absolute top-0 right-0 w-32 h-32 -mr-12 -mt-12 rounded-full blur-3xl opacity-10 ${bot.active ? 'bg-brand-primary' : 'bg-red-500'}`} />

                <div className="flex justify-between items-start mb-5">
                  <div>
                    <h3 className="text-2xl font-black text-white mb-2">{bot.name}</h3>
                    <div className="flex flex-wrap gap-2">
                      <span className="bg-gray-800 text-gray-400 text-[10px] font-black px-2 py-1 rounded-lg uppercase tracking-wider">
                        {bot.symbol}
                      </span>
                      <span className="bg-gray-800 text-gray-400 text-[10px] font-black px-2 py-1 rounded-lg uppercase tracking-wider">
                        {bot.timeframe}
                      </span>
                      <span className="bg-brand-primary/5 text-brand-primary/70 text-[10px] font-mono px-2 py-1 rounded-lg">
                        MG: {bot.magic_number}
                      </span>
                    </div>
                  </div>
                  <div className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest ${bot.active ? 'bg-brand-primary/10 text-brand-primary' : 'bg-red-500/10 text-red-500'}`}>
                    {bot.active ? 'LIVE' : 'IDLE'}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-5 text-[10px]">
                  <div className="bg-bg-dark/50 p-3 rounded-2xl border border-border-card/30">
                    <p className="text-gray-500 uppercase font-black mb-1">Spread</p>
                    <p className="text-white font-black">{maxSpread}</p>
                  </div>
                  <div className="bg-bg-dark/50 p-3 rounded-2xl border border-border-card/30">
                    <p className="text-gray-500 uppercase font-black mb-1">Slippage</p>
                    <p className="text-white font-black">{maxSlippage}</p>
                  </div>
                  <div className="bg-bg-dark/50 p-3 rounded-2xl border border-border-card/30">
                    <p className="text-gray-500 uppercase font-black mb-1">Símbolos</p>
                    <p className="text-white font-black truncate" title={allowedSymbols}>{bot.allowed_symbols?.length || 1}</p>
                  </div>
                </div>

                {renderProgress(bot.id)}

                <div className="grid grid-cols-2 gap-4 mb-5">
                  <div className="bg-bg-dark/50 p-3 rounded-2xl border border-border-card/30">
                    <p className="text-gray-500 text-[9px] uppercase font-black mb-1">PnL Realizado</p>
                    <p className={`text-lg font-black ${bot.total_pnl >= 0 ? 'text-brand-primary' : 'text-red-500'}`}>
                      R$ {bot.total_pnl.toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-bg-dark/50 p-3 rounded-2xl border border-border-card/30">
                    <p className="text-gray-500 text-[9px] uppercase font-black mb-1">Taxa de Acerto</p>
                    <p className="text-lg font-black text-white">{winRate.toFixed(1)}%</p>
                  </div>
                </div>

                <div className="bg-bg-dark/40 p-4 rounded-2xl border border-white/5 mb-5">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-black text-gray-500 uppercase flex items-center gap-1">
                      <Zap size={10} className="text-brand-secondary" /> Estado da IA
                    </span>
                    <span className="text-[10px] font-black text-brand-secondary">
                      {bot.ai_config?.mode || 'hybrid'}
                    </span>
                  </div>
                  <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-brand-secondary transition-all duration-700"
                      style={{ width: `${winRate > 60 ? 85 : winRate > 40 ? 60 : 35}%` }}
                    />
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-[9px] text-gray-500 font-medium">Símbolos permitidos:</span>
                    <span className="text-[9px] text-gray-400 font-bold truncate max-w-[180px]" title={allowedSymbols}>
                      {allowedSymbols}
                    </span>
                  </div>
                </div>

                <div className="flex gap-2 mt-auto pt-4 border-t border-white/5">
                  <button
                    disabled={!!progress}
                    onClick={() => toggleBot(bot.id, bot.active)}
                    className={`flex-1 py-4 rounded-2xl flex items-center justify-center gap-2 font-black text-xs transition-all active:scale-95 disabled:opacity-30 ${
                      bot.active ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20' : 'bg-brand-primary/10 text-brand-primary hover:bg-brand-primary/20'
                    }`}
                  >
                    {bot.active ? <Square size={16} /> : <Play size={16} fill="currentColor" />}
                    {bot.active ? 'PARAR' : 'INICIAR'}
                  </button>
                  <button
                    onClick={() => openEditModal(bot)}
                    className="p-4 bg-gray-800 text-gray-400 hover:text-white rounded-2xl transition-all"
                    title="Configurações"
                  >
                    <Settings size={20} />
                  </button>
                  <button
                    onClick={() => cloneBot(bot)}
                    className="p-4 bg-gray-800 text-gray-400 hover:text-brand-primary rounded-2xl transition-all"
                    title="Copiar Robô"
                  >
                    <Copy size={20} />
                  </button>
                  <button
                    onClick={() => deleteBot(bot.id)}
                    className="p-4 bg-gray-800 text-gray-400 hover:bg-red-500/10 hover:text-red-500 rounded-2xl transition-all"
                    title="Excluir Robô"
                  >
                    <Trash2 size={20} />
                  </button>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <button
                    disabled={!!progress}
                    onClick={() => trainBot(bot.id)}
                    className="text-[9px] font-black text-gray-500 hover:text-brand-primary py-2 flex items-center justify-center gap-1 uppercase bg-white/5 rounded-xl transition-all disabled:opacity-20"
                  >
                    <BrainCircuit size={12} />
                    {progress?.type === 'train' ? 'TREINANDO...' : 'TREINAR'}
                  </button>
                  <button
                    disabled={!!progress}
                    onClick={() => syncBot(bot.id)}
                    className="text-[9px] font-black text-gray-500 hover:text-brand-secondary py-2 flex items-center justify-center gap-1 uppercase bg-white/5 rounded-xl transition-all disabled:opacity-20"
                  >
                    <RefreshCw size={12} />
                    {progress?.type === 'sync' ? 'SYNCING...' : 'SYNC'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-bg-card border border-border-card rounded-[40px] w-full max-w-4xl my-auto animate-in zoom-in-95 duration-300">
            <div className="p-8 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
              <div>
                <h3 className="text-3xl font-black text-white">{selectedBot ? 'Ajustes do Robô' : 'Engenharia de Robô'}</h3>
                <p className="text-gray-400 text-sm mt-1">Exponha aqui os parâmetros que afetam a execução real.</p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-700 transition-all"
              >
                <X size={24} />
              </button>
            </div>

            <div className="p-8 max-h-[72vh] overflow-y-auto space-y-8 custom-scrollbar">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                    <Layers size={14} className="text-brand-primary" />
                    Identificação do Bot
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-bold focus:ring-2 ring-brand-primary outline-none transition-all"
                    placeholder="Ex: Sniper Win M5"
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                    <Activity size={14} className="text-brand-primary" />
                    Magic Number
                  </label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={formData.magic_number}
                    onChange={(e) => setFormData({ ...formData, magic_number: parseInt(e.target.value || '0', 10) })}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-brand-primary font-black font-mono focus:ring-2 ring-brand-primary outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-6">
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Símbolo Base</label>
                  <input
                    type="text"
                    value={formData.symbol}
                    onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-black uppercase"
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Timeframe</label>
                  <select
                    value={formData.timeframe}
                    onChange={(e) => setFormData({ ...formData, timeframe: e.target.value })}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-bold outline-none cursor-pointer"
                  >
                    {['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'].map((tf) => (
                      <option key={tf}>{tf}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Símbolos Permitidos</label>
                  <input
                    type="text"
                    value={formData.allowed_symbols}
                    onChange={(e) => setFormData({ ...formData, allowed_symbols: e.target.value })}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-black uppercase"
                    placeholder="WINM26, WIN$"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-6">
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Max Spread</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={formData.max_spread}
                    onChange={(e) => setFormData({ ...formData, max_spread: parseFloat(e.target.value || '0') })}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-bold"
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Max Slippage</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={formData.max_slippage}
                    onChange={(e) => setFormData({ ...formData, max_slippage: parseFloat(e.target.value || '0') })}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-bold"
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Janela</label>
                  <div className="grid grid-cols-3 gap-3">
                    <input
                      type="time"
                      value={formData.start_time}
                      onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                      className="w-full bg-bg-dark border border-border-card rounded-2xl px-4 py-4 text-white font-bold"
                    />
                    <input
                      type="time"
                      value={formData.end_time}
                      onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-4 py-4 text-white font-bold"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                  <Shield size={12} className="text-brand-secondary" />
                  Dias Excluídos
                </label>
                <div className="flex flex-wrap gap-2">
                  {DAYS_OF_WEEK.map((day) => {
                    const selected = formData.excluded_days.includes(day.id);
                    return (
                      <button
                        key={day.id}
                        type="button"
                        onClick={() => {
                          const next = selected
                            ? formData.excluded_days.filter((value) => value !== day.id)
                            : [...formData.excluded_days, day.id];
                          setFormData({ ...formData, excluded_days: next });
                        }}
                        className={`w-11 h-11 rounded-xl font-black text-sm border transition-all ${
                          selected
                            ? 'bg-red-500/15 text-red-400 border-red-500/40'
                            : 'bg-bg-dark text-gray-400 border-white/5 hover:border-brand-primary/40'
                        }`}
                        title={day.label}
                      >
                        {day.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="bg-white/5 p-8 rounded-[32px] border border-white/5 space-y-6">
                <h4 className="text-white font-black text-xs uppercase tracking-widest flex items-center gap-2">
                  <Zap size={16} className="text-yellow-400" /> Arsenal de Sinais
                </h4>

                <div className="grid grid-cols-2 gap-4">
                  <div className={`p-4 rounded-2xl border transition-all ${formData.signals_config.ma_cross.active ? 'bg-brand-primary/10 border-brand-primary/30' : 'bg-bg-dark border-white/5'}`}>
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-[10px] font-black text-white uppercase">Crossover Médias</span>
                      <input
                        type="checkbox"
                        checked={formData.signals_config.ma_cross.active}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            ma_cross: { ...formData.signals_config.ma_cross, active: e.target.checked }
                          }
                        })}
                        className="w-5 h-5 accent-brand-primary cursor-pointer"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        className="bg-black/20 text-[10px] p-2 rounded-lg text-white"
                        value={formData.signals_config.ma_cross.fast_period}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            ma_cross: { ...formData.signals_config.ma_cross, fast_period: parseInt(e.target.value || '0', 10) }
                          }
                        })}
                      />
                      <input
                        type="number"
                        className="bg-black/20 text-[10px] p-2 rounded-lg text-white"
                        value={formData.signals_config.ma_cross.slow_period}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            ma_cross: { ...formData.signals_config.ma_cross, slow_period: parseInt(e.target.value || '0', 10) }
                          }
                        })}
                      />
                    </div>
                  </div>

                  <div className={`p-4 rounded-2xl border transition-all ${formData.signals_config.rsi.active ? 'bg-blue-500/10 border-blue-500/30' : 'bg-bg-dark border-white/5'}`}>
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-[10px] font-black text-white uppercase">RSI</span>
                      <input
                        type="checkbox"
                        checked={formData.signals_config.rsi.active}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            rsi: { ...formData.signals_config.rsi, active: e.target.checked }
                          }
                        })}
                        className="w-5 h-5 accent-blue-500 cursor-pointer"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-1">
                      <input
                        type="number"
                        className="bg-black/20 text-[10px] p-2 rounded-lg text-white"
                        value={formData.signals_config.rsi.period}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            rsi: { ...formData.signals_config.rsi, period: parseInt(e.target.value || '0', 10) }
                          }
                        })}
                      />
                      <input
                        type="number"
                        className="bg-black/20 text-[10px] p-2 rounded-lg text-white"
                        value={formData.signals_config.rsi.overbought}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            rsi: { ...formData.signals_config.rsi, overbought: parseInt(e.target.value || '0', 10) }
                          }
                        })}
                      />
                      <input
                        type="number"
                        className="bg-black/20 text-[10px] p-2 rounded-lg text-white"
                        value={formData.signals_config.rsi.oversold}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            rsi: { ...formData.signals_config.rsi, oversold: parseInt(e.target.value || '0', 10) }
                          }
                        })}
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className={`p-4 rounded-2xl border transition-all ${formData.signals_config.atr.active ? 'bg-amber-500/10 border-amber-500/30' : 'bg-bg-dark border-white/5'}`}>
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-[10px] font-black text-white uppercase">ATR / Breakout</span>
                      <input
                        type="checkbox"
                        checked={formData.signals_config.atr.active}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            atr: { ...formData.signals_config.atr, active: e.target.checked }
                          }
                        })}
                        className="w-5 h-5 accent-amber-500 cursor-pointer"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="number"
                        className="bg-black/20 text-[10px] p-2 rounded-lg text-white"
                        value={formData.signals_config.atr.period}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            atr: { ...formData.signals_config.atr, period: parseInt(e.target.value || '0', 10) }
                          }
                        })}
                      />
                      <input
                        type="number"
                        step="0.1"
                        className="bg-black/20 text-[10px] p-2 rounded-lg text-white"
                        value={formData.signals_config.atr.multiplier}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            atr: { ...formData.signals_config.atr, multiplier: parseFloat(e.target.value || '0') }
                          }
                        })}
                      />
                    </div>
                  </div>

                  <div className={`p-4 rounded-2xl border transition-all ${formData.signals_config.price_action.active ? 'bg-purple-500/10 border-purple-500/30' : 'bg-bg-dark border-white/5'}`}>
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-[10px] font-black text-white uppercase">Price Action</span>
                      <input
                        type="checkbox"
                        checked={formData.signals_config.price_action.active}
                        onChange={(e) => setFormData({
                          ...formData,
                          signals_config: {
                            ...formData.signals_config,
                            price_action: { ...formData.signals_config.price_action, active: e.target.checked }
                          }
                        })}
                        className="w-5 h-5 accent-purple-500 cursor-pointer"
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {['pinbar', 'engulfing'].map((pattern) => {
                        const patterns = formData.signals_config.price_action.patterns || [];
                        const checked = patterns.includes(pattern);
                        return (
                          <label
                            key={pattern}
                            className={`px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest cursor-pointer border ${checked ? 'bg-white text-bg-dark border-white' : 'bg-black/20 text-gray-400 border-white/5'}`}
                          >
                            <input
                              type="checkbox"
                              className="hidden"
                              checked={checked}
                              onChange={(e) => {
                                const current = new Set(patterns);
                                if (e.target.checked) current.add(pattern);
                                else current.delete(pattern);
                                setFormData({
                                  ...formData,
                                  signals_config: {
                                    ...formData.signals_config,
                                    price_action: {
                                      ...formData.signals_config.price_action,
                                      patterns: Array.from(current)
                                    }
                                  }
                                });
                              }}
                            />
                            {pattern}
                          </label>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white/5 p-8 rounded-[32px] border border-white/5 space-y-6">
                <h4 className="text-white font-black text-xs uppercase tracking-widest flex items-center gap-2">
                  <Shield size={16} className="text-red-400" /> Blindagem de Risco
                </h4>

                <div className="grid grid-cols-2 xl:grid-cols-4 gap-6">
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Lote Base</label>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold"
                      value={formData.risk_config.lot_size}
                      onChange={(e) => setFormData({
                        ...formData,
                        risk_config: { ...formData.risk_config, lot_size: parseFloat(e.target.value || '0') }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Posições Máx.</label>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold"
                      value={formData.risk_config.max_positions}
                      onChange={(e) => setFormData({
                        ...formData,
                        risk_config: { ...formData.risk_config, max_positions: parseInt(e.target.value || '0', 10) }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Trades/Dia Máx.</label>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold"
                      value={formData.risk_config.max_daily_trades}
                      onChange={(e) => setFormData({
                        ...formData,
                        risk_config: { ...formData.risk_config, max_daily_trades: parseInt(e.target.value || '0', 10) }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Risco Máx/Trade (%)</label>
                    <input
                      type="number"
                      min="0.1"
                      step="0.1"
                      className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold"
                      value={(formData.risk_config.max_risk_per_trade * 100).toFixed(2)}
                      onChange={(e) => setFormData({
                        ...formData,
                        risk_config: { ...formData.risk_config, max_risk_per_trade: parseFloat(e.target.value || '0') / 100 }
                      })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Stop Loss (Pts)</label>
                    <input
                      type="number"
                      className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-red-500 font-black"
                      value={formData.risk_config.stop_loss}
                      onChange={(e) => setFormData({
                        ...formData,
                        risk_config: { ...formData.risk_config, stop_loss: parseFloat(e.target.value || '0') }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Take Profit (Pts)</label>
                    <input
                      type="number"
                      className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-brand-primary font-black"
                      value={formData.risk_config.take_profit}
                      onChange={(e) => setFormData({
                        ...formData,
                        risk_config: { ...formData.risk_config, take_profit: parseFloat(e.target.value || '0') }
                      })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6 p-4 bg-black/20 rounded-2xl">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black text-gray-400 uppercase">Meta Diária (R$)</span>
                    <input
                      type="number"
                      className="bg-transparent text-right text-brand-primary font-black outline-none"
                      value={formData.risk_config.daily_profit_limit}
                      onChange={(e) => setFormData({
                        ...formData,
                        risk_config: { ...formData.risk_config, daily_profit_limit: parseFloat(e.target.value || '0') }
                      })}
                    />
                  </div>
                  <div className="flex items-center justify-between border-l border-white/10 pl-6">
                    <span className="text-[10px] font-black text-gray-400 uppercase">Stop Diário (R$)</span>
                    <input
                      type="number"
                      className="bg-transparent text-right text-red-500 font-black outline-none"
                      value={formData.risk_config.daily_loss_limit}
                      onChange={(e) => setFormData({
                        ...formData,
                        risk_config: { ...formData.risk_config, daily_loss_limit: parseFloat(e.target.value || '0') }
                      })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center justify-between bg-bg-dark/50 p-4 rounded-2xl border border-white/5">
                    <div>
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${formData.risk_config.trailing_stop.active ? 'bg-brand-secondary animate-pulse' : 'bg-gray-700'}`} />
                        <span className="text-xs font-black text-white">STOP DINAMICO</span>
                      </div>
                      <p className="text-[10px] text-gray-500 mt-1">Protege lucro com 20 pts e reduz perda com 10 pts.</p>
                    </div>
                    <button
                      onClick={() => setFormData({
                        ...formData,
                        risk_config: {
                          ...formData.risk_config,
                          trailing_stop: {
                            ...formData.risk_config.trailing_stop,
                            active: !formData.risk_config.trailing_stop.active
                          }
                        }
                      })}
                      className={`px-4 py-2 rounded-xl text-[10px] font-black transition-all ${formData.risk_config.trailing_stop.active ? 'bg-brand-secondary text-bg-dark' : 'bg-gray-800 text-gray-400'}`}
                    >
                      {formData.risk_config.trailing_stop.active ? 'HABILITADO' : 'DESABILITADO'}
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="space-y-2">
                      <label className="text-[9px] font-black text-gray-500 uppercase">Proteção de lucro (pts)</label>
                      <input
                        type="number"
                        className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold"
                        value={formData.risk_config.trailing_stop.distance}
                        onChange={(e) => setFormData({
                          ...formData,
                          risk_config: {
                            ...formData.risk_config,
                            trailing_stop: { ...formData.risk_config.trailing_stop, distance: parseFloat(e.target.value || '0') }
                          }
                        })}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[9px] font-black text-gray-500 uppercase">Proteção de perda (pts)</label>
                      <input
                        type="number"
                        className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold"
                        value={formData.risk_config.trailing_stop.loss_distance ?? 10}
                        onChange={(e) => setFormData({
                          ...formData,
                          risk_config: {
                            ...formData.risk_config,
                            trailing_stop: { ...formData.risk_config.trailing_stop, loss_distance: parseFloat(e.target.value || '0') }
                          }
                        })}
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[9px] font-black text-gray-500 uppercase">Passo do ajuste</label>
                      <input
                        type="number"
                        className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold"
                        value={formData.risk_config.trailing_stop.step}
                        onChange={(e) => setFormData({
                          ...formData,
                          risk_config: {
                            ...formData.risk_config,
                            trailing_stop: { ...formData.risk_config.trailing_stop, step: parseFloat(e.target.value || '0') }
                          }
                        })}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-8">
                <div className="bg-gradient-to-br from-brand-primary/10 to-transparent p-6 rounded-[32px] border border-brand-primary/20">
                  <h4 className="text-[10px] font-black text-brand-primary uppercase tracking-widest mb-4 flex items-center gap-2">
                    <BrainCircuit size={16} /> Inteligência por Reforço
                  </h4>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-400">Status da IA</span>
                      <input
                        type="checkbox"
                        checked={formData.ai_config.rl_active}
                        onChange={(e) => setFormData({
                          ...formData,
                          ai_config: { ...formData.ai_config, rl_active: e.target.checked }
                        })}
                        className="w-5 h-5 accent-brand-primary"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[9px] font-black text-gray-500 uppercase">Modo</label>
                      <select
                        value={formData.ai_config.mode}
                        onChange={(e) => setFormData({
                          ...formData,
                          ai_config: { ...formData.ai_config, mode: e.target.value }
                        })}
                        className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold"
                      >
                        <option value="hybrid">Hybrid</option>
                        <option value="pure_signals">Pure Signals</option>
                        <option value="pure_ia">Pure IA</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-[9px] text-gray-500 font-black">
                        <span>CONFIANÇA MÍNIMA</span>
                        <span>{(formData.ai_config.confidence_threshold * 100).toFixed(0)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.5"
                        max="0.95"
                        step="0.05"
                        value={formData.ai_config.confidence_threshold}
                        onChange={(e) => setFormData({
                          ...formData,
                          ai_config: { ...formData.ai_config, confidence_threshold: parseFloat(e.target.value) }
                        })}
                        className="w-full h-1 bg-gray-800 accent-brand-primary rounded-full appearance-none"
                      />
                    </div>
                  </div>
                </div>

                <div className={`p-6 rounded-[32px] border transition-all ${formData.spy_config.active ? 'bg-purple-500/10 border-purple-500/30' : 'bg-white/5 border-white/5 grayscale opacity-40'}`}>
                  <h4 className="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                    <Activity size={16} /> Protocolo Espião
                  </h4>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-400">Ativar Espionagem</span>
                      <input
                        type="checkbox"
                        checked={formData.spy_config.active}
                        onChange={(e) => setFormData({
                          ...formData,
                          spy_config: { ...formData.spy_config, active: e.target.checked }
                        })}
                        className="w-5 h-5 accent-purple-500"
                      />
                    </div>
                    <input
                      type="number"
                      placeholder="Magic Number Alvo"
                      disabled={!formData.spy_config.active}
                      className="w-full bg-black/20 border border-white/5 p-3 rounded-xl text-white text-xs font-mono"
                      value={formData.spy_config.target_magic || ''}
                      onChange={(e) => setFormData({
                        ...formData,
                        spy_config: { ...formData.spy_config, target_magic: e.target.value ? parseInt(e.target.value, 10) : null }
                      })}
                    />
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={formData.spy_config.follow_signals}
                        onChange={(e) => setFormData({
                          ...formData,
                          spy_config: { ...formData.spy_config, follow_signals: e.target.checked }
                        })}
                        className="w-4 h-4 accent-purple-500"
                      />
                      <span className="text-xs text-gray-300">Seguir sinais do alvo</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={formData.spy_config.follow_trades}
                        onChange={(e) => setFormData({
                          ...formData,
                          spy_config: { ...formData.spy_config, follow_trades: e.target.checked }
                        })}
                        className="w-4 h-4 accent-purple-500"
                      />
                      <span className="text-xs text-gray-300">Seguir operações do alvo</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-8 border-t border-white/5 flex gap-4 bg-white/[0.01]">
              <button
                type="button"
                className="flex-1 bg-brand-primary text-bg-dark font-black py-5 rounded-2xl hover:bg-brand-primary-dark transition-all transform hover:-translate-y-1 shadow-xl shadow-brand-primary/20 disabled:opacity-50 disabled:translate-y-0"
                onClick={handleSave}
                disabled={!formData.name || saving}
              >
                {saving ? 'SALVANDO...' : selectedBot ? 'SALVAR ALTERAÇÕES' : 'GERAR ROBÔ AGORA'}
              </button>
              {selectedBot && (
                <button
                  onClick={() => deleteBot(selectedBot.id)}
                  className="w-16 flex items-center justify-center bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white rounded-2xl transition-all"
                  title="Excluir Robô"
                >
                  <Trash2 size={24} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
