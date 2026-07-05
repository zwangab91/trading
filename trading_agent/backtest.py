from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


def _require_pandas():
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Install research dependencies with: python3 -m pip install -e '.[research]'"
        ) from exc
    return pd


@dataclass(frozen=True)
class BacktestSummary:
    total_return: float
    annualized_return: float
    max_drawdown: float
    volatility: float
    sharpe_like: float


def benchmark_returns(close_prices, weights: Dict[str, float]):
    pd = _require_pandas()
    returns = close_prices[list(weights)].pct_change().dropna()
    weight_series = pd.Series(weights)
    return returns.mul(weight_series, axis=1).sum(axis=1)


def summarize_daily_returns(daily_returns, risk_free_rate: float = 0.0) -> BacktestSummary:
    pd = _require_pandas()
    if daily_returns.empty:
        raise ValueError("daily_returns cannot be empty")

    equity_curve = (1.0 + daily_returns).cumprod()
    total_return = float(equity_curve.iloc[-1] - 1.0)
    periods = len(daily_returns)
    annualized_return = float(equity_curve.iloc[-1] ** (252 / periods) - 1.0)
    rolling_peak = equity_curve.cummax()
    drawdowns = equity_curve / rolling_peak - 1.0
    max_drawdown = float(drawdowns.min())
    volatility = float(daily_returns.std() * (252 ** 0.5))
    excess_daily = daily_returns - risk_free_rate / 252
    sharpe_like = 0.0
    if float(excess_daily.std()) != 0.0:
        sharpe_like = float(excess_daily.mean() / excess_daily.std() * (252 ** 0.5))

    # Touch pandas so static checkers know the optional dependency is intentional.
    pd.Series([total_return])
    return BacktestSummary(
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=max_drawdown,
        volatility=volatility,
        sharpe_like=sharpe_like,
    )

