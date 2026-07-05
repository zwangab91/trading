import unittest

from trading_agent.demo import SAMPLE_SYMBOLS, generate_demo_prices, run_demo_backtests


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


if __name__ == "__main__":
    unittest.main()
