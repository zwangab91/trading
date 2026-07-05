from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from trading_agent.domain import AssetType


@dataclass(frozen=True)
class UniverseMember:
    symbol: str
    asset_type: AssetType
    name: str


CORE_ETF_UNIVERSE: Tuple[UniverseMember, ...] = (
    UniverseMember("SPY", AssetType.ETF, "SPDR S&P 500 ETF"),
    UniverseMember("QQQ", AssetType.ETF, "Invesco QQQ Trust"),
    UniverseMember("IWM", AssetType.ETF, "iShares Russell 2000 ETF"),
    UniverseMember("DIA", AssetType.ETF, "SPDR Dow Jones Industrial Average ETF"),
    UniverseMember("VTI", AssetType.ETF, "Vanguard Total Stock Market ETF"),
    UniverseMember("VEA", AssetType.ETF, "Vanguard FTSE Developed Markets ETF"),
    UniverseMember("VWO", AssetType.ETF, "Vanguard FTSE Emerging Markets ETF"),
    UniverseMember("TLT", AssetType.ETF, "iShares 20+ Year Treasury Bond ETF"),
    UniverseMember("IEF", AssetType.ETF, "iShares 7-10 Year Treasury Bond ETF"),
    UniverseMember("GLD", AssetType.ETF, "SPDR Gold Shares"),
)

