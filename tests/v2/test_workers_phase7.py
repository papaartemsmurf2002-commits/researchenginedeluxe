from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from tradingbotsuite.v2.archive import (
    ArchiveLayer,
    ArchiveLayout,
    ArchiveManifestStore,
    SilverFundingIntervalRow,
)
from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.archive.microstructure import write_microstructure_raw_capture
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode
from tradingbotsuite.v2.ledger import read_ledger
from tradingbotsuite.v2.lead_book import LeadBookStore
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads
from tradingbotsuite.v2.universe.hyperliquid import refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode
from tradingbotsuite.v2.venues.hyperliquid import HyperliquidInfoClient
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job


ROOT = Path(__file__).resolve().parents[2]
INSTRUMENT = "hyperliquid:perp:BTC"
START = datetime(2026, 1, 1, tzinfo=UTC)


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
    assert "source_mode=payload_file" in loaded.output_refs
    assert any(ref.startswith("raw_file_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("universe_snapshot_id=") for ref in loaded.archive_manifest_refs)
    assert (archive_root / "manifests" / "universe_snapshots.parquet").exists()


def test_universe_refresh_worker_public_api_source_outputs_provenance(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_root = tmp_path / "archive-public-universe"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert json.loads(request.content.decode("utf-8")) == {"type": "metaAndAssetCtxs"}
        return httpx.Response(200, json=_universe_payload())

    class FakeHyperliquidInfoClient:
        def __init__(self, base_url: str, timeout: float) -> None:
            self._client = HyperliquidInfoClient(
                base_url=base_url,
                timeout=timeout,
                transport=httpx.MockTransport(handler),
            )

        def fetch_meta_and_asset_contexts(self):
            return self._client.fetch_meta_and_asset_contexts()

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidInfoClient",
        FakeHyperliquidInfoClient,
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "public_info_url": "https://example.test/info",
            "public_info_timeout": 3.0,
            "asof_date": "2026-06-01",
            "min_day_notional_usd": 5_000_000,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        worker_id="worker-public-universe",
    )
    loaded = store.load_job(queued.job_id)
    ingestion_runs = ArchiveManifestStore(ArchiveLayout(archive_root)).load_ingestion_runs()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "source_mode=public_api" in loaded.output_refs
    assert "venue_adapter_id=hyperliquid_public_info_v1" in loaded.output_refs
    assert "source_endpoint_or_subscription=info/metaAndAssetCtxs" in loaded.output_refs
    assert any(ref.startswith("raw_payload_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_request_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_response_id=") for ref in loaded.output_refs)
    assert ingestion_runs[0].adapter_id == "hyperliquid_public_info_v1"
    assert ingestion_runs[0].source_endpoint_or_subscription == "info/metaAndAssetCtxs"


def test_universe_refresh_worker_requires_payload_file_or_public_api_source(tmp_path) -> None:
    archive_root = tmp_path / "archive-missing-universe-source"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "asof_date": "2026-06-01",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        worker_id="worker-universe-source-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "requires payload_file or source=public_api" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_recent_candle_bootstrap_worker_writes_archive_layers_and_coverage(tmp_path) -> None:
    archive_root = tmp_path / "archive-candles"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-candles",
        input_spec={
            "archive_root": str(archive_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-candles",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
            "derive_timeframes": ["5m"],
            "create_snapshot": True,
            "records": [_candle_row(index) for index in range(60)],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-candles",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)
    manifest_rows = ArchiveManifestStore(layout).load_file_manifest()
    coverage_reports = CoverageManifestStore(layout).load_coverage_reports()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "collector_mode=fixture_candle_archive_write" in loaded.output_refs
    assert any(ref.startswith("raw_file_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("bronze_file_ids=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("silver_file_ids=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("coverage_report_ids=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("archive_snapshot_id=") for ref in loaded.archive_manifest_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "candles"),
        (ArchiveLayer.BRONZE, "candles"),
        (ArchiveLayer.SILVER, "bars"),
    }
    silver_timeframes = {row.timeframe for row in manifest_rows if row.layer == ArchiveLayer.SILVER}
    assert silver_timeframes == {"1m", "5m"}
    assert {report.timeframe for report in coverage_reports} == {"1m", "5m"}
    assert all(report.coverage_ratio == 1.0 for report in coverage_reports)
    assert ArchiveManifestStore(layout).load_archive_snapshots()


def test_recent_candle_bootstrap_worker_public_api_writes_archive_layers(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_root = tmp_path / "archive-public-candles"
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(minutes=5)
    expected_body = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1m",
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert json.loads(request.content.decode("utf-8")) == expected_body
        return httpx.Response(
            200,
            json=[_hyperliquid_candle_row(index) for index in range(5)],
            headers={"x-ratelimit-remaining": "9"},
        )

    class FakeHyperliquidInfoClient:
        def __init__(self, base_url: str, timeout: float) -> None:
            self._client = HyperliquidInfoClient(
                base_url=base_url,
                timeout=timeout,
                transport=httpx.MockTransport(handler),
            )

        def fetch_candle_snapshot(self, **kwargs):
            return self._client.fetch_candle_snapshot(**kwargs)

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidInfoClient",
        FakeHyperliquidInfoClient,
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-public-candles",
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "public_info_url": "https://example.test/info",
            "public_info_timeout": 3.0,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-public-candles",
            "start_ts": start.isoformat(),
            "end_ts": end.isoformat(),
            "derive_timeframes": ["5m"],
            "create_snapshot": True,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-public-candles",
    )
    loaded = store.load_job(queued.job_id)
    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED

    layout = ArchiveLayout(archive_root)
    manifest_store = ArchiveManifestStore(layout)
    manifest_rows = manifest_store.load_file_manifest()
    coverage_reports = CoverageManifestStore(layout).load_coverage_reports()
    ingestion_runs = manifest_store.load_ingestion_runs()
    silver_1m = [
        row
        for row in manifest_rows
        if row.layer == ArchiveLayer.SILVER and row.datatype == "bars" and row.timeframe == "1m"
    ][0]
    silver_rows = pq.ParquetFile(layout.resolve(silver_1m.path)).read().to_pylist()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "collector_mode=public_api_candle_archive_write" in loaded.output_refs
    assert "source_mode=public_api" in loaded.output_refs
    assert "api_row_count=5" in loaded.output_refs
    assert "venue_adapter_id=hyperliquid_public_info_v1" in loaded.output_refs
    assert "source_endpoint_or_subscription=info/candleSnapshot" in loaded.output_refs
    assert "coin=BTC" in loaded.output_refs
    assert "api_documented_limit=most_recent_5000_candles" in loaded.output_refs
    assert any(ref.startswith("raw_request_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_response_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_payload_sha256=") for ref in loaded.output_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "candles"),
        (ArchiveLayer.BRONZE, "candles"),
        (ArchiveLayer.SILVER, "bars"),
    }
    assert {row["instrument_id"] for row in silver_rows} == {INSTRUMENT}
    assert {row.timeframe for row in manifest_rows if row.layer == ArchiveLayer.SILVER} == {"1m", "5m"}
    assert {report.timeframe for report in coverage_reports} == {"1m", "5m"}
    assert all(report.coverage_ratio == 1.0 for report in coverage_reports)
    assert ingestion_runs[0].adapter_id == "hyperliquid_public_info_v1"
    assert ingestion_runs[0].source_endpoint_or_subscription == "info/candleSnapshot"
    assert manifest_store.load_archive_snapshots()


def test_recent_candle_bootstrap_worker_public_api_pages_candle_snapshots(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_root = tmp_path / "archive-public-candles-paged"
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(minutes=5)
    start_ms = int(start.timestamp() * 1000)
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        body = json.loads(request.content.decode("utf-8"))
        seen_bodies.append(body)
        req = body["req"]
        assert isinstance(req, dict)
        page_start = int(req["startTime"])
        page_end = int(req["endTime"])
        first_index = (page_start - start_ms) // 60_000
        end_index = (page_end - start_ms) // 60_000
        return httpx.Response(
            200,
            json=[_hyperliquid_candle_row(index) for index in range(first_index, end_index)],
            headers={"x-ratelimit-remaining": "9"},
        )

    class FakeHyperliquidInfoClient:
        def __init__(self, base_url: str, timeout: float) -> None:
            self._client = HyperliquidInfoClient(
                base_url=base_url,
                timeout=timeout,
                transport=httpx.MockTransport(handler),
            )

        def fetch_candle_snapshot(self, **kwargs):
            return self._client.fetch_candle_snapshot(**kwargs)

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidInfoClient",
        FakeHyperliquidInfoClient,
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-public-candles-paged",
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "public_info_url": "https://example.test/info",
            "public_info_timeout": 3.0,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-public-candles-paged",
            "start_ts": start.isoformat(),
            "end_ts": end.isoformat(),
            "max_candles_per_public_page": 2,
            "max_public_info_pages": 5,
            "derive_timeframes": ["5m"],
            "create_snapshot": True,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-public-candles-paged",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)
    manifest_store = ArchiveManifestStore(layout)
    manifest_rows = manifest_store.load_file_manifest()
    coverage_reports = CoverageManifestStore(layout).load_coverage_reports()
    silver_1m = [
        row
        for row in manifest_rows
        if row.layer == ArchiveLayer.SILVER and row.datatype == "bars" and row.timeframe == "1m"
    ][0]
    silver_rows = pq.ParquetFile(layout.resolve(silver_1m.path)).read().to_pylist()
    raw_request_ids = [
        ref.removeprefix("raw_request_ids=")
        for ref in loaded.output_refs
        if ref.startswith("raw_request_ids=")
    ][0].split(",")
    raw_response_ids = [
        ref.removeprefix("raw_response_ids=")
        for ref in loaded.output_refs
        if ref.startswith("raw_response_ids=")
    ][0].split(",")
    raw_payload_hashes = [
        ref.removeprefix("raw_payload_sha256s=")
        for ref in loaded.output_refs
        if ref.startswith("raw_payload_sha256s=")
    ][0].split(",")

    assert seen_bodies == [
        {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "1m",
                "startTime": start_ms,
                "endTime": start_ms + 2 * 60_000,
            },
        },
        {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "1m",
                "startTime": start_ms + 2 * 60_000,
                "endTime": start_ms + 4 * 60_000,
            },
        },
        {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "1m",
                "startTime": start_ms + 4 * 60_000,
                "endTime": start_ms + 5 * 60_000,
            },
        },
    ]
    assert "api_row_count=5" in loaded.output_refs
    assert "api_page_count=3" in loaded.output_refs
    assert "api_page_span_limit_candles=2" in loaded.output_refs
    assert "api_recent_window_caveat=not_full_historical_evidence" in loaded.output_refs
    assert len(raw_request_ids) == 3
    assert len(raw_response_ids) == 3
    assert len(raw_payload_hashes) == 3
    assert {row["instrument_id"] for row in silver_rows} == {INSTRUMENT}
    assert len(silver_rows) == 5
    assert {report.timeframe for report in coverage_reports} == {"1m", "5m"}
    assert all(report.coverage_ratio == 1.0 for report in coverage_reports)
    assert manifest_store.load_archive_snapshots()


def test_recent_candle_bootstrap_worker_public_api_fails_when_page_cap_exhausted(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_root = tmp_path / "archive-public-candles-page-cap"
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(minutes=5)
    start_ms = int(start.timestamp() * 1000)
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        seen_bodies.append(body)
        req = body["req"]
        assert isinstance(req, dict)
        page_start = int(req["startTime"])
        page_end = int(req["endTime"])
        first_index = (page_start - start_ms) // 60_000
        end_index = (page_end - start_ms) // 60_000
        return httpx.Response(
            200,
            json=[_hyperliquid_candle_row(index) for index in range(first_index, end_index)],
        )

    class FakeHyperliquidInfoClient:
        def __init__(self, base_url: str, timeout: float) -> None:
            self._client = HyperliquidInfoClient(
                base_url=base_url,
                timeout=timeout,
                transport=httpx.MockTransport(handler),
            )

        def fetch_candle_snapshot(self, **kwargs):
            return self._client.fetch_candle_snapshot(**kwargs)

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidInfoClient",
        FakeHyperliquidInfoClient,
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-public-candles-page-cap",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "public_info_url": "https://example.test/info",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "start_ts": start.isoformat(),
            "end_ts": end.isoformat(),
            "max_candles_per_public_page": 2,
            "max_public_info_pages": 2,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-public-candles-page-cap",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "public candleSnapshot pagination exceeded max_public_info_pages" in (
        loaded.failure_reason or ""
    )
    assert len(seen_bodies) == 2
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_recent_candle_bootstrap_worker_public_api_rejects_oversized_candle_page(
    tmp_path,
) -> None:
    archive_root = tmp_path / "archive-public-candles-oversized-page"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-public-candles-oversized-page",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "public_info_url": "https://example.test/info",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:10:00+00:00",
            "max_candles_per_public_page": 5001,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-public-candles-oversized-page",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "cannot exceed documented 5000-candle limit" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_recent_candle_bootstrap_worker_rejects_public_api_with_local_records(tmp_path) -> None:
    archive_root = tmp_path / "archive-public-candle-reject"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-public-candle-records-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "records": [_candle_row(0)],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-public-candle-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "source=public_api cannot include records" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_funding_backfill_worker_writes_archive_layers(tmp_path) -> None:
    archive_root = tmp_path / "archive-funding"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.FUNDING_BACKFILL,
        job_id="JOB-funding",
        input_spec={
            "archive_root": str(archive_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "run_id": "run-funding",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T02:00:00+00:00",
            "records": [
                {
                    "ts": "2026-01-01T00:00:00Z",
                    "end_ts": "2026-01-01T01:00:00Z",
                    "instrument_id": INSTRUMENT,
                    "fundingRate": "0.0001",
                },
                {
                    "ts": "2026-01-01T01:00:00Z",
                    "end_ts": "2026-01-01T02:00:00Z",
                    "instrument_id": INSTRUMENT,
                    "fundingRate": "-0.0002",
                },
            ],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.FUNDING_BACKFILL,
        worker_id="worker-funding",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)
    manifest_rows = ArchiveManifestStore(layout).load_file_manifest()
    silver_file = [
        row
        for row in manifest_rows
        if row.layer == ArchiveLayer.SILVER and row.datatype == "funding"
    ][0]
    silver_rows = [
        SilverFundingIntervalRow.model_validate(row)
        for row in pq.ParquetFile(layout.resolve(silver_file.path)).read().to_pylist()
    ]

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "collector_mode=fixture_funding_archive_write" in loaded.output_refs
    assert any(ref.startswith("raw_file_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("bronze_file_ids=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("silver_file_ids=") for ref in loaded.archive_manifest_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "funding"),
        (ArchiveLayer.BRONZE, "funding"),
        (ArchiveLayer.SILVER, "funding"),
    }
    assert [row.funding_rate for row in silver_rows] == [0.0001, -0.0002]
    assert all(row.research_only and row.observe_only and not row.promotion_ready for row in silver_rows)


def test_funding_backfill_worker_public_api_paginates_and_writes_archive_layers(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_root = tmp_path / "archive-public-funding"
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=3)
    first_start_ms = int(start.timestamp() * 1000)
    second_start_ms = first_start_ms + 3_600_000 + 1
    end_ms = int(end.timestamp() * 1000)
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        seen_bodies.append(body)
        assert request.method == "POST"
        assert body["type"] == "fundingHistory"
        assert body["coin"] == "BTC"
        assert body["endTime"] == end_ms
        if body["startTime"] == first_start_ms:
            return httpx.Response(
                200,
                json=[
                    _hyperliquid_funding_row(0, "0.0001"),
                    _hyperliquid_funding_row(1, "-0.0002"),
                ],
                headers={"x-ratelimit-remaining": "8"},
            )
        assert body["startTime"] == second_start_ms
        return httpx.Response(
            200,
            json=[_hyperliquid_funding_row(2, "0.0003")],
            headers={"x-ratelimit-remaining": "7"},
        )

    class FakeHyperliquidInfoClient:
        def __init__(self, base_url: str, timeout: float) -> None:
            self._client = HyperliquidInfoClient(
                base_url=base_url,
                timeout=timeout,
                transport=httpx.MockTransport(handler),
            )

        def fetch_funding_history(self, **kwargs):
            return self._client.fetch_funding_history(**kwargs)

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidInfoClient",
        FakeHyperliquidInfoClient,
    )
    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs._PUBLIC_INFO_TIME_RANGE_PAGE_LIMIT",
        2,
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.FUNDING_BACKFILL,
        job_id="JOB-public-funding",
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "public_info_url": "https://example.test/info",
            "public_info_timeout": 3.0,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "run_id": "run-public-funding",
            "start_ts": start.isoformat(),
            "end_ts": end.isoformat(),
            "max_public_info_pages": 3,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.FUNDING_BACKFILL,
        worker_id="worker-public-funding",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)
    manifest_store = ArchiveManifestStore(layout)
    manifest_rows = manifest_store.load_file_manifest()
    ingestion_runs = manifest_store.load_ingestion_runs()
    silver_file = [
        row
        for row in manifest_rows
        if row.layer == ArchiveLayer.SILVER and row.datatype == "funding"
    ][0]
    silver_rows = [
        SilverFundingIntervalRow.model_validate(row)
        for row in pq.ParquetFile(layout.resolve(silver_file.path)).read().to_pylist()
    ]

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert len(seen_bodies) == 2
    assert seen_bodies[1]["startTime"] == second_start_ms
    assert "collector_mode=public_api_funding_archive_write" in loaded.output_refs
    assert "source_mode=public_api" in loaded.output_refs
    assert "api_row_count=3" in loaded.output_refs
    assert "api_page_count=2" in loaded.output_refs
    assert "venue_adapter_id=hyperliquid_public_info_v1" in loaded.output_refs
    assert "source_endpoint_or_subscription=info/fundingHistory" in loaded.output_refs
    assert "coin=BTC" in loaded.output_refs
    assert "api_documented_limit=time_range_responses_return_500_elements_or_blocks" in loaded.output_refs
    assert any(ref.startswith("raw_request_ids=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_response_ids=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_payload_sha256s=") for ref in loaded.output_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "funding"),
        (ArchiveLayer.BRONZE, "funding"),
        (ArchiveLayer.SILVER, "funding"),
    }
    assert [row.funding_rate for row in silver_rows] == [0.0001, -0.0002, 0.0003]
    assert {row.instrument_id for row in silver_rows} == {INSTRUMENT}
    assert ingestion_runs[0].adapter_id == "hyperliquid_public_info_v1"
    assert ingestion_runs[0].source_endpoint_or_subscription == "info/fundingHistory"
    assert all(row.research_only and row.observe_only and not row.promotion_ready for row in silver_rows)


