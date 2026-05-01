from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.backtesting import BacktestEngine, BacktestSpec
from tradingbotsuite.backtesting.engine import SUPPORTED_HOLDING_WINDOWS_MS
from tradingbotsuite.backtesting.metrics import REQUIRED_BACKTEST_METRICS
from tradingbotsuite.research.deterministic_datasets import write_hmm_knn_sweep_dataset


REQUIRED_OUTPUTS = {
    "backtest_manifest.json",
    "trades.parquet",
    "signals.parquet",
    "equity_curve.parquet",
    "metrics.json",
    "config_resolved.json",
}


def _run_fixture(tmp_path: Path, *, strategy_id: str = "baseline_trend", holding_window: str = "24h"):
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    spec = BacktestSpec(
        run_id=f"{strategy_id}-{holding_window}",
        symbol="BTCUSDT",
        output_dir=tmp_path / "backtests",
        dataset_path=dataset.parquet_path,
        dataset_sha256=dataset.parquet_sha256,
        strategy_id=strategy_id,  # type: ignore[arg-type]
        holding_window=holding_window,
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256="test-feature-hash",
        strategy_config={"slope_threshold": 0.1, "spacing_bars": 10},
    )
    return BacktestEngine().run(spec), dataset


def test_backtest_writes_required_artifact_contract(tmp_path: Path) -> None:
    result, dataset = _run_fixture(tmp_path)
    produced = {path.name for path in result.output_dir.iterdir()}
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert REQUIRED_OUTPUTS <= produced
    assert manifest["backtest_manifest_version"] == "backtest-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["dataset_sha256"] == dataset.parquet_sha256
    assert manifest["required_metrics_present"] is True
    assert manifest["same_bar_entry_exit_allowed"] is False
    assert manifest["validity"]["fees_slippage_funding_included"] is True


def test_required_metrics_include_costs_and_splits(tmp_path: Path) -> None:
    result, _ = _run_fixture(tmp_path)
    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    trades = pd.read_parquet(result.trades_path)

    assert set(REQUIRED_BACKTEST_METRICS) <= set(metrics)
    assert metrics["trade_count"] == len(trades)
    assert metrics["gross_return_before_costs"] != metrics["net_return_after_fees_slippage_funding"]
    assert metrics["slippage_sensitivity"] > 0
    assert metrics["funding_contribution"] != 0
    assert metrics["split_by_regime"]
    assert metrics["split_by_month"]
    assert metrics["split_by_volatility_bucket"]


def test_backtest_result_hash_is_reproducible(tmp_path: Path) -> None:
    first, dataset = _run_fixture(tmp_path)
    second = BacktestEngine().run(
        BacktestSpec(
            run_id="repeat",
            symbol="BTCUSDT",
            output_dir=tmp_path / "backtests",
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            strategy_id="baseline_trend",
            holding_window="24h",
            feature_set_id="features_price_trend_vol",
            feature_manifest_sha256="test-feature-hash",
            strategy_config={"slope_threshold": 0.1, "spacing_bars": 10},
        )
    )

    assert first.result_sha256 == second.result_sha256
    assert json.loads(first.metrics_path.read_text(encoding="utf-8")) == json.loads(second.metrics_path.read_text(encoding="utf-8"))


def test_supported_holding_windows_run(tmp_path: Path) -> None:
    for holding_window in ("1h", "24h", "72h", "7d"):
        result, _ = _run_fixture(tmp_path, holding_window=holding_window)
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        assert manifest["execution_assumptions"]["holding_period_ms"] == SUPPORTED_HOLDING_WINDOWS_MS[holding_window]


def test_invalid_holding_window_rejected(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120, variant="balanced")
    spec = BacktestSpec(
        run_id="invalid",
        symbol="BTCUSDT",
        output_dir=tmp_path / "backtests",
        dataset_path=dataset.parquet_path,
        strategy_id="baseline_trend",
        holding_window="15m",
    )

    with pytest.raises(ValueError, match="holding_window"):
        BacktestEngine().run(spec)
