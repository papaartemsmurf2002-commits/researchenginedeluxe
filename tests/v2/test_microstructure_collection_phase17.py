from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from tradingbotsuite.v2.archive import (
    ArchiveLayer,
    ArchiveLayout,
    ArchiveManifestStore,
    MicrostructureDataType,
    SilverAssetContextRow,
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


@pytest.mark.parametrize("datatype", ["bbo", "l2"])
def test_public_websocket_l2_bbo_worker_capture_writes_snapshot_microstructure(
    tmp_path,
    monkeypatch,
    datatype: str,
) -> None:
    archive_root = tmp_path / f"archive-public-ws-{datatype}"

    class FakeHyperliquidWebSocketClient:
        def __init__(self, ws_url: str, timeout: float) -> None:
            self.ws_url = ws_url
            self.timeout = timeout

        def fetch_bbo_snapshot(self, **kwargs):
            from tradingbotsuite.v2.venues.hyperliquid import HyperliquidWebSocketClient as RealClient

            client = RealClient(
                ws_url=self.ws_url,
                timeout=self.timeout,
                connect=_fake_bbo_websocket_connect,
            )
            return client.fetch_bbo_snapshot(**kwargs)

        def fetch_l2_book_snapshot(self, **kwargs):
            from tradingbotsuite.v2.venues.hyperliquid import HyperliquidWebSocketClient as RealClient

            client = RealClient(
                ws_url=self.ws_url,
                timeout=self.timeout,
                connect=_fake_l2_book_websocket_connect,
            )
            return client.fetch_l2_book_snapshot(**kwargs)

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidWebSocketClient",
        FakeHyperliquidWebSocketClient,
    )
    input_spec = {
        "archive_root": str(archive_root),
        "source": "public_websocket",
        "public_ws_url": "wss://example.test/ws",
        "public_ws_timeout": 3.0,
        "venue": "hyperliquid",
        "instrument_id": INSTRUMENT,
        "coin": "BTC",
        "datatype": datatype,
        "date": "2026-01-01",
        "run_id": f"run-public-ws-{datatype}",
        "start_ts": "2026-01-01T00:00:00+00:00",
        "end_ts": "2026-01-01T00:01:00+00:00",
        "max_public_ws_messages": 2,
        "max_public_ws_rows": 4 if datatype == "l2" else 2,
        "max_public_ws_seconds": 3.0,
        "storage_budget_bytes": 1_000_000,
    }
    if datatype == "l2":
        input_spec["n_sig_figs"] = 5
        input_spec["mantissa"] = 2
    store = WorkerJobStore(tmp_path / f"jobs-public-ws-{datatype}.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id=f"JOB-public-ws-{datatype}",
        input_spec=input_spec,
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        worker_id=f"worker-public-ws-{datatype}",
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
    assert "collector_mode=public_websocket_l2_bbo_snapshot_capture" in loaded.output_refs
    assert "source_mode=public_websocket" in loaded.output_refs
    assert "continuous_capture=false" in loaded.output_refs
    assert "accepted_historical_coverage_proof=false" in loaded.output_refs
    assert (
        "public_websocket_l2_bbo_snapshot_caveat=bounded_public_stream_snapshot_not_unattended_continuous_capture"
        in loaded.output_refs
    )
    assert f"datatype={datatype}" in loaded.output_refs
    assert "row_count=1" in loaded.output_refs
    assert "ws_message_count=2" in loaded.output_refs
    assert "venue_adapter_id=hyperliquid_public_websocket_v1" in loaded.output_refs
    assert "coin=BTC" in loaded.output_refs
    assert "max_public_ws_messages=2" in loaded.output_refs
    assert "max_public_ws_seconds=3.0" in loaded.output_refs
    assert "gap_evidence_recorded=false" in loaded.output_refs
    assert any(ref.startswith("raw_request_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_response_id=") for ref in loaded.output_refs)
    assert any(ref.startswith("raw_payload_sha256=") for ref in loaded.output_refs)
    assert [row.datatype for row in manifest_rows] == [datatype]
    assert manifest_rows[0].row_count == 1
    assert stored_rows[0]["event_type"] == datatype
    assert stored_rows[0]["instrument_id"] == INSTRUMENT
    if datatype == "bbo":
        assert "source_endpoint_or_subscription=websocket/bbo" in loaded.output_refs
        assert "ws_bbo_row_count=1" in loaded.output_refs
        assert stored_rows[0]["source"] == "public_websocket/bbo"
        assert stored_rows[0]["bid"] == 100.0
        assert stored_rows[0]["ask"] == 100.5
        assert stored_rows[0]["bid_size"] == 1.25
        assert stored_rows[0]["ask_size"] == 1.5
    else:
        assert "source_endpoint_or_subscription=websocket/l2Book" in loaded.output_refs
        assert "ws_l2_book_row_count=4" in loaded.output_refs
        assert "nSigFigs=5" in loaded.output_refs
        assert "mantissa=2" in loaded.output_refs
        assert stored_rows[0]["source"] == "public_websocket/l2Book"
        assert stored_rows[0]["bid_depth"] == pytest.approx(3.25)
        assert stored_rows[0]["ask_depth"] == pytest.approx(4.75)
        assert stored_rows[0]["book_levels"] == 4


@pytest.mark.parametrize("datatype", ["bbo", "l2"])
def test_public_websocket_l2_bbo_unattended_session_writes_report(
    tmp_path,
    monkeypatch,
    datatype: str,
) -> None:
    archive_root = tmp_path / f"archive-public-ws-session-{datatype}"

    class FakeHyperliquidWebSocketClient:
        def __init__(self, ws_url: str, timeout: float) -> None:
            self.ws_url = ws_url
            self.timeout = timeout

        def fetch_bbo_snapshot(self, **kwargs):
            from tradingbotsuite.v2.venues.hyperliquid import HyperliquidWebSocketClient as RealClient

            client = RealClient(
                ws_url=self.ws_url,
                timeout=self.timeout,
                connect=_fake_bbo_websocket_connect,
            )
            return client.fetch_bbo_snapshot(**kwargs)

        def fetch_l2_book_snapshot(self, **kwargs):
            from tradingbotsuite.v2.venues.hyperliquid import HyperliquidWebSocketClient as RealClient

            client = RealClient(
                ws_url=self.ws_url,
                timeout=self.timeout,
                connect=_fake_l2_book_websocket_connect,
            )
            return client.fetch_l2_book_snapshot(**kwargs)

    monkeypatch.setattr(
        "tradingbotsuite.v2.collectors.jobs.HyperliquidWebSocketClient",
        FakeHyperliquidWebSocketClient,
    )
    input_spec = {
        "archive_root": str(archive_root),
        "source": "public_websocket",
        "capture_mode": "unattended_session",
        "public_ws_url": "wss://example.test/ws",
        "public_ws_timeout": 3.0,
        "venue": "hyperliquid",
        "instrument_id": INSTRUMENT,
        "coin": "BTC",
        "datatype": datatype,
        "date": "2026-01-01",
        "run_id": f"run-public-ws-session-{datatype}",
        "start_ts": "2026-01-01T00:00:00+00:00",
        "end_ts": "2026-01-01T00:01:00+00:00",
        "max_public_ws_messages": 5,
        "max_public_ws_rows": 4 if datatype == "l2" else 2,
        "max_public_ws_seconds": 3.0,
        "storage_budget_bytes": 1_000_000,
    }
    if datatype == "l2":
        input_spec["n_sig_figs"] = 5
        input_spec["mantissa"] = 2
    store = WorkerJobStore(tmp_path / f"jobs-public-ws-session-{datatype}.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id=f"JOB-public-ws-session-{datatype}",
        input_spec=input_spec,
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        worker_id=f"worker-public-ws-session-{datatype}",
    )
    loaded = store.load_job(queued.job_id)
    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED

    session_path = [
        ref.removeprefix("capture_session_path=")
        for ref in loaded.output_refs
        if ref.startswith("capture_session_path=")
    ][0]
    report = json.loads((archive_root / session_path).read_text(encoding="utf-8"))
    heartbeat_phases = [heartbeat.details.get("phase") for heartbeat in store.list_heartbeats(queued.job_id)]

    assert "collector_mode=public_websocket_l2_bbo_capture_session" in loaded.output_refs
    assert "capture_mode=unattended_session" in loaded.output_refs
    assert "continuous_capture=true" in loaded.output_refs
    assert "accepted_historical_coverage_proof=false" in loaded.output_refs
    assert "unattended_capture_session=true" in loaded.output_refs
    assert "continuous_capture_segment=true" in loaded.output_refs
    assert (
        "public_websocket_capture_session_caveat="
        "bounded_unattended_public_stream_segment_not_historical_coverage_proof"
        in loaded.output_refs
    )
    assert report["capture_mode"] == "unattended_session"
    assert report["datatype"] == datatype
    assert report["stream"] == ("bbo" if datatype == "bbo" else "l2Book")
    assert report["instrument_id"] == INSTRUMENT
    assert report["coin"] == "BTC"
    assert report["continuous_capture"] is True
    assert report["continuous_capture_segment"] is True
    assert report["accepted_historical_coverage_proof"] is False
    assert report["promotion_ready"] is False
    assert report["candidate_evidence"] is False
    assert report["candidate_pack_eligible"] is False
    assert report["live_signal"] is False
    assert report["paper_signal"] is False
    assert report["order_placement_instruction"] is False
    assert report["runtime_mode_change"] is False
    assert report["ws_message_count"] == 2
    assert report["ws_source_row_count"] == (1 if datatype == "bbo" else 4)
    assert report["normalized_row_count"] == 1
    assert "raw_file_id=" in " ".join(report["archive_refs"])
    assert "public_websocket_capture_session" in heartbeat_phases
    assert "public_websocket_capture_session_archived" in heartbeat_phases


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


def test_public_websocket_l2_bbo_worker_rejects_public_websocket_with_local_records(tmp_path) -> None:
    archive_root = tmp_path / "archive-public-ws-l2-reject"
    store = WorkerJobStore(tmp_path / "jobs-public-ws-l2-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id="JOB-public-ws-l2-records-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_websocket",
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
        worker_id="worker-public-ws-l2-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "source=public_websocket cannot include records" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


@pytest.mark.parametrize("datatype", ["bbo", "l2"])
def test_official_s3_l2_replay_records_file_writes_microstructure(
    tmp_path,
    datatype: str,
) -> None:
    trusted_root = tmp_path / "trusted-official-l2"
    trusted_root.mkdir()
    payload_a = _l2_book_payload()
    payload_b = dict(_l2_book_payload())
    payload_b["time"] = int(START.timestamp() * 1000) + 1_000
    records_file = trusted_root / "btc-l2book.jsonl"
    records_file.write_text(
        "\n".join(json.dumps(payload) for payload in (payload_a, payload_b)),
        encoding="utf-8",
    )
    archive_root = tmp_path / f"archive-official-l2-{datatype}"
    store = WorkerJobStore(tmp_path / f"jobs-official-l2-{datatype}.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id=f"JOB-official-l2-{datatype}",
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_l2_replay",
            "records_file": records_file.name,
            "trusted_source_root": str(trusted_root),
            "records_format": "jsonl",
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "datatype": datatype,
            "date": "2026-01-01",
            "run_id": f"run-official-l2-{datatype}",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "official_dataset": "market_data_l2_book",
            "source_endpoint_or_subscription": (
                "s3://hyperliquid-archive/market_data/20260101/0/l2Book/BTC"
            ),
            "storage_budget_bytes": 1_000_000,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        worker_id=f"worker-official-l2-{datatype}",
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
    assert "collector_mode=official_s3_l2_replay_capture" in loaded.output_refs
    assert "source_mode=official_s3_l2_replay" in loaded.output_refs
    assert f"datatype={datatype}" in loaded.output_refs
    assert "row_count=2" in loaded.output_refs
    assert "payload_count=2" in loaded.output_refs
    assert "official_dataset=market_data_l2_book" in loaded.output_refs
    assert "official_dataset_scope=official_hyperliquid_l2_book_snapshots" in loaded.output_refs
    assert "records_file_row_count=2" in loaded.output_refs
    assert "official_s3_network_download=false" in loaded.output_refs
    assert (
        "official_s3_l2_replay_caveat=trusted_decompressed_payloads_not_continuous_coverage"
        in loaded.output_refs
    )
    assert any(ref.startswith("records_file_sha256=") for ref in loaded.output_refs)
    assert [row.datatype for row in manifest_rows] == [datatype]
    assert manifest_rows[0].row_count == 2
    assert [row["event_type"] for row in stored_rows] == [datatype, datatype]
    assert {row["source"] for row in stored_rows} == {"official_s3/market_data_l2_book"}
    if datatype == "bbo":
        assert stored_rows[0]["bid"] == 100.0
        assert stored_rows[0]["ask"] == 100.5
    else:
        assert stored_rows[0]["bid_depth"] == pytest.approx(3.25)
        assert stored_rows[0]["ask_depth"] == pytest.approx(4.75)
        assert stored_rows[0]["book_levels"] == 4


def test_official_s3_l2_replay_rejects_inline_records(tmp_path) -> None:
    archive_root = tmp_path / "archive-official-l2-inline-reject"
    store = WorkerJobStore(tmp_path / "jobs-official-l2-inline-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id="JOB-official-l2-inline-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_l2_replay",
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "datatype": "l2",
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "records": [_l2_book_payload()],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        worker_id="worker-official-l2-inline-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "source=official_s3_l2_replay cannot include records" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_official_s3_l2_replay_rejects_non_l2_dataset(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-official-asset-ctxs"
    trusted_root.mkdir()
    records_file = trusted_root / "asset-ctxs.json"
    records_file.write_text(json.dumps([_l2_book_payload()]), encoding="utf-8")
    archive_root = tmp_path / "archive-official-l2-dataset-reject"
    store = WorkerJobStore(tmp_path / "jobs-official-l2-dataset-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        job_id="JOB-official-l2-dataset-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_l2_replay",
            "records_file": records_file.name,
            "trusted_source_root": str(trusted_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "datatype": "l2",
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "official_dataset": "asset_ctxs",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        worker_id="worker-official-l2-dataset-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "requires official_dataset=market_data_l2_book" in (loaded.failure_reason or "")
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


def test_public_websocket_trade_unattended_session_writes_report(
    tmp_path,
    monkeypatch,
) -> None:
    archive_root = tmp_path / "archive-public-ws-trades-session"

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
    store = WorkerJobStore(tmp_path / "jobs-public-ws-trades-session.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        job_id="JOB-public-ws-trades-session",
        input_spec={
            "archive_root": str(archive_root),
            "source": "public_websocket",
            "capture_mode": "unattended_session",
            "public_ws_url": "wss://example.test/ws",
            "public_ws_timeout": 3.0,
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "coin": "BTC",
            "date": "2026-01-01",
            "run_id": "run-public-ws-trades-session",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "max_public_ws_messages": 5,
            "max_public_ws_rows": 2,
            "max_public_ws_seconds": 3.0,
            "storage_budget_bytes": 1_000_000,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        worker_id="worker-public-ws-trades-session",
    )
    loaded = store.load_job(queued.job_id)
    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED

    session_path = [
        ref.removeprefix("capture_session_path=")
        for ref in loaded.output_refs
        if ref.startswith("capture_session_path=")
    ][0]
    report = json.loads((archive_root / session_path).read_text(encoding="utf-8"))
    heartbeat_phases = [heartbeat.details.get("phase") for heartbeat in store.list_heartbeats(queued.job_id)]

    assert "collector_mode=public_websocket_trade_capture_session" in loaded.output_refs
    assert "capture_mode=unattended_session" in loaded.output_refs
    assert "continuous_capture=true" in loaded.output_refs
    assert "accepted_historical_coverage_proof=false" in loaded.output_refs
    assert "unattended_capture_session=true" in loaded.output_refs
    assert "continuous_capture_segment=true" in loaded.output_refs
    assert (
        "public_websocket_capture_session_caveat="
        "bounded_unattended_public_stream_segment_not_historical_coverage_proof"
        in loaded.output_refs
    )
    assert report["stream"] == "trades"
    assert report["datatype"] == "trades"
    assert report["instrument_id"] == INSTRUMENT
    assert report["continuous_capture"] is True
    assert report["accepted_historical_coverage_proof"] is False
    assert report["candidate_pack_eligible"] is False
    assert report["order_placement_instruction"] is False
    assert report["ws_message_count"] == 2
    assert report["ws_source_row_count"] == 3
    assert report["normalized_row_count"] == 2
    assert "raw_file_id=" in " ".join(report["archive_refs"])
    assert "public_websocket_capture_session" in heartbeat_phases
    assert "public_websocket_capture_session_archived" in heartbeat_phases


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


def test_official_s3_node_fills_replay_records_file_writes_trade_rows(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-official-node-fills"
    trusted_root.mkdir()
    records_file = trusted_root / "node-fills-by-block.jsonl"
    payloads = [
        {
            "block_time": "2026-01-01T00:00:00Z",
            "fills": [
                {
                    "coin": "BTC",
                    "side": "B",
                    "time": 1767225600000,
                    "px": "100.0",
                    "sz": "1.25",
                    "hash": "0xhash-a",
                    "tid": 101,
                },
                {
                    "coin": "SOL",
                    "side": "A",
                    "time": 1767225600500,
                    "px": "150.0",
                    "sz": "3.0",
                    "hash": "0xhash-sol",
                    "tid": 102,
                },
            ],
        },
        {
            "fills": [
                {
                    "coin": "BTC",
                    "side": "A",
                    "time": 1767225601000,
                    "px": "100.5",
                    "sz": "2.00",
                    "hash": "0xhash-b",
                    "tid": 103,
                }
            ]
        },
    ]
    records_file.write_text("\n".join(json.dumps(payload) for payload in payloads), encoding="utf-8")
    archive_root = tmp_path / "archive-official-node-fills"
    store = WorkerJobStore(tmp_path / "jobs-official-node-fills.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        job_id="JOB-official-node-fills",
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_node_trade_replay",
            "records_file": records_file.name,
            "trusted_source_root": str(trusted_root),
            "records_format": "jsonl",
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "coin": "BTC",
            "date": "2026-01-01",
            "run_id": "run-official-node-fills",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "official_dataset": "node_fills_by_block",
            "source_endpoint_or_subscription": "s3://hl-mainnet-node-data/node_fills_by_block/00000001.lz4",
            "storage_budget_bytes": 1_000_000,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        worker_id="worker-official-node-fills",
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
    assert "collector_mode=official_s3_node_trade_replay_capture" in loaded.output_refs
    assert "source_mode=official_s3_node_trade_replay" in loaded.output_refs
    assert "datatype=trades" in loaded.output_refs
    assert "row_count=2" in loaded.output_refs
    assert "trade_row_count=2" in loaded.output_refs
    assert "payload_count=2" in loaded.output_refs
    assert "skipped_row_count=1" in loaded.output_refs
    assert "official_dataset=node_fills_by_block" in loaded.output_refs
    assert "official_dataset_scope=official_hyperliquid_node_fills_by_block" in loaded.output_refs
    assert "records_file_row_count=2" in loaded.output_refs
    assert "coin=BTC" in loaded.output_refs
    assert "official_s3_network_download=false" in loaded.output_refs
    assert (
        "official_s3_node_trade_replay_caveat=trusted_decompressed_payloads_not_coverage_certification"
        in loaded.output_refs
    )
    assert any(ref.startswith("records_file_sha256=") for ref in loaded.output_refs)
    assert [row.datatype for row in manifest_rows] == ["trades"]
    assert manifest_rows[0].row_count == 2
    assert [row["event_type"] for row in stored_rows] == ["trade", "trade"]
    assert {row["instrument_id"] for row in stored_rows} == {INSTRUMENT}
    assert {row["source"] for row in stored_rows} == {"official_s3/node_fills_by_block"}
    assert [row["price"] for row in stored_rows] == [100.0, 100.5]
    assert [row["size"] for row in stored_rows] == [1.25, 2.0]
    assert [row["side"] for row in stored_rows] == ["B", "A"]
    assert [row["trade_id"] for row in stored_rows] == [
        "BTC:1767225600000:101",
        "BTC:1767225601000:103",
    ]


def test_official_s3_node_trades_replay_accepts_l1_trade_shape(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-official-node-trades"
    trusted_root.mkdir()
    records_file = trusted_root / "node-trades.json"
    records_file.write_text(
        json.dumps(
            [
                {
                    "coin": "BTC",
                    "side": "B",
                    "time": "2024-07-26T08:26:25.899",
                    "px": "51.367",
                    "sz": "0.31",
                    "hash": "0xad8e0566e813bdf98176040e6d51bd011100efa789e89430cdf17964235f55d8",
                    "side_info": [
                        {"user": "0xbuyer", "oid": 1},
                        {"user": "0xseller", "oid": 2},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    archive_root = tmp_path / "archive-official-node-trades"
    store = WorkerJobStore(tmp_path / "jobs-official-node-trades.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        job_id="JOB-official-node-trades",
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_node_trade_replay",
            "records_file": records_file.name,
            "trusted_source_root": str(trusted_root),
            "records_format": "json",
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "coin": "BTC",
            "date": "2024-07-26",
            "run_id": "run-official-node-trades",
            "start_ts": "2024-07-26T08:00:00+00:00",
            "end_ts": "2024-07-26T09:00:00+00:00",
            "official_dataset": "node_trades",
            "source_endpoint_or_subscription": "s3://hl-mainnet-node-data/node_trades/hourly/20240726/08",
            "storage_budget_bytes": 1_000_000,
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        worker_id="worker-official-node-trades",
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
    assert "official_dataset=node_trades" in loaded.output_refs
    assert "official_dataset_scope=official_hyperliquid_node_trades_legacy" in loaded.output_refs
    assert "row_count=1" in loaded.output_refs
    assert stored_rows[0]["ts"] == "2024-07-26T08:26:25.899000Z"
    assert stored_rows[0]["source"] == "official_s3/node_trades"
    assert stored_rows[0]["trade_id"] == (
        "0xad8e0566e813bdf98176040e6d51bd011100efa789e89430cdf17964235f55d8:0"
    )


def test_official_s3_node_trade_replay_rejects_inline_records(tmp_path) -> None:
    archive_root = tmp_path / "archive-official-node-trades-inline-reject"
    store = WorkerJobStore(tmp_path / "jobs-official-node-trades-inline-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        job_id="JOB-official-node-trades-inline-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_node_trade_replay",
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "official_dataset": "node_fills",
            "records": [{"coin": "BTC", "time": 1767225600000, "px": "100", "sz": "1"}],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        worker_id="worker-official-node-trades-inline-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "source=official_s3_node_trade_replay cannot include records" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_official_s3_node_trade_replay_rejects_non_node_dataset(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-official-node-trades-dataset-reject"
    trusted_root.mkdir()
    records_file = trusted_root / "node-trades.json"
    records_file.write_text(
        json.dumps([{"coin": "BTC", "time": 1767225600000, "px": "100", "sz": "1"}]),
        encoding="utf-8",
    )
    archive_root = tmp_path / "archive-official-node-trades-dataset-reject"
    store = WorkerJobStore(tmp_path / "jobs-official-node-trades-dataset-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        job_id="JOB-official-node-trades-dataset-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_node_trade_replay",
            "records_file": records_file.name,
            "trusted_source_root": str(trusted_root),
            "venue": "hyperliquid",
            "instrument_id": INSTRUMENT,
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "official_dataset": "asset_ctxs",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        worker_id="worker-official-node-trades-dataset-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "requires official_dataset=node_fills_by_block" in (loaded.failure_reason or "")
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


def test_official_s3_asset_ctxs_replay_records_file_writes_context_layers(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-official-asset-ctxs"
    trusted_root.mkdir()
    records_file = trusted_root / "asset-ctxs.json"
    records_file.write_text(
        json.dumps(
            [
                {
                    "universe": [
                        {"name": "BTC"},
                        {"name": "SOL"},
                    ]
                },
                [
                    {
                        "ts": "2026-01-01T00:00:00Z",
                        "markPx": "60000",
                        "oraclePx": "60001",
                        "openInterest": "10",
                        "dayNtlVlm": "100000000",
                        "funding": "0.0001",
                    },
                    {
                        "ts": "2026-01-01T00:00:00Z",
                        "markPx": "150",
                        "oraclePx": "151",
                        "openInterest": "20",
                        "dayNtlVlm": "12000000",
                        "funding": "0.0002",
                    },
                ],
            ]
        ),
        encoding="utf-8",
    )
    archive_root = tmp_path / "archive-official-asset-ctxs"
    store = WorkerJobStore(tmp_path / "jobs-official-asset-ctxs.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        job_id="JOB-official-asset-ctxs",
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_asset_ctxs_replay",
            "records_file": records_file.name,
            "trusted_source_root": str(trusted_root),
            "records_format": "json",
            "venue": "hyperliquid",
            "date": "2026-01-01",
            "run_id": "run-official-asset-ctxs",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "official_dataset": "asset_ctxs",
            "source_endpoint_or_subscription": "s3://hyperliquid-archive/asset_ctxs/20260101.lz4",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        worker_id="worker-official-asset-ctxs",
    )
    loaded = store.load_job(queued.job_id)
    layout = ArchiveLayout(archive_root)
    manifest_rows = ArchiveManifestStore(layout).load_file_manifest()
    silver_file = [
        row
        for row in manifest_rows
        if row.layer == ArchiveLayer.SILVER and row.datatype == "asset_contexts"
    ][0]
    silver_rows = [
        SilverAssetContextRow.model_validate(row)
        for row in pq.ParquetFile(layout.resolve(silver_file.path)).read().to_pylist()
    ]

    assert result is not None
    assert result.status == WorkerJobStatus.SUCCEEDED
    assert loaded is not None
    assert loaded.status == WorkerJobStatus.SUCCEEDED
    assert "collector_mode=official_s3_asset_ctxs_replay_archive_write" in loaded.output_refs
    assert "source_mode=official_s3_asset_ctxs_replay" in loaded.output_refs
    assert "row_count=2" in loaded.output_refs
    assert "raw_record_count=1" in loaded.output_refs
    assert "context_row_count=2" in loaded.output_refs
    assert "official_dataset=asset_ctxs" in loaded.output_refs
    assert "official_dataset_scope=official_hyperliquid_asset_contexts" in loaded.output_refs
    assert "records_file_row_count=1" in loaded.output_refs
    assert "official_s3_network_download=false" in loaded.output_refs
    assert (
        "official_s3_asset_ctxs_replay_caveat=trusted_decompressed_payloads_not_continuous_coverage"
        in loaded.output_refs
    )
    assert any(ref.startswith("records_file_sha256=") for ref in loaded.output_refs)
    assert {(row.layer, row.datatype) for row in manifest_rows} >= {
        (ArchiveLayer.RAW, "asset_contexts"),
        (ArchiveLayer.BRONZE, "asset_contexts"),
        (ArchiveLayer.SILVER, "asset_contexts"),
    }
    assert {row.instrument_id for row in silver_rows} == {"BTC", "SOL"}
    btc = [row for row in silver_rows if row.instrument_id == "BTC"][0]
    assert btc.mark_price == 60000
    assert btc.oracle_price == 60001
    assert btc.open_interest == 10
    assert btc.day_notional_volume_usd == 100000000
    assert btc.funding_rate == 0.0001
    assert btc.research_only is True
    assert btc.observe_only is True
    assert btc.promotion_ready is False


def test_official_s3_asset_ctxs_replay_rejects_inline_records(tmp_path) -> None:
    archive_root = tmp_path / "archive-official-asset-ctxs-inline-reject"
    store = WorkerJobStore(tmp_path / "jobs-official-asset-ctxs-inline-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        job_id="JOB-official-asset-ctxs-inline-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_asset_ctxs_replay",
            "venue": "hyperliquid",
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "official_dataset": "asset_ctxs",
            "records": [{"contexts": []}],
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        worker_id="worker-official-asset-ctxs-inline-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "source=official_s3_asset_ctxs_replay cannot include records" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_official_s3_asset_ctxs_replay_rejects_wrong_official_dataset(tmp_path) -> None:
    trusted_root = tmp_path / "trusted-official-asset-ctxs-wrong-dataset"
    trusted_root.mkdir()
    records_file = trusted_root / "asset-ctxs.json"
    records_file.write_text(json.dumps([{"contexts": []}]), encoding="utf-8")
    archive_root = tmp_path / "archive-official-asset-ctxs-dataset-reject"
    store = WorkerJobStore(tmp_path / "jobs-official-asset-ctxs-dataset-reject.sqlite")
    queued = store.enqueue(
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        job_id="JOB-official-asset-ctxs-dataset-reject",
        max_attempts=1,
        input_spec={
            "archive_root": str(archive_root),
            "source": "official_s3_asset_ctxs_replay",
            "records_file": records_file.name,
            "trusted_source_root": str(trusted_root),
            "venue": "hyperliquid",
            "date": "2026-01-01",
            "start_ts": "2026-01-01T00:00:00+00:00",
            "end_ts": "2026-01-01T00:01:00+00:00",
            "official_dataset": "market_data_l2_book",
        },
    )

    result = run_one_job(
        store=store,
        kind=WorkerJobKind.OFFICIAL_S3_BACKFILL,
        worker_id="worker-official-asset-ctxs-dataset-reject",
    )
    loaded = store.load_job(queued.job_id)

    assert result is not None
    assert result.status == WorkerJobStatus.FAILED
    assert loaded is not None
    assert "requires official_dataset=asset_ctxs" in (loaded.failure_reason or "")
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


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


def _fake_bbo_websocket_connect(url: str, **kwargs):
    assert url == "wss://example.test/ws"
    assert kwargs == {"open_timeout": 3.0}
    return _FakeBboWebSocket()


def _fake_l2_book_websocket_connect(url: str, **kwargs):
    assert url == "wss://example.test/ws"
    assert kwargs == {"open_timeout": 3.0}
    return _FakeL2BookWebSocket()


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


class _FakeBboWebSocket:
    def __init__(self) -> None:
        self.messages = [
            {"channel": "subscriptionResponse", "data": {"subscription": {"type": "bbo", "coin": "BTC"}}},
            {
                "channel": "bbo",
                "data": {
                    "coin": "BTC",
                    "time": 1_767_225_600_000,
                    "bbo": [
                        {"px": "100.0", "sz": "1.25", "n": 2},
                        {"px": "100.5", "sz": "1.50", "n": 3},
                    ],
                },
            },
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def send(self, raw_message: str) -> None:
        assert json.loads(raw_message) == {
            "method": "subscribe",
            "subscription": {"type": "bbo", "coin": "BTC"},
        }

    def recv(self, timeout=None) -> str:
        if not self.messages:
            raise TimeoutError("no more messages")
        return json.dumps(self.messages.pop(0))


class _FakeL2BookWebSocket:
    def __init__(self) -> None:
        self.messages = [
            {
                "channel": "subscriptionResponse",
                "data": {
                    "subscription": {
                        "type": "l2Book",
                        "coin": "BTC",
                        "nSigFigs": 5,
                        "mantissa": 2,
                    }
                },
            },
            {"channel": "l2Book", "data": _l2_book_payload()},
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def send(self, raw_message: str) -> None:
        assert json.loads(raw_message) == {
            "method": "subscribe",
            "subscription": {"type": "l2Book", "coin": "BTC", "nSigFigs": 5, "mantissa": 2},
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
