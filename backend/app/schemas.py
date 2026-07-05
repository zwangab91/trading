from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class PolicyResponse(BaseModel):
    initial_account_equity: float
    initial_live_capital_range: List[float]
    benchmark_weights: Dict[str, float]
    live_trading_enabled: bool
    manual_approval_required: bool
    long_only: bool
    allow_margin: bool
    allow_shorting: bool
    gross_exposure_cap_pct: float
    risk_per_trade_default_pct: float
    risk_per_trade_max_pct: float


class StrategySummary(BaseModel):
    id: str
    name: str
    sleeve: str
    ending_value: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    volatility: float
    sharpe_like: float


class TimeSeriesPoint(BaseModel):
    date: str
    value: float


class WeightRow(BaseModel):
    symbol: str
    weight: float


class DailyReturnRow(BaseModel):
    date: str
    daily_return: float


class TradeRow(BaseModel):
    strategy: str
    source_strategy: str
    sleeve: str
    trade_date: str
    entry_date: Optional[str]
    exit_trim_date: Optional[str]
    symbol: str
    action: str
    previous_weight: float
    target_weight: float
    weight_change: float
    price: float
    transaction_cost: float
    realized_marked_return: Optional[float]


class StrategyDetail(BaseModel):
    summary: StrategySummary
    description: str
    latest_weights: List[WeightRow]
    daily_returns: List[DailyReturnRow]
    trade_history: List[TradeRow]


class DashboardResponse(BaseModel):
    data_source: str
    is_real_data: bool
    data_error: str
    initial_capital: float
    summary: List[StrategySummary]
    equity_curves: Dict[str, List[TimeSeriesPoint]]
    drawdowns: Dict[str, List[TimeSeriesPoint]]
    prices: Dict[str, List[TimeSeriesPoint]]
    sample_etfs: List[str]
    sample_stocks: List[str]


class DataRefreshResponse(BaseModel):
    refreshed: bool
    dashboard: DashboardResponse
