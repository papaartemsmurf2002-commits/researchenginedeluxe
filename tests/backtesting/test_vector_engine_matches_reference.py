from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from tradingbotsuite.backtesting import (
    BACKTEST_ENGINE_VERSION,
    CUDA_BACKTEST_ENGINE_VERSION,
    CUDA_EXECUTION_SCOPE,
    VECTOR_BACKTEST_ENGINE_VERSION,
    BacktestEngine,
    BacktestSpec,
    CudaFixedHoldingBacktestEngine,
    VectorBacktestEngine,
    cuda_backtest_support_reason,
    cuda_runtime_evidence,
)
from tradingbotsuite.research.deterministic_datasets import write_hmm_knn_sweep_dataset


class _FakeCupyRuntime:
    @staticmethod
    def getDeviceCount() -> int:
        return 1

    @staticmethod
    def getDeviceProperties(_index: int) -> dict[str, Any]:
        return {"name": b"Fake CUDA Device", "major": 12, "minor": 0}

    @staticmethod
    def driverGetVersion() -> int:
        return 13020

    @staticmethod
    def runtimeGetVersion() -> int:
        return 12090


class _FakeCupyDevice:
    def __init__(self, _index: int) -> None:
        self.mem_info = (8 * 1024 * 1024, 16 * 1024 * 1024)

    def __enter__(self) -> "_FakeCupyDevice":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _FakeCupyCuda:
    runtime = _FakeCupyRuntime()
    Device = _FakeCupyDevice


class _FakeCupy:
    __version__ = "fake-cupy-test"
    cuda = _FakeCupyCuda()

    @staticmethod
    def asarray(value: Any) -> np.ndarray:
        return np.asarray(value)

    @staticmethod
    def asnumpy(value: Any) -> np.ndarray:
        return np.asarray(value)

    @staticmethod
    def searchsorted(values: Any, probes: Any, *, side: str = "left") -> np.ndarray:
        return np.searchsorted(np.asarray(values), np.asarray(probes), side=side)

    @staticmethod
    def max(value: Any) -> np.generic:
        return np.max(np.asarray(value))

    @staticmethod
    def min(value: Any) -> np.generic:
        return np.min(np.asarray(value))


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


def _assert_cuda_artifacts_match(reference, vector, cuda) -> None:
    assert_frame_equal(pd.read_parquet(cuda.signals_path), pd.read_parquet(reference.signals_path), check_dtype=False)
    assert_frame_equal(pd.read_parquet(cuda.trades_path), pd.read_parquet(vector.trades_path), check_dtype=False, check_exact=False, rtol=1e-12, atol=1e-12)
    assert_frame_equal(pd.read_parquet(cuda.equity_curve_path), pd.read_parquet(vector.equity_curve_path), check_dtype=False, check_exact=False, rtol=1e-12, atol=1e-12)
    reference_metrics = json.loads(reference.metrics_path.read_text(encoding="utf-8"))
    cuda_metrics = json.loads(cuda.metrics_path.read_text(encoding="utf-8"))
    assert set(cuda_metrics) == set(reference_metrics)
    for key, value in reference_metrics.items():
        if isinstance(value, (int, float)):
            assert cuda_metrics[key] == pytest.approx(value, rel=1e-12, abs=1e-12)
        else:
            assert cuda_metrics[key] == value


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
    trades = pd.read_parquet(reference.trades_path)
    assert not trades.empty
    assert trades["exit_policy"].eq("fixed_holding_window").all()
    assert trades["requested_exit_policy"].eq("fixed_holding_window").all()
    assert trades["canonical_exit_policy"].eq("fixed_holding_window").all()
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


