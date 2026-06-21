from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.autonomy import (
    AutonomyDryRunConfig,
    AutonomyLoopStatus,
    run_autonomy_dry_run,
)
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.lead_book import LeadBookStore
from tradingbotsuite.v2.ledger import read_ledger


FORBIDDEN_TRUE_FLAGS = {
    "promotion_ready",
    "candidate_evidence",
    "candidate_pack_eligible",
    "live_signal",
    "paper_signal",
    "sizing_instruction",
    "order_placement_instruction",
    "runtime_mode_change",
}


def test_autonomy_dry_run_writes_research_loop_artifacts(tmp_path) -> None:
    result = run_autonomy_dry_run(
        AutonomyDryRunConfig(output_root=str(tmp_path), run_id="loop-smoke")
    )

    manifest = _read_json(Path(result.manifest_path))
    blocker_report = _read_json(Path(result.blocker_report_path))
    run_manifest = _read_json(Path(result.backtest_run_dir) / "run_manifest.json")
    ledger_rows = read_ledger(result.ledger_path)
    lead_rows = LeadBookStore(result.lead_book_path).read()

    assert result.status == AutonomyLoopStatus.COMPLETED_WITH_BLOCKERS
    assert Path(result.manifest_path).exists()
    assert Path(result.blocker_report_path).exists()
    assert Path(result.ledger_path).exists()
    assert Path(result.lead_book_path).exists()
    assert {step["name"] for step in manifest["steps"]} == {
        "universe_fixture",
        "archive_fixture",
        "coverage_fixture",
        "strategy_spec_validation",
        "backtest_data_preflight",
        "backtest",
        "ledger_append",
        "lead_book_update",
        "blocker_report",
    }
    assert manifest["artifact_paths"]["archive_root"].endswith("archive")
    assert Path(manifest["artifact_paths"]["archive_fixture"]).exists()
    assert Path(manifest["artifact_paths"]["coverage_fixture"]).exists()
    assert Path(manifest["artifact_paths"]["universe_fixture"]).exists()
    assert Path(manifest["artifact_paths"]["backtest_data_manifest"]).exists()
    assert manifest["evidence_mode"] == "sandbox_diagnostic"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert all(manifest[flag] is False for flag in FORBIDDEN_TRUE_FLAGS)
    assert blocker_report["accepted_research_ready"] is False
    assert "fixture_dry_run_non_evidence" in blocker_report["blocker_reasons"]
    assert "real_hyperliquid_archive_operation_required" in blocker_report["blocker_reasons"]

    assert run_manifest["status"] == "succeeded"
    assert run_manifest["validation_status"] == "pass"
    assert run_manifest["usable_months"] >= 6
    assert run_manifest["data_coverage_min"] == 0.98
    assert run_manifest["universe_mode"] == "as_of"
    assert "metrics" in run_manifest["artifacts"]
    assert "cost_stress" in run_manifest["artifacts"]
    assert all(run_manifest[flag] is False for flag in FORBIDDEN_TRUE_FLAGS)

    assert len(ledger_rows) == 1
    assert ledger_rows[0].run_id == manifest["backtest_run_id"]
    assert ledger_rows[0].evidence_mode == "sandbox_diagnostic"
    assert ledger_rows[0].universe_mode == "as_of"
    assert ledger_rows[0].usable_months >= 6
    assert ledger_rows[0].data_coverage_min == 0.98
    assert ledger_rows[0].promotion_ready is False

    assert len(lead_rows) == 1
    assert lead_rows[0].source_type == "autonomy_dry_run"
    assert lead_rows[0].promotion_ready is False
    assert lead_rows[0].candidate_evidence is False
    assert "lead_not_candidate" in lead_rows[0].non_promotable_flags
    assert "fixture_dry_run_non_evidence" in lead_rows[0].known_blockers
    assert "real_hyperliquid_archive_operation_required" in lead_rows[0].known_blockers


def test_autonomy_cli_dry_run_prints_artifact_paths(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "autonomy",
            "dry-run",
            "--output-root",
            str(tmp_path),
            "--run-id",
            "cli-loop",
        ]
    )
    output = capsys.readouterr().out
    values = dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)

    assert exit_code == 0
    assert values["status"] == "completed_with_blockers"
    assert values["evidence_mode"] == "sandbox_diagnostic"
    assert values["promotion_ready"] == "false"
    assert Path(values["autonomy_manifest"]).exists()
    assert Path(values["blocker_report"]).exists()
    assert Path(values["ledger_path"]).exists()
    assert Path(values["lead_book_path"]).exists()
    assert Path(values["backtest_run_dir"]).exists()


def test_autonomy_cli_rejects_unsafe_run_id(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "autonomy",
            "dry-run",
            "--output-root",
            str(tmp_path),
            "--run-id",
            "..\\bad",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "autonomy_dry_run_rejected=" in output


def test_autonomy_manifest_fixture_mode_remains_available(tmp_path) -> None:
    result = run_autonomy_dry_run(
        AutonomyDryRunConfig(
            output_root=str(tmp_path),
            run_id="manifest-fixture-loop",
            data_mode="manifest_fixture",
        )
    )
    manifest = _read_json(Path(result.manifest_path))
    step_names = {step["name"] for step in manifest["steps"]}

    assert result.status == AutonomyLoopStatus.COMPLETED_WITH_BLOCKERS
    assert "archive_fixture" in step_names
    assert "backtest_data_preflight" not in step_names
    assert Path(manifest["artifact_paths"]["archive_fixture"]).suffix == ".json"


def test_autonomy_dry_run_rejects_accepted_research_mode(tmp_path) -> None:
    with pytest.raises(ValidationError, match="sandbox_diagnostic"):
        AutonomyDryRunConfig(
            output_root=str(tmp_path),
            run_id="bad-evidence-mode",
            evidence_mode="accepted_research",
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
