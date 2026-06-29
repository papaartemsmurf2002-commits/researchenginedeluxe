from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.backtest_data import (
    BacktestDataError,
    BacktestDataRequest,
    BacktestDataService,
    BacktestEvidenceMode,
    latest_full_calendar_month_lockbox,
)
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode
from tradingbotsuite.v2.universe.hyperliquid import refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode


ROOT = Path(__file__).resolve().parents[2]
VENUE = "hyperliquid"
INSTRUMENT = "hyperliquid:perp:SOL"


def test_latest_full_calendar_month_lockbox_calculator() -> None:
    window = latest_full_calendar_month_lockbox(asof_date=date(2026, 6, 21))

    assert window.start_ts == datetime(2026, 5, 1, tzinfo=UTC)
    assert window.end_ts == datetime(2026, 6, 1, tzinfo=UTC)


def test_reported_backtest_rejects_start_before_2024() -> None:
    request = _request(
        archive_root="unused",
        archive_snapshot_id="a" * 64,
        universe_snapshot_id="b" * 64,
        start_ts=datetime(2023, 12, 1, tzinfo=UTC),
        end_ts=datetime(2024, 6, 1, tzinfo=UTC),
    )

    with pytest.raises(BacktestDataError, match="reported_start_before_earliest"):
        BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))


def test_accepted_backtest_rejects_less_than_six_usable_months() -> None:
    request = _request(
        archive_root="unused",
        archive_snapshot_id="a" * 64,
        universe_snapshot_id="b" * 64,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 6, 30, tzinfo=UTC),
    )

    with pytest.raises(BacktestDataError, match="usable_months_below_minimum"):
        BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))


def test_lockbox_overlap_fails_before_archive_lookup() -> None:
    request = _request(
        archive_root="unused",
        archive_snapshot_id="a" * 64,
        universe_snapshot_id="b" * 64,
        start_ts=datetime(2025, 12, 1, tzinfo=UTC),
        end_ts=datetime(2026, 6, 1, tzinfo=UTC),
    )

    with pytest.raises(BacktestDataError, match="lockbox_overlap"):
        BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))


def test_current_universe_evidence_request_fails(tmp_path) -> None:
    fixture = _archive_fixture(
        tmp_path,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
        universe_mode=UniverseMode.CURRENT_LABELED_SANDBOX,
    )
    request = _request(
        archive_root=str(fixture.archive_root),
        archive_snapshot_id=fixture.archive_snapshot_id,
        universe_snapshot_id=fixture.universe_snapshot_id,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
    )

    with pytest.raises(BacktestDataError, match="current_universe_evidence_rejected"):
        BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))


def test_valid_request_loads_only_requested_fields_and_writes_manifest(tmp_path) -> None:
    fixture = _archive_fixture(
        tmp_path,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
    )
    request = _request(
        archive_root=str(fixture.archive_root),
        archive_snapshot_id=fixture.archive_snapshot_id,
        universe_snapshot_id=fixture.universe_snapshot_id,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
        requested_fields=("ts", "close"),
    )

    first = BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))
    second = BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))
    manifest_path = fixture.archive_root / "manifests" / "backtest_data_requests.parquet"
    manifest_index_path = fixture.archive_root / "manifests" / "backtest_data_requests.index.json"
    manifest_rows = pq.read_table(manifest_path).to_pylist()
    manifest_index = json.loads(manifest_index_path.read_text(encoding="utf-8"))

    assert len(first.rows) == 182
    assert first.reported_row_count == 182
    assert first.warmup_row_count == 0
    assert first.loaded_fields == ("ts", "close")
    assert set(first.rows[0]) == {"ts", "close"}
    assert "open" not in first.rows[0]
    assert first.data_manifest.data_manifest_id == second.data_manifest.data_manifest_id
    assert len(manifest_rows) == 1
    assert manifest_rows[0]["data_manifest_id"] == first.data_manifest.data_manifest_id
    assert manifest_index["schema_version"] == "backtest_data_request_index_v1"
    assert manifest_index["row_count"] == 1
    assert manifest_index["data_manifest_ids"] == {first.data_manifest.data_manifest_id: 0}


