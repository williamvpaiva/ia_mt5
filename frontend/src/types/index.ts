export interface Bot {
  id: string;
  name: string;
  magic_number: number;
  symbol: string;
  active: boolean;
  created_at: string;
}

export interface Trade {
  id: string;
  bot_id: string;
  symbol: string;
  type: 'buy' | 'sell';
  volume: number;
  entry_price: number;
  exit_price?: number;
  pnl?: number;
  timestamp: string;
}

export interface DashboardMetrics {
  total_pnl: number;
  win_rate: number;
  max_drawdown: number;
  dataset_size: number;
  pnl_delta: number;
}

export interface BacktestResult {
  total_pnl: number;
  trades_count: number;
  win_rate: number;
  equity_curve: number[];
  trades: Trade[];
}
