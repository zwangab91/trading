# V1 Implementation Plan

## Objective

Build a conservative low / mid frequency quantitative trading agent for a taxable Schwab account using real-money safety controls before live execution.

## Selected Policies

- Capital base: USD 50,000.
- First live deployment: USD 10,000 to USD 15,000 only after promotion gates pass.
- Assets: US equities and ETFs.
- Constraints: long-only, no margin, no shorts, no options, no leveraged ETFs, no inverse ETFs.
- Benchmark: 50% SPY / 50% QQQ.
- Execution: recommendations and prepared order tickets, with explicit user approval required.
- First live sleeve: ETF-only core sleeve.
- Equity satellite sleeve: research and paper trading first.

## V1 Sleeves

| Sleeve | Role | V1 Status |
| --- | --- | --- |
| Core ETF | ETF rotation, trend filters, volatility-aware exposure | First live candidate |
| Equity Satellite | Individual-stock momentum, quality/momentum, PEAD research | Paper/research first |

## Earnings Policy

The system treats earnings as a separate event-risk class.

- New equity entries are soft-blocked within 2 trading days before earnings.
- New equity entries are soft-blocked within 1 trading day after earnings.
- A blocked trade can proceed only if a validated event model exists or the user manually overrides it.
- Any blackout-period entry is capped at 50% of the normal single-stock size.
- The system should show downside gap scenarios before approval.

## Promotion Gate

No live trading until:

- At least 2 years of backtest evidence exists.
- Daily ETF strategies preferably have 10 years of history.
- Out-of-sample and walk-forward tests have been reviewed.
- Costs and slippage are included.
- Results are compared against 50% SPY / 50% QQQ, SPY, and QQQ.
- Paper trading has run for 30 to 60 market days.
- Dashboard, audit log, alerts, risk checks, and kill switch are working.

## Build Phases

1. Scaffold package, config, docs, and audit store.
2. Implement core domain models and risk engine.
3. Add strategy skeletons and backtest helpers.
4. Add recommendation and sizing helpers.
5. Add dashboard and approval workflow.
6. Add Schwab adapter behind disabled live-trading gates.
7. Add paper-trading state machine.
8. Add live-data and broker integration.
9. Add alerting and deployment automation.
10. Run backtest, paper, and promotion reviews.

