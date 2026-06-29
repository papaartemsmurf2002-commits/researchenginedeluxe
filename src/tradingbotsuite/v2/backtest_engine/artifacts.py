# V2-AUDIT-ID: V2-AUD-BTENG-001
# V2-CONTRACTS: docs/contracts/backtest_engine_contract.md, docs/contracts/run_artifact_contract.md
# V2-BOUNDARY: research_only, run_artifacts, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_backtest_engine
"""Run artifact schemas for v2 backtest engines."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_now
from tradingbotsuite.v2.costs.models import CostModelConfig, CostStressScenario
from tradingbotsuite.v2.security.boundary import require_research_boundary


class EngineLane(str, Enum):
    VECTORIZED = "vectorized"
    FAST_VECTORIZED = "fast_vectorized"
    EVENT_DRIVEN = "event_driven"


class RunStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class MissingDataPolicy(str, Enum):
    FAIL_CLOSED = "fail_closed"


class ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    QUARANTINE = "quarantine"


class RunArtifactRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    row_count: int | None = Field(default=None, ge=0)
    required: bool = True


class StrategyContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    run_id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    trial_index: int = Field(ge=0)
    archive_snapshot_id: str = Field(min_length=1)
    universe_snapshot_id: str = Field(min_length=1)
    data_manifest_id: str = Field(min_length=1)
    validation_policy_id: str = Field(min_length=1)
    cost_model_id: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    venue_scope: str = Field(min_length=1)
    universe_mode: str = Field(min_length=1)
    instrument_count: int = Field(ge=0)
    backtest_start: datetime
    backtest_end: datetime
    lockbox_policy_id: str = Field(min_length=1)
    lockbox_start: datetime | None = None
    lockbox_end: datetime | None = None
    data_coverage_min: float = Field(ge=0.0, le=1.0)
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

    @field_validator("backtest_start", "backtest_end", "lockbox_start", "lockbox_end")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _window_order(self) -> "StrategyContext":
        if self.backtest_end <= self.backtest_start:
            raise ValueError("backtest_end must be greater than backtest_start")
        require_research_boundary(self, context="strategy context")
        return self


class BacktestRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    run_id: str | None = None
    experiment_id: str = "v2_experiment"
    trial_index: int = Field(default=0, ge=0)
    agent_or_user: str = "agent"
    output_root: str = Field(min_length=1)
    archive_snapshot_id: str = Field(min_length=1)
    universe_snapshot_id: str = Field(min_length=1)
    data_manifest_id: str = Field(min_length=1)
    data_manifest_hash: str = Field(min_length=64, max_length=64)
    validation_manifest_hash: str = Field(min_length=64, max_length=64)
    cost_manifest_hash: str = Field(min_length=64, max_length=64)
    validation_policy_id: str = "v2_default_validation_v1"
    cost_model_id: str = "conservative_hyperliquid_taker_v1"
    cost_model: CostModelConfig | None = None
    engine_lane: EngineLane = EngineLane.VECTORIZED
    missing_data_policy: MissingDataPolicy = MissingDataPolicy.FAIL_CLOSED
    initial_equity: float = Field(default=1.0, gt=0.0)
    fee_bps: float = Field(default=6.0, ge=0.0)
    spread_bps: float = Field(default=5.0, ge=0.0)
    spread_observation_policy: str = "lenient"
    slippage_bps: float = Field(default=3.0, ge=0.0)
    impact_bps: float = Field(default=1.0, ge=0.0)
    account_notional_usd: float = Field(default=10_000.0, gt=0.0)
    max_volume_participation: float = Field(default=0.05, gt=0.0, le=1.0)
    cost_stress_scenarios: tuple[CostStressScenario, ...] = (
        CostStressScenario.BASE,
        CostStressScenario.STRESS_2X,
        CostStressScenario.STRESS_3X,
    )
    require_net_metrics: bool = True
    lockbox_policy_id: str = "dynamic_full_calendar_months_v1"
    lockbox_start: datetime | None = None
    lockbox_end: datetime | None = None
    data_coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
    universe_mode: str = "as_of"
    venue_scope: str = "hyperliquid"
    git_sha: str = "unknown"
    environment_hash: str | None = Field(default=None, min_length=64, max_length=64)

    @field_validator("lockbox_start", "lockbox_end")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @field_validator("spread_observation_policy")
    @classmethod
    def _known_spread_observation_policy(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"lenient", "accepted_research_strict"}:
            raise ValueError("spread_observation_policy must be lenient or accepted_research_strict")
        return normalized

    @model_validator(mode="after")
    def _validate_cost_identity(self) -> "BacktestRunConfig":
        if self.cost_model is not None and self.cost_model.cost_model_id != self.cost_model_id:
            raise ValueError("cost_model_id must match cost_model.cost_model_id")
        required_scenarios = {
            CostStressScenario.BASE,
            CostStressScenario.STRESS_2X,
            CostStressScenario.STRESS_3X,
        }
        if not required_scenarios.issubset(set(self.cost_stress_scenarios)):
            raise ValueError("backtest config must include base, stress_2x, and stress_3x scenarios")
        return self


class BacktestMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    run_id: str = Field(min_length=1)
    status: RunStatus
    gross_return: float
    net_return: float
    gross_equity_final: float
    net_equity_final: float
    total_fee_cost: float = Field(ge=0.0)
    total_spread_cost: float = Field(ge=0.0)
    total_slippage_cost: float = Field(ge=0.0)
    total_impact_cost: float = Field(ge=0.0)
    total_transaction_cost: float = Field(ge=0.0)
    total_funding_pnl: float
    total_turnover: float = Field(ge=0.0)
    trade_count: int = Field(ge=0)
    position_row_count: int = Field(ge=0)
    capacity_blocked_count: int = Field(default=0, ge=0)
    gross_only: bool = False
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
    def _validate_metrics(self) -> "BacktestMetrics":
        if self.gross_only:
            raise ValueError("reported v2 backtest metrics cannot be gross-only")
        require_research_boundary(self, context="backtest metrics")
        return self


class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "run_manifest_v1"
    run_id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    trial_index: int = Field(ge=0)
    agent_or_user: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)
    status: RunStatus
    engine_lane: EngineLane
    strategy_lane: str = "declarative"
    git_sha: str = Field(min_length=1)
    environment_hash: str = Field(min_length=64, max_length=64)
    strategy_id: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)
    strategy_hash: str = Field(min_length=64, max_length=64)
    strategy_spec_hash: str = Field(min_length=64, max_length=64)
    params_hash: str = Field(min_length=64, max_length=64)
    archive_snapshot_id: str = Field(min_length=1)
    universe_snapshot_id: str = Field(min_length=1)
    data_manifest_id: str = Field(min_length=1)
    data_manifest_hash: str = Field(min_length=64, max_length=64)
    validation_manifest_hash: str = Field(min_length=64, max_length=64)
    cost_manifest_hash: str = Field(min_length=64, max_length=64)
    universe_mode: str = Field(min_length=1)
    venue_scope: str = Field(min_length=1)
    instrument_count: int = Field(ge=0)
    timeframe: str = Field(min_length=1)
    backtest_start: datetime
    backtest_end: datetime
    usable_months: int = Field(ge=0)
    lockbox_policy_id: str = Field(min_length=1)
    lockbox_start: datetime | None = None
    lockbox_end: datetime | None = None
    data_coverage_min: float = Field(ge=0.0, le=1.0)
    cost_model_id: str = Field(min_length=1)
    cost_model_hash: str = Field(min_length=64, max_length=64)
    account_notional_usd: float = Field(default=10_000.0, gt=0.0)
    validation_policy_id: str = Field(min_length=1)
    validation_status: ValidationStatus
    missing_data_policy: MissingDataPolicy
    price_basis: str = Field(min_length=1)
    failure_reason: str | None = None
    metrics: BacktestMetrics | None = None
    artifacts: dict[str, RunArtifactRef] = Field(default_factory=dict)
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

    @field_validator("created_at", "backtest_start", "backtest_end", "lockbox_start", "lockbox_end")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _require_research_boundary(self) -> "RunManifest":
        if self.backtest_end <= self.backtest_start:
            raise ValueError("backtest_end must be greater than backtest_start")
        if self.status == RunStatus.FAILED and not self.failure_reason:
            raise ValueError("failed run manifests require failure_reason")
        if self.status == RunStatus.SUCCEEDED and self.metrics is None:
            raise ValueError("succeeded run manifests require metrics")
        require_research_boundary(self, context="run manifest")
        required = {
            "strategy_spec",
            "params",
            "data_manifest",
            "validation_manifest",
            "cost_manifest",
            "cost_stress",
            "metrics",
            "equity_curve",
            "daily_returns",
            "trades",
            "positions",
            "per_instrument_metrics",
            "fold_metrics",
            "log",
        }
        missing = sorted(required - set(self.artifacts))
        if missing:
            raise ValueError("run manifest missing artifact refs: " + ",".join(missing))
        return self


class BacktestRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_dir: str = Field(min_length=1)
    manifest: RunManifest
    metrics: BacktestMetrics | None = None
