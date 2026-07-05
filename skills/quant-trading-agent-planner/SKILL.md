---
name: quant-trading-agent-planner
description: Interview and plan conservative low/mid-frequency quantitative trading agents for real-money accounts. Use when the user asks to design, scope, review, or prepare a trading agent, strategy portfolio, broker/data plan, risk policy, backtesting standard, paper-trading gate, dashboard, alerts, kill switch, or live-deployment controls before implementation.
---

# Quant Trading Agent Planner

## Core Rule

Plan first. Do not implement trading code until the user explicitly approves the plan.

Treat real-money trading as high risk. Require paper trading, strict risk limits, audit logging, monitoring, manual approval, and a kill switch before any live deployment.

## Interview Workflow

Ask concise questions covering:

- Capital amount and whether losses materially affect the user.
- Account jurisdiction/type, broker, assets, margin/shorting/options permissions.
- Frequency target, holding period, operating hours, and order-type preferences.
- Autonomy level: recommendation-only, prepared orders, or full automation.
- Data source requirements: free/delayed research data versus live data.
- Strategy preferences: ETF rotation, trend, mean reversion, factors, stat arb, PEAD, ML, news/sentiment.
- Risk limits: drawdown, daily/weekly/monthly loss, risk per trade, exposure caps.
- Reporting, alerts, dashboard, and human controls.
- Backtest, out-of-sample, walk-forward, paper-trading, and live promotion standards.
- Goal definition: benchmark beating, Sharpe/Sortino, drawdown control, learning, or absolute return.

When the user asks for recommended defaults, use the session policy in `references/v1-policy.md`.

## Planning Standards

Recommend a staged system:

1. Research and backtest.
2. Paper trade.
3. Small live sleeve.
4. Gradual scale-up only after evidence and operational checks.

Separate strategy sleeves when risk profiles differ. For the session-derived plan, use a lower-complexity ETF sleeve as the first live candidate and keep individual equities in research/paper mode until proven.

## Earnings Events

Treat earnings as event risk, not ordinary volatility. Default to soft-blocking new single-stock entries near earnings unless there is a dedicated validated earnings-event model or explicit reduced-size manual override.

Use `references/v1-policy.md` for the exact earnings-event policy.

## Current Facts

Browse and cite primary/current sources when recommending broker API behavior, regulatory constraints, market-data terms, tax rules, or current product capabilities. Do not assume broker, FINRA/SEC, API, or data-provider facts are still current.

## Output

Produce a concrete plan with:

- Locked assumptions and open decisions.
- Risk policy.
- Portfolio sleeves and strategy classes.
- Data, backtesting, execution, dashboard, alerting, audit, and deployment architecture.
- Promotion gate before live capital.
- Clear next step requiring approval before implementation.

