import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { MetricCard } from './components/MetricCard';
import { Brain } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Bots } from './components/Bots';
import { Trades } from './components/Trades';

import { NewsAI } from './components/NewsAI';
import { NotificationOverlay } from './components/NotificationOverlay';
import { Backtesting } from './components/Backtesting';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [metrics, setMetrics] = useState({
    total_pnl: 0,
    win_rate: 0,
    max_drawdown: 0,
    total_candles: 0,
    active_bots: 0,
    total_trades: 0
  });
  const [lastTrades, setLastTrades] = useState([]);
  const [equityData, setEquityData] = useState([]);

  // Busca dados dinâmicos da API
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Métricas do Dashboard
        const metricsRes = await fetch('http://localhost:8000/dashboard/metrics');
        const metricsData = await metricsRes.json();
        setMetrics(metricsData);

        // Últimos 5 Trades
        const tradesRes = await fetch('http://localhost:8000/trades/?limit=5');
        const tradesData = await tradesRes.json();
        setLastTrades(tradesData);

        // TODO: Buscar dados da equity real futuramente
        // setEquityData(mockData); 
      } catch (err) {
        console.error("Erro ao carregar dados do Dashboard:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // Atualiza a cada 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex bg-bg-dark text-white min-h-screen font-sans">
      <NotificationOverlay />
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="flex-1 overflow-y-auto p-8">
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            <header className="mb-8 flex justify-between items-center">
              <div>
                <h2 className="text-3xl font-bold mb-1">Bem-vindo, Trader</h2>
                <p className="text-gray-400">Aqui está o resumo da sua operação hoje.</p>
              </div>
              <div className="flex gap-4">
                <div className="text-right">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-bold">Patrimônio Líquido</p>
                  <p className="text-2xl font-black text-brand-primary font-mono select-none">
                    R$ {(10000 + metrics.total_pnl).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </p>
                </div>
              </div>
            </header>

            {/* Métricas Principais Dinâmicas */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard 
                label="PnL Total (Dia)" 
                value={`R$ ${metrics.total_pnl.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`} 
                delta={metrics.total_trades.toString()} 
                deltaLabel="trades"
                isPositive={metrics.total_pnl >= 0} 
              />
              <MetricCard 
                label="Win Rate" 
                value={`${metrics.win_rate}%`} 
                isPositive={metrics.win_rate >= 50} 
              />
              <MetricCard 
                label="Max Drawdown" 
                value={`${metrics.max_drawdown}%`} 
                isPositive={false} 
              />
              <MetricCard 
                label="Dataset (Velas)" 
                value={metrics.total_candles.toLocaleString()} 
                delta={metrics.active_bots.toString()} 
                deltaLabel="IA bots"
                isPositive={true} 
              />
            </div>

            {/* Gráfico de Performance (Vazio se não houver dados) */}
            <div className="bg-bg-card border border-border-card p-6 rounded-3xl h-[400px] min-w-0">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold">Curva de Equity Real-time</h3>
                <div className="flex gap-2">
                  <span className="bg-brand-primary/10 text-brand-primary px-3 py-1 rounded-full text-xs font-bold ring-1 ring-brand-primary/30">M1</span>
                  <span className="bg-gray-800 text-gray-400 px-3 py-1 rounded-full text-xs font-bold">M5</span>
                </div>
              </div>
              
              {equityData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                  <LineChart data={equityData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2d333f" vertical={false} />
                    <XAxis dataKey="time" stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} 
                      tickFormatter={(val) => `R$ ${val/1000}k`} />
                    <Tooltip contentStyle={{ backgroundColor: '#161a23', border: '1px solid #2d333f', borderRadius: '12px' }} />
                    <Line type="monotone" dataKey="balance" stroke="#00ff88" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-600 italic">
                  Aguardando primeiras operações para gerar curva...
                </div>
              )}
            </div>

            {/* Seção Inferior Dinâmica */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-bg-card border border-border-card p-6 rounded-3xl">
                <h3 className="text-xl font-bold mb-4">Últimos Trades Reais</h3>
                <div className="overflow-x-auto">
                  {lastTrades.length > 0 ? (
                    <table className="w-full">
                      <thead>
                        <tr className="text-left text-gray-500 text-sm border-b border-border-card">
                          <th className="pb-4 font-medium">Ativo</th>
                          <th className="pb-4 font-medium">Tipo</th>
                          <th className="pb-4 font-medium">Preço</th>
                          <th className="pb-4 font-medium">PnL Bruto</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm">
                        {lastTrades.map((trade: any) => (
                          <tr key={trade.id} className="border-b border-border-card/50 last:border-0">
                            <td className="py-4 font-bold text-gray-200">{trade.symbol}</td>
                            <td className="py-4">
                              <span className={`px-2 py-1 rounded-md text-xs font-bold uppercase ${
                                trade.direction === 'buy' ? 'bg-brand-primary/10 text-brand-primary' : 'bg-red-500/10 text-red-500'
                              }`}>
                                {trade.direction}
                              </span>
                            </td>
                            <td className="py-4 font-mono text-gray-400">{trade.entry_price}</td>
                            <td className={`py-4 font-bold ${trade.profit >= 0 ? 'text-brand-primary' : 'text-red-500'}`}>
                              {trade.profit >= 0 ? '+' : ''}R$ {trade.profit?.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="text-center py-8 text-gray-500">Nenhum trade registrado ainda.</div>
                  )}
                </div>
              </div>
              
              <div className="bg-gradient-to-br from-brand-primary/10 to-brand-secondary/10 border border-brand-primary/20 p-6 rounded-3xl flex flex-col justify-between">
                <div>
                  <h3 className="text-xl font-black mb-2 flex items-center gap-2">
                    <Brain className="text-brand-primary" />
                    Status da IA
                  </h3>
                  <p className="text-gray-300 leading-relaxed italic">
                    {metrics.active_bots > 0 
                      ? "Motores neurais ativos e monitorando o mercado. Aguardando gatilhos de alta probabilidade."
                      : "Aguardando ativação de bots para iniciar análise de insights em tempo real."}
                  </p>
                </div>
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-bold text-gray-400">Prontidão do Sistema</span>
                    <span className="text-sm font-black text-brand-primary">
                      {metrics.total_candles > 0 ? "CALIBRADO" : "SINCRONIZANDO"}
                    </span>
                  </div>
                  <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                    <div className="bg-brand-primary h-full rounded-full" style={{ width: metrics.total_candles > 0 ? '100%' : '15%' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'bots' && <Bots />}
        {activeTab === 'trades' && <Trades />}
        {activeTab === 'news' && <NewsAI />}
        {activeTab === 'backtesting' && <Backtesting />}
      </main>
    </div>
  );
}

export default App;
