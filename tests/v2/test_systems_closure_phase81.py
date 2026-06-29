from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pyarrow as pa

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
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
from tradingbotsuite.v2.backtest_engine import (
    BacktestBenchmarkConfig,
    BacktestRunConfig,
    BenchmarkTier,
    EngineLane,
    FastLaneParityStatus,
    FullArtifactReplayVerificationStatus,
    audit_fast_lane_parity,
    build_full_artifact_replay_plan,
    run_archive_backtest_benchmark,
    run_vectorized_backtest,
    select_reference_audit_sample,
    verify_full_artifact_replay,
)
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.costs.models import CostModelConfig
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode
from tradingbotsuite.v2.feature_store import FeatureStoreCatalogService
from tradingbotsuite.v2.ledger import LedgerAppendRequest, append_run_to_ledger, export_ledger, read_ledger
from tradingbotsuite.v2.strategy_specs import compile_signal_frame, example_strategy_payloads
from tradingbotsuite.v2.universe.hyperliquid import refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
VENUE = "hyperliquid"
INSTRUMENTS = ("hyperliquid:perp:BTC", "hyperliquid:perp:ETH")


def test_archive_first_workflow_reaches_benchmark_replay_ledger_and_feature_discovery(tmp_path: Path) -> None:
    fixture = _archive_fixture(tmp_path, instrument_ids=INSTRUMENTS)
    output_root = tmp_path / "systems-closure"
    spec = _daily_mean_reversion_spec()
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 8, 1, tzinfo=UTC)
    inventory_service = ArchiveInventoryService(
        repo_root=tmp_path,
        archive_root=fixture["archive_root"],
        collection_ledger_path=tmp_path / "missing-ledger.json",
    )

    inventory = inventory_service.build_inventory()
    requirement = inventory_service.resolve_strategy_data_requirements(
        StrategyDataRequirementRequest(
            strategy_spec=spec,
            repo_root=str(tmp_path),
            archive_root=str(fixture["archive_root"]),
            instrument_ids=INSTRUMENTS,
            start_ts=start_ts,
            end_ts=end_ts,
            evidence_mode="accepted_research",
            artifact_mode=ArtifactMode.METRICS_ONLY,
            prefer_fast_lane=True,
        ),
        asof_date=date(2026, 6, 21),
    )
    feature_catalog = FeatureStoreCatalogService(
        repo_root=tmp_path,
        archive_root=fixture["archive_root"],
        materialization_report_paths=(),
    ).build_catalog()
    benchmark = run_archive_backtest_benchmark(
        BacktestBenchmarkConfig(
            benchmark_id="phase81-panel-benchmark",
            benchmark_tier=BenchmarkTier.PANEL,
            archive_root=str(fixture["archive_root"]),
            output_root=str(output_root / "benchmarks"),
            strategy_spec=spec,
            archive_snapshot_id=str(fixture["archive_snapshot_id"]),
            universe_snapshot_id=str(fixture["universe_snapshot_id"]),
            venue=VENUE,
            instrument_id=INSTRUMENTS[0],
            instrument_ids=INSTRUMENTS,
            timeframe="1d",
            start_ts=start_ts,
            end_ts=end_ts,
            asof_date=date(2026, 6, 21),
            artifact_mode=ArtifactMode.METRICS_ONLY,
        )
    )
    full_replay = run_archive_backtest_benchmark(
        BacktestBenchmarkConfig(
            benchmark_id="phase81-panel-benchmark-full",
            benchmark_tier=BenchmarkTier.PANEL,
            archive_root=str(fixture["archive_root"]),
            output_root=str(output_root / "benchmarks"),
            strategy_spec=spec,
            archive_snapshot_id=str(fixture["archive_snapshot_id"]),
            universe_snapshot_id=str(fixture["universe_snapshot_id"]),
            venue=VENUE,
            instrument_id=INSTRUMENTS[0],
            instrument_ids=INSTRUMENTS,
            timeframe="1d",
            start_ts=start_ts,
            end_ts=end_ts,
            asof_date=date(2026, 6, 21),
            artifact_mode=ArtifactMode.FULL,
        )
    )
    source_manifest = _read_json(Path(benchmark.reference_run_manifest_ref))
    full_manifest = _read_json(Path(full_replay.reference_run_manifest_ref))
    replay_plan = build_full_artifact_replay_plan(
        source_manifest,
        run_manifest_ref=benchmark.reference_run_manifest_ref,
    )
    replay_verification = verify_full_artifact_replay(
        source_manifest=source_manifest,
        replay_manifest=full_manifest,
        source_replay_manifest=_read_json(Path(benchmark.reference_run_manifest_ref).parent / "replay_manifest.json"),
        full_replay_manifest=_read_json(Path(full_replay.reference_run_manifest_ref).parent / "replay_manifest.json"),
    )
    sampled = select_reference_audit_sample(
        (benchmark.fast_run_id,),
        sample_rate=0.5,
        seed="phase81",
        minimum_count=1,
    )
    ledger_path = output_root / "ledger" / "systems_closure_ledger.parquet"
    append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=benchmark.reference_run_manifest_ref,
            ledger_path=str(ledger_path),
            evidence_mode="accepted_research",
            max_part_rows=1,
            notes="phase81 reference metrics-only run",
        )
    )
    append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=benchmark.fast_run_manifest_ref,
            ledger_path=str(ledger_path),
            evidence_mode="accepted_research",
            max_part_rows=1,
            notes="phase81 fast metrics-only run",
        )
    )
    export_path = export_ledger(
        ledger_path=ledger_path,
        output_path=output_root / "ledger" / "systems_closure_ledger.csv",
        export_format="csv",
    )
    ledger_rows = read_ledger(ledger_path)

    assert inventory.summary.record_count >= 2
    assert inventory.summary.accepted_research_record_count >= 2
    assert requirement.ready is True
    assert requirement.usable_instruments == INSTRUMENTS
    assert requirement.data_gap_requests == ()
    assert requirement.recommended_engine_lane == "fast_vectorized"
    assert requirement.reference_audit_required is True
    assert any(ref.startswith("archive://") for ref in requirement.usable_archive_refs)
    assert {"funding", "open_interest", "bbo_spread", "derived_bar_context"} <= set(feature_catalog.feature_families)
    assert benchmark.parity_report.status == FastLaneParityStatus.PASS
    assert benchmark.artifact_mode == ArtifactMode.METRICS_ONLY
    assert benchmark.instrument_count == 2
    assert benchmark.row_count == 426
    assert benchmark.speedup_claimed is False
    assert benchmark.benchmark_observations["reference_data_load_seconds"] >= 0.0
    assert benchmark.benchmark_observations["fast_data_load_seconds"] >= 0.0
    assert replay_plan.requested_artifact_mode == ArtifactMode.FULL
    assert replay_plan.expected_data_manifest_hash == source_manifest["data_manifest_hash"]
    assert replay_verification.status == FullArtifactReplayVerificationStatus.PASS
    assert replay_verification.full_artifacts_verified is True
    assert sampled == (benchmark.fast_run_id,)
    assert [row.run_id for row in ledger_rows] == [benchmark.reference_run_id, benchmark.fast_run_id]
    assert ledger_path.with_suffix(".index.json").exists()
    assert export_path.exists()