def test_columnar_request_matches_row_slice_without_duplicate_manifest(tmp_path) -> None:
    fixture = _archive_fixture(
        tmp_path,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
    )
    request = _request(
        archive_root=str(fixture.archive_root),
        archive_snapshot_id=fixture.archive_snapshot_id,
        universe_snapshot_id=fixture.universe_snapshot_id,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
        requested_fields=("ts", "instrument_id", "open", "close"),
    )

    row_slice = BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))
    columnar_slice = BacktestDataService().load_panel_columnar(request, asof_date=date(2026, 6, 21))
    manifest_path = fixture.archive_root / "manifests" / "backtest_data_requests.parquet"
    manifest_rows = pq.read_table(manifest_path).to_pylist()

    assert columnar_slice.table.num_rows == len(row_slice.rows)
    assert columnar_slice.table.schema.names == ["ts", "instrument_id", "open", "close"]
    assert columnar_slice.data_manifest.data_manifest_id == row_slice.data_manifest.data_manifest_id
    assert columnar_slice.warmup_row_count == row_slice.warmup_row_count
    assert columnar_slice.reported_row_count == row_slice.reported_row_count
    assert columnar_slice.to_rows() == row_slice.rows
    assert len(manifest_rows) == 1


def test_multi_instrument_request_loads_panel_with_coverage_provenance(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 7, 1, tzinfo=UTC)
    instrument_ids = ("hyperliquid:perp:SOL", "hyperliquid:perp:BTC")
    reports = []
    for index, instrument_id in enumerate(instrument_ids):
        rows = _daily_bar_rows(
            start_ts,
            end_ts,
            missing_day_offsets=set(),
            instrument_id=instrument_id,
        )
        write_parquet_rows(
            layout=layout,
            store=store,
            rows=rows,
            layer=ArchiveLayer.SILVER,
            dataset="bars",
            venue=VENUE,
            datatype="bars",
            date=start_ts.date().isoformat(),
            timeframe="1d",
            job_id=f"job-silver-bars-{index}",
            source_file_ids=(f"source-fixture-{index}",),
            instrument_id=instrument_id,
        )
        report = coverage_report_for_bars(
            rows,
            venue=VENUE,
            instrument_id=instrument_id,
            timeframe="1d",
            start_ts=start_ts,
            end_ts=end_ts,
            evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
        )
        CoverageManifestStore(layout).append_coverage_report(report)
        reports.append(report)
    snapshot = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope=VENUE,
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=[report.model_dump(mode="json") for report in reports],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="phase9_multi_instrument_test_fixture",
    )
    universe = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_multi_payload(),
        asof_date=start_ts.date(),
        mode=UniverseMode.AS_OF,
    )
    request = BacktestDataRequest(
        archive_root=str(archive_root),
        archive_snapshot_id=snapshot.archive_snapshot_id,
        universe_snapshot_id=universe.snapshot_id,
        venue=VENUE,
        instrument_id=instrument_ids[0],
        instrument_ids=instrument_ids,
        timeframe="1d",
        start_ts=start_ts,
        end_ts=end_ts,
        requested_fields=("ts", "instrument_id", "close"),
        evidence_mode=BacktestEvidenceMode.ACCEPTED_RESEARCH,
    )

    result = BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))

    assert len(result.rows) == 364
    assert {row["instrument_id"] for row in result.rows} == set(instrument_ids)
    assert result.data_manifest.instrument_ids == instrument_ids
    assert result.coverage_report_ids == tuple(report.coverage_report_id for report in reports)
    assert len(result.coverage_report_id) == 64
    assert result.coverage_report_id not in {report.coverage_report_id for report in reports}


def test_warmup_rows_are_separate_from_reported_window(tmp_path) -> None:
    fixture = _archive_fixture(
        tmp_path,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 8, 1, tzinfo=UTC),
    )
    request = _request(
        archive_root=str(fixture.archive_root),
        archive_snapshot_id=fixture.archive_snapshot_id,
        universe_snapshot_id=fixture.universe_snapshot_id,
        start_ts=datetime(2024, 2, 1, tzinfo=UTC),
        end_ts=datetime(2024, 8, 1, tzinfo=UTC),
        warmup_start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        requested_fields=("ts", "close"),
    )

    result = BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))

    assert result.warmup_row_count == 31
    assert result.reported_row_count == 182
    assert len(result.rows) == 213
    assert result.rows[0]["ts"] == datetime(2024, 1, 1, tzinfo=UTC)
    assert result.rows[31]["ts"] == datetime(2024, 2, 1, tzinfo=UTC)


def test_coverage_below_098_fails_accepted_evidence(tmp_path) -> None:
    fixture = _archive_fixture(
        tmp_path,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
        missing_day_offsets=set(range(10)),
    )
    request = _request(
        archive_root=str(fixture.archive_root),
        archive_snapshot_id=fixture.archive_snapshot_id,
        universe_snapshot_id=fixture.universe_snapshot_id,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
    )

    with pytest.raises(BacktestDataError, match="coverage_below_minimum"):
        BacktestDataService().load_panel(request, asof_date=date(2026, 6, 21))


