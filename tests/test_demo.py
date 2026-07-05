import unittest

from trading_agent.demo import SAMPLE_SYMBOLS, TRADE_HISTORY_COLUMNS, generate_demo_prices, run_demo_backtests


class DemoBacktestTests(unittest.TestCase):
    def test_demo_prices_include_sample_universe(self):
        prices = generate_demo_prices()

        self.assertGreater(len(prices), 1000)
        self.assertTrue(set(SAMPLE_SYMBOLS).issubset(set(prices.columns)))
        self.assertFalse(prices.isna().any().any())

    def test_demo_backtests_include_expected_strategies(self):
        demo = run_demo_backtests(use_real_data=False)

        expected = {
            "50/50 SPY/QQQ",
            "ETF Equal Weight",
            "ETF Momentum Rotation",
            "ETF Defensive Trend",
            "Equity Momentum",
            "70/30 Combined Policy",
        }
        self.assertEqual(set(demo.results), expected)
        self.assertEqual(len(demo.summary_table), len(expected))
        self.assertFalse(demo.summary_table.isna().any().any())

    def test_latest_weights_do_not_exceed_full_capital(self):
        demo = run_demo_backtests(use_real_data=False)

        for result in demo.results.values():
            self.assertLessEqual(float(result.latest_weights.sum()), 1.000001)

    def test_trade_history_is_emitted_for_each_strategy(self):
        demo = run_demo_backtests(use_real_data=False)

        self.assertEqual(list(demo.trade_history.columns), list(TRADE_HISTORY_COLUMNS))
        for result in demo.results.values():
            self.assertEqual(list(result.trade_history.columns), list(TRADE_HISTORY_COLUMNS))
            self.assertGreater(len(result.trade_history), 0)
            self.assertFalse(result.trade_history["Symbol"].isna().any())

    def test_buy_hold_strategies_only_emit_initial_entries_and_marks(self):
        demo = run_demo_backtests(use_real_data=False)

        for strategy_name in ("50/50 SPY/QQQ", "ETF Equal Weight"):
            trades = demo.results[strategy_name].trade_history
            self.assertEqual(set(trades["Action"]), {"Entry", "Mark"})
            self.assertEqual(trades[trades["Action"] == "Entry"]["Trade Date"].nunique(), 1)

    def test_rebalanced_strategies_emit_mid_period_trades(self):
        demo = run_demo_backtests(use_real_data=False)
        first_date = demo.prices.index[0]

        for strategy_name in ("ETF Momentum Rotation", "ETF Defensive Trend", "Equity Momentum"):
            trades = demo.results[strategy_name].trade_history
            executions = trades[trades["Action"] != "Mark"]
            self.assertGreater(executions["Trade Date"].nunique(), 1)
            self.assertGreater(executions["Trade Date"].min(), first_date)
            self.assertTrue({"Entry", "Trim", "Exit"}.intersection(set(executions["Action"])))

    def test_combined_trade_history_scales_underlying_sleeves(self):
        demo = run_demo_backtests(use_real_data=False)
        trades = demo.results["70/30 Combined Policy"].trade_history

        self.assertEqual(
            set(trades["Source Strategy"]),
            {"ETF Momentum Rotation", "Equity Momentum"},
        )
        self.assertLessEqual(float(trades["Target Weight"].abs().max()), 0.70)


if __name__ == "__main__":
    unittest.main()
