import unittest

import pandas as pd

from trading_agent.backtest import (
    benchmark_returns,
    portfolio_returns,
    portfolio_turnover,
    summarize_daily_returns,
    transaction_costs,
)


def _prices():
    index = pd.date_range("2024-01-01", periods=5, freq="B")
    return pd.DataFrame(
        {
            "AAA": [100.0, 101.0, 99.0, 102.0, 103.0],
            "BBB": [50.0, 50.5, 51.0, 50.0, 52.0],
        },
        index=index,
    )


def _rotating_weights(prices):
    # All AAA, then switch fully to BBB on day 2 (turnover 2.0 on that day).
    return pd.DataFrame(
        {
            "AAA": [1.0, 1.0, 0.0, 0.0, 0.0],
            "BBB": [0.0, 0.0, 1.0, 1.0, 1.0],
        },
        index=prices.index,
    )


class PortfolioReturnsTests(unittest.TestCase):
    def test_zero_costs_match_gross_returns(self):
        prices = _prices()
        weights = _rotating_weights(prices)

        net = portfolio_returns(prices, weights)
        expected = prices.pct_change().mul(weights.shift(1), axis=1).sum(axis=1).iloc[1:]

        pd.testing.assert_series_equal(net, expected)

    def test_constant_weights_match_benchmark_returns(self):
        prices = _prices()
        weights = pd.DataFrame({"AAA": 0.5, "BBB": 0.5}, index=prices.index)

        net = portfolio_returns(prices, weights)
        benchmark = benchmark_returns(prices, {"AAA": 0.5, "BBB": 0.5})

        pd.testing.assert_series_equal(net, benchmark, check_names=False)

    def test_costs_reduce_returns_by_turnover_times_rate(self):
        prices = _prices()
        weights = _rotating_weights(prices)

        gross = portfolio_returns(prices, weights)
        net = portfolio_returns(prices, weights, cost_bps=5.0, slippage_bps=5.0)
        drag = gross - net

        # Initial entry (turnover 1.0) is charged on day 1; the switch (2.0) on day 3.
        expected = pd.Series([0.001, 0.0, 0.002, 0.0], index=prices.index[1:])
        pd.testing.assert_series_equal(drag, expected, check_names=False)

    def test_no_turnover_means_no_cost(self):
        prices = _prices()
        weights = pd.DataFrame({"AAA": 0.0, "BBB": 0.0}, index=prices.index)

        net = portfolio_returns(prices, weights, cost_bps=10.0, slippage_bps=25.0)
        costs = transaction_costs(prices, weights, cost_bps=10.0, slippage_bps=25.0)

        self.assertTrue((net == 0.0).all())
        self.assertEqual(float(costs.sum()), 0.0)

    def test_held_weights_only_charge_on_rebalance_days(self):
        prices = _prices()
        sparse = pd.DataFrame(
            {"AAA": [1.0, 0.0], "BBB": [0.0, 1.0]},
            index=[prices.index[0], prices.index[2]],
        )

        turnover = portfolio_turnover(prices, sparse)

        self.assertEqual(list(turnover), [1.0, 0.0, 2.0, 0.0, 0.0])

    def test_rejects_negative_bps(self):
        prices = _prices()
        weights = _rotating_weights(prices)

        with self.assertRaises(ValueError):
            portfolio_returns(prices, weights, cost_bps=-1.0)
        with self.assertRaises(ValueError):
            portfolio_returns(prices, weights, slippage_bps=-0.5)
        with self.assertRaises(ValueError):
            transaction_costs(prices, weights, cost_bps=float("nan"))

    def test_rejects_weight_columns_missing_from_prices(self):
        prices = _prices()
        weights = pd.DataFrame({"AAA": 0.5, "ZZZ": 0.5}, index=prices.index)

        with self.assertRaises(ValueError):
            portfolio_returns(prices, weights)


class SummaryTests(unittest.TestCase):
    def test_summary_defaults_have_zero_turnover_and_cost(self):
        prices = _prices()
        summary = summarize_daily_returns(benchmark_returns(prices, {"AAA": 1.0}))

        self.assertEqual(summary.total_turnover, 0.0)
        self.assertEqual(summary.total_cost_drag, 0.0)

    def test_summary_reports_turnover_and_cost_drag(self):
        prices = _prices()
        weights = _rotating_weights(prices)
        net = portfolio_returns(prices, weights, cost_bps=10.0)

        summary = summarize_daily_returns(
            net,
            turnover=portfolio_turnover(prices, weights),
            costs=transaction_costs(prices, weights, cost_bps=10.0),
        )

        self.assertAlmostEqual(summary.total_turnover, 3.0)
        self.assertAlmostEqual(summary.total_cost_drag, 0.003)


if __name__ == "__main__":
    unittest.main()
