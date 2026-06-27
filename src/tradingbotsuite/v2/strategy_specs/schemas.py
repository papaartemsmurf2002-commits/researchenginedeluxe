# V2-AUDIT-ID: V2-AUD-STRAT-001
# V2-CONTRACTS: docs/contracts/strategy_spec_contract.md
# V2-BOUNDARY: research_only, declarative_specs_only, no_live_imports
# V2-OWNER: v2_strategy_specs
"""Declarative strategy spec and signal-frame schemas."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config import defaults
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.strategy_specs.registry import (
    FORBIDDEN_KEY_TOKENS,
    FORBIDDEN_VALUE_TOKENS,
    RANK_METRICS_BY_SIGNAL_TYPE,
    REQUIRED_FIELDS_BY_SIGNAL_TYPE,
    SUPPORTED_FEE_MODELS,
    SUPPORTED_FILTERS,
    SUPPORTED_INPUT_FIELDS,
    SUPPORTED_SLIPPAGE_MODELS,
    PriceBasis,
    SpecEvidenceMode,
    StrategySignalType,
    UniverseMode,
)

STRATEGY_SPEC_SCHEMA_VERSION = "strategy_spec_v1"
SIDE_EFFECT_SCAN_KEY_ALLOWLIST = frozenset(
    {
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
        "exclude_lockbox",
        "execution",
    }
)


class MarketScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    venue: str = Field(min_length=1)
    market_type: str = "perp"
    universe_rule: str = Field(min_length=1)


class StrategyInputs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    timeframe: str = Field(min_length=1)
    fields: tuple[str, ...]

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("inputs.fields must not be empty")
        invalid = sorted(set(value) - SUPPORTED_INPUT_FIELDS)
        if invalid:
            raise ValueError("unsupported input fields: " + ",".join(invalid))
        return tuple(dict.fromkeys(value))


class StrategyLogic(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_type: StrategySignalType
    lookback_bars: int | None = Field(default=None, ge=1)
    lookback_hours: int | None = Field(default=None, ge=1)
    rank_metric: str | None = None
    rank_direction: str = "momentum"
    long_top_quantile: float | None = Field(default=None, gt=0.0, le=0.5)
    short_bottom_quantile: float | None = Field(default=None, gt=0.0, le=0.5)
    entry_threshold: float | None = Field(default=None, ge=0.0)
    exit_threshold: float | None = Field(default=None, ge=0.0)
    filters: dict[str, float | int | bool] = Field(default_factory=dict)

    @field_validator("rank_direction")
    @classmethod
    def _validate_rank_direction(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"momentum", "reversion"}:
            raise ValueError("rank_direction must be momentum or reversion")
        return normalized

    @model_validator(mode="after")
    def _validate_logic(self) -> "StrategyLogic":
        if self.lookback_bars is None and self.lookback_hours is None:
            raise ValueError("logic requires lookback_bars or lookback_hours")
        if self.rank_metric is not None:
            allowed = RANK_METRICS_BY_SIGNAL_TYPE.get(self.signal_type, frozenset())
            if self.rank_metric not in allowed:
                raise ValueError(
                    f"unsupported rank_metric for {self.signal_type.value}: {self.rank_metric}"
                )
        invalid_filters = sorted(set(self.filters) - SUPPORTED_FILTERS)
        if invalid_filters:
            raise ValueError("unsupported filters: " + ",".join(invalid_filters))
        if self.signal_type in {
            StrategySignalType.CROSS_SECTIONAL_RANK,
            StrategySignalType.LIQUIDITY_FILTERED,
        }:
            if self.long_top_quantile is None and self.short_bottom_quantile is None:
                raise ValueError("rank strategies require long_top_quantile or short_bottom_quantile")
        return self


class RiskConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_gross_leverage: float = Field(gt=0.0, le=3.0)
    max_instrument_weight: float = Field(gt=0.0, le=1.0)
    rebalance: str = Field(min_length=1)


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    price_basis: PriceBasis
    fee_model: str = Field(min_length=1)
    slippage_model: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_execution(self) -> "ExecutionConfig":
        if self.fee_model not in SUPPORTED_FEE_MODELS:
            raise ValueError(f"unsupported fee_model: {self.fee_model}")
        if self.slippage_model not in SUPPORTED_SLIPPAGE_MODELS:
            raise ValueError(f"unsupported slippage_model: {self.slippage_model}")
        return self


class StrategyValidationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    min_backtest_months: int = Field(default=defaults.DEFAULT_PREFERRED_USABLE_MONTHS, ge=6)
    earliest_start: date = defaults.DEFAULT_EARLIEST_BACKTEST_START
    exclude_lockbox: bool = True
    universe_mode: UniverseMode = UniverseMode.AS_OF
    evidence_mode: SpecEvidenceMode = SpecEvidenceMode.ACCEPTED_RESEARCH

    @model_validator(mode="after")
    def _validate_evidence_policy(self) -> "StrategyValidationConfig":
        if self.earliest_start < defaults.DEFAULT_EARLIEST_BACKTEST_START:
            raise ValueError("validation.earliest_start cannot be before 2024-01-01")
        if not self.exclude_lockbox:
            raise ValueError("validation.exclude_lockbox must be true")
        if (
            self.evidence_mode != SpecEvidenceMode.SANDBOX_DIAGNOSTIC
            and self.universe_mode != UniverseMode.AS_OF
        ):
            raise ValueError("accepted/reported strategy specs require as_of universe")
        return self


class StrategySpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = STRATEGY_SPEC_SCHEMA_VERSION
    strategy_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,80}$")
    strategy_family: str = Field(min_length=1)
    version: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False
    market_scope: MarketScope
    inputs: StrategyInputs
    logic: StrategyLogic
    risk: RiskConfig
    execution: ExecutionConfig
    validation: StrategyValidationConfig
    parameters: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _schema_version(cls, value: str) -> str:
        if value != STRATEGY_SPEC_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {STRATEGY_SPEC_SCHEMA_VERSION}")
        return value

    @model_validator(mode="after")
    def _validate_spec(self) -> "StrategySpec":
        require_research_boundary(self, context="strategy spec")
        required = REQUIRED_FIELDS_BY_SIGNAL_TYPE[self.logic.signal_type]
        if self.logic.signal_type == StrategySignalType.FUNDING_CARRY and "funding" not in self.inputs.fields:
            if "funding_rate" in self.inputs.fields:
                required = frozenset({"funding_rate"})
        missing = sorted(required - set(self.inputs.fields))
        if (
            self.logic.signal_type == StrategySignalType.VOL_ADJUSTED_TREND
            and self.logic.rank_metric == "breakout_over_atr"
        ):
            missing = sorted(set(missing) | ({"high", "low"} - set(self.inputs.fields)))
        if missing:
            raise ValueError(
                f"{self.logic.signal_type.value} requires input fields: " + ",".join(missing)
            )
        side_effects = find_side_effect_markers(self.model_dump(mode="json"))
        if side_effects:
            raise ValueError("forbidden strategy side-effect content: " + ",".join(side_effects))
        return self

    @property
    def spec_hash(self) -> str:
        return strategy_spec_hash(self)


class StrategySpecValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    spec_hash: str | None = Field(default=None, min_length=64, max_length=64)
    strategy_id: str | None = None


class SignalSide(str):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class SignalRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = V2_SCHEMA_VERSION
    strategy_id: str = Field(min_length=1)
    spec_hash: str = Field(min_length=64, max_length=64)
    ts: datetime
    instrument_id: str = Field(min_length=1)
    signal: float = Field(ge=-1.0, le=1.0)
    target_weight: float = Field(ge=-1.0, le=1.0)
    side: str
    score: float | None = None
    reason: str = Field(min_length=1)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("ts")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_boundary(self) -> "SignalRow":
        require_research_boundary(self, context="signal row")
        return self


class SignalFrame(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    strategy_id: str = Field(min_length=1)
    spec_hash: str = Field(min_length=64, max_length=64)
    rows: tuple[SignalRow, ...]
    row_count: int = Field(ge=0)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_frame(self) -> "SignalFrame":
        if self.row_count != len(self.rows):
            raise ValueError("row_count must equal number of signal rows")
        require_research_boundary(self, context="signal frame")
        return self


def strategy_spec_hash(spec: StrategySpec | Mapping[str, Any]) -> str:
    if isinstance(spec, StrategySpec):
        payload = spec.model_dump(mode="json", exclude={"metadata"})
    else:
        payload = dict(spec)
    return _canonical_json_hash(payload)


def find_side_effect_markers(payload: Any, *, path: str = "$") -> tuple[str, ...]:
    markers: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key).lower()
            if key_text not in SIDE_EFFECT_SCAN_KEY_ALLOWLIST:
                for token in FORBIDDEN_KEY_TOKENS:
                    if token in key_text:
                        markers.append(f"{path}.{key}:forbidden_key_{token}")
                        break
            markers.extend(find_side_effect_markers(value, path=f"{path}.{key}"))
    elif isinstance(payload, list | tuple):
        for index, item in enumerate(payload):
            markers.extend(find_side_effect_markers(item, path=f"{path}[{index}]"))
    elif isinstance(payload, str):
        lowered = payload.lower()
        for token in FORBIDDEN_VALUE_TOKENS:
            if token in lowered:
                markers.append(f"{path}:forbidden_value_{token}")
    return tuple(dict.fromkeys(markers))


def _canonical_json_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
