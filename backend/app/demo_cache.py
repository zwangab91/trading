from __future__ import annotations

from threading import Lock

from trading_agent.demo import DemoBacktestResult, run_demo_backtests


_CACHE_LOCK = Lock()
_DEMO_CACHE: dict[tuple[float, bool], DemoBacktestResult] = {}


def _cache_key(initial_capital: float, use_real_data: bool) -> tuple[float, bool]:
    return (round(float(initial_capital), 2), bool(use_real_data))


def run_cached_demo_backtests(
    *,
    initial_capital: float,
    use_real_data: bool,
    refresh_data: bool = False,
) -> DemoBacktestResult:
    key = _cache_key(initial_capital, use_real_data)
    if not refresh_data:
        with _CACHE_LOCK:
            cached = _DEMO_CACHE.get(key)
        if cached is not None:
            return cached

    demo = run_demo_backtests(
        initial_capital=initial_capital,
        use_real_data=use_real_data,
        refresh_data=refresh_data,
    )
    with _CACHE_LOCK:
        _DEMO_CACHE[key] = demo
    return demo


def clear_demo_backtest_cache() -> None:
    with _CACHE_LOCK:
        _DEMO_CACHE.clear()
