from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas import DashboardResponse, StrategyDetail, StrategySummary, TradeRow
from backend.app.demo_cache import run_cached_demo_backtests
from backend.app.serialization import (
    require_strategy_name,
    serialize_dashboard,
    serialize_strategy_detail,
    serialize_strategy_summary,
    serialize_trade_history,
)
from trading_agent.config import load_policy


router = APIRouter(prefix="/api", tags=["dashboard"])


def _run_demo(initial_capital: float, use_real_data: bool, refresh_data: bool = False):
    return run_cached_demo_backtests(
        initial_capital=initial_capital,
        use_real_data=use_real_data,
        refresh_data=refresh_data,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    initial_capital: float = Query(None, gt=0),
    use_real_data: bool = True,
) -> DashboardResponse:
    capital = initial_capital or load_policy().initial_account_equity
    demo = _run_demo(initial_capital=capital, use_real_data=use_real_data)
    return serialize_dashboard(demo, initial_capital=capital)


@router.get("/strategies", response_model=list[StrategySummary])
def list_strategies(
    initial_capital: float = Query(None, gt=0),
    use_real_data: bool = True,
) -> list[StrategySummary]:
    capital = initial_capital or load_policy().initial_account_equity
    demo = _run_demo(initial_capital=capital, use_real_data=use_real_data)
    return [serialize_strategy_summary(result) for result in demo.results.values()]


@router.get("/strategies/{strategy_id}", response_model=StrategyDetail)
def get_strategy(
    strategy_id: str,
    initial_capital: float = Query(None, gt=0),
    use_real_data: bool = True,
) -> StrategyDetail:
    capital = initial_capital or load_policy().initial_account_equity
    demo = _run_demo(initial_capital=capital, use_real_data=use_real_data)
    try:
        strategy_name = require_strategy_name(demo.results, strategy_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc
    return serialize_strategy_detail(demo.results[strategy_name])


@router.get("/strategies/{strategy_id}/trades", response_model=list[TradeRow])
def get_strategy_trades(
    strategy_id: str,
    initial_capital: float = Query(None, gt=0),
    use_real_data: bool = True,
) -> list[TradeRow]:
    capital = initial_capital or load_policy().initial_account_equity
    demo = _run_demo(initial_capital=capital, use_real_data=use_real_data)
    try:
        strategy_name = require_strategy_name(demo.results, strategy_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Strategy not found") from exc
    return serialize_trade_history(demo.results[strategy_name].trade_history)
