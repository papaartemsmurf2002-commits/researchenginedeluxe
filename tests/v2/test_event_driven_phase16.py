from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq

from tradingbotsuite.v2.backtest_engine import (
    BacktestRunConfig,
    RunStatus,
    run_event_driven_backtest,
)
from tradingbotsuite.v2.backtest_engine.engine import _normalize_microstructure_events
from tradingbotsuite.v2.costs import CostModelConfig
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


def test_event_driven_engine_runs_fixture_microstructure_and_outputs_artifacts(tmp_path) -> None:
    result = run_event_driven_backtest(
        config=_config(tmp_path / "runs", run_id="event-success"),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(),
        microstructure_rows=_microstructure_rows(),
    )
    run_dir = Path(result.run_dir)

    assert result.manifest.status == RunStatus.SUCCEEDED
    assert result.manifest.engine_lane.value == "event_driven"
    assert result.manifest.live_signal is False
    assert result.manifest.order_placement_instruction is False
    assert {path.as_posix() for path in _artifact_files(run_dir)} >= REQUIRED_ARTIFACTS
    assert pq.read_table(run_dir / "positions.parquet").num_rows > 0
    assert "engine_lane=event_driven" in (run_dir / "logs" / "log.txt").read_text(encoding="utf-8")


def test_event_driven_missing_microstructure_fails_with_artifacts(tmp_path) -> None:
    result = run_event_driven_backtest(
        config=_config(tmp_path / "runs", run_id="event-missing-micro"),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(),
        microstructure_rows=[],
    )
    run_dir = Path(result.run_dir)

    assert result.manifest.status == RunStatus.FAILED
    assert result.manifest.engine_lane.value == "event_driven"
    assert result.manifest.failure_reason == "event_microstructure_rows_required"
    assert {path.as_posix() for path in _artifact_files(run_dir)} >= REQUIRED_ARTIFACTS


def test_event_queue_ordering_is_deterministic() -> None:
    events = _normalize_microstructure_events(
        [
            {"ts": "2024-01-01T00:01:00Z", "instrument_id": "ETH", "event_type": "bbo", "sequence": 2},
            {"ts": "2024-01-01T00:00:00Z", "instrument_id": "BTC", "event_type": "l2", "sequence": 1},
            {"ts": "2024-01-01T00:00:00Z", "instrument_id": "BTC", "event_type": "bbo", "sequence": 0},
        ]
    )

    assert [(event["instrument_id"], event["event_type"], event["sequence"]) for event in events] == [
        ("BTC", "bbo", 0),
        ("BTC", "l2", 1),
        ("ETH", "bbo", 2),
    ]


def test_event_driven_maker_assumption_requires_queue_model(tmp_path) -> None:
    result = run_event_driven_backtest(
        config=_config(
            tmp_path / "runs",
            run_id="event-maker-blocked",
            cost_model_id="event_maker_research_v1",
        ),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(),
        microstructure_rows=_microstructure_rows(),
    )

    assert result.manifest.status == RunStatus.FAILED
    assert result.manifest.failure_reason == "maker_assumption_requires_queue_model"


def test_event_driven_documented_queue_model_allows_maker_fixture_run(tmp_path) -> None:
    cost_model = CostModelConfig(
        cost_model_id="event_maker_research_v1",
        fee_side="maker",
        queue_model_documented=True,
    )
    result = run_event_driven_backtest(
        config=_config(
            tmp_path / "runs",
            run_id="event-maker-documented",
            cost_model_id=cost_model.cost_model_id,
            cost_model=cost_model,
        ),
        strategy_spec=_short_spec("hl_cross_sectional_momentum_v1"),
        panel_rows=_panel_rows(),
        microstructure_rows=_microstructure_rows(),
    )

    assert result.manifest.status == RunStatus.SUCCEEDED
    assert result.manifest.engine_lane.value == "event_driven"


def _config(
    output_root: Path,
    *,
    run_id: str,
    cost_model_id: str = "conservative_hyperliquid_taker_v1",
    cost_model: CostModelConfig | None = None,
) -> BacktestRunConfig:
    return BacktestRunConfig(
        run_id=run_id,
        experiment_id="phase16-test",
        output_root=str(output_root),
        archive_snapshot_id="archive-snapshot",
        universe_snapshot_id="universe-snapshot",
        data_manifest_id="data-manifest",
        data_manifest_hash=HEX_A,
        validation_manifest_hash=HEX_B,
        cost_manifest_hash=HEX_C,
        cost_model_id=cost_model_id,
        cost_model=cost_model,
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


def _microstructure_rows() -> list[dict[str, object]]:
    return [
        {
            "ts": "2024-01-01T00:00:00Z",
            "instrument_id": "hyperliquid:perp:BTC",
            "event_type": "bbo",
            "bid": 99.9,
            "ask": 100.1,
            "sequence": 0,
        },
        {
            "ts": "2024-01-01T00:00:01Z",
            "instrument_id": "hyperliquid:perp:BTC",
            "event_type": "l2",
            "bid_depth": 10_000.0,
            "ask_depth": 12_000.0,
            "sequence": 1,
        },
    ]


def _artifact_files(run_dir: Path) -> list[Path]:
    return [path.relative_to(run_dir) for path in run_dir.rglob("*") if path.is_file()]
