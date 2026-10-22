import math
import statistics
import unittest

import pandas as pd

from trading_agent.domain import AssetType, Sleeve
from trading_agent.strategies.equity_momentum import EquityMomentumStrategy
from trading_agent.strategies.etf_rotation import EtfRotationStrategy


def _frame(columns, periods):
    index = pd.bdate_range("2026-01-02", periods=periods)
    return pd.DataFrame({symbol: values(periods) for symbol, values in columns.items()}, index=index)


def _geometric(daily_return, start=100.0):
    return lambda periods: [start * (1.0 + daily_return) ** i for i in range(periods)]


def _noisy(drift, noise, start=100.0):
    """Alternate daily returns of drift + noise and drift - noise."""

    def build(periods):
        values = [start]
        for i in range(1, periods):
            step = drift + (noise if i % 2 else -noise)
            values.append(values[-1] * (1.0 + step))
        return values

    return build


class EtfRotationStrategyTests(unittest.TestCase):
    def _strategy(self, universe=("AAA", "BBB", "CCC", "DDD"), top_n=2):
        return EtfRotationStrategy(universe, lookback_days=5, trend_days=10, top_n=top_n)

    def test_ranks_uptrending_symbols_by_momentum(self):
        prices = _frame(
            {
                "AAA": _geometric(0.010),
                "BBB": _geometric(0.005),
                "CCC": _geometric(0.002),
                "DDD": _geometric(-0.010),
            },
            periods=30,
        )

        signals = list(self._strategy().generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["AAA", "BBB"])
        self.assertAlmostEqual(signals[0].score, 1.01**5 - 1.0)
        self.assertAlmostEqual(signals[1].score, 1.005**5 - 1.0)
        for signal in signals:
            self.assertEqual(signal.asset_type, AssetType.ETF)
            self.assertEqual(signal.sleeve, Sleeve.CORE_ETF)
            self.assertEqual(signal.metadata["strategy_name"], "etf_rotation_momentum_trend")
            self.assertIn("top 2", signal.rationale)

    def test_excludes_symbols_below_trend_filter(self):
        prices = _frame(
            {"AAA": _geometric(-0.010), "BBB": _geometric(-0.002), "CCC": _geometric(0.001)},
            periods=30,
        )

        signals = list(self._strategy(universe=("AAA", "BBB", "CCC"), top_n=3).generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["CCC"])

    def test_returns_no_signals_when_everything_is_in_downtrend(self):
        prices = _frame({"AAA": _geometric(-0.01), "BBB": _geometric(-0.02)}, periods=30)

        signals = list(self._strategy(universe=("AAA", "BBB")).generate_signals(prices))

        self.assertEqual(signals, [])

    def test_requires_more_rows_than_longest_window(self):
        strategy = self._strategy()
        columns = {"AAA": _geometric(0.01), "BBB": _geometric(0.01), "CCC": _geometric(0.01), "DDD": _geometric(0.01)}

        self.assertEqual(list(strategy.generate_signals(_frame(columns, periods=10))), [])
        self.assertEqual(len(list(strategy.generate_signals(_frame(columns, periods=11)))), 2)

    def test_default_windows_need_201_rows(self):
        strategy = EtfRotationStrategy(["spy", "qqq"])
        columns = {"SPY": _geometric(0.001), "QQQ": _geometric(0.002)}

        self.assertEqual(strategy.universe, ("SPY", "QQQ"))
        self.assertEqual(list(strategy.generate_signals(_frame(columns, periods=200))), [])
        signals = list(strategy.generate_signals(_frame(columns, periods=201)))
        self.assertEqual([signal.symbol for signal in signals], ["QQQ", "SPY"])

    def test_empty_frame_returns_no_signals(self):
        self.assertEqual(list(self._strategy().generate_signals(pd.DataFrame())), [])

    def test_ties_are_all_returned_when_within_top_n(self):
        prices = _frame(
            {"AAA": _geometric(0.004), "BBB": _geometric(0.004), "CCC": _geometric(0.001)},
            periods=30,
        )

        signals = list(self._strategy(universe=("AAA", "BBB", "CCC"), top_n=2).generate_signals(prices))

        self.assertEqual({signal.symbol for signal in signals}, {"AAA", "BBB"})
        self.assertAlmostEqual(signals[0].score, signals[1].score)

    def test_top_n_limits_signal_count(self):
        prices = _frame({symbol: _geometric(0.001 * (i + 1)) for i, symbol in enumerate("ABCDE")}, periods=30)

        signals = list(self._strategy(universe=tuple("ABCDE"), top_n=3).generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["E", "D", "C"])

    def test_ignores_columns_outside_universe(self):
        prices = _frame({"AAA": _geometric(0.001), "ZZZ": _geometric(0.05)}, periods=30)

        signals = list(self._strategy(universe=("AAA",), top_n=3).generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["AAA"])

    def test_missing_universe_column_raises(self):
        prices = _frame({"AAA": _geometric(0.001)}, periods=30)

        with self.assertRaises(KeyError):
            list(self._strategy(universe=("AAA", "BBB")).generate_signals(prices))

    def test_symbol_with_missing_history_is_skipped(self):
        prices = _frame({"AAA": _geometric(0.002), "BBB": _geometric(0.010)}, periods=30)
        prices.loc[prices.index[:25], "BBB"] = float("nan")

        signals = list(self._strategy(universe=("AAA", "BBB")).generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["AAA"])

    def test_confidence_is_clamped(self):
        prices = _frame({"FAST": _geometric(0.20), "SLOW": _geometric(0.0001)}, periods=30)

        signals = list(self._strategy(universe=("FAST", "SLOW")).generate_signals(prices))
        by_symbol = {signal.symbol: signal for signal in signals}

        self.assertEqual(by_symbol["FAST"].confidence, 0.95)
        self.assertAlmostEqual(by_symbol["SLOW"].confidence, 0.50 + by_symbol["SLOW"].score)

    def test_confidence_floor_for_negative_momentum_above_trend(self):
        # Long rally then a short pullback: still above the 20-day average but
        # with negative 3-day momentum.
        values = [100.0 * 1.02**i for i in range(30)] + [100.0 * 1.02**29 * 0.99**i for i in range(1, 4)]
        prices = pd.DataFrame({"AAA": values}, index=pd.bdate_range("2026-01-02", periods=len(values)))
        strategy = EtfRotationStrategy(("AAA",), lookback_days=3, trend_days=20, top_n=1)

        signals = list(strategy.generate_signals(prices))

        self.assertEqual(len(signals), 1)
        self.assertLess(signals[0].score, 0.0)
        self.assertEqual(signals[0].confidence, 0.50)


