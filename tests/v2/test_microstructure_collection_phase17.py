from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from tradingbotsuite.v2.archive import (
    ArchiveLayout,
    ArchiveManifestStore,
    MicrostructureDataType,
    build_retention_backup_policy,
    build_storage_budget_report,
    record_retention_backup_policy,
    write_microstructure_raw_capture,
)
from tradingbotsuite.v2.archive.raw_writer import read_jsonl_zstd
from tradingbotsuite.v2.backtest_engine import BacktestRunConfig, RunStatus, run_event_driven_backtest
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job


START = datetime(2026, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 1, 0, 1, tzinfo=UTC)
HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
INSTRUMENT = "hyperliquid:perp:BTC"


def test_trade_capture_raw_preserved_and_manifest_recorded(tmp_path) -> None:
    layout = ArchiveLayout(tmp_path / "archive")
    result = write_microstructure_raw_capture(
        archive_root=layout.root,
        records=_trade_rows(),
        venue="hyperliquid",
        datatype=MicrostructureDataType.TRADES,
        date="2026-01-01",
        run_id="run-trades",
        job_id="job-trades",
        adapter_id="fixture_microstructure_v1",
        source_endpoint_or_subscription="fixture/websocket/trades",
        instrument_id=INSTRUMENT,
        start_ts=START,
        end_ts=END,
        storage_budget_bytes=1_000_000,
    )

    raw_path = layout.resolve(result.raw_file.path)
    stored_rows = read_jsonl_zstd(
        raw_path,
        uncompressed_size=result.raw_file.uncompressed_size_bytes or 0,
    )
    manifest_rows = ArchiveManifestStore(layout).load_file_manifest()

    assert result.raw_file in manifest_rows
    assert result.raw_file.layer.value == "raw"
    assert result.raw_file.datatype == "trades"
    assert result.raw_file.row_count == 2
    assert [row["event_type"] for row in stored_rows] == ["trade", "trade"]
    assert result.quality_report.row_count == 2
    assert result.quality_report.quality_status == "ok"
    assert result.storage_report.total_bytes >= result.raw_file.size_bytes
    assert layout.resolve(
        "manifests",
        "microstructure_quality_reports",
        f"{result.quality_report.quality_report_id}.json",
    ).exists()


