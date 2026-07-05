# Trading Agent

Python scaffold for a low / mid frequency quantitative trading agent using a conservative v1 policy:

- US equities and ETFs only.
- Long-only.
- No margin, shorts, options, leveraged ETFs, or inverse ETFs.
- Manual approval required before any order submission.
- First live candidate is the ETF sleeve; the individual-equity sleeve starts in research/paper mode.
- Primary benchmark is a 50% SPY / 50% QQQ blend.

This project is intentionally built so the risk engine and approval workflow exist before live broker execution.

## Quick Start

```bash
python3 -m trading_agent show-policy
python3 -m trading_agent init-db
python3 -m trading_agent risk-check-sample
python3 -m trading_agent demo-summary
python3 -m unittest discover
```

Optional research dependencies can be installed later:

```bash
python3 -m pip install -e ".[research,test,dashboard]"
```

Run the demo dashboard:

```bash
streamlit run dashboard/app.py
```

The dashboard uses real historical adjusted-close data from Yahoo Finance via `yfinance` by default, cached under `var/market_data/`. Synthetic sample data remains available as a fallback for offline UI validation.

## Current Scope

The current scaffold includes:

- Policy configuration in `config/v1_policy.json`.
- Domain models for accounts, positions, orders, recommendations, and risk checks.
- A testable risk engine with drawdown, loss-limit, exposure, cash, long-only, blocked-symbol, and earnings-event checks.
- Strategy skeletons for ETF rotation and equity momentum.
- Basic data loading and benchmark helpers.
- A guarded Schwab adapter stub. It prepares order payloads but does not place live orders.
- SQLite audit logging.
- Optional Streamlit dashboard scaffold.
- Demo strategy dashboard with real historical ETF and stock strategy returns.

## Safety Defaults

Live order submission is disabled in code and configuration. The system is designed to produce recommendations and prepared order tickets, but every broker submission path must pass explicit approval and live-trading checks.

## Project Layout

```text
config/                 V1 policy configuration
dashboard/              Optional dashboard app
docs/                   Planning and policy documents
tests/                  Unit tests
trading_agent/          Python package
var/                    Local runtime state, ignored where sensitive
skills/                 Repo copy of the Codex skills created from this session
```

## Codex Skills

The `skills/` directory contains a repo-local copy of the planning and builder skills distilled from this project. The personal installed copies live under `~/.codex/skills/`.
