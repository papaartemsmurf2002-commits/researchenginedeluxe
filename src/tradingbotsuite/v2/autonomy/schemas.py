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
