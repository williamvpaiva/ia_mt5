import { useEffect, useRef, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { MetricCard } from './components/MetricCard';
import { Activity, Brain, Eye, RefreshCw, Settings, Wifi, WifiOff } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Bots } from './components/Bots';
import { BotLogs } from './components/BotLogs';
import { Trades } from './components/Trades';
import { NewsAI } from './components/NewsAI';
import { NotificationOverlay } from './components/NotificationOverlay';
import { Backtesting } from './components/Backtesting';

type DashboardSnapshot = {
  timestamp?: string;
  symbol?: string;
  mt5_connected?: boolean;
  bridge_uptime_seconds?: number;
  terminal_name?: string;
  account_login?: number | null;
  account_name?: string | null;
  account_server?: string | null;
  total_pnl?: number;
  live_total_pnl?: number;
  daily_pnl?: number;
  daily_realized_pnl?: number;
  floating_pnl?: number;
  win_rate?: number;
  max_drawdown?: number;
  active_bots?: number;
  total_candles?: number;
  total_trades?: number;
  open_trades?: number;
  closed_trades?: number;
  open_positions?: number;
  account_balance?: number;
  account_equity?: number;
  account_margin?: number;
  account_free_margin?: number;
  account_profit?: number;
  symbol_spread?: number;
  historical_daily_pnl?: number;
  recent_trades?: Array<Record<string, any>>;
  open_positions_detail?: Array<Record<string, any>>;
  equity_point?: {
    time?: string;
    balance?: number;
    equity?: number;
    floating_pnl?: number;
  };
};

type IndicatorKey =
  | 'live_total_pnl'
  | 'daily_pnl'
  | 'account_equity'
  | 'account_balance'
  | 'account_free_margin'
  | 'floating_pnl'
  | 'open_positions'
  | 'symbol_spread'
  | 'win_rate'
  | 'max_drawdown'
  | 'active_bots'
  | 'total_candles'
  | 'daily_realized_pnl'
  | 'historical_daily_pnl'
  | 'account_margin'
  | 'account_profit'
  | 'bridge_uptime_seconds'
  | 'mt5_connected';

type IndicatorOption = {
  id: IndicatorKey;
  label: string;
  defaultVisible: boolean;
};

const DASHBOARD_STORAGE_KEY = 'ia_mt5_dashboard_indicators_v2';

const DASHBOARD_INDICATORS: IndicatorOption[] = [
  { id: 'live_total_pnl', label: 'PnL ao vivo', defaultVisible: true },
  { id: 'daily_pnl', label: 'PnL diário', defaultVisible: true },
  { id: 'account_equity', label: 'Equity', defaultVisible: true },
  { id: 'account_balance', label: 'Saldo', defaultVisible: true },
  { id: 'floating_pnl', label: 'PnL flutuante', defaultVisible: false },
  { id: 'account_free_margin', label: 'Margem livre', defaultVisible: false },
  { id: 'open_positions', label: 'Posições abertas', defaultVisible: true },
  { id: 'symbol_spread', label: 'Spread', defaultVisible: false },
  { id: 'win_rate', label: 'Win rate', defaultVisible: true },
  { id: 'max_drawdown', label: 'Drawdown', defaultVisible: true },
  { id: 'active_bots', label: 'Bots ativos', defaultVisible: true },
  { id: 'total_candles', label: 'Velas', defaultVisible: false },
  { id: 'daily_realized_pnl', label: 'PnL realizado', defaultVisible: false },
  { id: 'historical_daily_pnl', label: 'PnL histórico', defaultVisible: false },
  { id: 'account_margin', label: 'Margem usada', defaultVisible: false },
  { id: 'account_profit', label: 'Lucro aberto', defaultVisible: false },
  { id: 'bridge_uptime_seconds', label: 'Uptime bridge', defaultVisible: false },
  { id: 'mt5_connected', label: 'MT5 online', defaultVisible: true },
];

const buildDefaultIndicatorPrefs = () =>
  Object.fromEntries(DASHBOARD_INDICATORS.map((item) => [item.id, item.defaultVisible])) as Record<IndicatorKey, boolean>;

