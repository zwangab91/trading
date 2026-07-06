from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.demo_cache import clear_demo_backtest_cache, run_cached_demo_backtests
from backend.app.schemas import DataRefreshResponse
from backend.app.serialization import serialize_dashboard
from trading_agent.config import load_policy


router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/refresh-yahoo", response_model=DataRefreshResponse)
def refresh_yahoo_data(
    initial_capital: float = Query(None, gt=0),
) -> DataRefreshResponse:
    capital = initial_capital or load_policy().initial_account_equity
    clear_demo_backtest_cache()
    demo = run_cached_demo_backtests(
        initial_capital=capital,
        use_real_data=True,
        refresh_data=True,
    )
    return DataRefreshResponse(
        refreshed=demo.is_real_data,
        dashboard=serialize_dashboard(demo, initial_capital=capital),
    )
