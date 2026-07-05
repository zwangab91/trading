from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence

from trading_agent.domain import AssetType, Sleeve, StrategySignal
from trading_agent.strategies.base import Strategy, require_pandas


class EquityMomentumStrategy(Strategy):
    name = "equity_cross_sectional_momentum"

    def __init__(
        self,
        universe: Sequence[str],
        lookback_days: int = 126,
        volatility_days: int = 63,
        top_n: int = 10,
    ):
        self.universe = tuple(symbol.upper() for symbol in universe)
        self.lookback_days = lookback_days
        self.volatility_days = volatility_days
        self.top_n = top_n

    def generate_signals(self, close_prices) -> Iterable[StrategySignal]:
        pd = require_pandas()
        if len(close_prices) < max(self.lookback_days, self.volatility_days) + 1:
            return []

        prices = close_prices[list(self.universe)].dropna(how="all")
        returns = prices.pct_change()
        momentum = prices.pct_change(self.lookback_days).iloc[-1]
        volatility = returns.rolling(self.volatility_days).std().iloc[-1]
        risk_adjusted_score = (momentum / volatility).replace([float("inf"), -float("inf")], pd.NA)
        ranked = risk_adjusted_score.dropna().sort_values(ascending=False)
        signals = []
        generated_at = datetime.utcnow()

        for symbol, score in ranked.head(self.top_n).items():
            confidence = min(0.90, max(0.50, 0.50 + float(score) / 10.0))
            signals.append(
                StrategySignal(
                    symbol=str(symbol).upper(),
                    asset_type=AssetType.EQUITY,
                    sleeve=Sleeve.EQUITY_SATELLITE,
                    score=float(score),
                    confidence=confidence,
                    rationale=(
                        f"{symbol} ranks in the top {self.top_n} by volatility-adjusted "
                        f"{self.lookback_days}-day momentum."
                    ),
                    generated_at=generated_at,
                    metadata={"strategy_name": self.name},
                )
            )

        pd.Series([len(signals)])
        return signals

