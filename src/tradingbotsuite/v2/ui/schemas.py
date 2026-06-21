# V2-AUDIT-ID: V2-AUD-UI-001
# V2-CONTRACTS: docs/contracts/ui_visibility_contract.md
# V2-BOUNDARY: research_only, read_only_visibility, no_live_imports
# V2-OWNER: v2_ui
"""Snapshot schemas for the read-only v2 visibility UI."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class UniverseVisibilityRow(_FrozenModel):
    venue: str
    instrument_id: str
    included: bool
    reason: str = ""
    day_notional_usd: float | None = None
    evidence_scope: str = "as_of"
    caveats: tuple[str, ...] = Field(default_factory=tuple)


class CollectionStatusRow(_FrozenModel):
    source: str
    datatype: str
    status: str
    latest_event_ts: datetime | None = None
    manifest_refs: tuple[str, ...] = Field(default_factory=tuple)
    gap_count: int = 0
    notes: str = ""

    @field_validator("gap_count")
    @classmethod
    def _gap_count_is_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("gap_count must be non-negative")
        return value


class ArchiveCoverageRow(_FrozenModel):
    venue: str
    instrument_id: str
    family: str
    timeframe: str
    start_ts: datetime
    end_ts: datetime
    coverage_ratio: float
    status: str
    missing_days: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("coverage_ratio")
    @classmethod
    def _coverage_ratio_in_range(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("coverage_ratio must be between 0 and 1")
        return value


class GapReportRow(_FrozenModel):
    report_id: str
    venue: str
    instrument_id: str
    family: str
    timeframe: str
    gap_count: int
    severity: str
    sample: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("gap_count")
    @classmethod
    def _gap_count_is_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("gap_count must be non-negative")
        return value


class LockboxVisibility(_FrozenModel):
    policy_id: str
    start_ts: datetime
    end_ts: datetime
    excluded_from_tuning: bool = True
    notes: str = ""

    @model_validator(mode="after")
    def _validate_lockbox(self) -> "LockboxVisibility":
        if self.end_ts <= self.start_ts:
            raise ValueError("lockbox end_ts must be after start_ts")
        if not self.excluded_from_tuning:
            raise ValueError("lockbox must be excluded from tuning")
        return self


class LeadBookVisibilityRow(_FrozenModel):
    lead_id: str
    strategy_family: str
    state: str
    human_inspection_status: str
    agent_approval_status: str
    promotion_ready: bool = False
    blocker_reasons: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _reject_promotion_ready_lead(self) -> "LeadBookVisibilityRow":
        if self.promotion_ready:
            raise ValueError("v2 UI lead rows must not be promotion_ready")
        return self


class DeepValidationVisibilityRow(_FrozenModel):
    lead_id: str
    status: str
    active: bool = False
    scorecard_status: str = "not_started"
    blocker_reasons: tuple[str, ...] = Field(default_factory=tuple)


class FinalHardTestVisibilityRow(_FrozenModel):
    slot_id: str
    lead_id: str
    status: str
    frozen_evidence: bool
    non_live_disclaimer: str

    @field_validator("non_live_disclaimer")
    @classmethod
    def _disclaimer_is_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("non_live_disclaimer must be non-empty")
        return value


class AuditChunkVisibilityRow(_FrozenModel):
    audit_id: str
    area: str
    status: str
    purpose: str
    evidence: str = ""


class WorkerJobVisibilityRow(_FrozenModel):
    job_id: str
    kind: str
    status: str
    terminal_state: bool = False
    attempts: int = 0
    archive_manifest_refs: tuple[str, ...] = Field(default_factory=tuple)
    failure_reason: str = ""

    @field_validator("attempts")
    @classmethod
    def _attempts_is_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("attempts must be non-negative")
        return value


class V2VisibilitySnapshot(_FrozenModel):
    snapshot_id: str
    generated_at: datetime
    title: str = "ResearchEngineDeluxe v2 Visibility"
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    read_only: bool = True
    command_controls_enabled: bool = False
    runtime_mutation_enabled: bool = False
    active_universe: tuple[UniverseVisibilityRow, ...] = Field(default_factory=tuple)
    collection_status: tuple[CollectionStatusRow, ...] = Field(default_factory=tuple)
    archive_coverage: tuple[ArchiveCoverageRow, ...] = Field(default_factory=tuple)
    gap_reports: tuple[GapReportRow, ...] = Field(default_factory=tuple)
    lockbox: LockboxVisibility | None = None
    lead_book: tuple[LeadBookVisibilityRow, ...] = Field(default_factory=tuple)
    deep_validation: tuple[DeepValidationVisibilityRow, ...] = Field(default_factory=tuple)
    final_hard_tests: tuple[FinalHardTestVisibilityRow, ...] = Field(default_factory=tuple)
    audit_chunks: tuple[AuditChunkVisibilityRow, ...] = Field(default_factory=tuple)
    worker_jobs: tuple[WorkerJobVisibilityRow, ...] = Field(default_factory=tuple)
    notes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("snapshot_id")
    @classmethod
    def _snapshot_id_is_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("snapshot_id must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_boundary(self) -> "V2VisibilitySnapshot":
        reasons: list[str] = []
        if not self.research_only:
            reasons.append("research_only_false")
        if not self.observe_only:
            reasons.append("observe_only_false")
        if self.promotion_ready:
            reasons.append("promotion_ready_true")
        if not self.read_only:
            reasons.append("read_only_false")
        if self.command_controls_enabled:
            reasons.append("command_controls_enabled")
        if self.runtime_mutation_enabled:
            reasons.append("runtime_mutation_enabled")
        if reasons:
            raise ValueError("invalid v2 UI boundary flags: " + ", ".join(reasons))
        return self

    def section_counts(self) -> dict[str, int]:
        return {
            "active_universe": len(self.active_universe),
            "collection_status": len(self.collection_status),
            "archive_coverage": len(self.archive_coverage),
            "gap_reports": len(self.gap_reports),
            "lockbox": 1 if self.lockbox is not None else 0,
            "lead_book": len(self.lead_book),
            "deep_validation": len(self.deep_validation),
            "final_hard_tests": len(self.final_hard_tests),
            "audit_chunks": len(self.audit_chunks),
            "worker_jobs": len(self.worker_jobs),
        }


def snapshot_from_json(text: str | bytes) -> V2VisibilitySnapshot:
    return V2VisibilitySnapshot.model_validate_json(text)


def snapshot_from_mapping(payload: dict[str, Any]) -> V2VisibilitySnapshot:
    return V2VisibilitySnapshot.model_validate(payload)
