from __future__ import annotations

import json

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job


def test_binance_derivatives_context_worker_runs_fixture_funding_backfill(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.BINANCE_DERIVATIVES_CONTEXT_BACKFILL,
        input_spec={
            "source": "fixture_payloads",
            "archive_root": str(archive_root),
            "family": "funding_rate_history",
            "symbol": "btcusdt",
            "instrument_id": "binance:perp:BTCUSDT",
            "start_time_ms": 0,
            "end_time_ms": 57_599_999,
            "limit": 1000,
            "universe_snapshot_ref": "manifests/universe/u.json",
            "source_registry_ref": "manifests/source_registry/s.json",
            "symbol_map_ref": "manifests/symbol_maps/m.json",
            "archive_snapshot_ref": "manifests/archive_snapshots/a.json",
            "response_payloads": [
                [
                    {
                        "symbol": "BTCUSDT",
                        "fundingRate": "0.0001",
                        "fundingTime": 0,
                        "markPrice": "42000",
                    },
                    {
                        "symbol": "BTCUSDT",
                        "fundingRate": "0.0002",
                        "fundingTime": 28_800_000,
                        "markPrice": "42100",
                    },
                ]
            ],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.BINANCE_DERIVATIVES_CONTEXT_BACKFILL,
        worker_id="worker-binance-derivatives",
    )

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    loaded = store.load_job(queued.job_id)
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "job_kind=binance_derivatives_context_backfill" in loaded.output_refs
    assert "source_mode=fixture_payloads" in loaded.output_refs
    assert "family=funding_rate_history" in loaded.output_refs
    assert "symbol=BTCUSDT" in loaded.output_refs
    assert "backfill_status=completed" in loaded.output_refs
    assert "accepted_for_research_reporting=true" in loaded.output_refs
    assert "blocker_reasons=" in loaded.output_refs
    coverage_ref = _ref_value(loaded.output_refs, "coverage_report_ref")
    coverage_payload = json.loads(
        ArchiveLayout(archive_root).resolve(coverage_ref).read_text(encoding="utf-8")
    )
    assert coverage_payload["accepted_for_research_reporting"] is True
    assert coverage_payload["family"] == "funding_rate_history"


def test_binance_derivatives_context_worker_preserves_blocked_coverage(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.BINANCE_DERIVATIVES_CONTEXT_BACKFILL,
        input_spec={
            "source": "fixture_payloads",
            "archive_root": str(archive_root),
            "family": "open_interest",
            "symbol": "ethusdt",
            "instrument_id": "binance:perp:ETHUSDT",
            "universe_snapshot_ref": "manifests/universe/u.json",
            "source_registry_ref": "manifests/source_registry/s.json",
            "symbol_map_ref": "manifests/symbol_maps/m.json",
            "archive_snapshot_ref": "manifests/archive_snapshots/a.json",
            "response_payloads": [
                {
                    "symbol": "ETHUSDT",
                    "openInterest": "123.4",
                    "time": 1704067200000,
                }
            ],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.BINANCE_DERIVATIVES_CONTEXT_BACKFILL,
        worker_id="worker-binance-derivatives",
    )

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    loaded = store.load_job(queued.job_id)
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "backfill_status=blocked" in loaded.output_refs
    assert "accepted_for_research_reporting=false" in loaded.output_refs
    assert "blocker_reasons=current_context_snapshot_only" in loaded.output_refs
    coverage_ref = _ref_value(loaded.output_refs, "coverage_report_ref")
    coverage_payload = json.loads(
        ArchiveLayout(archive_root).resolve(coverage_ref).read_text(encoding="utf-8")
    )
    assert coverage_payload["accepted_for_research_reporting"] is False
    assert coverage_payload["reason"] == ["current_context_snapshot_only"]


def test_binance_derivatives_context_worker_invalid_fixture_spec_fails(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.BINANCE_DERIVATIVES_CONTEXT_BACKFILL,
        input_spec={
            "source": "fixture_payloads",
            "archive_root": str(tmp_path / "archive"),
            "family": "open_interest",
            "symbol": "btcusdt",
            "instrument_id": "binance:perp:BTCUSDT",
            "universe_snapshot_ref": "manifests/universe/u.json",
            "source_registry_ref": "manifests/source_registry/s.json",
            "symbol_map_ref": "manifests/symbol_maps/m.json",
            "response_payloads": [],
        },
        max_attempts=1,
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.BINANCE_DERIVATIVES_CONTEXT_BACKFILL,
        worker_id="worker-binance-derivatives",
    )

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    loaded = store.load_job(queued.job_id)
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.FAILED
    assert "response_payloads" in (loaded.failure_reason or "")


def _ref_value(refs: tuple[str, ...], key: str) -> str:
    prefix = f"{key}="
    for ref in refs:
        if ref.startswith(prefix):
            return ref[len(prefix) :]
    raise AssertionError(f"missing ref {key}")
