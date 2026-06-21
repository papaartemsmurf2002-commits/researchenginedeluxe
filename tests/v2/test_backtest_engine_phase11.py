from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq

from tradingbotsuite.v2.backtest_engine import (
    BacktestRunConfig,
    RunStatus,
    recompute_metrics_from_run_manifest,
    run_event_driven_placeholder,
    run_vectorized_backtest,
)
from tradingbotsuite.v2.strategy_specs import example_strategy_payloads


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64

REQUIRED_ARTIFACTS = {
    "run_manifest.json",
    "strategy_spec.json",
    "params.json",
    "data_manifest.json",
    "validation_manifest.json",
    "cost_manifest.json",
    "metrics.json",
    "equity_curve.parquet",
    "daily_returns.parquet",
    "trades.parquet",
    "positions.parquet",
    "cost_stress.parquet",
    "per_instrument_metrics.parquet",
    "fold_metrics.parquet",
    "logs/log.txt",
}

FULL_INVARIANT_COLUMNS = {
    "research_only",
    "observe_only",
    "promotion_ready",
    "candidate_evidence",
    "candidate_pack_eligible",
    "live_signal",
    "paper_signal",
    "sizing_instruction",
    "order_placement_instruction",
    "runtime_mode_change",
}


def test_three_strategy_templates_run_over_same_data_snapshot(tmp_path) -> None:
    panel = _panel_rows()
    specs = [
        _short_spec("hl_cross_sectional_momentum_v1"),
        _short_spec("hl_mean_reversion_v1"),
        _short_spec("hl_funding_carry_v1"),
    ]
    results = [
        run_vectorized_backtest(
            config=_config(tmp_path / "runs", trial_index=index),
            strategy_spec=spec,
            panel_rows=panel,
        )
        for index, spec in enumerate(specs)
    ]

    assert all(result.manifest.status == RunStatus.SUCCEEDED for result in results)
    assert len({result.manifest.data_manifest_hash for result in results}) == 1
    assert all(result.metrics is not None for result in results)


def test_vectorized_engine_outputs_required_artifacts(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="artifact-smoke"),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(),
    )
    run_dir = Path(result.run_dir)
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert result.manifest.status == RunStatus.SUCCEEDED
    assert {path.as_posix() for path in _artifact_files(run_dir)} >= REQUIRED_ARTIFACTS
    assert set(result.manifest.artifacts) >= {
        "metrics",
        "equity_curve",
        "daily_returns",
        "trades",
        "positions",
        "cost_stress",
        "per_instrument_metrics",
        "fold_metrics",
        "log",
    }
    assert manifest["research_only"] is True
    assert manifest["promotion_ready"] is False
    positions = pq.read_table(run_dir / "positions.parquet")
    trades = pq.read_table(run_dir / "trades.parquet")

    assert positions.num_rows > 0
    assert pq.read_table(run_dir / "equity_curve.parquet").num_rows > 0
    assert FULL_INVARIANT_COLUMNS <= set(positions.schema.names)
    assert FULL_INVARIANT_COLUMNS <= set(trades.schema.names)
    assert all(row["research_only"] is True for row in positions.to_pylist())
    assert all(row["observe_only"] is True for row in positions.to_pylist())
    assert all(row["research_only"] is True for row in trades.to_pylist())
    assert all(row["observe_only"] is True for row in trades.to_pylist())
    for column in FULL_INVARIANT_COLUMNS - {"research_only", "observe_only"}:
        assert all(row[column] is False for row in positions.to_pylist())
        assert all(row[column] is False for row in trades.to_pylist())


def test_same_run_manifest_reproduces_metrics_on_fixture_data(tmp_path) -> None:
    panel = _panel_rows()
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="repro-run"),
        strategy_spec=_short_spec("hl_funding_carry_v1"),
        panel_rows=panel,
    )

    recomputed = recompute_metrics_from_run_manifest(
        run_dir=result.run_dir,
        panel_rows=panel,
    )

    assert result.metrics is not None
    assert recomputed.model_dump(mode="json") == result.metrics.model_dump(mode="json")


def test_funding_and_fees_affect_net_results(tmp_path) -> None:
    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="costed-run"),
        strategy_spec=_short_spec("hl_funding_carry_v1"),
        panel_rows=_panel_rows(),
    )

    assert result.metrics is not None
    assert result.metrics.total_fee_cost > 0
    assert result.metrics.total_funding_pnl != 0
    assert result.metrics.net_return != result.metrics.gross_return


def test_missing_data_policy_is_explicit_and_fail_closed(tmp_path) -> None:
    panel = [
        row
        for row in _panel_rows()
        if not (row["ts"] == "2024-01-01T03:00:00Z" and row["instrument_id"] == "hyperliquid:perp:ETH")
    ]

    result = run_vectorized_backtest(
        config=_config(tmp_path / "runs", run_id="missing-data-run"),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=panel,
    )

    assert result.manifest.status == RunStatus.FAILED
    assert "missing_data_policy_fail_closed" in (result.manifest.failure_reason or "")
    assert (Path(result.run_dir) / "run_manifest.json").exists()
    assert (Path(result.run_dir) / "metrics.json").exists()


def test_event_driven_engine_skeleton_outputs_same_artifact_contract(tmp_path) -> None:
    result = run_event_driven_placeholder(
        config=_config(tmp_path / "runs", run_id="event-placeholder"),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(),
    )
    run_dir = Path(result.run_dir)

    assert result.manifest.status == RunStatus.FAILED
    assert result.manifest.engine_lane.value == "event_driven"
    assert result.manifest.failure_reason == "event_driven_engine_placeholder_blocked"
    assert {path.as_posix() for path in _artifact_files(run_dir)} >= REQUIRED_ARTIFACTS


def test_engine_rejects_gross_only_metrics_for_reported_mode(tmp_path) -> None:
    config = _config(tmp_path / "runs", run_id="gross-only-rejected").model_copy(
        update={"require_net_metrics": False}
    )

    result = run_vectorized_backtest(
        config=config,
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(),
    )

    assert result.manifest.status == RunStatus.FAILED
    assert result.manifest.failure_reason == "gross_only_metrics_rejected"


def _config(output_root: Path, *, run_id: str | None = None, trial_index: int = 0) -> BacktestRunConfig:
    return BacktestRunConfig(
        run_id=run_id,
        experiment_id="phase11-test",
        trial_index=trial_index,
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


def _artifact_files(run_dir: Path) -> list[Path]:
    return [path.relative_to(run_dir) for path in run_dir.rglob("*") if path.is_file()]
