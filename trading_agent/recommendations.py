from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from trading_agent.config import Policy
from trading_agent.domain import (
    AccountState,
    AssetType,
    OrderIntent,
    Side,
    Sleeve,
    StrategySignal,
)


def size_long_order(
    account: AccountState,
    policy: Policy,
    symbol: str,
    asset_type: AssetType,
    sleeve: Sleeve,
    strategy_name: str,
    limit_price: float,
    stop_price: float,
    rationale: str,
    expected_holding_days: Optional[int] = None,
    generated_at: Optional[datetime] = None,
) -> OrderIntent:
    if limit_price <= 0:
        raise ValueError("limit_price must be positive")
    if stop_price <= 0 or stop_price >= limit_price:
        raise ValueError("stop_price must be positive and below limit_price")

    risk_per_share = limit_price - stop_price
    risk_budget = account.equity * policy.risk_per_trade_default_pct
    max_symbol_pct = (
        policy.single_etf_cap_pct if asset_type == AssetType.ETF else policy.single_stock_cap_pct
    )
    notional_budget = account.equity * max_symbol_pct

    quantity_by_risk = math.floor(risk_budget / risk_per_share)
    quantity_by_notional = math.floor(notional_budget / limit_price)
    quantity_by_cash_buffer = math.floor(
        max(0.0, account.cash - account.equity * policy.minimum_cash_buffer_pct)
        / limit_price
    )
    quantity = max(0, min(quantity_by_risk, quantity_by_notional, quantity_by_cash_buffer))

    return OrderIntent(
        symbol=symbol.upper(),
        asset_type=asset_type,
        sleeve=sleeve,
        side=Side.BUY,
        quantity=quantity,
        limit_price=limit_price,
        strategy_name=strategy_name,
        rationale=rationale,
        generated_at=generated_at or datetime.utcnow(),
        risk_amount=quantity * risk_per_share,
        expected_holding_days=expected_holding_days,
        metadata={"stop_price": stop_price},
    )


def order_from_signal(
    signal: StrategySignal,
    account: AccountState,
    policy: Policy,
    limit_price: float,
    stop_price: float,
    expected_holding_days: Optional[int] = None,
) -> OrderIntent:
    return size_long_order(
        account=account,
        policy=policy,
        symbol=signal.symbol,
        asset_type=signal.asset_type,
        sleeve=signal.sleeve,
        strategy_name=signal.metadata.get("strategy_name", "unknown_strategy"),
        limit_price=limit_price,
        stop_price=stop_price,
        rationale=signal.rationale,
        expected_holding_days=expected_holding_days,
        generated_at=signal.generated_at,
    )

