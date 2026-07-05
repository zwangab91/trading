# Session-Derived V1 Policy

Use these defaults when a user asks for a conservative starting point and has not supplied conflicting constraints.

## Account And Scope

- Capital base: USD 50,000.
- Loss materiality: losses materially affect the user.
- Jurisdiction/account: US taxable account.
- Broker: Schwab.
- Assets: US equities and ETFs.
- V1 constraints: long-only, no margin, no shorts, no options, no leveraged ETFs, no inverse ETFs.
- Execution: prepare order tickets but require explicit approval before submission.
- First live deployment: USD 10,000 to USD 15,000 only after promotion gates pass.

## Benchmark

Use `50% SPY / 50% QQQ total-return` as the primary benchmark. Also show SPY and QQQ separately.

Reasoning: SPY is broad large-cap US exposure; QQQ is concentrated Nasdaq-100 growth/tech exposure. The 50/50 blend is a fair hurdle without forcing excessive QQQ-like concentration.

## Sleeves

| Sleeve | Role | Initial Status |
| --- | --- | --- |
| Core ETF | ETF rotation, trend filters, volatility-aware exposure | First live candidate |
| Equity Satellite | Individual-stock momentum, quality/momentum, post-earnings drift research | Research/paper first |

Suggested policy allocation after both sleeves are approved: 70% ETF / 30% equities. Before approval, run ETF live first and equity paper-only.

## Risk Limits

| Limit | Default |
| --- | ---: |
| Pause drawdown | 5% / USD 2,500 |
| Hard stop review | 8% / USD 4,000 |
| Stop new trades after daily loss | 0.5% / USD 250 |
| Daily hard review | 1% / USD 500 |
| Weekly pause | 1.5% / USD 750 |
| Monthly pause | 3% / USD 1,500 |
| Default risk per trade | 0.25% / USD 125 |
| Maximum risk per trade | 0.5% / USD 250 |
| Gross exposure cap | 80% |
| Minimum cash buffer | 20% |
| Single stock cap | 5% |
| Single ETF cap | 10% |

## Earnings Policy

- Block automatic new single-stock entries within 2 trading days before earnings.
- Block automatic new single-stock entries within 1 trading day after earnings.
- Allow a manual override only with explicit approval and reduced size.
- Allow pre-earnings entries only for a dedicated validated event model.
- Cap blackout-period entries at 50% of normal single-stock size.
- Cap total pre-earnings exposure at 5% of account value.
- Show expected gap-risk scenarios before approval.

## Strategy Classes

Good v1 candidates:

- ETF trend following / regime filter.
- ETF rotation.
- Cross-sectional momentum.
- Factor model: value, quality, momentum, low volatility.
- Volatility targeting and risk overlay.
- Post-earnings drift after report, not casual pre-earnings bets.

Defer:

- Pairs/stat arb requiring shorts or margin.
- News/sentiment without reliable data and validation.
- ML ranking models until baselines exist.
- Reinforcement learning.
- HFT/market making.

## Promotion Gate

No live trading until:

- At least 2 years of backtest evidence exists.
- Prefer 10+ years for daily ETF strategies.
- Walk-forward and out-of-sample results are reviewed.
- Costs, slippage, dividends, and corporate actions are handled.
- Results are compared against 50% SPY / 50% QQQ, SPY, and QQQ.
- Paper trading runs 30 to 60 market days.
- Dashboard, audit log, alerts, risk checks, and kill switch are working.