def test_backtest_data_cli_load_panel(tmp_path) -> None:
    fixture = _archive_fixture(
        tmp_path,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "backtest-data",
            "load-panel",
            "--archive-root",
            str(fixture.archive_root),
            "--archive-snapshot-id",
            fixture.archive_snapshot_id,
            "--universe-snapshot-id",
            fixture.universe_snapshot_id,
            "--venue",
            VENUE,
            "--instrument-id",
            INSTRUMENT,
            "--timeframe",
            "1d",
            "--start-ts",
            "2024-01-01T00:00:00+00:00",
            "--end-ts",
            "2024-07-01T00:00:00+00:00",
            "--field",
            "ts",
            "--field",
            "close",
            "--asof-date",
            "2026-06-21",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "data_manifest_id=" in result.stdout
    assert "loaded_fields=ts,close" in result.stdout
    assert "reported_row_count=182" in result.stdout


class _Fixture:
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


def _archive_fixture(
    tmp_path: Path,
    *,
    start_ts: datetime,
    end_ts: datetime,
    universe_mode: UniverseMode = UniverseMode.AS_OF,
    missing_day_offsets: set[int] | None = None,
) -> _Fixture:
    archive_root = tmp_path / "archive"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    rows = _daily_bar_rows(start_ts, end_ts, missing_day_offsets=missing_day_offsets or set())
    write_parquet_rows(
        layout=layout,
        store=store,
        rows=rows,
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue=VENUE,
        datatype="bars",
        date=start_ts.date().isoformat(),
        timeframe="1d",
        job_id="job-silver-bars",
        source_file_ids=("source-fixture",),
        instrument_id=INSTRUMENT,
    )
    report = coverage_report_for_bars(
        rows,
        venue=VENUE,
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
        venue_scope=VENUE,
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=[report.model_dump(mode="json")],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="phase9_test_fixture",
    )
    universe = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(),
        asof_date=start_ts.date(),
        mode=universe_mode,
    )
    return _Fixture(
        archive_root=archive_root,
        archive_snapshot_id=snapshot.archive_snapshot_id,
        universe_snapshot_id=universe.snapshot_id,
    )


def _daily_bar_rows(
    start_ts: datetime,
    end_ts: datetime,
    *,
    missing_day_offsets: set[int],
    instrument_id: str = INSTRUMENT,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start_ts
    index = 0
    while current < end_ts:
        if index not in missing_day_offsets:
            close = 100.0 + index
            rows.append(
                {
                    "venue": VENUE,
                    "instrument_id": instrument_id,
                    "timeframe": "1d",
                    "ts": _iso(current),
                    "end_ts": _iso(current + timedelta(days=1)),
                    "open": close - 0.25,
                    "high": close + 0.5,
                    "low": close - 0.5,
                    "close": close,
                    "volume": 1000.0 + index,
                    "trade_count": index + 1,
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


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _request(
    *,
    archive_root: str,
    archive_snapshot_id: str,
    universe_snapshot_id: str,
    start_ts: datetime,
    end_ts: datetime,
    warmup_start_ts: datetime | None = None,
    requested_fields: tuple[str, ...] = ("ts", "open", "high", "low", "close", "volume"),
) -> BacktestDataRequest:
    return BacktestDataRequest(
        archive_root=archive_root,
        archive_snapshot_id=archive_snapshot_id,
        universe_snapshot_id=universe_snapshot_id,
        venue=VENUE,
        instrument_id=INSTRUMENT,
        timeframe="1d",
        start_ts=start_ts,
        end_ts=end_ts,
        warmup_start_ts=warmup_start_ts,
        requested_fields=requested_fields,
        evidence_mode=BacktestEvidenceMode.ACCEPTED_RESEARCH,
    )


def _payload():
    return [
        {
            "universe": [
                {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
                {"name": "LOW", "szDecimals": 1, "maxLeverage": 5},
            ]
        },
        [
            {
                "dayNtlVlm": "12000000",
                "openInterest": "20",
                "markPx": "150",
                "oraclePx": "151",
                "funding": "0.0002",
            },
            {
                "dayNtlVlm": "1000",
                "openInterest": "1",
                "markPx": "1",
                "oraclePx": "1",
                "funding": "0.0",
            },
        ],
    ]


def _multi_payload():
    return [
        {
            "universe": [
                {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
                {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
            ]
        },
        [
            {
                "dayNtlVlm": "12000000",
                "openInterest": "20",
                "markPx": "150",
                "oraclePx": "151",
                "funding": "0.0002",
            },
            {
                "dayNtlVlm": "100000000",
                "openInterest": "1000",
                "markPx": "60000",
                "oraclePx": "60001",
                "funding": "0.0001",
            },
        ],
    ]
