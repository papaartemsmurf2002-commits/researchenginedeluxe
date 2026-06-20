from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000
COST_PROFILE_CONTRACT_VERSION = "venue-cost-fill-profile-v1"
DEFAULT_RESEARCH_COST_PROFILE_ID = "binance_usdm_research_baseline"
DEFAULT_RESEARCH_FILL_PROFILE_ID = "primary_bar_latency_fill"
FUNDING_RATE_FIELD_ALIASES = ("funding_rate", "perp_last_funding_rate", "last_funding_rate")
RESEARCH_EXECUTION_PROOF_SCOPE = "historical_research_only_not_live_execution_proof"
DEFAULT_NON_EXECUTION_PROOF_VENUES = ("hyperliquid", "paper", "live")
SUPPORTED_RESEARCH_FILL_PROFILE_IDS = frozenset(
    {
        "primary_bar_latency_fill",
        "signal_close_latency_fill",
        "vwap_approximation_fill",
        "lower_timeframe_latency_open_fill",
        "wide_spread_primary_bar_stress",
    }
)


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
class VenueCostProfile:
    profile_id: str
    venue: str
    source_venue: str
    execution_venue: str
    fee_bps: float
    slippage_bps: float
    spread_bps: float
    funding_rate: float
    funding_interval_ms: int = FUNDING_INTERVAL_MS
    fill_profile_id: str = DEFAULT_RESEARCH_FILL_PROFILE_ID
    evidence_scope: str = "binance_historical_research_cost_stress"
    execution_proof_scope: str = RESEARCH_EXECUTION_PROOF_SCOPE
    candidate_gate_eligible: bool = True
    not_execution_proof_for: tuple[str, ...] = DEFAULT_NON_EXECUTION_PROOF_VENUES

    def to_payload(self) -> dict[str, object]:
        return {
            "cost_profile_contract_version": COST_PROFILE_CONTRACT_VERSION,
            "cost_profile_id": self.profile_id,
            "venue": self.venue,
            "source_venue": self.source_venue,
            "execution_venue": self.execution_venue,
            "fee_bps": float(self.fee_bps),
            "slippage_bps": float(self.slippage_bps),
            "spread_bps": float(self.spread_bps),
            "funding_rate": float(self.funding_rate),
            "funding_interval_ms": int(self.funding_interval_ms),
            "fill_profile_id": self.fill_profile_id,
            "evidence_scope": self.evidence_scope,
            "execution_proof_scope": self.execution_proof_scope,
            "candidate_gate_eligible": bool(self.candidate_gate_eligible),
            "not_execution_proof_for": list(self.not_execution_proof_for),
        }


@dataclass(frozen=True, slots=True)
class CostModel:
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    spread_bps: float = 0.0
    funding_rate: float = 0.0
    funding_interval_ms: int = FUNDING_INTERVAL_MS
    venue: str = "binance_usdm"
    cost_profile_id: str = DEFAULT_RESEARCH_COST_PROFILE_ID
    fill_profile_id: str = DEFAULT_RESEARCH_FILL_PROFILE_ID
    source_venue: str = "binance_usdm"
    execution_venue: str = "binance_usdm_research"
    evidence_scope: str = "binance_historical_research_cost_stress"
    execution_proof_scope: str = RESEARCH_EXECUTION_PROOF_SCOPE
    cost_profile_source: str = "registered_profile"
    not_execution_proof_for: tuple[str, ...] = DEFAULT_NON_EXECUTION_PROOF_VENUES

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
            "cost_profile_contract_version": COST_PROFILE_CONTRACT_VERSION,
            "cost_profile_id": self.cost_profile_id,
            "fill_profile_id": self.fill_profile_id,
            "fee_bps": float(self.fee_bps),
            "slippage_bps": float(self.slippage_bps),
            "spread_bps": float(self.spread_bps),
            "funding_rate": float(self.funding_rate),
            "funding_interval_ms": int(self.funding_interval_ms),
            "venue": self.venue,
            "source_venue": self.source_venue,
            "execution_venue": self.execution_venue,
            "evidence_scope": self.evidence_scope,
            "execution_proof_scope": self.execution_proof_scope,
            "cost_profile_source": self.cost_profile_source,
            "not_execution_proof_for": list(self.not_execution_proof_for),
        }


