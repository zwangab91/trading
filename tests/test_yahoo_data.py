import tempfile
import unittest
from pathlib import Path

import pandas as pd

from trading_agent.data.yahoo import load_yahoo_close_prices


class YahooDataLoaderTests(unittest.TestCase):
    def test_loads_cached_prices_without_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "prices.csv"
            frame = pd.DataFrame(
                {
                    "Date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                    "SPY": [470.0, 471.0],
                    "QQQ": [400.0, 402.0],
                }
            )
            frame.to_csv(cache_path, index=False)

            loaded = load_yahoo_close_prices(
                ["SPY", "QQQ"],
                cache_path=cache_path,
                refresh=False,
            )

        self.assertFalse(loaded.refreshed)
        self.assertEqual(list(loaded.close_prices.columns), ["SPY", "QQQ"])
        self.assertEqual(len(loaded.close_prices), 2)


if __name__ == "__main__":
    unittest.main()

