# V2-AUDIT-ID: V2-AUD-CONTRACTS-001
# V2-CONTRACTS: docs/contracts/cost_model_contract.md
# V2-BOUNDARY: research_only, net_costs_required, no_live_imports
# V2-OWNER: v2_costs
"""Cost model schemas and deterministic calculators for v2 research backtests."""

from __future__ import annotations

import hashlib
import json
import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION

COST_MODEL_SCHEMA_VERSION = "cost_model_v1"
COST_MANIFEST_SCHEMA_VERSION = "cost_manifest_v1"


class CostStressScenario(str, Enum):
    BASE = "base"
    STRESS_2X = "stress_2x"
    STRESS_3X = "stress_3x"


_SCENARIO_MULTIPLIERS = {
    CostStressScenario.BASE: 1.0,
    CostStressScenario.STRESS_2X: 2.0,
    CostStressScenario.STRESS_3X: 3.0,
}


class CostModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = COST_MODEL_SCHEMA_VERSION
    cost_model_id: str = "conservative_hyperliquid_taker_v1"
    fee_side: str = "taker"
    fee_bps: float = Field(default=6.0, ge=0.0)
    spread_bps: float = Field(default=2.0, ge=0.0)
    slippage_bps: float = Field(default=3.0, ge=0.0)
    impact_bps: float = Field(default=1.0, ge=0.0)
    max_volume_participation: float = Field(default=0.05, gt=0.0, le=1.0)
    slippage_model_id: str = "volume_participation_v1"
    impact_model_id: str = "impact_v1"
    funding_required: bool = True
    funding_source: str = "archive_funding_table"
    funding_missing_policy: str = "fail"
    liquidity_stress_required: bool = True
    ranking_allowed: bool = True
    queue_model_documented: bool = False
    stress_scenarios: tuple[CostStressScenario, ...] = (
        CostStressScenario.BASE,
        CostStressScenario.STRESS_2X,
        CostStressScenario.STRESS_3X,
    )
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @field_validator("fee_side")
    @classmethod
    def _known_fee_side(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"taker", "maker", "mixed"}:
            raise ValueError("fee_side must be taker, maker, or mixed")
        return normalized

    @field_validator("funding_missing_policy")
    @classmethod
    def _known_funding_missing_policy(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"fail", "explicit_zero"}:
            raise ValueError("funding_missing_policy must be fail or explicit_zero")
        return normalized

    @model_validator(mode="after")
    def _validate_cost_model(self) -> "CostModelConfig":
        required_scenarios = {
            CostStressScenario.BASE,
            CostStressScenario.STRESS_2X,
            CostStressScenario.STRESS_3X,
        }
        if not required_scenarios.issubset(set(self.stress_scenarios)):
            raise ValueError("cost model must include base, stress_2x, and stress_3x scenarios")
        if self.cost_model_id == "mixed_maker_taker_research_v1" or self.fee_side in {
            "maker",
            "mixed",
        }:
            if not self.queue_model_documented:
                raise ValueError("maker_assumption_requires_queue_model")
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("cost model config must preserve the v2 research boundary")
        return self

    @property
    def config_hash(self) -> str:
        return cost_model_hash(self)


class CostBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    scenario: CostStressScenario
    cost_multiplier: float = Field(gt=0.0)
    weight_delta: float = Field(ge=0.0)
    applied_weight: float
    funding_rate: float
    volume_notional: float | None = Field(default=None, ge=0.0)
    max_volume_participation: float = Field(gt=0.0, le=1.0)
    participation_rate: float = Field(ge=0.0)
    capacity_blocked: bool
    capacity_reason: str | None = None
    fee_cost: float = Field(ge=0.0)
    spread_cost: float = Field(ge=0.0)
    slippage_cost: float = Field(ge=0.0)
    impact_cost: float = Field(ge=0.0)
    total_transaction_cost: float = Field(ge=0.0)
    funding_pnl: float
    net_pnl_adjustment: float
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_boundary(self) -> "CostBreakdown":
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("cost breakdown must preserve the v2 research boundary")
        return self


def cost_model_hash(config: CostModelConfig) -> str:
    payload = config.model_dump(mode="json", exclude={"research_only", "observe_only"})
    return _canonical_json_hash(payload)


def scenario_multiplier(scenario: CostStressScenario | str) -> float:
    parsed = scenario if isinstance(scenario, CostStressScenario) else CostStressScenario(scenario)
    return _SCENARIO_MULTIPLIERS[parsed]


