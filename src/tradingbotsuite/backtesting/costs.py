from __future__ import annotations

from dataclasses import dataclass

FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    gross_return: float
    fee_return: float
    slippage_return: float
    spread_return: float
    funding_return: float
    net_return: float

    def to_payload(self) -> dict[str, float]:
        return {
            "gross_return": float(self.gross_return),
            "fee_return": float(self.fee_return),
            "slippage_return": float(self.slippage_return),
            "spread_return": float(self.spread_return),
            "funding_return": float(self.funding_return),
            "net_return": float(self.net_return),
        }


@dataclass(frozen=True, slots=True)
class CostModel:
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    spread_bps: float = 0.0
    funding_rate: float = 0.0
    funding_interval_ms: int = FUNDING_INTERVAL_MS
    venue: str = "binance_usdm"

    def estimate(
        self,
        *,
        entry_price: float,
        exit_price: float,
        side: str,
        holding_ms: int,
        funding_rate: float | None = None,
        spread_bps: float | None = None,
    ) -> CostBreakdown:
        if entry_price <= 0 or exit_price <= 0:
            raise ValueError("entry_price and exit_price must be positive")
        side_sign = 1.0 if str(side).lower() == "long" else -1.0
        gross_return = side_sign * ((float(exit_price) - float(entry_price)) / float(entry_price))
        fee_return = (float(self.fee_bps) * 2.0) / 10_000.0
        slippage_return = (float(self.slippage_bps) * 2.0) / 10_000.0
        spread_return = float(self.spread_bps if spread_bps is None else spread_bps) / 10_000.0
        funding_periods = max(float(holding_ms), 0.0) / max(float(self.funding_interval_ms), 1.0)
        effective_funding = float(self.funding_rate if funding_rate is None else funding_rate)
        funding_return = -side_sign * effective_funding * funding_periods
        net_return = gross_return - fee_return - slippage_return - spread_return + funding_return
        return CostBreakdown(
            gross_return=gross_return,
            fee_return=fee_return,
            slippage_return=slippage_return,
            spread_return=spread_return,
            funding_return=funding_return,
            net_return=net_return,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "fee_bps": float(self.fee_bps),
            "slippage_bps": float(self.slippage_bps),
            "spread_bps": float(self.spread_bps),
            "funding_rate": float(self.funding_rate),
            "funding_interval_ms": int(self.funding_interval_ms),
            "venue": self.venue,
        }
