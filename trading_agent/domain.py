from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class AssetType(str, Enum):
    EQUITY = "equity"
    ETF = "etf"


class Sleeve(str, Enum):
    CORE_ETF = "core_etf"
    EQUITY_SATELLITE = "equity_satellite"


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class RiskSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCK = "block"


@dataclass(frozen=True)
class Position:
    symbol: str
    asset_type: AssetType
    quantity: int
    market_price: float
    sleeve: Sleeve
    average_cost: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.market_price


@dataclass(frozen=True)
class AccountState:
    equity: float
    cash: float
    peak_equity: float
    day_pnl: float = 0.0
    week_pnl: float = 0.0
    month_pnl: float = 0.0
    positions: Tuple[Position, ...] = ()
    kill_switch_active: bool = False

    def position_for(self, symbol: str) -> Optional[Position]:
        normalized = symbol.upper()
        for position in self.positions:
            if position.symbol.upper() == normalized:
                return position
        return None

    @property
    def gross_long_exposure(self) -> float:
        return sum(max(position.market_value, 0.0) for position in self.positions)


@dataclass(frozen=True)
class StrategySignal:
    symbol: str
    asset_type: AssetType
    sleeve: Sleeve
    score: float
    confidence: float
    rationale: str
    generated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    asset_type: AssetType
    sleeve: Sleeve
    side: Side
    quantity: int
    limit_price: float
    strategy_name: str
    rationale: str
    generated_at: datetime
    risk_amount: Optional[float] = None
    expected_holding_days: Optional[int] = None
    earnings_date: Optional[date] = None
    earnings_override: bool = False
    event_model_validated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def symbol_normalized(self) -> str:
        return self.symbol.upper()

    @property
    def notional(self) -> float:
        return self.quantity * self.limit_price


@dataclass(frozen=True)
class RiskCheck:
    name: str
    passed: bool
    severity: RiskSeverity
    message: str


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    checks: Tuple[RiskCheck, ...]

    @property
    def blocking_checks(self) -> Tuple[RiskCheck, ...]:
        return tuple(
            check
            for check in self.checks
            if not check.passed and check.severity == RiskSeverity.BLOCK
        )

    @property
    def warnings(self) -> Tuple[RiskCheck, ...]:
        return tuple(check for check in self.checks if check.severity == RiskSeverity.WARNING)


@dataclass(frozen=True)
class PreparedOrder:
    intent: OrderIntent
    broker_payload: Dict[str, Any]
    risk_decision: RiskDecision
    approved_by_user: bool = False

