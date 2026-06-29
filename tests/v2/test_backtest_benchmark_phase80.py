from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.archive.snapshots import create_archive_snapshot
from tradingbotsuite.v2.backtest_engine import (
    ArtifactMode,
    BacktestBenchmarkConfig,
    BenchmarkTier,
    FastLaneParityStatus,
    run_archive_backtest_benchmark,
)
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.costs.models import CostModelConfig
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import EvidenceMode
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads
from tradingbotsuite.v2.universe.hyperliquid import refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode


ROOT = Path(__file__).resolve().parents[2]
INSTRUMENT = "hyperliquid:perp:BTC"
SECOND_INSTRUMENT = "hyperliquid:perp:ETH"
VENUE = "hyperliquid"


def test_archive_backed_benchmark_reports_reference_fast_speedup_without_archive_mutation(tmp_path) -> None:
    fixture = _archive_fixture(tmp_path)
    output_root = tmp_path / "benchmark-runs"

    report = run_archive_backtest_benchmark(
        BacktestBenchmarkConfig(
            benchmark_id="unit-archive-benchmark",
            archive_root=str(fixture.archive_root),
            output_root=str(output_root),
            strategy_spec=_strategy_spec(),
            archive_snapshot_id=fixture.archive_snapshot_id,
            universe_snapshot_id=fixture.universe_snapshot_id,
            venue=VENUE,
            instrument_id=INSTRUMENT,
            timeframe="1d",
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 8, 1, tzinfo=UTC),
            asof_date=date(2026, 6, 21),
            artifact_mode=ArtifactMode.METRICS_ONLY,
        )
    )

    assert report.parity_report.status == FastLaneParityStatus.PASS
    assert report.benchmark_tier == BenchmarkTier.SMOKE
    assert report.artifact_mode == ArtifactMode.METRICS_ONLY
    assert report.instrument_count == 1
    assert report.benchmark_window_days >= 213.0
    assert report.benchmark_scope["tier"] == "smoke"
    assert report.benchmark_scope["artifact_mode"] == "metrics_only"
    assert report.benchmark_scope["reference_lane"] == "vectorized"
    assert report.benchmark_scope["fast_lane"] == "fast_vectorized"
    assert report.benchmark_scope["speedup_claim_policy"] == "measured_speedup_ratio_required"
    assert report.measured_speedup_ratio is not None
    assert report.speedup_claimed is False
    for key in (
        "reference_runtime_seconds",
        "fast_runtime_seconds",
        "reference_data_load_seconds",
        "fast_data_load_seconds",
        "reference_artifact_write_seconds",
        "fast_artifact_write_seconds",
        "reference_memory_peak_bytes",
        "fast_memory_peak_bytes",
    ):
        assert report.benchmark_observations[key] >= 0.0
        assert key in report.benchmark_scope["required_observation_keys"]
    assert report.benchmark_observations["speedup_ratio"] == report.measured_speedup_ratio
    assert report.research_only is True
    assert report.promotion_ready is False
    assert Path(report.report_path or "").exists()
    assert not (fixture.archive_root / "manifests" / "backtest_data_requests.parquet").exists()

    reference_manifest = json.loads(Path(report.reference_run_manifest_ref).read_text(encoding="utf-8"))
    fast_manifest = json.loads(Path(report.fast_run_manifest_ref).read_text(encoding="utf-8"))
    assert reference_manifest["artifact_mode"] == "metrics_only"
    assert fast_manifest["artifact_mode"] == "metrics_only"
    assert reference_manifest["engine_lane"] == "vectorized"
    assert fast_manifest["engine_lane"] == "fast_vectorized"
    assert "replay_manifest" in reference_manifest["artifacts"]
    assert "replay_manifest" in fast_manifest["artifacts"]
    assert "trades" not in reference_manifest["artifacts"]
    assert "positions" not in fast_manifest["artifacts"]


def test_panel_tier_benchmark_runs_reference_and_fast_for_multi_instrument_panel(tmp_path) -> None:
    instrument_ids = (INSTRUMENT, SECOND_INSTRUMENT)
    fixture = _archive_fixture(tmp_path, instrument_ids=instrument_ids)

    report = run_archive_backtest_benchmark(
        BacktestBenchmarkConfig(
            benchmark_id="unit-panel-benchmark",
            benchmark_tier=BenchmarkTier.PANEL,
            archive_root=str(fixture.archive_root),
            output_root=str(tmp_path / "panel-benchmark-runs"),
            strategy_spec=_strategy_spec(),
            archive_snapshot_id=fixture.archive_snapshot_id,
            universe_snapshot_id=fixture.universe_snapshot_id,
            venue=VENUE,
            instrument_id=instrument_ids[0],
            instrument_ids=instrument_ids,
            timeframe="1d",
            start_ts=datetime(2024, 1, 1, tzinfo=UTC),
            end_ts=datetime(2024, 8, 1, tzinfo=UTC),
            asof_date=date(2026, 6, 21),
            artifact_mode=ArtifactMode.METRICS_ONLY,
        )
    )

    assert report.parity_report.status == FastLaneParityStatus.PASS
    assert report.benchmark_tier == BenchmarkTier.PANEL
    assert report.instrument_ids == instrument_ids
    assert report.instrument_count == 2
    assert report.row_count == 426
    assert report.reported_row_count == 426
    assert report.benchmark_scope["tier"] == "panel"
    assert report.benchmark_scope["instrument_count"] == 2
    assert report.benchmark_scope["requested_instrument_ids"] == instrument_ids
    assert report.speedup_claimed is False

    reference_manifest = json.loads(Path(report.reference_run_manifest_ref).read_text(encoding="utf-8"))
    fast_manifest = json.loads(Path(report.fast_run_manifest_ref).read_text(encoding="utf-8"))
    assert reference_manifest["instrument_count"] == 2
    assert fast_manifest["instrument_count"] == 2
    assert reference_manifest["artifact_mode"] == "metrics_only"
    assert fast_manifest["artifact_mode"] == "metrics_only"