@pytest.mark.parametrize(
    "entry_price_source,expected_fill_profile",
    [
        ("signal_bar_close_plus_latency", "signal_close_latency_fill"),
        ("primary_bar_open_plus_latency", "primary_bar_latency_fill"),
    ],
)
def test_vector_fixed_holding_matches_reference_for_latency_entry_sources(
    tmp_path: Path,
    entry_price_source: str,
    expected_fill_profile: str,
) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")
    common = {
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "entry_price_source": entry_price_source,
    }
    reference = BacktestEngine().run(_spec(tmp_path, run_id=f"reference-{entry_price_source}", **common))
    vector = VectorBacktestEngine().run(_spec(tmp_path, run_id=f"vector-{entry_price_source}", **common))

    _assert_reference_vector_artifacts_match(reference, vector)
    trades = pd.read_parquet(reference.trades_path)
    assert not trades.empty
    assert trades["exit_policy"].eq("fixed_holding_window").all()
    assert trades["requested_exit_policy"].eq("fixed_holding_window").all()
    assert trades["canonical_exit_policy"].eq("fixed_holding_window").all()
    manifest = json.loads(reference.manifest_path.read_text(encoding="utf-8"))
    trades = pd.read_parquet(reference.trades_path)
    signals = pd.read_parquet(reference.signals_path).set_index("signal_id")

    assert manifest["cost_model"]["fill_profile_id"] == expected_fill_profile
    assert not trades.empty
    if entry_price_source == "signal_bar_close_plus_latency":
        first_trade = trades.iloc[0]
        first_signal = signals.loc[first_trade["signal_id"]]
        assert first_trade["entry_price"] == pytest.approx(float(first_signal["signal_bar_close"]))


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
    trades = pd.read_parquet(reference.trades_path)
    assert not trades.empty
    assert trades["exit_policy"].eq("fixed_holding_window").all()
    assert trades["requested_exit_policy"].eq("4h_time_exit").all()
    assert trades["canonical_exit_policy"].eq("fixed_holding_window").all()


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


def test_cuda_fixed_holding_reports_runtime_or_scope_support_reason(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=80, variant="balanced")
    supported_spec = _spec(
        tmp_path,
        dataset_path=dataset.parquet_path,
        dataset_sha256=dataset.parquet_sha256,
        run_id="cuda-support-check",
    )
    support_reason = cuda_backtest_support_reason(supported_spec)
    runtime = cuda_runtime_evidence()

    if runtime["available"]:
        assert support_reason is None
        assert runtime["gpu_name"]
        assert runtime["compute_capability"]
    else:
        assert support_reason == runtime["unavailable_reason"]
        assert support_reason in {
            "cuda_engine_cupy_unavailable",
            "cuda_engine_no_device",
            "cuda_engine_runtime_unavailable",
            "cuda_engine_runtime_smoke_failed",
        }

    unsupported_spec = _spec(
        tmp_path,
        dataset_path=dataset.parquet_path,
        dataset_sha256=dataset.parquet_sha256,
        run_id="cuda-unsupported-lower-timeframe",
        lower_timeframe_dataset_path=dataset.parquet_path,
    )
    assert (
        cuda_backtest_support_reason(unsupported_spec)
        == "cuda_engine_scope_unsupported:vector_engine_lower_timeframe_not_supported"
    )


def test_cuda_fixed_holding_rejects_when_runtime_unavailable(tmp_path: Path) -> None:
    runtime = cuda_runtime_evidence()
    if runtime["available"]:
        pytest.skip("CUDA runtime is available; parity test covers execution")
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=80, variant="balanced")

    with pytest.raises(ValueError, match=str(runtime["unavailable_reason"])):
        CudaFixedHoldingBacktestEngine().run(
            _spec(
                tmp_path,
                dataset_path=dataset.parquet_path,
                dataset_sha256=dataset.parquet_sha256,
                run_id="cuda-runtime-unavailable",
            )
        )


