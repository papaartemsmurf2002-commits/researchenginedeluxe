from __future__ import annotations

import json
from pathlib import Path

from tradingbotsuite.v2.autonomy import (
    AutopilotFixtureCycleConfig,
    load_autopilot_cycle_spec,
    plan_autopilot_research_cycle,
    run_autopilot_cycle_plan,
    write_autopilot_fixture_cycle_spec,
)
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.lead_book import LeadBookStore
from tradingbotsuite.v2.ledger import read_ledger
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobStatus


def test_autopilot_fixture_cycle_executes_real_worker_chain_and_reports_blockers(tmp_path) -> None:
    result = write_autopilot_fixture_cycle_spec(
        AutopilotFixtureCycleConfig(
            output_root=str(tmp_path / "fixture-cycle"),
            run_id="cycle-fixture-pass",
        )
    )
    spec = _read_json(Path(result.cycle_spec_path))

    assert result.declared_job_count == 8
    assert result.declared_binding_count == 10
    assert Path(result.universe_payload_file).exists()
    assert Path(result.candle_records_file).exists()
    assert spec["schema_version"] == "autopilot_bounded_cycle_spec_v1"
    assert spec["run_id"] == "cycle-fixture-pass"
    assert [job["kind"] for job in spec["jobs"]] == [
        "universe_refresh",
        "recent_candle_bootstrap",
        "coverage_audit",
        "strategy_queue_scan",
        "vectorized_backtest",
        "validation_gate",
        "ledger_append_export",
        "lead_book_upsert",
    ]
    serialized_jobs = json.dumps(spec["jobs"], sort_keys=True)
    for unsafe_flag in (
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    ):
        assert f'"{unsafe_flag}": true' not in serialized_jobs
    jobs = {job["kind"]: job for job in spec["jobs"]}
    strategy_queue_spec = jobs["strategy_queue_scan"]["input_spec"]
    backtest_spec = jobs["vectorized_backtest"]["input_spec"]
    assert Path(strategy_queue_spec["strategy_root"]).exists()
    assert strategy_queue_spec["require_single_accepted"] is True
    assert "strategy_spec" not in backtest_spec
    assert "strategy_spec_file" not in backtest_spec

    config = load_autopilot_cycle_spec(result.cycle_spec_path)
    plan = plan_autopilot_research_cycle(
        config,
        output_root=result.suggested_plan_output_root,
        job_store_path=result.suggested_job_store_path,
        enqueue=True,
    )
    execution = run_autopilot_cycle_plan(
        plan.plan_manifest_path,
        worker_id="fixture-cycle-runner",
    )
    manifest = _read_json(Path(execution.execution_manifest_path))
    report = _read_json(Path(plan.audit_report_path))

    assert execution.status.value == "completed_with_blockers"
    assert execution.executed_job_count == 9
    assert execution.skipped_job_count == 0
    assert execution.audit_attempted is True
    assert manifest["accepted_research_ready"] is False
    assert manifest["promotion_ready"] is False
    assert all(job["action"] == "ran" for job in manifest["job_executions"])
    assert all(job["status_after"] == "succeeded" for job in manifest["job_executions"])
    _assert_binding_prefixes(
        _job_execution(manifest, "coverage_audit")["applied_bindings"],
        [
            "input_spec.universe_snapshot_id<=JOB-cycle-fixture-pass-universe:universe_snapshot_id=",
            "input_spec.archive_snapshot_id<=JOB-cycle-fixture-pass-candles:archive_snapshot_id=",
        ],
    )
    _assert_binding_prefixes(
        _job_execution(manifest, "vectorized_backtest")["applied_bindings"],
        [
            "input_spec.universe_snapshot_id<=JOB-cycle-fixture-pass-universe:universe_snapshot_id=",
            "input_spec.archive_snapshot_id<=JOB-cycle-fixture-pass-candles:archive_snapshot_id=",
            "input_spec.strategy_spec_file<=JOB-cycle-fixture-pass-strategy-queue:accepted_spec_path=",
            "input_spec.strategy_spec_file_sha256<=JOB-cycle-fixture-pass-strategy-queue:accepted_spec_sha256=",
        ],
    )
    assert _job_execution(manifest, "ledger_append_export")["applied_bindings"][0].startswith(
        "input_spec.run_manifest_path<=JOB-cycle-fixture-pass-backtest:run_manifest_path="
    )
    assert _job_execution(manifest, "ledger_append_export")["applied_bindings"][1].startswith(
        "input_spec.validation_manifest_path<=JOB-cycle-fixture-pass-validation:validation_manifest_path="
    )
    assert _job_execution(manifest, "validation_gate")["applied_bindings"][0].startswith(
        "input_spec.run_manifest_path<=JOB-cycle-fixture-pass-backtest:run_manifest_path="
    )
    assert _job_execution(manifest, "lead_book_upsert")["applied_bindings"][0].startswith(
        "input_spec.source_artifact_path<=JOB-cycle-fixture-pass-ledger:ledger_path="
    )

    store = WorkerJobStore(result.suggested_job_store_path)
    assert all(job.status == WorkerJobStatus.SUCCEEDED for job in store.list_jobs())
    coverage_job = store.load_job("JOB-cycle-fixture-pass-coverage")
    strategy_queue_job = store.load_job("JOB-cycle-fixture-pass-strategy-queue")
    backtest_job = store.load_job("JOB-cycle-fixture-pass-backtest")
    validation_job = store.load_job("JOB-cycle-fixture-pass-validation")
    lead_job = store.load_job("JOB-cycle-fixture-pass-lead")
    assert coverage_job is not None
    assert strategy_queue_job is not None
    assert backtest_job is not None
    assert validation_job is not None
    assert lead_job is not None
    assert "blocker_reasons=sandbox_diagnostic_non_evidence" in coverage_job.output_refs
    assert "accepted_count=1" in strategy_queue_job.output_refs
    assert any(ref.startswith("accepted_spec_path=") for ref in strategy_queue_job.output_refs)
    assert any(ref.startswith("accepted_spec_sha256=") for ref in strategy_queue_job.output_refs)
    assert "strategy_spec_source=file" in backtest_job.output_refs
    assert any(ref.startswith("strategy_spec_file_sha256=") for ref in backtest_job.output_refs)
    assert any(ref.startswith("validation_manifest_path=") for ref in validation_job.output_refs)
    assert any(ref.startswith("validation_manifest_id=") for ref in validation_job.archive_manifest_refs)
    assert any(ref.startswith("known_blockers=fixture_cycle_non_evidence") for ref in lead_job.output_refs)
    assert any(ref.startswith("missing_evidence=real_hyperliquid_archive_operation") for ref in lead_job.output_refs)

    expected_blockers = set(result.expected_audit_blockers)
    assert report["status"] == "completed_with_blockers"
    assert report["accepted_research_ready"] is False
    assert expected_blockers.issubset(set(report["blocker_reasons"]))
    assert "minimum_five_trades_per_month_failed" in report["blocker_reasons"]
    assert set(execution.blocker_reasons) == set(report["blocker_reasons"])

    ledger_rows = read_ledger(Path(result.ledger_path))
    assert len(ledger_rows) == 1
    assert ledger_rows[0].evidence_mode == "sandbox_diagnostic"
    assert ledger_rows[0].promotion_ready is False
    assert ledger_rows[0].candidate_evidence is False
    assert ledger_rows[0].row_status == "succeeded"

    leads = LeadBookStore(result.lead_book_path).read()
    assert len(leads) == 1
    lead = leads[0]
    assert lead.promotion_ready is False
    assert lead.candidate_evidence is False
    assert "fixture_cycle_non_evidence" in lead.known_blockers
    assert "minimum_five_trades_per_month_failed" in lead.known_blockers
    assert "real_hyperliquid_archive_operation" in lead.missing_evidence
    assert lead.source_artifact_path == str(Path(result.ledger_path).resolve())