def test_funding_backfill_worker_rejects_public_api_with_local_records(tmp_path) -> None:
    archive_root = tmp_path / "archive-public-funding-reject"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.FUNDING_BACKFILL,
        job_id="JOB-public-funding-records-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
            "records": [
                {
                    "ts": "2026-01-01T00:00:00Z",
                    "instrument_id": INSTRUMENT,
                    "fundingRate": "0.0001",
                }
            ],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.FUNDING_BACKFILL,
        worker_id="worker-public-funding-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "source=public_api cannot include records" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_coverage_audit_worker_writes_reports_from_silver_archive_file(tmp_path) -> None:
    archive_root = tmp_path / "archive-coverage"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-candles-for-coverage",
        input_spec={
            "archive_root": str(archive_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-candles-for-coverage",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
            "records": [_candle_row(index) for index in range(60)],
            "derive_timeframes": [],
            "skip_coverage": True,
        },
    )
    candle_result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-candles-for-coverage",
    )
    assert candle_result is not None
    silver_file_id = _silver_bars_file_id(archive_root, timeframe="1m")
    queued = store.enqueue(
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-coverage-audit",
        input_spec={
            "archive_root": str(archive_root),
            "silver_file_id": silver_file_id,
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.COVERAGE_AUDIT,
        worker_id="worker-coverage",
    )
    loaded = store.load_job(queued.job_id)
    coverage_store = CoverageManifestStore(ArchiveLayout(archive_root))
    reports = coverage_store.load_coverage_reports()
    checks = coverage_store.load_quality_checks()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "job_kind=coverage_audit" in loaded.output_refs
    assert "coverage_ratio=1.000000000000" in loaded.output_refs
    assert "quality_status=non_evidence" in loaded.output_refs
    assert "evidence_eligible=false" in loaded.output_refs
    assert "blocker_reasons=sandbox_diagnostic_non_evidence" in loaded.output_refs
    assert any(ref.startswith("coverage_report_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("quality_check_ids=") for ref in loaded.archive_manifest_refs)
    assert reports[0].coverage_ratio == 1.0
    assert reports[0].source_row_count == 60
    assert {check.check_type for check in checks} == {
        "duplicate_timestamps",
        "zero_volume",
        "stale_segments",
        "return_outliers",
        "spread_outliers",
        "funding_outliers",
    }


def test_coverage_audit_worker_records_low_coverage_blockers_without_job_failure(tmp_path) -> None:
    archive_root = tmp_path / "archive-low-coverage"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-low-coverage-candles",
        input_spec={
            "archive_root": str(archive_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-low-coverage-candles",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
            "records": [_candle_row(index) for index in range(58)],
            "derive_timeframes": [],
            "skip_coverage": True,
        },
    )
    assert run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-low-coverage-candles",
    ) is not None
    silver_file_id = _silver_bars_file_id(archive_root, timeframe="1m")
    queued = store.enqueue(
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-low-coverage-audit",
        input_spec={
            "archive_root": str(archive_root),
            "silver_file_id": silver_file_id,
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
            "evidence_mode": "accepted_research",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.COVERAGE_AUDIT,
        worker_id="worker-low-coverage",
    )
    loaded = store.load_job(queued.job_id)
    report = CoverageManifestStore(ArchiveLayout(archive_root)).load_coverage_reports()[0]

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "coverage_ratio=0.966666666667" in loaded.output_refs
    assert "quality_status=fail" in loaded.output_refs
    assert "evidence_eligible=false" in loaded.output_refs
    assert "blocker_reasons=coverage_below_minimum" in loaded.output_refs
    assert report.blocker_reasons == ("coverage_below_minimum",)


def test_coverage_audit_worker_writes_timestamped_report_from_raw_trades_file(tmp_path) -> None:
    archive_root = tmp_path / "archive-raw-trade-coverage"
    capture = write_microstructure_raw_capture(
        archive_root=archive_root,
        records=[
            {
                "ts": "2026-01-01T00:00:00Z",
                "instrument_id": INSTRUMENT,
                "event_type": "trade",
                "sequence": 0,
                "price": 100.0,
                "size": 1.0,
            },
            {
                "ts": "2026-01-01T00:02:00Z",
                "instrument_id": INSTRUMENT,
                "event_type": "trade",
                "sequence": 2,
                "price": 101.0,
                "size": 1.5,
            },
        ],
        venue="hyperliquid",
        datatype="trades",
        date="2026-01-01",
        run_id="run-raw-trade-coverage",
        job_id="JOB-raw-trade-source",
        adapter_id="fixture_microstructure_v1",
        source_endpoint_or_subscription="fixture/trades",
        instrument_id=INSTRUMENT,
        start_ts=START,
        end_ts=START + timedelta(minutes=3),
        storage_budget_bytes=1_000_000,
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-raw-trade-coverage-audit",
        input_spec={
            "archive_root": str(archive_root),
            "file_id": capture.raw_file.file_id,
            "family": "trades",
            "timeframe": "1m",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:03:00+00:00",
            "evidence_mode": "accepted_research",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.COVERAGE_AUDIT,
        worker_id="worker-raw-trade-coverage",
    )
    loaded = store.load_job(queued.job_id)
    report = CoverageManifestStore(ArchiveLayout(archive_root)).load_coverage_reports()[0]

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "coverage_scope=timestamped_file" in loaded.output_refs
    assert "coverage_method=nonempty_time_buckets" in loaded.output_refs
    assert "source_layer=raw" in loaded.output_refs
    assert "source_datatype=trades" in loaded.output_refs
    assert "coverage_ratio=0.666666666667" in loaded.output_refs
    assert "quality_status=non_evidence" in loaded.output_refs
    assert "evidence_eligible=false" in loaded.output_refs
    assert (
        "blocker_reasons=coverage_below_minimum,raw_microstructure_not_accepted_coverage_evidence"
        in loaded.output_refs
    )
    assert report.family == "trades"
    assert report.expected_rows == 3
    assert report.observed_rows == 2
    assert report.evidence_eligible is False


def test_coverage_audit_worker_writes_timestamped_report_from_silver_asset_contexts(tmp_path) -> None:
    archive_root = tmp_path / "archive-asset-context-coverage"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_store = ArchiveManifestStore(layout)
    output = write_parquet_rows(
        layout=layout,
        store=manifest_store,
        rows=[
            {
                "venue": "hyperliquid",
                "instrument_id": INSTRUMENT,
                "ts": "2026-01-01T00:00:00Z",
                "mark_price": 100.0,
                "oracle_price": 100.0,
                "open_interest": 1_000_000.0,
                "day_notional_volume_usd": 10_000_000.0,
                "funding_rate": 0.0001,
                "source_file_id": "a" * 64,
                "source_layer": "bronze",
                "missing_fields": (),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            },
            {
                "venue": "hyperliquid",
                "instrument_id": INSTRUMENT,
                "ts": "2026-01-02T00:00:00Z",
                "mark_price": 101.0,
                "oracle_price": 101.0,
                "open_interest": 1_100_000.0,
                "day_notional_volume_usd": 11_000_000.0,
                "funding_rate": 0.0002,
                "source_file_id": "a" * 64,
                "source_layer": "bronze",
                "missing_fields": (),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            },
        ],
        layer=ArchiveLayer.SILVER,
        dataset="asset_contexts",
        venue="hyperliquid",
        datatype="asset_contexts",
        date="2026-01-01",
        job_id="job-silver-context-coverage",
        source_file_ids=("a" * 64,),
        instrument_id=INSTRUMENT,
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-context-coverage-audit",
        input_spec={
            "archive_root": str(archive_root),
            "file_id": output.file_id,
            "family": "asset_contexts",
            "timeframe": "1d",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-03T00:00:00+00:00",
            "evidence_mode": "accepted_research",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.COVERAGE_AUDIT,
        worker_id="worker-context-coverage",
    )
    loaded = store.load_job(queued.job_id)
    report = CoverageManifestStore(layout).load_coverage_reports()[0]

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "coverage_scope=timestamped_file" in loaded.output_refs
    assert "source_layer=silver" in loaded.output_refs
    assert "source_datatype=asset_contexts" in loaded.output_refs
    assert "coverage_ratio=1.000000000000" in loaded.output_refs
    assert "quality_status=pass" in loaded.output_refs
    assert "evidence_eligible=true" in loaded.output_refs
    assert "blocker_reasons=" in loaded.output_refs
    assert report.family == "asset_contexts"
    assert report.evidence_eligible is True
    assert report.blocker_reasons == ()


def test_coverage_audit_worker_audits_archive_snapshot_against_universe_snapshot(tmp_path) -> None:
    archive_root = tmp_path / "archive-universe-coverage"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_store = ArchiveManifestStore(layout)
    start_ts = START
    end_ts = START + timedelta(hours=1)
    write_parquet_rows(
        layout=layout,
        store=manifest_store,
        rows=[_candle_row(index) for index in range(60)],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date=start_ts.date().isoformat(),
        timeframe="1m",
        job_id="job-universe-coverage-btc-bars",
        source_file_ids=("source-universe-coverage-btc",),
        instrument_id=INSTRUMENT,
    )
    universe = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_universe_payload(),
        asof_date=start_ts.date(),
        mode=UniverseMode.AS_OF,
    )
    snapshot = create_archive_snapshot(
        store=manifest_store,
        layer=ArchiveLayer.SILVER,
        venue_scope="hyperliquid",
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=(),
        quality_rows=(),
        notes="worker_universe_coverage_fixture",
    )
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-universe-coverage-audit",
        input_spec={
            "archive_root": str(archive_root),
            "archive_snapshot_id": snapshot.archive_snapshot_id,
            "universe_snapshot_id": universe.snapshot_id,
            "timeframe": "1m",
            "start_ts": start_ts.isoformat(),
            "end_ts": end_ts.isoformat(),
            "evidence_mode": "accepted_research",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.COVERAGE_AUDIT,
        worker_id="worker-universe-coverage",
    )
    loaded = store.load_job(queued.job_id)
    reports = CoverageManifestStore(layout).load_coverage_reports()
    report_by_instrument = {report.instrument_id: report for report in reports}

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "coverage_scope=universe_snapshot" in loaded.output_refs
    assert f"archive_snapshot_id={snapshot.archive_snapshot_id}" in loaded.output_refs
    assert f"universe_snapshot_id={universe.snapshot_id}" in loaded.output_refs
    assert "instrument_count=2" in loaded.output_refs
    assert "audited_instrument_count=2" in loaded.output_refs
    assert "missing_file_instrument_count=1" in loaded.output_refs
    assert "missing_file_instruments=hyperliquid:perp:SOL" in loaded.output_refs
    assert "min_coverage_ratio=0.000000000000" in loaded.output_refs
    assert "evidence_eligible_count=1" in loaded.output_refs
    assert "blocked_instrument_count=1" in loaded.output_refs
    assert "blocker_reasons=coverage_below_minimum,missing_silver_bars_file" in loaded.output_refs
    assert any(ref.startswith("coverage_report_ids=") for ref in loaded.archive_manifest_refs)
    assert set(report_by_instrument) == {INSTRUMENT, "hyperliquid:perp:SOL"}
    assert report_by_instrument[INSTRUMENT].coverage_ratio == 1.0
    assert report_by_instrument[INSTRUMENT].evidence_eligible is True
    sol_report = report_by_instrument["hyperliquid:perp:SOL"]
    assert sol_report.source_row_count == 0
    assert sol_report.coverage_ratio == 0.0
    assert sol_report.evidence_eligible is False
    assert sol_report.blocker_reasons == ("coverage_below_minimum",)


def test_coverage_audit_worker_audits_raw_trade_snapshot_against_universe_snapshot(tmp_path) -> None:
    archive_root = tmp_path / "archive-universe-trade-coverage"
    layout = ArchiveLayout(archive_root)
    capture = write_microstructure_raw_capture(
        archive_root=archive_root,
        records=[
            {
                "ts": "2026-01-01T00:00:00Z",
                "instrument_id": INSTRUMENT,
                "event_type": "trade",
                "sequence": 0,
                "price": 100.0,
                "size": 1.0,
            },
            {
                "ts": "2026-01-01T00:01:00Z",
                "instrument_id": INSTRUMENT,
                "event_type": "trade",
                "sequence": 1,
                "price": 101.0,
                "size": 1.0,
            },
        ],
        venue="hyperliquid",
        datatype="trades",
        date="2026-01-01",
        run_id="run-universe-trade-coverage",
        job_id="JOB-universe-trade-source",
        adapter_id="fixture_microstructure_v1",
        source_endpoint_or_subscription="fixture/trades",
        instrument_id=INSTRUMENT,
        start_ts=START,
        end_ts=START + timedelta(minutes=2),
        storage_budget_bytes=1_000_000,
    )
    manifest_store = ArchiveManifestStore(layout)
    universe = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_universe_payload(),
        asof_date=START.date(),
        mode=UniverseMode.AS_OF,
    )
    snapshot = create_archive_snapshot(
        store=manifest_store,
        layer=ArchiveLayer.RAW,
        venue_scope="hyperliquid",
        start_ts=START,
        end_ts=START + timedelta(minutes=2),
        coverage_rows=(),
        quality_rows=(),
        notes="worker_universe_trade_coverage_fixture",
    )
    assert capture.raw_file.file_id in snapshot.included_file_ids
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-universe-trade-coverage-audit",
        input_spec={
            "archive_root": str(archive_root),
            "archive_snapshot_id": snapshot.archive_snapshot_id,
            "universe_snapshot_id": universe.snapshot_id,
            "family": "trades",
            "timeframe": "1m",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:02:00+00:00",
            "evidence_mode": "accepted_research",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.COVERAGE_AUDIT,
        worker_id="worker-universe-trade-coverage",
    )
    loaded = store.load_job(queued.job_id)
    reports = CoverageManifestStore(layout).load_coverage_reports()
    report_by_instrument = {report.instrument_id: report for report in reports}

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "coverage_scope=universe_snapshot" in loaded.output_refs
    assert "coverage_method=nonempty_time_buckets" in loaded.output_refs
    assert "source_layer=raw" in loaded.output_refs
    assert "source_datatype=trades" in loaded.output_refs
    assert "missing_file_instrument_count=1" in loaded.output_refs
    assert "missing_file_instruments=hyperliquid:perp:SOL" in loaded.output_refs
    assert "evidence_eligible_count=0" in loaded.output_refs
    assert "blocked_instrument_count=2" in loaded.output_refs
    assert (
        "blocker_reasons=coverage_below_minimum,missing_raw_trades_file,"
        "raw_microstructure_not_accepted_coverage_evidence"
    ) in loaded.output_refs
    assert set(report_by_instrument) == {INSTRUMENT, "hyperliquid:perp:SOL"}
    btc_report = report_by_instrument[INSTRUMENT]
    assert btc_report.coverage_ratio == 1.0
    assert btc_report.evidence_eligible is False
    assert btc_report.blocker_reasons == ("raw_microstructure_not_accepted_coverage_evidence",)
    sol_report = report_by_instrument["hyperliquid:perp:SOL"]
    assert sol_report.source_row_count == 0
    assert sol_report.coverage_ratio == 0.0
    assert sol_report.evidence_eligible is False
    assert set(sol_report.blocker_reasons) == {
        "coverage_below_minimum",
        "raw_microstructure_not_accepted_coverage_evidence",
    }


def test_coverage_audit_worker_rejects_non_silver_bars_file_without_report_write(tmp_path) -> None:
    archive_root = tmp_path / "archive-coverage-reject"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-raw-for-coverage-reject",
        input_spec={
            "archive_root": str(archive_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-raw-for-coverage-reject",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "records": [_candle_row(0)],
            "derive_timeframes": [],
            "skip_coverage": True,
        },
    )
    candle_result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-raw-for-coverage-reject",
    )
    assert candle_result is not None
    raw_file_id = _ref_value(candle_result.archive_manifest_refs, "raw_file_id")
    queued = store.enqueue(
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-coverage-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "file_id": raw_file_id,
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.COVERAGE_AUDIT,
        worker_id="worker-coverage-reject",
    )
    loaded = store.load_job(queued.job_id)
    coverage_store = CoverageManifestStore(ArchiveLayout(archive_root))

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "requires a silver bars archive file" in (loaded.failure_reason or "")
    assert coverage_store.load_coverage_reports() == []
    assert coverage_store.load_quality_checks() == []


def test_vectorized_backtest_worker_loads_archive_panel_and_writes_run_artifacts(tmp_path) -> None:
    fixture = _backtest_archive_fixture(tmp_path)
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.VECTORIZED_BACKTEST,
        job_id="JOB-vectorized-backtest",
        input_spec={
            "archive_root": str(fixture.archive_root),
            "output_root": str(tmp_path / "runs"),
            "run_id": "worker-vectorized-run",
            "experiment_id": "phase7-worker-backtest",
            "archive_snapshot_id": fixture.archive_snapshot_id,
            "universe_snapshot_id": fixture.universe_snapshot_id,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1d",
            "start_ts": "2024-01-01T00:00:00+00:00",
            "end_ts": "2024-07-01T00:00:00+00:00",
            "asof_date": "2026-06-21",
            "evidence_mode": "accepted_research",
            "strategy_spec": _worker_backtest_strategy_spec(),
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.VECTORIZED_BACKTEST,
        worker_id="worker-backtest",
    )
    loaded = store.load_job(queued.job_id)
    run_dir = tmp_path / "runs" / "worker-vectorized-run"
    run_manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    cost_stress = pq.read_table(run_dir / "cost_stress.parquet").to_pylist()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "job_kind=vectorized_backtest" in loaded.output_refs
    assert "engine_lane=vectorized" in loaded.output_refs
    assert "run_status=succeeded" in loaded.output_refs
    assert "run_id=worker-vectorized-run" in loaded.output_refs
    assert any(ref.startswith("run_manifest_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("data_manifest_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("coverage_report_id=") for ref in loaded.archive_manifest_refs)
    assert run_manifest["status"] == "succeeded"
    assert run_manifest["archive_snapshot_id"] == fixture.archive_snapshot_id
    assert run_manifest["universe_snapshot_id"] == fixture.universe_snapshot_id
    assert run_manifest["research_only"] is True
    assert run_manifest["promotion_ready"] is False
    assert {row["scenario_id"] for row in cost_stress} == {"base", "stress_2x", "stress_3x"}


def test_vectorized_backtest_worker_rejects_invalid_strategy_spec_before_run(tmp_path) -> None:
    fixture = _backtest_archive_fixture(tmp_path)
    bad_spec = _worker_backtest_strategy_spec()
    bad_spec["live_signal"] = True
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.VECTORIZED_BACKTEST,
        job_id="JOB-vectorized-backtest-bad-spec",
        max_attempts=1,
        input_spec={
            "archive_root": str(fixture.archive_root),
            "output_root": str(tmp_path / "runs"),
            "run_id": "worker-vectorized-bad-spec",
            "archive_snapshot_id": fixture.archive_snapshot_id,
            "universe_snapshot_id": fixture.universe_snapshot_id,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1d",
            "start_ts": "2024-01-01T00:00:00+00:00",
            "end_ts": "2024-07-01T00:00:00+00:00",
            "asof_date": "2026-06-21",
            "evidence_mode": "accepted_research",
            "strategy_spec": bad_spec,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.VECTORIZED_BACKTEST,
        worker_id="worker-backtest-bad-spec",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "strategy_spec_validation_failed" in (loaded.failure_reason or "")
    assert not (tmp_path / "runs" / "worker-vectorized-bad-spec" / "run_manifest.json").exists()


def test_ledger_append_export_worker_records_backtest_run_and_generated_exports(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    run_manifest_path = _worker_backtest_run_manifest(
        tmp_path,
        store=store,
        job_id="JOB-backtest-for-ledger",
        run_id="worker-ledger-source-run",
    )
    ledger_path = tmp_path / "ledger" / "experiment_ledger.parquet"
    csv_path = tmp_path / "ledger" / "experiment_ledger.csv"
    xlsx_path = tmp_path / "ledger" / "experiment_ledger.xlsx"
    queued = store.enqueue(
        kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
        job_id="JOB-ledger-append-export",
        input_spec={
            "run_manifest_path": str(run_manifest_path),
            "ledger_path": str(ledger_path),
            "evidence_mode": "accepted_research",
            "notes": "worker ledger append/export smoke",
            "export_csv_path": str(csv_path),
            "export_xlsx_path": str(xlsx_path),
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
        worker_id="worker-ledger",
    )
    loaded = store.load_job(queued.job_id)
    rows = read_ledger(ledger_path)

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "job_kind=ledger_append_export" in loaded.output_refs
    assert "run_id=worker-ledger-source-run" in loaded.output_refs
    assert "row_status=succeeded" in loaded.output_refs
    assert any(ref.startswith("row_hash=") for ref in loaded.output_refs)
    assert any(ref.startswith("ledger_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("export_csv_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("export_xlsx_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("archive_snapshot_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("universe_snapshot_id=") for ref in loaded.archive_manifest_refs)
    assert len(rows) == 1
    assert rows[0].run_id == "worker-ledger-source-run"
    assert rows[0].evidence_mode == "accepted_research"
    assert rows[0].research_only is True
    assert rows[0].promotion_ready is False
    assert csv_path.exists()
    assert xlsx_path.exists()


def test_ledger_append_export_worker_rejects_secret_like_ledger_path_before_write(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    run_manifest_path = _worker_backtest_run_manifest(
        tmp_path,
        store=store,
        job_id="JOB-backtest-for-ledger-reject",
        run_id="worker-ledger-reject-source-run",
    )
    queued = store.enqueue(
        kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
        job_id="JOB-ledger-reject-secret-path",
        max_attempts=1,
        input_spec={
            "run_manifest_path": str(run_manifest_path),
            "ledger_path": str(tmp_path / ".env"),
            "evidence_mode": "accepted_research",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
        worker_id="worker-ledger-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "reserved for secrets or local state" in (loaded.failure_reason or "")
    assert not (tmp_path / ".env").exists()


def test_lead_book_upsert_worker_records_ledger_backed_non_promotable_lead(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    run_manifest_path = _worker_backtest_run_manifest(
        tmp_path,
        store=store,
        job_id="JOB-backtest-for-lead-book",
        run_id="worker-lead-book-source-run",
    )
    ledger_path = tmp_path / "ledger" / "experiment_ledger.parquet"
    store.enqueue(
        kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
        job_id="JOB-ledger-for-lead-book",
        input_spec={
            "run_manifest_path": str(run_manifest_path),
            "ledger_path": str(ledger_path),
            "evidence_mode": "accepted_research",
            "notes": "source row for durable Lead Book worker smoke",
        },
    )
    ledger_result = run_one_job(
        store=store,
        kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
        worker_id="worker-ledger-for-lead-book",
    )
    assert ledger_result is not None
    assert ledger_result.status == WorkerJobStatus.SUCCEEDED
    ledger_row = read_ledger(ledger_path)[0]
    lead_book_path = tmp_path / "lead-book" / "lead_book.parquet"
    lead_csv_path = tmp_path / "lead-book" / "lead_book.csv"
    queued = store.enqueue(
        kind=WorkerJobKind.LEAD_BOOK_UPSERT,
        job_id="JOB-lead-book-upsert",
        input_spec={
            "lead_book_path": str(lead_book_path),
            "source_artifact_path": str(ledger_path),
            "source_type": "ledger_row",
            "strategy_family": ledger_row.strategy_id,
            "economic_thesis": "ledger-backed mean reversion row merits human inspection",
            "created_by_id": "worker-agent",
            "instrument_scope": [INSTRUMENT],
            "data_window_start": "2024-01-01T00:00:00Z",
            "data_window_end": "2024-08-01T00:00:00Z",
            "roi_observed": ledger_row.roi_observed,
            "roi_projected": 0.0,
            "roi_projection_assumptions": "projection is a placeholder for triage, not a claim",
            "roi_projection_confidence": "low",
            "why_interesting": "accepted-research ledger row has complete source provenance for follow-up triage",
            "trade_count_summary": {"avg_trades_per_month": 6.0, "total_trades": 42},
            "monthly_stability_summary": {
                "usable_months": 7,
                "losing_months_12m": 2,
                "positive_months_12m": 5,
            },
            "pnl_concentration_summary": {
                "top_2_trades_profit_share": 0.2,
                "best_month_profit_share": 0.2,
            },
            "known_blockers": ["human_inspection_required_before_deep_validation"],
            "missing_evidence": ["independent_agent_audit_required"],
            "required_next_validation": ["human_inspection", "deep_validation"],
            "export_csv_path": str(lead_csv_path),
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.LEAD_BOOK_UPSERT,
        worker_id="worker-lead-book",
    )
    loaded = store.load_job(queued.job_id)
    leads = LeadBookStore(lead_book_path).read()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "job_kind=lead_book_upsert" in loaded.output_refs
    assert any(ref.startswith("lead_id=") for ref in loaded.output_refs)
    assert "lead_state=idea_only" in loaded.output_refs
    assert "promotion_ready=false" in loaded.output_refs
    assert "candidate_evidence=false" in loaded.output_refs
    assert any(ref.startswith("lead_book_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("export_csv_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("source_artifact_sha256=") for ref in loaded.archive_manifest_refs)
    assert len(leads) == 1
    assert leads[0].source_artifact_path == str(ledger_path.resolve())
    assert leads[0].source_artifact_sha256 == file_sha256(ledger_path)
    assert leads[0].promotion_ready is False
    assert leads[0].candidate_evidence is False
    assert leads[0].human_inspection_status.value == "not_requested"
    assert "lead_not_candidate" in leads[0].non_promotable_flags
    assert lead_csv_path.exists()


def test_lead_book_upsert_worker_rejects_secret_like_output_before_write(tmp_path) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"source":"lead"}\n', encoding="utf-8")
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.LEAD_BOOK_UPSERT,
        job_id="JOB-lead-book-secret-reject",
        max_attempts=1,
        input_spec={
            "lead_book_path": str(tmp_path / ".env"),
            "source_artifact_path": str(source),
            "source_type": "ledger_row",
            "strategy_family": "mean_reversion",
            "economic_thesis": "secret path rejection smoke",
            "created_by_id": "worker-agent",
            "roi_observed": 0.1,
            "roi_projected": 0.0,
            "roi_projection_assumptions": "not a claim",
            "why_interesting": "path guard regression",
            "trade_count_summary": {"avg_trades_per_month": 6.0, "total_trades": 36},
            "monthly_stability_summary": {"usable_months": 6, "losing_months_12m": 1},
            "pnl_concentration_summary": {
                "top_2_trades_profit_share": 0.2,
                "best_month_profit_share": 0.2,
            },
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.LEAD_BOOK_UPSERT,
        worker_id="worker-lead-book-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "reserved for secrets or local state" in (loaded.failure_reason or "")
    assert not (tmp_path / ".env").exists()


def test_lead_book_upsert_worker_rejects_boundary_override_before_write(tmp_path) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"source":"lead"}\n', encoding="utf-8")
    lead_book_path = tmp_path / "lead-book" / "lead_book.parquet"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.LEAD_BOOK_UPSERT,
        job_id="JOB-lead-book-boundary-reject",
        max_attempts=1,
        input_spec={
            "lead_book_path": str(lead_book_path),
            "source_artifact_path": str(source),
            "source_type": "ledger_row",
            "strategy_family": "mean_reversion",
            "economic_thesis": "boundary override rejection smoke",
            "created_by_id": "worker-agent",
            "roi_observed": 0.1,
            "roi_projected": 0.0,
            "roi_projection_assumptions": "not a claim",
            "why_interesting": "boundary guard regression",
            "trade_count_summary": {"avg_trades_per_month": 6.0, "total_trades": 36},
            "monthly_stability_summary": {"usable_months": 6, "losing_months_12m": 1},
            "pnl_concentration_summary": {
                "top_2_trades_profit_share": 0.2,
                "best_month_profit_share": 0.2,
            },
            "promotion_ready": False,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.LEAD_BOOK_UPSERT,
        worker_id="worker-lead-book-boundary-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "must not override boundary fields" in (loaded.failure_reason or "")
    assert not lead_book_path.exists()


def test_audit_check_worker_writes_blocker_report_from_job_store(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    failed_source = store.enqueue(
        kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
        job_id="JOB-audit-source-failed-ledger",
        max_attempts=1,
        input_spec={
            "run_manifest_path": str(tmp_path / "missing" / "run_manifest.json"),
            "ledger_path": str(tmp_path / "ledger" / "experiment_ledger.parquet"),
            "evidence_mode": "accepted_research",
        },
    )
    failed_result = run_one_job(
        store=store,
        kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
        worker_id="worker-audit-source-failed-ledger",
    )
    assert failed_result is not None
    assert failed_result.status == WorkerJobStatus.FAILED
    blocker_ref_source = store.enqueue(
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-audit-source-blocker-refs",
        input_spec={"purpose": "manual blocker-ref audit source"},
    )
    claimed = store.claim_next(kind=WorkerJobKind.COVERAGE_AUDIT, worker_id="worker-audit-source-blocker-refs")
    assert claimed is not None
    running = store.start_job(claimed.job_id, worker_id="worker-audit-source-blocker-refs")
    store.succeed_job(
        running.job_id,
        worker_id="worker-audit-source-blocker-refs",
        output_refs=(
            "blocker_reasons=coverage_below_minimum",
            "known_blockers=human_inspection_required_before_deep_validation",
            "missing_evidence=accepted_research_coverage_manifest",
        ),
        reason="manual_blocker_ref_source_succeeded",
    )
    report_path = tmp_path / "audit" / "blocker_report.json"
    queued = store.enqueue(
        kind=WorkerJobKind.AUDIT_CHECK,
        job_id="JOB-audit-check",
        input_spec={
            "run_id": "worker-audit-check-smoke",
            "report_path": str(report_path),
            "target_job_ids": [failed_source.job_id, blocker_ref_source.job_id, "JOB-missing-target"],
            "extra_blocker_reasons": ["real_hyperliquid_archive_operation_required"],
            "required_next_actions": ["fix_failed_ledger_job", "rerun_audit_check"],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.AUDIT_CHECK,
        worker_id="worker-audit-check",
    )
    loaded = store.load_job(queued.job_id)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "job_kind=audit_check" in loaded.output_refs
    assert "report_status=completed_with_blockers" in loaded.output_refs
    assert "accepted_research_ready=false" in loaded.output_refs
    assert any(ref.startswith("report_sha256=") for ref in loaded.output_refs)
    assert any(ref.startswith("audited_job_count=2") for ref in loaded.archive_manifest_refs)
    assert report["schema_version"] == "audit_blocker_report_v1"
    assert report["status"] == "completed_with_blockers"
    assert report["accepted_research_ready"] is False
    assert report["research_only"] is True
    assert report["promotion_ready"] is False
    assert report["audited_job_ids"] == [failed_source.job_id, blocker_ref_source.job_id]
    assert report["job_status_counts"] == {"failed": 1, "succeeded": 1}
    assert "real_hyperliquid_archive_operation_required" in report["blocker_reasons"]
    assert "target_job_missing:JOB-missing-target" in report["blocker_reasons"]
    assert "coverage_below_minimum" in report["blocker_reasons"]
    assert "human_inspection_required_before_deep_validation" in report["blocker_reasons"]
    assert "missing_evidence:accepted_research_coverage_manifest" in report["blocker_reasons"]
    assert any(
        reason.startswith("job_failed:JOB-audit-source-failed-ledger:")
        for reason in report["blocker_reasons"]
    )
    assert report["required_next_actions"] == ["fix_failed_ledger_job", "rerun_audit_check"]
    assert report["job_summaries"][0]["job_id"] == failed_source.job_id
    assert report["job_summaries"][0]["status"] == "failed"


def test_audit_check_worker_blocks_missing_required_loop_evidence(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    universe = _succeed_worker_job_for_audit(
        store,
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        job_id="JOB-required-universe",
        output_refs=("universe_snapshot_id=UNIV-1",),
        archive_manifest_refs=("universe_snapshot_id=UNIV-1",),
    )
    backtest = _succeed_worker_job_for_audit(
        store,
        kind=WorkerJobKind.VECTORIZED_BACKTEST,
        job_id="JOB-required-backtest",
        output_refs=(
            "run_manifest_path=C:/tmp/run_manifest.json",
            "archive_snapshot_id=ARCH-1",
            "universe_snapshot_id=UNIV-1",
        ),
        archive_manifest_refs=("archive_snapshot_id=ARCH-1",),
    )
    report_path = tmp_path / "audit" / "required_loop_report.json"
    queued = store.enqueue(
        kind=WorkerJobKind.AUDIT_CHECK,
        job_id="JOB-audit-required-loop-missing",
        input_spec={
            "run_id": "required-loop-missing",
            "report_path": str(report_path),
            "target_job_ids": [universe.job_id, backtest.job_id],
            "required_successful_job_kinds": [
                "universe_refresh",
                "coverage_audit",
                "vectorized_backtest",
                "ledger_append_export",
                "lead_book_upsert",
            ],
            "required_artifact_ref_prefixes": [
                "archive_snapshot_id=",
                "coverage_report_ids=",
                "ledger_path=",
                "lead_book_path=",
            ],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.AUDIT_CHECK,
        worker_id="worker-audit-required-loop-missing",
    )
    loaded = store.load_job(queued.job_id)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "report_status=completed_with_blockers" in loaded.output_refs
    assert (
        "required_successful_job_kinds=universe_refresh,coverage_audit,vectorized_backtest,ledger_append_export,lead_book_upsert"
        in loaded.output_refs
    )
    assert (
        "required_artifact_ref_prefixes=archive_snapshot_id=,coverage_report_ids=,ledger_path=,lead_book_path="
        in loaded.output_refs
    )
    assert report["status"] == "completed_with_blockers"
    assert report["required_successful_job_kinds"] == [
        "universe_refresh",
        "coverage_audit",
        "vectorized_backtest",
        "ledger_append_export",
        "lead_book_upsert",
    ]
    assert report["required_artifact_ref_prefixes"] == [
        "archive_snapshot_id=",
        "coverage_report_ids=",
        "ledger_path=",
        "lead_book_path=",
    ]
    assert "missing_evidence:successful_job_kind:coverage_audit" in report["blocker_reasons"]
    assert "missing_evidence:successful_job_kind:ledger_append_export" in report["blocker_reasons"]
    assert "missing_evidence:successful_job_kind:lead_book_upsert" in report["blocker_reasons"]
    assert "missing_evidence:artifact_ref_prefix:coverage_report_ids=" in report["blocker_reasons"]
    assert "missing_evidence:artifact_ref_prefix:ledger_path=" in report["blocker_reasons"]
    assert "missing_evidence:artifact_ref_prefix:lead_book_path=" in report["blocker_reasons"]
    assert "missing_evidence:successful_job_kind:universe_refresh" not in report["blocker_reasons"]
    assert "missing_evidence:successful_job_kind:vectorized_backtest" not in report["blocker_reasons"]
    assert "missing_evidence:artifact_ref_prefix:archive_snapshot_id=" not in report["blocker_reasons"]
    assert report["accepted_research_ready"] is False


def test_audit_check_worker_passes_when_required_loop_evidence_is_present(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    jobs = [
        _succeed_worker_job_for_audit(
            store,
            kind=WorkerJobKind.UNIVERSE_REFRESH,
            job_id="JOB-loop-universe",
            output_refs=("universe_snapshot_id=UNIV-2",),
            archive_manifest_refs=("universe_snapshot_id=UNIV-2",),
            finished_at=START,
        ),
        _succeed_worker_job_for_audit(
            store,
            kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
            job_id="JOB-loop-candles",
            output_refs=("collector_mode=fixture_candle_archive_write",),
            archive_manifest_refs=("archive_snapshot_id=ARCH-2", "silver_file_ids=SILVER-2"),
            finished_at=START + timedelta(minutes=1),
        ),
        _succeed_worker_job_for_audit(
            store,
            kind=WorkerJobKind.COVERAGE_AUDIT,
            job_id="JOB-loop-coverage",
            output_refs=("coverage_report_ids=COV-2",),
            archive_manifest_refs=("coverage_report_ids=COV-2",),
            finished_at=START + timedelta(minutes=2),
        ),
        _succeed_worker_job_for_audit(
            store,
            kind=WorkerJobKind.VECTORIZED_BACKTEST,
            job_id="JOB-loop-backtest",
            output_refs=(
                "run_manifest_path=C:/tmp/run_manifest.json",
                "archive_snapshot_id=ARCH-2",
                "universe_snapshot_id=UNIV-2",
            ),
            archive_manifest_refs=("archive_snapshot_id=ARCH-2",),
            finished_at=START + timedelta(minutes=3),
        ),
        _succeed_worker_job_for_audit(
            store,
            kind=WorkerJobKind.LEDGER_APPEND_EXPORT,
            job_id="JOB-loop-ledger",
            output_refs=("ledger_path=C:/tmp/ledger.parquet",),
            archive_manifest_refs=("ledger_path=C:/tmp/ledger.parquet",),
            finished_at=START + timedelta(minutes=4),
        ),
        _succeed_worker_job_for_audit(
            store,
            kind=WorkerJobKind.LEAD_BOOK_UPSERT,
            job_id="JOB-loop-lead-book",
            output_refs=("lead_book_path=C:/tmp/lead_book.parquet",),
            archive_manifest_refs=("lead_book_path=C:/tmp/lead_book.parquet",),
            finished_at=START + timedelta(minutes=5),
        ),
    ]
    required_order = [
        "universe_refresh",
        "recent_candle_bootstrap",
        "coverage_audit",
        "vectorized_backtest",
        "ledger_append_export",
        "lead_book_upsert",
    ]
    report_path = tmp_path / "audit" / "required_loop_pass_report.json"
    queued = store.enqueue(
        kind=WorkerJobKind.AUDIT_CHECK,
        job_id="JOB-audit-required-loop-pass",
        input_spec={
            "run_id": "required-loop-pass",
            "report_path": str(report_path),
            "target_job_ids": [record.job_id for record in jobs],
            "required_successful_job_kinds": required_order,
            "required_job_kind_order": required_order,
            "required_artifact_ref_prefixes": [
                "universe_snapshot_id=",
                "archive_snapshot_id=",
                "coverage_report_ids=",
                "run_manifest_path=",
                "ledger_path=",
                "lead_book_path=",
            ],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.AUDIT_CHECK,
        worker_id="worker-audit-required-loop-pass",
    )
    loaded = store.load_job(queued.job_id)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "report_status=pass" in loaded.output_refs
    assert (
        "required_job_kind_order=universe_refresh,recent_candle_bootstrap,coverage_audit,vectorized_backtest,ledger_append_export,lead_book_upsert"
        in loaded.output_refs
    )
    assert report["status"] == "pass"
    assert report["accepted_research_ready"] is False
    assert report["blocker_reasons"] == []
    assert report["required_successful_job_kinds"] == required_order
    assert report["required_job_kind_order"] == required_order
    assert report["required_artifact_ref_prefixes"] == [
        "universe_snapshot_id=",
        "archive_snapshot_id=",
        "coverage_report_ids=",
        "run_manifest_path=",
        "ledger_path=",
        "lead_book_path=",
    ]
    assert report["required_next_actions"] == [
        "independent_completion_audit_required_before_autonomous_ready"
    ]


def test_audit_check_worker_blocks_required_loop_order_violation(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    coverage = _succeed_worker_job_for_audit(
        store,
        kind=WorkerJobKind.COVERAGE_AUDIT,
        job_id="JOB-loop-order-coverage-first",
        output_refs=("coverage_report_ids=COV-ORDER",),
        archive_manifest_refs=("coverage_report_ids=COV-ORDER",),
        finished_at=START,
    )
    universe = _succeed_worker_job_for_audit(
        store,
        kind=WorkerJobKind.UNIVERSE_REFRESH,
        job_id="JOB-loop-order-universe-second",
        output_refs=("universe_snapshot_id=UNIV-ORDER",),
        archive_manifest_refs=("universe_snapshot_id=UNIV-ORDER",),
        finished_at=START + timedelta(minutes=1),
    )
    report_path = tmp_path / "audit" / "required_loop_order_violation_report.json"
    queued = store.enqueue(
        kind=WorkerJobKind.AUDIT_CHECK,
        job_id="JOB-audit-required-loop-order-violation",
        input_spec={
            "run_id": "required-loop-order-violation",
            "report_path": str(report_path),
            "target_job_ids": [coverage.job_id, universe.job_id],
            "required_job_kind_order": [
                "universe_refresh",
                "coverage_audit",
            ],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.AUDIT_CHECK,
        worker_id="worker-audit-required-loop-order-violation",
    )
    loaded = store.load_job(queued.job_id)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "report_status=completed_with_blockers" in loaded.output_refs
    assert "required_job_kind_order=universe_refresh,coverage_audit" in loaded.output_refs
    assert report["status"] == "completed_with_blockers"
    assert report["required_job_kind_order"] == ["universe_refresh", "coverage_audit"]
    assert "loop_order_violation:universe_refresh_after_coverage_audit" in report["blocker_reasons"]
    assert "missing_evidence:loop_order_job_kind:universe_refresh" not in report["blocker_reasons"]
    assert "missing_evidence:loop_order_job_kind:coverage_audit" not in report["blocker_reasons"]
    assert report["accepted_research_ready"] is False


def test_audit_check_worker_rejects_unknown_required_job_kind_before_write(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    report_path = tmp_path / "audit" / "bad_required_kind_report.json"
    queued = store.enqueue(
        kind=WorkerJobKind.AUDIT_CHECK,
        job_id="JOB-audit-required-kind-reject",
        max_attempts=1,
        input_spec={
            "report_path": str(report_path),
            "required_successful_job_kinds": ["paper_live_worker"],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.AUDIT_CHECK,
        worker_id="worker-audit-required-kind-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "unsupported required_successful_job_kinds value" in (loaded.failure_reason or "")
    assert not report_path.exists()


def test_audit_check_worker_rejects_unknown_required_job_order_before_write(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    report_path = tmp_path / "audit" / "bad_required_order_report.json"
    queued = store.enqueue(
        kind=WorkerJobKind.AUDIT_CHECK,
        job_id="JOB-audit-required-order-reject",
        max_attempts=1,
        input_spec={
            "report_path": str(report_path),
            "required_job_kind_order": ["paper_live_worker"],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.AUDIT_CHECK,
        worker_id="worker-audit-required-order-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "unsupported required_job_kind_order value" in (loaded.failure_reason or "")
    assert not report_path.exists()


def test_audit_check_worker_rejects_secret_like_report_path_before_write(tmp_path) -> None:
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.AUDIT_CHECK,
        job_id="JOB-audit-check-secret-reject",
        max_attempts=1,
        input_spec={
            "report_path": str(tmp_path / ".env"),
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.AUDIT_CHECK,
        worker_id="worker-audit-check-secret-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "reserved for secrets or local state" in (loaded.failure_reason or "")
    assert not (tmp_path / ".env").exists()


def test_recent_candle_bootstrap_worker_reads_trusted_jsonl_records_file(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-source"
    trusted_root.mkdir()
    records_file = trusted_root / "btc-candles.jsonl"
    records_file.write_text(
        "\n".join(json.dumps(_candle_row(index)) for index in range(60)),
        encoding="utf-8",
    )
    archive_root = tmp_path / "archive-candles-file"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-candles-file",
        input_spec={
            "archive_root": str(archive_root),
            "trusted_source_root": str(trusted_root),
            "records_file": records_file.name,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-candles-file",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
            "derive_timeframes": ["5m"],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-candles-file",
    )
    loaded = store.load_job(queued.job_id)
    manifest_rows = ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "records_source=records_file" in loaded.output_refs
    assert "records_file_row_count=60" in loaded.output_refs
    assert any(ref.startswith("records_file_sha256=") for ref in loaded.output_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "candles"),
        (ArchiveLayer.BRONZE, "candles"),
        (ArchiveLayer.SILVER, "bars"),
    }


def test_funding_backfill_worker_reads_trusted_json_records_file(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-source"
    trusted_root.mkdir()
    records_file = trusted_root / "btc-funding.json"
    records_file.write_text(
        json.dumps(
            [
                {
                    "ts": "2026-01-01T00:00:00Z",
                    "end_ts": "2026-01-01T01:00:00Z",
                    "instrument_id": INSTRUMENT,
                    "fundingRate": "0.0001",
                }
            ]
        ),
        encoding="utf-8",
    )
    archive_root = tmp_path / "archive-funding-file"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.FUNDING_BACKFILL,
        job_id="JOB-funding-file",
        input_spec={
            "archive_root": str(archive_root),
            "trusted_source_root": str(trusted_root),
            "records_file": records_file.name,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "run_id": "run-funding-file",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.FUNDING_BACKFILL,
        worker_id="worker-funding-file",
    )
    loaded = store.load_job(queued.job_id)
    manifest_rows = ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "records_source=records_file" in loaded.output_refs
    assert "records_file_row_count=1" in loaded.output_refs
    assert any(ref.startswith("records_file_sha256=") for ref in loaded.output_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "funding"),
        (ArchiveLayer.BRONZE, "funding"),
        (ArchiveLayer.SILVER, "funding"),
    }


@pytest.mark.parametrize(
    ("records_file", "expected_reason"),
    [
        ("../escape.jsonl", "path escapes configured root"),
        (".env", "reserved for secrets"),
        ("payload.zip", "unsafe extension"),
    ],
)
def test_collector_records_file_rejects_untrusted_or_unsafe_sources(
    tmp_path,
    records_file: str,
    expected_reason: str,
) -> None:
    trusted_root = tmp_path / "trusted-source"
    trusted_root.mkdir()
    (trusted_root / ".env").write_text("TOKEN=must-not-enter-archive", encoding="utf-8")
    (trusted_root / "payload.zip").write_bytes(b"not-json")
    (tmp_path / "escape.jsonl").write_text(json.dumps(_candle_row(0)), encoding="utf-8")
    archive_root = tmp_path / "archive-reject"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id=f"JOB-reject-{records_file.replace('.', 'dot').replace('/', '-')}",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "trusted_source_root": str(trusted_root),
            "records_file": records_file,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-reject",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert expected_reason in (loaded.failure_reason or "")
    assert ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest() == []


def test_collector_records_file_rejects_invalid_record_shape_before_archive_write(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-source"
    trusted_root.mkdir()
    records_file = trusted_root / "bad-candles.json"
    records_file.write_text(
        json.dumps([{"ts": "2026-01-01T00:00:00Z"}, "not-an-object"]),
        encoding="utf-8",
    )
    archive_root = tmp_path / "archive-bad-shape"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        job_id="JOB-bad-record-shape",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "trusted_source_root": str(trusted_root),
            "records_file": records_file.name,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-bad-shape",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        worker_id="worker-bad-shape",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "collector records_file[1] must be an object" in (loaded.failure_reason or "")
    assert ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest() == []


def test_websocket_candle_batch_worker_writes_archive_layers_and_coverage(tmp_path) -> None:
    archive_root = tmp_path / "archive-ws-candles"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_CAPTURE,
        job_id="JOB-ws-candles",
        input_spec={
            "archive_root": str(archive_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "datatype": "candles",
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-ws-candles",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
            "derive_timeframes": ["5m"],
            "create_snapshot": True,
            "source_endpoint_or_subscription": "fixture/websocket/candles",
            "records": [_candle_row(index) for index in range(60)],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_CAPTURE,
        worker_id="worker-ws-candles",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)
    manifest_rows = ArchiveManifestStore(layout).load_file_manifest()
    coverage_reports = CoverageManifestStore(layout).load_coverage_reports()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "collector_mode=websocket_candle_batch_archive_write" in loaded.output_refs
    assert "source_mode=local_records" in loaded.output_refs
    assert "continuous_capture=false" in loaded.output_refs
    assert "accepted_historical_coverage_proof=false" in loaded.output_refs
    assert (
        "websocket_candle_batch_caveat=bounded_batch_not_unattended_continuous_capture"
        in loaded.output_refs
    )
    assert "source_endpoint_or_subscription=fixture/websocket/candles" in loaded.output_refs
    assert "records_source=inline" in loaded.output_refs
    assert "records_inline_row_count=60" in loaded.output_refs
    assert any(ref.startswith("raw_file_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("bronze_file_ids=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("silver_file_ids=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("coverage_report_ids=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("archive_snapshot_id=") for ref in loaded.archive_manifest_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "candles"),
        (ArchiveLayer.BRONZE, "candles"),
        (ArchiveLayer.SILVER, "bars"),
    }
    assert {row.timeframe for row in manifest_rows if row.layer == ArchiveLayer.SILVER} == {
        "1m",
        "5m",
    }
    assert {report.timeframe for report in coverage_reports} == {"1m", "5m"}
    assert all(report.coverage_ratio == 1.0 for report in coverage_reports)


def test_websocket_candle_batch_worker_reads_trusted_records_file(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-source"
    trusted_root.mkdir()
    records_file = trusted_root / "ws-candles.jsonl"
    records_file.write_text(
        "\n".join(json.dumps(_candle_row(index)) for index in range(60)),
        encoding="utf-8",
    )
    archive_root = tmp_path / "archive-ws-candles-file"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_CAPTURE,
        job_id="JOB-ws-candles-file",
        input_spec={
            "archive_root": str(archive_root),
            "trusted_source_root": str(trusted_root),
            "records_file": records_file.name,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "datatype": "candle",
            "timeframe": "1m",
            "date": "2026-01-01",
            "run_id": "run-ws-candles-file",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T01:00:00+00:00",
            "derive_timeframes": ["5m"],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_CAPTURE,
        worker_id="worker-ws-candles-file",
    )
    loaded = store.load_job(queued.job_id)
    manifest_rows = ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "collector_mode=websocket_candle_batch_archive_write" in loaded.output_refs
    assert "records_source=records_file" in loaded.output_refs
    assert "records_file_row_count=60" in loaded.output_refs
    assert any(ref.startswith("records_file_sha256=") for ref in loaded.output_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "candles"),
        (ArchiveLayer.BRONZE, "candles"),
        (ArchiveLayer.SILVER, "bars"),
    }


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


class _BacktestFixture:
    def __init__(
        self,
        *,
        archive_root: Path,
        archive_snapshot_id: str,
        universe_snapshot_id: str,
    ) -> None:
        self.archive_root = archive_root
        self.archive_snapshot_id = archive_snapshot_id
        self.universe_snapshot_id = universe_snapshot_id


def _backtest_archive_fixture(tmp_path: Path) -> _BacktestFixture:
    archive_root = tmp_path / "archive-backtest"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 8, 1, tzinfo=UTC)
    rows = _backtest_daily_rows(start_ts, end_ts)
    write_parquet_rows(
        layout=layout,
        store=store,
        rows=rows,
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date=start_ts.date().isoformat(),
        timeframe="1d",
        job_id="job-worker-backtest-silver",
        source_file_ids=("source-worker-backtest",),
        instrument_id=INSTRUMENT,
    )
    report = coverage_report_for_bars(
        rows,
        venue="hyperliquid",
        instrument_id=INSTRUMENT,
        timeframe="1d",
        start_ts=start_ts,
        end_ts=end_ts,
        evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
    )
    CoverageManifestStore(layout).append_coverage_report(report)
    snapshot = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope="hyperliquid",
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=[report.model_dump(mode="json")],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="worker_vectorized_backtest_fixture",
    )
    universe = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_universe_payload(),
        asof_date=date(2024, 1, 1),
        mode=UniverseMode.AS_OF,
    )
    return _BacktestFixture(
        archive_root=archive_root,
        archive_snapshot_id=snapshot.archive_snapshot_id,
        universe_snapshot_id=universe.snapshot_id,
    )


def _backtest_daily_rows(start_ts: datetime, end_ts: datetime) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start_ts
    index = 0
    while current < end_ts:
        close = 100.0 + (index * 0.2) + ((index % 7) * 0.1)
        rows.append(
            {
                "venue": "hyperliquid",
                "instrument_id": INSTRUMENT,
                "timeframe": "1d",
                "ts": current.isoformat().replace("+00:00", "Z"),
                "end_ts": (current + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "open": close - 0.15,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 100_000.0 + index,
                "trade_count": index + 1,
                "funding": 0.00001 if index % 2 == 0 else -0.00001,
                "funding_rate": 0.00001 if index % 2 == 0 else -0.00001,
                "open_interest": 5_000_000.0 + index,
                "mark_price": close,
                "oracle_price": close,
                "spread": 0.001,
                "coverage_ratio": 1.0,
                "source_timeframe": "1d",
                "source_file_id": "f" * 64,
                "source_layer": "bronze",
                "normalization_warnings": (),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
        current += timedelta(days=1)
        index += 1
    return rows


def _worker_backtest_strategy_spec() -> dict[str, object]:
    payload = json.loads(json.dumps(example_strategy_payloads()["hl_mean_reversion_v1"]))
    payload["inputs"]["timeframe"] = "1d"
    payload["inputs"]["fields"] = ["close", "volume", "coverage_ratio"]
    payload["logic"]["lookback_bars"] = 2
    payload["logic"]["lookback_hours"] = None
    payload["logic"]["entry_threshold"] = 0.1
    payload["risk"]["rebalance"] = "1d"
    payload["validation"]["min_backtest_months"] = 6
    return payload


def _worker_backtest_run_manifest(
    tmp_path: Path,
    *,
    store: WorkerJobStore,
    job_id: str,
    run_id: str,
) -> Path:
    fixture = _backtest_archive_fixture(tmp_path / job_id)
    queued = store.enqueue(
        kind=WorkerJobKind.VECTORIZED_BACKTEST,
        job_id=job_id,
        input_spec={
            "archive_root": str(fixture.archive_root),
            "output_root": str(tmp_path / "runs"),
            "run_id": run_id,
            "experiment_id": "phase7-ledger-worker-backtest",
            "archive_snapshot_id": fixture.archive_snapshot_id,
            "universe_snapshot_id": fixture.universe_snapshot_id,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "timeframe": "1d",
            "start_ts": "2024-01-01T00:00:00+00:00",
            "end_ts": "2024-08-01T00:00:00+00:00",
            "asof_date": "2026-06-21",
            "evidence_mode": "accepted_research",
            "strategy_spec": _worker_backtest_strategy_spec(),
        },
    )
    result = run_one_job(
        store=store,
        kind=WorkerJobKind.VECTORIZED_BACKTEST,
        worker_id=f"worker-{job_id}",
    )
    loaded = store.load_job(queued.job_id)
    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    return tmp_path / "runs" / run_id / "run_manifest.json"


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


def _candle_row(index: int) -> dict[str, object]:
    ts = START + timedelta(minutes=index)
    return {
        "ts": ts.isoformat().replace("+00:00", "Z"),
        "end_ts": (ts + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "instrument_id": INSTRUMENT,
        "timeframe": "1m",
        "open": 100 + index,
        "high": 101 + index,
        "low": 99 + index,
        "close": 100 + index,
        "volume": 10 + index,
        "trade_count": index + 1,
    }


def _hyperliquid_candle_row(index: int) -> dict[str, object]:
    ts = START + timedelta(minutes=index)
    open_price = 100 + index
    return {
        "t": int(ts.timestamp() * 1000),
        "T": int((ts + timedelta(minutes=1)).timestamp() * 1000),
        "s": "BTC",
        "i": "1m",
        "o": str(open_price),
        "h": str(open_price + 2),
        "l": str(open_price - 2),
        "c": str(open_price + 1),
        "v": str(10 + index),
        "n": index + 1,
    }


def _hyperliquid_funding_row(index: int, funding_rate: str) -> dict[str, object]:
    ts = START + timedelta(hours=index)
    return {
        "coin": "BTC",
        "fundingRate": funding_rate,
        "premium": "0.0",
        "time": int(ts.timestamp() * 1000),
    }


def _silver_bars_file_id(archive_root: Path, *, timeframe: str) -> str:
    matches = [
        row
        for row in ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest()
        if row.layer == ArchiveLayer.SILVER and row.datatype == "bars" and row.timeframe == timeframe
    ]
    assert len(matches) == 1
    return matches[0].file_id


def _ref_value(refs: tuple[str, ...], key: str) -> str:
    prefix = f"{key}="
    for ref in refs:
        if ref.startswith(prefix):
            return ref.removeprefix(prefix)
    raise AssertionError(f"{key} not found in refs: {refs}")


def _succeed_worker_job_for_audit(
    store: WorkerJobStore,
    *,
    kind: WorkerJobKind,
    job_id: str,
    output_refs: tuple[str, ...] = (),
    archive_manifest_refs: tuple[str, ...] = (),
    finished_at: datetime | None = None,
):
    store.enqueue(
        kind=kind,
        job_id=job_id,
        input_spec={"purpose": "audit-required-loop-evidence-fixture"},
    )
    worker_id = f"worker-{job_id}"
    claimed = store.claim_next(kind=kind, worker_id=worker_id)
    assert claimed is not None
    running = store.start_job(claimed.job_id, worker_id=worker_id)
    succeeded = store.succeed_job(
        running.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_manifest_refs,
        reason="audit_required_loop_evidence_fixture_succeeded",
    )
    if finished_at is None:
        return succeeded
    updated = succeeded.model_copy(update={"finished_at": finished_at})
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE worker_jobs SET record_json = ?, updated_at = ? WHERE job_id = ?",
            (updated.model_dump_json(), finished_at.isoformat(), updated.job_id),
        )
    loaded = store.load_job(updated.job_id)
    assert loaded == updated
    return loaded
