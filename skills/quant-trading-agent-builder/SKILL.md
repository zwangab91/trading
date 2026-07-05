---
name: quant-trading-agent-builder
description: Build safety-first Python scaffolds for low/mid-frequency quantitative trading agents. Use when implementing a trading-agent repo with policy config, risk engine, strategy/backtest skeletons, real historical market-data demos, Streamlit dashboard, manual approval workflow, audit logging, broker adapter guardrails, tests, or CLI commands.
---

# Quant Trading Agent Builder

## Core Rule

Build safety controls before broker execution. Live trading must default to disabled, and broker adapters must refuse submission unless explicit live-trading configuration, user approval, and risk checks all pass.

If the user has not already approved a plan, stop and use a planning workflow first.

## Implementation Workflow

1. Inspect the target directory before writing files.
2. Create a small Python package with config, domain models, risk checks, recommendations, storage, data, strategies, backtests, execution, CLI, dashboard, and tests.
3. Store policy in a versioned config file such as `config/v1_policy.json`.
4. Make the risk engine independently testable.
5. Add broker integration as a guarded adapter stub first; do not implement live network submission in the first scaffold.
6. Add real historical data for demos and cache it locally.
7. Keep synthetic data only as an explicit fallback or offline UI test path.
8. Add dashboard and CLI views that show strategy return, benchmark comparison, drawdown, weights, and policy status.
9. Run compile, unit tests, CLI smoke tests, server checks, and dashboard smoke tests.

Use `references/session-build-outline.md` for the concrete file/module pattern from the trading-agent session.
For reproducing the pushed GitHub project from scratch, use the steps in `references/session-build-outline.md`.

## Safety Requirements

Enforce these before any broker submission path:

- Policy has live trading enabled.
- Manual approval exists if required.
- Risk decision is allowed.
- Kill switch is inactive.
- Order is long-only and does not create shorts.
- Cash, exposure, single-name, drawdown, daily/weekly/monthly loss, blocked-symbol, and earnings checks pass.

For Schwab or any broker API, browse current official docs before implementing auth, account, market-data, or order-submission behavior.

## Data And Backtest Requirements

Use adjusted daily historical prices for the dashboard demo when possible. `yfinance` is acceptable for personal/research demos with clear labeling and local caching, but do not treat it as production live data.

Backtest outputs should include:

- Ending value.
- Total return.
- Annualized return.
- Max drawdown.
- Volatility.
- Sharpe-like metric.
- Equity curve.
- Drawdown curve.
- Latest weights.

Always state that demo/backtest returns are not live-trading proof.

## Verification Commands

Prefer these checks after implementation:

```bash
python3 -m compileall trading_agent dashboard tests
python3 -m unittest discover
python3 -m trading_agent show-policy
python3 -m trading_agent risk-check-sample
python3 -m trading_agent demo-summary --refresh-data
```

For Streamlit dashboards, start a local server and verify it returns HTTP 200. If a browser surface is available, inspect the rendered page; otherwise run Streamlit's testing harness when installed.