def test_autopilot_fixture_cycle_cli_writes_spec_paths(tmp_path, capsys) -> None:
    exit_code = main(
        [
            "autopilot",
            "fixture-cycle-spec",
            "--output-root",
            str(tmp_path / "cli-fixture-cycle"),
            "--run-id",
            "cycle-fixture-cli",
        ]
    )
    output = capsys.readouterr().out
    lines = output.strip().splitlines()
    values = dict(
        line.split("=", 1)
        for line in lines
        if "=" in line and not line.startswith("expected_audit_blocker=")
    )
    blockers = [
        line.split("=", 1)[1]
        for line in lines
        if line.startswith("expected_audit_blocker=")
    ]

    assert exit_code == 0
    assert values["evidence_mode"] == "sandbox_diagnostic"
    assert values["accepted_research_ready"] == "false"
    assert values["promotion_ready"] == "false"
    assert values["declared_job_count"] == "8"
    assert values["declared_binding_count"] == "10"
    assert Path(values["cycle_spec"]).exists()
    assert Path(values["universe_payload_file"]).exists()
    assert Path(values["candle_records_file"]).exists()
    assert "sandbox_diagnostic_non_evidence" in blockers
    assert "fixture_cycle_non_evidence" in blockers


def _job_execution(manifest: dict, kind: str) -> dict:
    for execution in manifest["job_executions"]:
        if execution["kind"] == kind:
            return execution
    raise AssertionError(f"missing job execution for kind: {kind}")


def _assert_binding_prefixes(bindings: list[str], prefixes: list[str]) -> None:
    assert len(bindings) == len(prefixes)
    for binding, prefix in zip(bindings, prefixes, strict=True):
        assert binding.startswith(prefix)
        assert len(binding) > len(prefix)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