def calculate_cost_breakdown(
    *,
    config: CostModelConfig,
    weight_delta: float,
    applied_weight: float,
    funding_rate: float,
    volume_notional: float | None,
    observed_spread_bps: float | None = None,
    scenario: CostStressScenario = CostStressScenario.BASE,
) -> CostBreakdown:
    turnover = _finite_non_negative(weight_delta, "weight_delta")
    funding = _finite(funding_rate, "funding_rate")
    volume = None if volume_notional is None else _finite_non_negative(volume_notional, "volume_notional")
    participation_rate = 0.0
    capacity_blocked = False
    capacity_reason: str | None = None
    if turnover > 0.0:
        if volume is None or volume <= 0.0:
            capacity_blocked = config.liquidity_stress_required
            capacity_reason = "volume_notional_missing_for_turnover"
        else:
            participation_rate = turnover / volume
            if participation_rate > config.max_volume_participation:
                capacity_blocked = True
                capacity_reason = "liquidity_participation_cap_exceeded"
    multiplier = scenario_multiplier(scenario)
    spread_bps = config.spread_bps
    if observed_spread_bps is not None:
        spread_bps = max(spread_bps, _finite_non_negative(observed_spread_bps, "observed_spread_bps"))
    fee_cost = turnover * (config.fee_bps * multiplier / 10_000.0)
    spread_cost = turnover * (spread_bps * multiplier / 10_000.0)
    slippage_cost = turnover * (config.slippage_bps * multiplier / 10_000.0)
    impact_scale = 1.0
    if participation_rate > 0.0:
        impact_scale = max(1.0, participation_rate / config.max_volume_participation)
    impact_cost = turnover * (config.impact_bps * multiplier * impact_scale / 10_000.0)
    total_transaction_cost = fee_cost + spread_cost + slippage_cost + impact_cost
    funding_pnl = -applied_weight * funding
    return CostBreakdown(
        scenario=scenario,
        cost_multiplier=multiplier,
        weight_delta=turnover,
        applied_weight=applied_weight,
        funding_rate=funding,
        volume_notional=volume,
        max_volume_participation=config.max_volume_participation,
        participation_rate=participation_rate,
        capacity_blocked=capacity_blocked,
        capacity_reason=capacity_reason,
        fee_cost=fee_cost,
        spread_cost=spread_cost,
        slippage_cost=slippage_cost,
        impact_cost=impact_cost,
        total_transaction_cost=total_transaction_cost,
        funding_pnl=funding_pnl,
        net_pnl_adjustment=funding_pnl - total_transaction_cost,
    )


def build_cost_manifest(
    *,
    config: CostModelConfig,
    stress_rows: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    rows_by_scenario = {str(row["scenario_id"]): row for row in stress_rows}
    base = rows_by_scenario.get(CostStressScenario.BASE.value)
    stress_2x = rows_by_scenario.get(CostStressScenario.STRESS_2X.value)
    stress_3x = rows_by_scenario.get(CostStressScenario.STRESS_3X.value)
    cost_fragile_warning = any(bool(row.get("cost_fragile_warning")) for row in stress_rows)
    cost_dependent_failure = any(bool(row.get("cost_dependent_failure")) for row in stress_rows)
    return {
        "schema_version": COST_MANIFEST_SCHEMA_VERSION,
        "cost_model_id": config.cost_model_id,
        "cost_model_hash": config.config_hash,
        "cost_model_config": config.model_dump(mode="json"),
        "fee_model": {
            "side": config.fee_side,
            "rate_source": "config_or_manifested_source",
            "rate_value_bps": config.fee_bps,
        },
        "funding_model": {
            "applied": True,
            "source": config.funding_source,
            "missing_policy": config.funding_missing_policy,
            "required": config.funding_required,
        },
        "slippage_model": {
            "id": config.slippage_model_id,
            "participation_cap": config.max_volume_participation,
            "spread_component_bps": config.spread_bps,
            "slippage_component_bps": config.slippage_bps,
            "volume_component": "volume_notional_or_volume_times_close",
        },
        "impact_model": {
            "enabled": True,
            "model_id": config.impact_model_id,
            "impact_bps": config.impact_bps,
        },
        "capacity_model": {
            "liquidity_stress_required": config.liquidity_stress_required,
            "max_volume_participation": config.max_volume_participation,
        },
        "stress_matrix": {
            scenario.value: {
                "required": True,
                "multiplier": scenario_multiplier(scenario),
                "reported": scenario.value in rows_by_scenario,
            }
            for scenario in config.stress_scenarios
        },
        "cost_sensitivity": {
            "base_cost_net_return": None if base is None else base["net_return"],
            "stress_2x_net_return": None if stress_2x is None else stress_2x["net_return"],
            "stress_3x_net_return": None if stress_3x is None else stress_3x["net_return"],
            "cost_fragile_warning": cost_fragile_warning,
            "cost_dependent_failure": cost_dependent_failure,
        },
        "stress_costs_exclude_funding_pnl_multiplier": True,
        "gross_and_net_required": True,
        "ranking_allowed": config.ranking_allowed,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _finite(value: float, field_name: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{field_name} must be finite")
    return parsed


def _finite_non_negative(value: float, field_name: str) -> float:
    parsed = _finite(value, field_name)
    if parsed < 0.0:
        raise ValueError(f"{field_name} must be non-negative")
    return parsed


def _canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
