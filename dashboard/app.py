from __future__ import annotations

import json
from pathlib import Path

from trading_agent.config import load_policy
from trading_agent.demo import SAMPLE_ETFS, SAMPLE_STOCKS, run_demo_backtests


def main() -> None:
    try:
        import streamlit as st  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Install dashboard dependencies with: python3 -m pip install -e '.[dashboard]'"
        ) from exc

    policy = load_policy()
    st.set_page_config(page_title="Trading Agent", layout="wide", initial_sidebar_state="expanded")
    st.title("Trading Agent")
    initial_capital = st.sidebar.number_input(
        "Initial capital",
        min_value=1000,
        max_value=1000000,
        value=int(policy.initial_account_equity),
        step=1000,
    )
    use_real_data = st.sidebar.checkbox("Use real historical data", value=True)
    refresh_data = st.sidebar.checkbox("Refresh cached data", value=False)
    demo = run_demo_backtests(
        initial_capital=float(initial_capital),
        use_real_data=use_real_data,
        refresh_data=refresh_data,
    )

    if demo.is_real_data:
        st.caption(f"Using real historical adjusted-close data: {demo.data_source}")
    else:
        st.warning(
            "Using deterministic synthetic fallback data. Real-data download failed or was disabled."
        )
        if demo.data_error:
            st.caption(demo.data_error)

    summary = demo.summary_table.copy()
    best = summary.iloc[0]
    benchmark = summary[summary["Strategy"] == "50/50 SPY/QQQ"].iloc[0]
    combined = summary[summary["Strategy"] == "70/30 Combined Policy"].iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Best demo strategy", best["Strategy"], f"{best['Total Return']:.1%}")
    col2.metric("Combined policy", f"${combined['Ending Value']:,.0f}", f"{combined['Total Return']:.1%}")
    col3.metric("50/50 benchmark", f"${benchmark['Ending Value']:,.0f}", f"{benchmark['Total Return']:.1%}")
    col4.metric("Data mode", "Real" if demo.is_real_data else "Synthetic", "Live trading disabled")

    tab_overview, tab_strategy, tab_universe, tab_policy = st.tabs(
        ["Overview", "Strategy Detail", "Universe", "Policy"]
    )

    with tab_overview:
        st.subheader("Demo Backtest Summary")
        st.dataframe(
            summary.style.format(
                {
                    "Ending Value": "${:,.0f}",
                    "Total Return": "{:.1%}",
                    "Annualized Return": "{:.1%}",
                    "Max Drawdown": "{:.1%}",
                    "Volatility": "{:.1%}",
                    "Sharpe-like": "{:.2f}",
                }
            ),
            width="stretch",
        )

        st.subheader("Equity Curve")
        st.line_chart(demo.equity_curves)

        st.subheader("Drawdown")
        st.line_chart(demo.drawdowns)

    with tab_strategy:
        strategy_name = st.selectbox("Strategy", list(demo.results.keys()), index=5)
        result = demo.results[strategy_name]
        st.caption(result.description)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ending value", f"${result.ending_value:,.0f}")
        col2.metric("Total return", f"{result.summary.total_return:.1%}")
        col3.metric("Max drawdown", f"{result.summary.max_drawdown:.1%}")
        col4.metric("Sharpe-like", f"{result.summary.sharpe_like:.2f}")

        st.subheader("Latest Demo Weights")
        if len(result.latest_weights) > 0:
            latest_weights = (
                result.latest_weights.rename("Weight")
                .reset_index()
                .rename(columns={"index": "Symbol"})
            )
            st.bar_chart(latest_weights, x="Symbol", y="Weight")
            st.dataframe(
                latest_weights.style.format({"Weight": "{:.1%}"}),
                width="stretch",
            )
        else:
            st.info("This strategy is currently in cash in the demo path.")

        st.subheader("Daily Returns")
        recent_returns = (
            result.daily_returns.tail(126)
            .rename("Daily Return")
            .reset_index()
            .rename(columns={"index": "Date"})
        )
        st.bar_chart(recent_returns, x="Date", y="Daily Return")

    with tab_universe:
        st.subheader("ETF Prices")
        st.line_chart(demo.prices[list(SAMPLE_ETFS)])
        st.subheader("Stock Prices")
        st.line_chart(demo.prices[list(SAMPLE_STOCKS)])

    with tab_policy:
        st.subheader("Policy")
        st.json(
            {
                "benchmark": dict(policy.benchmark_weights),
                "live_trading_enabled": policy.live_trading_enabled,
                "manual_approval_required": policy.manual_approval_required,
                "long_only": policy.long_only,
                "allow_margin": policy.allow_margin,
                "allow_shorting": policy.allow_shorting,
                "gross_exposure_cap_pct": policy.gross_exposure_cap_pct,
                "risk_per_trade_default_pct": policy.risk_per_trade_default_pct,
                "risk_per_trade_max_pct": policy.risk_per_trade_max_pct,
            }
        )

        recommendations_path = Path("var/recommendations.json")
        st.subheader("Recommendations")
        if recommendations_path.exists():
            st.json(json.loads(recommendations_path.read_text(encoding="utf-8")))
        else:
            st.info("No recommendations file found at var/recommendations.json.")


if __name__ == "__main__":
    main()
