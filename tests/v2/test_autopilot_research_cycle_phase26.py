from __future__ import annotations

import json
from pathlib import Path

from tradingbotsuite.v2.autonomy import (
    AutopilotCyclePlanConfig,
    AutopilotCyclePlanError,
    AutopilotCyclePlanStatus,
    plan_autopilot_research_cycle,
)
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job


def test_bounded_research_cycle_plan_writes_manifest_without_enqueue(tmp_path) -> None:
    config = AutopilotCyclePlanConfig.model_validate(_cycle_spec())
    job_store_path = tmp_path / "jobs.sqlite"

    result = plan_autopilot_research_cycle(
        config,
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=False,
    )
    manifest = _read_json(Path(result.plan_manifest_path))

    assert result.status == AutopilotCyclePlanStatus.PLANNED
    assert result.enqueued_job_count == 0
    assert not job_store_path.exists()
    assert manifest["schema_version"] == "autopilot_bounded_cycle_plan_v1"
    assert manifest["status"] == "planned"
    assert manifest["accepted_research_ready"] is False
    assert manifest["research_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["planned_jobs"][-1]["kind"] == "audit_check"
    assert manifest["planned_jobs"][-1]["generated_by_planner"] is True
    assert manifest["required_job_kind_order"] == [
        "universe_refresh",
        "recent_candle_bootstrap",
        "coverage_audit",
        "vectorized_backtest",
        "ledger_append_export",
        "lead_book_upsert",
    ]
    assert manifest["required_artifact_ref_prefixes"] == [
        "universe_snapshot_id=",
        "archive_snapshot_id=",
        "coverage_report_id",
        "run_manifest_path=",
        "ledger_path=",
        "lead_book_path=",
    ]


def test_bounded_research_cycle_enqueue_adds_jobs_and_generated_audit(tmp_path) -> None:
    config = AutopilotCyclePlanConfig.model_validate(_cycle_spec(run_id="cycle-enqueue"))
    job_store_path = tmp_path / "jobs.sqlite"

    result = plan_autopilot_research_cycle(
        config,
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    store = WorkerJobStore(job_store_path)
    jobs = store.list_jobs()
    audit = store.load_job(result.audit_job_id)

    assert result.status == AutopilotCyclePlanStatus.ENQUEUED
    assert result.enqueued_job_count == 7
    assert [job.kind for job in jobs] == [
        WorkerJobKind.UNIVERSE_REFRESH,
        WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        WorkerJobKind.COVERAGE_AUDIT,
        WorkerJobKind.VECTORIZED_BACKTEST,
        WorkerJobKind.LEDGER_APPEND_EXPORT,
        WorkerJobKind.LEAD_BOOK_UPSERT,
        WorkerJobKind.AUDIT_CHECK,
    ]
    assert all(job.status == WorkerJobStatus.QUEUED for job in jobs)
    assert audit is not None
    assert audit.input_spec["target_job_ids"] == [
        "JOB-cycle-enqueue-universe",
        "JOB-cycle-enqueue-candles",
        "JOB-cycle-enqueue-coverage",
        "JOB-cycle-enqueue-backtest",
        "JOB-cycle-enqueue-ledger",
        "JOB-cycle-enqueue-lead",
    ]
    assert audit.input_spec["required_successful_job_kinds"] == [
        "universe_refresh",
        "recent_candle_bootstrap",
        "coverage_audit",
        "vectorized_backtest",
        "ledger_append_export",
        "lead_book_upsert",
    ]
    assert audit.input_spec["required_job_kind_order"] == audit.input_spec["required_successful_job_kinds"]

    audit_result = run_one_job(
        store=store,
        kind=WorkerJobKind.AUDIT_CHECK,
        worker_id="worker-cycle-audit",
    )
    report = _read_json(Path(result.audit_report_path))

    assert audit_result is not None
    assert audit_result.status == WorkerJobStatus.SUCCEEDED
    assert report["accepted_research_ready"] is False
    assert "job_incomplete:JOB-cycle-enqueue-universe:queued" in report["blocker_reasons"]
    assert "missing_evidence:successful_job_kind:universe_refresh" in report["blocker_reasons"]


def test_bounded_research_cycle_plan_persists_declared_bindings(tmp_path) -> None:
    payload = _cycle_spec(run_id="cycle-bind-plan")
    payload["bindings"] = [
        {
            "source_job_id": "JOB-cycle-bind-plan-universe",
            "target_job_id": "JOB-cycle-bind-plan-candles",
            "target_input_path": "instrument_id",
            "source_ref_prefix": "instrument_id=",
        }
    ]
    config = AutopilotCyclePlanConfig.model_validate(payload)

    result = plan_autopilot_research_cycle(
        config,
        output_root=tmp_path / "plans",
        job_store_path=tmp_path / "jobs.sqlite",
        enqueue=False,
    )
    manifest = _read_json(Path(result.plan_manifest_path))

    assert manifest["bindings"] == payload["bindings"]


def test_bounded_research_cycle_rejects_out_of_order_binding(tmp_path) -> None:
    payload = _cycle_spec(run_id="cycle-bad-binding")
    payload["bindings"] = [
        {
            "source_job_id": "JOB-cycle-bad-binding-backtest",
            "target_job_id": "JOB-cycle-bad-binding-coverage",
            "target_input_path": "archive_snapshot_id",
            "source_ref_prefix": "archive_snapshot_id=",
        }
    ]
    config = AutopilotCyclePlanConfig.model_validate(payload)

    try:
        plan_autopilot_research_cycle(
            config,
            output_root=tmp_path / "plans",
            job_store_path=tmp_path / "jobs.sqlite",
            enqueue=False,
        )
    except AutopilotCyclePlanError as exc:
        assert "source job must precede target job" in str(exc)
    else:
        raise AssertionError("expected out-of-order binding rejection")


def test_bounded_research_cycle_rejects_boundary_binding_target(tmp_path) -> None:
    payload = _cycle_spec(run_id="cycle-bad-binding-boundary")
    payload["bindings"] = [
        {
            "source_job_id": "JOB-cycle-bad-binding-boundary-universe",
            "target_job_id": "JOB-cycle-bad-binding-boundary-candles",
            "target_input_path": "promotion_ready",
            "source_ref_prefix": "instrument_id=",
        }
    ]
    config = AutopilotCyclePlanConfig.model_validate(payload)

    try:
        plan_autopilot_research_cycle(
            config,
            output_root=tmp_path / "plans",
            job_store_path=tmp_path / "jobs.sqlite",
            enqueue=False,
        )
    except AutopilotCyclePlanError as exc:
        assert "boundary override" in str(exc)
    else:
        raise AssertionError("expected boundary binding target rejection")


def test_bounded_research_cycle_rejects_boundary_override_before_enqueue(tmp_path) -> None:
    payload = _cycle_spec(run_id="cycle-bad-boundary")
    payload["jobs"][0]["input_spec"]["promotion_ready"] = True
    config = AutopilotCyclePlanConfig.model_validate(payload)
    job_store_path = tmp_path / "jobs.sqlite"

    try:
        plan_autopilot_research_cycle(
            config,
            output_root=tmp_path / "plans",
            job_store_path=job_store_path,
            enqueue=True,
        )
    except AutopilotCyclePlanError as exc:
        assert "boundary override" in str(exc)
    else:
        raise AssertionError("expected boundary override rejection")

    assert not job_store_path.exists()


def test_bounded_research_cycle_rejects_missing_required_stage(tmp_path) -> None:
    payload = _cycle_spec(run_id="cycle-missing-stage")
    payload["jobs"] = [job for job in payload["jobs"] if job["kind"] != "lead_book_upsert"]
    config = AutopilotCyclePlanConfig.model_validate(payload)

    try:
        plan_autopilot_research_cycle(
            config,
            output_root=tmp_path / "plans",
            job_store_path=tmp_path / "jobs.sqlite",
            enqueue=False,
        )
    except AutopilotCyclePlanError as exc:
        assert "lead_book_upsert" in str(exc)
    else:
        raise AssertionError("expected missing stage rejection")


def test_bounded_research_cycle_rejects_audit_report_path_escape(tmp_path) -> None:
    payload = _cycle_spec(run_id="cycle-bad-report-path")
    payload["audit_report_path"] = "../outside.json"
    config = AutopilotCyclePlanConfig.model_validate(payload)

    try:
        plan_autopilot_research_cycle(
            config,
            output_root=tmp_path / "plans",
            job_store_path=tmp_path / "jobs.sqlite",
            enqueue=False,
        )
    except AutopilotCyclePlanError as exc:
        assert "audit_report_path escapes" in str(exc)
    else:
        raise AssertionError("expected audit report path escape rejection")


def test_autopilot_research_cycle_cli_enqueue_prints_plan_paths(tmp_path, capsys) -> None:
    spec_file = tmp_path / "cycle_spec.json"
    spec_file.write_text(json.dumps(_cycle_spec(run_id="cycle-cli")), encoding="utf-8")
    exit_code = main(
        [
            "autopilot",
            "research-cycle",
            "--mode",
            "bounded",
            "--cycle-spec-file",
            str(spec_file),
            "--output-root",
            str(tmp_path / "plans"),
            "--job-store",
            str(tmp_path / "jobs.sqlite"),
            "--enqueue",
        ]
    )
    output = capsys.readouterr().out
    values = dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)

    assert exit_code == 0
    assert values["status"] == "enqueued"
    assert values["planned_job_count"] == "7"
    assert values["enqueued_job_count"] == "7"
    assert values["accepted_research_ready"] == "false"
    assert values["promotion_ready"] == "false"
    assert Path(values["plan_manifest"]).exists()
    assert values["audit_job_id"] == "JOB-cycle-cli-audit"


def _cycle_spec(*, run_id: str = "cycle-plan") -> dict:
    return {
        "schema_version": "autopilot_bounded_cycle_spec_v1",
        "run_id": run_id,
        "mode": "bounded",
        "jobs": [
            {
                "job_id": f"JOB-{run_id}-universe",
                "kind": "universe_refresh",
                "input_spec": {"archive_root": "ARCHIVE_ROOT", "source": "payload_file"},
            },
            {
                "job_id": f"JOB-{run_id}-candles",
                "kind": "recent_candle_bootstrap",
                "input_spec": {"archive_root": "ARCHIVE_ROOT", "source": "public_api"},
            },
            {
                "job_id": f"JOB-{run_id}-coverage",
                "kind": "coverage_audit",
                "input_spec": {"archive_root": "ARCHIVE_ROOT", "coverage_min": 0.98},
            },
            {
                "job_id": f"JOB-{run_id}-backtest",
                "kind": "vectorized_backtest",
                "input_spec": {"archive_root": "ARCHIVE_ROOT", "evidence_mode": "accepted_research"},
            },
            {
                "job_id": f"JOB-{run_id}-ledger",
                "kind": "ledger_append_export",
                "input_spec": {"ledger_path": "LEDGER_PATH"},
            },
            {
                "job_id": f"JOB-{run_id}-lead",
                "kind": "lead_book_upsert",
                "input_spec": {"lead_book_path": "LEAD_BOOK_PATH"},
            },
        ],
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
