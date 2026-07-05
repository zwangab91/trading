from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, FrozenSet, Mapping

from trading_agent.domain import AssetType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "config" / "v1_policy.json"


@dataclass(frozen=True)
class Policy:
    initial_account_equity: float
    initial_live_capital_min: float
    initial_live_capital_max: float
    benchmark_weights: Mapping[str, float]
    live_trading_enabled: bool
    manual_approval_required: bool
    regular_session_only_v1: bool
    allowed_asset_types: FrozenSet[AssetType]
    long_only: bool
    allow_margin: bool
    allow_shorting: bool
    allow_options: bool
    allow_leveraged_etfs: bool
    allow_inverse_etfs: bool
    blocked_symbols: FrozenSet[str]
    drawdown_pause_pct: float
    drawdown_hard_stop_pct: float
    day_stop_new_trades_pct: float
    day_hard_review_pct: float
    week_pause_pct: float
    month_pause_pct: float
    risk_per_trade_default_pct: float
    risk_per_trade_max_pct: float
    gross_exposure_cap_pct: float
    single_stock_cap_pct: float
    single_etf_cap_pct: float
    minimum_cash_buffer_pct: float
    pre_earnings_blackout_trading_days: int
    post_earnings_blackout_trading_days: int
    earnings_manual_override_allowed: bool
    earnings_validated_event_model_allowed: bool
    earnings_max_size_multiplier_during_blackout: float
    earnings_max_total_pre_earnings_exposure_pct: float
    raw: Mapping[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Policy":
        capital = data["capital"]
        benchmark = data["benchmark"]
        broker = data["broker"]
        asset_policy = data["asset_policy"]
        risk_limits = data["risk_limits"]
        earnings_policy = data["earnings_policy"]

        return cls(
            initial_account_equity=float(capital["initial_account_equity"]),
            initial_live_capital_min=float(capital["initial_live_capital_min"]),
            initial_live_capital_max=float(capital["initial_live_capital_max"]),
            benchmark_weights={k.upper(): float(v) for k, v in benchmark["weights"].items()},
            live_trading_enabled=bool(broker["live_trading_enabled"]),
            manual_approval_required=bool(broker["manual_approval_required"]),
            regular_session_only_v1=bool(broker["regular_session_only_v1"]),
            allowed_asset_types=frozenset(
                AssetType(asset_type) for asset_type in asset_policy["allowed_asset_types"]
            ),
            long_only=bool(asset_policy["long_only"]),
            allow_margin=bool(asset_policy["allow_margin"]),
            allow_shorting=bool(asset_policy["allow_shorting"]),
            allow_options=bool(asset_policy["allow_options"]),
            allow_leveraged_etfs=bool(asset_policy["allow_leveraged_etfs"]),
            allow_inverse_etfs=bool(asset_policy["allow_inverse_etfs"]),
            blocked_symbols=frozenset(
                symbol.upper() for symbol in asset_policy.get("blocked_symbols", [])
            ),
            drawdown_pause_pct=float(risk_limits["drawdown_pause_pct"]),
            drawdown_hard_stop_pct=float(risk_limits["drawdown_hard_stop_pct"]),
            day_stop_new_trades_pct=float(risk_limits["day_stop_new_trades_pct"]),
            day_hard_review_pct=float(risk_limits["day_hard_review_pct"]),
            week_pause_pct=float(risk_limits["week_pause_pct"]),
            month_pause_pct=float(risk_limits["month_pause_pct"]),
            risk_per_trade_default_pct=float(risk_limits["risk_per_trade_default_pct"]),
            risk_per_trade_max_pct=float(risk_limits["risk_per_trade_max_pct"]),
            gross_exposure_cap_pct=float(risk_limits["gross_exposure_cap_pct"]),
            single_stock_cap_pct=float(risk_limits["single_stock_cap_pct"]),
            single_etf_cap_pct=float(risk_limits["single_etf_cap_pct"]),
            minimum_cash_buffer_pct=float(risk_limits["minimum_cash_buffer_pct"]),
            pre_earnings_blackout_trading_days=int(
                earnings_policy["pre_earnings_blackout_trading_days"]
            ),
            post_earnings_blackout_trading_days=int(
                earnings_policy["post_earnings_blackout_trading_days"]
            ),
            earnings_manual_override_allowed=bool(earnings_policy["manual_override_allowed"]),
            earnings_validated_event_model_allowed=bool(
                earnings_policy["validated_event_model_allowed"]
            ),
            earnings_max_size_multiplier_during_blackout=float(
                earnings_policy["max_size_multiplier_during_blackout"]
            ),
            earnings_max_total_pre_earnings_exposure_pct=float(
                earnings_policy["max_total_pre_earnings_exposure_pct"]
            ),
            raw=data,
        )


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> Policy:
    with path.open("r", encoding="utf-8") as handle:
        return Policy.from_dict(json.load(handle))

