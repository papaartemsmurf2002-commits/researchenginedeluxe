from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode
from tradingbotsuite.v2.feature_store import FeatureStoreCatalogService
from tradingbotsuite.v2.universe.hyperliquid import refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode

ROOT = Path(__file__).resolve().parents[2]


def test_feature_store_catalog_discovers_materialized_of_style_report(tmp_path: Path) -> None:
    report_path = (
        tmp_path
        / "data"
        / "research"
        / "of_style_feature_materialization"
        / "wpr_test"
        / "manifests"
        / "wpr-test-feature-materialization-report.json"
    )
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps(_report(), sort_keys=True), encoding="utf-8")

    catalog = FeatureStoreCatalogService(repo_root=tmp_path).build_catalog()

    assert catalog.entry_count == 1
    assert catalog.feature_families == ("derivatives_context",)
    entry = catalog.entries[0]
    assert entry.symbol == "SOL"
    assert entry.instrument_id == "binance:perp:SOLUSDT"
    assert entry.timeframe == "1m"
    assert entry.row_count == 1440
    assert entry.usable_archive_ref.startswith("feature://derivatives_context/SOL/")
    assert entry.accepted_research_evidence_allowed is False
    assert entry.research_only is True
    assert entry.promotion_ready is False


def test_feature_store_catalog_projects_archive_backed_funding_oi_spread_and_derived_features(tmp_path: Path) -> None:
    archive_root = _write_archive_feature_fixture(tmp_path)

    catalog = FeatureStoreCatalogService(
        repo_root=tmp_path,
        archive_root=archive_root,
        materialization_report_paths=(),
    ).build_catalog()

    assert {
        "funding",
        "open_interest",
        "bbo_spread",
        "kline_context",
        "derived_bar_context",
    } <= set(catalog.feature_families)
    by_family = {entry.feature_family: entry for entry in catalog.entries}
    assert by_family["funding"].instrument_id == "hyperliquid:perp:SOL"
    assert by_family["funding"].accepted_research_evidence_allowed is True
    assert by_family["funding"].evidence_scope == "archive_feature_projection"
    assert by_family["funding"].usable_archive_ref.startswith("archive://hyperliquid/bars/")
    assert by_family["open_interest"].row_count == 213
    assert by_family["bbo_spread"].timeframe == "1d"
    assert by_family["derived_bar_context"].research_only is True
    assert by_family["derived_bar_context"].promotion_ready is False


def test_feature_store_catalog_query_filters_accepted_archive_backed_features(tmp_path: Path) -> None:
    report_path = (
        tmp_path
        / "data"
        / "research"
        / "of_style_feature_materialization"
        / "wpr_test"
        / "manifests"
        / "wpr-test-feature-materialization-report.json"
    )
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps(_report(), sort_keys=True), encoding="utf-8")
    archive_root = _write_archive_feature_fixture(tmp_path)
    service = FeatureStoreCatalogService(repo_root=tmp_path, archive_root=archive_root)

    accepted = service.query(
        feature_family="funding",
        source_family="bars",
        venue="hyperliquid",
        instrument_id="hyperliquid:perp:SOL",
        timeframe="1d",
        evidence_scope="archive_feature_projection",
        accepted_only=True,
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
    )
    non_evidence = service.query(feature_family="derivatives_context", accepted_only=True)

    assert len(accepted) == 1
    assert accepted[0].usable_archive_ref.startswith("archive://hyperliquid/bars/")
    assert non_evidence == ()


def test_archive_inventory_feature_catalog_cli_filters_existing_features(tmp_path: Path) -> None:
    archive_root = _write_archive_feature_fixture(tmp_path)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "archive-inventory",
            "--repo-root",
            str(tmp_path),
            "--archive-root",
            str(archive_root),
            "--feature-catalog",
            "--feature-family",
            "funding",
            "--source-family",
            "bars",
            "--venue",
            "hyperliquid",
            "--instrument-id",
            "hyperliquid:perp:SOL",
            "--timeframe",
            "1d",
            "--accepted-only",
            "--start-ts",
            "2024-01-01T00:00:00Z",
            "--end-ts",
            "2024-07-01T00:00:00Z",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    entries = json.loads(result.stdout)
    assert len(entries) == 1
    assert entries[0]["feature_family"] == "funding"
    assert entries[0]["accepted_research_evidence_allowed"] is True
    assert entries[0]["research_only"] is True
    assert entries[0]["promotion_ready"] is False