VENUE_COST_PROFILES: dict[str, VenueCostProfile] = {
    DEFAULT_RESEARCH_COST_PROFILE_ID: VenueCostProfile(
        profile_id=DEFAULT_RESEARCH_COST_PROFILE_ID,
        venue="binance_usdm",
        source_venue="binance_usdm",
        execution_venue="binance_usdm_research",
        fee_bps=5.0,
        slippage_bps=5.0,
        spread_bps=0.0,
        funding_rate=0.0,
    ),
    "binance_usdm_research_slippage_2x": VenueCostProfile(
        profile_id="binance_usdm_research_slippage_2x",
        venue="binance_usdm",
        source_venue="binance_usdm",
        execution_venue="binance_usdm_research",
        fee_bps=5.0,
        slippage_bps=10.0,
        spread_bps=0.0,
        funding_rate=0.0,
    ),
    "binance_usdm_research_slippage_3x": VenueCostProfile(
        profile_id="binance_usdm_research_slippage_3x",
        venue="binance_usdm",
        source_venue="binance_usdm",
        execution_venue="binance_usdm_research",
        fee_bps=5.0,
        slippage_bps=15.0,
        spread_bps=0.0,
        funding_rate=0.0,
    ),
    "binance_usdm_research_adverse_funding": VenueCostProfile(
        profile_id="binance_usdm_research_adverse_funding",
        venue="binance_usdm",
        source_venue="binance_usdm",
        execution_venue="binance_usdm_research",
        fee_bps=5.0,
        slippage_bps=5.0,
        spread_bps=0.0,
        funding_rate=0.00005,
        evidence_scope="binance_historical_research_funding_stress",
    ),
    "binance_usdm_research_wide_spread": VenueCostProfile(
        profile_id="binance_usdm_research_wide_spread",
        venue="binance_usdm",
        source_venue="binance_usdm",
        execution_venue="binance_usdm_research",
        fee_bps=5.0,
        slippage_bps=5.0,
        spread_bps=25.0,
        funding_rate=0.0,
        fill_profile_id="wide_spread_primary_bar_stress",
        evidence_scope="binance_historical_research_spread_stress",
    ),
}


def venue_cost_profile(profile_id: str) -> VenueCostProfile:
    key = str(profile_id or "").strip()
    if key not in VENUE_COST_PROFILES:
        raise ValueError(f"unknown_cost_profile_id:{key}")
    return VENUE_COST_PROFILES[key]


def validate_fill_profile_id(fill_profile_id: str) -> str:
    key = str(fill_profile_id or "").strip()
    if key not in SUPPORTED_RESEARCH_FILL_PROFILE_IDS:
        raise ValueError(f"unknown_fill_profile_id:{key}")
    return key


def funding_rate_from_row(row: Mapping[str, object]) -> float | None:
    for column in FUNDING_RATE_FIELD_ALIASES:
        value = row.get(column)
        if value is None:
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(parsed):
            continue
        return parsed
    return None


def research_cost_stress_scenarios() -> tuple[dict[str, object], ...]:
    definitions = (
        {"scenario_id": "base_costs", "scenario_group": "cost", "cost_profile_id": DEFAULT_RESEARCH_COST_PROFILE_ID},
        {"scenario_id": "slippage_2x", "scenario_group": "cost", "cost_profile_id": "binance_usdm_research_slippage_2x"},
        {"scenario_id": "slippage_3x", "scenario_group": "cost", "cost_profile_id": "binance_usdm_research_slippage_3x"},
        {
            "scenario_id": "adverse_funding_shock",
            "scenario_group": "funding",
            "cost_profile_id": "binance_usdm_research_adverse_funding",
        },
        {
            "scenario_id": "wide_spread_stress",
            "scenario_group": "spread",
            "cost_profile_id": "binance_usdm_research_wide_spread",
            "transform": "wide_spread",
        },
        {
            "scenario_id": "missing_optional_context_stress",
            "scenario_group": "feature_context",
            "cost_profile_id": DEFAULT_RESEARCH_COST_PROFILE_ID,
            "transform": "missing_optional_context",
        },
        {
            "scenario_id": "high_volatility_only",
            "scenario_group": "volatility",
            "cost_profile_id": DEFAULT_RESEARCH_COST_PROFILE_ID,
            "filter": "high_volatility",
        },
        {
            "scenario_id": "low_volatility_only",
            "scenario_group": "volatility",
            "cost_profile_id": DEFAULT_RESEARCH_COST_PROFILE_ID,
            "filter": "low_volatility",
        },
        {
            "scenario_id": "trend_only",
            "scenario_group": "regime",
            "cost_profile_id": DEFAULT_RESEARCH_COST_PROFILE_ID,
            "filter": "trend",
        },
        {
            "scenario_id": "range_only",
            "scenario_group": "regime",
            "cost_profile_id": DEFAULT_RESEARCH_COST_PROFILE_ID,
            "filter": "range",
        },
        {
            "scenario_id": "shock_transition_only",
            "scenario_group": "shock",
            "cost_profile_id": DEFAULT_RESEARCH_COST_PROFILE_ID,
            "filter": "shock_transition",
        },
    )
    scenarios: list[dict[str, object]] = []
    for definition in definitions:
        profile = venue_cost_profile(str(definition["cost_profile_id"]))
        payload = profile.to_payload()
        payload.update(definition)
        scenarios.append(payload)
    return tuple(scenarios)
