import React, { useState, useEffect } from 'react';
import { 
  Search, 
  RefreshCw,
  TrendingUp,
  DollarSign,
  Target,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  Bot as BotIcon
} from 'lucide-react';

interface Trade {
  id: number;
  bot_id: number;
  symbol: string;
  direction: string;
  volume: number;
  entry_price: number;
  exit_price?: number;
  profit: number;
  pnl: number;
  open_time: string;
  close_time?: string;
  status: string;
  comment?: string;
  magic_number?: number;
}

interface Stats {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  total_pnl: number;
  avg_win: number;
  avg_loss: number;
}

export const Trades: React.FC = () => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  
  const api_url = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const fetchTrades = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${api_url}/trades/?limit=100`);
      const data = await response.json();
      if (Array.isArray(data)) {
        setTrades(data);
      } else {
        console.error("API não retornou uma lista:", data);
        setTrades([]);
      }
    } catch (error) {
      console.error("Erro ao buscar trades:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrades();
  }, []);

  const filteredTrades = trades.filter(t => {
    const matchesSearch = t.symbol.toLowerCase().includes(searchTerm.toLowerCase()) || 
                         t.id.toString().includes(searchTerm);
    if (filter === 'all') return matchesSearch;
    if (filter === 'buy') return matchesSearch && t.direction === 'buy';
    if (filter === 'sell') return matchesSearch && t.direction === 'sell';
    return matchesSearch;
  });

  // Cálculos de Estatísticas
  const closedTrades = trades.filter(t => t.close_time);
  const wins = closedTrades.filter(t => t.pnl > 0);
  const losses = closedTrades.filter(t => t.pnl <= 0);
  
  const stats: Stats = {
    total_trades: trades.length,
    win_rate: closedTrades.length > 0 ? (wins.length / closedTrades.length) * 100 : 0,
    total_pnl: trades.reduce((acc, t) => acc + (t.pnl || 0), 0),
    avg_win: wins.length > 0 ? wins.reduce((acc, t) => acc + t.pnl, 0) / wins.length : 0,
    avg_loss: losses.length > 0 ? Math.abs(losses.reduce((acc, t) => acc + t.pnl, 0) / losses.length) : 0,
    profit_factor: 1.5 // Mock: Seria calculado sum(wins)/abs(sum(losses))
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Header com Estatísticas "Extremas" */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-bg-card border border-border-card p-6 rounded-[32px] relative overflow-hidden group">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-brand-primary/10 rounded-full blur-2xl group-hover:bg-brand-primary/20 transition-all" />
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-tighter mb-4 flex items-center gap-2">
            <DollarSign size={12} className="text-brand-primary" /> Lucro Líquido Acumulado
          </p>
          <div className="flex items-end justify-between">
            <h3 className={`text-3xl font-black ${stats.total_pnl >= 0 ? 'text-brand-primary' : 'text-red-500'}`}>
              R$ {stats.total_pnl.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </h3>
            <span className="text-[10px] bg-brand-primary/10 text-brand-primary px-2 py-1 rounded-lg font-black">+12.4%</span>
          </div>
        </div>

        <div className="bg-bg-card border border-border-card p-6 rounded-[32px] relative overflow-hidden group">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-tighter mb-4 flex items-center gap-2">
            <Target size={12} className="text-brand-secondary" /> Taxa de Acerto (Win Rate)
          </p>
          <div className="flex items-end justify-between">
            <h3 className="text-3xl font-black text-white">{stats.win_rate.toFixed(1)}%</h3>
            <div className="w-16 h-2 bg-gray-800 rounded-full overflow-hidden mb-2">
              <div className="bg-brand-secondary h-full" style={{ width: `${stats.win_rate}%` }} />
            </div>
          </div>
        </div>

        <div className="bg-bg-card border border-border-card p-6 rounded-[32px] relative overflow-hidden group">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-tighter mb-4 flex items-center gap-2">
            <BarChart3 size={12} className="text-purple-500" /> Fator de Lucro
          </p>
          <div className="flex items-end justify-between">
            <h3 className="text-3xl font-black text-white">{stats.profit_factor.toFixed(2)}</h3>
            <span className="text-[10px] text-gray-500 font-bold mb-1">IDEAL: &gt; 1.5</span>
          </div>
        </div>

        <div className="bg-bg-card border border-border-card p-6 rounded-[32px] relative overflow-hidden group">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-tighter mb-4 flex items-center gap-2">
            <TrendingUp size={12} className="text-emerald-500" /> Expectativa Por Trade
          </p>
          <div className="flex flex-col">
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-emerald-400 font-bold">Ganho: R$ {stats.avg_win.toFixed(0)}</span>
              <span className="text-red-400 font-bold">Perda: R$ {stats.avg_loss.toFixed(0)}</span>
            </div>
            <div className="w-full h-1 bg-gray-800 rounded-full flex overflow-hidden">
               <div className="bg-emerald-500 h-full" style={{ width: '60%' }} />
               <div className="bg-red-500 h-full" style={{ width: '40%' }} />
            </div>
          </div>
        </div>
      </div>

      {/* Tabela de Operações "Extrema" */}
      <div className="bg-bg-card border border-border-card rounded-[40px] overflow-hidden shadow-2xl">
        <div className="p-8 border-b border-border-card/50 flex flex-wrap gap-6 items-center justify-between bg-white/[0.01]">
          <div className="flex items-center gap-4">
            <h3 className="text-xl font-black text-white">Journal de Operações</h3>
            <div className="flex bg-bg-dark border border-border-card p-1 rounded-2xl">
              {['all', 'buy', 'sell'].map((t) => (
                <button
                  key={t}
                  onClick={() => setFilter(t)}
                  className={`px-5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                    filter === t 
                    ? 'bg-brand-primary text-bg-dark shadow-lg shadow-brand-primary/20' 
                    : 'text-gray-500 hover:text-white'
                  }`}
                >
                  {t === 'all' ? 'TUDO' : t === 'buy' ? 'COMPRAS' : 'VENDAS'}
                </button>
              ))}
            </div>
          </div>
          
          <div className="flex gap-4">
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-brand-primary transition-colors" size={18} />
              <input 
                type="text" 
                placeholder="Buscar por ativo, ID ou robô..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-bg-dark border border-border-card rounded-2xl pl-12 pr-6 py-3 text-sm text-white outline-none focus:ring-2 ring-brand-primary/20 w-80 transition-all font-medium"
              />
            </div>
            <button 
              onClick={fetchTrades}
              className="px-6 py-3 bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700 rounded-2xl transition-all border border-transparent hover:border-gray-600 active:scale-95"
            >
              <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] border-b border-border-card/30 bg-bg-dark/20">
                <th className="px-8 py-6">Operação / Ativo</th>
                <th className="px-6 py-6">Tipo & Robô</th>
                <th className="px-6 py-6">Qtde (Lote)</th>
                <th className="px-6 py-6 font-mono">Preço Entrada</th>
                <th className="px-6 py-6 font-mono">Preço Saída</th>
                <th className="px-6 py-6 text-right">Resultado</th>
                <th className="px-8 py-6">Fechamento</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-32 text-center">
                    <div className="flex flex-col items-center gap-4">
                      <RefreshCw className="animate-spin text-brand-primary" size={40} />
                      <p className="text-xs font-black text-gray-500 uppercase tracking-widest">Sincronizando Histórico Pro...</p>
                    </div>
                  </td>
                </tr>
              ) : filteredTrades.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-32 text-center text-gray-500 italic">
                    Nenhuma operação encontrada com os filtros atuais.
                  </td>
                </tr>
              ) : (
                filteredTrades.map((trade) => (
                  <tr key={trade.id} className="border-b border-border-card/5 hover:bg-white/[0.02] transition-colors group cursor-pointer">
                    <td className="px-8 py-6">
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-[18px] flex items-center justify-center border font-black text-xs ${
                          trade.pnl > 0 
                          ? 'bg-brand-primary/10 border-brand-primary/20 text-brand-primary' 
                          : 'bg-red-500/10 border-red-500/20 text-red-500'
                        }`}>
                          {trade.symbol.slice(0, 3)}
                        </div>
                        <div>
                          <p className="font-black text-gray-100 text-base">{trade.symbol}</p>
                          <p className="text-[10px] font-mono text-gray-500 flex items-center gap-1 uppercase">
                            <BotIcon size={10} /> ID: {trade.id} <span className="text-gray-700">•</span> MG: {trade.magic_number}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-6">
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded-md text-[9px] font-black uppercase tracking-wider ${
                            trade.direction === 'buy' ? 'bg-brand-primary text-bg-dark' : 'bg-red-500 text-white'
                          }`}>
                            {trade.direction}
                          </span>
                          <span className="text-[10px] text-gray-400 font-bold uppercase">Sniper Bot v2</span>
                        </div>
                        <p className="text-[10px] text-gray-600 font-medium truncate max-w-[120px]">
                          {trade.comment || 'Executado via IA Orchestrator'}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-6">
                      <span className="font-mono font-black text-gray-300 bg-gray-800/50 px-3 py-1.5 rounded-xl border border-white/5">
                        {trade.volume.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-6 py-6 font-mono font-bold text-gray-400">
                      {trade.entry_price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-6 font-mono font-bold text-gray-200">
                      {trade.exit_price ? trade.exit_price.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '---'}
                    </td>
                    <td className="px-6 py-6 text-right">
                      <div className="flex flex-col items-end">
                        <div className={`flex items-center gap-1 font-black text-lg ${trade.pnl >= 0 ? 'text-brand-primary' : 'text-red-500'}`}>
                          {trade.pnl >= 0 ? <ArrowUpRight size={20} /> : <ArrowDownRight size={20} />}
                          R$ {Math.abs(trade.pnl).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </div>
                        <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest mt-0.5">
                          {trade.pnl >= 0 ? 'Lucro Líquido' : 'Prejuízo Real'}
                        </span>
                      </div>
                    </td>
                    <td className="px-8 py-6">
                      <div className="flex items-center justify-between">
                        <div className="text-right mr-4">
                          <p className="text-xs font-bold text-gray-300">{trade.close_time ? new Date(trade.close_time).toLocaleDateString('pt-BR') : 'Operando...'}</p>
                          <p className="text-[10px] font-mono text-gray-600">{trade.close_time ? new Date(trade.close_time).toLocaleTimeString('pt-BR') : 'Aguardando Saída'}</p>
                        </div>
                        <ChevronRight className="text-gray-800 group-hover:text-brand-primary group-hover:translate-x-1 transition-all" size={20} />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Footer da Tabela */}
        <div className="p-6 bg-bg-dark/30 border-t border-border-card/50 flex justify-between items-center text-[10px] font-black uppercase text-gray-500 tracking-widest">
           <div>MOSTRANDO {filteredTrades.length} DE {trades.length} OPERAÇÕES</div>
           <div className="flex gap-4">
              <button className="hover:text-white transition-colors">Anterior</button>
              <div className="flex gap-2">
                 <span className="text-brand-primary bg-brand-primary/10 px-2 rounded">1</span>
                 <span className="px-2">2</span>
                 <span className="px-2">3</span>
              </div>
              <button className="hover:text-white transition-colors">Próxima</button>
           </div>
        </div>
      </div>
    </div>
  );
};
