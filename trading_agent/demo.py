from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence

from trading_agent.backtest import BacktestSummary, benchmark_returns, summarize_daily_returns
from trading_agent.data.yahoo import load_yahoo_close_prices


SAMPLE_ETFS = ("SPY", "QQQ", "IWM", "TLT", "IEF", "GLD")
SAMPLE_STOCKS = ("AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "XOM", "UNH", "COST")
SAMPLE_SYMBOLS = SAMPLE_ETFS + SAMPLE_STOCKS


@dataclass(frozen=True)
class StrategyResult:
    name: str
    sleeve: str
    description: str
    daily_returns: object
    equity_curve: object
    drawdown: object
    latest_weights: object
    summary: BacktestSummary
    ending_value: float


@dataclass(frozen=True)
class DemoBacktestResult:
    prices: object
    results: Mapping[str, StrategyResult]
    summary_table: object
    equity_curves: object
    drawdowns: object
    data_source: str
    is_real_data: bool
    data_error: str


def _require_pandas_numpy():
    try:
        import numpy as np  # type: ignore
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Install demo dependencies with: python3 -m pip install -e '.[research,dashboard]'"
        ) from exc
    return pd, np


def generate_demo_prices(
    start: str = "2021-01-04",
    end: str = "2026-06-30",
    seed: int = 1,
):
    """Generate deterministic sample prices for dashboard and strategy demos.

    These are synthetic market-like paths. They are useful for validating the
    dashboard and calculation pipeline, but they are not evidence of strategy
    performance on real markets.
    """
    pd, np = _require_pandas_numpy()
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, end=end)
    count = len(dates)

    market = rng.normal(0.00034, 0.0080, count)
    rates = rng.normal(0.00002, 0.0055, count)
    commodity = rng.normal(0.00008, 0.0075, count)

    # Add broad regimes so trend and defensive strategies have something to react to.
    market[int(count * 0.20) : int(count * 0.32)] += -0.0011
    market[int(count * 0.48) : int(count * 0.58)] += 0.0012
    market[int(count * 0.76) : int(count * 0.83)] += -0.0008
    rates[int(count * 0.20) : int(count * 0.32)] += 0.0009
    rates[int(count * 0.76) : int(count * 0.83)] += -0.0007

    params: Dict[str, Dict[str, float]] = {
        "SPY": {"start": 375.0, "drift": 0.00025, "market": 1.00, "rates": -0.05, "commodity": 0.00, "idio": 0.0025},
        "QQQ": {"start": 315.0, "drift": 0.00034, "market": 1.25, "rates": -0.10, "commodity": 0.00, "idio": 0.0045},
        "IWM": {"start": 190.0, "drift": 0.00020, "market": 1.15, "rates": -0.06, "commodity": 0.00, "idio": 0.0060},
        "TLT": {"start": 155.0, "drift": 0.00002, "market": -0.20, "rates": 1.15, "commodity": 0.00, "idio": 0.0040},
        "IEF": {"start": 115.0, "drift": 0.00004, "market": -0.10, "rates": 0.60, "commodity": 0.00, "idio": 0.0020},
        "GLD": {"start": 175.0, "drift": 0.00010, "market": -0.05, "rates": 0.10, "commodity": 0.75, "idio": 0.0040},
        "AAPL": {"start": 130.0, "drift": 0.00034, "market": 1.18, "rates": -0.08, "commodity": 0.00, "idio": 0.0080},
        "MSFT": {"start": 220.0, "drift": 0.00033, "market": 1.10, "rates": -0.06, "commodity": 0.00, "idio": 0.0070},
        "NVDA": {"start": 130.0, "drift": 0.00054, "market": 1.55, "rates": -0.12, "commodity": 0.00, "idio": 0.0140},
        "AMZN": {"start": 160.0, "drift": 0.00028, "market": 1.25, "rates": -0.08, "commodity": 0.00, "idio": 0.0090},
        "META": {"start": 270.0, "drift": 0.00030, "market": 1.35, "rates": -0.08, "commodity": 0.00, "idio": 0.0100},
        "GOOGL": {"start": 90.0, "drift": 0.00029, "market": 1.15, "rates": -0.07, "commodity": 0.00, "idio": 0.0080},
        "JPM": {"start": 125.0, "drift": 0.00014, "market": 1.05, "rates": 0.10, "commodity": 0.00, "idio": 0.0075},
        "XOM": {"start": 45.0, "drift": 0.00013, "market": 0.80, "rates": 0.02, "commodity": 0.45, "idio": 0.0085},
        "UNH": {"start": 350.0, "drift": 0.00017, "market": 0.75, "rates": -0.02, "commodity": 0.00, "idio": 0.0065},
        "COST": {"start": 375.0, "drift": 0.00020, "market": 0.70, "rates": -0.03, "commodity": 0.00, "idio": 0.0060},
    }

    prices = {}
    for symbol, values in params.items():
        idiosyncratic = rng.normal(0.0, values["idio"], count)
        daily = (
            values["drift"]
            + values["market"] * market
            + values["rates"] * rates
            + values["commodity"] * commodity
            + idiosyncratic
        )
        daily = np.clip(daily, -0.16, 0.16)
        prices[symbol] = values["start"] * np.cumprod(1.0 + daily)

    return pd.DataFrame(prices, index=dates)


