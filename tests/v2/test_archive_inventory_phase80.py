from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tradingbotsuite.v2.cli.main import main
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.archive_inventory import ArchiveInventoryService
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode


def test_archive_inventory_discovers_manifest_coverage_and_fields(tmp_path: Path) -> None:
    fixture = _archive_fixture(tmp_path)
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=fixture["archive_root"],
        collection_ledger_path=tmp_path / "missing-ledger.json",
    )

    inventory = service.build_inventory()
    records = service.query(instrument_id="hyperliquid:perp:SOL", family="bars", timeframe="1d")
    derived_records = service.query(
        instrument_id="hyperliquid:perp:SOL",
        family="derived_bar_context",
        timeframe="1d",
    )

    assert inventory.summary.record_count == 2
    assert inventory.summary.accepted_research_record_count == 2
    assert records[0].accepted_research_evidence_allowed is True
    assert records[0].archive_snapshot_id == fixture["archive_snapshot_id"]
    assert records[0].coverage_report_id == fixture["coverage_report_id"]
    assert records[0].row_count == 182
    assert {"ts", "open", "close", "volume"} <= set(records[0].field_names)
    assert records[0].usable_archive_ref.startswith("archive://hyperliquid/bars/")
    assert derived_records[0].evidence_scope == "archive_feature_projection"
    assert derived_records[0].usable_archive_ref.startswith("archive://hyperliquid/bars/")


def test_archive_inventory_query_filters_evidence_scope_acceptance_and_coverage(tmp_path: Path, capsys) -> None:
    fixture = _archive_fixture(tmp_path)
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=fixture["archive_root"],
        collection_ledger_path=tmp_path / "missing-ledger.json",
    )

    accepted_records = service.query(
        instrument_id="hyperliquid:perp:SOL",
        family="bars",
        timeframe="1d",
        evidence_scope="accepted_research",
        coverage_report_id=str(fixture["coverage_report_id"]),
        accepted_only=True,
    )
    nonmatching_records = service.query(
        instrument_id="hyperliquid:perp:SOL",
        family="bars",
        timeframe="1d",
        evidence_scope="central_collection_ledger",
        accepted_only=True,
    )
    cli_exit = main(
        [
            "archive-inventory",
            "--repo-root",
            str(tmp_path),
            "--archive-root",
            str(fixture["archive_root"]),
            "--instrument-id",
            "hyperliquid:perp:SOL",
            "--family",
            "bars",
            "--timeframe",
            "1d",
            "--evidence-scope",
            "accepted_research",
            "--coverage-report-id",
            str(fixture["coverage_report_id"]),
            "--accepted-only",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert len(accepted_records) == 1
    assert accepted_records[0].coverage_report_id == fixture["coverage_report_id"]
    assert accepted_records[0].accepted_research_evidence_allowed is True
    assert nonmatching_records == ()
    assert cli_exit == 0
    assert len(payload) == 1
    assert payload[0]["coverage_report_id"] == fixture["coverage_report_id"]
    assert payload[0]["evidence_scope"] == "accepted_research"
    assert payload[0]["accepted_research_evidence_allowed"] is True


def test_archive_inventory_cli_honors_repeated_instrument_filters(tmp_path: Path, capsys) -> None:
    fixture = _archive_fixture(
        tmp_path,
        instrument_ids=("hyperliquid:perp:SOL", "hyperliquid:perp:ETH"),
    )

    exit_code = main(
        [
            "archive-inventory",
            "--repo-root",
            str(tmp_path),
            "--archive-root",
            str(fixture["archive_root"]),
            "--instrument-id",
            "hyperliquid:perp:SOL",
            "--instrument-id",
            "hyperliquid:perp:ETH",
            "--family",
            "bars",
            "--timeframe",
            "1d",
            "--accepted-only",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [row["instrument_id"] for row in payload] == [
        "hyperliquid:perp:ETH",
        "hyperliquid:perp:SOL",
    ]
    assert all(row["accepted_research_evidence_allowed"] is True for row in payload)


def _archive_fixture(
    tmp_path: Path,
    *,
    instrument_ids: tuple[str, ...] = ("hyperliquid:perp:SOL",),
) -> dict[str, object]:
    archive_root = tmp_path / "archive"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 7, 1, tzinfo=UTC)
    coverage_store = CoverageManifestStore(layout)
    reports = []
    for index, instrument_id in enumerate(instrument_ids):
        rows = _daily_bar_rows(start_ts, end_ts, instrument_id=instrument_id, price_offset=index * 10.0)
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
            job_id=f"job-silver-bars-{index}",
            source_file_ids=(f"source-fixture-{index}",),
            instrument_id=instrument_id,
        )
        report = coverage_report_for_bars(
            rows,
            venue="hyperliquid",
            instrument_id=instrument_id,
            timeframe="1d",
            start_ts=start_ts,
            end_ts=end_ts,
            evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
        )
        coverage_store.append_coverage_report(report)
        reports.append(report)
    snapshot = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope="hyperliquid",
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=[report.model_dump(mode="json") for report in reports],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="phase80_inventory_fixture",
    )
    return {
        "archive_root": archive_root,
        "archive_snapshot_id": snapshot.archive_snapshot_id,
        "coverage_report_id": reports[0].coverage_report_id,
        "coverage_report_ids": tuple(report.coverage_report_id for report in reports),
    }


def _daily_bar_rows(
    start_ts: datetime,
    end_ts: datetime,
    *,
    instrument_id: str = "hyperliquid:perp:SOL",
    price_offset: float = 0.0,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start_ts
    index = 0
    while current < end_ts:
        close = 100.0 + price_offset + index
        rows.append(
            {
                "venue": "hyperliquid",
                "instrument_id": instrument_id,
                "timeframe": "1d",
                "ts": current.isoformat().replace("+00:00", "Z"),
                "end_ts": (current + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
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