@pytest.mark.parametrize(
    ("datatype", "records"),
    [
        ("bbo", [{"ts": "2026-01-01T00:00:00Z", "instrument_id": INSTRUMENT, "event_type": "bbo", "bid": 99.9, "ask": 100.1, "sequence": 0}]),
        ("l2", [{"ts": "2026-01-01T00:00:00Z", "instrument_id": INSTRUMENT, "event_type": "l2", "bid_depth": 10_000.0, "ask_depth": 12_000.0, "sequence": 0}]),
    ],
)
def test_bbo_and_l2_worker_capture_are_raw_preserved(tmp_path, datatype: str, records: list[dict[str, object]]) -> None:
    archive_root = tmp_path / f"archive-{datatype}"
    store = WorkerJobStore(tmp_path / f"jobs-{datatype}.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id=f"JOB-{datatype}-capture",
        input_spec={
            "archive_root": str(archive_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "datatype": datatype,
            "date": "2026-01-01",
            "run_id": f"run-{datatype}",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "records": records,
            "storage_budget_bytes": 1_000_000,
            "reconnect_attempts": 2 if datatype == "bbo" else 0,
            "backoff_seconds": 5 if datatype == "bbo" else 0,
            "gap_reason": "fixture_reconnect_gap" if datatype == "bbo" else "",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        worker_id=f"worker-{datatype}",
    )
    loaded = store.load_job(queued.job_id)
    manifest_rows = ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert any(ref.startswith("raw_file_id=") for ref in loaded.archive_manifest_refs)
    assert any(ref.startswith("quality_report_id=") for ref in loaded.archive_manifest_refs)
    assert [row.datatype for row in manifest_rows] == [datatype]
    assert manifest_rows[0].row_count == 1
    if datatype == "bbo":
        gaps = store.list_gap_records(queued.job_id)
        assert len(gaps) == 1
        assert gaps[0].reason == "fixture_reconnect_gap"
        assert gaps[0].reconnect_attempts == 2


@pytest.mark.parametrize("datatype", ["bbo", "l2"])
def test_public_l2_book_worker_capture_writes_snapshot_microstructure(
    tmp_path,
    monkeypatch,
    datatype: str,
) -> None:
    archive_root = tmp_path / f"archive-public-{datatype}"
    seen_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        seen_bodies.append(body)
        assert request.method == "POST"
        assert body == {"type": "l2Book", "coin": "BTC"}
        return httpx.Response(200, json=_l2_book_payload())

    class FakeHyperliquidInfoClient:
        def __init__(self, base_url: str, timeout: float) -> None:
            self._client = _real_hyperliquid_client(
                base_url=base_url,
                timeout=timeout,
                transport=httpx.MockTransport(handler),
            )

        def fetch_l2_book(self, **kwargs):
            return self._client.fetch_l2_book(**kwargs)

    from tradingbotsuite.v2.venues.hyperliquid import HyperliquidInfoClient as _real_hyperliquid_client

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidInfoClient",
        FakeHyperliquidInfoClient,
    )
    store = WorkerJobStore(tmp_path / f"jobs-public-{datatype}.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id=f"JOB-public-l2-book-{datatype}",
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "public_info_url": "https://example.test/info",
            "public_info_timeout": 3.0,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "coin": "BTC",
            "datatype": datatype,
            "date": "2026-01-01",
            "run_id": f"run-public-l2-book-{datatype}",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "storage_budget_bytes": 1_000_000,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        worker_id=f"worker-public-{datatype}",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)
    manifest_rows = ArchiveManifestStore(layout).load_file_manifest()
    stored_rows = read_jsonl_zstd(
        layout.resolve(manifest_rows[0].path),
        uncompressed_size=manifest_rows[0].uncompressed_size_bytes or 0,
    )

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert seen_bodies == [{"type": "l2Book", "coin": "BTC"}]
    assert "collector_mode=public_api_l2_bbo_snapshot_capture" in loaded.output_refs
    assert "source_mode=public_api" in loaded.output_refs
    assert f"datatype={datatype}" in loaded.output_refs
    assert "row_count=1" in loaded.output_refs
    assert "api_row_count=4" in loaded.output_refs
    assert "venue_adapter_id=hyperliquid_public_info_v1" in loaded.output_refs
    assert "source_endpoint_or_subscription=info/l2Book" in loaded.output_refs
    assert "coin=BTC" in loaded.output_refs
    assert "api_documented_limit=max_20_levels_per_side" in loaded.output_refs
    assert "gap_evidence_recorded=false" in loaded.output_refs
    assert any(ref.startswith("raw_request_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_response_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_payload_sha256=") for ref in loaded.output_refs)
    assert [row.datatype for row in manifest_rows] == [datatype]
    assert manifest_rows[0].row_count == 1
    assert stored_rows[0]["event_type"] == datatype
    assert stored_rows[0]["instrument_id"] == INSTRUMENT
    assert stored_rows[0]["source"] == "public_api/info/l2Book"
    if datatype == "bbo":
        assert stored_rows[0]["bid"] == 100.0
        assert stored_rows[0]["ask"] == 100.5
        assert stored_rows[0]["bid_size"] == 1.25
        assert stored_rows[0]["ask_size"] == 1.5
    else:
        assert stored_rows[0]["bid_depth"] == pytest.approx(3.25)
        assert stored_rows[0]["ask_depth"] == pytest.approx(4.75)
        assert stored_rows[0]["book_levels"] == 4


def test_public_l2_book_worker_rejects_public_api_with_local_records(tmp_path) -> None:
    archive_root = tmp_path / "archive-public-l2-reject"
    store = WorkerJobStore(tmp_path / "jobs-public-l2-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id="JOB-public-l2-records-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_api",
            "instrument_id": INSTRUMENT,
            "datatype": "l2",
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "records": [
                {
                    "ts": "2026-01-01T00:00:00Z",
                    "instrument_id": INSTRUMENT,
                    "event_type": "l2",
                    "bid_depth": 10_000.0,
                    "ask_depth": 12_000.0,
                }
            ],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        worker_id="worker-public-l2-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "source=public_api cannot include records" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_public_websocket_trade_worker_capture_writes_snapshot_microstructure(
    tmp_path,
    monkeypatch,
) -> None:
    archive_root = tmp_path / "archive-public-ws-trades"

    class FakeHyperliquidWebSocketClient:
        def __init__(self, ws_url: str, timeout: float) -> None:
            self.ws_url = ws_url
            self.timeout = timeout

        def fetch_trade_snapshot(self, **kwargs):
            from tradingbotsuite.v2.venues.hyperliquid import HyperliquidWebSocketClient as RealClient

            client = RealClient(
                ws_url=self.ws_url,
                timeout=self.timeout,
                connect=_fake_trade_websocket_connect,
            )
            return client.fetch_trade_snapshot(**kwargs)

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidWebSocketClient",
        FakeHyperliquidWebSocketClient,
    )
    store = WorkerJobStore(tmp_path / "jobs-public-ws-trades.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        job_id="JOB-public-ws-trades",
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_websocket",
            "public_ws_url": "wss://example.test/ws",
            "public_ws_timeout": 3.0,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "coin": "BTC",
            "date": "2026-01-01",
            "run_id": "run-public-ws-trades",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "max_public_ws_messages": 2,
            "max_public_ws_rows": 2,
            "max_public_ws_seconds": 3.0,
            "storage_budget_bytes": 1_000_000,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        worker_id="worker-public-ws-trades",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)
    manifest_rows = ArchiveManifestStore(layout).load_file_manifest()
    stored_rows = read_jsonl_zstd(
        layout.resolve(manifest_rows[0].path),
        uncompressed_size=manifest_rows[0].uncompressed_size_bytes or 0,
    )

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "collector_mode=public_websocket_trade_snapshot_capture" in loaded.output_refs
    assert "source_mode=public_websocket" in loaded.output_refs
    assert "datatype=trades" in loaded.output_refs
    assert "row_count=2" in loaded.output_refs
    assert "ws_message_count=2" in loaded.output_refs
    assert "ws_trade_row_count=3" in loaded.output_refs
    assert "venue_adapter_id=hyperliquid_public_websocket_v1" in loaded.output_refs
    assert "source_endpoint_or_subscription=websocket/trades" in loaded.output_refs
    assert "coin=BTC" in loaded.output_refs
    assert "max_public_ws_messages=2" in loaded.output_refs
    assert "max_public_ws_rows=2" in loaded.output_refs
    assert "gap_evidence_recorded=false" in loaded.output_refs
    assert any(ref.startswith("raw_request_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_response_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_payload_sha256=") for ref in loaded.output_refs)
    assert [row.datatype for row in manifest_rows] == ["trades"]
    assert manifest_rows[0].row_count == 2
    assert [row["event_type"] for row in stored_rows] == ["trade", "trade"]
    assert [row["price"] for row in stored_rows] == [100.0, 100.5]
    assert [row["size"] for row in stored_rows] == [1.25, 2.0]
    assert [row["trade_id"] for row in stored_rows] == [
        "BTC:1767225600000:123",
        "BTC:1767225600500:124",
    ]
    assert all(row["source"] == "public_websocket/trades" for row in stored_rows)


