from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence

from trading_agent.domain import AssetType, Sleeve, StrategySignal
from trading_agent.strategies.base import Strategy, require_pandas


class EtfRotationStrategy(Strategy):
    name = "etf_rotation_momentum_trend"

    def __init__(
        self,
        universe: Sequence[str],
        lookback_days: int = 126,
        trend_days: int = 200,
        top_n: int = 3,
    ):
        self.universe = tuple(symbol.upper() for symbol in universe)
        self.lookback_days = lookback_days
        self.trend_days = trend_days
        self.top_n = top_n

    def generate_signals(self, close_prices) -> Iterable[StrategySignal]:
        pd = require_pandas()
        if len(close_prices) < max(self.lookback_days, self.trend_days) + 1:
            return []

        prices = close_prices[list(self.universe)].dropna(how="all")
        latest = prices.iloc[-1]
        momentum = prices.pct_change(self.lookback_days).iloc[-1]
        trend_average = prices.rolling(self.trend_days).mean().iloc[-1]
        in_uptrend = latest > trend_average
        ranked = momentum[in_uptrend].dropna().sort_values(ascending=False)
        signals = []
        generated_at = datetime.utcnow()

        for symbol, score in ranked.head(self.top_n).items():
            confidence = min(0.95, max(0.50, 0.50 + float(score)))
            signals.append(
                StrategySignal(
                    symbol=str(symbol).upper(),
                    asset_type=AssetType.ETF,
                    sleeve=Sleeve.CORE_ETF,
                    score=float(score),
                    confidence=confidence,
                    rationale=(
                        f"{symbol} ranks in the top {self.top_n} by "
                        f"{self.lookback_days}-day momentum and is above its "
                        f"{self.trend_days}-day trend filter."
                    ),
                    generated_at=generated_at,
                    metadata={"strategy_name": self.name},
                )
            )

        pd.Series([len(signals)])
        return signals

