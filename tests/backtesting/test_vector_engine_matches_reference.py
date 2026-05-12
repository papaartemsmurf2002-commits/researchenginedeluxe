from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from tradingbotsuite.backtesting import (
    BACKTEST_ENGINE_VERSION,
    VECTOR_BACKTEST_ENGINE_VERSION,
    BacktestEngine,
    BacktestSpec,
    VectorBacktestEngine,
)
from tradingbotsuite.research.deterministic_datasets import write_hmm_knn_sweep_dataset


def _spec(
    tmp_path: Path,
    *,
    dataset_path: Path,
    dataset_sha256: str,
    run_id: str,
    strategy_id: str = "trend_following_v1",
    holding_window: str = "4h",
    exit_policy_id: str = "fixed_holding_window",
    entry_price_source: str = "next_bar_open",
    interval_ms: int = 900_000,
    entry_latency_ms: int = 900_000,
    lower_timeframe_dataset_path: Path | None = None,
    strategy_config: dict[str, Any] | None = None,
) -> BacktestSpec:
    return BacktestSpec(
        run_id=run_id,
        symbol="BTCUSDT",
        output_dir=tmp_path / "backtests",
        dataset_path=dataset_path,
        dataset_sha256=dataset_sha256,
        strategy_id=strategy_id,
        holding_window=holding_window,
        interval_ms=interval_ms,
        entry_latency_ms=entry_latency_ms,
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256="test-feature-hash",
        entry_price_source=entry_price_source,
        exit_policy_id=exit_policy_id,
        lower_timeframe_dataset_path=lower_timeframe_dataset_path,
        strategy_config=strategy_config if strategy_config is not None else {"slope_threshold": 0.1, "spacing_bars": 8},
    )


def _assert_reference_vector_artifacts_match(reference, vector) -> None:
    assert_frame_equal(pd.read_parquet(vector.trades_path), pd.read_parquet(reference.trades_path), check_dtype=False)
    assert_frame_equal(pd.read_parquet(vector.signals_path), pd.read_parquet(reference.signals_path), check_dtype=False)
    assert_frame_equal(pd.read_parquet(vector.equity_curve_path), pd.read_parquet(reference.equity_curve_path), check_dtype=False)
    assert json.loads(vector.metrics_path.read_text(encoding="utf-8")) == json.loads(reference.metrics_path.read_text(encoding="utf-8"))


def _stable_test_hash(payload: object) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()


