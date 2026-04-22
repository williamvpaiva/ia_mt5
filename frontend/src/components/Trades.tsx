import { useEffect, useState } from 'react';
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Bot as BotIcon,
  Clock3,
  Filter,
  RefreshCw,
  Search,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { MetricCard } from './MetricCard';

type DashboardTrade = Record<string, any>;

type DashboardPosition = Record<string, any>;

type BotItem = {
  id: number;
  name: string;
  symbol?: string | null;
  magic_number?: number | null;
  timeframe?: string | null;
  active?: boolean | null;
};

type TradeStats = {
  total_trades: number;
  open_trades: number;
  closed_trades: number;
  total_pnl: number;
  win_rate: number;
  avg_profit: number;
  avg_loss: number;
  profit_factor: number;
  max_drawdown: number;
  sharpe_ratio: number;
};

type DashboardSnapshot = {
  timestamp?: string;
  symbol?: string;
  mt5_connected?: boolean;
  terminal_connected?: boolean;
  bridge_status?: string;
  bridge_last_error?: string | null;
  bridge_uptime_seconds?: number;
  terminal_name?: string | null;
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
  running_bots?: number;
  paused_bots?: number;
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
  metrics_source?: string;
  recent_trades?: DashboardTrade[];
  open_positions_detail?: DashboardPosition[];
};

type OperationScope = 'live' | 'history' | 'all';
type DirectionFilter = 'all' | 'buy' | 'sell';
type StatusFilter = 'all' | 'open' | 'closed';
type OperationSource = 'live' | 'position' | 'database';

type OperationRow = {
  key: string;
  source: OperationSource;
  sourceLabel: string;
  status: 'open' | 'closed' | 'pending' | 'unknown';
  statusLabel: string;
  eventLabel: string;
  botName: string;
  botId?: number | null;
  magicNumber?: number | null;
  symbol: string;
  direction: 'buy' | 'sell' | 'unknown';
  volume?: number | null;
  entryPrice?: number | null;
  exitPrice?: number | null;
  pnl?: number | null;
  time?: string | number | null;
  ticket?: number | string | null;
  comment?: string | null;
};

const DEFAULT_DASHBOARD: DashboardSnapshot = {
  mt5_connected: false,
  bridge_status: 'degraded',
  bridge_uptime_seconds: 0,
  total_pnl: 0,
  live_total_pnl: 0,
  daily_pnl: 0,
  daily_realized_pnl: 0,
  floating_pnl: 0,
  win_rate: 0,
  max_drawdown: 0,
  active_bots: 0,
  running_bots: 0,
  paused_bots: 0,
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
  metrics_source: 'mt5_live',
};

const normalizeText = (value: any) => String(value ?? '').trim().toLowerCase();

