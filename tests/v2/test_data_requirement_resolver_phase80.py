from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.archive_inventory import (
    ArtifactMode,
    ArchiveInventoryService,
    StrategyDataRequirementRequest,
)
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode
from tradingbotsuite.v2.feature_store.schemas import FeatureCatalog, FeatureCatalogEntry
from tradingbotsuite.v2.strategy_specs.examples import example_strategy_payloads
from tradingbotsuite.v2.universe.hyperliquid import refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode


def test_resolver_returns_existing_archive_refs_for_testable_bar_strategy(tmp_path: Path) -> None:
    ledger_path = _write_collection_ledger(tmp_path)
    spec = _spec("hl_mean_reversion_v1", fields=["close", "volume", "coverage_ratio"])
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=tmp_path / "missing-archive",
        collection_ledger_path=ledger_path,
    )

    report = service.resolve_strategy_data_requirements(
        StrategyDataRequirementRequest(
            strategy_spec=spec,
            repo_root=str(tmp_path),
            archive_root=str(tmp_path / "missing-archive"),
            instrument_ids=("hyperliquid:perp:SOL",),
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 7, 1, tzinfo=UTC),
            evidence_mode="accepted_research",
            artifact_mode=ArtifactMode.METRICS_ONLY,
            prefer_fast_lane=True,
        ),
        asof_date=date(2026, 6, 21),
    )

    assert report.ready is True
    assert report.usable_instruments == ("hyperliquid:perp:SOL",)
    assert report.missing_fields == ()
    assert report.data_gap_requests == ()
    assert report.do_not_collect_reason == "existing_archive_refs_sufficient"
    assert report.artifact_mode == ArtifactMode.METRICS_ONLY
    assert report.fast_lane_policy.reference_engine_authority is True
    assert report.recommended_engine_lane == "fast_vectorized"
    assert report.reference_audit_required is True
    assert report.fast_lane_reason == "prefer_fast_lane_requested"
    assert any(ref.startswith("ledger://") for ref in report.usable_archive_refs)


def test_resolver_returns_bounded_data_gap_for_missing_funding_family(tmp_path: Path) -> None:
    ledger_path = _write_collection_ledger(tmp_path)
    spec = _spec("hl_funding_carry_v1", fields=["close", "funding", "volume", "coverage_ratio"])
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=tmp_path / "missing-archive",
        collection_ledger_path=ledger_path,
    )

    report = service.resolve_strategy_data_requirements(
        StrategyDataRequirementRequest(
            strategy_spec=spec,
            repo_root=str(tmp_path),
            archive_root=str(tmp_path / "missing-archive"),
            instrument_ids=("hyperliquid:perp:SOL",),
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 7, 1, tzinfo=UTC),
            evidence_mode="accepted_research",
        ),
        asof_date=date(2026, 6, 21),
    )

    assert report.ready is False
    assert report.usable_instruments == ()
    assert report.missing_instruments == ("hyperliquid:perp:SOL",)
    assert "funding" in report.missing_fields
    assert "funding" in report.missing_families
    assert "derivatives_context" in report.missing_families
    assert report.data_gap_requests
    assert all(gap.strategy_id == "hl_funding_carry_v1" for gap in report.data_gap_requests)
    assert all(gap.start_ts == datetime(2024, 1, 1, tzinfo=UTC) for gap in report.data_gap_requests)
    assert all(gap.end_ts == datetime(2024, 7, 1, tzinfo=UTC) for gap in report.data_gap_requests)
    assert any(ref.startswith("ledger://") for ref in report.usable_archive_refs)
    assert not any(ref.startswith("feature://") for ref in report.usable_archive_refs)
    assert "materialize_feature_family:derivatives_context" in report.required_feature_materializations


def test_resolver_recommends_fast_lane_for_large_sweeps_without_changing_readiness(tmp_path: Path) -> None:
    spec = _spec("hl_mean_reversion_v1", fields=["close", "volume", "coverage_ratio"])
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=tmp_path / "missing-archive",
        collection_ledger_path=tmp_path / "missing-ledger.json",
    )
    instrument_ids = tuple(f"hyperliquid:perp:SYM{index}" for index in range(10))

    report = service.resolve_strategy_data_requirements(
        StrategyDataRequirementRequest(
            strategy_spec=spec,
            repo_root=str(tmp_path),
            archive_root=str(tmp_path / "missing-archive"),
            instrument_ids=instrument_ids,
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 7, 1, tzinfo=UTC),
            evidence_mode="accepted_research",
        ),
        asof_date=date(2026, 6, 21),
    )

    assert report.ready is False
    assert report.recommended_engine_lane == "fast_vectorized"
    assert report.reference_audit_required is True
    assert report.fast_lane_reason == "large_sweep_instrument_count>=10"
    assert report.fast_lane_policy.reference_engine_authority is True
    bars_gap = next(gap for gap in report.data_gap_requests if gap.requested_family == "bars")
    assert bars_gap.venue_probe_allowed is True
    assert bars_gap.existing_archive_refs_checked == (
        "archive_inventory://checked/no_usable_refs"
        "?family=bars&venue=hyperliquid&instruments=hyperliquid:perp:SYM0",
    )


