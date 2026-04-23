import { useEffect, useState } from 'react';
import { Activity, Bot, Clock3, Filter, RefreshCw, Search } from 'lucide-react';

type BotLogEntry = {
  id: number;
  level: string;
  context: string;
  message: string;
  timestamp: string;
  details?: Record<string, any>;
  bot_id?: number | null;
  bot_name?: string | null;
  symbol?: string | null;
  timeframe?: string | null;
  action?: string | null;
  signal?: string | null;
  decision?: string | null;
  market_state?: string | null;
  accepted?: boolean | null;
  reason?: string | null;
  entry_block_reason?: string | null;
  technical_summary?: string | null;
  market_summary?: string | null;
  pnl?: number | null;
};

type BotLogsPayload = {
  items?: BotLogEntry[];
  summary?: {
    total?: number;
    accepted?: number;
    rejected?: number;
    signal_logs?: number;
    train_logs?: number;
    sync_logs?: number;
    market_logs?: number;
    latest_timestamp?: string | null;
    latest_market?: BotLogEntry | null;
  };
};

type BotOption = {
  id: number;
  name: string;
  symbol?: string | null;
  magic_number?: number | null;
  active?: boolean;
};

const CONTEXT_LABELS: Record<string, { label: string; className: string }> = {
  signal: { label: 'Mercado', className: 'bg-sky-500/10 text-sky-400 border-sky-500/20' },
  trade_accept: { label: 'Trade iniciado', className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  trade_block: { label: 'Operação rejeitada', className: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  trade_close: { label: 'Encerramento', className: 'bg-violet-500/10 text-violet-400 border-violet-500/20' },
  trade_error: { label: 'Erro de envio', className: 'bg-red-500/10 text-red-400 border-red-500/20' },
  dynamic_stop: { label: 'Stop dinâmico', className: 'bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/20' },
  train: { label: 'Treino', className: 'bg-brand-primary/10 text-brand-primary border-brand-primary/20' },
  sync: { label: 'Sync', className: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' },
  bot_admin: { label: 'Cadastro', className: 'bg-gray-700/60 text-gray-300 border-white/10' },
  error: { label: 'Erro', className: 'bg-red-500/10 text-red-400 border-red-500/20' },
};

const LEVEL_STYLES: Record<string, string> = {
  INFO: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  WARN: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  ERROR: 'text-red-400 bg-red-400/10 border-red-400/20',
  DEBUG: 'text-gray-400 bg-gray-500/10 border-white/10',
};

const formatTime = (iso?: string) => {
  if (!iso) return '--:--:--';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '--:--:--';
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const formatDateTime = (iso?: string) => {
  if (!iso) return '--';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '--';
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' });
};

const formatMoney = (value?: number | null) =>
  (value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const normalizeText = (value: any) => String(value ?? '').trim().toLowerCase();

const formatSignalLabel = (value?: string | null) => {
  const normalized = normalizeText(value);
  if (normalized === 'buy') return 'COMPRA';
  if (normalized === 'sell') return 'VENDA';
  if (normalized === 'neutral') return 'NEUTRO';
  if (normalized === 'idle') return 'AGUARDANDO';
  if (!normalized) return '---';
  return String(value).toUpperCase();
};

const formatMarketStateLabel = (value?: string | null) => {
  const normalized = normalizeText(value);
  if (normalized === 'bullish') return 'Alta';
  if (normalized === 'bearish') return 'Baixa';
  if (normalized === 'neutral') return 'Neutro';
  if (normalized === 'idle') return 'Sem consenso';
  if (!normalized) return 'Neutro';
  return String(value);
};

export const BotLogs: React.FC = () => {
  const [logs, setLogs] = useState<BotLogEntry[]>([]);
  const [bots, setBots] = useState<BotOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedContext, setSelectedContext] = useState('all');
  const [selectedLevel, setSelectedLevel] = useState('all');
  const [selectedBotId, setSelectedBotId] = useState('all');

  const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

  const fetchLogs = async (silent = false) => {
    if (!silent) {
      setRefreshing(true);
      if (loading) {
        setLoading(true);
      }
    }

    try {
      const response = await fetch(`${apiUrl}/bots/logs?limit=250`, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Falha ao buscar logs (${response.status})`);
      }

      const data = (await response.json()) as BotLogsPayload;
      setLogs(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      console.error('Erro ao buscar logs dos robos:', error);
      setLogs([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchBots = async () => {
    try {
      const response = await fetch(`${apiUrl}/bots/?t=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`Falha ao buscar robos (${response.status})`);
      }

      const data = (await response.json()) as BotOption[];
      setBots(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Erro ao buscar robos para os logs:', error);
    }
  };

  useEffect(() => {
    fetchLogs();
    fetchBots();
    const interval = window.setInterval(() => {
      fetchLogs(true);
      fetchBots();
    }, 5000);

    return () => window.clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedBotId === 'all') {
      return;
    }

    if (!bots.some((bot) => String(bot.id) === selectedBotId)) {
      setSelectedBotId('all');
    }
  }, [bots, selectedBotId]);

  const botNameById = new Map(bots.map((bot) => [bot.id, bot.name]));
  const botOptions = bots
    .slice()
    .sort((left, right) => {
      if (left.active !== right.active) {
        return left.active ? -1 : 1;
      }
      return left.name.localeCompare(right.name);
    });

  const resolveBotName = (log: BotLogEntry) => {
    if (log.bot_id != null && botNameById.has(log.bot_id)) {
      return botNameById.get(log.bot_id) || log.bot_name || `Bot ${log.bot_id}`;
    }

    return log.bot_name || (log.bot_id != null ? `Bot ${log.bot_id}` : 'Bot ---');
  };

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      normalizeText(log.message).includes(normalizeText(searchTerm)) ||
      normalizeText(log.bot_name).includes(normalizeText(searchTerm)) ||
      normalizeText(resolveBotName(log)).includes(normalizeText(searchTerm)) ||
      normalizeText(log.symbol).includes(normalizeText(searchTerm)) ||
      normalizeText(log.reason).includes(normalizeText(searchTerm)) ||
      normalizeText(log.market_state).includes(normalizeText(searchTerm));

    const matchesContext = selectedContext === 'all' || log.context === selectedContext;
    const matchesLevel = selectedLevel === 'all' || log.level === selectedLevel;
    const matchesBot = selectedBotId === 'all' || String(log.bot_id ?? '') === selectedBotId;

    return matchesSearch && matchesContext && matchesLevel && matchesBot;
  });

  const summary = {
    total: filteredLogs.length,
    accepted: filteredLogs.filter((log) => log.accepted === true).length,
    rejected: filteredLogs.filter((log) => log.accepted === false || log.context === 'trade_block' || log.context === 'trade_error').length,
    signals: filteredLogs.filter((log) => log.context === 'signal').length,
    market: filteredLogs.filter(
      (log) => log.context === 'signal' || log.context === 'trade_accept' || log.context === 'trade_block' || log.context === 'trade_error' || log.context === 'dynamic_stop',
    ).length,
    train: filteredLogs.filter((log) => log.context === 'train').length,
    sync: filteredLogs.filter((log) => log.context === 'sync').length,
  };

  const latestSignal = filteredLogs.find(
    (log) => log.context === 'signal' || log.context === 'trade_accept' || log.context === 'trade_block' || log.context === 'trade_error' || log.context === 'dynamic_stop',
  );
  const latestMarket = latestSignal?.details || {};

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className="px-3 py-1 rounded-full bg-brand-primary/10 text-brand-primary text-[10px] font-black uppercase tracking-[0.3em] flex items-center gap-2">
              <Activity size={12} />
              Logs dos robos
            </span>
            <span className="px-3 py-1 rounded-full bg-white/5 text-gray-300 text-[10px] font-black uppercase tracking-[0.3em]">
              Ao vivo
            </span>
          </div>
          <h2 className="text-3xl font-black text-white">Aceites, bloqueios e leitura do mercado</h2>
          <p className="text-gray-400 mt-2">Acompanhe sinais técnicos, entradas aprovadas e recusas de risco em um unico painel.</p>
        </div>

        <button
          onClick={() => fetchLogs()}
          className="inline-flex items-center gap-2 px-4 py-3 rounded-2xl bg-brand-primary/10 text-brand-primary font-black uppercase tracking-[0.2em] text-[10px] hover:bg-brand-primary/20 transition-colors"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        <div className="bg-bg-card border border-border-card p-5 rounded-3xl">
          <p className="text-[10px] uppercase tracking-[0.2em] font-black text-gray-500 mb-2">Total visivel</p>
          <p className="text-3xl font-black text-white">{summary.total}</p>
        </div>
        <div className="bg-bg-card border border-border-card p-5 rounded-3xl">
          <p className="text-[10px] uppercase tracking-[0.2em] font-black text-gray-500 mb-2">Trades aceitos</p>
          <p className="text-3xl font-black text-emerald-400">{summary.accepted}</p>
        </div>
        <div className="bg-bg-card border border-border-card p-5 rounded-3xl">
          <p className="text-[10px] uppercase tracking-[0.2em] font-black text-gray-500 mb-2">Bloqueios</p>
          <p className="text-3xl font-black text-amber-400">{summary.rejected}</p>
        </div>
        <div className="bg-bg-card border border-border-card p-5 rounded-3xl">
          <p className="text-[10px] uppercase tracking-[0.2em] font-black text-gray-500 mb-2">Leituras de mercado</p>
          <p className="text-3xl font-black text-brand-primary">{summary.market}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-bg-card border border-border-card rounded-3xl p-6 space-y-5">
          <div className="flex flex-col md:flex-row md:items-end gap-3 md:justify-between">
            <div>
              <h3 className="text-xl font-black text-white flex items-center gap-2">
                <Filter size={16} className="text-brand-primary" />
                Filtros
              </h3>
              <p className="text-sm text-gray-400">Filtre por bot, contexto, nivel ou texto livre.</p>
            </div>
            <div className="w-full md:w-96 relative">
              <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar por bot, ativo, mensagem..."
                className="w-full bg-bg-dark border border-border-card rounded-2xl pl-11 pr-4 py-3 text-white outline-none focus:ring-2 ring-brand-primary/40"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <select
              value={selectedBotId}
              onChange={(e) => setSelectedBotId(e.target.value)}
              className="w-full bg-bg-dark border border-border-card rounded-2xl px-4 py-3 text-white outline-none"
            >
              <option value="all">Todos os robos</option>
              {botOptions.map((bot) => (
                <option key={bot.id} value={bot.id}>
                  {bot.name}
                  {bot.symbol ? ` • ${bot.symbol}` : ''}
                  {bot.magic_number ? ` • MG ${bot.magic_number}` : ''}
                </option>
              ))}
            </select>

            <select
              value={selectedContext}
              onChange={(e) => setSelectedContext(e.target.value)}
              className="w-full bg-bg-dark border border-border-card rounded-2xl px-4 py-3 text-white outline-none"
            >
              <option value="all">Todos os contextos</option>
              <option value="signal">Sinais</option>
              <option value="trade_accept">Aceites</option>
              <option value="trade_block">Bloqueios</option>
              <option value="trade_close">Fechos</option>
              <option value="dynamic_stop">Stops dinamicos</option>
              <option value="train">Treinos</option>
              <option value="sync">Sync</option>
              <option value="bot_admin">Cadastro</option>
              <option value="error">Erros</option>
            </select>

            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value)}
              className="w-full bg-bg-dark border border-border-card rounded-2xl px-4 py-3 text-white outline-none"
            >
              <option value="all">Todos os niveis</option>
              <option value="INFO">INFO</option>
              <option value="WARN">WARN</option>
              <option value="ERROR">ERROR</option>
              <option value="DEBUG">DEBUG</option>
            </select>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              { key: 'all', label: 'Tudo' },
              { key: 'signal', label: 'Sinais' },
              { key: 'trade_accept', label: 'Aceites' },
              { key: 'trade_block', label: 'Bloqueios' },
              { key: 'dynamic_stop', label: 'Stops dinamicos' },
              { key: 'train', label: 'Treino' },
              { key: 'sync', label: 'Sync' },
            ].map((item) => {
              const active = selectedContext === item.key;
              return (
                <button
                  key={item.key}
                  onClick={() => setSelectedContext(item.key)}
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
          </div>
        </div>

        <div className="bg-gradient-to-br from-brand-primary/10 to-brand-secondary/10 border border-brand-primary/20 rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-black text-white">Pulso do mercado</h3>
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-primary">
              {latestSignal ? formatTime(latestSignal.timestamp) : '--:--:--'}
            </span>
          </div>

          {latestSignal ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-gray-500 font-black">Bot</p>
                  <p className="text-lg font-black text-white">{resolveBotName(latestSignal)}</p>
                </div>
                <div
                  className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border ${
                    latestSignal.market_state === 'bullish'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : latestSignal.market_state === 'bearish'
                        ? 'bg-red-500/10 text-red-400 border-red-500/20'
                        : 'bg-gray-700/60 text-gray-300 border-white/10'
                  }`}
                >
                  {formatMarketStateLabel(latestSignal.market_state)}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-bg-dark/50 border border-white/5 rounded-2xl p-3">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Decisao</p>
                  <p className="font-black text-white">{formatSignalLabel(latestSignal.signal || latestSignal.decision || latestSignal.details?.decision || 'neutral')}</p>
                </div>
                <div className="bg-bg-dark/50 border border-white/5 rounded-2xl p-3">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Ativo</p>
                  <p className="font-black text-white">{latestSignal.symbol || latestSignal.details?.symbol || '---'}</p>
                </div>
                <div className="bg-bg-dark/50 border border-white/5 rounded-2xl p-3">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">TF</p>
                  <p className="font-black text-white">{latestSignal.timeframe || latestSignal.details?.timeframe || '---'}</p>
                </div>
                <div className="bg-bg-dark/50 border border-white/5 rounded-2xl p-3">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black mb-1">Voto</p>
                  <p className="font-black text-white">{latestMarket.final_vote ?? '---'}</p>
                </div>
              </div>

                <div className="bg-bg-dark/50 border border-white/5 rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-black">Sinais tecnicos</span>
                  <span className="text-[10px] uppercase tracking-[0.2em] text-brand-primary font-black">
                    {latestMarket.entry_allowed === false ? 'Entrada bloqueada' : 'Entrada avaliada'}
                  </span>
                </div>
                {latestMarket.technical_summary && (
                  <p className="text-sm text-gray-300 leading-relaxed">{latestMarket.technical_summary}</p>
                )}
                <div className="flex flex-wrap gap-2">
                  {latestMarket.technical_signals &&
                    Object.entries(latestMarket.technical_signals).map(([key, value]) => (
                      <span
                        key={key}
                        className="px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-[0.2em] bg-white/5 text-gray-300 border border-white/10"
                      >
                        {key}: {String(value)}
                      </span>
                    ))}
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs text-gray-400">
                  <span>RSI: {latestMarket.rsi ?? '---'}</span>
                  <span>Spread: {latestMarket.spread ?? '---'}</span>
                  <span>EMA9: {latestMarket.ema_9 ?? '---'}</span>
                  <span>EMA21: {latestMarket.ema_21 ?? '---'}</span>
                </div>
                {latestMarket.entry_block_reason && (
                  <p className="text-sm text-amber-400 font-medium">Bloqueio: {latestMarket.entry_block_reason}</p>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[220px] flex items-center justify-center text-gray-500 italic text-sm">
              Nenhum sinal recente encontrado.
            </div>
          )}
        </div>
      </div>

      <div className="bg-bg-card border border-border-card rounded-3xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-xl font-black text-white">Timeline dos logs</h3>
          <span className="text-xs text-gray-500 uppercase tracking-[0.2em] font-black">{filteredLogs.length} itens</span>
        </div>

        {loading ? (
          <div className="py-20 flex justify-center">
            <RefreshCw className="animate-spin text-brand-primary" size={40} />
          </div>
        ) : filteredLogs.length > 0 ? (
          <div className="space-y-4">
            {filteredLogs.map((log) => {
              const contextMeta = CONTEXT_LABELS[log.context] || { label: log.context, className: 'bg-white/5 text-gray-300 border-white/10' };
              const levelClass = LEVEL_STYLES[log.level] || LEVEL_STYLES.INFO;
              const techSignals = log.details?.technical_signals ? Object.entries(log.details.technical_signals) : [];

              return (
                <div key={log.id} className="bg-bg-dark/50 border border-white/5 rounded-[28px] p-5 hover:border-brand-primary/20 transition-colors">
                  <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                    <div className="space-y-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border ${contextMeta.className}`}>
                          {contextMeta.label}
                        </span>
                        <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border ${levelClass}`}>
                          {log.level}
                        </span>
                        {(log.bot_id != null || log.bot_name) && (
                          <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] bg-white/5 text-gray-300 border border-white/10 flex items-center gap-1">
                            <Bot size={12} />
                            {resolveBotName(log)}
                          </span>
                        )}
                        {log.symbol && (
                          <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] bg-gray-800/80 text-gray-300 border border-white/10">
                            {log.symbol}
                          </span>
                        )}
                      </div>

                      <div className="space-y-1">
                        <p className="text-lg font-black text-white">{log.message}</p>
                        <p className="text-xs text-gray-500">{formatDateTime(log.timestamp)}</p>
                      </div>

                      <div className="flex flex-wrap gap-2 text-xs">
                        {log.market_state && (
                          <span className={`px-2 py-1 rounded-lg font-black uppercase tracking-[0.2em] border ${
                            log.market_state === 'bullish'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : log.market_state === 'bearish'
                                ? 'bg-red-500/10 text-red-400 border-red-500/20'
                                : 'bg-gray-700/60 text-gray-300 border-white/10'
                          }`}>
                            {formatMarketStateLabel(log.market_state)}
                          </span>
                        )}
                        {log.signal && (
                          <span className="px-2 py-1 rounded-lg font-black uppercase tracking-[0.2em] bg-sky-500/10 text-sky-400 border border-sky-500/20">
                            decisao: {formatSignalLabel(log.decision || log.signal)}
                          </span>
                        )}
                        {log.action && (
                          <span className="px-2 py-1 rounded-lg font-black uppercase tracking-[0.2em] bg-white/5 text-gray-300 border border-white/10">
                            {log.action}
                          </span>
                        )}
                        {log.accepted !== undefined && (
                          <span className={`px-2 py-1 rounded-lg font-black uppercase tracking-[0.2em] border ${
                            log.accepted
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : 'bg-red-500/10 text-red-400 border-red-500/20'
                          }`}>
                            {log.accepted ? 'aceito' : 'rejeitado'}
                          </span>
                        )}
                      </div>

                      {log.reason && (
                        <p className="text-sm text-amber-400 font-medium">Motivo: {log.reason}</p>
                      )}

                      {log.market_summary && (
                        <p className="text-sm text-gray-300 leading-relaxed">{log.market_summary}</p>
                      )}

                      {log.technical_summary && (
                        <p className="text-sm text-gray-400 leading-relaxed">{log.technical_summary}</p>
                      )}

                      {techSignals.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                          {techSignals.map(([key, value]) => (
                            <span key={key} className="px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-[0.2em] bg-white/5 text-gray-300 border border-white/10">
                              {key}: {String(value)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="min-w-[170px] lg:text-right space-y-2">
                      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 text-gray-300 text-[10px] font-black uppercase tracking-[0.2em]">
                        <Clock3 size={12} />
                        {formatTime(log.timestamp)}
                      </div>
                      {typeof log.pnl === 'number' && (
                        <div className={`text-xl font-black ${log.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {log.pnl >= 0 ? '+' : ''}R$ {formatMoney(log.pnl)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-16 text-center text-gray-500 italic">
            Nenhum log encontrado com os filtros atuais.
          </div>
        )}
      </div>
    </div>
  );
};