class EquityMomentumStrategyTests(unittest.TestCase):
    def _strategy(self, universe, top_n=10):
        return EquityMomentumStrategy(universe, lookback_days=10, volatility_days=6, top_n=top_n)

    def _expected_score(self, values, lookback=10, vol_days=6):
        momentum = values[-1] / values[-1 - lookback] - 1.0
        returns = [values[i] / values[i - 1] - 1.0 for i in range(len(values) - vol_days, len(values))]
        return momentum / statistics.stdev(returns)

    def test_ranks_by_volatility_adjusted_momentum(self):
        builders = {
            # Same drift, different noise: lower volatility wins.
            "CALM": _noisy(0.005, 0.002),
            "WILD": _noisy(0.005, 0.020),
            "FLAT": _noisy(0.000, 0.010),
        }
        prices = _frame(builders, periods=40)

        signals = list(self._strategy(("CALM", "WILD", "FLAT")).generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["CALM", "WILD", "FLAT"])
        for signal in signals:
            expected = self._expected_score(list(prices[signal.symbol]))
            self.assertAlmostEqual(signal.score, expected, places=6)
            self.assertEqual(signal.asset_type, AssetType.EQUITY)
            self.assertEqual(signal.sleeve, Sleeve.EQUITY_SATELLITE)
            self.assertEqual(signal.metadata["strategy_name"], "equity_cross_sectional_momentum")

    def test_negative_momentum_symbols_are_still_ranked(self):
        # Documents current behaviour: there is no absolute-momentum filter, so
        # losers fill remaining slots when top_n exceeds the number of winners.
        prices = _frame({"UP": _noisy(0.004, 0.01), "DOWN": _noisy(-0.004, 0.01)}, periods=40)

        signals = list(self._strategy(("UP", "DOWN")).generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["UP", "DOWN"])
        self.assertLess(signals[1].score, 0.0)
        self.assertEqual(signals[1].confidence, 0.50)

    def test_top_n_limits_signal_count(self):
        prices = _frame({f"S{i}": _noisy(0.001 * i, 0.01) for i in range(1, 6)}, periods=40)

        signals = list(self._strategy(tuple(f"S{i}" for i in range(1, 6)), top_n=2).generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["S5", "S4"])

    def test_requires_more_rows_than_longest_window(self):
        columns = {"AAA": _noisy(0.002, 0.01)}
        strategy = self._strategy(("AAA",))

        self.assertEqual(list(strategy.generate_signals(_frame(columns, periods=10))), [])
        self.assertEqual(len(list(strategy.generate_signals(_frame(columns, periods=11)))), 1)

    def test_default_windows_need_127_rows(self):
        strategy = EquityMomentumStrategy(["aapl"])
        columns = {"AAPL": _noisy(0.001, 0.01)}

        self.assertEqual(strategy.universe, ("AAPL",))
        self.assertEqual(list(strategy.generate_signals(_frame(columns, periods=126))), [])
        self.assertEqual(len(list(strategy.generate_signals(_frame(columns, periods=127)))), 1)

    def test_empty_frame_returns_no_signals(self):
        self.assertEqual(list(self._strategy(("AAA",)).generate_signals(pd.DataFrame())), [])

    def test_zero_volatility_symbols_are_dropped(self):
        # Doubling every day gives exactly constant returns (std == 0 -> inf
        # score); a constant price gives 0/0 (NaN). Both must be excluded.
        prices = _frame(
            {
                "DOUBLE": lambda periods: [2.0**i for i in range(periods)],
                "CONST": lambda periods: [50.0] * periods,
                "OK": _noisy(0.002, 0.01),
            },
            periods=20,
        )

        signals = list(self._strategy(("DOUBLE", "CONST", "OK")).generate_signals(prices))

        self.assertEqual([signal.symbol for signal in signals], ["OK"])
        self.assertTrue(math.isfinite(signals[0].score))

    def test_ties_are_all_returned_when_within_top_n(self):
        prices = _frame({"AAA": _noisy(0.003, 0.01), "BBB": _noisy(0.003, 0.01)}, periods=40)

        signals = list(self._strategy(("AAA", "BBB"), top_n=2).generate_signals(prices))

        self.assertEqual({signal.symbol for signal in signals}, {"AAA", "BBB"})
        self.assertAlmostEqual(signals[0].score, signals[1].score)

    def test_confidence_is_clamped(self):
        prices = _frame({"HOT": _noisy(0.05, 0.001), "MILD": _noisy(0.0002, 0.01)}, periods=40)

        signals = list(self._strategy(("HOT", "MILD")).generate_signals(prices))
        by_symbol = {signal.symbol: signal for signal in signals}

        self.assertEqual(by_symbol["HOT"].confidence, 0.90)
        self.assertAlmostEqual(by_symbol["MILD"].confidence, 0.50 + by_symbol["MILD"].score / 10.0)
        for signal in signals:
            self.assertGreaterEqual(signal.confidence, 0.50)
            self.assertLessEqual(signal.confidence, 0.90)

    def test_missing_universe_column_raises(self):
        prices = _frame({"AAA": _noisy(0.002, 0.01)}, periods=40)

        with self.assertRaises(KeyError):
            list(self._strategy(("AAA", "BBB")).generate_signals(prices))


if __name__ == "__main__":
    unittest.main()
