from __future__ import annotations

import json
import time
from pathlib import Path

from tradingbotsuite.v2.autonomy import (
    plan_autopilot_research_cycle,
    run_autopilot_scheduler_tick,
)
from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus


def test_scheduler_tick_runs_enqueued_plan_and_writes_manifest(tmp_path) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="scheduler-pass"),
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    _seed_successful_loop_jobs(WorkerJobStore(job_store_path), run_id="scheduler-pass")

    tick = run_autopilot_scheduler_tick(
        plan_manifest_paths=(result.plan_manifest_path,),
        output_root=tmp_path / "scheduler",
        worker_id="scheduler-pass-worker",
    )
    manifest = _read_json(Path(tick.scheduler_manifest_path))

    assert tick.status.value == "completed"
    assert tick.executed_plan_count == 1
    assert tick.blocker_reasons == ()
    assert manifest["schema_version"] == "autopilot_scheduler_tick_v1"
    assert manifest["accepted_research_ready"] is False
    assert manifest["research_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["plan_results"][0]["action"] == "ran"
    assert manifest["plan_results"][0]["status"] == "completed"
    assert manifest["plan_results"][0]["executed_job_count"] == 1
    assert manifest["plan_results"][0]["skipped_job_count"] == 9
    assert Path(manifest["plan_results"][0]["execution_manifest_path"]).exists()


def test_scheduler_tick_defers_plans_after_max_plans_without_mutating_them(tmp_path) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    first = plan_autopilot_research_cycle(
        _cycle_spec(run_id="scheduler-first"),
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    second = plan_autopilot_research_cycle(
        _cycle_spec(run_id="scheduler-second"),
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    store = WorkerJobStore(job_store_path)
    _seed_successful_loop_jobs(store, run_id="scheduler-first")

    tick = run_autopilot_scheduler_tick(
        plan_manifest_paths=(first.plan_manifest_path, second.plan_manifest_path),
        output_root=tmp_path / "scheduler",
        max_plans=1,
        worker_id="scheduler-budget-worker",
    )
    manifest = _read_json(Path(tick.scheduler_manifest_path))

    assert tick.status.value == "completed_with_blockers"
    assert tick.executed_plan_count == 1
    assert any(reason.startswith("scheduler_plan_deferred_max_plans:") for reason in tick.blocker_reasons)
    assert manifest["requested_plan_count"] == 2
    assert manifest["selected_plan_count"] == 1
    assert manifest["plan_results"][1]["action"] == "deferred_max_plans"
    assert store.load_job(second.audit_job_id).status == WorkerJobStatus.QUEUED


def test_scheduler_tick_blocks_plan_only_manifest(tmp_path) -> None:
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="scheduler-plan-only"),
        output_root=tmp_path / "plans",
        job_store_path=tmp_path / "jobs.sqlite",
        enqueue=False,
    )

    tick = run_autopilot_scheduler_tick(
        plan_manifest_paths=(result.plan_manifest_path,),
        output_root=tmp_path / "scheduler",
    )
    manifest = _read_json(Path(tick.scheduler_manifest_path))

    assert tick.status.value == "completed_with_blockers"
    assert tick.executed_plan_count == 0
    assert "enqueued plan" in tick.blocker_reasons[0]
    assert manifest["plan_results"][0]["action"] == "blocked"
    assert manifest["accepted_research_ready"] is False


def test_scheduler_tick_records_missing_plan_manifest_as_blocker(tmp_path) -> None:
    missing_plan = tmp_path / "missing" / "autopilot_cycle_plan.json"

    tick = run_autopilot_scheduler_tick(
        plan_manifest_paths=(missing_plan,),
        output_root=tmp_path / "scheduler",
    )
    manifest = _read_json(Path(tick.scheduler_manifest_path))

    assert tick.status.value == "completed_with_blockers"
    assert tick.executed_plan_count == 0
    assert any(
        reason.startswith(
            "scheduler_plan_blocker:"
            f"{missing_plan.resolve(strict=False)}:"
            f"scheduler_plan_rejected:{missing_plan.resolve(strict=False)}:"
        )
        and "cycle plan cannot be read" in reason
        for reason in tick.blocker_reasons
    )
    assert manifest["plan_results"][0]["action"] == "blocked"
    assert manifest["plan_results"][0]["status"] == "blocked"
    assert manifest["accepted_research_ready"] is False


def test_scheduler_tick_records_max_jobs_per_plan_runner_blockers(tmp_path) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="scheduler-max-jobs"),
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )

    tick = run_autopilot_scheduler_tick(
        plan_manifest_paths=(result.plan_manifest_path,),
        output_root=tmp_path / "scheduler",
        worker_id="scheduler-max-jobs-worker",
        max_jobs_per_plan=1,
    )
    manifest = _read_json(Path(tick.scheduler_manifest_path))
    plan_result = manifest["plan_results"][0]
    execution_manifest = _read_json(Path(plan_result["execution_manifest_path"]))

    assert tick.status.value == "completed_with_blockers"
    assert tick.executed_plan_count == 1
    assert any("max_jobs_exhausted_before:" in reason for reason in tick.blocker_reasons)
    assert plan_result["action"] == "ran"
    assert plan_result["status"] == "completed_with_blockers"
    assert plan_result["executed_job_count"] == 1
    assert any("max_jobs_exhausted_before:" in reason for reason in plan_result["blocker_reasons"])
    assert execution_manifest["max_jobs"] == 1
    assert any(execution["action"] == "not_run_max_jobs" for execution in execution_manifest["job_executions"])
    assert manifest["accepted_research_ready"] is False


