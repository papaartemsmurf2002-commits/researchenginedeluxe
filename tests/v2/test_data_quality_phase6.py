from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.backtest_data.coverage_gate import (
    CoverageGateError,
    require_coverage_for_evidence,
)
from tradingbotsuite.v2.data_quality.coverage import (
    coverage_report_for_timestamped_rows,
    coverage_report_for_bars,
    expected_bar_count,
    iter_expected_bar_timestamps,
)
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode, QualityStatus


ROOT = Path(__file__).resolve().parents[2]
START = datetime(2026, 1, 1, tzinfo=UTC)


def test_expected_row_calculators_for_bar_timeframes() -> None:
    assert expected_bar_count(START, START + timedelta(hours=1), "1m") == 60
    assert expected_bar_count(START, START + timedelta(hours=1), "5m") == 12
    assert expected_bar_count(START, START + timedelta(hours=3), "1h") == 3
    assert expected_bar_count(START, START + timedelta(days=3), "1d") == 3
    assert list(iter_expected_bar_timestamps(START, START + timedelta(minutes=30), "1h")) == []


def test_coverage_report_manifest_is_queryable_by_instrument_date_timeframe(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    rows = [
        _bar("2026-01-01T00:00:00Z", close=100),
        _bar("2026-01-03T00:00:00Z", close=102),
    ]
    report = coverage_report_for_bars(
        rows,
        venue="hyperliquid",
        instrument_id="hyperliquid:perp:SOL",
        timeframe="1d",
        start_ts=START,
        end_ts=START + timedelta(days=3),
    )
    store = CoverageManifestStore(layout)
    store.append_coverage_report(report)

    queried = store.query_coverage_reports(
        instrument_id="hyperliquid:perp:SOL",
        timeframe="1d",
        window_date="2026-01-02",
    )

    assert queried == [report]
    assert queried[0].missing_days == ("2026-01-02",)
    assert queried[0].missing_timestamp_count == 1


def test_coverage_below_098_fails_accepted_evidence_gate() -> None:
    rows = [_bar(START + timedelta(minutes=index), close=100 + index) for index in range(97)]
    report = coverage_report_for_bars(
        rows,
        venue="hyperliquid",
        instrument_id="hyperliquid:perp:BTC",
        timeframe="1m",
        start_ts=START,
        end_ts=START + timedelta(minutes=100),
        evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
    )

    assert report.coverage_ratio == 0.97
    assert report.evidence_eligible is False
    assert "coverage_below_minimum" in report.blocker_reasons
    with pytest.raises(CoverageGateError, match="coverage_below_minimum"):
        require_coverage_for_evidence(report)


def test_timestamped_event_coverage_uses_nonempty_buckets_not_event_count() -> None:
    rows = [
        {"ts": "2026-01-01T00:00:00Z", "sequence": 0, "price": 100.0},
        {"ts": "2026-01-01T00:00:00Z", "sequence": 0, "price": 100.0},
        {"ts": "2026-01-01T00:02:00Z", "sequence": 2, "price": 101.0},
        {"sequence": 3, "price": 102.0},
    ]

    report = coverage_report_for_timestamped_rows(
        rows,
        venue="hyperliquid",
        instrument_id="hyperliquid:perp:BTC",
        family="trades",
        timeframe="1m",
        start_ts=START,
        end_ts=START + timedelta(minutes=3),
        force_non_evidence_reason="raw_microstructure_not_accepted_coverage_evidence",
    )

    assert report.expected_rows == 3
    assert report.observed_rows == 2
    assert report.source_row_count == 4
    assert report.coverage_ratio == pytest.approx(2 / 3)
    assert report.missing_timestamps_sample == ("2026-01-01T00:01:00Z",)
    assert report.duplicate_timestamp_count == 1
    assert report.parse_failure_count == 1
    assert report.quality_status == QualityStatus.NON_EVIDENCE
    assert report.evidence_eligible is False
    assert set(report.blocker_reasons) == {
        "coverage_below_minimum",
        "duplicate_event_keys",
        "parse_failures",
        "raw_microstructure_not_accepted_coverage_evidence",
    }


def test_timestamped_context_coverage_can_pass_when_buckets_are_present() -> None:
    rows = [
        {"ts": "2026-01-01T00:00:00Z", "mark_price": 100.0},
        {"ts": "2026-01-02T00:00:00Z", "mark_price": 101.0},
    ]

    report = coverage_report_for_timestamped_rows(
        rows,
        venue="hyperliquid",
        instrument_id="hyperliquid:perp:BTC",
        family="asset_contexts",
        timeframe="1d",
        start_ts=START,
        end_ts=START + timedelta(days=2),
    )

    assert report.expected_rows == 2
    assert report.observed_rows == 2
    assert report.coverage_ratio == 1.0
    assert report.quality_status == QualityStatus.PASS
    assert report.evidence_eligible is True
    assert report.blocker_reasons == ()


def test_sandbox_diagnostic_low_coverage_is_labeled_non_evidence() -> None:
    rows = [_bar(START + timedelta(minutes=index), close=100 + index) for index in range(97)]
    report = coverage_report_for_bars(
        rows,
        venue="hyperliquid",
        instrument_id="hyperliquid:perp:BTC",
        timeframe="1m",
        start_ts=START,
        end_ts=START + timedelta(minutes=100),
        evidence_mode=EvidenceMode.SANDBOX_DIAGNOSTIC,
    )

    assert report.quality_status == QualityStatus.NON_EVIDENCE
    assert report.evidence_eligible is False
    assert report.blocker_reasons == ("sandbox_diagnostic_non_evidence",)
    assert "coverage_below_minimum" not in report.blocker_reasons
    with pytest.raises(CoverageGateError, match="sandbox_diagnostic_non_evidence"):
        require_coverage_for_evidence(report)


def test_duplicate_zero_stale_and_outlier_checks_are_reported() -> None:
    rows = [
        _bar("2026-01-01T00:00:00Z", close=100, volume=1, spread=0.001, funding=0.0),
        _bar("2026-01-01T00:01:00Z", close=100, volume=1, spread=0.001, funding=0.0),
        _bar("2026-01-01T00:01:00Z", close=100, volume=1, spread=0.001, funding=0.0),
        _bar("2026-01-01T00:02:00Z", close=100, volume=0, spread=0.001, funding=0.0),
        _bar("2026-01-01T00:03:00Z", close=300, volume=1, spread=0.001, funding=0.0),
        _bar("2026-01-01T00:04:00Z", close=300, volume=1, spread=0.2, funding=0.2),
    ]

    report = coverage_report_for_bars(
        rows,
        venue="hyperliquid",
        instrument_id="hyperliquid:perp:BTC",
        timeframe="1m",
        start_ts=START,
        end_ts=START + timedelta(minutes=5),
    )

    assert report.coverage_ratio == 1.0
    assert report.duplicate_timestamp_count == 1
    assert report.zero_volume_count == 1
    assert report.stale_segment_count == 1
    assert report.return_outlier_count == 1
    assert report.spread_outlier_count == 1
    assert report.funding_outlier_count == 1
    assert set(report.blocker_reasons) >= {
        "duplicate_timestamps",
        "zero_volume_rows",
        "stale_segments",
        "outliers",
    }


def test_data_coverage_and_quality_report_cli_write_manifests(tmp_path) -> None:
    parquet_path = tmp_path / "bars.parquet"
    _write_parquet(
        parquet_path,
        [
            _bar("2026-01-01T00:00:00Z", close=100),
            _bar("2026-01-01T00:01:00Z", close=100),
        ],
    )
    archive_root = tmp_path / "archive"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    coverage = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "data",
            "coverage",
            "--archive-root",
            str(archive_root),
            "--input-parquet",
            str(parquet_path),
            "--venue",
            "hyperliquid",
            "--instrument-id",
            "hyperliquid:perp:BTC",
            "--timeframe",
            "1m",
            "--start-ts",
            "2026-01-01T00:00:00+00:00",
            "--end-ts",
            "2026-01-01T00:03:00+00:00",
            "--write-manifest",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert coverage.returncode == 1
    assert "coverage_ratio=0.666666666667" in coverage.stdout
    assert "coverage_below_minimum" in coverage.stdout
    assert (archive_root / "manifests" / "data_coverage.parquet").exists()

    quality = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "data",
            "quality-report",
            "--archive-root",
            str(archive_root),
            "--input-parquet",
            str(parquet_path),
            "--venue",
            "hyperliquid",
            "--instrument-id",
            "hyperliquid:perp:BTC",
            "--timeframe",
            "1m",
            "--start-ts",
            "2026-01-01T00:00:00+00:00",
            "--end-ts",
            "2026-01-01T00:03:00+00:00",
            "--write-manifest",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert quality.returncode == 0
    assert "duplicate_timestamps\tpass\t0" in quality.stdout
    assert (archive_root / "manifests" / "data_quality_checks.parquet").exists()


def _bar(ts, *, close: float, volume: float = 1, spread: float = 0.001, funding: float = 0.0):
    if isinstance(ts, datetime):
        ts = ts.isoformat().replace("+00:00", "Z")
    return {
        "ts": ts,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": volume,
        "spread": spread,
        "funding": funding,
    }


def _write_parquet(path: Path, rows) -> None:
    pq.write_table(pa.Table.from_pylist(rows), path)