def _drawdown(equity_curve):
    rolling_peak = equity_curve.cummax()
    return equity_curve / rolling_peak - 1.0


def _empty_weights(pd, columns):
    return pd.Series(0.0, index=columns, dtype=float)


def _normalize_weights(pd, columns, raw_weights: Mapping[str, float]):
    weights = _empty_weights(pd, columns)
    total = sum(max(0.0, weight) for weight in raw_weights.values())
    if total <= 0:
        return weights
    for symbol, weight in raw_weights.items():
        if symbol in weights.index:
            weights.loc[symbol] = max(0.0, weight) / total
    return weights


def _run_rebalanced_strategy(
    prices,
    selector,
    start_index: int,
    rebalance_interval: int = 21,
    transaction_cost_bps: float = 5.0,
):
    pd, _ = _require_pandas_numpy()
    asset_returns = prices.pct_change().fillna(0.0)
    strategy_returns = pd.Series(0.0, index=prices.index, dtype=float)
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    current_weights = _empty_weights(pd, prices.columns)

    for index in range(1, len(prices)):
        cost = 0.0
        signal_index = index - 1
        if signal_index >= start_index and (signal_index - start_index) % rebalance_interval == 0:
            new_weights = selector(prices.iloc[:index])
            turnover = float((new_weights - current_weights).abs().sum())
            cost = turnover * transaction_cost_bps / 10000.0
            current_weights = new_weights
        weights.iloc[index] = current_weights
        strategy_returns.iloc[index] = float((current_weights * asset_returns.iloc[index]).sum()) - cost

    return strategy_returns, weights


def _buy_hold_returns(prices, symbols: Sequence[str], transaction_cost_bps: float = 2.0):
    pd, _ = _require_pandas_numpy()
    asset_returns = prices[list(symbols)].pct_change().fillna(0.0)
    base_weights = pd.Series(1.0 / len(symbols), index=list(symbols), dtype=float)
    daily = asset_returns.mul(base_weights, axis=1).sum(axis=1)
    if len(daily) > 1:
        daily.iloc[1] -= transaction_cost_bps / 10000.0
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for symbol in symbols:
        weights[symbol] = 1.0 / len(symbols)
    return daily, weights


