# V2-AUDIT-ID: V2-AUD-FINAL-001
# V2-CONTRACTS: docs/contracts/validation_contract.md, docs/contracts/lead_book_contract.md
# V2-BOUNDARY: research_only, final_governance_only, no_live_imports
# V2-OWNER: v2_validation
"""Deep-validation and final hard-test governance helpers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.lead_book.schemas import LeadBookRow, LeadState

FINAL_HARD_TEST_MAX_SLOTS = 3
NON_LIVE_SURVIVOR_DISCLAIMER = (
    "Final hard-test survivor reports are research-only governance artifacts. "
    "They are not paper/live/trade-ready signals and do not authorize orders, sizing, "
    "runtime changes, candidate packs, or promotion."
)


class DeepValidationStatus(str, Enum):
    REQUESTED = "requested"
    RUNNING = "running"
    COMPLETED = "completed"
    REJECTED = "rejected"


class Pre2024FallbackStatus(str, Enum):
    NOT_USED = "not_used"
    FAILED_LEAD = "failed_lead"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    RETURN_TO_RESEARCH_QUEUE_WITH_WARNING = "return_to_research_queue_with_warning"


class DeepValidationScorecard(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    full_valid_2024_history: bool
    min_six_months: bool
    lockbox_excluded: bool
    asof_universe_snapshot: bool
    walk_forward_validation: bool
    negative_controls: bool
    feature_ablations: bool
    filter_ablations: bool
    exit_lab_fixed_hold_comparison: bool
    cost_stress: bool
    concentration_checks: bool
    parameter_neighborhood_stability: bool
    regime_robustness: bool
    venue_symbol_robustness: bool
    diminishing_returns_checked: bool
    failure_mode_report: bool
    pre_2024_fallback_status: Pre2024FallbackStatus = Pre2024FallbackStatus.NOT_USED
    passed: bool
    missing_checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @classmethod
    def build(cls, **checks: bool | str) -> "DeepValidationScorecard":
        bool_fields = [
            "full_valid_2024_history",
            "min_six_months",
            "lockbox_excluded",
            "asof_universe_snapshot",
            "walk_forward_validation",
            "negative_controls",
            "feature_ablations",
            "filter_ablations",
            "exit_lab_fixed_hold_comparison",
            "cost_stress",
            "concentration_checks",
            "parameter_neighborhood_stability",
            "regime_robustness",
            "venue_symbol_robustness",
            "diminishing_returns_checked",
            "failure_mode_report",
        ]
        values = {field: bool(checks.get(field, False)) for field in bool_fields}
        missing = tuple(field for field in bool_fields if not values[field])
        fallback_status = Pre2024FallbackStatus(str(checks.get("pre_2024_fallback_status", "not_used")))
        warnings: list[str] = []
        if fallback_status != Pre2024FallbackStatus.NOT_USED:
            warnings.append("pre_2024_fallback_diagnostic_only")
        return cls(
            **values,
            pre_2024_fallback_status=fallback_status,
            passed=not missing,
            missing_checks=missing,
            warnings=tuple(warnings),
        )

    @model_validator(mode="after")
    def _validate_scorecard(self) -> "DeepValidationScorecard":
        _require_boundary(self.research_only, self.observe_only, self.promotion_ready)
        required_values = {
            "full_valid_2024_history": self.full_valid_2024_history,
            "min_six_months": self.min_six_months,
            "lockbox_excluded": self.lockbox_excluded,
            "asof_universe_snapshot": self.asof_universe_snapshot,
            "walk_forward_validation": self.walk_forward_validation,
            "negative_controls": self.negative_controls,
            "feature_ablations": self.feature_ablations,
            "filter_ablations": self.filter_ablations,
            "exit_lab_fixed_hold_comparison": self.exit_lab_fixed_hold_comparison,
            "cost_stress": self.cost_stress,
            "concentration_checks": self.concentration_checks,
            "parameter_neighborhood_stability": self.parameter_neighborhood_stability,
            "regime_robustness": self.regime_robustness,
            "venue_symbol_robustness": self.venue_symbol_robustness,
            "diminishing_returns_checked": self.diminishing_returns_checked,
            "failure_mode_report": self.failure_mode_report,
        }
        missing = tuple(field for field, value in required_values.items() if not value)
        if self.passed and missing:
            raise ValueError("deep validation scorecard cannot pass with missing checks")
        if set(self.missing_checks) != set(missing):
            raise ValueError("deep validation scorecard missing_checks mismatch")
        if (
            self.pre_2024_fallback_status != Pre2024FallbackStatus.NOT_USED
            and "pre_2024_fallback_diagnostic_only" not in self.warnings
        ):
            raise ValueError("pre-2024 fallback must be labeled diagnostic-only")
        return self


class DeepValidationManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_id: str = Field(min_length=64, max_length=64)
    lead_id: str = Field(min_length=1)
    status: DeepValidationStatus
    scorecard: DeepValidationScorecard
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    active_serious_lead_lock: bool = True
    failure_reason: str | None = None
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
    def _validate_manifest(self) -> "DeepValidationManifest":
        _require_boundary(self.research_only, self.observe_only, self.promotion_ready)
        _reject_forbidden_flags(self)
        if self.status == DeepValidationStatus.RUNNING and not self.active_serious_lead_lock:
            raise ValueError("running deep validation requires active serious lead lock")
        if self.status in {DeepValidationStatus.COMPLETED, DeepValidationStatus.REJECTED} and self.completed_at is None:
            raise ValueError("terminal deep validation manifests require completed_at")
        if self.status == DeepValidationStatus.COMPLETED and not self.scorecard.passed:
            raise ValueError("completed deep validation requires passing scorecard")
        if self.status == DeepValidationStatus.REJECTED and not self.failure_reason:
            raise ValueError("rejected deep validation requires failure_reason")
        return self


class Pre2024FallbackDiagnostic(BaseModel):
    model_config = ConfigDict(frozen=True)

    diagnostic_id: str = Field(min_length=64, max_length=64)
    lead_id: str = Field(min_length=1)
    available: bool
    passed: bool = False
    status: Pre2024FallbackStatus
    required_label: str = "diagnostic_fallback_only"
    modern_evidence_substituted: bool = False
    warning: str | None = None
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_fallback(self) -> "Pre2024FallbackDiagnostic":
        _require_boundary(self.research_only, self.observe_only, self.promotion_ready)
        if self.required_label != "diagnostic_fallback_only":
            raise ValueError("pre-2024 fallback requires diagnostic_fallback_only label")
        if self.modern_evidence_substituted:
            raise ValueError("pre-2024 fallback cannot substitute for mandatory 2024+ evidence")
        if self.available is False and self.status != Pre2024FallbackStatus.FAILED_LEAD:
            raise ValueError("unavailable pre-2024 fallback must fail the lead")
        return self


class FinalHardTestSlot(BaseModel):
    model_config = ConfigDict(frozen=True)

    slot_id: str = Field(min_length=64, max_length=64)
    lead_id: str = Field(min_length=1)
    slot_rank: int = Field(ge=1, le=FINAL_HARD_TEST_MAX_SLOTS)
    frozen_strategy_spec_hash: str = Field(min_length=64, max_length=64)
    frozen_params_hash: str = Field(min_length=64, max_length=64)
    frozen_data_manifest_hash: str = Field(min_length=64, max_length=64)
    frozen_universe_snapshot_id: str = Field(min_length=64, max_length=64)
    frozen_cost_model_hash: str = Field(min_length=64, max_length=64)
    final_phase_manifest_id: str = Field(min_length=64, max_length=64)
    lockbox_access_allowed: bool = True
    parameter_edits_after_lockbox: bool = False
    final_result_to_leaderboard_section: str = "final_hard_test_separate_section_only"
    paper_live_implication: bool = False
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
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
    def _validate_slot(self) -> "FinalHardTestSlot":
        _require_boundary(self.research_only, self.observe_only, self.promotion_ready)
        _reject_forbidden_flags(self)
        if not self.lockbox_access_allowed:
            raise ValueError("final hard-test slot must explicitly represent final-phase lockbox access")
        if self.parameter_edits_after_lockbox:
            raise ValueError("parameter edits after lockbox access are forbidden")
        if self.paper_live_implication:
            raise ValueError("final hard-test slots cannot imply paper/live readiness")
        return self


class FinalSurvivorReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str = Field(min_length=64, max_length=64)
    slot_id: str = Field(min_length=64, max_length=64)
    lead_id: str = Field(min_length=1)
    result_summary: str = Field(min_length=1)
    non_live_disclaimer: str = NON_LIVE_SURVIVOR_DISCLAIMER
    paper_live_implication: bool = False
    trade_readiness_claim: bool = False
    order_authorization: bool = False
    sizing_authorization: bool = False
    runtime_mode_change_authorization: bool = False
    promotion_ready: bool = False
    schema_version: str = V2_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utc_now)
    research_only: bool = True
    observe_only: bool = True
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> "FinalSurvivorReport":
        _require_boundary(self.research_only, self.observe_only, self.promotion_ready)
        _reject_forbidden_flags(self)
        forbidden = {
            "paper_live_implication": self.paper_live_implication,
            "trade_readiness_claim": self.trade_readiness_claim,
            "order_authorization": self.order_authorization,
            "sizing_authorization": self.sizing_authorization,
            "runtime_mode_change_authorization": self.runtime_mode_change_authorization,
        }
        enabled = [name for name, value in forbidden.items() if value]
        if enabled:
            raise ValueError("final survivor report violates non-live disclaimer: " + ",".join(enabled))
        if "not paper/live/trade-ready" not in self.non_live_disclaimer:
            raise ValueError("final survivor report requires non-live disclaimer")
        return self


def start_deep_validation(
    *,
    lead: LeadBookRow,
    existing_manifests: Iterable[DeepValidationManifest],
    scorecard: DeepValidationScorecard,
) -> DeepValidationManifest:
    if lead.state != LeadState.DEEP_VALIDATION_REQUESTED:
        raise ValueError("deep_validation_start_requires_requested_lead")
    running = [manifest for manifest in existing_manifests if manifest.status == DeepValidationStatus.RUNNING]
    if running:
        raise ValueError("one_active_serious_lead_lock")
    return _deep_validation_manifest(
        lead_id=lead.lead_id,
        status=DeepValidationStatus.RUNNING,
        scorecard=scorecard,
    )


def complete_deep_validation(
    manifest: DeepValidationManifest,
    *,
    scorecard: DeepValidationScorecard,
) -> DeepValidationManifest:
    status = DeepValidationStatus.COMPLETED if scorecard.passed else DeepValidationStatus.REJECTED
    return _deep_validation_manifest(
        lead_id=manifest.lead_id,
        status=status,
        scorecard=scorecard,
        completed_at=utc_now(),
        failure_reason=None if scorecard.passed else "deep_validation_scorecard_failed",
    )


def build_pre_2024_fallback_diagnostic(
    *,
    lead_id: str,
    available: bool,
    passed: bool = False,
) -> Pre2024FallbackDiagnostic:
    if not available:
        status = Pre2024FallbackStatus.FAILED_LEAD
        warning = "pre_2024_fallback_unavailable_failed_lead"
    elif passed:
        status = Pre2024FallbackStatus.RETURN_TO_RESEARCH_QUEUE_WITH_WARNING
        warning = "pre_2024_fallback_passed_diagnostic_only"
    else:
        status = Pre2024FallbackStatus.DIAGNOSTIC_ONLY
        warning = "pre_2024_fallback_failed_diagnostic_only"
    payload = {
        "lead_id": lead_id,
        "available": available,
        "passed": passed,
        "status": status.value,
        "required_label": "diagnostic_fallback_only",
        "schema_version": V2_SCHEMA_VERSION,
    }
    return Pre2024FallbackDiagnostic(
        diagnostic_id=canonical_json_hash(payload),
        lead_id=lead_id,
        available=available,
        passed=passed,
        status=status,
        warning=warning,
    )


def allocate_final_hard_test_slot(
    *,
    lead: LeadBookRow,
    existing_slots: Iterable[FinalHardTestSlot],
    slot_rank: int,
    frozen_strategy_spec_hash: str,
    frozen_params_hash: str,
    frozen_data_manifest_hash: str,
    frozen_universe_snapshot_id: str,
    frozen_cost_model_hash: str,
    final_phase_manifest_id: str,
) -> FinalHardTestSlot:
    if lead.state not in {LeadState.DEEP_VALIDATION_APPROVED, LeadState.FINAL_TEST_CANDIDATE}:
        raise ValueError("final_hard_test_requires_deep_validation_approved_lead")
    active_slots = [slot for slot in existing_slots if slot.active]
    if len(active_slots) >= FINAL_HARD_TEST_MAX_SLOTS:
        raise ValueError("final_hard_test_rejects_more_than_three_slots")
    if any(slot.lead_id == lead.lead_id for slot in active_slots):
        raise ValueError("final_hard_test_duplicate_lead_slot")
    payload = {
        "lead_id": lead.lead_id,
        "slot_rank": slot_rank,
        "frozen_strategy_spec_hash": frozen_strategy_spec_hash,
        "frozen_params_hash": frozen_params_hash,
        "frozen_data_manifest_hash": frozen_data_manifest_hash,
        "frozen_universe_snapshot_id": frozen_universe_snapshot_id,
        "frozen_cost_model_hash": frozen_cost_model_hash,
        "final_phase_manifest_id": final_phase_manifest_id,
        "schema_version": V2_SCHEMA_VERSION,
    }
    return FinalHardTestSlot(slot_id=canonical_json_hash(payload), **payload)


def reject_parameter_edit_after_lockbox(slot: FinalHardTestSlot, *, attempted_params_hash: str) -> None:
    if attempted_params_hash != slot.frozen_params_hash:
        raise ValueError("parameter_edits_after_lockbox_access_are_forbidden")


def build_final_survivor_report(
    *,
    slot: FinalHardTestSlot,
    result_summary: str,
) -> FinalSurvivorReport:
    payload = {
        "slot_id": slot.slot_id,
        "lead_id": slot.lead_id,
        "result_summary": result_summary,
        "non_live_disclaimer": NON_LIVE_SURVIVOR_DISCLAIMER,
        "schema_version": V2_SCHEMA_VERSION,
    }
    return FinalSurvivorReport(
        report_id=canonical_json_hash(payload),
        slot_id=slot.slot_id,
        lead_id=slot.lead_id,
        result_summary=result_summary,
    )


def _deep_validation_manifest(
    *,
    lead_id: str,
    status: DeepValidationStatus,
    scorecard: DeepValidationScorecard,
    completed_at: datetime | None = None,
    failure_reason: str | None = None,
) -> DeepValidationManifest:
    payload = {
        "lead_id": lead_id,
        "status": status.value,
        "scorecard": scorecard.model_dump(mode="json"),
        "completed": completed_at is not None,
        "failure_reason": failure_reason,
        "schema_version": V2_SCHEMA_VERSION,
    }
    return DeepValidationManifest(
        manifest_id=canonical_json_hash(payload),
        lead_id=lead_id,
        status=status,
        scorecard=scorecard,
        completed_at=completed_at,
        failure_reason=failure_reason,
    )


def _require_boundary(research_only: bool, observe_only: bool, promotion_ready: bool) -> None:
    if not research_only or not observe_only or promotion_ready:
        raise ValueError("deep-validation governance records must preserve the v2 research boundary")


def _reject_forbidden_flags(model: BaseModel) -> None:
    forbidden_names = (
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    )
    enabled = [name for name in forbidden_names if bool(getattr(model, name, False))]
    if enabled:
        raise ValueError("deep-validation governance record violates research boundary: " + ",".join(enabled))