def test_autopilot_scheduler_tick_cli_prints_manifest(tmp_path, capsys) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="scheduler-cli"),
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    _seed_successful_loop_jobs(WorkerJobStore(job_store_path), run_id="scheduler-cli")

    exit_code = main(
        [
            "autopilot",
            "scheduler-tick",
            "--plan-manifest",
            result.plan_manifest_path,
            "--output-root",
            str(tmp_path / "scheduler"),
            "--worker-id",
            "scheduler-cli-worker",
        ]
    )
    output = capsys.readouterr().out
    values = dict(line.split("=", 1) for line in output.strip().splitlines() if "=" in line)

    assert exit_code == 0
    assert values["status"] == "completed"
    assert values["executed_plan_count"] == "1"
    assert values["blocker_count"] == "0"
    assert values["accepted_research_ready"] == "false"
    assert values["promotion_ready"] == "false"
    assert Path(values["scheduler_manifest"]).exists()


def _seed_successful_loop_jobs(store: WorkerJobStore, *, run_id: str) -> None:
    worker_id = "seed-scheduler-success"
    expected = [
        (WorkerJobKind.UNIVERSE_REFRESH, f"JOB-{run_id}-universe", ("universe_snapshot_id=UNIV",)),
        (WorkerJobKind.RECENT_CANDLE_BOOTSTRAP, f"JOB-{run_id}-candles", ("archive_snapshot_id=ARCH",)),
        (WorkerJobKind.COVERAGE_AUDIT, f"JOB-{run_id}-coverage", ("coverage_report_id=COV",)),
        (
            WorkerJobKind.STRATEGY_QUEUE_SCAN,
            f"JOB-{run_id}-strategy-queue",
            (
                "strategy_queue_manifest_id=SQ",
                "accepted_spec_path=SPEC",
                "accepted_spec_sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "strategy_spec_hash=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            ),
        ),
        (
            WorkerJobKind.BACKTEST_DATA_LOAD,
            f"JOB-{run_id}-backtest-data",
            (
                "backtest_data_manifest_path=BACKTEST_DATA",
                "data_manifest_id=DATA",
                "data_manifest_hash=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
                "archive_snapshot_id=ARCH",
                "universe_snapshot_id=UNIV",
                "coverage_report_id=COV",
            ),
        ),
        (WorkerJobKind.VECTORIZED_BACKTEST, f"JOB-{run_id}-backtest", ("run_manifest_path=RUN",)),
        (
            WorkerJobKind.VALIDATION_GATE,
            f"JOB-{run_id}-validation",
            ("validation_manifest_path=VALIDATION", "validation_manifest_id=VAL"),
        ),
        (WorkerJobKind.LEDGER_APPEND_EXPORT, f"JOB-{run_id}-ledger", ("ledger_path=LEDGER",)),
        (WorkerJobKind.LEAD_BOOK_UPSERT, f"JOB-{run_id}-lead", ("lead_book_path=LEAD",)),
    ]
    for kind, job_id, output_refs in expected:
        claimed = store.claim_next(kind=kind, worker_id=worker_id)
        assert claimed is not None
        assert claimed.job_id == job_id
        running = store.start_job(job_id, worker_id=worker_id)
        assert running.status == WorkerJobStatus.RUNNING
        succeeded = store.succeed_job(job_id, worker_id=worker_id, output_refs=output_refs)
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
                "job_id": f"JOB-{run_id}-strategy-queue",
                "kind": "strategy_queue_scan",
                "input_spec": {"strategy_root": "STRATEGY_ROOT", "output_root": "STRATEGY_QUEUE"},
            },
            {
                "job_id": f"JOB-{run_id}-backtest-data",
                "kind": "backtest_data_load",
                "input_spec": {"archive_root": "ARCHIVE_ROOT", "evidence_mode": "accepted_research"},
            },
            {
                "job_id": f"JOB-{run_id}-backtest",
                "kind": "vectorized_backtest",
                "input_spec": {"archive_root": "ARCHIVE_ROOT", "evidence_mode": "accepted_research"},
            },
            {
                "job_id": f"JOB-{run_id}-validation",
                "kind": "validation_gate",
                "input_spec": {"run_manifest_path": "RUN_MANIFEST_PATH"},
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
