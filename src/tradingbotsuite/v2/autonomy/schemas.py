# V2-AUDIT-ID: V2-AUD-AUTONOMY-001
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md
# V2-BOUNDARY: research_only, sandbox_diagnostic, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_autonomy
"""Schemas for the v2 autonomy dry-run loop."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.workers.models import WorkerJobKind


class AutonomyStepStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AutonomyLoopStatus(str, Enum):
    COMPLETED = "completed"
    COMPLETED_WITH_BLOCKERS = "completed_with_blockers"
    FAILED = "failed"


class AutonomyDataMode(str, Enum):
    ARCHIVE_FIXTURE = "archive_fixture"
    MANIFEST_FIXTURE = "manifest_fixture"


class AutonomyDryRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    run_id: str = Field(default="autonomy-dry-run", pattern=r"^[A-Za-z0-9_.-]+$")
    output_root: str = Field(min_length=1)
    strategy_id: str = "hl_funding_carry_v1"
    data_mode: AutonomyDataMode = AutonomyDataMode.ARCHIVE_FIXTURE
    evidence_mode: str = "sandbox_diagnostic"
    created_by_id: str = "codex-manager-agent"

    @field_validator("evidence_mode")
    @classmethod
    def _sandbox_only(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized != "sandbox_diagnostic":
            raise ValueError("autonomy dry-run evidence_mode must be sandbox_diagnostic")
        return normalized


class AutonomyStepResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    status: AutonomyStepStatus
    artifact_path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
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
    def _validate_boundary(self) -> "AutonomyStepResult":
        require_research_boundary(self, context="autonomy step")
        return self


class AutonomyBlockerReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "autonomy_blocker_report_v1"
    run_id: str = Field(min_length=1)
    status: AutonomyLoopStatus
    accepted_research_ready: bool = False
    evidence_mode: str = "sandbox_diagnostic"
    blocker_reasons: tuple[str, ...]
    required_next_actions: tuple[str, ...]
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

    @model_validator(mode="after")
    def _validate_boundary(self) -> "AutonomyBlockerReport":
        if self.accepted_research_ready:
            raise ValueError("dry-run blocker reports cannot mark accepted_research_ready")
        require_research_boundary(self, context="autonomy blocker report")
        return self


class AutonomyDryRunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "autonomy_dry_run_v1"
    run_id: str = Field(min_length=1)
    status: AutonomyLoopStatus
    evidence_mode: str = "sandbox_diagnostic"
    strategy_id: str = Field(min_length=1)
    backtest_run_id: str = Field(min_length=1)
    output_root: str = Field(min_length=1)
    backtest_run_dir: str = Field(min_length=1)
    ledger_path: str = Field(min_length=1)
    lead_book_path: str = Field(min_length=1)
    blocker_report_path: str = Field(min_length=1)
    artifact_paths: dict[str, str]
    steps: tuple[AutonomyStepResult, ...]
    decisions_made: tuple[str, ...]
    blocker_reasons: tuple[str, ...]
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

    @model_validator(mode="after")
    def _validate_boundary(self) -> "AutonomyDryRunManifest":
        if self.evidence_mode != "sandbox_diagnostic":
            raise ValueError("autonomy dry-run manifest must stay sandbox_diagnostic")
        require_research_boundary(self, context="autonomy manifest")
        return self


class AutonomyDryRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: AutonomyLoopStatus
    manifest_path: str = Field(min_length=1)
    blocker_report_path: str = Field(min_length=1)
    ledger_path: str = Field(min_length=1)
    lead_book_path: str = Field(min_length=1)
    backtest_run_dir: str = Field(min_length=1)
    blocker_reasons: tuple[str, ...]


class AutopilotCycleMode(str, Enum):
    BOUNDED = "bounded"


class AutopilotCyclePlanStatus(str, Enum):
    PLANNED = "planned"
    ENQUEUED = "enqueued"


class AutopilotCycleJobSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.:-]+$")
    kind: WorkerJobKind
    input_spec: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def _reject_audit_check(self) -> "AutopilotCycleJobSpec":
        if self.kind == WorkerJobKind.AUDIT_CHECK:
            raise ValueError("audit_check jobs are generated by the bounded cycle planner")
        return self


class AutopilotCycleBindingSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_job_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.:-]+$")
    target_job_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.:-]+$")
    target_input_path: str = Field(
        min_length=1,
        pattern=r"^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$",
    )
    source_ref_prefix: str = Field(min_length=1)

    @field_validator("source_ref_prefix")
    @classmethod
    def _require_value_prefix(cls, value: str) -> str:
        if not value.endswith("="):
            raise ValueError("binding source_ref_prefix must end with '='")
        return value


class AutopilotCyclePlanConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "autopilot_bounded_cycle_spec_v1"
    run_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.-]+$")
    mode: AutopilotCycleMode = AutopilotCycleMode.BOUNDED
    jobs: tuple[AutopilotCycleJobSpec, ...] = Field(min_length=1)
    bindings: tuple[AutopilotCycleBindingSpec, ...] = Field(default=(), max_length=500)
    max_jobs: int = Field(default=10, ge=1, le=100)
    audit_job_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.:-]+$")
    audit_report_path: str | None = None
    required_successful_job_kinds: tuple[WorkerJobKind, ...] = ()
    required_artifact_ref_prefixes: tuple[str, ...] = ()
    required_job_kind_order: tuple[WorkerJobKind, ...] = ()
    required_next_actions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_unique_jobs(self) -> "AutopilotCyclePlanConfig":
        job_ids = [job.job_id for job in self.jobs]
        if len(job_ids) != len(set(job_ids)):
            raise ValueError("bounded cycle job_id values must be unique")
        if self.audit_job_id is not None and self.audit_job_id in set(job_ids):
            raise ValueError("audit_job_id must not duplicate a planned job_id")
        return self


class AutopilotPlannedJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    kind: WorkerJobKind
    input_spec_hash: str = Field(min_length=64, max_length=64)
    max_attempts: int = Field(ge=1)
    dependency_order: int = Field(ge=0)
    generated_by_planner: bool = False
    enqueued: bool = False


class AutopilotCyclePlanManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "autopilot_bounded_cycle_plan_v1"
    plan_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    mode: AutopilotCycleMode = AutopilotCycleMode.BOUNDED
    status: AutopilotCyclePlanStatus
    output_root: str = Field(min_length=1)
    job_store_path: str | None = None
    plan_manifest_path: str = Field(min_length=1)
    planned_jobs: tuple[AutopilotPlannedJob, ...]
    bindings: tuple[AutopilotCycleBindingSpec, ...] = ()
    audit_job_id: str = Field(min_length=1)
    audit_report_path: str = Field(min_length=1)
    required_successful_job_kinds: tuple[str, ...]
    required_artifact_ref_prefixes: tuple[str, ...]
    required_job_kind_order: tuple[str, ...]
    required_next_actions: tuple[str, ...]
    accepted_research_ready: bool = False
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

    @model_validator(mode="after")
    def _validate_boundary(self) -> "AutopilotCyclePlanManifest":
        if self.accepted_research_ready:
            raise ValueError("bounded cycle plans cannot mark accepted_research_ready")
        require_research_boundary(self, context="autopilot cycle plan")
        return self


class AutopilotCyclePlanResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: AutopilotCyclePlanStatus
    plan_manifest_path: str = Field(min_length=1)
    plan_id: str = Field(min_length=64, max_length=64)
    planned_job_count: int = Field(ge=0)
    enqueued_job_count: int = Field(ge=0)
    audit_job_id: str = Field(min_length=1)
    audit_report_path: str = Field(min_length=1)


class AutopilotCycleExecutionStatus(str, Enum):
    COMPLETED = "completed"
    COMPLETED_WITH_BLOCKERS = "completed_with_blockers"


class AutopilotCycleJobExecutionAction(str, Enum):
    RAN = "ran"
    SKIPPED_ALREADY_SUCCEEDED = "skipped_already_succeeded"
    BLOCKED_MISSING = "blocked_missing"
    BLOCKED_BINDING = "blocked_binding"
    BLOCKED_NOT_NEXT_FOR_KIND = "blocked_not_next_for_kind"
    BLOCKED_STATUS = "blocked_status"
    NOT_RUN_AFTER_BLOCKER = "not_run_after_blocker"
    NOT_RUN_MAX_JOBS = "not_run_max_jobs"


class AutopilotCycleJobExecution(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    kind: WorkerJobKind
    dependency_order: int = Field(ge=0)
    generated_by_planner: bool = False
    action: AutopilotCycleJobExecutionAction
    status_before: str | None = None
    status_after: str | None = None
    input_spec_hash_before: str | None = Field(default=None, min_length=64, max_length=64)
    input_spec_hash_after: str | None = Field(default=None, min_length=64, max_length=64)
    applied_bindings: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    archive_manifest_refs: tuple[str, ...] = ()
    gap_record_ids: tuple[str, ...] = ()
    failure_reason: str | None = None
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
    def _validate_boundary(self) -> "AutopilotCycleJobExecution":
        require_research_boundary(self, context="autopilot cycle job execution")
        return self


class AutopilotCycleExecutionManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "autopilot_bounded_cycle_execution_v1"
    execution_id: str = Field(min_length=64, max_length=64)
    plan_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    mode: AutopilotCycleMode = AutopilotCycleMode.BOUNDED
    status: AutopilotCycleExecutionStatus
    plan_manifest_path: str = Field(min_length=1)
    execution_manifest_path: str = Field(min_length=1)
    job_store_path: str = Field(min_length=1)
    worker_id: str = Field(min_length=1)
    max_jobs: int = Field(ge=1)
    planned_job_count: int = Field(ge=0)
    executed_job_count: int = Field(ge=0)
    skipped_job_count: int = Field(ge=0)
    audit_job_id: str = Field(min_length=1)
    audit_report_path: str = Field(min_length=1)
    audit_attempted: bool = False
    blocker_count: int = Field(ge=0)
    blocker_reasons: tuple[str, ...] = ()
    job_executions: tuple[AutopilotCycleJobExecution, ...]
    accepted_research_ready: bool = False
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

    @model_validator(mode="after")
    def _validate_boundary(self) -> "AutopilotCycleExecutionManifest":
        if self.accepted_research_ready:
            raise ValueError("bounded cycle executions cannot mark accepted_research_ready")
        if self.blocker_count != len(self.blocker_reasons):
            raise ValueError("blocker_count must match blocker_reasons length")
        if self.status == AutopilotCycleExecutionStatus.COMPLETED and self.blocker_reasons:
            raise ValueError("completed cycle executions cannot contain blockers")
        if (
            self.status == AutopilotCycleExecutionStatus.COMPLETED_WITH_BLOCKERS
            and not self.blocker_reasons
        ):
            raise ValueError("completed_with_blockers cycle executions require blockers")
        require_research_boundary(self, context="autopilot cycle execution")
        return self


class AutopilotCycleExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: AutopilotCycleExecutionStatus
    execution_manifest_path: str = Field(min_length=1)
    execution_id: str = Field(min_length=64, max_length=64)
    audit_report_path: str = Field(min_length=1)
    executed_job_count: int = Field(ge=0)
    skipped_job_count: int = Field(ge=0)
    audit_attempted: bool
    blocker_reasons: tuple[str, ...] = ()


class AutopilotSchedulerTickStatus(str, Enum):
    COMPLETED = "completed"
    COMPLETED_WITH_BLOCKERS = "completed_with_blockers"


class AutopilotSchedulerPlanAction(str, Enum):
    RAN = "ran"
    BLOCKED = "blocked"
    DEFERRED_MAX_PLANS = "deferred_max_plans"


class AutopilotSchedulerPlanResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_manifest_path: str = Field(min_length=1)
    action: AutopilotSchedulerPlanAction
    status: str = Field(min_length=1)
    execution_manifest_path: str | None = None
    execution_id: str | None = None
    audit_report_path: str | None = None
    executed_job_count: int = Field(default=0, ge=0)
    skipped_job_count: int = Field(default=0, ge=0)
    audit_attempted: bool = False
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
    def _validate_boundary(self) -> "AutopilotSchedulerPlanResult":
        require_research_boundary(self, context="autopilot scheduler plan result")
        return self


class AutopilotSchedulerTickManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "autopilot_scheduler_tick_v1"
    session_id: str = Field(min_length=64, max_length=64)
    scheduler_id: str = Field(min_length=1)
    status: AutopilotSchedulerTickStatus
    output_root: str = Field(min_length=1)
    scheduler_manifest_path: str = Field(min_length=1)
    job_store_path: str | None = None
    worker_id: str = Field(min_length=1)
    max_plans: int = Field(ge=1)
    max_jobs_per_plan: int | None = Field(default=None, ge=1)
    requested_plan_count: int = Field(ge=0)
    selected_plan_count: int = Field(ge=0)
    executed_plan_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    blocker_reasons: tuple[str, ...] = ()
    plan_results: tuple[AutopilotSchedulerPlanResult, ...]
    accepted_research_ready: bool = False
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

    @model_validator(mode="after")
    def _validate_boundary(self) -> "AutopilotSchedulerTickManifest":
        if self.accepted_research_ready:
            raise ValueError("scheduler ticks cannot mark accepted_research_ready")
        if self.blocker_count != len(self.blocker_reasons):
            raise ValueError("blocker_count must match blocker_reasons length")
        if self.status == AutopilotSchedulerTickStatus.COMPLETED and self.blocker_reasons:
            raise ValueError("completed scheduler ticks cannot contain blockers")
        if (
            self.status == AutopilotSchedulerTickStatus.COMPLETED_WITH_BLOCKERS
            and not self.blocker_reasons
        ):
            raise ValueError("completed_with_blockers scheduler ticks require blockers")
        require_research_boundary(self, context="autopilot scheduler tick")
        return self


class AutopilotSchedulerTickResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: AutopilotSchedulerTickStatus
    scheduler_manifest_path: str = Field(min_length=1)
    session_id: str = Field(min_length=64, max_length=64)
    executed_plan_count: int = Field(ge=0)
    blocker_reasons: tuple[str, ...] = ()
