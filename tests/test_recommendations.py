import unittest
from datetime import date, datetime

from trading_agent.config import load_policy
from trading_agent.domain import AccountState, AssetType, Side, Sleeve, StrategySignal
from trading_agent.recommendations import order_from_signal, size_long_order
from trading_agent.risk import RiskEngine


class SizeLongOrderTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()
        self.account = AccountState(equity=50000.0, cash=50000.0, peak_equity=50000.0)
        self.generated_at = datetime(2026, 7, 6, 14, 30)

    def _size(self, account=None, **overrides):
        data = {
            "account": account or self.account,
            "policy": self.policy,
            "symbol": "spy",
            "asset_type": AssetType.ETF,
            "sleeve": Sleeve.CORE_ETF,
            "strategy_name": "test",
            "limit_price": 100.0,
            "stop_price": 95.0,
            "rationale": "test rationale",
            "generated_at": self.generated_at,
        }
        data.update(overrides)
        return size_long_order(**data)

    def test_policy_values_used_by_sizing(self):
        self.assertEqual(self.policy.risk_per_trade_default_pct, 0.0025)
        self.assertEqual(self.policy.single_etf_cap_pct, 0.10)
        self.assertEqual(self.policy.single_stock_cap_pct, 0.05)
        self.assertEqual(self.policy.minimum_cash_buffer_pct, 0.20)

    def test_risk_budget_binds_with_wide_stop(self):
        # Risk budget: 50,000 * 0.25% = 125 -> 125 / 5 = 25 shares.
        # Notional cap: 5,000 / 100 = 50 shares. Cash: 40,000 / 100 = 400 shares.
        order = self._size()

        self.assertEqual(order.quantity, 25)
        self.assertAlmostEqual(order.risk_amount, 125.0)
        self.assertEqual(order.symbol, "SPY")
        self.assertEqual(order.side, Side.BUY)
        self.assertEqual(order.asset_type, AssetType.ETF)
        self.assertEqual(order.sleeve, Sleeve.CORE_ETF)
        self.assertEqual(order.limit_price, 100.0)
        self.assertEqual(order.strategy_name, "test")
        self.assertEqual(order.rationale, "test rationale")
        self.assertEqual(order.generated_at, self.generated_at)
        self.assertEqual(order.metadata, {"stop_price": 95.0})
        self.assertIsNone(order.expected_holding_days)

    def test_etf_notional_cap_binds_with_tight_stop(self):
        # Risk: 125 / 1 = 125 shares; ETF cap 10% -> 5,000 / 100 = 50 shares.
        order = self._size(stop_price=99.0)

        self.assertEqual(order.quantity, 50)
        self.assertAlmostEqual(order.notional, 5000.0)
        self.assertAlmostEqual(order.risk_amount, 50.0)

    def test_equity_uses_single_stock_cap(self):
        # Stock cap 5% -> 2,500 / 100 = 25 shares (risk would allow 125).
        order = self._size(
            symbol="aapl",
            asset_type=AssetType.EQUITY,
            sleeve=Sleeve.EQUITY_SATELLITE,
            stop_price=99.0,
        )

        self.assertEqual(order.quantity, 25)
        self.assertEqual(order.symbol, "AAPL")

    def test_cash_buffer_binds(self):
        # Cash above the 20% buffer: 10,300 - 10,000 = 300 -> 3 shares.
        account = AccountState(equity=50000.0, cash=10300.0, peak_equity=50000.0)

        order = self._size(account=account, stop_price=99.0)

        self.assertEqual(order.quantity, 3)

    def test_cash_below_buffer_sizes_to_zero(self):
        account = AccountState(equity=50000.0, cash=5000.0, peak_equity=50000.0)

        order = self._size(account=account)

        self.assertEqual(order.quantity, 0)
        self.assertEqual(order.risk_amount, 0.0)

    def test_quantities_are_floored(self):
        # Risk: 125 / 3 = 41.67 -> 41 shares.
        order = self._size(stop_price=97.0)

        self.assertEqual(order.quantity, 41)
        self.assertAlmostEqual(order.risk_amount, 123.0)

    def test_price_above_notional_budget_sizes_to_zero(self):
        order = self._size(limit_price=6000.0, stop_price=5999.0)

        self.assertEqual(order.quantity, 0)

    def test_zero_equity_sizes_to_zero(self):
        account = AccountState(equity=0.0, cash=0.0, peak_equity=0.0)

        self.assertEqual(self._size(account=account).quantity, 0)

    def test_negative_equity_never_produces_negative_quantity(self):
        account = AccountState(equity=-1000.0, cash=-1000.0, peak_equity=50000.0)

        self.assertEqual(self._size(account=account).quantity, 0)

    def test_rejects_non_positive_limit_price(self):
        for limit_price in (0.0, -1.0):
            with self.subTest(limit_price=limit_price):
                with self.assertRaisesRegex(ValueError, "limit_price"):
                    self._size(limit_price=limit_price, stop_price=-2.0)

    def test_rejects_invalid_stop_price(self):
        for stop_price in (0.0, -5.0, 100.0, 101.0):
            with self.subTest(stop_price=stop_price):
                with self.assertRaisesRegex(ValueError, "stop_price"):
                    self._size(stop_price=stop_price)

    def test_passes_expected_holding_days(self):
        self.assertEqual(self._size(expected_holding_days=20).expected_holding_days, 20)

    def test_default_generated_at_is_set(self):
        order = self._size(generated_at=None)

        self.assertIsInstance(order.generated_at, datetime)

    def test_sized_orders_pass_risk_engine(self):
        engine = RiskEngine(self.policy)
        cases = [
            {},
            {"stop_price": 99.0},
            {"stop_price": 97.0},
            {"symbol": "msft", "asset_type": AssetType.EQUITY, "sleeve": Sleeve.EQUITY_SATELLITE, "stop_price": 99.5},
        ]
        for overrides in cases:
            with self.subTest(**{k: str(v) for k, v in overrides.items()}):
                order = self._size(**overrides)
                decision = engine.evaluate_order(self.account, order, today=date(2026, 7, 6))
                self.assertGreater(order.quantity, 0)
                self.assertLessEqual(order.risk_amount, self.account.equity * self.policy.risk_per_trade_default_pct)
                self.assertTrue(decision.allowed, decision.blocking_checks)


class OrderFromSignalTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()
        self.account = AccountState(equity=50000.0, cash=50000.0, peak_equity=50000.0)

    def _signal(self, **overrides):
        data = {
            "symbol": "qqq",
            "asset_type": AssetType.ETF,
            "sleeve": Sleeve.CORE_ETF,
            "score": 0.12,
            "confidence": 0.62,
            "rationale": "Top momentum ETF.",
            "generated_at": datetime(2026, 7, 6, 13, 0),
            "metadata": {"strategy_name": "etf_rotation_momentum_trend"},
        }
        data.update(overrides)
        return StrategySignal(**data)

    def test_copies_signal_fields_into_order(self):
        signal = self._signal()

        order = order_from_signal(signal, self.account, self.policy, limit_price=400.0, stop_price=380.0, expected_holding_days=21)

        # Risk 125 / 20 = 6 shares; ETF cap 5,000 / 400 = 12 shares.
        self.assertEqual(order.quantity, 6)
        self.assertEqual(order.symbol, "QQQ")
        self.assertEqual(order.asset_type, AssetType.ETF)
        self.assertEqual(order.sleeve, Sleeve.CORE_ETF)
        self.assertEqual(order.strategy_name, "etf_rotation_momentum_trend")
        self.assertEqual(order.rationale, "Top momentum ETF.")
        self.assertEqual(order.generated_at, signal.generated_at)
        self.assertEqual(order.expected_holding_days, 21)
        self.assertEqual(order.metadata["stop_price"], 380.0)

    def test_missing_strategy_name_falls_back(self):
        order = order_from_signal(self._signal(metadata={}), self.account, self.policy, limit_price=400.0, stop_price=380.0)

        self.assertEqual(order.strategy_name, "unknown_strategy")

    def test_equity_signal_uses_stock_cap(self):
        signal = self._signal(symbol="nvda", asset_type=AssetType.EQUITY, sleeve=Sleeve.EQUITY_SATELLITE)

        order = order_from_signal(signal, self.account, self.policy, limit_price=100.0, stop_price=99.0)

        self.assertEqual(order.quantity, 25)
        self.assertEqual(order.sleeve, Sleeve.EQUITY_SATELLITE)

    def test_invalid_prices_raise(self):
        with self.assertRaises(ValueError):
            order_from_signal(self._signal(), self.account, self.policy, limit_price=100.0, stop_price=100.0)


if __name__ == "__main__":
    unittest.main()
