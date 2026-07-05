export interface PolicyResponse {
  initial_account_equity: number;
  initial_live_capital_range: number[];
  benchmark_weights: Record<string, number>;
  live_trading_enabled: boolean;
  manual_approval_required: boolean;
  long_only: boolean;
  allow_margin: boolean;
  allow_shorting: boolean;
  gross_exposure_cap_pct: number;
  risk_per_trade_default_pct: number;
  risk_per_trade_max_pct: number;
}

export interface StrategySummary {
  id: string;
  name: string;
  sleeve: string;
  ending_value: number;
  total_return: number;
  annualized_return: number;
  max_drawdown: number;
  volatility: number;
  sharpe_like: number;
}

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

export interface WeightRow {
  symbol: string;
  weight: number;
}

export interface DailyReturnRow {
  date: string;
  daily_return: number;
}

export interface TradeRow {
  strategy: string;
  source_strategy: string;
  sleeve: string;
  trade_date: string;
  entry_date: string | null;
  exit_trim_date: string | null;
  symbol: string;
  action: string;
  previous_weight: number;
  target_weight: number;
  weight_change: number;
  price: number;
  transaction_cost: number;
  realized_marked_return: number | null;
}

export interface StrategyDetail {
  summary: StrategySummary;
  description: string;
  latest_weights: WeightRow[];
  daily_returns: DailyReturnRow[];
  trade_history: TradeRow[];
}

export interface DashboardResponse {
  data_source: string;
  is_real_data: boolean;
  data_error: string;
  initial_capital: number;
  summary: StrategySummary[];
  equity_curves: Record<string, TimeSeriesPoint[]>;
  drawdowns: Record<string, TimeSeriesPoint[]>;
  prices?: Record<string, TimeSeriesPoint[]>;
  sample_etfs?: string[];
  sample_stocks?: string[];
}

export interface DataRefreshResponse {
  refreshed: boolean;
  dashboard: DashboardResponse;
}
