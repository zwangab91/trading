# Risk Policy

This file documents the default risk policy implemented in `config/v1_policy.json`.

## Account-Level Limits

| Control | Value |
| --- | ---: |
| Pause drawdown | 5% |
| Hard stop review | 8% |
| Stop new trades after daily loss | 0.5% |
| Daily hard review | 1% |
| Weekly pause | 1.5% |
| Monthly pause | 3% |
| Gross exposure cap | 80% |
| Minimum cash buffer | 20% |

## Position-Level Limits

| Control | Value |
| --- | ---: |
| Default risk per trade | 0.25% |
| Maximum risk per trade | 0.50% |
| Single stock cap | 5% |
| Single ETF cap | 10% |

## Execution Principles

- Every order must pass risk checks before it can be prepared for broker submission.
- Every broker submission requires explicit user approval.
- The broker adapter starts with live trading disabled.
- Sells that reduce existing long positions are allowed; sells that create shorts are blocked.
- Buy orders require a defined risk amount.
- Leveraged and inverse ETF tickers in the blocked list are rejected.