def _etf_momentum_selector(pd, columns, history):
    lookback = 126
    trend = 200
    tradable = [symbol for symbol in SAMPLE_ETFS if symbol in history.columns]
    if len(history) < trend or not tradable:
        return _empty_weights(pd, columns)

    latest = history[tradable].iloc[-1]
    momentum = history[tradable].pct_change(lookback).iloc[-1]
    trend_average = history[tradable].rolling(trend).mean().iloc[-1]
    eligible = momentum[(latest > trend_average) & momentum.notna()].sort_values(ascending=False)
    selected = list(eligible.head(3).index)
    if selected:
        return _normalize_weights(pd, columns, {symbol: 1.0 for symbol in selected})

    fallback = {symbol: weight for symbol, weight in {"IEF": 0.60, "TLT": 0.30, "GLD": 0.10}.items() if symbol in columns}
    return _normalize_weights(pd, columns, fallback)


def _defensive_trend_selector(pd, columns, history):
    if len(history) < 200 or "SPY" not in history.columns:
        return _empty_weights(pd, columns)

    spy = history["SPY"]
    risk_on = float(spy.iloc[-1]) > float(spy.rolling(200).mean().iloc[-1])
    if risk_on:
        return _normalize_weights(pd, columns, {"SPY": 0.45, "QQQ": 0.35, "IWM": 0.20})
    return _normalize_weights(pd, columns, {"IEF": 0.55, "TLT": 0.30, "GLD": 0.15})


def _equity_momentum_selector(pd, columns, history):
    lookback = 126
    volatility_window = 63
    trend = 200
    tradable = [symbol for symbol in SAMPLE_STOCKS if symbol in history.columns]
    if len(history) < trend or not tradable:
        return _empty_weights(pd, columns)

    stock_prices = history[tradable]
    returns = stock_prices.pct_change()
    momentum = stock_prices.pct_change(lookback).iloc[-1]
    volatility = returns.rolling(volatility_window).std().iloc[-1]
    trend_average = stock_prices.rolling(trend).mean().iloc[-1]
    latest = stock_prices.iloc[-1]
    score = (momentum / volatility).replace([float("inf"), -float("inf")], pd.NA)
    ranked = score[(latest > trend_average) & score.notna()].sort_values(ascending=False)
    selected = list(ranked.head(5).index)
    return _normalize_weights(pd, columns, {symbol: 1.0 for symbol in selected})


def _make_result(
    name: str,
    sleeve: str,
    description: str,
    daily_returns,
    weights,
    initial_capital: float,
) -> StrategyResult:
    equity_curve = initial_capital * (1.0 + daily_returns).cumprod()
    drawdown = _drawdown(equity_curve)
    summary = summarize_daily_returns(daily_returns)
    latest_weights = weights.iloc[-1][weights.iloc[-1] > 0.0001].sort_values(ascending=False)
    return StrategyResult(
        name=name,
        sleeve=sleeve,
        description=description,
        daily_returns=daily_returns,
        equity_curve=equity_curve,
        drawdown=drawdown,
        latest_weights=latest_weights,
        summary=summary,
        ending_value=float(equity_curve.iloc[-1]),
    )


