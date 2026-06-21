from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.lead_book import (
    LeadState,
    approve_after_human_inspection,
    complete_human_inspection,
    create_lead_from_source,
    request_deep_validation,
)
from tradingbotsuite.v2.validation import (
    DeepValidationScorecard,
    DeepValidationStatus,
    FinalHardTestSlot,
    FinalSurvivorReport,
    Pre2024FallbackStatus,
    allocate_final_hard_test_slot,
    build_final_survivor_report,
    build_pre_2024_fallback_diagnostic,
    complete_deep_validation,
    reject_parameter_edit_after_lockbox,
    start_deep_validation,
)


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64
HEX_E = "e" * 64
HEX_F = "f" * 64


def test_deep_validation_only_one_active_serious_lead(tmp_path) -> None:
    first = _requested_lead(tmp_path, "first.txt")
    second = _requested_lead(tmp_path, "second.txt")
    running = start_deep_validation(
        lead=first,
        existing_manifests=(),
        scorecard=_passing_scorecard(),
    )

    assert running.status == DeepValidationStatus.RUNNING
    assert running.scorecard.passed is True
    with pytest.raises(ValueError, match="one_active_serious_lead_lock"):
        start_deep_validation(
            lead=second,
            existing_manifests=(running,),
            scorecard=_passing_scorecard(),
        )


def test_deep_validation_scorecard_records_required_checks_and_rejection(tmp_path) -> None:
    lead = _requested_lead(tmp_path, "lead.txt")
    running = start_deep_validation(
        lead=lead,
        existing_manifests=(),
        scorecard=_passing_scorecard(),
    )
    failed_scorecard = _passing_scorecard(feature_ablations=False)
    rejected = complete_deep_validation(running, scorecard=failed_scorecard)

    assert failed_scorecard.passed is False
    assert failed_scorecard.missing_checks == ("feature_ablations",)
    assert rejected.status == DeepValidationStatus.REJECTED
    assert rejected.failure_reason == "deep_validation_scorecard_failed"


def test_pre_2024_fallback_is_diagnostic_only_and_cannot_replace_modern_evidence() -> None:
    unavailable = build_pre_2024_fallback_diagnostic(lead_id="LEAD-1", available=False)
    passed = build_pre_2024_fallback_diagnostic(lead_id="LEAD-1", available=True, passed=True)

    assert unavailable.status == Pre2024FallbackStatus.FAILED_LEAD
    assert unavailable.required_label == "diagnostic_fallback_only"
    assert passed.status == Pre2024FallbackStatus.RETURN_TO_RESEARCH_QUEUE_WITH_WARNING
    payload = passed.model_dump()
    payload["modern_evidence_substituted"] = True
    with pytest.raises(ValidationError, match="cannot substitute"):
        type(passed).model_validate(payload)


def test_final_hard_test_rejects_more_than_three_slots(tmp_path) -> None:
    slots = []
    for index in range(3):
        slots.append(
            allocate_final_hard_test_slot(
                lead=_approved_lead(tmp_path, f"lead-{index}.txt"),
                existing_slots=slots,
                slot_rank=index + 1,
                frozen_strategy_spec_hash=HEX_A,
                frozen_params_hash=HEX_B,
                frozen_data_manifest_hash=HEX_C,
                frozen_universe_snapshot_id=HEX_D,
                frozen_cost_model_hash=HEX_E,
                final_phase_manifest_id=HEX_F,
            )
        )

    with pytest.raises(ValueError, match="more_than_three"):
        allocate_final_hard_test_slot(
            lead=_approved_lead(tmp_path, "lead-4.txt"),
            existing_slots=slots,
            slot_rank=4,
            frozen_strategy_spec_hash=HEX_A,
            frozen_params_hash=HEX_B,
            frozen_data_manifest_hash=HEX_C,
            frozen_universe_snapshot_id=HEX_D,
            frozen_cost_model_hash=HEX_E,
            final_phase_manifest_id=HEX_F,
        )


def test_final_hard_test_requires_frozen_strategy_params_data_universe_and_cost(tmp_path) -> None:
    lead = _approved_lead(tmp_path, "lead.txt")

    with pytest.raises(ValidationError, match="frozen_strategy_spec_hash"):
        allocate_final_hard_test_slot(
            lead=lead,
            existing_slots=(),
            slot_rank=1,
            frozen_strategy_spec_hash="not-a-hash",
            frozen_params_hash=HEX_B,
            frozen_data_manifest_hash=HEX_C,
            frozen_universe_snapshot_id=HEX_D,
            frozen_cost_model_hash=HEX_E,
            final_phase_manifest_id=HEX_F,
        )
    with pytest.raises(ValidationError, match="final_phase_manifest_id"):
        allocate_final_hard_test_slot(
            lead=lead,
            existing_slots=(),
            slot_rank=1,
            frozen_strategy_spec_hash=HEX_A,
            frozen_params_hash=HEX_B,
            frozen_data_manifest_hash=HEX_C,
            frozen_universe_snapshot_id=HEX_D,
            frozen_cost_model_hash=HEX_E,
            final_phase_manifest_id="missing",
        )


