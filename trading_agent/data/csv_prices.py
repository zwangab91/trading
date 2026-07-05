from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional


def _require_pandas():
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Install research dependencies with: python3 -m pip install -e '.[research]'"
        ) from exc
    return pd


def load_close_prices(path: Path, symbols: Optional[Iterable[str]] = None):
    """Load long-form CSV prices into a date x symbol close-price frame.

    Expected columns: date, symbol, close.
    """
    pd = _require_pandas()
    frame = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "symbol", "close"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frame["symbol"] = frame["symbol"].str.upper()
    if symbols is not None:
        allowed = {symbol.upper() for symbol in symbols}
        frame = frame[frame["symbol"].isin(allowed)]
    return frame.pivot(index="date", columns="symbol", values="close").sort_index()
