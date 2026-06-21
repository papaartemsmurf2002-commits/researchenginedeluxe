# V2-AUDIT-ID: V2-AUD-LEAD-001
# V2-CONTRACTS: docs/contracts/lead_book_contract.md
# V2-BOUNDARY: research_only, non_promotable_leads, no_live_imports
# V2-OWNER: v2_lead_book
"""Lead Book schemas for non-promotable v2 research leads."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.security.boundary import require_research_boundary

LEAD_BOOK_SCHEMA_VERSION = "lead_book_row_v1"


class LeadState(str, Enum):
    IDEA_ONLY = "idea_only"
    SANDBOX_SCREENED = "sandbox_screened"
    HUMAN_INSPECTION_REQUESTED = "human_inspection_requested"
    HUMAN_INSPECTION_COMPLETED = "human_inspection_completed"
    AGENT_APPROVED_AFTER_HUMAN_INSPECTION = "agent_approved_after_human_inspection"
    DEEP_VALIDATION_REQUESTED = "deep_validation_requested"
    DEEP_VALIDATION_APPROVED = "deep_validation_approved"
    DEEP_VALIDATION_RUNNING = "deep_validation_running"
    DEEP_VALIDATION_REJECTED = "deep_validation_rejected"
    FINAL_TEST_CANDIDATE = "final_test_candidate"
    FINAL_TEST_REJECTED = "final_test_rejected"
    FINAL_TEST_SURVIVOR = "final_test_survivor"


class HumanInspectionStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    COMPLETED = "completed"
    REJECTED = "rejected"


class AgentApprovalStatus(str, Enum):
    NOT_REVIEWED = "not_reviewed"
    APPROVED_AFTER_HUMAN_INSPECTION = "approved_after_human_inspection"
    REJECTED = "rejected"
    NEEDS_MORE_INFO = "needs_more_info"


class RoiProjectionConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class GateSeverity(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class TradeCountSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    avg_trades_per_month: float = Field(ge=0.0)
    total_trades: int = Field(default=0, ge=0)


class MonthlyStabilitySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    usable_months: int = Field(ge=0)
    losing_months_12m: int = Field(default=0, ge=0)
    positive_months_12m: int = Field(default=0, ge=0)
    pre_2024_fallback_label: str | None = None


class PnlConcentrationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    top_2_trades_profit_share: float = Field(default=0.0, ge=0.0)
    best_month_profit_share: float = Field(default=0.0, ge=0.0)


class LeadBookRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = LEAD_BOOK_SCHEMA_VERSION
    lead_id: str = Field(min_length=1)
    lead_version: str = "1"
    created_at: datetime
    created_by_type: str = Field(min_length=1)
    created_by_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_artifact_path: str = Field(min_length=1)
    source_artifact_sha256: str = Field(min_length=64, max_length=64)
    strategy_family: str = Field(min_length=1)
    economic_thesis: str = Field(min_length=1)
    venue_scope: str = Field(min_length=1)
    universe_scope: str = Field(min_length=1)
    instrument_scope: tuple[str, ...]
    hip3_or_rwa_flag: bool = False
    data_window_start: datetime
    data_window_end: datetime
    data_source: str = Field(min_length=1)
    archive_snapshot_id: str | None = None
    universe_snapshot_id: str | None = None
    feature_snapshot_id: str | None = None
    cost_assumptions: str = Field(min_length=1)
    funding_assumptions: str = Field(min_length=1)
    slippage_assumptions: str = Field(min_length=1)
    fill_assumptions: str = Field(min_length=1)
    headline_metrics: dict[str, Any] = Field(default_factory=dict)
    roi_observed: float
    roi_projected: float
    roi_projection_assumptions: str = Field(min_length=1)
    roi_projection_confidence: RoiProjectionConfidence = RoiProjectionConfidence.UNKNOWN
    roi_projection_is_not_claim: bool = True
    why_interesting: str = Field(min_length=1)
    known_blockers: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    required_next_validation: tuple[str, ...] = ()
    trade_count_summary: TradeCountSummary
    monthly_stability_summary: MonthlyStabilitySummary
    pnl_concentration_summary: PnlConcentrationSummary
    diminishing_returns_warning: bool = False
    pre_2024_fallback_absent: bool = False
    human_inspection_status: HumanInspectionStatus = HumanInspectionStatus.NOT_REQUESTED
    human_inspected_by: str | None = None
    human_inspected_at: datetime | None = None
    human_inspection_notes: str | None = None
    agent_approval_status: AgentApprovalStatus = AgentApprovalStatus.NOT_REVIEWED
    approving_agent_id: str | None = None
    approved_at: datetime | None = None
    state: LeadState = LeadState.IDEA_ONLY
    non_promotable_flags: tuple[str, ...] = ("lead_not_candidate", "research_only")
    notes: str = ""
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

    @field_validator("created_at", "data_window_start", "data_window_end", "human_inspected_at", "approved_at")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_lead(self) -> "LeadBookRow":
        if self.data_window_end <= self.data_window_start:
            raise ValueError("lead data_window_end must be after data_window_start")
        if not self.instrument_scope:
            raise ValueError("lead instrument_scope must not be empty")
        if not self.roi_projection_is_not_claim:
            raise ValueError("roi_projection_is_not_claim must be true")
        if "lead_not_candidate" not in self.non_promotable_flags:
            raise ValueError("lead rows require non_promotable lead_not_candidate flag")
        if self.agent_approval_status == AgentApprovalStatus.APPROVED_AFTER_HUMAN_INSPECTION:
            if self.human_inspection_status != HumanInspectionStatus.COMPLETED:
                raise ValueError("agent_approval_requires_human_inspection")
        deep_states = {
            LeadState.DEEP_VALIDATION_REQUESTED,
            LeadState.DEEP_VALIDATION_APPROVED,
            LeadState.DEEP_VALIDATION_RUNNING,
            LeadState.FINAL_TEST_CANDIDATE,
            LeadState.FINAL_TEST_REJECTED,
            LeadState.FINAL_TEST_SURVIVOR,
        }
        if self.state in deep_states:
            if self.human_inspection_status != HumanInspectionStatus.COMPLETED:
                raise ValueError("deep_validation_requires_human_inspection_completed")
            if self.agent_approval_status != AgentApprovalStatus.APPROVED_AFTER_HUMAN_INSPECTION:
                raise ValueError("deep_validation_requires_agent_approval_after_human_inspection")
        require_research_boundary(self, context="lead row")
        return self


class LeadGateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    lead_id: str = Field(min_length=1)
    status: GateSeverity
    warnings: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    avg_trades_per_month: float = Field(ge=0.0)
    usable_months: int = Field(ge=0)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
