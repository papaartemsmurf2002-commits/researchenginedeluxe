from __future__ import annotations

import json

from tradingbotsuite.promotion.artifact_validator import validate_artifact_for_live_input
from tradingbotsuite.promotion.stage13_readiness import (
    PAPER_RUN_MANIFEST_VERSION,
    SHADOW_RUN_ARCHIVE_MANIFEST_VERSION,
    STAGE13_READINESS_REPORT_VERSION,
    TESTNET_VALIDATION_MANIFEST_VERSION,
    build_stage13_readiness_report,
    summarize_shadow_archive,
    validate_asset_scope_for_requested_symbol,
    validate_stage12_oos_stress_evidence,
    verify_execution_journal_evidence,
    write_stage13_readiness_plan,
)


def _valid_stage12_oos_stress_evidence() -> dict[str, object]:
    return {
        "out_of_sample": True,
        "evidence_scope": "walk_forward_oos",
        "stress_evidence": True,
        "real_market_archive": True,
        "event_rows_by_asset": {"BTCUSDT": 12_000},
        "uses_regime_model": True,
        "regime_rows": {"low_vol": 1_500, "high_vol": 1_300},
        "labeled_trades_by_side": {"long": 350, "short": 340},
        "accepted_trades_by_validation_split": {
            "split_1": 55,
            "split_2": 60,
            "split_3": 58,
            "split_4": 62,
            "split_5": 57,
            "split_6": 59,
        },
        "volatility_regimes": ["low", "high"],
        "stress_periods": ["2024-08-05"],
        "costed_expectancy_after_fees_slippage_funding": 0.02,
        "max_split_pnl_share": 0.32,
        "side_outcomes": {"long": {"expectancy": 0.01}, "short": {"expectancy": 0.015}},
        "slippage_stress_passed": True,
        "funding_stress_passed": True,
        "feature_missingness_max_rate": 0.05,
        "feature_missingness_threshold": 0.10,
        "wt3d_claimed": True,
        "wt3d_ablation_passed": True,
    }


def test_plan_stage13_readiness_writes_blocked_templates_only(tmp_path) -> None:
    result = write_stage13_readiness_plan(tmp_path / "stage13" / "readiness")

    paper = json.loads(result.paper_manifest_template_path.read_text(encoding="utf-8"))
    shadow = json.loads(result.shadow_archive_manifest_template_path.read_text(encoding="utf-8"))
    testnet = json.loads(result.testnet_validation_manifest_template_path.read_text(encoding="utf-8"))
    report = json.loads(result.readiness_report_path.read_text(encoding="utf-8"))

    assert paper["manifest_version"] == PAPER_RUN_MANIFEST_VERSION
    assert shadow["manifest_version"] == SHADOW_RUN_ARCHIVE_MANIFEST_VERSION
    assert testnet["manifest_version"] == TESTNET_VALIDATION_MANIFEST_VERSION
    assert report["manifest_version"] == STAGE13_READINESS_REPORT_VERSION
    assert report["ready"] is False
    assert report["blocked"] is True
    assert report["live_canary_authorized"] is False
    assert report["operator_control_input"] is False
    assert report["live_execution_input"] is False
    assert result.rollback_runbook_checklist_path.exists()


def test_stage12_evidence_validator_accepts_only_oos_stress_evidence() -> None:
    accepted = validate_stage12_oos_stress_evidence(_valid_stage12_oos_stress_evidence())
    assert accepted["passed"] is True

    rejected_payload = _valid_stage12_oos_stress_evidence()
    rejected_payload["out_of_sample"] = False
    rejected_payload["evidence_scope"] = "in_sample"
    rejected_payload["in_sample_only"] = True
    rejected_payload["stress_evidence"] = False
    rejected_payload["stress_periods"] = []
    rejected = validate_stage12_oos_stress_evidence(rejected_payload)
    assert rejected["passed"] is False
    assert "out_of_sample_evidence_required" in rejected["reasons"]
    assert "stress_evidence_required" in rejected["reasons"]
    assert "in_sample_only_evidence_rejected" in rejected["reasons"]


def test_btc_only_artifacts_reject_eth_requested_symbol() -> None:
    result = validate_asset_scope_for_requested_symbol({"asset_scope": ["BTCUSDT"]}, "ETHUSDT")

    assert not result.passed
    assert "btc_only_artifact_rejected_for_eth" in result.reasons


def test_execution_journal_verifier_detects_missing_reconciliation_and_dead_man() -> None:
    result = verify_execution_journal_evidence({"event_types": ["deterministic_cloid", "order_intent"]})

    assert not result.passed
    assert "missing_execution_journal_evidence:reconciliation" in result.reasons
    assert "missing_execution_journal_evidence:schedule_cancel_set" in result.reasons


def test_stage13_readiness_stays_blocked_without_archives_and_approval() -> None:
    report = build_stage13_readiness_report()

    assert report.ready is False
    assert report.blocked is True
    assert report.live_canary_authorized is False
    assert any(reason.startswith("human_approval:") for reason in report.blockers)
    assert any(reason.startswith("paper_run_manifest:") for reason in report.blockers)


def test_shadow_summary_and_stage13_taxonomy_are_research_only_live_rejected(tmp_path) -> None:
    result = write_stage13_readiness_plan(tmp_path / "readiness")
    paper = json.loads(result.paper_manifest_template_path.read_text(encoding="utf-8"))
    live_validation = validate_artifact_for_live_input(paper)
    assert not live_validation.allowed
    assert "research_only_artifact_rejected_for_live_input" in live_validation.reasons
    assert "observe_only_artifact_rejected_for_live_input" in live_validation.reasons

    shadow = json.loads(result.shadow_archive_manifest_template_path.read_text(encoding="utf-8"))
    summary = summarize_shadow_archive(shadow)
    assert summary["operator_control_input"] is False
    assert summary["live_execution_input"] is False
    assert summary["promotion_ready"] is False
