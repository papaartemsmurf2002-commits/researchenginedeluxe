from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

import tradingbotsuite.backtesting.cuda_engine as cuda_module
import tradingbotsuite.backtesting as backtesting_module
from tradingbotsuite.backtesting import (
    BacktestEngine,
    BacktestSpec,
    CudaFixedHoldingBacktestEngine,
    VectorBacktestEngine,
)
from tradingbotsuite.research.deterministic_datasets import write_hmm_knn_sweep_dataset


class _FakeCupyRuntime:
    @staticmethod
    def getDeviceCount() -> int:
        return 1

    @staticmethod
    def getDeviceProperties(_index: int) -> dict[str, Any]:
        return {"name": b"Fake R97 CUDA Device", "major": 12, "minor": 0}

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


class _FakeRawKernel:
    def __init__(self, code: str, name: str, **kwargs: Any) -> None:
        self.code = code
        self.name = name
        self.kwargs = dict(kwargs)

    def __call__(self, _grid: Any, _block: Any, _args: Any) -> None:
        return None


class _FakeCupyCuda:
    runtime = _FakeCupyRuntime()
    Device = _FakeCupyDevice


class _FakeCupyModule:
    __version__ = "fake-cupy-r97-test"
    cuda = _FakeCupyCuda()
    RawKernel = _FakeRawKernel
    float32 = np.float32
    float64 = np.float64
    int32 = np.int32
    int64 = np.int64
    bool_ = np.bool_

    def __getattr__(self, name: str) -> Any:
        if hasattr(np, name):
            return getattr(np, name)
        raise AttributeError(name)

    @staticmethod
    def asarray(value: Any, dtype: Any | None = None) -> np.ndarray:
        return np.asarray(value, dtype=dtype)

    @staticmethod
    def array(value: Any, dtype: Any | None = None) -> np.ndarray:
        return np.asarray(value, dtype=dtype)

    @staticmethod
    def asnumpy(value: Any) -> np.ndarray:
        return np.asarray(value)

    @staticmethod
    def searchsorted(values: Any, probes: Any, *, side: str = "left") -> np.ndarray:
        return np.searchsorted(np.asarray(values), np.asarray(probes), side=side)

    @staticmethod
    def zeros(shape: Any, dtype: Any = float) -> np.ndarray:
        return np.zeros(shape, dtype=dtype)

    @staticmethod
    def empty(shape: Any, dtype: Any = float) -> np.ndarray:
        return np.empty(shape, dtype=dtype)

    @staticmethod
    def arange(*args: Any, **kwargs: Any) -> np.ndarray:
        return np.arange(*args, **kwargs)

    @staticmethod
    def max(value: Any, *args: Any, **kwargs: Any) -> np.generic:
        return np.max(np.asarray(value), *args, **kwargs)

    @staticmethod
    def min(value: Any, *args: Any, **kwargs: Any) -> np.generic:
        return np.min(np.asarray(value), *args, **kwargs)


_FAKE_CUPY = _FakeCupyModule()


def _batched_engine_class() -> type:
    for name in (
        "CudaBatchedFixedHoldingBacktestEngine",
        "CudaBatchedFixedHoldingEngine",
        "CudaBatchedBacktestEngine",
    ):
        engine_cls = getattr(backtesting_module, name, None) or getattr(cuda_module, name, None)
        if engine_cls is not None:
            return engine_cls
    pytest.fail("R97 batched CUDA fixed-holding engine is not exposed from tradingbotsuite.backtesting")


def _batched_support_fn() -> Callable[..., str | None]:
    for name in (
        "cuda_batched_fixed_holding_support_reason",
        "cuda_batched_backtest_support_reason",
        "cuda_batched_fixed_holding_backtest_support_reason",
    ):
        fn = getattr(backtesting_module, name, None) or getattr(cuda_module, name, None)
        if fn is not None:
            return fn
    pytest.fail("R97 batched CUDA support-reason function is not exposed")


