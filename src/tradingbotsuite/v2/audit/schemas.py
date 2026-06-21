# V2-AUDIT-ID: V2-AUD-AUDIT-001
# V2-CONTRACTS: docs/contracts/audit_report_contract.md
# V2-BOUNDARY: research_only, blocker_report, no_live_imports
# V2-OWNER: v2_audit
"""Schemas for durable v2 audit/blocker reports."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.security.boundary import require_research_boundary

AUDIT_BLOCKER_REPORT_SCHEMA_VERSION = "audit_blocker_report_v1"


class AuditReportStatus(str, Enum):
    PASS = "pass"
    COMPLETED_WITH_BLOCKERS = "completed_with_blockers"


class AuditJobSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    status: str = Field(min_length=1)
    terminal_state: bool
    attempts: int = Field(ge=0)
    finished_at: datetime | None = None
    failure_reason: str | None = None
    blocker_reasons: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    archive_manifest_refs: tuple[str, ...] = ()
    gap_record_ids: tuple[str, ...] = ()


class AuditBlockerReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = AUDIT_BLOCKER_REPORT_SCHEMA_VERSION
    report_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    created_at: datetime
    status: AuditReportStatus
    accepted_research_ready: bool = False
    job_store_path: str = Field(min_length=1)
    audited_job_ids: tuple[str, ...]
    job_status_counts: dict[str, int]
    blocker_reasons: tuple[str, ...] = ()
    required_next_actions: tuple[str, ...] = ()
    required_successful_job_kinds: tuple[str, ...] = ()
    required_artifact_ref_prefixes: tuple[str, ...] = ()
    required_job_kind_order: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    job_summaries: tuple[AuditJobSummary, ...] = ()
    boundary_flags: dict[str, bool] = Field(default_factory=lambda: dict(RESEARCH_BOUNDARY))
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

    @field_validator("created_at")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_report(self) -> "AuditBlockerReport":
        if self.accepted_research_ready:
            raise ValueError("audit blocker reports cannot mark accepted_research_ready")
        if self.status == AuditReportStatus.PASS and self.blocker_reasons:
            raise ValueError("pass audit reports cannot contain blocker_reasons")
        if self.status == AuditReportStatus.COMPLETED_WITH_BLOCKERS and not self.blocker_reasons:
            raise ValueError("completed_with_blockers audit reports require blocker_reasons")
        require_research_boundary(self, context="audit blocker report")
        return self
