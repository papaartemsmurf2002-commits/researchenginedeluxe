from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter, read_jsonl_zstd
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot


ROOT = Path(__file__).resolve().parents[3]
START = datetime(2026, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 2, tzinfo=UTC)


def test_archive_init_command_creates_directory_tree_safely(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "archive",
            "init",
            "--archive-root",
            str(archive_root),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "archive_initialized=" in result.stdout
    for dirname in ArchiveLayout.REQUIRED_DIRS:
        assert (archive_root / dirname).is_dir()


def test_raw_payload_written_before_normalization(tmp_path) -> None:
    layout = ArchiveLayout(tmp_path / "archive")
    layout.initialize()
    store = ArchiveManifestStore(layout)
    writer = RawJsonlZstdWriter(layout, store)

    manifest_row = writer.write_records(
        records=[{"coin": "BTC", "price": "1"}, {"coin": "ETH", "price": "2"}],
        venue="hyperliquid",
        datatype="meta_and_asset_ctxs",
        date="2026-01-01",
        run_id="run-raw",
        job_id="job-raw",
        adapter_id="hyperliquid_native_v1",
        source_endpoint_or_subscription="info/metaAndAssetCtxs",
        symbols=("BTC", "ETH"),
        start_ts=START,
        end_ts=END,
    )

    raw_path = layout.resolve(manifest_row.path)
    assert raw_path.exists()
    assert manifest_row.layer == ArchiveLayer.RAW
    assert not any(layout.layer_root(ArchiveLayer.BRONZE).rglob("*.parquet"))
    assert read_jsonl_zstd(
        raw_path,
        uncompressed_size=manifest_row.uncompressed_size_bytes or 0,
    ) == [{"coin": "BTC", "price": "1"}, {"coin": "ETH", "price": "2"}]


def test_file_manifest_has_sha256_size_rows_schema_version(tmp_path) -> None:
    layout = ArchiveLayout(tmp_path / "archive")
    layout.initialize()
    store = ArchiveManifestStore(layout)
    writer = RawJsonlZstdWriter(layout, store)

    manifest_row = writer.write_records(
        records=[{"t": 1}],
        venue="hyperliquid",
        datatype="candles",
        date="2026-01-01",
        run_id="run-manifest",
        job_id="job-manifest",
        adapter_id="hyperliquid_native_v1",
        source_endpoint_or_subscription="websocket/candle",
        symbols=("BTC",),
        start_ts=START,
        end_ts=END,
        instrument_id="BTC",
        timeframe="1m",
    )
    stored = store.load_file_manifest()
    runs = store.load_ingestion_runs()

    assert stored == [manifest_row]
    assert len(manifest_row.sha256) == 64
    assert manifest_row.size_bytes > 0
    assert manifest_row.row_count == 1
    assert manifest_row.schema_version.startswith("redx-v2")
    assert manifest_row.source_file_ids == ()
    assert len(runs) == 1
    assert runs[0].row_count == 1
    assert runs[0].byte_count == manifest_row.size_bytes


def test_archive_manifest_store_batch_upsert_dedupes_and_orders_file_rows(tmp_path) -> None:
    layout = ArchiveLayout(tmp_path / "archive")
    layout.initialize()
    store = ArchiveManifestStore(layout)
    first = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[{"ts": "2026-01-01T00:00:00Z", "close": 1.0}],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date="2026-01-01",
        timeframe="1m",
        job_id="job-first",
        source_file_ids=("source-a",),
        filename="part-b",
    )
    second = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[{"ts": "2026-01-01T00:01:00Z", "close": 2.0}],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date="2026-01-01",
        timeframe="1m",
        job_id="job-second",
        source_file_ids=("source-b",),
        filename="part-a",
    )

    replacement = first.model_copy(update={"created_by_job_id": "job-first-replacement"})
    store.upsert_file_manifests((second, first, replacement))

    rows = store.load_file_manifest()
    assert [row.path for row in rows] == sorted(row.path for row in rows)
    assert len(rows) == 2
    assert {row.file_id for row in rows} == {first.file_id, second.file_id}
    assert next(row for row in rows if row.file_id == first.file_id).created_by_job_id == "job-first-replacement"


def test_bronze_to_silver_rebuild_is_deterministic(tmp_path) -> None:
    first = _build_bronze_silver_fixture(tmp_path / "one")
    second = _build_bronze_silver_fixture(tmp_path / "two")

    assert first == second


