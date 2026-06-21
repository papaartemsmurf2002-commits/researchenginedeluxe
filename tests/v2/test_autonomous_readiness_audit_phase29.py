from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tradingbotsuite.v2.audit import (
    AuditBlockerReport,
    AuditReportStatus,
    AutonomousReadinessEvidence,
    AutonomousReadinessStatus,
    ReadinessEvidenceItem,
    REQUIRED_AUTONOMOUS_READINESS_KEYS,
    run_autonomous_readiness_audit,
)
from tradingbotsuite.v2.audit.readiness import REQUIRED_CYCLE_JOB_KINDS
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.ledger import LedgerAppendRequest, append_run_to_ledger
from tradingbotsuite.v2.lead_book import LeadBookStore, create_lead_from_source

HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


def test_autonomous_readiness_audit_blocks_missing_current_evidence(tmp_path) -> None:
    evidence = AutonomousReadinessEvidence(
        run_id="current-incomplete",
        evidence_items=(
            ReadinessEvidenceItem(
                key="repo.clean_git_tree",
                passed=True,
                evidence_ref="git status --short empty",
            ),
        ),
        known_p1_open=1,
    )

    report = run_autonomous_readiness_audit(
        evidence,
        output_path=tmp_path / "readiness_report.json",
    )

    assert report.status == AutonomousReadinessStatus.BLOCKED
    assert report.autonomous_research_ready is False
    assert "missing_evidence:validation.python_3_11_pinned" in report.blocker_reasons
    assert "missing_artifact:cycle_execution_manifest" in report.blocker_reasons
    assert "missing_artifact:ledger" in report.blocker_reasons
    assert "known_p1_open:1" in report.blocker_reasons
    assert report.promotion_ready is False


def test_autonomous_readiness_blocks_fixture_cycle_blockers(tmp_path) -> None:
    ledger_path = _write_ledger(tmp_path)
    lead_book_path = _write_lead_book(tmp_path, source_artifact_path=ledger_path)
    cycle_path = _write_cycle_execution(
        tmp_path,
        status="completed_with_blockers",
        blockers=("sandbox_diagnostic_non_evidence",),
    )
    audit_report_path = _write_audit_report(
        tmp_path,
        status=AuditReportStatus.COMPLETED_WITH_BLOCKERS,
        blockers=("sandbox_diagnostic_non_evidence",),
    )
    evidence = _complete_evidence(
        run_id="synthetic-fixture-blocked",
        cycle_path=cycle_path,
        audit_report_path=audit_report_path,
        ledger_path=ledger_path,
        lead_book_path=lead_book_path,
    )

    report = run_autonomous_readiness_audit(
        evidence,
        output_path=tmp_path / "blocked_readiness_report.json",
    )

    assert report.status == AutonomousReadinessStatus.BLOCKED
    assert report.autonomous_research_ready is False
    assert "cycle_execution_not_completed:completed_with_blockers" in report.blocker_reasons
    assert "cycle_execution_blocker:sandbox_diagnostic_non_evidence" in report.blocker_reasons
    assert "final_audit_not_pass:completed_with_blockers" in report.blocker_reasons
    assert "final_audit_blocker:sandbox_diagnostic_non_evidence" in report.blocker_reasons
    assert report.promotion_ready is False


def test_synthetic_complete_evidence_can_pass_gate_without_promotion_claims(tmp_path) -> None:
    ledger_path = _write_ledger(tmp_path)
    lead_book_path = _write_lead_book(tmp_path, source_artifact_path=ledger_path)
    cycle_path = _write_cycle_execution(tmp_path)
    audit_report_path = _write_audit_report(tmp_path)
    evidence = _complete_evidence(
        run_id="synthetic-complete",
        cycle_path=cycle_path,
        audit_report_path=audit_report_path,
        ledger_path=ledger_path,
        lead_book_path=lead_book_path,
    )

    report_path = tmp_path / "pass_readiness_report.json"
    report = run_autonomous_readiness_audit(evidence, output_path=report_path)
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert report.status == AutonomousReadinessStatus.AUTONOMOUS_RESEARCH_READY
    assert report.autonomous_research_ready is True
    assert report.blocker_count == 0
    assert report.passed_check_count == len(REQUIRED_AUTONOMOUS_READINESS_KEYS)
    assert payload["promotion_ready"] is False
    assert payload["live_signal"] is False
    assert payload["order_placement_instruction"] is False
    assert payload["sizing_instruction"] is False