def test_fast_reference_parity_matrix_covers_current_family_modes(tmp_path: Path) -> None:
    cases = (
        ("hl_cross_sectional_momentum_v1", "next_bar_open", ArtifactMode.METRICS_ONLY, "lenient"),
        ("hl_funding_carry_v1", "close", ArtifactMode.SUMMARY, "lenient"),
        ("hl_mean_reversion_v1", "mark", ArtifactMode.FULL, "lenient"),
        ("hl_volatility_breakout_v1", "oracle", ArtifactMode.METRICS_ONLY, "lenient"),
        ("hl_liquidity_filtered_momentum_v1", "next_bar_open", ArtifactMode.SUMMARY, "accepted_research_strict"),
    )
    panel = _hourly_panel_rows()
    for index, (strategy_id, price_basis, artifact_mode, spread_policy) in enumerate(cases):
        spec = _matrix_spec(strategy_id, price_basis=price_basis)
        signal_frame = compile_signal_frame(spec, panel)
        output_root = tmp_path / "matrix" / f"phase81-{index}"
        reference = run_vectorized_backtest(
            config=_run_config(
                output_root,
                run_id=f"phase81-ref-{index}",
                artifact_mode=artifact_mode,
                spread_policy=spread_policy,
                engine_lane=EngineLane.VECTORIZED,
            ),
            strategy_spec=spec,
            panel_rows=panel,
            signal_frame=signal_frame,
        )
        fast = run_vectorized_backtest(
            config=_run_config(
                output_root,
                run_id=f"phase81-fast-{index}",
                artifact_mode=artifact_mode,
                spread_policy=spread_policy,
                engine_lane=EngineLane.FAST_VECTORIZED,
            ),
            strategy_spec=spec,
            panel_table=pa.Table.from_pylist(panel),
            signal_frame=signal_frame,
        )
        report = audit_fast_lane_parity(
            reference_manifest=reference.manifest,
            fast_manifest=fast.manifest,
        )

        assert report.status == FastLaneParityStatus.PASS
        assert report.reference_engine_authority is True
        assert report.speedup_claimed is False
        assert all(row.within_tolerance for row in report.metric_diffs)
        assert reference.manifest.artifact_mode == artifact_mode
        assert fast.manifest.artifact_mode == artifact_mode