def test_archive_snapshot_id_changes_when_input_changes(tmp_path) -> None:
    layout = ArchiveLayout(tmp_path / "archive")
    layout.initialize()
    store = ArchiveManifestStore(layout)
    silver_one = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[{"ts": "2026-01-01T00:00:00Z", "close": 1.0}],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date="2026-01-01",
        timeframe="1m",
        job_id="job-silver",
        source_file_ids=("source-a",),
    )
    first = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope="hyperliquid",
        start_ts=START,
        end_ts=END,
    )
    write_parquet_rows(
        layout=layout,
        store=store,
        rows=[{"ts": "2026-01-01T00:01:00Z", "close": 2.0}],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date="2026-01-01",
        timeframe="1m",
        job_id="job-silver-2",
        source_file_ids=(silver_one.file_id,),
    )
    second = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope="hyperliquid",
        start_ts=START,
        end_ts=END,
    )

    assert first.archive_snapshot_id != second.archive_snapshot_id


def test_archive_snapshot_command_writes_snapshot_record(tmp_path) -> None:
    layout = ArchiveLayout(tmp_path / "archive")
    layout.initialize()
    store = ArchiveManifestStore(layout)
    write_parquet_rows(
        layout=layout,
        store=store,
        rows=[{"ts": "2026-01-01T00:00:00Z", "close": 1.0}],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date="2026-01-01",
        timeframe="1m",
        job_id="job-silver",
        source_file_ids=("source-a",),
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "archive",
            "snapshot",
            "--archive-root",
            str(layout.root),
            "--layer",
            "silver",
            "--venue-scope",
            "hyperliquid",
            "--start-ts",
            "2026-01-01T00:00:00+00:00",
            "--end-ts",
            "2026-01-02T00:00:00+00:00",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "archive_snapshot_id=" in result.stdout
    assert len(store.load_archive_snapshots()) == 1


def test_archive_validate_detects_missing_manifest_file(tmp_path) -> None:
    layout = ArchiveLayout(tmp_path / "archive")
    layout.initialize()
    store = ArchiveManifestStore(layout)
    writer = RawJsonlZstdWriter(layout, store)
    manifest_row = writer.write_records(
        records=[{"t": 1}],
        venue="hyperliquid",
        datatype="trades",
        date="2026-01-01",
        run_id="run-missing",
        job_id="job-missing",
        adapter_id="hyperliquid_native_v1",
        source_endpoint_or_subscription="websocket/trades",
        symbols=("BTC",),
        start_ts=START,
        end_ts=END,
    )

    layout.resolve(manifest_row.path).unlink()
    issues = store.validate_files()

    assert [issue.code for issue in issues] == ["manifest_file_missing"]

    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "archive",
            "validate",
            "--archive-root",
            str(layout.root),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "archive_valid=false" in result.stdout
    assert "manifest_file_missing" in result.stdout


def _build_bronze_silver_fixture(root: Path) -> tuple[str, str, str]:
    layout = ArchiveLayout(root / "archive")
    layout.initialize()
    store = ArchiveManifestStore(layout)
    raw = RawJsonlZstdWriter(layout, store).write_records(
        records=[{"ts": "2026-01-01T00:00:00Z", "close": 1.0}],
        venue="hyperliquid",
        datatype="candles",
        date="2026-01-01",
        run_id="run-deterministic",
        job_id="job-raw",
        adapter_id="hyperliquid_native_v1",
        source_endpoint_or_subscription="fixture",
        symbols=("BTC",),
        start_ts=START,
        end_ts=END,
    )
    bronze = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[{"ts": "2026-01-01T00:00:00Z", "close": 1.0}],
        layer=ArchiveLayer.BRONZE,
        dataset="candles",
        venue="hyperliquid",
        datatype="candles",
        date="2026-01-01",
        timeframe="1m",
        job_id="job-bronze",
        source_file_ids=(raw.file_id,),
    )
    silver = write_parquet_rows(
        layout=layout,
        store=store,
        rows=[{"ts": "2026-01-01T00:00:00Z", "close": 1.0}],
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="hyperliquid",
        datatype="bars",
        date="2026-01-01",
        timeframe="1m",
        job_id="job-silver",
        source_file_ids=(bronze.file_id,),
    )
    snapshot = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope="hyperliquid",
        start_ts=START,
        end_ts=END,
    )
    return bronze.sha256, silver.sha256, snapshot.archive_snapshot_id
