import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Square, 
  Settings, 
  Plus, 
  Activity, 
  Trash2, 
  RefreshCw, 
  Edit2,
  X,
  Layers,
  Zap,
  BrainCircuit,
  ChevronRight,
  Cpu,
  Database,
  Shield,
  TrendingUp,
  AlertCircle
} from 'lucide-react';

interface Bot {
  id: number;
  name: string;
  symbol: string;
  timeframe: string;
  active: boolean;
  magic_number: number;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  excluded_days?: number[];
  start_time?: string;
  end_time?: string;
  config?: any;
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

export const Bots: React.FC = () => {
  const [bots, setBots] = useState<Bot[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedBot, setSelectedBot] = useState<Bot | null>(null);
  const [progressMap, setProgressMap] = useState<Record<string, ProgressData>>({});
  
  // Estado do formulário
  const [formData, setFormData] = useState({
    name: '',
    symbol: 'WIN',
    timeframe: 'M5',
    magic_number: 0,
    start_time: '09:00',
    end_time: '17:50',
    excluded_days: [] as number[],
    
    // Módulos Independentes
    signals_config: {
      ma_cross: { active: false, fast_period: 9, slow_period: 21 },
      rsi: { active: false, period: 14, overbought: 70, oversold: 30 },
      atr: { active: false, period: 14, multiplier: 2.0 },
      price_action: { active: false }
    },
    risk_config: {
      lot_size: 1,
      stop_loss: 200,
      take_profit: 500,
      trailing_stop: { active: false, distance: 150, step: 10 },
      daily_loss_limit: 500.0,
      daily_profit_limit: 1000.0,
    },
    ai_config: {
      rl_active: true,
      confidence_threshold: 0.7,
      mode: 'hybrid' // hybrid, pure_ia, pure_signals
    },
    spy_config: {
      active: false,
      target_magic: null as number | null,
      follow_signals: true
    }
  });

  const api_url = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

  const fetchBots = async () => {
    try {
      const response = await fetch(`${api_url}/bots/`);
      const data = await response.json();
      setBots(data);
    } catch (error) {
      console.error("Erro ao buscar bots:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchProgress = async () => {
    try {
      const response = await fetch(`${api_url}/bots/progress`);
      if (response.ok) {
        const data = await response.json();
        // console.log("[DEBUG] Progress data received:", data);
        setProgressMap(data);
      }
    } catch (error) {
      console.error("Erro ao buscar progresso:", error);
    }
  };

  useEffect(() => {
    fetchBots();
    
    // Polling de progresso a cada 1s
    const interval = setInterval(() => {
      fetchProgress();
    }, 1000);
    
    return () => clearInterval(interval);
  }, []);

  const handleOpenModal = (bot: any | null = null) => {
    if (bot) {
      setSelectedBot(bot);
      setFormData({
        name: bot.name,
        symbol: bot.symbol,
        timeframe: bot.timeframe,
        magic_number: bot.magic_number,
        start_time: bot.start_time || '09:00',
        end_time: bot.end_time || '17:50',
        excluded_days: bot.excluded_days || [],
        
        signals_config: bot.signals_config || {
          ma_cross: { active: false, fast_period: 9, slow_period: 21 },
          rsi: { active: false, period: 14, overbought: 70, oversold: 30 },
          atr: { active: false, period: 14, multiplier: 2.0 },
          price_action: { active: false }
        },
        risk_config: bot.risk_config || {
          lot_size: 1,
          stop_loss: 200,
          take_profit: 500,
          trailing_stop: { active: false, distance: 150, step: 10 },
          daily_loss_limit: 500.0,
          daily_profit_limit: 1000.0,
        },
        ai_config: bot.ai_config || {
          rl_active: true,
          confidence_threshold: 0.7,
          mode: 'hybrid'
        },
        spy_config: bot.spy_config || {
          active: false,
          target_magic: null,
          follow_signals: true
        }
      });
    } else {
      setSelectedBot(null);
      setFormData({
        name: '',
        symbol: 'WIN',
        timeframe: 'M5',
        magic_number: Math.floor(Math.random() * 900000) + 100000,
        start_time: '09:00',
        end_time: '17:50',
        excluded_days: [],
        signals_config: {
          ma_cross: { active: false, fast_period: 9, slow_period: 21 },
          rsi: { active: false, period: 14, overbought: 70, oversold: 30 },
          atr: { active: false, period: 14, multiplier: 2.0 },
          price_action: { active: false }
        },
        risk_config: {
          lot_size: 1,
          stop_loss: 200,
          take_profit: 500,
          trailing_stop: { active: false, distance: 150, step: 10 },
          daily_loss_limit: 500.0,
          daily_profit_limit: 1000.0,
        },
        ai_config: {
          rl_active: true,
          confidence_threshold: 0.7,
          mode: 'hybrid'
        },
        spy_config: {
          active: false,
          target_magic: null,
          follow_signals: true
        }
      });
    }
    setShowModal(true);
  };

  const handleSave = async () => {
    const payload = {
      name: formData.name,
      symbol: formData.symbol,
      timeframe: formData.timeframe,
      magic_number: Number(formData.magic_number),
      excluded_days: formData.excluded_days,
      start_time: formData.start_time,
      end_time: formData.end_time,
      
      signals_config: formData.signals_config,
      risk_config: formData.risk_config,
      ai_config: formData.ai_config,
      spy_config: formData.spy_config,
      
      config: {
        last_train: new Date().toISOString()
      }
    };

    try {
      const method = selectedBot ? 'PUT' : 'POST';
      const url = selectedBot ? `${api_url}/bots/${selectedBot.id}` : `${api_url}/bots/`;

      const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        setShowModal(false);
        fetchBots();
      }
    } catch (error) {
      console.error("Erro ao salvar:", error);
    }
  };

  const deleteBot = async (id: number) => {
    if (!confirm("Tem certeza que deseja excluir?")) return;
    try {
      const response = await fetch(`${api_url}/bots/${id}`, { method: 'DELETE' });
      if (response.ok) {
        fetchBots();
        setShowModal(false);
      } else {
        alert("Erro ao excluir robô. Verifique se há ordens abertas.");
      }
    } catch (error) {
      console.error("Erro:", error);
    }
  };

  const toggleBot = async (botId: number, currentStatus: boolean) => {
    const action = currentStatus ? 'stop' : 'start';
    try {
      await fetch(`${api_url}/bots/${botId}/${action}`, { method: 'POST' });
      fetchBots();
    } catch (error) {
      console.error(`Erro:`, error);
    }
  };

  const trainBot = async (botId: number) => {
    console.log(`[ACTION] Iniciando treino para bot ${botId}`);
    try {
      const response = await fetch(`${api_url}/bots/${botId}/train`, { method: 'POST' });
      if (response.ok) {
        console.log(`[SUCCESS] Treino no bot ${botId} disparado.`);
        fetchProgress(); // Força uma atualização imediata
      } else {
        console.error(`[ERROR] Falha ao disparar treino: ${response.status}`);
      }
    } catch (error) {
      console.error("Erro no fetch train:", error);
    }
  };

  const syncBot = async (botId: number) => {
    console.log(`[ACTION] Iniciando sync para bot ${botId}`);
    try {
      const response = await fetch(`${api_url}/bots/${botId}/sync`, { method: 'POST' });
      if (response.ok) {
        console.log(`[SUCCESS] Sync no bot ${botId} disparado.`);
        fetchProgress(); // Força uma atualização imediata
      } else {
        console.error(`[ERROR] Falha ao disparar sync: ${response.status}`);
      }
    } catch (error) {
      console.error("Erro no fetch sync:", error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-3xl font-black text-white flex items-center gap-3">
            <Activity className="text-brand-primary h-8 w-8" />
            Meus Robôs
          </h2>
          <p className="text-gray-400">Frota operacional e qualidade de treinamento.</p>
        </div>
        <button 
          onClick={() => handleOpenModal()}
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {bots.map((bot) => {
            const winRate = bot.total_trades > 0 ? (bot.winning_trades / bot.total_trades) * 100 : 0;
            const aiQuality = winRate > 60 ? 85 : winRate > 40 ? 60 : 30;
            const progress = progressMap[String(bot.id)];
            
            return (
              <div key={bot.id} className="bg-bg-card border border-border-card rounded-[32px] p-6 hover:border-brand-primary/50 transition-all group relative overflow-hidden flex flex-col h-full">
                <div className={`absolute top-0 right-0 w-32 h-32 -mr-12 -mt-12 rounded-full blur-3xl opacity-10 ${bot.active ? 'bg-brand-primary' : 'bg-red-500'}`} />
                
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-2xl font-black text-white mb-2">{bot.name}</h3>
                    <div className="flex flex-wrap gap-2">
                      <span className="bg-gray-800 text-gray-400 text-[10px] font-black px-2 py-1 rounded-lg uppercase tracking-wider">{bot.symbol}</span>
                      <span className="bg-gray-800 text-gray-400 text-[10px] font-black px-2 py-1 rounded-lg uppercase tracking-wider">{bot.timeframe}</span>
                      <span className="bg-brand-primary/5 text-brand-primary/60 text-[10px] font-mono px-2 py-1 rounded-lg">MG: {bot.magic_number}</span>
                    </div>
                  </div>
                  <div className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest ${bot.active ? 'bg-brand-primary/10 text-brand-primary' : 'bg-red-500/10 text-red-500'}`}>
                    {bot.active ? 'LIVE' : 'IDLE'}
                  </div>
                </div>

                <div className="mb-6 bg-bg-dark/40 p-4 rounded-2xl border border-white/5">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-black text-gray-500 uppercase flex items-center gap-1">
                      <Zap size={10} className="text-brand-secondary" /> Qualidade da IA
                    </span>
                    <span className="text-[10px] font-black text-brand-secondary">{aiQuality}%</span>
                  </div>
                  <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-1000 ${aiQuality > 70 ? 'bg-brand-secondary' : aiQuality > 50 ? 'bg-yellow-500' : 'bg-red-500'}`} 
                      style={{ width: `${aiQuality}%` }} 
                    />
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-[9px] text-gray-500 font-medium">Última atualização:</span>
                    <span className="text-[9px] text-gray-400 font-bold">{bot.config?.last_train ? new Date(bot.config.last_train).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : 'Never'}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-bg-dark/50 p-3 rounded-2xl border border-border-card/30">
                    <p className="text-gray-500 text-[9px] uppercase font-black mb-1">PnL Realizado</p>
                    <p className={`text-lg font-black ${bot.total_pnl >= 0 ? 'text-brand-primary' : 'text-red-500'}`}>
                      R$ {bot.total_pnl.toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-bg-dark/50 p-3 rounded-2xl border border-border-card/30">
                    <p className="text-gray-500 text-[9px] uppercase font-black mb-1">Taxa de Acerto</p>
                    <p className="text-lg font-black text-white">
                      {winRate.toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* BARRA DE PROGRESSO DINÂMICA */}
                {progress && (
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
                      >
                        <div className="w-full h-full bg-white/20 animate-shimmer" />
                      </div>
                    </div>
                  </div>
                )}

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
                    onClick={() => handleOpenModal(bot)}
                    className="p-4 bg-gray-800 text-gray-400 hover:text-white rounded-2xl transition-all"
                    title="Configurações"
                  >
                    <Settings size={20} />
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
                    <BrainCircuit size={12} /> {progress?.type === 'train' ? 'TREINANDO...' : 'TREINAR'}
                  </button>
                  <button 
                    disabled={!!progress}
                    onClick={() => syncBot(bot.id)} 
                    className="text-[9px] font-black text-gray-500 hover:text-brand-secondary py-2 flex items-center justify-center gap-1 uppercase bg-white/5 rounded-xl transition-all disabled:opacity-20"
                  >
                    <RefreshCw size={12} /> {progress?.type === 'sync' ? 'SYNCING...' : 'SYNC'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-bg-card border border-border-card rounded-[48px] w-full max-w-2xl my-auto animate-in zoom-in-95 duration-300">
            <div className="p-10 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
              <div>
                <h3 className="text-3xl font-black text-white">{selectedBot ? 'Ajustes Finos' : 'Engenharia de Robô'}</h3>
                <p className="text-gray-400 text-sm mt-1">Defina parâmetros operacionais e algorítmicos.</p>
              </div>
              <button onClick={() => setShowModal(false)} className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-700 transition-all">
                <X size={24} />
              </button>
            </div>
            
            <div className="p-8 max-h-[70vh] overflow-y-auto space-y-10 custom-scrollbar">
              {/* SEÇÃO 1: NAVEGAÇÃO BÁSICA */}
              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                    <Layers size={14} className="text-brand-primary" /> Identificação do Bot
                  </label>
                  <input 
                    type="text" 
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-bold focus:ring-2 ring-brand-primary outline-none transition-all" 
                    placeholder="Ex: Sniper Win M5" 
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                    <Activity size={14} className="text-brand-primary" /> Magic Number
                  </label>
                  <input 
                    type="number" 
                    value={formData.magic_number}
                    onChange={(e) => setFormData({...formData, magic_number: parseInt(e.target.value)})}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-brand-primary font-black font-mono focus:ring-2 ring-brand-primary outline-none" 
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-8">
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Símbolo</label>
                  <input 
                    type="text" 
                    value={formData.symbol}
                    onChange={(e) => setFormData({...formData, symbol: e.target.value.toUpperCase()})}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-black uppercase" 
                  />
                </div>
                <div className="space-y-3">
                  <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Timeframe</label>
                  <select 
                    value={formData.timeframe}
                    onChange={(e) => setFormData({...formData, timeframe: e.target.value})}
                    className="w-full bg-bg-dark border border-border-card rounded-2xl px-5 py-4 text-white font-bold outline-none cursor-pointer"
                  >
                    {['M1', 'M5', 'M15', 'H1', 'D1'].map(tf => <option key={tf}>{tf}</option>)}
                  </select>
                </div>
              </div>

              {/* SEÇÃO 2: ARSENAL TÉCNICO (SINAIS) */}
              <div className="bg-white/5 p-8 rounded-[32px] border border-white/5 space-y-6">
                <h4 className="text-white font-black text-xs uppercase tracking-widest flex items-center gap-2">
                  <Zap size={16} className="text-yellow-400" /> Arsenal de Sinais Técnicos
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  {/* MA Cross */}
                  <div className={`p-4 rounded-2xl border transition-all ${formData.signals_config.ma_cross.active ? 'bg-brand-primary/10 border-brand-primary/30' : 'bg-bg-dark border-white/5'}`}>
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-[10px] font-black text-white uppercase">Crossover Médias</span>
                      <input 
                        type="checkbox" 
                        checked={formData.signals_config.ma_cross.active}
                        onChange={(e) => setFormData({...formData, signals_config: {...formData.signals_config, ma_cross: {...formData.signals_config.ma_cross, active: e.target.checked}}})}
                        className="w-5 h-5 accent-brand-primary cursor-pointer"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input type="number" placeholder="Fast" className="bg-black/20 text-[10px] p-2 rounded-lg text-white" value={formData.signals_config.ma_cross.fast_period} onChange={(e) => setFormData({...formData, signals_config: {...formData.signals_config, ma_cross: {...formData.signals_config.ma_cross, fast_period: parseInt(e.target.value)}}})} />
                      <input type="number" placeholder="Slow" className="bg-black/20 text-[10px] p-2 rounded-lg text-white" value={formData.signals_config.ma_cross.slow_period} onChange={(e) => setFormData({...formData, signals_config: {...formData.signals_config, ma_cross: {...formData.signals_config.ma_cross, slow_period: parseInt(e.target.value)}}})} />
                    </div>
                  </div>

                  {/* RSI */}
                  <div className={`p-4 rounded-2xl border transition-all ${formData.signals_config.rsi.active ? 'bg-blue-500/10 border-blue-500/30' : 'bg-bg-dark border-white/5'}`}>
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-[10px] font-black text-white uppercase">RSI (Ifr)</span>
                      <input 
                        type="checkbox" 
                        checked={formData.signals_config.rsi.active}
                        onChange={(e) => setFormData({...formData, signals_config: {...formData.signals_config, rsi: {...formData.signals_config.rsi, active: e.target.checked}}})}
                        className="w-5 h-5 accent-blue-500 cursor-pointer"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-1">
                      <input type="number" className="bg-black/20 text-[10px] p-2 rounded-lg text-white" value={formData.signals_config.rsi.period} onChange={(e) => setFormData({...formData, signals_config: {...formData.signals_config, rsi: {...formData.signals_config.rsi, period: parseInt(e.target.value)}}})} />
                      <input type="number" className="bg-black/20 text-[10px] p-2 rounded-lg text-white" value={formData.signals_config.rsi.overbought} onChange={(e) => setFormData({...formData, signals_config: {...formData.signals_config, rsi: {...formData.signals_config.rsi, overbought: parseInt(e.target.value)}}})} />
                      <input type="number" className="bg-black/20 text-[10px] p-2 rounded-lg text-white" value={formData.signals_config.rsi.oversold} onChange={(e) => setFormData({...formData, signals_config: {...formData.signals_config, rsi: {...formData.signals_config.rsi, oversold: parseInt(e.target.value)}}})} />
                    </div>
                  </div>
                </div>
              </div>

              {/* SEÇÃO 3: GESTÃO DE RISCO */}
              <div className="bg-white/5 p-8 rounded-[32px] border border-white/5 space-y-6">
                <h4 className="text-white font-black text-xs uppercase tracking-widest flex items-center gap-2">
                  <Square size={16} className="text-red-400" /> Blindagem de Risco
                </h4>
                <div className="grid grid-cols-3 gap-6">
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Lote Base</label>
                    <input type="number" className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-white font-bold" value={formData.risk_config.lot_size} onChange={(e) => setFormData({...formData, risk_config: {...formData.risk_config, lot_size: parseInt(e.target.value)}})} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Stop Loss (Pts)</label>
                    <input type="number" className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-red-500 font-black" value={formData.risk_config.stop_loss} onChange={(e) => setFormData({...formData, risk_config: {...formData.risk_config, stop_loss: parseInt(e.target.value)}})} />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[9px] font-black text-gray-500 uppercase">Take Profit (Pts)</label>
                    <input type="number" className="w-full bg-bg-dark border border-white/5 p-3 rounded-xl text-brand-primary font-black" value={formData.risk_config.take_profit} onChange={(e) => setFormData({...formData, risk_config: {...formData.risk_config, take_profit: parseInt(e.target.value)}})} />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6 p-4 bg-black/20 rounded-2xl">
                   <div className="flex items-center justify-between">
                      <span className="text-[10px] font-black text-gray-400 uppercase">Meta Diária (R$)</span>
                      <input type="number" className="bg-transparent text-right text-brand-primary font-black outline-none" value={formData.risk_config.daily_profit_limit} onChange={(e) => setFormData({...formData, risk_config: {...formData.risk_config, daily_profit_limit: parseFloat(e.target.value)}})} />
                   </div>
                   <div className="flex items-center justify-between border-l border-white/10 pl-6">
                      <span className="text-[10px] font-black text-gray-400 uppercase">Stop Diário (R$)</span>
                      <input type="number" className="bg-transparent text-right text-red-500 font-black outline-none" value={formData.risk_config.daily_loss_limit} onChange={(e) => setFormData({...formData, risk_config: {...formData.risk_config, daily_loss_limit: parseFloat(e.target.value)}})} />
                   </div>
                </div>

                {/* Trailing Stop Toggle */}
                <div className="flex items-center justify-between bg-bg-dark/50 p-4 rounded-2xl border border-white/5">
                   <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${formData.risk_config.trailing_stop.active ? 'bg-brand-secondary animate-pulse' : 'bg-gray-700'}`} />
                      <span className="text-xs font-black text-white">TRAILING STOP ATIVO</span>
                   </div>
                   <button 
                    onClick={() => setFormData({...formData, risk_config: {...formData.risk_config, trailing_stop: {...formData.risk_config.trailing_stop, active: !formData.risk_config.trailing_stop.active}}})}
                    className={`px-4 py-2 rounded-xl text-[10px] font-black transition-all ${formData.risk_config.trailing_stop.active ? 'bg-brand-secondary text-bg-dark' : 'bg-gray-800 text-gray-400'}`}
                   >
                     {formData.risk_config.trailing_stop.active ? 'HABILITADO' : 'DESABILITADO'}
                   </button>
                </div>
              </div>

              {/* SEÇÃO 4: IA & ESPIÃO */}
              <div className="grid grid-cols-2 gap-8">
                <div className="bg-gradient-to-br from-brand-primary/10 to-transparent p-6 rounded-[32px] border border-brand-primary/20">
                   <h4 className="text-[10px] font-black text-brand-primary uppercase tracking-widest mb-4 flex items-center gap-2">
                     <BrainCircuit size={16} /> Inteligência por Reforço
                   </h4>
                   <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-400">Status da IA</span>
                        <input type="checkbox" checked={formData.ai_config.rl_active} onChange={(e) => setFormData({...formData, ai_config: {...formData.ai_config, rl_active: e.target.checked}})} className="w-5 h-5 accent-brand-primary" />
                      </div>
                      <div className="space-y-1">
                        <div className="flex justify-between text-[9px] text-gray-500 font-black">
                          <span>CONFIANÇA MÍNIMA</span>
                          <span>{(formData.ai_config.confidence_threshold * 100).toFixed(0)}%</span>
                        </div>
                        <input type="range" min="0.5" max="0.95" step="0.05" value={formData.ai_config.confidence_threshold} onChange={(e) => setFormData({...formData, ai_config: {...formData.ai_config, confidence_threshold: parseFloat(e.target.value)}})} className="w-full h-1 bg-gray-800 accent-brand-primary rounded-full appearance-none" />
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
                        <input type="checkbox" checked={formData.spy_config.active} onChange={(e) => setFormData({...formData, spy_config: {...formData.spy_config, active: e.target.checked}})} className="w-5 h-5 accent-purple-500" />
                      </div>
                      <input 
                        type="number" 
                        placeholder="Magic Number Alvo" 
                        disabled={!formData.spy_config.active}
                        className="w-full bg-black/20 border border-white/5 p-3 rounded-xl text-white text-xs font-mono"
                        value={formData.spy_config.target_magic || ''}
                        onChange={(e) => setFormData({...formData, spy_config: {...formData.spy_config, target_magic: parseInt(e.target.value)}})}
                      />
                   </div>
                </div>
              </div>
            </div>

            <div className="p-10 border-t border-white/5 flex gap-4 bg-white/[0.01]">
              <button 
                className="flex-1 bg-brand-primary text-bg-dark font-black py-5 rounded-2xl hover:bg-brand-primary-dark transition-all transform hover:-translate-y-1 shadow-xl shadow-brand-primary/20 disabled:opacity-50 disabled:translate-y-0"
                onClick={handleSave}
                disabled={!formData.name}
              >
                {selectedBot ? 'SALVAR ALTERAÇÕES' : 'GERAR ROBÔ AGORA'}
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
