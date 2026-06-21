from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.market_data import (
    SilverAssetContextRow,
    SilverBarRow,
    SilverFundingIntervalRow,
)
from tradingbotsuite.v2.archive.normalization_store import NormalizationManifestStore
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter
from tradingbotsuite.v2.archive.rebuild import (
    bronze_asset_contexts_to_silver,
    bronze_candles_to_silver_bars,
    bronze_funding_to_silver,
    raw_asset_contexts_to_bronze,
    raw_candles_to_bronze,
    raw_funding_to_bronze,
)
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore


ROOT = Path(__file__).resolve().parents[3]
START = datetime(2026, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 1, 1, tzinfo=UTC)


def test_raw_candles_flow_to_bronze_silver_derived_coverage_and_snapshot(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    raw = _write_raw(
        archive_root=archive_root,
        datatype="candles",
        records=[_candle(index) for index in range(60)],
        run_id="run-candles",
        job_id="job-raw-candles",
        instrument_id="hyperliquid:perp:BTC",
        timeframe="1m",
    )

    bronze = raw_candles_to_bronze(
        archive_root=archive_root,
        raw_file_id=raw.file_id,
        job_id="job-bronze-candles",
    )
    silver = bronze_candles_to_silver_bars(
        archive_root=archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id="job-silver-bars",
        create_snapshot=True,
    )

    store = ArchiveManifestStore(ArchiveLayout(archive_root))
    manifest_rows = store.load_file_manifest()
    silver_rows = [row for row in manifest_rows if row.layer == ArchiveLayer.SILVER and row.datatype == "bars"]
    by_timeframe = {row.timeframe: row for row in silver_rows}
    one_hour_rows = _read_rows(archive_root, by_timeframe["1h"], SilverBarRow)
    coverage_reports = CoverageManifestStore(ArchiveLayout(archive_root)).load_coverage_reports()

    assert bronze.output_files[0].source_file_ids == (raw.file_id,)
    assert {row.timeframe for row in silver_rows} == {"1m", "5m", "15m", "1h"}
    assert by_timeframe["1m"].row_count == 60
    assert by_timeframe["5m"].row_count == 12
    assert by_timeframe["15m"].row_count == 4
    assert by_timeframe["1h"].row_count == 1
    assert one_hour_rows[0].open == 100
    assert one_hour_rows[0].close == 159
    assert one_hour_rows[0].high == 160
    assert one_hour_rows[0].low == 99
    assert one_hour_rows[0].volume == sum(10 + index for index in range(60))
    assert all(report.coverage_ratio == 1.0 for report in coverage_reports)
    assert set(silver.coverage_report_ids) == {report.coverage_report_id for report in coverage_reports}
    assert silver.archive_snapshot_id is not None
    assert store.load_archive_snapshots()[0].archive_snapshot_id == silver.archive_snapshot_id


def test_incomplete_derived_windows_are_recorded_in_normalization_manifest(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    raw = _write_raw(
        archive_root=archive_root,
        datatype="candles",
        records=[_candle(index) for index in range(10) if index != 7],
        run_id="run-gap-candles",
        job_id="job-gap-raw",
        instrument_id="hyperliquid:perp:BTC",
        timeframe="1m",
    )
    bronze = raw_candles_to_bronze(
        archive_root=archive_root,
        raw_file_id=raw.file_id,
        job_id="job-gap-bronze",
    )

    result = bronze_candles_to_silver_bars(
        archive_root=archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id="job-gap-silver",
        derive_timeframes=("5m",),
    )
    manifests = NormalizationManifestStore(ArchiveLayout(archive_root)).load()
    five_minute_manifest = [row for row in manifests if row.dataset == "bars" and row.timeframe == "5m"][0]
    five_minute_file = [row for row in result.output_files if row.timeframe == "5m"][0]

    assert five_minute_file.row_count == 1
    assert five_minute_manifest.gap_count == 1
    assert five_minute_manifest.gap_reasons[0].startswith("incomplete_5m_window:")
    coverage = CoverageManifestStore(ArchiveLayout(archive_root)).load_coverage_reports()
    one_minute_report = [report for report in coverage if report.timeframe == "1m"][0]
    assert one_minute_report.coverage_ratio == 0.9
    assert "coverage_below_minimum" in one_minute_report.blocker_reasons


def test_raw_funding_rows_normalize_to_silver_utc_intervals(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    raw = _write_raw(
        archive_root=archive_root,
        datatype="funding",
        records=[
            {
                "ts": "2026-01-01T00:00:00Z",
                "end_ts": "2026-01-01T01:00:00Z",
                "coin": "BTC",
                "fundingRate": "0.0001",
            }
        ],
        run_id="run-funding",
        job_id="job-raw-funding",
        instrument_id="hyperliquid:perp:BTC",
    )
    bronze = raw_funding_to_bronze(
        archive_root=archive_root,
        raw_file_id=raw.file_id,
        job_id="job-bronze-funding",
        instrument_id="hyperliquid:perp:BTC",
    )

    silver = bronze_funding_to_silver(
        archive_root=archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id="job-silver-funding",
    )
    rows = _read_rows(archive_root, silver.output_files[0], SilverFundingIntervalRow)

    assert rows[0].interval_start_ts == START
    assert rows[0].interval_end_ts == START + timedelta(hours=1)
    assert rows[0].funding_rate == 0.0001
    assert rows[0].source_file_id == bronze.output_files[0].file_id


def test_raw_asset_context_rows_normalize_context_fields(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    raw = _write_raw(
        archive_root=archive_root,
        datatype="asset_contexts",
        records=[
            {
                "contexts": [
                    {
                        "ts": "2026-01-01T00:00:00Z",
                        "coin": "BTC",
                        "markPx": "60000",
                        "oraclePx": "60001",
                        "openInterest": "10",
                        "dayNtlVlm": "100000000",
                        "funding": "0.0001",
                    },
                    {
                        "ts": "2026-01-01T00:00:00Z",
                        "coin": "SOL",
                        "markPx": "150",
                        "oraclePx": "151",
                        "openInterest": "20",
                        "dayNtlVlm": "12000000",
                        "funding": "0.0002",
                    },
                ]
            }
        ],
        run_id="run-context",
        job_id="job-raw-context",
    )
    bronze = raw_asset_contexts_to_bronze(
        archive_root=archive_root,
        raw_file_id=raw.file_id,
        job_id="job-bronze-context",
    )

    silver = bronze_asset_contexts_to_silver(
        archive_root=archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id="job-silver-context",
    )
    rows = _read_rows(archive_root, silver.output_files[0], SilverAssetContextRow)

    assert {row.instrument_id for row in rows} == {"BTC", "SOL"}
    btc = [row for row in rows if row.instrument_id == "BTC"][0]
    assert btc.mark_price == 60000
    assert btc.oracle_price == 60001
    assert btc.open_interest == 10
    assert btc.day_notional_volume_usd == 100000000
    assert btc.funding_rate == 0.0001
    assert btc.missing_fields == ()


def test_archive_rebuild_cli_builds_bronze_and_silver(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    raw = _write_raw(
        archive_root=archive_root,
        datatype="candles",
        records=[_candle(index) for index in range(5)],
        run_id="run-cli-candles",
        job_id="job-cli-raw",
        instrument_id="hyperliquid:perp:BTC",
        timeframe="1m",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    bronze = _run_cli(
        [
            "archive",
            "build-bronze",
            "--archive-root",
            str(archive_root),
            "--raw-file-id",
            raw.file_id,
            "--datatype",
            "candles",
            "--job-id",
            "job-cli-bronze",
        ],
        env=env,
    )
    bronze_file_id = _extract_value(bronze.stdout, "output_file_ids").split(",")[0]
    silver = _run_cli(
        [
            "archive",
            "build-silver",
            "--archive-root",
            str(archive_root),
            "--bronze-file-id",
            bronze_file_id,
            "--datatype",
            "candles",
            "--job-id",
            "job-cli-silver",
            "--derive-timeframes",
            "5m",
            "--snapshot",
        ],
        env=env,
    )

    assert bronze.returncode == 0
    assert "normalization_manifest_ids=" in bronze.stdout
    assert silver.returncode == 0
    assert "coverage_report_ids=" in silver.stdout
    assert "archive_snapshot_id=" in silver.stdout


def _write_raw(
    *,
    archive_root: Path,
    datatype: str,
    records,
    run_id: str,
    job_id: str,
    instrument_id: str | None = None,
    timeframe: str | None = None,
):
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    return RawJsonlZstdWriter(layout, store).write_records(
        records=records,
        venue="hyperliquid",
        datatype=datatype,
        date="2026-01-01",
        run_id=run_id,
        job_id=job_id,
        adapter_id="fixture",
        source_endpoint_or_subscription="fixture",
        symbols=("BTC",),
        start_ts=START,
        end_ts=END,
        instrument_id=instrument_id,
        timeframe=timeframe,
    )


def _candle(index: int):
    ts = START + timedelta(minutes=index)
    return {
        "ts": ts.isoformat().replace("+00:00", "Z"),
        "end_ts": (ts + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        "coin": "hyperliquid:perp:BTC",
        "timeframe": "1m",
        "open": 100 + index,
        "high": 101 + index,
        "low": 99 + index,
        "close": 100 + index,
        "volume": 10 + index,
        "trade_count": index + 1,
    }


def _read_rows(archive_root: Path, manifest_row, model):
    rows = pq.ParquetFile(ArchiveLayout(archive_root).resolve(manifest_row.path)).read().to_pylist()
    return [model.model_validate(row) for row in rows]


def _run_cli(args: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tradingbotsuite.v2.cli.main", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _extract_value(stdout: str, key: str) -> str:
    for line in stdout.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"{key} not found in stdout: {stdout}")