def test_parameter_edits_after_lockbox_access_are_forbidden(tmp_path) -> None:
    slot = _slot(tmp_path)

    reject_parameter_edit_after_lockbox(slot, attempted_params_hash=slot.frozen_params_hash)
    with pytest.raises(ValueError, match="parameter_edits_after_lockbox"):
        reject_parameter_edit_after_lockbox(slot, attempted_params_hash=HEX_A)

    payload = slot.model_dump()
    payload["parameter_edits_after_lockbox"] = True
    with pytest.raises(ValidationError, match="parameter edits after lockbox"):
        FinalHardTestSlot.model_validate(payload)


def test_final_survivor_report_has_non_live_disclaimer_and_rejects_implications(tmp_path) -> None:
    slot = _slot(tmp_path)
    report = build_final_survivor_report(
        slot=slot,
        result_summary="survived frozen lockbox review, still research-only",
    )

    assert "not paper/live/trade-ready" in report.non_live_disclaimer
    assert report.paper_live_implication is False
    assert report.trade_readiness_claim is False
    assert report.order_authorization is False
    assert report.sizing_authorization is False
    assert report.runtime_mode_change_authorization is False
    assert report.promotion_ready is False

    payload = report.model_dump()
    payload["paper_live_implication"] = True
    with pytest.raises(ValidationError, match="paper_live_implication"):
        FinalSurvivorReport.model_validate(payload)


def _passing_scorecard(**overrides: bool):
    values = {
        "full_valid_2024_history": True,
        "min_six_months": True,
        "lockbox_excluded": True,
        "asof_universe_snapshot": True,
        "walk_forward_validation": True,
        "negative_controls": True,
        "feature_ablations": True,
        "filter_ablations": True,
        "exit_lab_fixed_hold_comparison": True,
        "cost_stress": True,
        "concentration_checks": True,
        "parameter_neighborhood_stability": True,
        "regime_robustness": True,
        "venue_symbol_robustness": True,
        "diminishing_returns_checked": True,
        "failure_mode_report": True,
    }
    values.update(overrides)
    return DeepValidationScorecard.build(**values)


def _slot(tmp_path: Path):
    return allocate_final_hard_test_slot(
        lead=_approved_lead(tmp_path, "slot-lead.txt"),
        existing_slots=(),
        slot_rank=1,
        frozen_strategy_spec_hash=HEX_A,
        frozen_params_hash=HEX_B,
        frozen_data_manifest_hash=HEX_C,
        frozen_universe_snapshot_id=HEX_D,
        frozen_cost_model_hash=HEX_E,
        final_phase_manifest_id=HEX_F,
    )


def _requested_lead(tmp_path: Path, name: str):
    lead = _lead(tmp_path, name)
    inspected = complete_human_inspection(lead, inspected_by="human-1", notes="reviewed")
    approved = approve_after_human_inspection(inspected, approving_agent_id="agent-1")
    return request_deep_validation(approved)


def _approved_lead(tmp_path: Path, name: str):
    return _requested_lead(tmp_path, name).model_copy(update={"state": LeadState.DEEP_VALIDATION_APPROVED})


def _lead(tmp_path: Path, name: str):
    source = tmp_path / name
    source.write_text("lead source\n", encoding="utf-8")
    return create_lead_from_source(
        source_artifact_path=source,
        source_type="sandbox_run",
        strategy_family="momentum",
        economic_thesis="costed continuation with robust follow-up checklist",
        created_by_id="agent-1",
        instrument_scope=("BTC", "ETH"),
        data_window_start=datetime(2024, 1, 1, tzinfo=UTC),
        data_window_end=datetime(2024, 7, 1, tzinfo=UTC),
        roi_observed=0.12,
        roi_projected=0.08,
        roi_projection_assumptions="not a claim",
        why_interesting="needs final hard-test governance",
        trade_count_summary={"avg_trades_per_month": 6.0, "total_trades": 36},
        monthly_stability_summary={"usable_months": 6, "losing_months_12m": 2},
        pnl_concentration_summary={
            "top_2_trades_profit_share": 0.2,
            "best_month_profit_share": 0.2,
        },
    )