const normalizeNumber = (value: any) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const toNullableNumber = (value: any) => {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const formatMoney = (value?: number | null) =>
  (value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const formatPrice = (value?: number | null) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '---';
  }

  return Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

const parseTimestamp = (value?: string | number | null) => {
  if (value === null || value === undefined || value === '') return null;

  if (typeof value === 'number') {
    return value > 1_000_000_000_000 ? value : value * 1000;
  }

  const raw = String(value).trim();
  if (!raw) return null;

  if (/^\d+$/.test(raw)) {
    const numeric = Number(raw);
    return numeric > 1_000_000_000_000 ? numeric : numeric * 1000;
  }

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return null;
  return date.getTime();
};

const formatDateTime = (value?: string | number | null) => {
  const timestamp = parseTimestamp(value);
  if (timestamp === null) return '--';
  return new Date(timestamp).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' });
};

const formatTime = (value?: string | number | null) => {
  const timestamp = parseTimestamp(value);
  if (timestamp === null) return '--:--:--';
  return new Date(timestamp).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

const formatDirectionLabel = (value: string) => {
  if (value === 'buy') return 'COMPRA';
  if (value === 'sell') return 'VENDA';
  return '---';
};

const formatStatusLabel = (value: OperationRow['status']) => {
  if (value === 'open') return 'Aberta';
  if (value === 'closed') return 'Fechada';
  if (value === 'pending') return 'Pendente';
  return 'Indefinida';
};

const formatSourceLabel = (value: OperationSource) => {
  if (value === 'live') return 'Tempo real';
  if (value === 'position') return 'Posição';
  return 'Banco';
};

const normalizeDirection = (value: any): 'buy' | 'sell' | 'unknown' => {
  const text = normalizeText(value);

  if (value === 0 || text === '0' || text === 'buy' || text === 'compra') return 'buy';
  if (value === 1 || text === '1' || text === 'sell' || text === 'venda') return 'sell';

  return 'unknown';
};

const normalizeEntry = (value: any) => {
  const text = normalizeText(value);
  if (text === 'in' || text === 'entrada' || text === 'open') return 'in';
  if (text === 'out' || text === 'saida' || text === 'saída' || text === 'close') return 'out';
  if (text === 'out_by' || text === 'inout') return text;
  return text || 'unknown';
};

const buildDashboardDefaults = (payload: any): DashboardSnapshot => {
  const source = payload?.data ?? payload ?? {};

  return {
    ...DEFAULT_DASHBOARD,
    ...source,
    recent_trades: Array.isArray(source.recent_trades) ? source.recent_trades : [],
    open_positions_detail: Array.isArray(source.open_positions_detail) ? source.open_positions_detail : [],
  };
};

const buildBotLookup = (bots: BotItem[]) => {
  const byId: Record<number, BotItem> = {};
  const byMagic: Record<number, BotItem> = {};

  bots.forEach((bot) => {
    byId[bot.id] = bot;
    if (bot.magic_number !== null && bot.magic_number !== undefined) {
      byMagic[bot.magic_number] = bot;
    }
  });

  return { byId, byMagic };
};

const resolveBotName = (
  botId: number | null | undefined,
  magicNumber: number | null | undefined,
  symbol: string | undefined,
  botLookup: { byId: Record<number, BotItem>; byMagic: Record<number, BotItem> },
) => {
  if (botId !== null && botId !== undefined && botLookup.byId[botId]) {
    return botLookup.byId[botId].name;
  }

  if (magicNumber !== null && magicNumber !== undefined && botLookup.byMagic[magicNumber]) {
    return botLookup.byMagic[magicNumber].name;
  }

  if (symbol) {
    return symbol;
  }

  if (botId !== null && botId !== undefined) {
    return `Bot #${botId}`;
  }

  if (magicNumber !== null && magicNumber !== undefined) {
    return `MG ${magicNumber}`;
  }

  return 'Bot nao mapeado';
};

const toOperationRow = (
  item: DashboardTrade | DashboardPosition | Record<string, any>,
  source: OperationSource,
  botLookup: { byId: Record<number, BotItem>; byMagic: Record<number, BotItem> },
  fallbackSymbol?: string,
): OperationRow => {
  const symbol = String(item.symbol || fallbackSymbol || '---');
  const botId = item.bot_id !== undefined ? Number(item.bot_id) : null;
  const magicNumber =
    item.magic !== undefined
      ? Number(item.magic)
      : item.magic_number !== undefined
        ? Number(item.magic_number)
        : null;
  const direction = normalizeDirection(item.direction ?? item.type);
  const sourceLabel = formatSourceLabel(source);
  const comment = item.comment ?? null;

  if (source === 'position') {
    return {
      key: `position-${item.ticket ?? item.symbol ?? symbol}-${item.time ?? item.price_open ?? Math.random()}`,
      source,
      sourceLabel,
      status: 'open',
      statusLabel: formatStatusLabel('open'),
      eventLabel: 'Posição aberta',
      botName: resolveBotName(botId, magicNumber, symbol, botLookup),
      botId,
      magicNumber,
      symbol,
      direction,
      volume: toNullableNumber(item.volume),
      entryPrice: toNullableNumber(item.price_open),
      exitPrice: null,
      pnl: toNullableNumber(item.profit),
      time: item.time ?? null,
      ticket: item.ticket ?? null,
      comment,
    };
  }

  if (source === 'database') {
    const isClosed = Boolean(item.close_time);
    return {
      key: `db-${item.id ?? item.ticket ?? `${symbol}-${item.open_time}`}`,
      source,
      sourceLabel,
      status: isClosed ? 'closed' : 'open',
      statusLabel: formatStatusLabel(isClosed ? 'closed' : 'open'),
      eventLabel: isClosed ? 'Fechada' : 'Aberta',
      botName: resolveBotName(botId, magicNumber, symbol, botLookup),
      botId,
      magicNumber,
      symbol,
      direction,
      volume: toNullableNumber(item.volume),
      entryPrice: toNullableNumber(item.entry_price ?? item.open_price),
      exitPrice: toNullableNumber(item.exit_price ?? item.close_price),
      pnl: toNullableNumber(item.profit ?? item.pnl),
      time: item.close_time || item.open_time || null,
      ticket: item.ticket ?? null,
      comment,
    };
  }

  const entry = normalizeEntry(item.entry);
  const isClosed = entry === 'out' || entry === 'out_by' || entry === 'inout' || item.status === 'closed';
  const isOpen = entry === 'in' || item.status === 'open';

  return {
    key: `live-${item.id ?? item.ticket ?? item.order ?? `${symbol}-${item.time ?? Math.random()}`}`,
    source: 'live',
    sourceLabel,
    status: isClosed ? 'closed' : isOpen ? 'open' : 'pending',
    statusLabel: formatStatusLabel(isClosed ? 'closed' : isOpen ? 'open' : 'pending'),
    eventLabel: entry === 'out' || entry === 'out_by' || entry === 'inout' ? 'Saída' : 'Entrada',
    botName: resolveBotName(botId, magicNumber, symbol, botLookup),
    botId,
    magicNumber,
    symbol,
    direction,
    volume: toNullableNumber(item.volume),
    entryPrice: toNullableNumber(item.price ?? item.entry_price),
    exitPrice: isClosed ? toNullableNumber(item.price ?? item.exit_price) : null,
    pnl: toNullableNumber(item.profit ?? item.pnl),
    time: item.time ?? item.open_time ?? item.close_time ?? null,
    ticket: item.ticket ?? item.order ?? item.position_id ?? null,
    comment,
  };
};

const formatSignedMoney = (value?: number | null) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '---';
  }

  const numeric = Number(value);
  const amount = Math.abs(numeric);
  const prefix = numeric > 0 ? '+' : numeric < 0 ? '-' : '';
  return `${prefix}R$ ${formatMoney(amount)}`;
};

