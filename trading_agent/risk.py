from __future__ import annotations

from datetime import date
from typing import List

from trading_agent.calendar import business_days_between
from trading_agent.config import Policy
from trading_agent.domain import (
    AccountState,
    AssetType,
    OrderIntent,
    RiskCheck,
    RiskDecision,
    RiskSeverity,
    Side,
)


class RiskEngine:
    def __init__(self, policy: Policy):
        self.policy = policy

    def evaluate_order(
        self,
        account: AccountState,
        order: OrderIntent,
        today: date,
    ) -> RiskDecision:
        checks: List[RiskCheck] = []

        checks.extend(self._account_halt_checks(account))
        checks.extend(self._asset_policy_checks(order))
        checks.extend(self._order_shape_checks(account, order))
        checks.extend(self._loss_limit_checks(account))
        checks.extend(self._exposure_checks(account, order))
        checks.extend(self._risk_amount_checks(account, order))
        checks.extend(self._earnings_checks(account, order, today))

        allowed = all(
            check.passed or check.severity != RiskSeverity.BLOCK for check in checks
        )
        return RiskDecision(allowed=allowed, checks=tuple(checks))

    def _account_halt_checks(self, account: AccountState) -> List[RiskCheck]:
        return [
            RiskCheck(
                name="kill_switch",
                passed=not account.kill_switch_active,
                severity=RiskSeverity.BLOCK,
                message=(
                    "Kill switch is inactive."
                    if not account.kill_switch_active
                    else "Kill switch is active; no new orders allowed."
                ),
            )
        ]

    def _asset_policy_checks(self, order: OrderIntent) -> List[RiskCheck]:
        checks: List[RiskCheck] = []
        checks.append(
            RiskCheck(
                name="allowed_asset_type",
                passed=order.asset_type in self.policy.allowed_asset_types,
                severity=RiskSeverity.BLOCK,
                message=f"Asset type is {order.asset_type.value}.",
            )
        )
        checks.append(
            RiskCheck(
                name="blocked_symbol",
                passed=order.symbol_normalized not in self.policy.blocked_symbols,
                severity=RiskSeverity.BLOCK,
                message=(
                    f"{order.symbol_normalized} is not in the blocked symbol list."
                    if order.symbol_normalized not in self.policy.blocked_symbols
                    else f"{order.symbol_normalized} is blocked by v1 asset policy."
                ),
            )
        )
        return checks

    def _order_shape_checks(
        self, account: AccountState, order: OrderIntent
    ) -> List[RiskCheck]:
        checks: List[RiskCheck] = []
        checks.append(
            RiskCheck(
                name="positive_quantity",
                passed=order.quantity > 0,
                severity=RiskSeverity.BLOCK,
                message=f"Order quantity is {order.quantity}.",
            )
        )
        checks.append(
            RiskCheck(
                name="positive_limit_price",
                passed=order.limit_price > 0,
                severity=RiskSeverity.BLOCK,
                message=f"Order limit price is {order.limit_price}.",
            )
        )

        if order.side == Side.SELL and self.policy.long_only:
            current_position = account.position_for(order.symbol)
            current_quantity = current_position.quantity if current_position else 0
            checks.append(
                RiskCheck(
                    name="no_short_sale",
                    passed=order.quantity <= current_quantity,
                    severity=RiskSeverity.BLOCK,
                    message=(
                        "Sell order only reduces an existing long position."
                        if order.quantity <= current_quantity
                        else "Sell order would create a short position."
                    ),
                )
            )

        return checks

    def _loss_limit_checks(self, account: AccountState) -> List[RiskCheck]:
        checks: List[RiskCheck] = []
        drawdown = 0.0
        if account.peak_equity > 0:
            drawdown = max(0.0, 1.0 - account.equity / account.peak_equity)

        checks.append(
            RiskCheck(
                name="drawdown_hard_stop",
                passed=drawdown < self.policy.drawdown_hard_stop_pct,
                severity=RiskSeverity.BLOCK,
                message=f"Current drawdown is {drawdown:.2%}.",
            )
        )
        checks.append(
            RiskCheck(
                name="drawdown_pause",
                passed=drawdown < self.policy.drawdown_pause_pct,
                severity=RiskSeverity.BLOCK,
                message=f"Current drawdown is {drawdown:.2%}.",
            )
        )
        checks.append(
            RiskCheck(
                name="daily_hard_review",
                passed=account.day_pnl > -account.equity * self.policy.day_hard_review_pct,
                severity=RiskSeverity.BLOCK,
                message=f"Day P&L is {account.day_pnl:.2f}.",
            )
        )
        checks.append(
            RiskCheck(
                name="daily_stop_new_trades",
                passed=account.day_pnl > -account.equity * self.policy.day_stop_new_trades_pct,
                severity=RiskSeverity.BLOCK,
                message=f"Day P&L is {account.day_pnl:.2f}.",
            )
        )
        checks.append(
            RiskCheck(
                name="weekly_pause",
                passed=account.week_pnl > -account.equity * self.policy.week_pause_pct,
                severity=RiskSeverity.BLOCK,
                message=f"Week P&L is {account.week_pnl:.2f}.",
            )
        )
        checks.append(
            RiskCheck(
                name="monthly_pause",
                passed=account.month_pnl > -account.equity * self.policy.month_pause_pct,
                severity=RiskSeverity.BLOCK,
                message=f"Month P&L is {account.month_pnl:.2f}.",
            )
        )
        return checks

    def _exposure_checks(
        self, account: AccountState, order: OrderIntent
    ) -> List[RiskCheck]:
        current_symbol_position = account.position_for(order.symbol)
        current_symbol_value = (
            current_symbol_position.market_value if current_symbol_position else 0.0
        )

        projected_gross = account.gross_long_exposure
        projected_symbol_value = current_symbol_value

        if order.side == Side.BUY:
            projected_gross += order.notional
            projected_symbol_value += order.notional
        else:
            reduction = min(order.notional, max(current_symbol_value, 0.0))
            projected_gross -= reduction
            projected_symbol_value = max(0.0, projected_symbol_value - reduction)

        max_symbol_pct = (
            self.policy.single_etf_cap_pct
            if order.asset_type == AssetType.ETF
            else self.policy.single_stock_cap_pct
        )
        max_symbol_value = account.equity * max_symbol_pct
        max_gross_value = account.equity * self.policy.gross_exposure_cap_pct
        min_cash_after_buy = account.equity * self.policy.minimum_cash_buffer_pct
        projected_cash = account.cash - order.notional if order.side == Side.BUY else account.cash

        return [
            RiskCheck(
                name="gross_exposure_cap",
                passed=projected_gross <= max_gross_value,
                severity=RiskSeverity.BLOCK,
                message=(
                    f"Projected gross exposure is {projected_gross:.2f}; "
                    f"cap is {max_gross_value:.2f}."
                ),
            ),
            RiskCheck(
                name="single_name_cap",
                passed=projected_symbol_value <= max_symbol_value,
                severity=RiskSeverity.BLOCK,
                message=(
                    f"Projected {order.symbol_normalized} exposure is "
                    f"{projected_symbol_value:.2f}; cap is {max_symbol_value:.2f}."
                ),
            ),
            RiskCheck(
                name="cash_available",
                passed=order.side == Side.SELL or order.notional <= account.cash,
                severity=RiskSeverity.BLOCK,
                message=(
                    f"Order notional is {order.notional:.2f}; cash is {account.cash:.2f}."
                ),
            ),
            RiskCheck(
                name="minimum_cash_buffer",
                passed=order.side == Side.SELL or projected_cash >= min_cash_after_buy,
                severity=RiskSeverity.BLOCK,
                message=(
                    f"Projected cash is {projected_cash:.2f}; minimum buffer is "
                    f"{min_cash_after_buy:.2f}."
                ),
            ),
        ]

    def _risk_amount_checks(
        self, account: AccountState, order: OrderIntent
    ) -> List[RiskCheck]:
        if order.side == Side.SELL:
            return [
                RiskCheck(
                    name="risk_amount",
                    passed=True,
                    severity=RiskSeverity.INFO,
                    message="Sell orders reduce exposure.",
                )
            ]

        if order.risk_amount is None:
            return [
                RiskCheck(
                    name="risk_amount_required",
                    passed=False,
                    severity=RiskSeverity.BLOCK,
                    message="Buy orders require a defined max risk amount.",
                )
            ]

        max_risk = account.equity * self.policy.risk_per_trade_max_pct
        default_risk = account.equity * self.policy.risk_per_trade_default_pct
        return [
            RiskCheck(
                name="risk_amount_max",
                passed=order.risk_amount <= max_risk,
                severity=RiskSeverity.BLOCK,
                message=(
                    f"Order risk is {order.risk_amount:.2f}; max is {max_risk:.2f}."
                ),
            ),
            RiskCheck(
                name="risk_amount_default",
                passed=order.risk_amount <= default_risk,
                severity=RiskSeverity.WARNING,
                message=(
                    f"Order risk is {order.risk_amount:.2f}; default target is "
                    f"{default_risk:.2f}."
                ),
            ),
        ]

    def _earnings_checks(
        self, account: AccountState, order: OrderIntent, today: date
    ) -> List[RiskCheck]:
        if order.asset_type != AssetType.EQUITY or order.side != Side.BUY:
            return [
                RiskCheck(
                    name="earnings_policy",
                    passed=True,
                    severity=RiskSeverity.INFO,
                    message="Earnings blackout policy does not apply.",
                )
            ]

        if order.earnings_date is None:
            return [
                RiskCheck(
                    name="earnings_date_known",
                    passed=False,
                    severity=RiskSeverity.WARNING,
                    message="No earnings date supplied; live data should fill this before deployment.",
                )
            ]

        days_until = business_days_between(today, order.earnings_date)
        days_since = business_days_between(order.earnings_date, today)
        in_pre_blackout = 0 <= days_until <= self.policy.pre_earnings_blackout_trading_days
        in_post_blackout = 0 <= days_since <= self.policy.post_earnings_blackout_trading_days
        if not in_pre_blackout and not in_post_blackout:
            return [
                RiskCheck(
                    name="earnings_blackout",
                    passed=True,
                    severity=RiskSeverity.INFO,
                    message="Order is outside the earnings blackout window.",
                )
            ]

        allowed_exception = (
            self.policy.earnings_manual_override_allowed and order.earnings_override
        ) or (
            self.policy.earnings_validated_event_model_allowed
            and order.event_model_validated
        )
        reduced_size_cap = (
            account.equity
            * self.policy.single_stock_cap_pct
            * self.policy.earnings_max_size_multiplier_during_blackout
        )

        checks = [
            RiskCheck(
                name="earnings_exception_required",
                passed=allowed_exception,
                severity=RiskSeverity.BLOCK,
                message=(
                    "Earnings blackout exception is present."
                    if allowed_exception
                    else "New equity buy is inside the earnings blackout window."
                ),
            ),
            RiskCheck(
                name="earnings_reduced_size_cap",
                passed=order.notional <= reduced_size_cap,
                severity=RiskSeverity.BLOCK,
                message=(
                    f"Blackout-period notional is {order.notional:.2f}; reduced "
                    f"cap is {reduced_size_cap:.2f}."
                ),
            ),
        ]

        if allowed_exception:
            checks.append(
                RiskCheck(
                    name="earnings_event_warning",
                    passed=True,
                    severity=RiskSeverity.WARNING,
                    message=(
                        "Trade is inside earnings blackout and requires explicit review "
                        "of gap-risk scenarios."
                    ),
                )
            )
        return checks

