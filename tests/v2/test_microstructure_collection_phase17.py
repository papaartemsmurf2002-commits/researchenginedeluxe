from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

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