def _batched_runtime_evidence() -> dict[str, Any]:
    for name in (
        "cuda_batched_fixed_holding_runtime_evidence",
        "cuda_batched_runtime_evidence",
    ):
        fn = getattr(cuda_module, name, None)
        if fn is not None:
            return dict(fn())
    return dict(cuda_module.cuda_runtime_evidence())


def _support_reason(fn: Callable[..., str | None], spec: BacktestSpec, *, check_runtime: bool = True) -> str | None:
    try:
        return fn(spec, check_runtime=check_runtime)
    except TypeError:
        return fn(spec)


def _install_fake_cupy(monkeypatch: pytest.MonkeyPatch) -> None:
    for loader_name in ("_load_cupy", "_load_batched_cupy", "_load_cuda_module"):
        if hasattr(cuda_module, loader_name):
            monkeypatch.setattr(cuda_module, loader_name, lambda: _FAKE_CUPY)


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
        feature_set_id="features_price_trend_vol",
        feature_manifest_sha256="test-feature-hash",
        entry_price_source=entry_price_source,
        exit_policy_id=exit_policy_id,
        lower_timeframe_dataset_path=lower_timeframe_dataset_path,
        strategy_config=strategy_config if strategy_config is not None else {"slope_threshold": 0.1, "spacing_bars": 8},
    )