def _archive_fixture(tmp_path: Path, *, instrument_ids: tuple[str, ...]) -> dict[str, object]:
    archive_root = tmp_path / "archive"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    coverage_store = CoverageManifestStore(layout)
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 8, 1, tzinfo=UTC)
    reports = []
    file_ids = []
    for index, instrument_id in enumerate(instrument_ids):
        rows = _daily_rows(start_ts, end_ts, instrument_id=instrument_id, price_offset=index * 20.0)
        manifest = write_parquet_rows(
            layout=layout,
            store=store,
            rows=rows,
            layer=ArchiveLayer.SILVER,
            dataset="bars",
            venue=VENUE,
            datatype="bars",
            date=start_ts.date().isoformat(),
            timeframe="1d",
            job_id=f"phase81-silver-bars-{index}",
            source_file_ids=(f"phase81-source-{index}",),
            instrument_id=instrument_id,
        )
        file_ids.append(manifest.file_id)
        coverage = coverage_report_for_bars(
            rows,
            venue=VENUE,
            instrument_id=instrument_id,
            timeframe="1d",
            start_ts=start_ts,
            end_ts=end_ts,
            evidence_mode=EvidenceMode.ACCEPTED_RESEARCH,
        )
        coverage_store.append_coverage_report(coverage)
        reports.append(coverage)
    snapshot = create_archive_snapshot(
        store=store,
        layer=ArchiveLayer.SILVER,
        venue_scope=VENUE,
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_rows=[report.model_dump(mode="json") for report in reports],
        quality_rows=(),
        lockbox_policy_id="dynamic_full_calendar_months_v1",
        notes="phase81_systems_closure_fixture",
    )
    universe = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_universe_payload(instrument_ids),
        asof_date=start_ts.date(),
        mode=UniverseMode.AS_OF,
    )
    return {
        "archive_root": archive_root,
        "archive_snapshot_id": snapshot.archive_snapshot_id,
        "universe_snapshot_id": universe.snapshot_id,
        "file_ids": tuple(file_ids),
    }