def test_autonomous_readiness_cli_writes_blocker_report(tmp_path, capsys) -> None:
    evidence_path = tmp_path / "incomplete_evidence.json"
    output_path = tmp_path / "cli_readiness_report.json"
    evidence_path.write_text(
        AutonomousReadinessEvidence(run_id="cli-incomplete").model_dump_json(indent=2),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "audit",
            "autonomous-readiness",
            "--evidence-file",
            str(evidence_path),
            "--output-path",
            str(output_path),
        ]
    )
    output = capsys.readouterr().out
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert output_path.exists()
    assert "status=blocked" in output
    assert "blocker=missing_evidence:repo.clean_git_tree" in output
    assert "promotion_ready=false" in output
    assert report["autonomous_research_ready"] is False
    assert report["promotion_ready"] is False


def test_autonomous_readiness_rejects_secret_like_report_paths(tmp_path) -> None:
    evidence = AutonomousReadinessEvidence(run_id="path-rejection")

    with pytest.raises(ValueError, match="secret-like"):
        run_autonomous_readiness_audit(
            evidence,
            output_path=tmp_path / "token_readiness_report.json",
        )


def _complete_evidence(
    *,
    run_id: str,
    cycle_path: Path,
    audit_report_path: Path,
    ledger_path: Path,
    lead_book_path: Path,
) -> AutonomousReadinessEvidence:
    return AutonomousReadinessEvidence(
        run_id=run_id,
        evidence_items=tuple(
            ReadinessEvidenceItem(
                key=key,
                passed=True,
                evidence_ref=f"synthetic_evidence:{key}",
            )
            for key in REQUIRED_AUTONOMOUS_READINESS_KEYS
        ),
        cycle_execution_manifest_path=str(cycle_path),
        final_audit_report_path=str(audit_report_path),
        ledger_path=str(ledger_path),
        lead_book_path=str(lead_book_path),
    )


def _write_cycle_execution(
    root: Path,
    *,
    status: str = "completed",
    blockers: tuple[str, ...] = (),
) -> Path:
    path = root / f"{status}_cycle_execution.json"
    payload = {
        "schema_version": "autopilot_cycle_execution_manifest_v1",
        "execution_id": f"execution-{status}",
        "status": status,
        "audit_attempted": True,
        "blocker_reasons": list(blockers),
        "job_executions": [
            {
                "job_id": f"JOB-{kind}",
                "kind": kind,
                "action": "ran",
                "status_after": "succeeded",
            }
            for kind in REQUIRED_CYCLE_JOB_KINDS
        ],
        "accepted_research_ready": False,
        "promotion_ready": False,
    }
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return path


def _write_audit_report(
    root: Path,
    *,
    status: AuditReportStatus = AuditReportStatus.PASS,
    blockers: tuple[str, ...] = (),
) -> Path:
    path = root / f"{status.value}_audit_report.json"
    report = AuditBlockerReport(
        report_id=("d" if status == AuditReportStatus.PASS else "e") * 64,
        run_id=f"audit-{status.value}",
        created_at=datetime(2024, 8, 1, tzinfo=UTC),
        status=status,
        accepted_research_ready=False,
        job_store_path=str(root / "jobs.sqlite"),
        audited_job_ids=tuple(f"JOB-{kind}" for kind in REQUIRED_CYCLE_JOB_KINDS),
        job_status_counts={"succeeded": len(REQUIRED_CYCLE_JOB_KINDS)},
        blocker_reasons=blockers,
        required_next_actions=()
        if not blockers
        else ("provide_real_hyperliquid_archive_operation_evidence",),
        required_successful_job_kinds=REQUIRED_CYCLE_JOB_KINDS,
        required_job_kind_order=REQUIRED_CYCLE_JOB_KINDS,
        artifact_refs=("synthetic_loop_artifact_refs_complete=true",),
    )
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def _write_ledger(root: Path) -> Path:
    manifest_path = _write_run_manifest(root, "readiness-ledger-run")
    ledger_path = root / "ledger.parquet"
    append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(manifest_path),
            ledger_path=str(ledger_path),
            evidence_mode="accepted_research",
        )
    )
    return ledger_path