export const Trades: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardSnapshot>(DEFAULT_DASHBOARD);
  const [tradeStats, setTradeStats] = useState<TradeStats>({
    total_trades: 0,
    open_trades: 0,
    closed_trades: 0,
    total_pnl: 0,
    win_rate: 0,
    avg_profit: 0,
    avg_loss: 0,
    profit_factor: 0,
    max_drawdown: 0,
    sharpe_ratio: 0,
  });
  const [dbTrades, setDbTrades] = useState<Record<string, any>[]>([]);
  const [bots, setBots] = useState<BotItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [scope, setScope] = useState<OperationScope>('live');
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [selectedBot, setSelectedBot] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

  const fetchJson = async (endpoint: string) => {
    const separator = endpoint.includes('?') ? '&' : '?';
    const response = await fetch(`${apiUrl}${endpoint}${separator}t=${Date.now()}`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`Falha ao buscar ${endpoint} (${response.status})`);
    }

    return response.json();
  };

  const refreshData = async (manual = false) => {
    if (manual) {
      setRefreshing(true);
    }

    try {
      const [liveResult, statsResult, tradesResult, botsResult] = await Promise.allSettled([
        fetchJson('/dashboard/live'),
        fetchJson('/trades/stats/summary?days=30'),
        fetchJson('/trades/?limit=200'),
        fetchJson('/bots/'),
      ]);

      if (liveResult.status === 'fulfilled') {
        setDashboard(buildDashboardDefaults(liveResult.value));
        setLastUpdated(new Date().toISOString());
      }

      if (statsResult.status === 'fulfilled') {
        const nextStats = statsResult.value ?? {};
        setTradeStats({
          total_trades: normalizeNumber(nextStats.total_trades),
          open_trades: normalizeNumber(nextStats.open_trades),
          closed_trades: normalizeNumber(nextStats.closed_trades),
          total_pnl: normalizeNumber(nextStats.total_pnl),
          win_rate: normalizeNumber(nextStats.win_rate),
          avg_profit: normalizeNumber(nextStats.avg_profit),
          avg_loss: normalizeNumber(nextStats.avg_loss),
          profit_factor: normalizeNumber(nextStats.profit_factor),
          max_drawdown: normalizeNumber(nextStats.max_drawdown),
          sharpe_ratio: normalizeNumber(nextStats.sharpe_ratio),
        });
      }

      if (tradesResult.status === 'fulfilled') {
        setDbTrades(Array.isArray(tradesResult.value) ? tradesResult.value : []);
      }

      if (botsResult.status === 'fulfilled') {
        setBots(Array.isArray(botsResult.value) ? botsResult.value : []);
      }
    } catch (error) {
      console.error('Erro ao atualizar Operacoes:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    refreshData(false);
    const interval = window.setInterval(() => {
      refreshData(false).catch((error) => {
        console.error('Falha no refresh automatico das Operacoes:', error);
      });
    }, 10000);

    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const botLookup = buildBotLookup(bots);
  const recentLiveRows = (dashboard.recent_trades || []).map((trade) => toOperationRow(trade, 'live', botLookup, dashboard.symbol));
  const openPositionRows = (dashboard.open_positions_detail || []).map((position) => toOperationRow(position, 'position', botLookup, dashboard.symbol));
  const historyRows = dbTrades.map((trade) => toOperationRow(trade, 'database', botLookup, dashboard.symbol));

  const allRows = scope === 'live' ? [...recentLiveRows, ...openPositionRows] : scope === 'history' ? historyRows : [...recentLiveRows, ...openPositionRows, ...historyRows];

  const botOptions = Array.from(
    new Set([
      ...bots.map((bot) => bot.name),
      ...allRows.map((row) => row.botName),
    ]),
  )
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b, 'pt-BR'));

  const filteredRows = allRows
    .filter((row) => {
      const term = normalizeText(searchTerm);
      if (!term) return true;

      return (
        normalizeText(row.symbol).includes(term) ||
        normalizeText(row.botName).includes(term) ||
        normalizeText(row.comment).includes(term) ||
        normalizeText(row.ticket).includes(term) ||
        normalizeText(row.eventLabel).includes(term) ||
        normalizeText(row.statusLabel).includes(term) ||
        normalizeText(row.sourceLabel).includes(term)
      );
    })
    .filter((row) => {
      if (directionFilter === 'all') return true;
      return row.direction === directionFilter;
    })
    .filter((row) => {
      if (statusFilter === 'all') return true;
      return row.status === statusFilter;
    })
    .filter((row) => {
      if (selectedBot === 'all') return true;
      return row.botName === selectedBot;
    })
    .sort((a, b) => (parseTimestamp(b.time) ?? 0) - (parseTimestamp(a.time) ?? 0));

  const liveSourceRows = [...recentLiveRows, ...openPositionRows].sort((a, b) => (parseTimestamp(b.time) ?? 0) - (parseTimestamp(a.time) ?? 0));
  const latestRow = liveSourceRows[0] || historyRows[0];
  const latestLiveEvent = recentLiveRows[0];
  const updatedAtLabel = lastUpdated ? new Date(lastUpdated).toLocaleString('pt-BR') : '--';
  const dataAgeSeconds = lastUpdated ? Math.max(0, Math.floor((Date.now() - new Date(lastUpdated).getTime()) / 1000)) : null;
  const isMt5Healthy = Boolean(dashboard.mt5_connected) && dashboard.bridge_status !== 'degraded';
  const hasHistory = tradeStats.total_trades > 0;

  const topMetrics = [
    {
      label: 'PnL ao vivo',
      value: `R$ ${formatMoney(dashboard.live_total_pnl)}`,
      delta: `R$ ${formatMoney(dashboard.floating_pnl)}`,
      deltaLabel: 'flutuante',
      isPositive: (dashboard.live_total_pnl ?? 0) >= 0,
    },
    {
      label: 'PnL do dia',
      value: `R$ ${formatMoney(dashboard.daily_pnl)}`,
      delta: `R$ ${formatMoney(dashboard.daily_realized_pnl)}`,
      deltaLabel: 'realizado',
      isPositive: (dashboard.daily_pnl ?? 0) >= 0,
    },
    {
      label: 'Win rate',
      value: `${(dashboard.win_rate ?? 0).toFixed(1)}%`,
      delta: `${dashboard.closed_trades ?? 0}`,
      deltaLabel: 'fechadas',
      isPositive: (dashboard.win_rate ?? 0) >= 50,
    },
    {
      label: 'Posições abertas',
      value: `${dashboard.open_positions ?? 0}`,
      delta: `${dashboard.running_bots ?? 0}`,
      deltaLabel: 'bots rodando',
      isPositive: (dashboard.open_positions ?? 0) >= 0,
    },
    {
      label: 'Margem livre',
      value: `R$ ${formatMoney(dashboard.account_free_margin)}`,
      delta: `R$ ${formatMoney(dashboard.account_margin)}`,
      deltaLabel: 'usada',
      isPositive: (dashboard.account_free_margin ?? 0) >= 0,
    },
    {
      label: 'Conexão MT5',
      value: dashboard.mt5_connected ? 'ONLINE' : 'OFFLINE',
      delta: dashboard.bridge_status || 'desconhecido',
      deltaLabel: formatDuration(dashboard.bridge_uptime_seconds),
      isPositive: dashboard.mt5_connected ?? false,
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="px-3 py-1 rounded-full bg-brand-primary/10 text-brand-primary text-[10px] font-black uppercase tracking-[0.3em] flex items-center gap-2">
              <Activity size={12} />
              Operações ao vivo
            </span>
            <span
              className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.3em] flex items-center gap-2 ${
                isMt5Healthy ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
              }`}
            >
              {isMt5Healthy ? <Wifi size={12} /> : <WifiOff size={12} />}
              {isMt5Healthy ? 'MT5 online' : 'MT5 offline'}
            </span>
            <button
              onClick={() => refreshData(true)}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 text-gray-300 text-[10px] font-black uppercase tracking-[0.2em] hover:bg-white/10 transition-colors"
            >
              <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
              Atualizar agora
            </button>
          </div>

          <h2 className="text-3xl font-black text-white">Operações atualizadas em tempo real</h2>
          <p className="text-gray-400 max-w-3xl">
            A tela agora prioriza o snapshot vivo do MT5, mas continua mostrando o histórico do banco para comparação e auditoria.
          </p>
          <div className="flex flex-wrap gap-3 text-xs text-gray-500">
            <span>Ultima sincronização: {updatedAtLabel}</span>
            {dataAgeSeconds !== null && <span>Dados atualizados ha {dataAgeSeconds}s</span>}
            <span>Fonte principal: {dashboard.metrics_source === 'mt5_live+db' ? 'MT5 + banco' : 'MT5 ao vivo'}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 min-w-[340px]">
          <div className="bg-bg-card border border-border-card rounded-2xl p-4 text-right">
            <p className="text-[10px] uppercase tracking-widest font-black text-gray-500">MT5</p>
            <p className={`text-lg font-black ${dashboard.mt5_connected ? 'text-brand-primary' : 'text-red-400'}`}>
              {dashboard.mt5_connected ? 'Online' : 'Offline'}
            </p>
            <p className="text-xs text-white/70">{dashboard.terminal_name || 'Terminal local'}</p>
          </div>
          <div className="bg-bg-card border border-border-card rounded-2xl p-4 text-right">
            <p className="text-[10px] uppercase tracking-widest font-black text-gray-500">Conta</p>
            <p className="text-lg font-black text-white">{dashboard.account_login ?? '---'}</p>
            <p className="text-xs text-white/70">{dashboard.account_server || 'Aguardando bridge'}</p>
          </div>
          <div className="bg-bg-card border border-border-card rounded-2xl p-4 text-right">
            <p className="text-[10px] uppercase tracking-widest font-black text-gray-500">Spread</p>
            <p className="text-lg font-black text-white">{(dashboard.symbol_spread ?? 0).toFixed(1)}</p>
            <p className="text-xs text-white/70">{dashboard.symbol || 'Ativo atual'}</p>
          </div>
        </div>
      </div>

      {!isMt5Healthy && (
        <div className="rounded-3xl border border-red-500/30 bg-red-500/10 p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-red-300 mb-2">Atenção</p>
            <h3 className="text-lg font-black text-white">A ponte do MT5 está degradada ou offline</h3>
            <p className="text-sm text-red-100/80 mt-1">
              A tela continua atualizando com o último snapshot, mas as operações ao vivo podem ficar desatualizadas até a conexão voltar.
            </p>
            {dashboard.bridge_last_error && (
              <p className="text-xs text-red-200/70 mt-2 break-words">Ultimo erro: {dashboard.bridge_last_error}</p>
            )}
          </div>
          <button
            onClick={() => refreshData(true)}
            className="px-4 py-3 rounded-2xl bg-red-500 text-white font-black uppercase tracking-[0.2em] text-xs hover:bg-red-400 transition-colors"
          >
            Tentar reconectar
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {topMetrics.map((metric) => (
          <MetricCard
            key={metric.label}
            label={metric.label}
            value={metric.value}
            delta={metric.delta}
            deltaLabel={metric.deltaLabel}
            isPositive={metric.isPositive}
          />
        ))}
      </div>

      {hasHistory && (
        <div className="bg-bg-card border border-border-card rounded-3xl p-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
            <div>
              <h3 className="text-xl font-black text-white">Resumo histórico dos ultimos 30 dias</h3>
              <p className="text-sm text-gray-400">Dados do banco para apoio. O fluxo principal continua vindo do MT5 ao vivo.</p>
            </div>
            <span className="text-[10px] uppercase tracking-[0.2em] font-black text-gray-500">
              {tradeStats.total_trades} operações registradas
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded-2xl border border-white/5 bg-bg-dark/50 p-4">
              <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-2">Total</p>
              <p className="text-2xl font-black text-white">{tradeStats.total_trades}</p>
            </div>
            <div className="rounded-2xl border border-white/5 bg-bg-dark/50 p-4">
              <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-2">PnL</p>
              <p className={`text-2xl font-black ${tradeStats.total_pnl >= 0 ? 'text-brand-primary' : 'text-red-400'}`}>
                R$ {formatMoney(tradeStats.total_pnl)}
              </p>
            </div>
            <div className="rounded-2xl border border-white/5 bg-bg-dark/50 p-4">
              <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-2">Win rate</p>
              <p className="text-2xl font-black text-white">{tradeStats.win_rate.toFixed(1)}%</p>
            </div>
            <div className="rounded-2xl border border-white/5 bg-bg-dark/50 p-4">
              <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-2">Fator de lucro</p>
              <p className="text-2xl font-black text-white">{tradeStats.profit_factor.toFixed(2)}</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-bg-card border border-border-card rounded-3xl p-6 space-y-5">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Filter size={16} className="text-brand-primary" />
                  <h3 className="text-xl font-black text-white">Linha do tempo das operações</h3>
                </div>
                <p className="text-sm text-gray-400">Filtre por fonte, bot, direcao e status. O escopo padrao prioriza o fluxo ao vivo.</p>
              </div>

              <div className="w-full md:w-96 relative">
                <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Buscar por ativo, bot, ticket ou comentario"
                  className="w-full bg-bg-dark border border-border-card rounded-2xl pl-11 pr-4 py-3 text-white outline-none focus:ring-2 ring-brand-primary/40"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {[
                { key: 'live', label: 'Tempo real' },
                { key: 'history', label: 'Historico' },
                { key: 'all', label: 'Tudo' },
              ].map((item) => {
                const active = scope === item.key;
                return (
                  <button
                    key={item.key}
                    onClick={() => setScope(item.key as OperationScope)}
                    className={`px-3 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border transition-all ${
                      active
                        ? 'bg-brand-primary/10 text-brand-primary border-brand-primary/30'
                        : 'bg-white/5 text-gray-500 border-white/10 hover:text-gray-300'
                    }`}
                  >
                    {item.label}
                  </button>
                );
              })}

              <div className="h-8 w-px bg-white/10 self-center mx-1" />

              {[
                { key: 'all', label: 'Todos os status' },
                { key: 'open', label: 'Abertas' },
                { key: 'closed', label: 'Fechadas' },
              ].map((item) => {
                const active = statusFilter === item.key;
                return (
                  <button
                    key={item.key}
                    onClick={() => setStatusFilter(item.key as StatusFilter)}
                    className={`px-3 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border transition-all ${
                      active
                        ? 'bg-brand-primary/10 text-brand-primary border-brand-primary/30'
                        : 'bg-white/5 text-gray-500 border-white/10 hover:text-gray-300'
                    }`}
                  >
                    {item.label}
                  </button>
                );
              })}

              <div className="h-8 w-px bg-white/10 self-center mx-1" />

              {[
                { key: 'all', label: 'Todas as direcoes' },
                { key: 'buy', label: 'Compra' },
                { key: 'sell', label: 'Venda' },
              ].map((item) => {
                const active = directionFilter === item.key;
                return (
                  <button
                    key={item.key}
                    onClick={() => setDirectionFilter(item.key as DirectionFilter)}
                    className={`px-3 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border transition-all ${
                      active
                        ? 'bg-brand-primary/10 text-brand-primary border-brand-primary/30'
                        : 'bg-white/5 text-gray-500 border-white/10 hover:text-gray-300'
                    }`}
                  >
                    {item.label}
                  </button>
                );
              })}

              <select
                value={selectedBot}
                onChange={(e) => setSelectedBot(e.target.value)}
                className="min-w-[220px] bg-bg-dark border border-border-card rounded-full px-4 py-2 text-[10px] font-black uppercase tracking-[0.2em] text-white outline-none"
              >
                <option value="all">Todos os robos</option>
                {botOptions.map((botName) => (
                  <option key={botName} value={botName}>
                    {botName}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] border-b border-border-card/30 bg-bg-dark/20">
                  <th className="px-4 py-4">Operação / Bot</th>
                  <th className="px-4 py-4">Fonte / Evento</th>
                  <th className="px-4 py-4">Direção</th>
                  <th className="px-4 py-4">Entrada</th>
                  <th className="px-4 py-4">Saída / Atual</th>
                  <th className="px-4 py-4 text-right">Resultado</th>
                  <th className="px-4 py-4">Horário</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-28 text-center">
                      <div className="flex flex-col items-center gap-4">
                        <RefreshCw className="animate-spin text-brand-primary" size={40} />
                        <p className="text-xs font-black text-gray-500 uppercase tracking-widest">Sincronizando operacoes...</p>
                      </div>
                    </td>
                  </tr>
                ) : filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-28 text-center text-gray-500 italic">
                      Nenhuma operacao encontrada com os filtros atuais.
                    </td>
                  </tr>
                ) : (
                  filteredRows.map((row) => (
                    <tr key={row.key} className="border-b border-border-card/5 hover:bg-white/[0.02] transition-colors group">
                      <td className="px-4 py-5">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-11 h-11 rounded-2xl flex items-center justify-center border font-black text-[11px] ${
                              row.pnl !== null && row.pnl !== undefined
                                ? row.pnl >= 0
                                  ? 'bg-brand-primary/10 border-brand-primary/20 text-brand-primary'
                                  : 'bg-red-500/10 border-red-500/20 text-red-400'
                                : 'bg-white/5 border-white/10 text-gray-400'
                            }`}
                          >
                            {String(row.symbol || '---').slice(0, 3).toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="font-black text-white text-base truncate">{row.symbol}</p>
                            <p className="text-[10px] font-mono text-gray-500 flex items-center gap-1 uppercase truncate">
                              <BotIcon size={10} />
                              {row.botName}
                              {row.magicNumber !== null && row.magicNumber !== undefined && (
                                <>
                                  <span className="text-gray-700">•</span>
                                  MG {row.magicNumber}
                                </>
                              )}
                              {row.ticket !== null && row.ticket !== undefined && (
                                <>
                                  <span className="text-gray-700">•</span>
                                  Ticket {row.ticket}
                                </>
                              )}
                            </p>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-5">
                        <div className="flex flex-col gap-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`px-2 py-1 rounded-md text-[9px] font-black uppercase tracking-wider border ${
                                row.source === 'live'
                                  ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                                  : row.source === 'position'
                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                    : 'bg-white/5 text-gray-300 border-white/10'
                              }`}
                            >
                              {row.sourceLabel}
                            </span>
                            <span
                              className={`px-2 py-1 rounded-md text-[9px] font-black uppercase tracking-wider border ${
                                row.status === 'open'
                                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                  : row.status === 'closed'
                                    ? 'bg-violet-500/10 text-violet-400 border-violet-500/20'
                                    : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                              }`}
                            >
                              {row.eventLabel}
                            </span>
                          </div>
                          <p className="text-[10px] text-gray-500 uppercase tracking-[0.2em]">{row.statusLabel}</p>
                        </div>
                      </td>

                      <td className="px-4 py-5">
                        <span
                          className={`px-2.5 py-1 rounded-md text-[10px] font-black uppercase tracking-wider ${
                            row.direction === 'buy'
                              ? 'bg-brand-primary text-bg-dark'
                              : row.direction === 'sell'
                                ? 'bg-red-500 text-white'
                                : 'bg-gray-700 text-gray-300'
                          }`}
                        >
                          {formatDirectionLabel(row.direction)}
                        </span>
                      </td>

                      <td className="px-4 py-5 font-mono font-semibold text-gray-300">{formatPrice(row.entryPrice)}</td>

                      <td className="px-4 py-5 font-mono font-semibold text-gray-200">
                        {row.status === 'open' && row.source === 'position' ? 'Em andamento' : formatPrice(row.exitPrice)}
                      </td>

                      <td className="px-4 py-5 text-right">
                        <div className={`flex flex-col items-end font-black text-lg ${normalizeNumber(row.pnl) >= 0 ? 'text-brand-primary' : 'text-red-500'}`}>
                          <span className="flex items-center gap-1">
                            {normalizeNumber(row.pnl) >= 0 ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                            {formatSignedMoney(row.pnl)}
                          </span>
                          <span className="text-[9px] font-black text-gray-600 uppercase tracking-widest mt-0.5">
                            {row.status === 'open' ? 'Operacao em curso' : row.pnl && row.pnl >= 0 ? 'Lucro realizado' : 'Resultado da operacao'}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-5">
                        <div className="flex items-center justify-between gap-4">
                          <div className="text-right">
                            <p className="text-xs font-bold text-gray-300">{formatDateTime(row.time)}</p>
                            <p className="text-[10px] font-mono text-gray-600">{formatTime(row.time)}</p>
                          </div>
                          <Clock3 className="text-gray-800 group-hover:text-brand-primary group-hover:translate-x-1 transition-all" size={18} />
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pt-4 border-t border-border-card/40 text-[10px] font-black uppercase text-gray-500 tracking-widest">
            <div>
              Mostrando {filteredRows.length} de {allRows.length} operacoes
            </div>
            <div className="flex flex-wrap gap-3">
              <span>Tempo real: {liveSourceRows.length}</span>
              <span>Historico: {historyRows.length}</span>
              <span>Atualizacao a cada 10s</span>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-gradient-to-br from-brand-primary/10 to-brand-secondary/10 border border-brand-primary/20 p-6 rounded-3xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xl font-black flex items-center gap-2">
                <Activity className="text-brand-primary" />
                Pulso da sessão
              </h3>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-primary">
                {dashboard.active_bots ?? 0} ativos
              </span>
            </div>
            <p className="text-gray-300 leading-relaxed italic">
              {dashboard.running_bots && dashboard.running_bots > 0
                ? 'O robô está acompanhando o mercado ao vivo e reagindo aos sinais configurados.'
                : 'Nao ha robos em execucao no momento.'}
            </p>

            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <div className="bg-bg-dark/40 border border-white/5 rounded-2xl p-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Fonte</p>
                <p className="font-black text-white">{dashboard.metrics_source === 'mt5_live+db' ? 'MT5 + banco' : 'MT5 ao vivo'}</p>
              </div>
              <div className="bg-bg-dark/40 border border-white/5 rounded-2xl p-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Uptime</p>
                <p className="font-black text-white">{formatDuration(dashboard.bridge_uptime_seconds)}</p>
              </div>
              <div className="bg-bg-dark/40 border border-white/5 rounded-2xl p-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Conta</p>
                <p className="font-black text-white">{dashboard.account_login ?? '---'}</p>
              </div>
              <div className="bg-bg-dark/40 border border-white/5 rounded-2xl p-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Servidor</p>
                <p className="font-black text-white truncate">{dashboard.account_server || '---'}</p>
              </div>
            </div>
          </div>

          <div className="bg-bg-card border border-border-card p-6 rounded-3xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-bold text-white">Operação mais recente</h3>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">ao vivo</span>
            </div>

            {latestRow ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-white/5 bg-bg-dark/50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-gray-500 font-black">Ativo</p>
                      <p className="text-lg font-black text-white">{latestRow.symbol}</p>
                    </div>
                    <div
                      className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border ${
                        latestRow.status === 'open'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : latestRow.status === 'closed'
                            ? 'bg-violet-500/10 text-violet-400 border-violet-500/20'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}
                    >
                      {latestRow.statusLabel}
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-white/5 rounded-2xl p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Bot</p>
                      <p className="font-black text-white">{latestRow.botName}</p>
                    </div>
                    <div className="bg-white/5 rounded-2xl p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Evento</p>
                      <p className="font-black text-white">{latestRow.eventLabel}</p>
                    </div>
                    <div className="bg-white/5 rounded-2xl p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Entrada</p>
                      <p className="font-black text-white">{formatPrice(latestRow.entryPrice)}</p>
                    </div>
                    <div className="bg-white/5 rounded-2xl p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Resultado</p>
                      <p className={`font-black ${normalizeNumber(latestRow.pnl) >= 0 ? 'text-brand-primary' : 'text-red-400'}`}>
                        {formatSignedMoney(latestRow.pnl)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className="px-2 py-1 rounded-lg bg-white/5 text-gray-300 border border-white/10">
                      {latestRow.sourceLabel}
                    </span>
                    <span className="px-2 py-1 rounded-lg bg-white/5 text-gray-300 border border-white/10">
                      {formatDateTime(latestRow.time)}
                    </span>
                    {latestRow.ticket !== null && latestRow.ticket !== undefined && (
                      <span className="px-2 py-1 rounded-lg bg-white/5 text-gray-300 border border-white/10">
                        Ticket {latestRow.ticket}
                      </span>
                    )}
                  </div>
                </div>

                {latestLiveEvent?.comment && (
                  <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
                    <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-2">Comentario da operacao</p>
                    <p className="text-sm text-gray-300 leading-relaxed">{latestLiveEvent.comment}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full min-h-[180px] flex items-center justify-center text-gray-500 italic text-sm">
                Nenhuma operacao recente encontrada.
              </div>
            )}
          </div>

          <div className="bg-bg-card border border-border-card p-6 rounded-3xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-bold text-white">Posicoes abertas</h3>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">
                {openPositionRows.length} abertas
              </span>
            </div>

            {openPositionRows.length > 0 ? (
              <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
                {openPositionRows.map((position) => (
                  <div key={position.key} className="bg-white/5 rounded-2xl p-3 border border-white/5">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-black text-white">{position.symbol}</span>
                      <span
                        className={`text-[10px] font-black uppercase ${
                          position.direction === 'buy' ? 'text-brand-primary' : position.direction === 'sell' ? 'text-red-400' : 'text-gray-400'
                        }`}
                      >
                        {formatDirectionLabel(position.direction)}
                      </span>
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-400">
                      <span>Bot: {position.botName}</span>
                      <span>Ticket: {position.ticket ?? '---'}</span>
                      <span>Volume: {position.volume !== null && position.volume !== undefined ? Number(position.volume).toFixed(2) : '---'}</span>
                      <span>PnL: {formatSignedMoney(position.pnl)}</span>
                      <span>Entrada: {formatPrice(position.entryPrice)}</span>
                      <span>Horario: {formatTime(position.time)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500 italic">Sem posições abertas no momento.</div>
            )}
          </div>

          <div className="bg-bg-card border border-border-card p-6 rounded-3xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-bold text-white">Historico do banco</h3>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">30 dias</span>
            </div>

            {hasHistory ? (
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Operacoes</span>
                  <span className="font-black text-white">{tradeStats.total_trades}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Fechadas</span>
                  <span className="font-black text-white">{tradeStats.closed_trades}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Abertas</span>
                  <span className="font-black text-white">{tradeStats.open_trades}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Max drawdown</span>
                  <span className="font-black text-white">R$ {formatMoney(tradeStats.max_drawdown)}</span>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-100/80">
                Nenhum historico salvo no banco ainda. O painel esta usando o MT5 ao vivo como fonte principal.
              </div>
            )}
          </div>

          <div className="bg-bg-card border border-border-card p-6 rounded-3xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-bold text-white">Leitura rapida</h3>
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">mercado</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Operacoes visiveis</span>
                <span className="font-black text-white">{filteredRows.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Tempo real</span>
                <span className="font-black text-white">{liveSourceRows.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Historico</span>
                <span className="font-black text-white">{historyRows.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Bots mapeados</span>
                <span className="font-black text-white">{bots.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