def test_archive_inventory_feature_catalog_cli_honors_repeated_instrument_filters(tmp_path: Path) -> None:
    report_path = (
        tmp_path
        / "data"
        / "research"
        / "of_style_feature_materialization"
        / "wpr_test"
        / "manifests"
        / "wpr-test-feature-materialization-report.json"
    )
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps(_report(symbols=("SOL", "ETH")), sort_keys=True), encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "archive-inventory",
            "--repo-root",
            str(tmp_path),
            "--archive-root",
            str(tmp_path / "missing-archive"),
            "--feature-catalog",
            "--feature-family",
            "derivatives_context",
            "--instrument-id",
            "binance:perp:SOLUSDT",
            "--instrument-id",
            "binance:perp:ETHUSDT",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    entries = json.loads(result.stdout)
    assert [entry["instrument_id"] for entry in entries] == [
        "binance:perp:ETHUSDT",
        "binance:perp:SOLUSDT",
    ]
    assert all(entry["feature_family"] == "derivatives_context" for entry in entries)
    assert all(entry["research_only"] is True for entry in entries)
    assert all(entry["promotion_ready"] is False for entry in entries)


def _report(*, symbols: tuple[str, ...] = ("SOL",)) -> dict:
    boundary = {
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
    }
    return {
        "schema_version": "v2",
        "report_type": "of_style_feature_materialization_report",
        "materialization_report_id": "r" * 64,
        "source_results": [
            {
                "schema_version": "v2",
                "source_result_id": chr(115 + index) * 64,
                "family": "metrics",
                "feature_family": "derivatives_context",
                "dataset": "metrics",
                "symbol": symbol,
                "venue_symbol": f"{symbol}USDT",
                "interval": "1m",
                "day": "2024-01-01",
                "source_ref": f"data/futures/um/daily/metrics/{symbol}USDT/source.zip",
                "output_format": "jsonl",
                "output_ref": f"features/derivatives_context/metrics/{symbol}USDT/native/source.jsonl",
                "output_sha256": "a" * 64,
                "output_bytes": 100,
                "output_part_refs": [],
                "output_part_count": 0,
                "status": "materialized",
                "input_row_count": 1440,
                "feature_row_count": 1440,
                "row_manifest_hash": "b" * 64,
                "blocker_reasons": [],
                **boundary,
            }
            for index, symbol in enumerate(symbols)
        ],
        **boundary,
    }


def _write_archive_feature_fixture(tmp_path: Path) -> Path:
    archive_root = tmp_path / "archive"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 8, 1, tzinfo=UTC)
    rows = _daily_rows(start_ts, end_ts)
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
        job_id="feature-store-silver-bars",
        source_file_ids=("source-feature-store",),
        instrument_id="hyperliquid:perp:SOL",
    )
    coverage = coverage_report_for_bars(
        rows,
        venue="hyperliquid",
        instrument_id="hyperliquid:perp:SOL",
        timeframe="1d",
        start_ts=start_ts,
        end_ts=end_ts,
        evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
    )
    CoverageManifestStore(layout).append_coverage_report(coverage)
    create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope="hyperliquid",
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=[coverage.model_dump(mode="json")],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="phase80_feature_store_fixture",
    )
    refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=[
            {"universe": [{"name": "SOL", "szDecimals": 2, "maxLeverage": 20}]},
            [
                {
                    "dayNtlVlm": "12000000",
                    "openInterest": "20",
                    "markPx": "150",
                    "oraclePx": "151",
                    "funding": "0.0002",
                }
            ],
        ],
        asof_date=date(2024, 1, 1),
        mode=UniverseMode.AS_OF,
    )
    return archive_root


def _daily_rows(start_ts: datetime, end_ts: datetime) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start_ts
    index = 0
    while current < end_ts:
        close = 100.0 + index
        rows.append(
            {
                "venue": "hyperliquid",
                "instrument_id": "hyperliquid:perp:SOL",
                "timeframe": "1d",
                "ts": current.isoformat().replace("+00:00", "Z"),
                "end_ts": (current + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "open": close - 0.25,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 1000.0 + index,
                "trade_count": index + 1,
                "funding": 0.00001,
                "funding_rate": 0.00001,
                "open_interest": 2_000_000.0 + index,
                "mark_price": close,
                "oracle_price": close,
                "spread": 0.001,
                "coverage_ratio": 1.0,
                "source_timeframe": "1d",
                "source_file_id": "f" * 64,
                "source_layer": "bronze",
                "normalization_warnings": (),
                **dict(RESEARCH_BOUNDARY),
            }
        )
        current += timedelta(days=1)
        index += 1
    return rows
