import unittest
from datetime import date, datetime

from trading_agent.config import load_policy
from trading_agent.domain import AccountState, AssetType, OrderIntent, Position, Side, Sleeve
from trading_agent.risk import RiskEngine


class RiskEngineTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()
        self.engine = RiskEngine(self.policy)
        self.account = AccountState(equity=50000.0, cash=30000.0, peak_equity=50000.0)

    def _buy_order(self, **overrides):
        data = {
            "symbol": "SPY",
            "asset_type": AssetType.ETF,
            "sleeve": Sleeve.CORE_ETF,
            "side": Side.BUY,
            "quantity": 5,
            "limit_price": 500.0,
            "strategy_name": "test",
            "rationale": "test",
            "generated_at": datetime.utcnow(),
            "risk_amount": 100.0,
        }
        data.update(overrides)
        return OrderIntent(**data)

    def test_allows_safe_etf_buy(self):
        decision = self.engine.evaluate_order(
            self.account,
            self._buy_order(),
            today=date(2026, 7, 6),
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.blocking_checks, ())

    def test_blocks_leveraged_etf_symbol(self):
        decision = self.engine.evaluate_order(
            self.account,
            self._buy_order(symbol="TQQQ"),
            today=date(2026, 7, 6),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("blocked_symbol", [check.name for check in decision.blocking_checks])

    def test_blocks_risk_over_max(self):
        decision = self.engine.evaluate_order(
            self.account,
            self._buy_order(risk_amount=300.0),
            today=date(2026, 7, 6),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("risk_amount_max", [check.name for check in decision.blocking_checks])

    def test_blocks_new_equity_buy_before_earnings_without_exception(self):
        decision = self.engine.evaluate_order(
            self.account,
            self._buy_order(
                symbol="MSFT",
                asset_type=AssetType.EQUITY,
                sleeve=Sleeve.EQUITY_SATELLITE,
                quantity=5,
                limit_price=300.0,
                earnings_date=date(2026, 7, 8),
            ),
            today=date(2026, 7, 6),
        )

        self.assertFalse(decision.allowed)
        self.assertIn(
            "earnings_exception_required",
            [check.name for check in decision.blocking_checks],
        )

    def test_allows_reduced_earnings_override(self):
        decision = self.engine.evaluate_order(
            self.account,
            self._buy_order(
                symbol="MSFT",
                asset_type=AssetType.EQUITY,
                sleeve=Sleeve.EQUITY_SATELLITE,
                quantity=4,
                limit_price=300.0,
                earnings_date=date(2026, 7, 8),
                earnings_override=True,
            ),
            today=date(2026, 7, 6),
        )

        self.assertTrue(decision.allowed)
        self.assertTrue(any(check.name == "earnings_event_warning" for check in decision.checks))

    def test_blocks_short_sale(self):
        account = AccountState(
            equity=50000.0,
            cash=30000.0,
            peak_equity=50000.0,
            positions=(
                Position(
                    symbol="SPY",
                    asset_type=AssetType.ETF,
                    quantity=3,
                    market_price=500.0,
                    sleeve=Sleeve.CORE_ETF,
                ),
            ),
        )
        order = self._buy_order(side=Side.SELL, quantity=5)
        decision = self.engine.evaluate_order(account, order, today=date(2026, 7, 6))

        self.assertFalse(decision.allowed)
        self.assertIn("no_short_sale", [check.name for check in decision.blocking_checks])


if __name__ == "__main__":
    unittest.main()

