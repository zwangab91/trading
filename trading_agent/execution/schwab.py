from __future__ import annotations

from typing import Any, Dict

from trading_agent.config import Policy
from trading_agent.domain import OrderIntent, PreparedOrder, RiskDecision, Side


class LiveTradingDisabled(RuntimeError):
    pass


class OrderNotApproved(RuntimeError):
    pass


class SchwabAdapter:
    """Guarded adapter facade for Schwab order preparation.

    This class intentionally does not implement OAuth or network submission yet.
    Live order submission must stay disabled until account auth, paper/live
    separation, approval UI, and end-to-end audit logging are complete.
    """

    def __init__(self, policy: Policy):
        self.policy = policy

    def prepare_order(self, intent: OrderIntent, risk_decision: RiskDecision) -> PreparedOrder:
        payload = self._to_order_payload(intent)
        return PreparedOrder(
            intent=intent,
            broker_payload=payload,
            risk_decision=risk_decision,
            approved_by_user=False,
        )

    def submit_order(self, prepared_order: PreparedOrder) -> Dict[str, Any]:
        if not self.policy.live_trading_enabled:
            raise LiveTradingDisabled("Live trading is disabled in policy configuration.")
        if self.policy.manual_approval_required and not prepared_order.approved_by_user:
            raise OrderNotApproved("Order requires explicit user approval.")
        if not prepared_order.risk_decision.allowed:
            raise ValueError("Order did not pass risk checks.")
        raise NotImplementedError("Schwab network submission is not implemented yet.")

    def _to_order_payload(self, intent: OrderIntent) -> Dict[str, Any]:
        instruction = "BUY" if intent.side == Side.BUY else "SELL"
        return {
            "orderType": "LIMIT",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "price": f"{intent.limit_price:.2f}",
            "orderLegCollection": [
                {
                    "instruction": instruction,
                    "quantity": intent.quantity,
                    "instrument": {
                        "symbol": intent.symbol_normalized,
                        "assetType": "EQUITY",
                    },
                }
            ],
        }

