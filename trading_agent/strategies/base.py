from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from trading_agent.domain import StrategySignal


class Strategy(ABC):
    name: str

    @abstractmethod
    def generate_signals(self, close_prices) -> Iterable[StrategySignal]:
        raise NotImplementedError


def require_pandas():
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Install research dependencies with: python3 -m pip install -e '.[research]'"
        ) from exc
    return pd