def test_vector_fixed_holding_matches_reference_engine_artifacts(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")
    reference = BacktestEngine().run(
        _spec(tmp_path, dataset_path=dataset.parquet_path, dataset_sha256=dataset.parquet_sha256, run_id="reference")
    )
    vector = VectorBacktestEngine().run(
        _spec(tmp_path, dataset_path=dataset.parquet_path, dataset_sha256=dataset.parquet_sha256, run_id="vector")
    )

    _assert_reference_vector_artifacts_match(reference, vector)
    vector_manifest = json.loads(vector.manifest_path.read_text(encoding="utf-8"))
    vector_config = json.loads(vector.config_resolved_path.read_text(encoding="utf-8"))

    assert vector_manifest["engine_version"] == VECTOR_BACKTEST_ENGINE_VERSION
    assert vector_manifest["reference_engine_version"] == BACKTEST_ENGINE_VERSION
    assert vector_manifest["cache_key_components"]["engine_version"] == VECTOR_BACKTEST_ENGINE_VERSION
    assert vector_manifest["config_sha256"] == _stable_test_hash(vector_config)
    assert vector_manifest["research_only"] is True
    assert vector_manifest["observe_only"] is True
    assert vector_manifest["promotion_ready"] is False
    assert vector_manifest["vector_execution_scope"] == "fixed_holding_primary_bar"
    assert vector_manifest["required_metrics_present"] is True
    for output_path in vector_manifest["required_outputs"].values():
        assert Path(output_path).exists()


def test_vector_fixed_holding_alias_matches_reference_engine(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")
    reference = BacktestEngine().run(
        _spec(
            tmp_path,
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            run_id="reference-alias",
            exit_policy_id="4h_time_exit",
        )
    )
    vector = VectorBacktestEngine().run(
        _spec(
            tmp_path,
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            run_id="vector-alias",
            exit_policy_id="4h_time_exit",
        )
    )

    _assert_reference_vector_artifacts_match(reference, vector)


def test_vector_no_trade_artifacts_match_reference_for_all_holding_windows(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")

    for holding_window in ("1h", "4h", "12h", "24h", "72h", "7d"):
        reference = BacktestEngine().run(
            _spec(
                tmp_path,
                dataset_path=dataset.parquet_path,
                dataset_sha256=dataset.parquet_sha256,
                run_id=f"reference-no-trade-{holding_window}",
                strategy_id="baseline_no_trade",
                holding_window=holding_window,
                strategy_config={},
            )
        )
        vector = VectorBacktestEngine().run(
            _spec(
                tmp_path,
                dataset_path=dataset.parquet_path,
                dataset_sha256=dataset.parquet_sha256,
                run_id=f"vector-no-trade-{holding_window}",
                strategy_id="baseline_no_trade",
                holding_window=holding_window,
                strategy_config={},
            )
        )

        _assert_reference_vector_artifacts_match(reference, vector)
        assert pd.read_parquet(vector.trades_path).empty


def test_vector_end_of_data_fallback_matches_reference_engine(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=80, variant="balanced")
    config = {
        "slope_threshold": 0.01,
        "spacing_bars": 74,
        "max_choppiness": 100.0,
        "funding_penalty_threshold": 1.0,
    }
    reference = BacktestEngine().run(
        _spec(
            tmp_path,
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            run_id="reference-fallback",
            strategy_config=config,
        )
    )
    vector = VectorBacktestEngine().run(
        _spec(
            tmp_path,
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            run_id="vector-fallback",
            strategy_config=config,
        )
    )

    _assert_reference_vector_artifacts_match(reference, vector)
    assert pd.read_parquet(vector.trades_path)["exit_used_fallback"].any()


@pytest.mark.parametrize(
    "exit_policy_id",
    [
        "triple_barrier",
        "triple_barrier_atr",
        "volatility_scaled_barrier",
        "regime_flip_exit",
        "funding_adverse_exit",
        "funding_aware_exit_v1",
        "oi_contraction_exit_v1",
        "basis_normalization_exit_v1",
        "premium_normalization_exit_v1",
        "gmm_transition_exit_v1",
        "knn_remaining_edge_exit_v1",
        "knn_dynamic_barriers_v1",
        "alpha_decay_exit",
        "adverse_selection_exit",
        "trailing_atr_after_profit",
        "max_mae_stop",
    ],
)
def test_vector_engine_rejects_unsupported_exit_policy(tmp_path: Path, exit_policy_id: str) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")

    with pytest.raises(ValueError, match="vector_engine_supports_fixed_holding_only"):
        VectorBacktestEngine().run(
            _spec(
                tmp_path,
                dataset_path=dataset.parquet_path,
                dataset_sha256=dataset.parquet_sha256,
                run_id=f"unsupported-{exit_policy_id}",
                exit_policy_id=exit_policy_id,
            )
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("interval_ms", 0, "interval_ms must be positive"),
        ("entry_latency_ms", -1, "entry_latency_ms must be non-negative"),
    ],
)
def test_vector_engine_reuses_reference_assumption_validation(
    tmp_path: Path,
    field: str,
    value: int,
    message: str,
) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")
    overrides = {field: value}

    with pytest.raises(ValueError, match=message):
        VectorBacktestEngine().run(
            _spec(
                tmp_path,
                dataset_path=dataset.parquet_path,
                dataset_sha256=dataset.parquet_sha256,
                run_id=f"invalid-{field}",
                **overrides,
            )
        )


def test_vector_engine_rejects_lower_timeframe_execution_scope(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")

    with pytest.raises(ValueError, match="vector_engine_lower_timeframe_not_supported"):
        VectorBacktestEngine().run(
            _spec(
                tmp_path,
                dataset_path=dataset.parquet_path,
                dataset_sha256=dataset.parquet_sha256,
                run_id="unsupported-lower-timeframe",
                lower_timeframe_dataset_path=dataset.parquet_path,
            )
        )

    with pytest.raises(ValueError, match="vector_engine_entry_price_source_not_supported"):
        VectorBacktestEngine().run(
            _spec(
                tmp_path,
                dataset_path=dataset.parquet_path,
                dataset_sha256=dataset.parquet_sha256,
                run_id="unsupported-entry-source",
                entry_price_source="lower_timeframe_execution_path",
            )
        )
