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
    total_turnover: float = 0.0
    total_cost_drag: float = 0.0


def benchmark_returns(close_prices, weights: Dict[str, float]):
    pd = _require_pandas()
    returns = close_prices[list(weights)].pct_change().dropna()
    weight_series = pd.Series(weights)
    return returns.mul(weight_series, axis=1).sum(axis=1)


def _validate_bps(name: str, value: float) -> float:
    value = float(value)
    if not value >= 0.0:  # also rejects NaN
        raise ValueError(f"{name} must be a non-negative number of basis points")
    return value


def _align_target_weights(pd, close_prices, target_weights):
    missing = [column for column in target_weights.columns if column not in close_prices.columns]
    if missing:
        raise ValueError(f"target_weights columns missing from close_prices: {missing}")
    # Weights given only on rebalance days are held until the next rebalance.
    aligned = target_weights.reindex(close_prices.index).ffill().fillna(0.0)
    return aligned.astype(float)


def portfolio_turnover(close_prices, target_weights):
    """Sum of absolute target-weight changes per day, indexed like close_prices.

    The first day counts the move from all cash into the initial weights.
    """
    pd = _require_pandas()
    weights = _align_target_weights(pd, close_prices, target_weights)
    return weights.diff().fillna(weights).abs().sum(axis=1)


def transaction_costs(
    close_prices,
    target_weights,
    cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
):
    """Daily cost drag, as a fraction of equity, charged on each day's turnover."""
    rate = (_validate_bps("cost_bps", cost_bps) + _validate_bps("slippage_bps", slippage_bps)) / 10_000
    return portfolio_turnover(close_prices, target_weights) * rate


def portfolio_returns(
    close_prices,
    target_weights,
    cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
):
    """Net daily returns of a portfolio rebalanced to target weights at each close.

    Weights set at the close of day t earn the day t+1 return. Costs are
    charged as (cost_bps + slippage_bps) / 10,000 times the turnover of the
    rebalance, deducted from the return of the following day.
    """
    pd = _require_pandas()
    weights = _align_target_weights(pd, close_prices, target_weights)
    costs = transaction_costs(close_prices, target_weights, cost_bps, slippage_bps)
    asset_returns = close_prices[list(weights.columns)].pct_change()
    gross = asset_returns.mul(weights.shift(1), axis=1).sum(axis=1)
    net = gross - costs.shift(1)
    return net.iloc[1:]


def summarize_daily_returns(
    daily_returns,
    risk_free_rate: float = 0.0,
    *,
    turnover=None,
    costs=None,
) -> BacktestSummary:
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
        total_turnover=0.0 if turnover is None else float(turnover.sum()),
        total_cost_drag=0.0 if costs is None else float(costs.sum()),
    )

