from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any, Dict, List, Mapping, Optional

from backend.app.schemas import (
    DailyReturnRow,
    DashboardResponse,
    PolicyResponse,
    StrategyDetail,
    StrategySummary,
    TimeSeriesPoint,
    TradeRow,
    WeightRow,
)
from trading_agent.config import Policy
from trading_agent.demo import SAMPLE_ETFS, SAMPLE_STOCKS


def strategy_id(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return normalized or "strategy"


def strategy_id_map(results: Mapping[str, Any]) -> Dict[str, str]:
    return {strategy_id(name): name for name in results}


def require_strategy_name(results: Mapping[str, Any], strategy_key: str) -> str:
    by_id = strategy_id_map(results)
    if strategy_key in by_id:
        return by_id[strategy_key]
    if strategy_key in results:
        return strategy_key
    raise KeyError(strategy_key)


def serialize_policy(policy: Policy) -> PolicyResponse:
    return PolicyResponse(
        initial_account_equity=policy.initial_account_equity,
        initial_live_capital_range=[
            policy.initial_live_capital_min,
            policy.initial_live_capital_max,
        ],
        benchmark_weights=dict(policy.benchmark_weights),
        live_trading_enabled=policy.live_trading_enabled,
        manual_approval_required=policy.manual_approval_required,
        long_only=policy.long_only,
        allow_margin=policy.allow_margin,
        allow_shorting=policy.allow_shorting,
        gross_exposure_cap_pct=policy.gross_exposure_cap_pct,
        risk_per_trade_default_pct=policy.risk_per_trade_default_pct,
        risk_per_trade_max_pct=policy.risk_per_trade_max_pct,
    )


def serialize_dashboard(demo: Any, initial_capital: float) -> DashboardResponse:
    return DashboardResponse(
        data_source=demo.data_source,
        is_real_data=demo.is_real_data,
        data_error=demo.data_error,
        initial_capital=initial_capital,
        summary=[serialize_strategy_summary(result) for result in demo.results.values()],
        equity_curves=_serialize_frame_series(demo.equity_curves),
        drawdowns=_serialize_frame_series(demo.drawdowns),
        prices=_serialize_frame_series(demo.prices),
        sample_etfs=list(SAMPLE_ETFS),
        sample_stocks=list(SAMPLE_STOCKS),
    )


def serialize_strategy_summary(result: Any) -> StrategySummary:
    return StrategySummary(
        id=strategy_id(result.name),
        name=result.name,
        sleeve=result.sleeve,
        ending_value=_finite_float(result.ending_value),
        total_return=_finite_float(result.summary.total_return),
        annualized_return=_finite_float(result.summary.annualized_return),
        max_drawdown=_finite_float(result.summary.max_drawdown),
        volatility=_finite_float(result.summary.volatility),
        sharpe_like=_finite_float(result.summary.sharpe_like),
    )


def serialize_strategy_detail(result: Any) -> StrategyDetail:
    return StrategyDetail(
        summary=serialize_strategy_summary(result),
        description=result.description,
        latest_weights=serialize_weights(result.latest_weights),
        daily_returns=serialize_daily_returns(result.daily_returns),
        trade_history=serialize_trade_history(result.trade_history),
    )


def serialize_weights(weights: Any) -> List[WeightRow]:
    rows = []
    for symbol, weight in weights.items():
        rows.append(WeightRow(symbol=str(symbol), weight=_finite_float(weight)))
    return rows


def serialize_daily_returns(daily_returns: Any) -> List[DailyReturnRow]:
    rows = []
    for index, value in daily_returns.items():
        rows.append(
            DailyReturnRow(
                date=_date_string(index),
                daily_return=_finite_float(value),
            )
        )
    return rows


def serialize_trade_history(trade_history: Any) -> List[TradeRow]:
    rows = []
    rename = {
        "Strategy": "strategy",
        "Source Strategy": "source_strategy",
        "Sleeve": "sleeve",
        "Trade Date": "trade_date",
        "Entry Date": "entry_date",
        "Exit/Trim Date": "exit_trim_date",
        "Symbol": "symbol",
        "Action": "action",
        "Previous Weight": "previous_weight",
        "Target Weight": "target_weight",
        "Weight Change": "weight_change",
        "Price": "price",
        "Transaction Cost": "transaction_cost",
        "Realized/Marked Return": "realized_marked_return",
    }
    for raw in trade_history.rename(columns=rename).to_dict(orient="records"):
        rows.append(
            TradeRow(
                strategy=str(raw["strategy"]),
                source_strategy=str(raw["source_strategy"]),
                sleeve=str(raw["sleeve"]),
                trade_date=_date_string(raw["trade_date"]),
                entry_date=_optional_date_string(raw["entry_date"]),
                exit_trim_date=_optional_date_string(raw["exit_trim_date"]),
                symbol=str(raw["symbol"]),
                action=str(raw["action"]),
                previous_weight=_finite_float(raw["previous_weight"]),
                target_weight=_finite_float(raw["target_weight"]),
                weight_change=_finite_float(raw["weight_change"]),
                price=_finite_float(raw["price"]),
                transaction_cost=_finite_float(raw["transaction_cost"]),
                realized_marked_return=_optional_float(raw["realized_marked_return"]),
            )
        )
    return rows


def _serialize_frame_series(frame: Any) -> Dict[str, List[TimeSeriesPoint]]:
    output = {}
    for column in frame.columns:
        output[str(column)] = [
            TimeSeriesPoint(date=_date_string(index), value=_finite_float(value))
            for index, value in frame[column].items()
        ]
    return output


def _date_string(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "date") and callable(value.date):
        return value.date().isoformat()
    return str(value)


def _optional_date_string(value: Any) -> Optional[str]:
    if _is_missing(value):
        return None
    return _date_string(value)


def _optional_float(value: Any) -> Optional[float]:
    if _is_missing(value):
        return None
    return _finite_float(value)


def _finite_float(value: Any) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"Expected finite numeric value, got {value!r}")
    return numeric


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        import pandas as pd  # type: ignore

        if pd.isna(value):
            return True
    except (ImportError, TypeError, ValueError):
        pass
    return False