const loadIndicatorPrefs = (): Record<IndicatorKey, boolean> => {
  const defaults = buildDefaultIndicatorPrefs();
  if (typeof window === 'undefined') return defaults;

  try {
    const raw = window.localStorage.getItem(DASHBOARD_STORAGE_KEY);
    if (!raw) return defaults;

    const parsed = JSON.parse(raw) as Record<string, boolean>;
    return DASHBOARD_INDICATORS.reduce((acc, item) => {
      acc[item.id] = typeof parsed[item.id] === 'boolean' ? parsed[item.id] : item.defaultVisible;
      return acc;
    }, {} as Record<IndicatorKey, boolean>);
  } catch {
    return defaults;
  }
};

const formatMoney = (value?: number) =>
  (value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const formatTime = (iso?: string) => {
  if (!iso) return '--:--:--';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '--:--:--';
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const formatDuration = (seconds?: number) => {
  const total = Math.max(0, Math.floor(seconds ?? 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
};

const normalizeSnapshot = (payload: any): DashboardSnapshot => {
  const source = payload?.data ?? payload ?? {};
  const snapshot: DashboardSnapshot = {
    mt5_connected: false,
    bridge_uptime_seconds: 0,
    total_pnl: 0,
    live_total_pnl: 0,
    daily_pnl: 0,
    daily_realized_pnl: 0,
    floating_pnl: 0,
    win_rate: 0,
    max_drawdown: 0,
    active_bots: 0,
    total_candles: 0,
    total_trades: 0,
    open_trades: 0,
    closed_trades: 0,
    open_positions: 0,
    account_balance: 0,
    account_equity: 0,
    account_margin: 0,
    account_free_margin: 0,
    account_profit: 0,
    symbol_spread: 0,
    historical_daily_pnl: 0,
    recent_trades: [],
    open_positions_detail: [],
    ...source,
  };

  snapshot.recent_trades = Array.isArray(source.recent_trades) ? source.recent_trades : [];
  snapshot.open_positions_detail = Array.isArray(source.open_positions_detail) ? source.open_positions_detail : [];

  return snapshot;
};

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboard, setDashboard] = useState<DashboardSnapshot>(normalizeSnapshot({}));
  const [equityData, setEquityData] = useState<Array<{ time: string; balance: number; equity: number }>>([]);
  const [indicatorPrefs, setIndicatorPrefs] = useState<Record<IndicatorKey, boolean>>(loadIndicatorPrefs);
  const [transportMode, setTransportMode] = useState<'websocket' | 'polling' | 'offline'>('offline');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<number | null>(null);

  const apiBase = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
  const wsBase = apiBase.replace(/^https?/i, (match) => (match.toLowerCase() === 'https' ? 'wss' : 'ws'));

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(DASHBOARD_STORAGE_KEY, JSON.stringify(indicatorPrefs));
  }, [indicatorPrefs]);

  const appendEquityPoint = (snapshot: DashboardSnapshot) => {
    const point = snapshot.equity_point ?? {
      time: snapshot.timestamp || new Date().toISOString(),
      balance: snapshot.account_balance ?? 0,
      equity: snapshot.account_equity ?? 0,
      floating_pnl: snapshot.floating_pnl ?? 0,
    };

    const label = formatTime(point.time);
    setEquityData((prev) => {
      const nextPoint = {
        time: label,
        balance: point.balance ?? 0,
        equity: point.equity ?? 0,
      };

      const last = prev[prev.length - 1];
      if (last && last.time === nextPoint.time && last.balance === nextPoint.balance && last.equity === nextPoint.equity) {
        return prev;
      }

      return [...prev.slice(-59), nextPoint];
    });
  };

  const applySnapshot = (payload: any) => {
    const snapshot = normalizeSnapshot(payload);
    setDashboard(snapshot);
    setLastUpdated(snapshot.timestamp || new Date().toISOString());
    appendEquityPoint(snapshot);
  };

  const fetchDashboard = async () => {
    setRefreshing(true);
    try {
      const response = await fetch(`${apiBase}/dashboard/live?t=${Date.now()}`, {
        cache: 'no-store',
      });

      if (!response.ok) {
        throw new Error(`Dashboard request failed with ${response.status}`);
      }

      const data = await response.json();
      applySnapshot(data);
      setTransportMode((prev) => (prev === 'offline' ? 'polling' : prev));
    } finally {
      setRefreshing(false);
    }
  };

  const stopPolling = () => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = () => {
    if (pollRef.current !== null) return;
    pollRef.current = window.setInterval(() => {
      fetchDashboard().catch((error) => {
        console.error('Erro ao atualizar dashboard:', error);
      });
    }, 5000);
  };

  useEffect(() => {
    if (activeTab !== 'dashboard') {
      stopPolling();
      wsRef.current?.close();
      wsRef.current = null;
      setTransportMode('offline');
      return;
    }

    let cancelled = false;

    const connectDashboardStream = () => {
      try {
        const wsUrl = `${wsBase}/ws/dashboard`;
        const socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (cancelled) return;
          setTransportMode('websocket');
          stopPolling();
        };

        socket.onmessage = (event) => {
          if (cancelled) return;
          try {
            applySnapshot(JSON.parse(event.data));
            setTransportMode('websocket');
          } catch (error) {
            console.error('Erro ao processar snapshot do dashboard:', error);
          }
        };

        socket.onerror = () => {
          if (cancelled) return;
          setTransportMode('polling');
          startPolling();
        };

        socket.onclose = () => {
          if (cancelled) return;
          setTransportMode('polling');
          startPolling();
        };
      } catch (error) {
        console.error('Falha ao abrir WebSocket do dashboard:', error);
        setTransportMode('polling');
        startPolling();
      }
    };

    fetchDashboard().catch((error) => {
      console.error('Erro ao carregar dashboard:', error);
      setTransportMode('polling');
      startPolling();
    });

    connectDashboardStream();

    return () => {
      cancelled = true;
      stopPolling();
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [activeTab, apiBase, wsBase]);

  const dashboardCards = [
    {
      id: 'live_total_pnl' as IndicatorKey,
      label: 'PnL ao vivo',
      value: `R$ ${formatMoney(dashboard.live_total_pnl)}`,
      delta: `R$ ${formatMoney(dashboard.floating_pnl)}`,
      deltaLabel: 'flutuante',
      isPositive: (dashboard.live_total_pnl ?? 0) >= 0,
    },
    {
      id: 'daily_pnl' as IndicatorKey,
      label: 'PnL diário',
      value: `R$ ${formatMoney(dashboard.daily_pnl)}`,
      delta: `R$ ${formatMoney(dashboard.daily_realized_pnl)}`,
      deltaLabel: 'realizado',
      isPositive: (dashboard.daily_pnl ?? 0) >= 0,
    },
    {
      id: 'account_equity' as IndicatorKey,
      label: 'Equity',
      value: `R$ ${formatMoney(dashboard.account_equity)}`,
      delta: `R$ ${formatMoney(dashboard.account_balance)}`,
      deltaLabel: 'saldo',
      isPositive: (dashboard.account_equity ?? 0) >= 0,
    },
    {
      id: 'account_balance' as IndicatorKey,
      label: 'Saldo',
      value: `R$ ${formatMoney(dashboard.account_balance)}`,
      delta: `R$ ${formatMoney(dashboard.account_profit)}`,
      deltaLabel: 'lucro aberto',
      isPositive: (dashboard.account_balance ?? 0) >= 0,
    },
    {
      id: 'floating_pnl' as IndicatorKey,
      label: 'PnL flutuante',
      value: `R$ ${formatMoney(dashboard.floating_pnl)}`,
      delta: `${dashboard.open_positions ?? 0}`,
      deltaLabel: 'posições',
      isPositive: (dashboard.floating_pnl ?? 0) >= 0,
    },
    {
      id: 'account_free_margin' as IndicatorKey,
      label: 'Margem livre',
      value: `R$ ${formatMoney(dashboard.account_free_margin)}`,
      delta: `R$ ${formatMoney(dashboard.account_margin)}`,
      deltaLabel: 'margem',
      isPositive: (dashboard.account_free_margin ?? 0) >= 0,
    },
    {
      id: 'open_positions' as IndicatorKey,
      label: 'Posições abertas',
      value: `${dashboard.open_positions ?? 0}`,
      delta: `${dashboard.total_trades ?? 0}`,
      deltaLabel: 'eventos',
      isPositive: (dashboard.open_positions ?? 0) >= 0,
    },
    {
      id: 'symbol_spread' as IndicatorKey,
      label: 'Spread',
      value: `${(dashboard.symbol_spread ?? 0).toFixed(1)}`,
      delta: dashboard.symbol || 'ativo',
      deltaLabel: 'mercado',
      isPositive: false,
    },
    {
      id: 'win_rate' as IndicatorKey,
      label: 'Win rate',
      value: `${(dashboard.win_rate ?? 0).toFixed(1)}%`,
      delta: `${dashboard.closed_trades ?? 0}`,
      deltaLabel: 'fechados',
      isPositive: (dashboard.win_rate ?? 0) >= 50,
    },
    {
      id: 'max_drawdown' as IndicatorKey,
      label: 'Drawdown',
      value: `R$ ${formatMoney(dashboard.max_drawdown)}`,
      delta: 'risco',
      deltaLabel: 'controle',
      isPositive: false,
    },
    {
      id: 'active_bots' as IndicatorKey,
      label: 'Bots ativos',
      value: `${dashboard.active_bots ?? 0}`,
      delta: dashboard.mt5_connected ? 'MT5 ON' : 'MT5 OFF',
      deltaLabel: dashboard.terminal_name || 'terminal',
      isPositive: (dashboard.active_bots ?? 0) > 0,
    },
    {
      id: 'total_candles' as IndicatorKey,
      label: 'Velas no banco',
      value: `${(dashboard.total_candles ?? 0).toLocaleString('pt-BR')}`,
      delta: formatDuration(dashboard.bridge_uptime_seconds),
      deltaLabel: 'bridge',
      isPositive: (dashboard.total_candles ?? 0) > 0,
    },
    {
      id: 'daily_realized_pnl' as IndicatorKey,
      label: 'PnL realizado',
      value: `R$ ${formatMoney(dashboard.daily_realized_pnl)}`,
      delta: `${dashboard.total_trades ?? 0}`,
      deltaLabel: 'trades',
      isPositive: (dashboard.daily_realized_pnl ?? 0) >= 0,
    },
    {
      id: 'historical_daily_pnl' as IndicatorKey,
      label: 'PnL histórico',
      value: `R$ ${formatMoney(dashboard.historical_daily_pnl ?? dashboard.daily_realized_pnl)}`,
      delta: `${dashboard.closed_trades ?? 0}`,
      deltaLabel: 'fechados',
      isPositive: (dashboard.historical_daily_pnl ?? 0) >= 0,
    },
    {
      id: 'account_margin' as IndicatorKey,
      label: 'Margem usada',
      value: `R$ ${formatMoney(dashboard.account_margin)}`,
      delta: `R$ ${formatMoney(dashboard.account_free_margin)}`,
      deltaLabel: 'livre',
      isPositive: (dashboard.account_margin ?? 0) <= (dashboard.account_balance ?? 0),
    },
    {
      id: 'account_profit' as IndicatorKey,
      label: 'Lucro aberto',
      value: `R$ ${formatMoney(dashboard.account_profit)}`,
      delta: `${dashboard.open_positions ?? 0}`,
      deltaLabel: 'posições',
      isPositive: (dashboard.account_profit ?? 0) >= 0,
    },
    {
      id: 'bridge_uptime_seconds' as IndicatorKey,
      label: 'Uptime da bridge',
      value: formatDuration(dashboard.bridge_uptime_seconds),
      delta: transportMode.toUpperCase(),
      deltaLabel: dashboard.mt5_connected ? 'online' : 'offline',
      isPositive: dashboard.mt5_connected ?? false,
    },
    {
      id: 'mt5_connected' as IndicatorKey,
      label: 'Conexão MT5',
      value: dashboard.mt5_connected ? 'ONLINE' : 'OFFLINE',
      delta: dashboard.account_login ? `Conta ${dashboard.account_login}` : 'sem conta',
      deltaLabel: dashboard.account_server || 'terminal',
      isPositive: dashboard.mt5_connected ?? false,
    },
  ];

  const toggleIndicator = (id: IndicatorKey) => {
    setIndicatorPrefs((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const setAllIndicators = (visible: boolean) => {
    const next = DASHBOARD_INDICATORS.reduce((acc, item) => {
      acc[item.id] = visible;
      return acc;
    }, {} as Record<IndicatorKey, boolean>);
    setIndicatorPrefs(next);
  };

  const resetIndicators = () => {
    setIndicatorPrefs(buildDefaultIndicatorPrefs());
  };

  const visibleCards = dashboardCards.filter((card) => indicatorPrefs[card.id]);
  const chartData = equityData.length > 0 ? equityData : [];
  const recentTrades = dashboard.recent_trades || [];
  const openPositions = dashboard.open_positions_detail || [];
  const updatedAtLabel = lastUpdated ? new Date(lastUpdated).toLocaleString('pt-BR') : '--';

  return (
    <div className="flex bg-bg-dark text-white min-h-screen font-sans">
      <NotificationOverlay />
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 overflow-y-auto p-8">
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            <header className="mb-6 flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="px-3 py-1 rounded-full bg-brand-primary/10 text-brand-primary text-[10px] font-black uppercase tracking-[0.3em] flex items-center gap-2">
                    <Activity size={12} />
                    Dashboard ao vivo
                  </span>
                  <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.3em] flex items-center gap-2 ${
                    transportMode === 'websocket'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : transportMode === 'polling'
                        ? 'bg-amber-500/10 text-amber-400'
                        : 'bg-red-500/10 text-red-400'
                  }`}>
                    {transportMode === 'websocket' ? <Wifi size={12} /> : <WifiOff size={12} />}
                    {transportMode === 'websocket' ? 'websocket' : transportMode === 'polling' ? 'polling' : 'offline'}
                  </span>
                  <button
                    onClick={() => fetchDashboard().catch((error) => console.error(error))}
                    className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 text-gray-300 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-white/10 transition-colors"
                  >
                    <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
                    Atualizar agora
                  </button>
                </div>
                <h2 className="text-3xl font-black text-white">Resumo em tempo real da operação</h2>
                <p className="text-gray-400">
                  Última atualização: {updatedAtLabel}
                  {dashboard.symbol ? ` • ${dashboard.symbol}` : ''}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 min-w-[320px]">
                <div className="bg-bg-card border border-border-card rounded-2xl p-4 text-right">
                  <p className="text-[10px] uppercase tracking-widest font-black text-gray-500">MT5</p>
                  <p className={`text-lg font-black ${dashboard.mt5_connected ? 'text-brand-primary' : 'text-red-400'}`}>
                    {dashboard.mt5_connected ? 'Online' : 'Offline'}
                  </p>
                  <p className="text-xs text-white/70">{dashboard.terminal_name || 'Terminal local'}</p>
                </div>
                <div className="bg-bg-card border border-border-card rounded-2xl p-4 text-right">
                  <p className="text-[10px] uppercase tracking-widest font-black text-gray-500">Conta</p>
                  <p className="text-lg font-black text-white">
                    {dashboard.account_login ? dashboard.account_login : '---'}
                  </p>
                  <p className="text-xs text-white/70">{dashboard.account_server || 'Aguardando bridge'}</p>
                </div>
                <div className="bg-bg-card border border-border-card rounded-2xl p-4 text-right">
                  <p className="text-[10px] uppercase tracking-widest font-black text-gray-500">Open PnL</p>
                  <p className={`text-lg font-black ${(dashboard.floating_pnl ?? 0) >= 0 ? 'text-brand-primary' : 'text-red-400'}`}>
                    R$ {formatMoney(dashboard.floating_pnl)}
                  </p>
                  <p className="text-xs text-white/70">{dashboard.open_positions ?? 0} posições</p>
                </div>
              </div>
            </header>

            <div className="bg-bg-card border border-border-card rounded-3xl p-5 space-y-4">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Settings size={16} className="text-brand-primary" />
                    <h3 className="text-lg font-black text-white">Indicadores do painel</h3>
                  </div>
                  <p className="text-sm text-gray-400">Ligue ou desligue os blocos que quer acompanhar.</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setAllIndicators(true)}
                    className="px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] bg-white/5 text-gray-300 hover:bg-white/10 transition-colors"
                  >
                    Mostrar tudo
                  </button>
                  <button
                    onClick={resetIndicators}
                    className="px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-[0.2em] bg-brand-primary/10 text-brand-primary hover:bg-brand-primary/20 transition-colors"
                  >
                    Padrão
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {DASHBOARD_INDICATORS.map((indicator) => {
                  const enabled = indicatorPrefs[indicator.id];
                  return (
                    <button
                      key={indicator.id}
                      onClick={() => toggleIndicator(indicator.id)}
                      className={`inline-flex items-center gap-2 px-3 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border transition-all ${
                        enabled
                          ? 'bg-brand-primary/10 text-brand-primary border-brand-primary/30'
                          : 'bg-white/5 text-gray-500 border-white/10 hover:text-gray-300'
                      }`}
                    >
                      <Eye size={12} />
                      {indicator.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
              {visibleCards.map((card) => (
                <MetricCard
                  key={card.id}
                  label={card.label}
                  value={card.value}
                  delta={card.delta}
                  deltaLabel={card.deltaLabel}
                  isPositive={card.isPositive}
                />
              ))}
            </div>

            <div className="bg-bg-card border border-border-card p-6 rounded-3xl h-[420px] min-w-0">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
                <div>
                  <h3 className="text-xl font-bold text-white">Curva de Equity ao vivo</h3>
                  <p className="text-sm text-gray-400">A linha acompanha cada snapshot recebido do MT5.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="bg-brand-primary/10 text-brand-primary px-3 py-1 rounded-full text-xs font-bold ring-1 ring-brand-primary/30">
                    Live
                  </span>
                  <span className="bg-gray-800 text-gray-400 px-3 py-1 rounded-full text-xs font-bold">
                    {equityData.length} pontos
                  </span>
                </div>
              </div>

              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2d333f" vertical={false} />
                    <XAxis dataKey="time" stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `R$ ${Math.round(Number(val))}`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#161a23', border: '1px solid #2d333f', borderRadius: '12px' }}
                      formatter={(value: any, name: any) => [
                        `R$ ${formatMoney(Number(value))}`,
                        name === 'equity' ? 'Equity' : 'Saldo',
                      ]}
                    />
                    <Line type="monotone" dataKey="equity" stroke="#00ffb2" strokeWidth={3} dot={false} />
                    <Line type="monotone" dataKey="balance" stroke="#60a5fa" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-gray-600 italic">
                  Aguardando snapshots para montar a curva de equity...
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-bg-card border border-border-card p-6 rounded-3xl">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-white">Movimentações recentes</h3>
                  <span className="text-xs text-gray-500 uppercase tracking-[0.2em] font-black">
                    {recentTrades.length} itens
                  </span>
                </div>

                <div className="overflow-x-auto">
                  {recentTrades.length > 0 ? (
                    <table className="w-full">
                      <thead>
                        <tr className="text-left text-gray-500 text-sm border-b border-border-card">
                          <th className="pb-4 font-medium">Ativo</th>
                          <th className="pb-4 font-medium">Direção</th>
                          <th className="pb-4 font-medium">Evento</th>
                          <th className="pb-4 font-medium">Preço</th>
                          <th className="pb-4 font-medium">PnL</th>
                        </tr>
                      </thead>
                      <tbody className="text-sm">
                        {recentTrades.map((trade: any) => {
                          const profit = Number(trade.profit ?? trade.pnl ?? 0);
                          const side = String(trade.direction ?? trade.type ?? '').toLowerCase();
                          const status = String(trade.status ?? trade.entry ?? 'open').toLowerCase();
                          const price = trade.price ?? trade.entry_price ?? trade.price_open;
                          const time = trade.time ?? trade.open_time ?? trade.close_time;

                          return (
                            <tr key={trade.id ?? `${trade.symbol}-${time}`} className="border-b border-border-card/50 last:border-0">
                              <td className="py-4 font-bold text-gray-200">{trade.symbol ?? dashboard.symbol ?? '---'}</td>
                              <td className="py-4">
                                <span
                                  className={`px-2 py-1 rounded-md text-xs font-bold uppercase ${
                                    side === 'buy'
                                      ? 'bg-brand-primary/10 text-brand-primary'
                                      : side === 'sell'
                                        ? 'bg-red-500/10 text-red-500'
                                        : 'bg-gray-700 text-gray-300'
                                  }`}
                                >
                                  {side || 'n/a'}
                                </span>
                              </td>
                              <td className="py-4">
                                <span
                                  className={`px-2 py-1 rounded-md text-xs font-bold uppercase ${
                                    status === 'closed'
                                      ? 'bg-emerald-500/10 text-emerald-400'
                                      : status === 'open'
                                        ? 'bg-sky-500/10 text-sky-400'
                                        : 'bg-gray-700 text-gray-300'
                                  }`}
                                >
                                  {status}
                                </span>
                              </td>
                              <td className="py-4 font-mono text-gray-400">{price ?? '---'}</td>
                              <td className={`py-4 font-bold ${profit >= 0 ? 'text-brand-primary' : 'text-red-500'}`}>
                                {profit >= 0 ? '+' : ''}R$ {formatMoney(profit)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  ) : (
                    <div className="text-center py-8 text-gray-500">Nenhuma movimentação recente disponível.</div>
                  )}
                </div>
              </div>

              <div className="space-y-6">
                <div className="bg-gradient-to-br from-brand-primary/10 to-brand-secondary/10 border border-brand-primary/20 p-6 rounded-3xl">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xl font-black flex items-center gap-2">
                      <Brain className="text-brand-primary" />
                      Status da IA
                    </h3>
                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-primary">
                      {dashboard.active_bots ?? 0} ativos
                    </span>
                  </div>
                  <p className="text-gray-300 leading-relaxed italic">
                    {dashboard.active_bots && dashboard.active_bots > 0
                      ? 'Motores neurais ativos e acompanhando o mercado em tempo real.'
                      : 'Aguardando bots ativos para gerar fluxo ao vivo.'}
                  </p>
                  <div className="mt-6">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-bold text-gray-400">Conexão MT5</span>
                      <span className={`text-sm font-black ${dashboard.mt5_connected ? 'text-brand-primary' : 'text-red-400'}`}>
                        {dashboard.mt5_connected ? 'CONECTADO' : 'DESCONECTADO'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${dashboard.mt5_connected ? 'bg-brand-primary' : 'bg-red-500'}`}
                        style={{ width: dashboard.mt5_connected ? '100%' : '18%' }}
                      />
                    </div>
                  </div>
                </div>

                <div className="bg-bg-card border border-border-card p-6 rounded-3xl">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-bold text-white">Posições ao vivo</h3>
                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">
                      {openPositions.length} abertas
                    </span>
                  </div>
                  {openPositions.length > 0 ? (
                    <div className="space-y-3 max-h-[240px] overflow-y-auto pr-1">
                      {openPositions.map((position: any) => (
                        <div key={position.ticket ?? `${position.symbol}-${position.time}`} className="bg-white/5 rounded-2xl p-3 border border-white/5">
                          <div className="flex items-center justify-between">
                            <span className="font-black text-white">{position.symbol || dashboard.symbol}</span>
                            <span className={`text-[10px] font-black uppercase ${String(position.direction).toLowerCase() === 'buy' ? 'text-brand-primary' : 'text-red-400'}`}>
                              {position.direction}
                            </span>
                          </div>
                          <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-400">
                            <span>Ticket: {position.ticket ?? '---'}</span>
                            <span>Volume: {position.volume ?? '---'}</span>
                            <span>Entrada: {position.price_open ?? '---'}</span>
                            <span>PnL: {position.profit ?? 0}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-gray-500 italic">Sem posições abertas no momento.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'bots' && <Bots />}
        {activeTab === 'logs' && <BotLogs />}
        {activeTab === 'trades' && <Trades />}
        {activeTab === 'news' && <NewsAI />}
        {activeTab === 'backtesting' && <Backtesting />}
      </main>
    </div>
  );
}

export default App;