def test_resolver_uses_archive_backed_funding_oi_and_spread_fields_before_gap_requests(tmp_path: Path) -> None:
    archive_root = _write_archive_feature_fixture(tmp_path)
    spec = _spec(
        "hl_funding_carry_v1",
        fields=[
            "close",
            "funding",
            "funding_rate",
            "open_interest",
            "spread",
            "volume",
            "coverage_ratio",
        ],
    )
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=archive_root,
        collection_ledger_path=tmp_path / "missing-ledger.json",
    )

    report = service.resolve_strategy_data_requirements(
        StrategyDataRequirementRequest(
            strategy_spec=spec,
            repo_root=str(tmp_path),
            archive_root=str(archive_root),
            instrument_ids=("hyperliquid:perp:SOL",),
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 7, 1, tzinfo=UTC),
            evidence_mode="accepted_research",
        ),
        asof_date=date(2026, 6, 21),
    )

    assert report.ready is True
    assert report.missing_fields == ()
    assert report.missing_families == ()
    assert report.data_gap_requests == ()
    assert report.do_not_collect_reason == "existing_archive_refs_sufficient"
    assert any(ref.startswith("archive://hyperliquid/bars/") for ref in report.usable_archive_refs)


def test_resolver_gap_requests_include_checked_refs_and_coverage_reports_for_incomplete_window(tmp_path: Path) -> None:
    archive_root = _write_archive_feature_fixture(tmp_path)
    spec = _spec("hl_mean_reversion_v1", fields=["close", "volume", "coverage_ratio"])
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=archive_root,
        collection_ledger_path=tmp_path / "missing-ledger.json",
    )

    report = service.resolve_strategy_data_requirements(
        StrategyDataRequirementRequest(
            strategy_spec=spec,
            repo_root=str(tmp_path),
            archive_root=str(archive_root),
            instrument_ids=("hyperliquid:perp:SOL",),
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 9, 1, tzinfo=UTC),
            evidence_mode="accepted_research",
        ),
        asof_date=date(2026, 6, 21),
    )

    assert report.ready is False
    gaps_by_family = {gap.requested_family: gap for gap in report.data_gap_requests}
    assert {"bars", "coverage"} <= set(gaps_by_family)
    assert any(ref.startswith("archive://hyperliquid/bars/") for ref in gaps_by_family["bars"].existing_archive_refs_checked)
    assert any(ref.startswith("archive://hyperliquid/bars/") for ref in gaps_by_family["coverage"].existing_archive_refs_checked)
    assert gaps_by_family["bars"].missing_coverage_report_ids
    assert gaps_by_family["coverage"].missing_coverage_report_ids == gaps_by_family["bars"].missing_coverage_report_ids
    assert gaps_by_family["bars"].venue_probe_allowed is True
    assert gaps_by_family["bars"].suggested_collector == "research_only_bars_gap_collector_template"
    assert gaps_by_family["coverage"].venue_probe_allowed is False


def test_resolver_does_not_promote_non_evidence_feature_materialization_to_accepted_ready(tmp_path: Path) -> None:
    ledger_path = _write_collection_ledger(tmp_path)
    feature_entry = _feature_catalog_entry(accepted=False)
    spec = _spec("hl_funding_carry_v1", fields=["close", "funding", "volume", "coverage_ratio"])
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=tmp_path / "missing-archive",
        collection_ledger_path=ledger_path,
        feature_catalog_service=_StaticFeatureCatalogService((feature_entry,)),
    )

    report = service.resolve_strategy_data_requirements(
        StrategyDataRequirementRequest(
            strategy_spec=spec,
            repo_root=str(tmp_path),
            archive_root=str(tmp_path / "missing-archive"),
            instrument_ids=("hyperliquid:perp:SOL",),
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 7, 1, tzinfo=UTC),
            evidence_mode="accepted_research",
        ),
        asof_date=date(2026, 6, 21),
    )

    assert report.ready is False
    assert "funding" in report.missing_fields
    assert "derivatives_context" in report.missing_families
    assert "bars" not in report.missing_families
    assert any(ref.startswith("ledger://") for ref in report.usable_archive_refs)
    assert not any(ref.startswith("feature://") for ref in report.usable_archive_refs)
    derivative_gap = next(gap for gap in report.data_gap_requests if gap.requested_family == "derivatives_context")
    assert derivative_gap.existing_archive_refs_checked == (
        "feature://derivatives_context/SOL/features/derivatives_context/metrics/SOL/native/features.jsonl",
    )
    assert derivative_gap.venue_probe_allowed is False
    assert any(
        task.startswith("materialize_feature_family:derivatives_context")
        for task in report.required_feature_materializations
    )


