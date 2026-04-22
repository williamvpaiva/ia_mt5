import React, { useState } from 'react';
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  AreaChart, Area, BarChart, Bar, Cell 
} from 'recharts';
import { 
  Play, Target, ShieldAlert, Zap, 
  BarChart3, TrendingUp, History, RefreshCw, Calendar
} from 'lucide-react';

export const Backtesting: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [btData, setBtData] = useState<any>(null);
  const [bots, setBots] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);

  // Garantindo que a API seja acessada corretamente
  const API_URL = 'http://localhost:8000';

  const [params, setParams] = useState({
    bot_id: 0,
    symbol: 'WIN$',
    timeframe: 'M5',
    start_date: '2024-01-01',
    end_date: '2024-04-19',
    initial_capital: 10000
  });

  const fetchAll = async () => {
    try {
      const [botsRes, histRes] = await Promise.all([
        fetch(`${API_URL}/bots/`),
        fetch(`${API_URL}/backtest/list`)
      ]);
      const botsData = await botsRes.json();
      const histData = await histRes.json();
      
      setBots(botsData || []);
      setHistory(histData || []);
      
      if (botsData && botsData.length > 0 && params.bot_id === 0) {
        setParams(p => ({ ...p, bot_id: botsData[0].id, symbol: botsData[0].symbol || 'WIN$' }));
      }
    } catch (err) {
      console.error("Erro ao carregar dados:", err);
    }
  };

  React.useEffect(() => {
    fetchAll();
    console.log("[Research Hub] Terminal Ativo");
  }, []);

  const runTest = async () => {
    setLoading(true);
    setBtData(null);
    try {
      console.log("[Research Hub] Enviando Simulação:", params);
      const res = await fetch(`${API_URL}/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Falha na simulação");
      }
      const data = await res.json();
      console.log("[Research Hub] Resultado Recebido:", data);
      setBtData(data);
      fetchAll();
    } catch (err: any) {
      console.error("Erro no Backtest:", err);
      alert("Erro: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-1000 pb-20">
      <div className="bg-[#11141b]/60 backdrop-blur-2xl border border-white/5 rounded-[40px] p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-brand-primary/5 blur-[100px] rounded-full -mr-32 -mt-32" />
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-8 relative z-10">
          <div className="flex items-center gap-6">
            <div className="w-16 h-16 rounded-[24px] bg-gradient-to-br from-brand-primary/20 to-brand-primary/5 flex items-center justify-center border border-brand-primary/30 shadow-[0_0_30px_rgba(0,255,178,0.15)]">
              <History className="text-brand-primary" size={32} />
            </div>
            <div>
              <h1 className="text-3xl font-black uppercase tracking-tighter text-white">Research Hub</h1>
              <div className="flex items-center gap-2 mt-1">
                <span className="w-2 h-2 rounded-full bg-brand-primary animate-pulse" />
                <p className="text-[10px] font-black text-gray-500 uppercase tracking-[4px]">Plataforma de Simulação Estável</p>
              </div>
            </div>
          </div>
          <button 
            onClick={runTest}
            disabled={loading || !params.bot_id}
            className="px-12 py-4 bg-[#00FFB2] text-[#0a0d14] font-black text-[12px] uppercase rounded-[24px] transition-all flex items-center gap-3 shadow-[0_10px_30px_rgba(0,255,178,0.2)] hover:scale-105 active:scale-95 disabled:opacity-30"
          >
            {loading ? <RefreshCw className="animate-spin" size={18} /> : <Play size={18} fill="currentColor" />}
            {loading ? 'CALCULANDO' : 'INICIAR NOVA SIMULAÇÃO'}
          </button>
        </div>
      </div>

      <div className="bg-[#11141b]/40 border border-white/5 p-6 rounded-[32px] flex flex-wrap gap-4 items-center">
        <select 
          className="bg-black/40 text-white text-[10px] font-black uppercase px-6 py-3 rounded-2xl border border-white/5 outline-none cursor-pointer focus:border-brand-primary/50 transition-all min-w-[200px]"
          value={params.bot_id}
          onChange={(e) => {
            const b = bots.find(x => x.id === parseInt(e.target.value));
            setParams({...params, bot_id: parseInt(e.target.value), symbol: b?.symbol || b?.config?.symbol || 'WIN$'});
          }}
        >
          <option value="">SELECIONAR ROBÔ</option>
          {bots.map(b => (
            <option key={b.id} value={b.id} className="bg-[#11141b]">{b.name.toUpperCase()}</option>
          ))}
        </select>
        <div className="flex gap-2 bg-black/40 px-5 py-3 rounded-2xl border border-white/5">
          <Calendar size={14} className="text-brand-primary opacity-60" />
          <input type="date" className="bg-transparent text-white text-[10px] font-black outline-none [color-scheme:dark]" value={params.start_date} onChange={(e) => setParams({...params, start_date: e.target.value})} />
          <span className="text-gray-700">/</span>
          <input type="date" className="bg-transparent text-white text-[10px] font-black outline-none [color-scheme:dark]" value={params.end_date} onChange={(e) => setParams({...params, end_date: e.target.value})} />
        </div>
      </div>

      {btData && (
        <div className="grid grid-cols-12 gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
          <div className="col-span-12 grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard title="Total Return" value={`${(btData?.metrics?.total_return || 0).toFixed(2)}%`} icon={<TrendingUp size={16} />} color="#00FFB2" />
            <MetricCard title="Sharpe Ratio" value={(btData?.metrics?.sharpe || 0).toFixed(2)} icon={<Target size={16} />} color="#60A5FA" />
            <MetricCard title="Max Drawdown" value={`${(btData?.metrics?.max_drawdown || 0).toFixed(2)}%`} icon={<ShieldAlert size={16} />} color="#F87171" />
            <MetricCard title="Trades" value={btData?.metrics?.trades_count || 0} icon={<Zap size={16} />} color="#FACC15" />
          </div>

          <div className="col-span-12 lg:col-span-8 bg-[#11141b] border border-white/5 rounded-[32px] p-8">
            <h2 className="text-xs font-black uppercase tracking-widest text-[#00FFB2] mb-8 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00FFB2]" /> Curva de Capital
            </h2>
            <div className="h-[400px] w-full min-w-0" style={{ minHeight: '400px' }}>
              {btData?.equity_curve && btData.equity_curve.length > 0 ? (
                <ResponsiveContainer width="99%" height={400}>
                  <AreaChart data={btData.equity_curve.map((e: any) => ({ time: e[0], value: e[1] }))}>
                    <defs>
                      <linearGradient id="colorEq" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00FFB2" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#00FFB2" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis 
                      stroke="#ffffff20" 
                      fontSize={9} 
                      tickFormatter={(value) => `R$ ${value.toLocaleString()}`}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#11141b', border: '1px solid #ffffff10', borderRadius: '16px' }}
                      itemStyle={{ color: '#00FFB2' }}
                    />
                    <Area type="monotone" dataKey="value" stroke="#00FFB2" strokeWidth={3} fill="url(#colorEq)" isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-500 text-xs font-black uppercase tracking-widest bg-black/20 rounded-2xl">
                  Aguardando Execução...
                </div>
              )}
            </div>
          </div>

          <div className="col-span-12 lg:col-span-4 bg-[#11141b] border border-white/5 rounded-[32px] p-8">
            <h2 className="text-xs font-black uppercase tracking-widest text-[#F87171] mb-8 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#F87171]" /> Distribuição P&L
            </h2>
            <div className="h-[400px] w-full min-w-0 overflow-hidden">
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={mockReturnDist}>
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    {mockReturnDist.map((e, index) => <Cell key={index} fill={e.count > 5 ? '#00FFB2' : '#F87171'} opacity={0.6} />)}
                  </Bar>
                  <XAxis dataKey="bucket" hide />
                  <Tooltip contentStyle={{ backgroundColor: '#11141b', border: '1px solid #ffffff10' }} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      <div className="bg-[#11141b]/60 border border-white/5 rounded-[40px] p-8 shadow-2xl relative overflow-hidden">
        <div className="mb-10 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <BarChart3 className="text-brand-primary" size={20} />
              <h2 className="text-2xl font-black text-white tracking-tight uppercase">Histórico Quantitativo</h2>
            </div>
            <p className="text-[10px] font-bold text-gray-500 tracking-[5px] uppercase mt-2">Log de Performance</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-separate border-spacing-y-3">
            <thead>
              <tr className="text-gray-500">
                <th className="text-left px-6 py-4 text-[10px] font-black uppercase tracking-widest">Bot Name</th>
                <th className="text-center px-6 py-4 text-[10px] font-black uppercase tracking-widest">Return</th>
                <th className="text-center px-6 py-4 text-[10px] font-black uppercase tracking-widest">Drawdown</th>
                <th className="text-right px-6 py-4 text-[10px] font-black uppercase tracking-widest">Action</th>
              </tr>
            </thead>
            <tbody>
              {history.map((bt) => (
                <tr key={bt.id} className="group">
                  <td className="bg-white/[0.02] py-5 px-6 rounded-l-2xl border-y border-l border-white/5">
                    <span className="text-xs font-black text-white">{bt.bot_name?.toUpperCase() || 'ROBÔ'}</span>
                  </td>
                  <td className="bg-white/[0.02] py-5 px-6 border-y border-white/5 text-center">
                    <span className={`text-sm font-black ${(bt.total_return_pct || bt.total_return || 0) >= 0 ? 'text-[#00FFB2]' : 'text-red-400'}`}>
                      {(bt.total_return_pct || bt.total_return || 0).toFixed(2)}%
                    </span>
                  </td>
                  <td className="bg-white/[0.02] py-5 px-6 border-y border-white/5 text-center text-sm font-black text-red-500/80">
                    -{Math.abs(bt.max_drawdown || 0).toFixed(2)}%
                  </td>
                  <td className="bg-white/[0.02] py-5 px-6 rounded-r-2xl border-y border-r border-white/5 text-right">
                    <button onClick={() => { setBtData(bt); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="px-6 py-2 bg-white/5 hover:bg-brand-primary hover:text-bg-dark rounded-xl text-[10px] font-black text-gray-300 transition-all uppercase">Ver</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const MetricCard = ({ title, value, icon, color }: any) => (
  <div className="bg-[#11141b] border border-white/5 p-6 rounded-[28px] hover:border-white/10 transition-all group overflow-hidden relative">
    <div className="absolute top-0 right-0 p-4 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity">{React.cloneElement(icon, { size: 64 })}</div>
    <div className="flex items-center gap-2 mb-2">
      <div className="p-1.5 rounded-lg bg-opacity-10" style={{ backgroundColor: `${color}20`, color }}>{icon}</div>
      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{title}</span>
    </div>
    <div className="text-2xl font-black tracking-tighter" style={{ color }}>{value || '---'}</div>
  </div>
);

const mockReturnDist = [
  { bucket: '-5%', count: 2 }, { bucket: '-2%', count: 5 }, { bucket: '0%', count: 12 }, { bucket: '2%', count: 18 }, { bucket: '5%', count: 7 }, { bucket: '10%', count: 3 },
];
