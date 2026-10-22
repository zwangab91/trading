import tempfile
import unittest
from pathlib import Path

import pandas as pd

from trading_agent.data.csv_prices import load_close_prices


class LoadClosePricesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def _write(self, text, name="prices.csv"):
        path = self.dir / name
        path.write_text(text)
        return path

    def test_pivots_long_csv_into_date_by_symbol_frame(self):
        path = self._write(
            "date,symbol,close\n"
            "2026-07-07,SPY,501.0\n"
            "2026-07-06,SPY,500.0\n"
            "2026-07-06,QQQ,450.0\n"
            "2026-07-07,QQQ,452.5\n"
        )

        frame = load_close_prices(path)

        self.assertEqual(list(frame.columns), ["QQQ", "SPY"])
        self.assertEqual(list(frame.index), [pd.Timestamp("2026-07-06"), pd.Timestamp("2026-07-07")])
        self.assertTrue(frame.index.is_monotonic_increasing)
        self.assertEqual(frame.loc["2026-07-07", "QQQ"], 452.5)
        self.assertEqual(frame.loc["2026-07-06", "SPY"], 500.0)

    def test_normalizes_symbols_to_upper_case(self):
        path = self._write("date,symbol,close\n2026-07-06,spy,500.0\n2026-07-06,Qqq,450.0\n")

        frame = load_close_prices(path)

        self.assertEqual(sorted(frame.columns), ["QQQ", "SPY"])

    def test_filters_to_requested_symbols_case_insensitively(self):
        path = self._write(
            "date,symbol,close\n"
            "2026-07-06,SPY,500.0\n"
            "2026-07-06,QQQ,450.0\n"
            "2026-07-06,IWM,200.0\n"
        )

        frame = load_close_prices(path, symbols=["spy", "IwM"])

        self.assertEqual(sorted(frame.columns), ["IWM", "SPY"])

    def test_filter_with_no_matches_returns_empty_frame(self):
        path = self._write("date,symbol,close\n2026-07-06,SPY,500.0\n")

        frame = load_close_prices(path, symbols=["TLT"])

        self.assertTrue(frame.empty)

    def test_empty_symbol_filter_returns_empty_frame(self):
        path = self._write("date,symbol,close\n2026-07-06,SPY,500.0\n")

        self.assertTrue(load_close_prices(path, symbols=[]).empty)

    def test_header_only_file_returns_empty_frame(self):
        path = self._write("date,symbol,close\n")

        self.assertTrue(load_close_prices(path).empty)

    def test_missing_values_become_nan(self):
        path = self._write(
            "date,symbol,close\n"
            "2026-07-06,SPY,500.0\n"
            "2026-07-06,QQQ,450.0\n"
            "2026-07-07,SPY,501.0\n"
        )

        frame = load_close_prices(path)

        self.assertTrue(pd.isna(frame.loc["2026-07-07", "QQQ"]))

    def test_extra_columns_are_ignored(self):
        path = self._write(
            "date,symbol,open,close,volume\n"
            "2026-07-06,SPY,499.0,500.0,1000\n"
        )

        frame = load_close_prices(path)

        self.assertEqual(list(frame.columns), ["SPY"])
        self.assertEqual(frame.iloc[0, 0], 500.0)

    def test_missing_close_column_raises(self):
        path = self._write("date,symbol,price\n2026-07-06,SPY,500.0\n")

        with self.assertRaisesRegex(ValueError, r"Missing required columns: \['close'\]"):
            load_close_prices(path)

    def test_missing_symbol_and_close_columns_are_both_reported(self):
        path = self._write("date,ticker,price\n2026-07-06,SPY,500.0\n")

        with self.assertRaisesRegex(ValueError, r"\['close', 'symbol'\]"):
            load_close_prices(path)

    def test_missing_date_column_reports_required_columns(self):
        path = self._write("day,symbol,close\n2026-07-06,SPY,500.0\n")

        with self.assertRaisesRegex(ValueError, r"Missing required columns: \['date'\]"):
            load_close_prices(path)

    def test_missing_date_column_still_raises_value_error(self):
        path = self._write("day,symbol,close\n2026-07-06,SPY,500.0\n")

        with self.assertRaises(ValueError):
            load_close_prices(path)

    def test_duplicate_date_symbol_rows_raise(self):
        path = self._write(
            "date,symbol,close\n"
            "2026-07-06,SPY,500.0\n"
            "2026-07-06,spy,501.0\n"
        )

        with self.assertRaises(ValueError):
            load_close_prices(path)

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_close_prices(self.dir / "nope.csv")


if __name__ == "__main__":
    unittest.main()