def test_resolver_allows_non_evidence_feature_materialization_for_sandbox_diagnostic(tmp_path: Path) -> None:
    ledger_path = _write_collection_ledger(tmp_path)
    feature_entry = _feature_catalog_entry(accepted=False)
    spec = _spec("hl_funding_carry_v1", fields=["close", "funding", "volume", "coverage_ratio"])
    service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=tmp_path / "missing-archive",
        collection_ledger_path=ledger_path,
        feature_catalog_service=_StaticFeatureCatalogService((feature_entry,)),
    )

    report = service.resolve_strategy_data_requirements(
        StrategyDataRequirementRequest(
            strategy_spec=spec,
            repo_root=str(tmp_path),
            archive_root=str(tmp_path / "missing-archive"),
            instrument_ids=("hyperliquid:perp:SOL",),
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 7, 1, tzinfo=UTC),
            evidence_mode="sandbox_diagnostic",
        ),
        asof_date=date(2026, 6, 21),
    )

    assert report.ready is True
    assert report.missing_fields == ()
    assert report.data_gap_requests == ()
    assert any(ref.startswith("feature://derivatives_context/SOL/") for ref in report.usable_archive_refs)


def _spec(strategy_id: str, *, fields: list[str]) -> dict:
    spec = example_strategy_payloads()[strategy_id]
    spec = dict(spec)
    spec["inputs"] = dict(spec["inputs"])
    spec["inputs"]["timeframe"] = "1d"
    spec["inputs"]["fields"] = fields
    spec["validation"] = dict(spec["validation"])
    spec["validation"]["min_backtest_months"] = 6
    return spec


def _write_collection_ledger(tmp_path: Path) -> Path:
    path = tmp_path / "collection-ledger.json"
    payload = {
        "schema_version": "central_market_history_v1",
        "report_type": "central_market_history_collection_ledger",
        "ledger_id": "test-ledger",
        "entry_count": 1,
        "entries": [
            {
                "schema_version": "central_market_history_v1",
                "provider": "hyperliquid",
                "venue_symbol": "SOL",
                "source_id": "fixture_archive",
                "family": "ohlcv",
                "timeframe": "1d",
                "start": "2024-01",
                "end": "2024-06",
                "status": "complete",
                "backtest_usable": True,
                "parsed_row_count": 182,
                "manifest_refs": ["manifests/fixture-sol-bars.json"],
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
        ],
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
    import json

    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


class _StaticFeatureCatalogService:
    def __init__(self, entries: tuple[FeatureCatalogEntry, ...]) -> None:
        self._catalog = FeatureCatalog(
            catalog_id="c" * 64,
            entries=entries,
            feature_families=tuple(sorted({entry.feature_family for entry in entries})),
            source_families=tuple(sorted({entry.source_family for entry in entries})),
            symbols=tuple(sorted({entry.symbol for entry in entries})),
            entry_count=len(entries),
            total_feature_rows=sum(entry.row_count for entry in entries),
            **dict(RESEARCH_BOUNDARY),
        )

    def build_catalog(self) -> FeatureCatalog:
        return self._catalog


def _feature_catalog_entry(*, accepted: bool) -> FeatureCatalogEntry:
    return FeatureCatalogEntry(
        feature_catalog_id="e" * 64,
        feature_family="derivatives_context",
        source_family="metrics",
        source_id="feature-materialization-fixture",
        venue="hyperliquid",
        symbol="SOL",
        venue_symbol="SOL",
        instrument_id="hyperliquid:perp:SOL",
        timeframe="1d",
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 7, 1, tzinfo=UTC),
        row_count=182,
        input_row_count=182,
        output_format="jsonl",
        output_ref="features/derivatives_context/metrics/SOL/native/features.jsonl",
        output_sha256="f" * 64,
        output_part_refs=(),
        materialization_report_id="m" * 64,
        materialization_report_ref="manifests/feature-materialization-report.json",
        evidence_scope="feature_materialization",
        accepted_research_evidence_allowed=accepted,
        usable_archive_ref="feature://derivatives_context/SOL/features/derivatives_context/metrics/SOL/native/features.jsonl",
        blocker_reasons=() if accepted else ("not_accepted_historical_coverage_proof",),
        **dict(RESEARCH_BOUNDARY),
    )


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
        job_id="resolver-silver-bars",
        source_file_ids=("source-resolver",),
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
        notes="phase80_resolver_feature_fixture",
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
