# V2-AUDIT-ID: V2-AUD-WORKER-001
# V2-CONTRACTS: docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_jobs, no_live_imports
# V2-OWNER: v2_workers
"""Durable worker job schemas for v2."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now


class WorkerJobStatus(str, Enum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    STALE = "stale"


class WorkerJobKind(str, Enum):
    UNIVERSE_REFRESH = "universe_refresh"
    RECENT_CANDLE_BOOTSTRAP = "recent_candle_bootstrap"
    FUNDING_BACKFILL = "funding_backfill"
    WEBSOCKET_CAPTURE = "websocket_capture"
    WEBSOCKET_TRADE_CAPTURE = "websocket_trade_capture"
    WEBSOCKET_L2_BBO_CAPTURE = "websocket_l2_bbo_capture"
    OFFICIAL_S3_BACKFILL = "official_s3_backfill"
    COVERAGE_AUDIT = "coverage_audit"
    BACKTEST = "backtest"
    VECTORIZED_BACKTEST = "vectorized_backtest"
    EVENT_DRIVEN_SIMULATION = "event_driven_simulation"
    VALIDATION_GATE = "validation_gate"
    LEDGER_APPEND_EXPORT = "ledger_append_export"
    LEAD_BOOK_UPSERT = "lead_book_upsert"
    AUDIT_CHECK = "audit_check"


TERMINAL_STATUSES = {
    WorkerJobStatus.SUCCEEDED,
    WorkerJobStatus.FAILED,
    WorkerJobStatus.CANCELLED,
}


class WorkerJobRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    kind: WorkerJobKind
    status: WorkerJobStatus = WorkerJobStatus.QUEUED
    input_spec_hash: str = Field(min_length=64, max_length=64)
    input_spec: dict[str, Any] = Field(default_factory=dict)
    attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    queued_at: datetime = Field(default_factory=utc_now)
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    heartbeat_at: datetime | None = None
    lock_owner: str | None = None
    output_refs: tuple[str, ...] = ()
    archive_manifest_refs: tuple[str, ...] = ()
    gap_record_ids: tuple[str, ...] = ()
    failure_reason: str | None = None
    retry_after: datetime | None = None
    terminal_state: bool = False
    schema_version: str = V2_SCHEMA_VERSION
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
    def _validate_record(self) -> "WorkerJobRecord":
        if self.status in TERMINAL_STATUSES and not self.terminal_state:
            raise ValueError("terminal worker statuses must set terminal_state")
        if self.status not in TERMINAL_STATUSES and self.terminal_state:
            raise ValueError("non-terminal worker statuses cannot set terminal_state")
        if self.attempts > self.max_attempts:
            raise ValueError("attempts cannot exceed max_attempts")
        if self.status in {WorkerJobStatus.CLAIMED, WorkerJobStatus.RUNNING} and not self.lock_owner:
            raise ValueError("claimed/running jobs require a lock_owner")
        boundary = (
            self.research_only
            and self.observe_only
            and not self.promotion_ready
            and not self.candidate_evidence
            and not self.candidate_pack_eligible
            and not self.live_signal
            and not self.paper_signal
            and not self.sizing_instruction
            and not self.order_placement_instruction
            and not self.runtime_mode_change
        )
        if not boundary:
            raise ValueError("worker job records must preserve the v2 research boundary")
        return self


class WorkerHeartbeat(BaseModel):
    model_config = ConfigDict(frozen=True)

    heartbeat_id: str = Field(min_length=64, max_length=64)
    job_id: str = Field(min_length=1)
    worker_id: str = Field(min_length=1)
    status: WorkerJobStatus
    heartbeat_at: datetime = Field(default_factory=utc_now)
    details: dict[str, str] = Field(default_factory=dict)
    schema_version: str = V2_SCHEMA_VERSION


class WorkerTransition(BaseModel):
    model_config = ConfigDict(frozen=True)

    transition_id: str = Field(min_length=64, max_length=64)
    job_id: str = Field(min_length=1)
    from_status: WorkerJobStatus | None = None
    to_status: WorkerJobStatus
    worker_id: str | None = None
    reason: str = Field(min_length=1)
    transitioned_at: datetime = Field(default_factory=utc_now)
    schema_version: str = V2_SCHEMA_VERSION


class WorkerGapRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    gap_record_id: str = Field(min_length=64, max_length=64)
    job_id: str = Field(min_length=1)
    worker_id: str | None = None
    kind: WorkerJobKind
    reason: str = Field(min_length=1)
    start_ts: datetime | None = None
    end_ts: datetime | None = None
    backoff_seconds: int = Field(default=0, ge=0)
    reconnect_attempts: int = Field(default=0, ge=0)
    evidence_scope: str = "diagnostic_gap_record"
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_gap(self) -> "WorkerGapRecord":
        if self.start_ts is not None and self.end_ts is not None and self.end_ts < self.start_ts:
            raise ValueError("gap end_ts must be >= start_ts")
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("gap records must preserve the v2 research boundary")
        return self


class WorkerRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    status: WorkerJobStatus
    output_refs: tuple[str, ...] = ()
    archive_manifest_refs: tuple[str, ...] = ()
    gap_record_ids: tuple[str, ...] = ()
    failure_reason: str | None = None
