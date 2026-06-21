from __future__ import annotations

import json
import time
from pathlib import Path

from tradingbotsuite.v2.autonomy import (
    AutopilotCycleRunnerError,
    run_autopilot_cycle_plan,
)
from tradingbotsuite.v2.autonomy.cycle_planner import plan_autopilot_research_cycle
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus


def test_bounded_cycle_runner_skips_successes_and_runs_generated_audit(tmp_path) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="cycle-run-pass"),
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    store = WorkerJobStore(job_store_path)
    _seed_successful_loop_jobs(store, run_id="cycle-run-pass")

    execution = run_autopilot_cycle_plan(
        result.plan_manifest_path,
        worker_id="runner-pass",
    )
    manifest = _read_json(Path(execution.execution_manifest_path))
    report = _read_json(Path(result.audit_report_path))
    audit = store.load_job(result.audit_job_id)

    assert execution.status.value == "completed"
    assert execution.executed_job_count == 1
    assert execution.skipped_job_count == 6
    assert execution.audit_attempted is True
    assert execution.blocker_reasons == ()
    assert manifest["schema_version"] == "autopilot_bounded_cycle_execution_v1"
    assert manifest["accepted_research_ready"] is False
    assert manifest["research_only"] is True
    assert manifest["promotion_ready"] is False
    assert [job["action"] for job in manifest["job_executions"]].count("skipped_already_succeeded") == 6
    assert manifest["job_executions"][-1]["action"] == "ran"
    assert report["status"] == "pass"
    assert report["accepted_research_ready"] is False
    assert audit is not None
    assert audit.status == WorkerJobStatus.SUCCEEDED


def test_bounded_cycle_runner_rejects_plan_only_manifest(tmp_path) -> None:
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="cycle-run-plan-only"),
        output_root=tmp_path / "plans",
        job_store_path=tmp_path / "jobs.sqlite",
        enqueue=False,
    )

    try:
        run_autopilot_cycle_plan(result.plan_manifest_path)
    except AutopilotCycleRunnerError as exc:
        assert "enqueued plan" in str(exc)
    else:
        raise AssertionError("expected plan-only manifest rejection")


def test_bounded_cycle_runner_rejects_job_store_mismatch(tmp_path) -> None:
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="cycle-run-mismatch"),
        output_root=tmp_path / "plans",
        job_store_path=tmp_path / "jobs.sqlite",
        enqueue=True,
    )

    try:
        run_autopilot_cycle_plan(
            result.plan_manifest_path,
            job_store_path=tmp_path / "other.sqlite",
        )
    except AutopilotCycleRunnerError as exc:
        assert "does not match plan manifest" in str(exc)
    else:
        raise AssertionError("expected job-store mismatch rejection")


def test_bounded_cycle_runner_blocks_when_planned_job_is_not_next_for_kind(tmp_path) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    store = WorkerJobStore(job_store_path)
    store.enqueue(
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        job_id="JOB-unrelated-universe",
        input_spec={"source": "payload_file"},
        reason="preexisting_unrelated_job",
    )
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="cycle-run-not-next"),
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )

    execution = run_autopilot_cycle_plan(
        result.plan_manifest_path,
        worker_id="runner-blocked",
    )
    manifest = _read_json(Path(execution.execution_manifest_path))
    report = _read_json(Path(result.audit_report_path))

    assert execution.status.value == "completed_with_blockers"
    assert execution.executed_job_count == 1
    assert any(
        reason.startswith("planned_job_not_next_for_kind:JOB-cycle-run-not-next-universe")
        for reason in execution.blocker_reasons
    )
    assert "job_incomplete:JOB-cycle-run-not-next-universe:queued" in report["blocker_reasons"]
    assert manifest["job_executions"][0]["action"] == "blocked_not_next_for_kind"
    assert manifest["job_executions"][-1]["job_id"] == result.audit_job_id
    assert manifest["job_executions"][-1]["action"] == "ran"
    assert store.load_job("JOB-unrelated-universe").status == WorkerJobStatus.QUEUED


def test_autopilot_run_cycle_plan_cli_prints_execution_manifest(tmp_path, capsys) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="cycle-run-cli"),
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    _seed_successful_loop_jobs(WorkerJobStore(job_store_path), run_id="cycle-run-cli")

    exit_code = main(
        [
            "autopilot",
            "run-cycle-plan",
            "--plan-manifest",
            result.plan_manifest_path,
            "--worker-id",
            "runner-cli",
        ]
    )
    output = capsys.readouterr().out
    values = dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)

    assert exit_code == 0
    assert values["status"] == "completed"
    assert values["executed_job_count"] == "1"
    assert values["skipped_job_count"] == "6"
    assert values["audit_attempted"] == "true"
    assert values["blocker_count"] == "0"
    assert values["accepted_research_ready"] == "false"
    assert values["promotion_ready"] == "false"
    assert Path(values["execution_manifest"]).exists()


def _seed_successful_loop_jobs(store: WorkerJobStore, *, run_id: str) -> None:
    worker_id = "seed-loop-success"
    expected = [
        (WorkerJobKind.UNIVERSE_REFRESH, f"JOB-{run_id}-universe", ("universe_snapshot_id=UNIV",)),
        (WorkerJobKind.RECENT_CANDLE_BOOTSTRAP, f"JOB-{run_id}-candles", ("archive_snapshot_id=ARCH",)),
        (WorkerJobKind.COVERAGE_AUDIT, f"JOB-{run_id}-coverage", ("coverage_report_id=COV",)),
        (WorkerJobKind.VECTORIZED_BACKTEST, f"JOB-{run_id}-backtest", ("run_manifest_path=RUN",)),
        (WorkerJobKind.LEDGER_APPEND_EXPORT, f"JOB-{run_id}-ledger", ("ledger_path=LEDGER",)),
        (WorkerJobKind.LEAD_BOOK_UPSERT, f"JOB-{run_id}-lead", ("lead_book_path=LEAD",)),
    ]
    for kind, job_id, output_refs in expected:
        claimed = store.claim_next(kind=kind, worker_id=worker_id)
        assert claimed is not None
        assert claimed.job_id == job_id
        running = store.start_job(job_id, worker_id=worker_id)
        assert running.status == WorkerJobStatus.RUNNING
        succeeded = store.succeed_job(
            job_id,
            worker_id=worker_id,
            output_refs=output_refs,
        )
        assert succeeded.status == WorkerJobStatus.SUCCEEDED
        time.sleep(0.002)


def _cycle_spec(*, run_id: str) -> dict:
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