def test_fast_lane_benchmark_run_cli_writes_report(tmp_path) -> None:
    fixture = _archive_fixture(tmp_path)
    spec_path = tmp_path / "strategy.json"
    spec_path.write_text(json.dumps(_strategy_spec(), sort_keys=True), encoding="utf-8")
    cost_model_path = tmp_path / "cost-model.json"
    cost_model_path.write_text(
        CostModelConfig(
            funding_required=False,
            funding_missing_policy="explicit_zero",
        ).model_dump_json(),
        encoding="utf-8",
    )
    output_root = tmp_path / "cli-benchmark"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "fast-lane",
            "benchmark-run",
            "--benchmark-id",
            "cli-archive-benchmark",
            "--strategy-spec-file",
            str(spec_path),
            "--archive-root",
            str(fixture.archive_root),
            "--output-root",
            str(output_root),
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
            "2024-08-01T00:00:00+00:00",
            "--asof-date",
            "2026-06-21",
            "--cost-model-file",
            str(cost_model_path),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["report_type"] == "backtest_fast_lane_benchmark_report_v1"
    assert payload["benchmark_tier"] == "smoke"
    assert payload["benchmark_scope"]["tier"] == "smoke"
    assert payload["parity_report"]["status"] == "pass"
    assert payload["speedup_claimed"] is False
    assert Path(payload["report_path"]).exists()


def test_panel_and_sweep_benchmark_tiers_reject_too_small_scope(tmp_path) -> None:
    fixture = _archive_fixture(tmp_path)
    base = dict(
        benchmark_id="bad-tier-benchmark",
        archive_root=str(fixture.archive_root),
        output_root=str(tmp_path / "benchmark-runs"),
        strategy_spec=_strategy_spec(),
        archive_snapshot_id=fixture.archive_snapshot_id,
        universe_snapshot_id=fixture.universe_snapshot_id,
        venue=VENUE,
        instrument_id=INSTRUMENT,
        timeframe="1d",
        start_ts=datetime(2024, 1, 1, tzinfo=UTC),
        end_ts=datetime(2024, 1, 15, tzinfo=UTC),
        asof_date=date(2026, 6, 21),
    )

    with pytest.raises(ValueError, match="panel benchmark tier requires at least two instruments"):
        BacktestBenchmarkConfig(**base, benchmark_tier=BenchmarkTier.PANEL)

    with pytest.raises(ValueError, match="sweep benchmark tier requires at least two instruments"):
        BacktestBenchmarkConfig(**base, benchmark_tier=BenchmarkTier.SWEEP)

    with pytest.raises(ValueError, match="sweep benchmark tier requires a window of at least 30 days"):
        BacktestBenchmarkConfig(
            **base,
            benchmark_tier=BenchmarkTier.SWEEP,
            instrument_ids=(INSTRUMENT, "hyperliquid:perp:ETH"),
        )


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
    instrument_ids: tuple[str, ...] = (INSTRUMENT,),
) -> _Fixture:
    archive_root = tmp_path / "archive"
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    start_ts = datetime(2024, 1, 1, tzinfo=UTC)
    end_ts = datetime(2024, 8, 1, tzinfo=UTC)
    reports = []
    coverage_store = CoverageManifestStore(layout)
    for index, instrument_id in enumerate(instrument_ids):
        rows = _daily_rows(start_ts, end_ts, instrument_id=instrument_id, price_offset=index * 10.0)
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
            job_id=f"benchmark-silver-bars-{index}",
            source_file_ids=(f"source-benchmark-{index}",),
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
        coverage_store.append_coverage_report(report)
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
        notes="phase80_benchmark_fixture",
    )
    universe = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_universe_payload(instrument_ids),
        asof_date=start_ts.date(),
        mode=UniverseMode.AS_OF,
    )
    return _Fixture(
        archive_root=archive_root,
        archive_snapshot_id=snapshot.archive_snapshot_id,
        universe_snapshot_id=universe.snapshot_id,
    )


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
        close = 100.0 + price_offset + (index * 0.2) + ((index % 7) * 0.1)
        rows.append(
            {
                "venue": VENUE,
                "instrument_id": instrument_id,
                "timeframe": "1d",
                "ts": current.isoformat().replace("+00:00", "Z"),
                "end_ts": (current + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "open": close - 0.15,
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


def _strategy_spec() -> dict[str, object]:
    payload = json.loads(json.dumps(example_strategy_payloads()["hl_mean_reversion_v1"]))
    payload["inputs"]["timeframe"] = "1d"
    payload["inputs"]["fields"] = ["close", "volume", "coverage_ratio"]
    payload["logic"]["lookback_bars"] = 2
    payload["logic"]["lookback_hours"] = None
    payload["logic"]["entry_threshold"] = 0.1
    payload["risk"]["rebalance"] = "1d"
    payload["validation"]["min_backtest_months"] = 6
    return payload


def _universe_payload(instrument_ids: tuple[str, ...]):
    names = [_coin_from_instrument(instrument_id) for instrument_id in instrument_ids]
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


def _coin_from_instrument(instrument_id: str) -> str:
    return instrument_id.rsplit(":", 1)[-1]
