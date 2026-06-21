from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job


ROOT = Path(__file__).resolve().parents[2]


def test_sqlite_wal_job_store_survives_process_restart(tmp_path) -> None:
    store_path = tmp_path / "jobs" / "redx_jobs.sqlite"
    first = WorkerJobStore(store_path)
    first.initialize()
    queued = first.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        input_spec={"instrument_id": "hyperliquid:perp:BTC", "timeframe": "1m"},
    )

    second = WorkerJobStore(store_path)
    loaded = second.load_job(queued.job_id)

    assert loaded == queued
    with sqlite3.connect(store_path) as connection:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
    assert journal_mode.lower() == "wal"


def test_claim_heartbeat_failure_retry_and_terminal_transitions_are_recorded(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        input_spec={"instrument_id": "hyperliquid:perp:BTC"},
        max_attempts=2,
    )
    claimed = store.claim_next(kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP, worker_id="worker-a")
    assert claimed is not None
    running = store.start_job(claimed.job_id, worker_id="worker-a")
    heartbeat = store.heartbeat(running.job_id, worker_id="worker-a", details={"phase": "test"})

    requeued = store.fail_job(
        queued.job_id,
        worker_id="worker-a",
        reason="transient_failure",
        retryable=True,
    )
    second_claim = store.claim_next(kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP, worker_id="worker-a")
    assert second_claim is not None
    store.start_job(second_claim.job_id, worker_id="worker-a")
    terminal = store.fail_job(
        queued.job_id,
        worker_id="worker-a",
        reason="terminal_failure",
        retryable=True,
    )

    assert heartbeat.details == {"phase": "test"}
    assert requeued.status == WorkerJobStatus.QUEUED
    assert terminal.status == WorkerJobStatus.FAILED
    assert terminal.terminal_state is True
    assert terminal.failure_reason == "terminal_failure"
    transitions = [transition.to_status for transition in store.list_transitions(queued.job_id)]
    assert transitions == [
        WorkerJobStatus.QUEUED,
        WorkerJobStatus.CLAIMED,
        WorkerJobStatus.RUNNING,
        WorkerJobStatus.FAILED,
        WorkerJobStatus.RETRYING,
        WorkerJobStatus.QUEUED,
        WorkerJobStatus.CLAIMED,
        WorkerJobStatus.RUNNING,
        WorkerJobStatus.FAILED,
    ]


def test_stale_running_job_becomes_retryable_evidence(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        input_spec={"instrument_id": "hyperliquid:perp:BTC"},
    )
    claimed = store.claim_next(kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP, worker_id="worker-a")
    assert claimed is not None
    store.start_job(claimed.job_id, worker_id="worker-a")

    stale = store.mark_stale_jobs(stale_after=timedelta(seconds=0))

    assert [record.job_id for record in stale] == [queued.job_id]
    assert stale[0].status == WorkerJobStatus.STALE
    retried = store.retry_job(queued.job_id, worker_id="operator")
    assert retried.status == WorkerJobStatus.QUEUED
    assert retried.terminal_state is False


def test_universe_refresh_worker_outputs_archive_manifest_refs(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(_universe_payload()), encoding="utf-8")
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        input_spec={
            "archive_root": str(archive_root),
            "payload_file": str(payload_file),
            "asof_date": "2026-06-01",
            "min_day_notional_usd": 5_000_000,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        worker_id="worker-universe",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert any(ref.startswith("raw_file_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("universe_snapshot_id=") for ref in loaded.archive_manifest_refs)
    assert (archive_root / "manifests" / "universe_snapshots.parquet").exists()


def test_websocket_capture_skeleton_records_gap_instead_of_silent_success(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_CAPTURE,
        input_spec={
            "instrument_id": "hyperliquid:perp:BTC",
            "datatype": "bbo",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "reconnect_attempts": 3,
            "backoff_seconds": 5,
            "gap_reason": "test_reconnect_gap",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_CAPTURE,
        worker_id="worker-ws",
    )
    gaps = store.list_gap_records(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert len(gaps) == 1
    assert gaps[0].reason == "test_reconnect_gap"
    assert gaps[0].reconnect_attempts == 3
    assert gaps[0].backoff_seconds == 5
    assert gaps[0].evidence_scope == "diagnostic_gap_record"


def test_worker_runner_rejects_asgi_operator_process_execution(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        input_spec={"instrument_id": "hyperliquid:perp:BTC"},
    )

    with pytest.raises(RuntimeError, match="ASGI/operator process"):
        run_one_job(
            store=store,
            kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
            worker_id="operator-process",
            forbid_asgi=True,
        )

    loaded = store.load_job(queued.job_id)
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.QUEUED
    assert loaded.attempts == 0


def test_worker_cli_enqueue_run_status_retry_and_cancel(tmp_path) -> None:
    store_path = tmp_path / "jobs.sqlite"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    spec = {"instrument_id": "hyperliquid:perp:BTC", "timeframe": "1m"}

    init = _run_cli(["worker", "init", "--job-store", str(store_path)], env=env)
    enqueue = _run_cli(
        [
            "worker",
            "enqueue",
            "--job-store",
            str(store_path),
            "--kind",
            "recent_candle_bootstrap",
            "--input-spec-json",
            json.dumps(spec),
            "--job-id",
            "JOB-cli-recent",
        ],
        env=env,
    )
    run = _run_cli(
        [
            "worker",
            "run",
            "--job-store",
            str(store_path),
            "--kind",
            "recent_candle_bootstrap",
            "--worker-id",
            "worker-cli",
        ],
        env=env,
    )
    status = _run_cli(
        ["worker", "status", "--job-store", str(store_path), "--job-id", "JOB-cli-recent"],
        env=env,
    )

    assert init.returncode == 0
    assert enqueue.returncode == 0
    assert "job_id=JOB-cli-recent" in enqueue.stdout
    assert run.returncode == 0
    assert "status=succeeded" in run.stdout
    assert "api_cap_warning_id=" in run.stdout
    assert status.returncode == 0
    assert "JOB-cli-recent\trecent_candle_bootstrap\tsucceeded" in status.stdout

    queued_cancel = _run_cli(
        [
            "worker",
            "enqueue",
            "--job-store",
            str(store_path),
            "--kind",
            "funding_backfill",
            "--input-spec-json",
            json.dumps({"instrument_id": "hyperliquid:perp:BTC"}),
            "--job-id",
            "JOB-cli-cancel",
        ],
        env=env,
    )
    cancel = _run_cli(
        ["worker", "cancel", "--job-store", str(store_path), "--job-id", "JOB-cli-cancel"],
        env=env,
    )
    retry = _run_cli(
        ["worker", "retry", "--job-store", str(store_path), "--job-id", "JOB-cli-cancel"],
        env=env,
    )

    assert queued_cancel.returncode == 0
    assert "JOB-cli-cancel\tfunding_backfill\tcancelled" in cancel.stdout
    assert "JOB-cli-cancel\tfunding_backfill\tqueued" in retry.stdout


def _run_cli(args: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tradingbotsuite.v2.cli.main", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _universe_payload():
    return [
        {
            "universe": [
                {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
                {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
            ]
        },
        [
            {
                "dayNtlVlm": "100000000",
                "openInterest": "10",
                "markPx": "60000",
                "oraclePx": "60001",
                "funding": "0.0001",
            },
            {
                "dayNtlVlm": "12000000",
                "openInterest": "20",
                "markPx": "150",
                "oraclePx": "151",
                "funding": "0.0002",
            },
        ],
    ]
