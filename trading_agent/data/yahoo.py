from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Sequence


DEFAULT_CACHE_PATH = Path("var/market_data/yahoo_close_prices.csv")


@dataclass(frozen=True)
class YahooPriceData:
    close_prices: object
    source: str
    cache_path: Path
    refreshed: bool


def _require_pandas():
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Install data dependencies with: python3 -m pip install -e '.[dashboard]'"
        ) from exc
    return pd


def _download_yahoo_close_prices(
    symbols: Sequence[str],
    start: str,
    end: Optional[str],
):
    pd = _require_pandas()
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Install yfinance with: python3 -m pip install -e '.[dashboard]'"
        ) from exc

    normalized = [symbol.upper() for symbol in symbols]
    download_end = end
    if download_end is None:
        download_end = (date.today() + timedelta(days=1)).isoformat()

    downloaded = yf.download(
        normalized,
        start=start,
        end=download_end,
        auto_adjust=True,
        progress=False,
        threads=False,
        group_by="column",
    )
    if downloaded.empty:
        raise RuntimeError("Yahoo Finance returned no rows.")

    if hasattr(downloaded.columns, "nlevels") and downloaded.columns.nlevels > 1:
        close_prices = downloaded["Close"].copy()
    else:
        close_prices = downloaded[["Close"]].copy()
        close_prices.columns = normalized[:1]

    if not isinstance(close_prices, pd.DataFrame):
        close_prices = close_prices.to_frame(name=normalized[0])

    close_prices.columns = [str(symbol).upper() for symbol in close_prices.columns]
    missing = [symbol for symbol in normalized if symbol not in close_prices.columns]
    if missing:
        raise RuntimeError(f"Missing downloaded symbols: {missing}")

    close_prices = close_prices[normalized].dropna(how="all").ffill()
    close_prices = close_prices.dropna(axis=1, how="all")
    close_prices.index.name = "Date"
    if close_prices.empty:
        raise RuntimeError("Downloaded close-price frame is empty after cleaning.")
    return close_prices


def load_yahoo_close_prices(
    symbols: Sequence[str],
    start: str = "2021-01-04",
    end: Optional[str] = None,
    cache_path: Path = DEFAULT_CACHE_PATH,
    refresh: bool = False,
) -> YahooPriceData:
    pd = _require_pandas()
    normalized = [symbol.upper() for symbol in symbols]
    cache_path = Path(cache_path)

    if cache_path.exists() and not refresh:
        cached = pd.read_csv(cache_path, parse_dates=["Date"], index_col="Date")
        cached.columns = [str(column).upper() for column in cached.columns]
        missing = [symbol for symbol in normalized if symbol not in cached.columns]
        if not missing:
            return YahooPriceData(
                close_prices=cached[normalized].dropna(how="all").ffill(),
                source="Yahoo Finance adjusted close via yfinance cache",
                cache_path=cache_path,
                refreshed=False,
            )

    close_prices = _download_yahoo_close_prices(normalized, start=start, end=end)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    close_prices.to_csv(cache_path)
    return YahooPriceData(
        close_prices=close_prices,
        source="Yahoo Finance adjusted close via yfinance",
        cache_path=cache_path,
        refreshed=True,
    )

