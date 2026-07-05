from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from trading_agent.config import DEFAULT_POLICY_PATH, load_policy
from trading_agent.demo import run_demo_backtests
from trading_agent.domain import AccountState, AssetType, OrderIntent, Side, Sleeve
from trading_agent.risk import RiskEngine
from trading_agent.storage import AuditStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trading-agent")
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="Path to policy JSON.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show-policy", help="Print key policy settings.")
    subparsers.add_parser("init-db", help="Initialize the local audit database.")
    subparsers.add_parser("risk-check-sample", help="Run a sample risk check.")
    demo_parser = subparsers.add_parser("demo-summary", help="Print demo strategy backtest summary.")
    demo_parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use deterministic synthetic fallback data instead of real historical data.",
    )
    demo_parser.add_argument(
        "--refresh-data",
        action="store_true",
        help="Refresh cached Yahoo Finance historical data.",
    )
    return parser


def show_policy(policy_path: Path) -> int:
    policy = load_policy(policy_path)
    summary = {
        "initial_account_equity": policy.initial_account_equity,
        "initial_live_capital_range": [
            policy.initial_live_capital_min,
            policy.initial_live_capital_max,
        ],
        "benchmark_weights": policy.benchmark_weights,
        "live_trading_enabled": policy.live_trading_enabled,
        "manual_approval_required": policy.manual_approval_required,
        "long_only": policy.long_only,
        "gross_exposure_cap_pct": policy.gross_exposure_cap_pct,
        "risk_per_trade_default_pct": policy.risk_per_trade_default_pct,
        "risk_per_trade_max_pct": policy.risk_per_trade_max_pct,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def init_db() -> int:
    store = AuditStore(Path("var/audit.sqlite3"))
    store.initialize()
    event_id = store.record_event("system.initialized", {"component": "audit_store"})
    print(f"Initialized audit store at var/audit.sqlite3; event_id={event_id}")
    return 0


def risk_check_sample(policy_path: Path) -> int:
    policy = load_policy(policy_path)
    account = AccountState(
        equity=50000.0,
        cash=30000.0,
        peak_equity=50000.0,
    )
    order = OrderIntent(
        symbol="SPY",
        asset_type=AssetType.ETF,
        sleeve=Sleeve.CORE_ETF,
        side=Side.BUY,
        quantity=10,
        limit_price=500.0,
        strategy_name="sample",
        rationale="Sample risk-check order.",
        generated_at=datetime.utcnow(),
        risk_amount=100.0,
    )
    decision = RiskEngine(policy).evaluate_order(account, order, today=date.today())
    print(f"allowed={decision.allowed}")
    for check in decision.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status} [{check.severity.value}] {check.name}: {check.message}")
    return 0 if decision.allowed else 1


def demo_summary(use_real_data: bool = True, refresh_data: bool = False) -> int:
    demo = run_demo_backtests(use_real_data=use_real_data, refresh_data=refresh_data)
    print(f"Data source: {demo.data_source}")
    if demo.data_error:
        print(f"Data warning: {demo.data_error}")
    display = demo.summary_table.copy()
    for column in ["Total Return", "Annualized Return", "Max Drawdown", "Volatility"]:
        display[column] = display[column].map(lambda value: f"{value:.1%}")
    display["Sharpe-like"] = display["Sharpe-like"].map(lambda value: f"{value:.2f}")
    display["Ending Value"] = display["Ending Value"].map(lambda value: f"${value:,.0f}")
    print(display.to_string(index=False))
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "show-policy":
        return show_policy(args.policy)
    if args.command == "init-db":
        return init_db()
    if args.command == "risk-check-sample":
        return risk_check_sample(args.policy)
    if args.command == "demo-summary":
        return demo_summary(use_real_data=not args.synthetic, refresh_data=args.refresh_data)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