def test_public_websocket_trade_worker_rejects_public_websocket_with_local_records(tmp_path) -> None:
    archive_root = tmp_path / "archive-public-ws-trades-reject"
    store = WorkerJobStore(tmp_path / "jobs-public-ws-trades-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        job_id="JOB-public-ws-trades-records-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_websocket",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "records": _trade_rows(),
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        worker_id="worker-public-ws-trades-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "source=public_websocket cannot include records" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_official_s3_backfill_preserves_native_file_and_manifest(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-s3"
    trusted_root.mkdir()
    source = trusted_root / "BTCUSDT-trades-2026-01.zip"
    source.write_bytes(b"official-s3-fixture")
    archive_root = tmp_path / "archive"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        job_id="JOB-s3-backfill",
        input_spec={
            "archive_root": str(archive_root),
            "source_file": str(source),
            "trusted_source_root": str(trusted_root),
            "venue": "binance",
            "instrument_id": "binance:perp:BTCUSDT",
            "date": "2026-01-01",
            "run_id": "run-s3",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-31T23:59:59+00:00",
            "row_count": 42,
            "storage_budget_bytes": 1_000_000,
            "source_endpoint_or_subscription": "s3://public-fixture/BTCUSDT-trades-2026-01.zip",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        worker_id="worker-s3",
    )
    loaded = store.load_job(queued.job_id)
    manifest_rows = ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest()
    raw_file = ArchiveLayout(archive_root).resolve(manifest_rows[0].path)

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert any(ref.startswith("raw_file_id=") for ref in loaded.archive_manifest_refs)
    assert manifest_rows[0].datatype == "official_s3"
    assert manifest_rows[0].row_count == 42
    assert raw_file.read_bytes() == b"official-s3-fixture"


def test_hyperliquid_official_s3_backfill_records_dataset_scope(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-hyperliquid-s3"
    trusted_root.mkdir()
    source = trusted_root / "BTC.lz4"
    source.write_bytes(b"official-hyperliquid-l2-fixture")
    archive_root = tmp_path / "archive-hyperliquid-l2"
    store = WorkerJobStore(tmp_path / "jobs-hyperliquid-l2.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        job_id="JOB-hyperliquid-s3-l2",
        input_spec={
            "archive_root": str(archive_root),
            "source_file": str(source),
            "trusted_source_root": str(trusted_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "run_id": "run-hyperliquid-s3-l2",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:59:59+00:00",
            "row_count": 12,
            "official_dataset": "market_data_l2_book",
            "storage_budget_bytes": 1_000_000,
            "source_endpoint_or_subscription": (
                "s3://hyperliquid-archive/market_data/20260101/0/l2Book/BTC.lz4"
            ),
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        worker_id="worker-hyperliquid-s3-l2",
    )
    loaded = store.load_job(queued.job_id)
    manifest_rows = ArchiveManifestStore(ArchiveLayout(archive_root)).load_file_manifest()

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "source_mode=trusted_local_official_file" in loaded.output_refs
    assert "official_dataset=market_data_l2_book" in loaded.output_refs
    assert "official_dataset_scope=official_hyperliquid_l2_book_snapshots" in loaded.output_refs
    assert "official_s3_network_download=false" in loaded.output_refs
    assert (
        "official_s3_research_caveat=raw_native_file_preserved_not_normalized_coverage_evidence"
        in loaded.output_refs
    )
    assert any(ref.startswith("raw_file_sha256=") for ref in loaded.output_refs)
    assert manifest_rows[0].datatype == "official_s3"
    assert manifest_rows[0].venue == "hyperliquid"
    assert manifest_rows[0].row_count == 12


def test_hyperliquid_official_s3_backfill_infers_node_fills_dataset(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-hyperliquid-node"
    trusted_root.mkdir()
    source = trusted_root / "00000001.lz4"
    source.write_bytes(b"official-hyperliquid-node-fills-fixture")
    archive_root = tmp_path / "archive-hyperliquid-node"
    store = WorkerJobStore(tmp_path / "jobs-hyperliquid-node.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        job_id="JOB-hyperliquid-node-fills",
        input_spec={
            "archive_root": str(archive_root),
            "source_file": str(source),
            "trusted_source_root": str(trusted_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "run_id": "run-hyperliquid-node-fills",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:59:59+00:00",
            "row_count": 3,
            "source_endpoint_or_subscription": (
                "s3://hl-mainnet-node-data/node_fills_by_block/00000001.lz4"
            ),
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        worker_id="worker-hyperliquid-node-fills",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert "official_dataset=node_fills_by_block" in loaded.output_refs
    assert "official_dataset_scope=official_hyperliquid_node_fills_by_block" in loaded.output_refs


def test_hyperliquid_official_s3_backfill_rejects_unsupported_candle_dataset(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-hyperliquid-candles"
    trusted_root.mkdir()
    source = trusted_root / "BTC-candles.lz4"
    source.write_bytes(b"unsupported-candles")
    archive_root = tmp_path / "archive-hyperliquid-candles"
    store = WorkerJobStore(tmp_path / "jobs-hyperliquid-candles.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        job_id="JOB-hyperliquid-candles-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source_file": str(source),
            "trusted_source_root": str(trusted_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "run_id": "run-hyperliquid-candles-reject",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:59:59+00:00",
            "row_count": 1,
            "official_dataset": "candles",
            "source_endpoint_or_subscription": "s3://hyperliquid-archive/candles/BTC.lz4",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        worker_id="worker-hyperliquid-candles-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "not supported for v2 official_s3_backfill" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


@pytest.mark.parametrize(
    ("source_name", "expected_reason"),
    [
        (".env", "secret or local state"),
        ("credentials.pem", "secret or local state"),
        ("../escape.zip", "trusted_source_root"),
    ],
)
def test_official_s3_backfill_rejects_untrusted_or_secret_sources(
    tmp_path, source_name: str, expected_reason: str
) -> None:
    trusted_root = tmp_path / "trusted-s3"
    trusted_root.mkdir()
    source = (trusted_root / source_name).resolve()
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"must-not-enter-archive")
    archive_root = tmp_path / "archive"
    store = WorkerJobStore(tmp_path / "jobs.sqlite")
    safe_job_id = source_name.replace(".", "dot").replace("/", "-").replace("\\", "-")
    queued = store.enqueue(
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        job_id=f"JOB-s3-reject-{safe_job_id}",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source_file": source_name,
            "trusted_source_root": str(trusted_root),
            "venue": "binance",
            "instrument_id": "binance:perp:BTCUSDT",
            "date": "2026-01-01",
            "run_id": "run-s3-reject",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-31T23:59:59+00:00",
            "row_count": 42,
            "storage_budget_bytes": 1_000_000,
            "source_endpoint_or_subscription": "s3://public-fixture/BTCUSDT-trades-2026-01.zip",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        worker_id="worker-s3-reject",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert expected_reason in (loaded.failure_reason or "")
    assert not list((archive_root / "raw").glob("**/*")) if (archive_root / "raw").exists() else True
    assert ArchiveManifestStore(layout).load_file_manifest() == []


def test_storage_budget_and_retention_policy_are_record_only(tmp_path) -> None:
    layout = ArchiveLayout(tmp_path / "archive")
    capture = write_microstructure_raw_capture(
        archive_root=layout.root,
        records=_bbo_rows(),
        venue="hyperliquid",
        datatype="bbo",
        date="2026-01-01",
        run_id="run-budget",
        job_id="job-budget",
        adapter_id="fixture_microstructure_v1",
        source_endpoint_or_subscription="fixture/websocket/bbo",
        instrument_id=INSTRUMENT,
        start_ts=START,
        end_ts=END,
        storage_budget_bytes=1,
    )
    raw_path = layout.resolve(capture.raw_file.path)
    before_bytes = raw_path.stat().st_size
    policy = build_retention_backup_policy(
        retention_days=30,
        backup_target="operator_managed_cold_storage",
    )
    policy_path = record_retention_backup_policy(layout, policy)
    report = build_storage_budget_report(layout, max_bytes=1)

    assert raw_path.exists()
    assert raw_path.stat().st_size == before_bytes
    assert policy_path.exists()
    assert policy.deletion_authorized is False
    assert policy.backup_transfer_authorized is False
    assert report.within_budget is False
    assert report.layer_bytes["raw"] >= before_bytes


def test_event_driven_engine_consumes_captured_microstructure_fixture(tmp_path) -> None:
    capture = write_microstructure_raw_capture(
        archive_root=tmp_path / "archive",
        records=_bbo_rows(),
        venue="hyperliquid",
        datatype="bbo",
        date="2026-01-01",
        run_id="run-event-fixture",
        job_id="job-event-fixture",
        adapter_id="fixture_microstructure_v1",
        source_endpoint_or_subscription="fixture/websocket/bbo",
        instrument_id=INSTRUMENT,
        start_ts=START,
        end_ts=END,
        storage_budget_bytes=1_000_000,
    )
    result = run_event_driven_backtest(
        config=_config(tmp_path / "runs", run_id="phase17-event"),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(),
        microstructure_rows=capture.normalized_rows,
    )

    assert result.manifest.status == RunStatus.SUCCEEDED
    assert result.manifest.engine_lane.value == "event_driven"
    assert result.manifest.promotion_ready is False
    assert result.manifest.order_placement_instruction is False


def _trade_rows() -> list[dict[str, object]]:
    return [
        {
            "ts": "2026-01-01T00:00:00Z",
            "instrument_id": INSTRUMENT,
            "event_type": "trade",
            "sequence": 0,
            "price": 100.0,
            "size": 1.5,
            "side": "buy",
        },
        {
            "ts": "2026-01-01T00:00:01Z",
            "instrument_id": INSTRUMENT,
            "event_type": "trade",
            "sequence": 1,
            "price": 100.5,
            "size": 0.7,
            "side": "sell",
        },
    ]


def _bbo_rows() -> list[dict[str, object]]:
    return [
        {
            "ts": "2026-01-01T00:00:00Z",
            "instrument_id": INSTRUMENT,
            "event_type": "bbo",
            "sequence": 0,
            "bid": 99.9,
            "ask": 100.1,
            "bid_size": 10.0,
            "ask_size": 11.0,
        },
        {
            "ts": "2026-01-01T00:00:01Z",
            "instrument_id": INSTRUMENT,
            "event_type": "bbo",
            "sequence": 1,
            "bid": 100.0,
            "ask": 100.2,
            "bid_size": 12.0,
            "ask_size": 13.0,
        },
    ]


def _l2_book_payload() -> dict[str, object]:
    return {
        "coin": "BTC",
        "time": int(START.timestamp() * 1000),
        "levels": [
            [
                {"px": "100.0", "sz": "1.25", "n": 2},
                {"px": "99.5", "sz": "2.00", "n": 1},
            ],
            [
                {"px": "100.5", "sz": "1.50", "n": 3},
                {"px": "101.0", "sz": "3.25", "n": 1},
            ],
        ],
    }


def _fake_trade_websocket_connect(url: str, **kwargs):
    assert url == "wss://example.test/ws"
    assert kwargs == {"open_timeout": 3.0}
    return _FakeTradeWebSocket()


class _FakeTradeWebSocket:
    def __init__(self) -> None:
        self.messages = [
            {"channel": "subscriptionResponse", "data": {"subscription": {"type": "trades", "coin": "BTC"}}},
            {"channel": "trades", "data": _ws_trade_rows()},
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def send(self, raw_message: str) -> None:
        assert json.loads(raw_message) == {
            "method": "subscribe",
            "subscription": {"type": "trades", "coin": "BTC"},
        }

    def recv(self, timeout=None) -> str:
        if not self.messages:
            raise TimeoutError("no more messages")
        return json.dumps(self.messages.pop(0))


def _ws_trade_rows() -> list[dict[str, object]]:
    return [
        {
            "coin": "BTC",
            "side": "A",
            "px": "100.0",
            "sz": "1.25",
            "hash": "0xabc",
            "time": 1_767_225_600_000,
            "tid": 123,
            "users": ["0x1", "0x2"],
        },
        {
            "coin": "BTC",
            "side": "B",
            "px": "100.5",
            "sz": "2.00",
            "hash": "0xdef",
            "time": 1_767_225_600_500,
            "tid": 124,
            "users": ["0x3", "0x4"],
        },
        {
            "coin": "BTC",
            "side": "A",
            "px": "101.0",
            "sz": "3.00",
            "hash": "0xghi",
            "time": 1_767_225_601_000,
            "tid": 125,
            "users": ["0x5", "0x6"],
        },
    ]


def _config(output_root: Path, *, run_id: str) -> BacktestRunConfig:
    return BacktestRunConfig(
        run_id=run_id,
        experiment_id="phase17-test",
        output_root=str(output_root),
        archive_snapshot_id="archive-snapshot",
        universe_snapshot_id="universe-snapshot",
        data_manifest_id="data-manifest",
        data_manifest_hash=HEX_A,
        validation_manifest_hash=HEX_B,
        cost_manifest_hash=HEX_C,
        universe_mode="as_of",
        venue_scope="hyperliquid",
        git_sha="test-git-sha",
    )


def _short_spec(strategy_id: str):
    payload = example_strategy_payloads()[strategy_id]
    payload = json.loads(json.dumps(payload))
    payload["logic"]["lookback_hours"] = 2
    payload["logic"]["lookback_bars"] = 2
    payload["inputs"]["fields"] = sorted(
        {
            *payload["inputs"]["fields"],
            "open",
            "high",
            "low",
            "close",
            "volume",
            "funding",
            "funding_rate",
            "open_interest",
            "mark_price",
            "oracle_price",
            "spread",
            "coverage_ratio",
        }
    )
    return payload


def _panel_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    instruments = {
        "hyperliquid:perp:BTC": 100.0,
        "hyperliquid:perp:ETH": 80.0,
        "hyperliquid:perp:SOL": 40.0,
    }
    for hour in range(12):
        ts = f"2024-01-01T{hour:02d}:00:00Z"
        for offset, (instrument_id, base) in enumerate(instruments.items()):
            drift = (hour * (offset + 1)) * (1 if offset != 1 else -0.5)
            open_price = base + drift
            close = open_price * (1.01 if offset == 0 else 0.995 if offset == 1 else 1.002)
            rows.append(
                {
                    "ts": ts,
                    "instrument_id": instrument_id,
                    "open": open_price,
                    "high": max(open_price, close) * 1.01,
                    "low": min(open_price, close) * 0.99,
                    "close": close,
                    "volume": 100_000.0 + (hour * 1000) + offset,
                    "funding": 0.0002 if offset == 0 else -0.0001 if offset == 1 else 0.0,
                    "funding_rate": 0.0002 if offset == 0 else -0.0001 if offset == 1 else 0.0,
                    "open_interest": 2_000_000.0 + offset,
                    "mark_price": close,
                    "oracle_price": close,
                    "spread": 0.001,
                    "coverage_ratio": 1.0,
                }
            )
    return rows