def run_demo_backtests(
    initial_capital: float = 50000.0,
    use_real_data: bool = True,
    refresh_data: bool = False,
    allow_synthetic_fallback: bool = True,
) -> DemoBacktestResult:
    pd, _ = _require_pandas_numpy()
    data_source = "Deterministic synthetic sample prices"
    is_real_data = False
    data_error = ""

    if use_real_data:
        try:
            loaded = load_yahoo_close_prices(SAMPLE_SYMBOLS, refresh=refresh_data)
            prices = loaded.close_prices
            data_source = f"{loaded.source} ({loaded.cache_path})"
            is_real_data = True
        except Exception as exc:
            if not allow_synthetic_fallback:
                raise
            data_error = str(exc)
            prices = generate_demo_prices()
    else:
        prices = generate_demo_prices()

    results: Dict[str, StrategyResult] = {}

    benchmark_daily = benchmark_returns(prices, {"SPY": 0.5, "QQQ": 0.5}).reindex(prices.index).fillna(0.0)
    benchmark_weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    benchmark_weights["SPY"] = 0.5
    benchmark_weights["QQQ"] = 0.5
    results["50/50 SPY/QQQ"] = _make_result(
        "50/50 SPY/QQQ",
        "Benchmark",
        "Primary benchmark selected for policy review.",
        benchmark_daily,
        benchmark_weights,
        initial_capital,
    )

    etf_buy_hold_daily, etf_buy_hold_weights = _buy_hold_returns(prices, SAMPLE_ETFS)
    results["ETF Equal Weight"] = _make_result(
        "ETF Equal Weight",
        "Core ETF",
        "Equal-weight buy-and-hold basket across sample ETFs.",
        etf_buy_hold_daily,
        etf_buy_hold_weights,
        initial_capital,
    )

    etf_momentum_daily, etf_momentum_weights = _run_rebalanced_strategy(
        prices,
        selector=lambda history: _etf_momentum_selector(pd, prices.columns, history),
        start_index=200,
        rebalance_interval=21,
        transaction_cost_bps=5.0,
    )
    results["ETF Momentum Rotation"] = _make_result(
        "ETF Momentum Rotation",
        "Core ETF",
        "Monthly top-3 ETF momentum rotation with a 200-day trend filter and defensive fallback.",
        etf_momentum_daily,
        etf_momentum_weights,
        initial_capital,
    )

    defensive_daily, defensive_weights = _run_rebalanced_strategy(
        prices,
        selector=lambda history: _defensive_trend_selector(pd, prices.columns, history),
        start_index=200,
        rebalance_interval=21,
        transaction_cost_bps=4.0,
    )
    results["ETF Defensive Trend"] = _make_result(
        "ETF Defensive Trend",
        "Core ETF",
        "Risk-on/risk-off ETF allocation driven by SPY's 200-day trend.",
        defensive_daily,
        defensive_weights,
        initial_capital,
    )

    equity_momentum_daily, equity_momentum_weights = _run_rebalanced_strategy(
        prices,
        selector=lambda history: _equity_momentum_selector(pd, prices.columns, history),
        start_index=200,
        rebalance_interval=21,
        transaction_cost_bps=8.0,
    )
    results["Equity Momentum"] = _make_result(
        "Equity Momentum",
        "Equity Satellite",
        "Monthly top-5 volatility-adjusted momentum strategy across sample stocks.",
        equity_momentum_daily,
        equity_momentum_weights,
        initial_capital,
    )

    combined_daily = 0.70 * etf_momentum_daily + 0.30 * equity_momentum_daily
    combined_weights = 0.70 * etf_momentum_weights + 0.30 * equity_momentum_weights
    results["70/30 Combined Policy"] = _make_result(
        "70/30 Combined Policy",
        "Combined",
        "Policy-style blend of ETF momentum and equity momentum sleeves.",
        combined_daily,
        combined_weights,
        initial_capital,
    )

    summary_rows: List[Dict[str, float]] = []
    for result in results.values():
        summary_rows.append(
            {
                "Strategy": result.name,
                "Sleeve": result.sleeve,
                "Ending Value": result.ending_value,
                "Total Return": result.summary.total_return,
                "Annualized Return": result.summary.annualized_return,
                "Max Drawdown": result.summary.max_drawdown,
                "Volatility": result.summary.volatility,
                "Sharpe-like": result.summary.sharpe_like,
            }
        )

    summary_table = pd.DataFrame(summary_rows).sort_values("Ending Value", ascending=False)
    equity_curves = pd.DataFrame({name: result.equity_curve for name, result in results.items()})
    drawdowns = pd.DataFrame({name: result.drawdown for name, result in results.items()})

    return DemoBacktestResult(
        prices=prices,
        results=results,
        summary_table=summary_table,
        equity_curves=equity_curves,
        drawdowns=drawdowns,
        data_source=data_source,
        is_real_data=is_real_data,
        data_error=data_error,
    )