@pytest.mark.parametrize(
    "case",
    [
        {"name": "default"},
        {"name": "alias", "exit_policy_id": "4h_time_exit"},
        {"name": "no-trade", "strategy_id": "baseline_no_trade", "strategy_config": {}},
        {
            "name": "end-of-data",
            "row_count": 80,
            "strategy_config": {
                "slope_threshold": 0.01,
                "spacing_bars": 74,
                "max_choppiness": 100.0,
                "funding_penalty_threshold": 1.0,
            },
        },
        {"name": "vwap", "entry_price_source": "vwap_approximation"},
        {"name": "signal-close", "entry_price_source": "signal_bar_close_plus_latency"},
        {"name": "primary-open-latency", "entry_price_source": "primary_bar_open_plus_latency"},
    ],
)
def test_cuda_fixed_holding_matches_reference_with_fake_cupy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: dict[str, Any],
) -> None:
    import tradingbotsuite.backtesting.cuda_engine as cuda_module

    monkeypatch.setattr(cuda_module, "_load_cupy", lambda: _FakeCupy)
    dataset = write_hmm_knn_sweep_dataset(
        output_dir=tmp_path / "datasets" / str(case["name"]),
        row_count=int(case.get("row_count", 160)),
        variant="balanced",
    )
    common = {
        "dataset_path": dataset.parquet_path,
        "dataset_sha256": dataset.parquet_sha256,
        "exit_policy_id": str(case.get("exit_policy_id", "fixed_holding_window")),
        "entry_price_source": str(case.get("entry_price_source", "next_bar_open")),
        "strategy_id": str(case.get("strategy_id", "trend_following_v1")),
        "strategy_config": case.get("strategy_config"),
    }

    reference = BacktestEngine().run(_spec(tmp_path, run_id=f"reference-fake-{case['name']}", **common))
    vector = VectorBacktestEngine().run(_spec(tmp_path, run_id=f"vector-fake-{case['name']}", **common))
    cuda = CudaFixedHoldingBacktestEngine().run(_spec(tmp_path, run_id=f"cuda-fake-{case['name']}", **common))

    _assert_cuda_artifacts_match(reference, vector, cuda)
    manifest = json.loads(cuda.manifest_path.read_text(encoding="utf-8"))
    assert manifest["gpu_runtime_evidence"]["runtime_smoke_test"] == "passed"
    assert manifest["cuda_kernel_scope"] == "cupy_searchsorted_batches_with_cpu_trade_loop"
    assert manifest["speed_claimed"] is False


def test_cuda_fixed_holding_matches_reference_when_runtime_available(tmp_path: Path) -> None:
    runtime = cuda_runtime_evidence()
    if not runtime["available"]:
        pytest.skip(f"CUDA runtime unavailable: {runtime['unavailable_reason']}")
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")
    reference = BacktestEngine().run(
        _spec(tmp_path, dataset_path=dataset.parquet_path, dataset_sha256=dataset.parquet_sha256, run_id="reference-cuda")
    )
    vector = VectorBacktestEngine().run(
        _spec(tmp_path, dataset_path=dataset.parquet_path, dataset_sha256=dataset.parquet_sha256, run_id="vector-cuda")
    )
    cuda = CudaFixedHoldingBacktestEngine().run(
        _spec(tmp_path, dataset_path=dataset.parquet_path, dataset_sha256=dataset.parquet_sha256, run_id="cuda")
    )

    _assert_cuda_artifacts_match(reference, vector, cuda)

    manifest = json.loads(cuda.manifest_path.read_text(encoding="utf-8"))
    assert manifest["engine_version"] == CUDA_BACKTEST_ENGINE_VERSION
    assert manifest["reference_engine_version"] == BACKTEST_ENGINE_VERSION
    assert manifest["vector_reference_engine_version"] == VECTOR_BACKTEST_ENGINE_VERSION
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["diagnostic_only"] is True
    assert manifest["cuda_execution_scope"] == CUDA_EXECUTION_SCOPE
    assert manifest["cuda_kernel_scope"] == "cupy_searchsorted_batches_with_cpu_trade_loop"
    assert manifest["gpu_execution_status"] == "cuda_fixed_holding_executed"
    assert manifest["cuda_parity_status"] == "parity_required_before_performance_claim"
    assert manifest["speed_claimed"] is False
    assert manifest["gpu_runtime_evidence"]["runtime_smoke_test"] == "passed"
