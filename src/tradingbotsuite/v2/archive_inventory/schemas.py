# V2-AUDIT-ID: V2-AUD-ARCH-020
# V2-CONTRACTS: docs/contracts/archive_contract.md, docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, archive_inventory, no_live_imports, no_archive_writes
# V2-OWNER: v2_archive_inventory
"""Schemas for archive inventory and strategy data-requirement resolution."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.security.boundary import require_research_boundary


class ArtifactMode(str, Enum):
    FULL = "full"
    SUMMARY = "summary"
    METRICS_ONLY = "metrics_only"


class ArchiveInventoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    inventory_id: str = Field(min_length=64, max_length=64)
    instrument_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    family: str = Field(min_length=1)
    timeframe: str | None = None
    start_ts: datetime | None = None
    end_ts: datetime | None = None
    row_count: int = Field(ge=0)
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    coverage_min: float | None = Field(default=None, ge=0.0, le=1.0)
    field_names: tuple[str, ...] = ()
    source_file_ids: tuple[str, ...] = ()
    archive_snapshot_id: str | None = None
    coverage_report_id: str | None = None
    coverage_report_ids: tuple[str, ...] = ()
    universe_snapshot_id: str | None = None
    evidence_scope: str = "archive_inventory"
    accepted_research_evidence_allowed: bool = False
    native_to_hyperliquid: bool = False
    proxy_to_hyperliquid: bool = False
    data_quality_status: str = "unknown"
    known_gap_reasons: tuple[str, ...] = ()
    usable_archive_ref: str = Field(min_length=1)
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

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @field_validator("field_names", "source_file_ids", "coverage_report_ids", "known_gap_reasons")
    @classmethod
    def _dedupe_tuple(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(str(item) for item in value if str(item)))

    @model_validator(mode="after")
    def _validate_record(self) -> "ArchiveInventoryRecord":
        if self.start_ts is not None and self.end_ts is not None and self.end_ts <= self.start_ts:
            raise ValueError("inventory end_ts must be greater than start_ts")
        if self.coverage_report_id and self.coverage_report_id not in self.coverage_report_ids:
            raise ValueError("coverage_report_id must be included in coverage_report_ids")
        require_research_boundary(self, context="archive inventory record")
        return self


class ArchiveInventorySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    inventory_hash: str = Field(min_length=64, max_length=64)
    record_count: int = Field(ge=0)
    instruments: tuple[str, ...] = ()
    venues: tuple[str, ...] = ()
    source_families: tuple[str, ...] = ()
    timeframes: tuple[str, ...] = ()
    feature_families: tuple[str, ...] = ()
    earliest_start_ts: datetime | None = None
    latest_end_ts: datetime | None = None
    total_rows: int = Field(ge=0)
    accepted_research_record_count: int = Field(ge=0)
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

    @field_validator("earliest_start_ts", "latest_end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_summary(self) -> "ArchiveInventorySummary":
        require_research_boundary(self, context="archive inventory summary")
        return self


class ArchiveInventory(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    summary: ArchiveInventorySummary
    records: tuple[ArchiveInventoryRecord, ...] = ()
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
    def _validate_inventory(self) -> "ArchiveInventory":
        if self.summary.record_count != len(self.records):
            raise ValueError("summary.record_count must equal records length")
        require_research_boundary(self, context="archive inventory")
        return self


class DataGapRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    data_gap_request_id: str = Field(min_length=64, max_length=64)
    strategy_id: str = Field(min_length=1)
    requested_family: str = Field(min_length=1)
    requested_fields: tuple[str, ...] = ()
    instrument_ids: tuple[str, ...] = Field(min_length=1)
    venue_preference: tuple[str, ...] = ()
    start_ts: datetime
    end_ts: datetime
    reason: str = Field(min_length=1)
    existing_archive_refs_checked: tuple[str, ...] = ()
    missing_coverage_report_ids: tuple[str, ...] = ()
    suggested_collector: str | None = None
    estimated_size_bytes: int | None = Field(default=None, ge=0)
    priority: str = "normal"
    venue_probe_allowed: bool = False
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

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_gap(self) -> "DataGapRequest":
        if self.end_ts <= self.start_ts:
            raise ValueError("data gap end_ts must be greater than start_ts")
        if self.venue_probe_allowed and self.suggested_collector is None:
            raise ValueError("venue probes require a suggested collector")
        require_research_boundary(self, context="data gap request")
        return self


class StrategyDataRequirementRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    strategy_spec: dict[str, Any]
    archive_root: str = "data/research/central_market_history"
    repo_root: str = "."
    instrument_ids: tuple[str, ...] = ()
    venue: str | None = None
    start_ts: datetime
    end_ts: datetime
    evidence_mode: str | None = None
    artifact_mode: ArtifactMode = ArtifactMode.FULL
    prefer_fast_lane: bool = False
    require_reference_audit: bool = False
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

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_request(self) -> "StrategyDataRequirementRequest":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        require_research_boundary(self, context="strategy data requirement request")
        return self


class BenchmarkObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    value: float = Field(ge=0.0)
    unit: str = Field(min_length=1)
    speedup_claimed: bool = False


class FastLaneExecutionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_id: str = "fast_lane_reference_authority_v1"
    reference_engine_authority: bool = True
    large_sweep_default_lane: str = "fast_vectorized"
    new_family_required_lanes: tuple[str, ...] = ("vectorized", "fast_vectorized")
    reference_audit_sample_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    suspicious_result_rerun_lane: str = "vectorized"
    parity_report_required: bool = True
    speedup_claimed: bool = False


class StrategyDataRequirementReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    requirement_report_id: str = Field(min_length=64, max_length=64)
    strategy_id: str = Field(min_length=1)
    spec_hash: str = Field(min_length=64, max_length=64)
    ready: bool
    usable_instruments: tuple[str, ...] = ()
    missing_instruments: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    missing_families: tuple[str, ...] = ()
    missing_time_ranges: tuple[str, ...] = ()
    usable_archive_refs: tuple[str, ...] = ()
    required_feature_materializations: tuple[str, ...] = ()
    recommended_collection_tasks: tuple[str, ...] = ()
    do_not_collect_reason: str | None = None
    data_gap_requests: tuple[DataGapRequest, ...] = ()
    archive_inventory_hash: str = Field(min_length=64, max_length=64)
    feature_catalog_id: str | None = None
    fast_lane_policy: FastLaneExecutionPolicy = Field(default_factory=FastLaneExecutionPolicy)
    recommended_engine_lane: str = "vectorized"
    reference_audit_required: bool = False
    fast_lane_reason: str | None = None
    artifact_mode: ArtifactMode = ArtifactMode.FULL
    replayable_to_full_artifacts: bool = True
    benchmark_observations: tuple[BenchmarkObservation, ...] = ()
    blocker_reasons: tuple[str, ...] = ()
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
    def _validate_report(self) -> "StrategyDataRequirementReport":
        if self.ready and self.data_gap_requests:
            raise ValueError("ready reports cannot include data gap requests")
        if self.ready and self.blocker_reasons:
            raise ValueError("ready reports cannot include blocker reasons")
        require_research_boundary(self, context="strategy data requirement report")
        return self