def _assert_batched_matches_reference_vector_and_r96(reference: Any, vector: Any, r96_cuda: Any, batched: Any) -> None:
    assert_frame_equal(pd.read_parquet(batched.signals_path), pd.read_parquet(reference.signals_path), check_dtype=False)
    assert_frame_equal(
        pd.read_parquet(batched.trades_path),
        pd.read_parquet(vector.trades_path),
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    assert_frame_equal(
        pd.read_parquet(batched.trades_path),
        pd.read_parquet(r96_cuda.trades_path),
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    assert_frame_equal(
        pd.read_parquet(batched.equity_curve_path),
        pd.read_parquet(vector.equity_curve_path),
        check_dtype=False,
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    reference_metrics = json.loads(reference.metrics_path.read_text(encoding="utf-8"))
    batched_metrics = json.loads(batched.metrics_path.read_text(encoding="utf-8"))
    assert set(batched_metrics) == set(reference_metrics)
    for key, value in reference_metrics.items():
        if isinstance(value, (int, float)):
            assert batched_metrics[key] == pytest.approx(value, rel=1e-12, abs=1e-12)
        else:
            assert batched_metrics[key] == value


@pytest.mark.parametrize(
    "case",
    [
        {"name": "default"},
        {"name": "alias", "exit_policy_id": "4h_time_exit"},
        {"name": "no-trade", "strategy_id": "baseline_no_trade", "strategy_config": {}},
        {"name": "vwap", "entry_price_source": "vwap_approximation"},
        {"name": "signal-close", "entry_price_source": "signal_bar_close_plus_latency"},
        {"name": "primary-open-latency", "entry_price_source": "primary_bar_open_plus_latency"},
    ],
)
def test_cuda_batched_fixed_holding_matches_reference_vector_and_r96_with_fake_cupy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: dict[str, Any],
) -> None:
    _install_fake_cupy(monkeypatch)
    engine_cls = _batched_engine_class()
    dataset = write_hmm_knn_sweep_dataset(
        output_dir=tmp_path / "datasets" / str(case["name"]),
        row_count=160,
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

    reference = BacktestEngine().run(_spec(tmp_path, run_id=f"reference-r97-{case['name']}", **common))
    vector = VectorBacktestEngine().run(_spec(tmp_path, run_id=f"vector-r97-{case['name']}", **common))
    r96_cuda = CudaFixedHoldingBacktestEngine().run(_spec(tmp_path, run_id=f"r96-cuda-r97-{case['name']}", **common))
    batched = engine_cls().run(_spec(tmp_path, run_id=f"batched-r97-{case['name']}", **common))

    _assert_batched_matches_reference_vector_and_r96(reference, vector, r96_cuda, batched)


def test_cuda_batched_fixed_holding_manifest_records_research_only_rawkernel_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_cupy(monkeypatch)
    engine_cls = _batched_engine_class()
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")

    result = engine_cls().run(
        _spec(
            tmp_path,
            dataset_path=dataset.parquet_path,
            dataset_sha256=dataset.parquet_sha256,
            run_id="batched-manifest",
        )
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["diagnostic_only"] is True
    assert manifest["position_sizing_input"] is False
    assert manifest["live_signal_input"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["speed_claimed"] is False
    assert manifest["cuda_execution_scope"] == "cuda_batched_fixed_holding_primary_bar"
    assert "rawkernel" in str(manifest["cuda_kernel_scope"]).lower()
    assert str(manifest["cuda_kernel_sha256"])
    assert str(manifest["cuda_sm_target"])
    assert str(manifest["cuda_precision_policy"])
    assert str(manifest["cuda_determinism_policy"])
    assert manifest["cuda_parity_status"] == "parity_required_before_performance_claim"
    assert str(manifest["cpu_reference_result_sha256"])
    assert float(manifest["max_trade_diff"]) == pytest.approx(0.0)
    assert float(manifest["max_equity_diff"]) == pytest.approx(0.0)
    assert manifest["backtest_backend_fallback_reason"] == ""
    runtime = manifest["gpu_runtime_evidence"]
    assert runtime["research_only"] is True
    assert runtime["observe_only"] is True
    assert runtime["promotion_ready"] is False


def test_cuda_batched_fixed_holding_reports_scope_and_runtime_fallback_reasons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    support_reason = _batched_support_fn()
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=80, variant="balanced")
    unsupported = _spec(
        tmp_path,
        dataset_path=dataset.parquet_path,
        dataset_sha256=dataset.parquet_sha256,
        run_id="batched-unsupported-lower-timeframe",
        lower_timeframe_dataset_path=dataset.parquet_path,
    )

    scope_reason = _support_reason(support_reason, unsupported, check_runtime=False)
    assert scope_reason is not None
    assert "unsupported" in scope_reason
    assert "lower_timeframe" in scope_reason
    assert "vector_engine_lower_timeframe_not_supported" in scope_reason

    def raise_import_error() -> Any:
        raise ImportError("cupy intentionally unavailable in fallback test")

    for loader_name in ("_load_cupy", "_load_batched_cupy", "_load_cuda_module"):
        if hasattr(cuda_module, loader_name):
            monkeypatch.setattr(cuda_module, loader_name, raise_import_error)
    supported = _spec(
        tmp_path,
        dataset_path=dataset.parquet_path,
        dataset_sha256=dataset.parquet_sha256,
        run_id="batched-runtime-unavailable",
    )

    runtime_reason = _support_reason(support_reason, supported)
    assert runtime_reason is not None
    assert "cupy" in runtime_reason or "runtime" in runtime_reason


def test_cuda_batched_fixed_holding_matches_reference_when_runtime_available(tmp_path: Path) -> None:
    engine_cls = _batched_engine_class()
    support_reason = _batched_support_fn()
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=160, variant="balanced")
    spec = _spec(
        tmp_path,
        dataset_path=dataset.parquet_path,
        dataset_sha256=dataset.parquet_sha256,
        run_id="batched-runtime",
    )
    reason = _support_reason(support_reason, spec)
    if reason is not None:
        runtime = _batched_runtime_evidence()
        pytest.skip(f"R97 batched CUDA runtime unavailable: {reason}; evidence={runtime}")

    reference = BacktestEngine().run(_spec(tmp_path, dataset_path=dataset.parquet_path, dataset_sha256=dataset.parquet_sha256, run_id="reference-runtime"))
    vector = VectorBacktestEngine().run(_spec(tmp_path, dataset_path=dataset.parquet_path, dataset_sha256=dataset.parquet_sha256, run_id="vector-runtime"))
    r96_cuda = CudaFixedHoldingBacktestEngine().run(_spec(tmp_path, dataset_path=dataset.parquet_path, dataset_sha256=dataset.parquet_sha256, run_id="r96-runtime"))
    batched = engine_cls().run(spec)

    _assert_batched_matches_reference_vector_and_r96(reference, vector, r96_cuda, batched)
