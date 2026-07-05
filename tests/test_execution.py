import unittest
from dataclasses import replace
from datetime import date, datetime

from trading_agent.config import load_policy
from trading_agent.domain import AccountState, AssetType, OrderIntent, Side, Sleeve
from trading_agent.execution.schwab import LiveTradingDisabled, SchwabAdapter
from trading_agent.risk import RiskEngine


class SchwabAdapterTests(unittest.TestCase):
    def test_submit_order_is_blocked_when_live_trading_disabled(self):
        policy = load_policy()
        account = AccountState(equity=50000.0, cash=30000.0, peak_equity=50000.0)
        order = OrderIntent(
            symbol="SPY",
            asset_type=AssetType.ETF,
            sleeve=Sleeve.CORE_ETF,
            side=Side.BUY,
            quantity=5,
            limit_price=500.0,
            strategy_name="test",
            rationale="test",
            generated_at=datetime.utcnow(),
            risk_amount=100.0,
        )
        decision = RiskEngine(policy).evaluate_order(account, order, today=date(2026, 7, 6))
        prepared = SchwabAdapter(policy).prepare_order(order, decision)
        prepared = replace(prepared, approved_by_user=True)

        with self.assertRaises(LiveTradingDisabled):
            SchwabAdapter(policy).submit_order(prepared)


if __name__ == "__main__":
    unittest.main()

