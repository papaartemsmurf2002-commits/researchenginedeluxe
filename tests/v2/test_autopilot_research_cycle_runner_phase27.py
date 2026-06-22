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
    assert execution.skipped_job_count == 7
    assert execution.audit_attempted is True
    assert execution.blocker_reasons == ()
    assert manifest["schema_version"] == "autopilot_bounded_cycle_execution_v1"
    assert manifest["accepted_research_ready"] is False
    assert manifest["research_only"] is True
    assert manifest["promotion_ready"] is False
    assert [job["action"] for job in manifest["job_executions"]].count("skipped_already_succeeded") == 7
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


def test_bounded_cycle_runner_rejects_invalid_plan_binding_manifest(tmp_path) -> None:
    result = plan_autopilot_research_cycle(
        _cycle_spec(run_id="cycle-run-bad-binding-manifest"),
        output_root=tmp_path / "plans",
        job_store_path=tmp_path / "jobs.sqlite",
        enqueue=True,
    )
    manifest_path = Path(result.plan_manifest_path)
    manifest = _read_json(manifest_path)
    manifest["bindings"] = [
        {
            "source_job_id": "JOB-cycle-run-bad-binding-manifest-backtest",
            "target_job_id": "JOB-cycle-run-bad-binding-manifest-coverage",
            "target_input_path": "archive_snapshot_id",
            "source_ref_prefix": "archive_snapshot_id=",
        }
    ]
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    try:
        run_autopilot_cycle_plan(result.plan_manifest_path)
    except AutopilotCycleRunnerError as exc:
        assert "source job must precede target job" in str(exc)
    else:
        raise AssertionError("expected invalid binding manifest rejection")


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


def test_bounded_cycle_runner_binds_source_output_ref_before_running_target(tmp_path) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    payload = _cycle_spec(run_id="cycle-run-bind")
    payload["jobs"][1]["input_spec"] = {"archive_root": "ARCHIVE_ROOT"}
    payload["bindings"] = [
        {
            "source_job_id": "JOB-cycle-run-bind-universe",
            "target_job_id": "JOB-cycle-run-bind-candles",
            "target_input_path": "instrument_id",
            "source_ref_prefix": "instrument_id=",
        }
    ]
    result = plan_autopilot_research_cycle(
        payload,
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    store = WorkerJobStore(job_store_path)
    _seed_successful_job(
        store,
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        job_id="JOB-cycle-run-bind-universe",
        output_refs=("universe_snapshot_id=UNIV", "instrument_id=hyperliquid:perp:BTC"),
    )
    original = store.load_job("JOB-cycle-run-bind-candles")
    assert original is not None
    assert "instrument_id" not in original.input_spec

    execution = run_autopilot_cycle_plan(
        result.plan_manifest_path,
        worker_id="runner-bind",
        max_jobs=1,
    )
    manifest = _read_json(Path(execution.execution_manifest_path))
    bound = store.load_job("JOB-cycle-run-bind-candles")
    transitions = store.list_transitions("JOB-cycle-run-bind-candles")

    assert bound is not None
    assert bound.status == WorkerJobStatus.SUCCEEDED
    assert bound.input_spec["instrument_id"] == "hyperliquid:perp:BTC"
    assert bound.input_spec_hash != original.input_spec_hash
    assert any(
        transition.reason == "autopilot_cycle_binding_applied"
        for transition in transitions
    )
    candle_execution = manifest["job_executions"][1]
    assert candle_execution["action"] == "ran"
    assert candle_execution["input_spec_hash_before"] == original.input_spec_hash
    assert candle_execution["input_spec_hash_after"] == bound.input_spec_hash
    assert candle_execution["applied_bindings"] == [
        "input_spec.instrument_id<=JOB-cycle-run-bind-universe:instrument_id=hyperliquid:perp:BTC"
    ]
    assert execution.status.value == "completed_with_blockers"
    assert "max_jobs_exhausted_before:JOB-cycle-run-bind-coverage" in execution.blocker_reasons


def test_bounded_cycle_runner_blocks_when_binding_ref_is_missing(tmp_path) -> None:
    job_store_path = tmp_path / "jobs.sqlite"
    payload = _cycle_spec(run_id="cycle-run-bind-missing")
    payload["jobs"][1]["input_spec"] = {"archive_root": "ARCHIVE_ROOT"}
    payload["bindings"] = [
        {
            "source_job_id": "JOB-cycle-run-bind-missing-universe",
            "target_job_id": "JOB-cycle-run-bind-missing-candles",
            "target_input_path": "instrument_id",
            "source_ref_prefix": "instrument_id=",
        }
    ]
    result = plan_autopilot_research_cycle(
        payload,
        output_root=tmp_path / "plans",
        job_store_path=job_store_path,
        enqueue=True,
    )
    store = WorkerJobStore(job_store_path)
    _seed_successful_job(
        store,
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        job_id="JOB-cycle-run-bind-missing-universe",
        output_refs=("universe_snapshot_id=UNIV",),
    )

    execution = run_autopilot_cycle_plan(
        result.plan_manifest_path,
        worker_id="runner-bind-missing",
    )
    manifest = _read_json(Path(execution.execution_manifest_path))
    bound = store.load_job("JOB-cycle-run-bind-missing-candles")

    assert bound is not None
    assert bound.status == WorkerJobStatus.QUEUED
    assert "instrument_id" not in bound.input_spec
    assert manifest["job_executions"][1]["action"] == "blocked_binding"
    assert (
        "binding_ref_missing:JOB-cycle-run-bind-missing-candles:"
        "JOB-cycle-run-bind-missing-universe:instrument_id="
    ) in execution.blocker_reasons


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
    assert values["skipped_job_count"] == "7"
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
        succeeded = store.succeed_job(
            job_id,
            worker_id=worker_id,
            output_refs=output_refs,
        )
        assert succeeded.status == WorkerJobStatus.SUCCEEDED
        time.sleep(0.002)


def _seed_successful_job(
    store: WorkerJobStore,
    *,
    kind: WorkerJobKind,
    job_id: str,
    output_refs: tuple[str, ...],
) -> None:
    worker_id = "seed-single-success"
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