def _daily_rows(
    start_ts: datetime,
    end_ts: datetime,
    *,
    instrument_id: str,
    price_offset: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current = start_ts
    index = 0
    while current < end_ts:
        close = 100.0 + price_offset + (index * 0.15) + ((index % 5) * 0.04)
        rows.append(
            {
                "venue": VENUE,
                "instrument_id": instrument_id,
                "timeframe": "1d",
                "ts": current.isoformat().replace("+00:00", "Z"),
                "end_ts": (current + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "open": close - 0.2,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": 100_000.0 + index,
                "trade_count": index + 1,
                "funding": 0.00001 if index % 2 == 0 else -0.00001,
                "funding_rate": 0.00001 if index % 2 == 0 else -0.00001,
                "open_interest": 5_000_000.0 + index,
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


def _daily_mean_reversion_spec() -> dict[str, object]:
    payload = json.loads(json.dumps(example_strategy_payloads()["hl_mean_reversion_v1"]))
    payload["inputs"]["timeframe"] = "1d"
    payload["inputs"]["fields"] = ["close", "volume", "coverage_ratio"]
    payload["logic"]["lookback_bars"] = 2
    payload["logic"]["lookback_hours"] = None
    payload["logic"]["entry_threshold"] = 0.1
    payload["risk"]["rebalance"] = "1d"
    payload["validation"]["min_backtest_months"] = 6
    return payload


def _matrix_spec(strategy_id: str, *, price_basis: str) -> dict[str, object]:
    payload = json.loads(json.dumps(example_strategy_payloads()[strategy_id]))
    payload["inputs"]["timeframe"] = "1h"
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
    payload["execution"]["price_basis"] = price_basis
    payload["logic"]["lookback_hours"] = 2
    payload["logic"]["lookback_bars"] = 2
    payload["logic"]["entry_threshold"] = 0.1
    payload["risk"]["rebalance"] = "1h"
    payload["validation"]["min_backtest_months"] = 6
    return payload


def _hourly_panel_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    instruments = {
        "hyperliquid:perp:BTC": 100.0,
        "hyperliquid:perp:ETH": 80.0,
        "hyperliquid:perp:SOL": 40.0,
    }
    for hour in range(18):
        ts = f"2024-01-01T{hour:02d}:00:00Z"
        for offset, (instrument_id, base) in enumerate(instruments.items()):
            drift = (hour * (offset + 1)) * (1 if offset != 1 else -0.4)
            open_price = base + drift
            close = open_price * (1.01 if offset == 0 else 0.996 if offset == 1 else 1.002)
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
                    "open_interest": 2_000_000.0 + (offset * 10_000.0),
                    "mark_price": close * 1.0001,
                    "oracle_price": close * 0.9999,
                    "spread": 0.001,
                    "spread_units": "fraction",
                    "coverage_ratio": 1.0,
                }
            )
    return rows


def _run_config(
    output_root: Path,
    *,
    run_id: str,
    artifact_mode: ArtifactMode,
    spread_policy: str,
    engine_lane: EngineLane,
) -> BacktestRunConfig:
    cost_model = CostModelConfig(spread_observation_policy=spread_policy)
    return BacktestRunConfig(
        run_id=run_id,
        experiment_id="phase81-fast-reference-parity-matrix",
        trial_index=0 if engine_lane == EngineLane.VECTORIZED else 1,
        output_root=str(output_root),
        archive_snapshot_id="archive-snapshot",
        universe_snapshot_id="universe-snapshot",
        data_manifest_id="data-manifest",
        data_manifest_hash=HEX_A,
        validation_manifest_hash=HEX_B,
        cost_manifest_hash=canonical_json_hash(cost_model.model_dump(mode="json")),
        cost_model_id=cost_model.cost_model_id,
        cost_model=cost_model,
        engine_lane=engine_lane,
        artifact_mode=artifact_mode,
        universe_mode="as_of",
        venue_scope=VENUE,
        git_sha="test-git-sha",
    )


def _universe_payload(instrument_ids: tuple[str, ...]):
    names = [instrument_id.rsplit(":", 1)[-1] for instrument_id in instrument_ids]
    return [
        {
            "universe": [
                {"name": name, "szDecimals": 5, "maxLeverage": 50}
                for name in names
            ]
        },
        [
            {
                "dayNtlVlm": "12000000",
                "openInterest": "20",
                "markPx": "150",
                "oraclePx": "151",
                "funding": "0.0002",
            }
            for _name in names
        ],
    ]


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
