---
name: quant-trading-agent-builder
description: Build safety-first Python scaffolds for low/mid-frequency quantitative trading agents. Use when implementing a trading-agent repo with policy config, risk engine, strategy/backtest skeletons, trade-history backtest rows, FastAPI backend endpoints, Next.js dashboard frontend, real historical market-data demos, Streamlit legacy dashboard, manual approval workflow, audit logging, broker adapter guardrails, tests, or CLI commands.
---

# Quant Trading Agent Builder

## Core Rule

Build safety controls before broker execution. Live trading must default to disabled, and broker adapters must refuse submission unless explicit live-trading configuration, user approval, and risk checks all pass.

If the user has not already approved a plan, stop and use a planning workflow first.

## Implementation Workflow

1. Inspect the target directory before writing files.
2. Create a small Python package with config, domain models, risk checks, recommendations, storage, data, strategies, backtests, execution, CLI, backend API, dashboard frontend, and tests.
3. Store policy in a versioned config file such as `config/v1_policy.json`.
4. Make the risk engine independently testable.
5. Add broker integration as a guarded adapter stub first; do not implement live network submission in the first scaffold.
6. Add real historical data for demos and cache it locally.
7. Keep synthetic data only as an explicit fallback or offline UI test path.
8. Add FastAPI endpoints and a Next.js dashboard that show strategy return, benchmark comparison, drawdown, weights, simulated trade history, and policy status.
9. Keep the Streamlit dashboard optional or legacy if present; do not make it the primary deployment surface for product-style dashboards.
10. Run compile, unit tests, CLI smoke tests, backend checks, frontend type/build checks, server checks, and dashboard smoke tests.

Use `references/session-build-outline.md` for the concrete file/module pattern from the trading-agent session.
For reproducing the pushed GitHub project from scratch, use the steps in `references/session-build-outline.md`.

## Web App Architecture

Prefer this split for a proper deployable dashboard:

- `trading_agent/`: Python trading engine, policy, risk, data, strategies, backtests, and trade-history generation.
- `backend/`: FastAPI app exposing policy, dashboard summary, strategy detail, trade history, and explicit Yahoo refresh endpoints.
- `frontend/`: Next.js + TypeScript dashboard consuming `NEXT_PUBLIC_API_URL`.
- CORS: Allow both local frontend origins (`http://localhost:3000`, `http://127.0.0.1:3000`) by default and use `ALLOWED_ORIGINS` for deployment.
- Refresh: Make Yahoo refresh an explicit POST/button action, not a persistent checkbox or automatic render side effect.

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
- Simulated trade history with strategy, source strategy when blended, sleeve, trade date, entry date, exit/trim date, symbol, action, previous weight, target weight, weight change, price, transaction cost, and realized/marked return.

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

For FastAPI + Next.js dashboards, also run:

```bash
python3 -m compileall backend trading_agent dashboard tests
python3 -m unittest discover
cd frontend && npm audit && npm run typecheck && NEXT_TELEMETRY_DISABLED=1 npm run build
```

Start the backend with `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000` and the frontend with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3000`; verify both return HTTP 200.