def _write_lead_book(root: Path, *, source_artifact_path: Path) -> Path:
    lead_book_path = root / "lead_book.parquet"
    lead = create_lead_from_source(
        source_artifact_path=source_artifact_path,
        source_type="synthetic_readiness_test",
        strategy_family="momentum",
        economic_thesis="synthetic gate fixture, not a production claim",
        created_by_id="readiness-test-agent",
        instrument_scope=("hyperliquid:perp:BTC", "hyperliquid:perp:ETH"),
        data_window_start=datetime(2024, 1, 1, tzinfo=UTC),
        data_window_end=datetime(2024, 8, 1, tzinfo=UTC),
        roi_observed=0.08,
        roi_projected=0.04,
        roi_projection_assumptions="synthetic test assumption, not a claim",
        why_interesting="synthetic complete artifact for readiness-gate regression",
        trade_count_summary={"avg_trades_per_month": 6.0, "total_trades": 42},
        monthly_stability_summary={
            "usable_months": 7,
            "losing_months_12m": 1,
            "positive_months_12m": 6,
        },
        pnl_concentration_summary={
            "top_2_trades_profit_share": 0.2,
            "best_month_profit_share": 0.2,
        },
    )
    LeadBookStore(lead_book_path).upsert(lead)
    return lead_book_path


def _write_run_manifest(root: Path, run_id: str) -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "run_manifest_v1",
        "run_id": run_id,
        "experiment_id": "readiness-test",
        "trial_index": 0,
        "agent_or_user": "agent",
        "created_at": "2024-08-01T00:00:00Z",
        "status": "succeeded",
        "engine_lane": "vectorized",
        "strategy_lane": "declarative",
        "git_sha": "test-git-sha",
        "environment_hash": HEX_A,
        "strategy_id": "readiness_test_strategy",
        "strategy_version": "0.1.0",
        "strategy_hash": HEX_B,
        "strategy_spec_hash": HEX_B,
        "params_hash": HEX_C,
        "archive_snapshot_id": "archive-snapshot",
        "universe_snapshot_id": "universe-snapshot",
        "data_manifest_id": "data-manifest",
        "data_manifest_hash": HEX_A,
        "validation_manifest_hash": HEX_B,
        "cost_manifest_hash": HEX_C,
        "universe_mode": "as_of",
        "venue_scope": "hyperliquid",
        "instrument_count": 2,
        "timeframe": "1h",
        "backtest_start": "2024-01-01T00:00:00Z",
        "backtest_end": "2024-08-01T00:00:00Z",
        "usable_months": 7,
        "lockbox_policy_id": "dynamic_full_calendar_months_v1",
        "lockbox_start": None,
        "lockbox_end": None,
        "data_coverage_min": 0.98,
        "cost_model_id": "conservative_hyperliquid_taker_v1",
        "cost_model_hash": HEX_A,
        "validation_policy_id": "validation-v1",
        "validation_status": "pass",
        "missing_data_policy": "fail_closed",
        "price_basis": "next_bar_open",
        "failure_reason": None,
        "metrics": {
            "schema_version": "v2",
            "run_id": run_id,
            "status": "succeeded",
            "gross_return": 0.1,
            "net_return": 0.08,
            "gross_equity_final": 1.1,
            "net_equity_final": 1.08,
            "total_fee_cost": 0.01,
            "total_spread_cost": 0.002,
            "total_slippage_cost": 0.003,
            "total_impact_cost": 0.001,
            "total_transaction_cost": 0.016,
            "total_funding_pnl": 0.0,
            "total_turnover": 2.0,
            "trade_count": 6,
            "position_row_count": 12,
            "capacity_blocked_count": 0,
            "gross_only": False,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        },
        "artifacts": {
            name: {"name": name, "path": path, "sha256": HEX_A, "required": True}
            for name, path in _artifact_paths().items()
        },
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
    }
    path = run_dir / "run_manifest.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return path


def _artifact_paths() -> dict[str, str]:
    return {
        "strategy_spec": "strategy_spec.json",
        "params": "params.json",
        "data_manifest": "data_manifest.json",
        "validation_manifest": "validation_manifest.json",
        "cost_manifest": "cost_manifest.json",
        "cost_stress": "cost_stress.parquet",
        "metrics": "metrics.json",
        "equity_curve": "equity_curve.parquet",
        "daily_returns": "daily_returns.parquet",
        "trades": "trades.parquet",
        "positions": "positions.parquet",
        "per_instrument_metrics": "per_instrument_metrics.parquet",
        "fold_metrics": "fold_metrics.parquet",
        "log": "logs/log.txt",
    }
