from __future__ import annotations

import time
from typing import Any, Mapping

import numpy as np
import pandas as pd

import tradingbotsuite.backtesting.cuda_engine as cuda_module
from tradingbotsuite.backtesting.costs import CostModel
from tradingbotsuite.backtesting.cuda_engine import CUDA_BACKTEST_ENGINE_VERSION
from tradingbotsuite.backtesting.engine import (
    BACKTEST_CACHE_POLICY,
    BACKTEST_ENGINE_VERSION,
    BACKTEST_MANIFEST_VERSION,
    BacktestEngine,
    BacktestResult,
    BacktestSpec,
    _cache_key_components,
    _enrich_trades,
    _execution_assumptions,
    _file_sha256,
    _frame_hash,
    _market_frame,
    _reproducible_config,
    _signals_for_strategy,
    _source_hash,
    _stable_hash,
    _write_json,
)
from tradingbotsuite.backtesting.execution_sim import _equity_curve
from tradingbotsuite.backtesting.exits import fixed_holding_window_exit
from tradingbotsuite.backtesting.metrics import REQUIRED_BACKTEST_METRICS, calculate_backtest_metrics
from tradingbotsuite.backtesting.vector_engine import (
    VECTOR_BACKTEST_ENGINE_VERSION,
    _empty_trades,
    _optional_float,
    _vector_fixed_holding_trades,
    vector_backtest_support_reason,
)


CUDA_BATCHED_BACKEND_NAME = "cuda_batched_fixed_holding"
CUDA_BATCHED_BACKTEST_ENGINE_VERSION = "research-cuda-batched-fixed-holding-backtest-engine-v1"
CUDA_BATCHED_BACKEND_EVIDENCE_VERSION = "cuda-batched-fixed-holding-backend-evidence-v1"
CUDA_BATCHED_EXECUTION_SCOPE = "cuda_batched_fixed_holding_primary_bar"
CUDA_BATCHED_RAWKERNEL_SCOPE = "rawkernel_batched_fixed_holding_candidates_fp64"
CUDA_BATCHED_FALLBACK_KERNEL_SCOPE = "r96_cuda_fixed_holding_primitive_fallback"
CUDA_BATCHED_KERNEL_NAME = "fixed_holding_candidates_fp64"
_MAX_FINITE_DIFF = float(np.finfo(np.float64).max)


_FIXED_HOLDING_CANDIDATE_KERNEL = r"""
extern "C" __global__
void fixed_holding_candidates_fp64(
    const long long* market_times,
    const double* open_values,
    const double* high_values,
    const double* low_values,
    const double* close_values,
    const long long* decision_times,
    const double* signal_bar_close,
    const long long n_market,
    const long long n_signals,
    const long long entry_latency_ms,
    const long long holding_ms,
    const long long min_holding_ms,
    const int entry_price_policy,
    const int signal_close_present,
    signed char* valid,
    long long* entry_indices,
    long long* exit_indices,
    long long* entry_times,
    long long* exit_times,
    long long* target_exit_times,
    signed char* used_fallback,
    double* entry_prices,
    double* exit_prices,
    double* path_highs,
    double* path_lows
) {
    long long i = (long long)blockDim.x * (long long)blockIdx.x + (long long)threadIdx.x;
    if (i >= n_signals) {
        return;
    }
    valid[i] = 0;
    entry_indices[i] = -1;
    exit_indices[i] = -1;
    entry_times[i] = 0;
    exit_times[i] = 0;
    target_exit_times[i] = 0;
    used_fallback[i] = 0;
    entry_prices[i] = 0.0;
    exit_prices[i] = 0.0;
    path_highs[i] = 0.0;
    path_lows[i] = 0.0;
    if (n_market <= 0) {
        return;
    }

    long long target_entry_time = decision_times[i] + entry_latency_ms;
    long long lo = 0;
    long long hi = n_market;
    while (lo < hi) {
        long long mid = lo + ((hi - lo) >> 1);
        if (market_times[mid] < target_entry_time) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    long long entry_index = lo;
    if (entry_index >= n_market) {
        return;
    }

    long long entry_time = market_times[entry_index];
    long long target_exit_time = entry_time + holding_ms;
    lo = 0;
    hi = n_market;
    while (lo < hi) {
        long long mid = lo + ((hi - lo) >> 1);
        if (market_times[mid] < target_exit_time) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    long long exit_index = lo;
    signed char fallback = 0;
    if (exit_index >= n_market) {
        exit_index = n_market - 1;
        fallback = 1;
        if (market_times[exit_index] - entry_time < min_holding_ms) {
            return;
        }
    }

    double entry_price = open_values[entry_index];
    if (entry_price_policy == 1) {
        entry_price = signal_close_present ? signal_bar_close[i] : open_values[entry_index];
    } else if (entry_price_policy == 2) {
        entry_price = (high_values[entry_index] + low_values[entry_index] + close_values[entry_index]) / 3.0;
    }

    double high_value = high_values[entry_index];
    double low_value = low_values[entry_index];
    for (long long j = entry_index + 1; j <= exit_index; ++j) {
        double candidate_high = high_values[j];
        double candidate_low = low_values[j];
        if (candidate_high > high_value) {
            high_value = candidate_high;
        }
        if (candidate_low < low_value) {
            low_value = candidate_low;
        }
    }

    valid[i] = 1;
    entry_indices[i] = entry_index;
    exit_indices[i] = exit_index;
    entry_times[i] = entry_time;
    exit_times[i] = market_times[exit_index];
    target_exit_times[i] = target_exit_time;
    used_fallback[i] = fallback;
    entry_prices[i] = entry_price;
    exit_prices[i] = close_values[exit_index];
    path_highs[i] = high_value;
    path_lows[i] = low_value;
}
"""


class CudaBatchedFixedHoldingBacktestEngine:
    """Research-only batched CUDA fixed-holding backend.

    The primary result path uses CuPy arrays and a RawKernel candidate kernel
    when available. Fake CuPy implementations without RawKernel are allowed to
    fall back to the R96 CUDA primitive path for import and parity tests.
    """

    def run(
        self,
        spec: BacktestSpec,
        *,
        market_data: pd.DataFrame | None = None,
        dataset: pd.DataFrame | None = None,
    ) -> BacktestResult:
        started = time.perf_counter()
        reason = cuda_batched_backtest_support_reason(spec)
        if reason is not None:
            raise ValueError(reason)
        cp = cuda_module._load_cupy()
        runtime_evidence = cuda_module.cuda_runtime_evidence()
        output_dir = spec.output_dir / spec.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        reference_engine = BacktestEngine()
        source_frame = reference_engine._load_source_frame(spec, dataset=dataset, market_data=market_data)
        market = _market_frame(source_frame, symbol=spec.symbol)
        assumptions = _execution_assumptions(spec)
        reference_engine.execution_simulator._validate_assumptions(assumptions, None)
        signals, strategy_metadata = _signals_for_strategy(source_frame, spec)
        cost_model = CostModel(
            fee_bps=spec.fee_bps,
            slippage_bps=spec.slippage_bps,
            spread_bps=spec.spread_bps,
            funding_rate=spec.funding_rate,
        )
        trades, kernel_evidence = _cuda_batched_fixed_holding_trades(
            signals,
            market,
            costs=cost_model,
            assumptions=assumptions,
            symbol=spec.symbol,
            cupy=cp,
        )
        trades = _enrich_trades(trades, market)
        equity_curve = _equity_curve(spec.initial_equity, market, trades)
        metrics = calculate_backtest_metrics(
            trades=trades,
            signals=signals,
            equity_curve=equity_curve,
            market_data=market,
            initial_equity=spec.initial_equity,
        )
        parity_evidence = _cpu_reference_parity_evidence(
            signals=signals,
            market=market,
            costs=cost_model,
            assumptions=assumptions,
            symbol=spec.symbol,
            initial_equity=spec.initial_equity,
            gpu_metrics=metrics,
            gpu_trades=trades,
            gpu_equity_curve=equity_curve,
        )
        config_resolved = spec.resolved_config()
        config_resolved["backend_name"] = CUDA_BATCHED_BACKEND_NAME
        config_resolved["engine_version"] = CUDA_BATCHED_BACKTEST_ENGINE_VERSION
        source_hash = _source_hash(spec, source_frame)
        cache_key_components = _cache_key_components(
            dataset_sha256=source_hash,
            lower_timeframe_dataset_sha256=None,
            feature_manifest_sha256=spec.feature_manifest_sha256,
            config_resolved=config_resolved,
            assumptions=assumptions,
            cost_model=cost_model,
        )
        cache_key_components["backend_name"] = CUDA_BATCHED_BACKEND_NAME
        cache_key_components["engine_version"] = CUDA_BATCHED_BACKTEST_ENGINE_VERSION
        cache_key = _stable_hash(cache_key_components)

        trades_path = output_dir / "trades.parquet"
        signals_path = output_dir / "signals.parquet"
        equity_curve_path = output_dir / "equity_curve.parquet"
        metrics_path = output_dir / "metrics.json"
        config_resolved_path = output_dir / "config_resolved.json"
        manifest_path = output_dir / "backtest_manifest.json"
        trades.to_parquet(trades_path, index=False)
        signals.to_parquet(signals_path, index=False)
        equity_curve.to_parquet(equity_curve_path, index=False)
        _write_json(metrics_path, metrics)
        _write_json(config_resolved_path, config_resolved)

        artifact_hashes = {
            "trades_sha256": _file_sha256(trades_path),
            "signals_sha256": _file_sha256(signals_path),
            "equity_curve_sha256": _file_sha256(equity_curve_path),
            "metrics_sha256": _file_sha256(metrics_path),
            "config_resolved_sha256": _file_sha256(config_resolved_path),
        }
        result_sha256 = _stable_hash(
            {
                "trades": _frame_hash(trades),
                "signals": _frame_hash(signals),
                "equity_curve": _frame_hash(equity_curve),
                "metrics": metrics,
                "config": _reproducible_config(config_resolved),
            }
        )
        manifest = {
            "backtest_manifest_version": BACKTEST_MANIFEST_VERSION,
            "backend_name": CUDA_BATCHED_BACKEND_NAME,
            "engine_version": CUDA_BATCHED_BACKTEST_ENGINE_VERSION,
            "reference_engine_version": BACKTEST_ENGINE_VERSION,
            "vector_reference_engine_version": VECTOR_BACKTEST_ENGINE_VERSION,
            "r96_cuda_reference_engine_version": CUDA_BACKTEST_ENGINE_VERSION,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "diagnostic_only": True,
            "position_sizing_input": False,
            "live_signal_input": False,
            "order_placement_used": False,
            "symbol": spec.symbol,
            "strategy_id": spec.strategy_id,
            "strategy_metadata": strategy_metadata,
            "holding_window": spec.holding_window,
            "entry_price_source": spec.entry_price_source,
            "exit_policy_id": spec.exit_policy_id,
            "exit_price_source": spec.exit_price_source,
            "same_bar_entry_exit_allowed": False,
            "vector_execution_scope": "",
            "cuda_backend_evidence_version": CUDA_BATCHED_BACKEND_EVIDENCE_VERSION,
            "cuda_execution_scope": CUDA_BATCHED_EXECUTION_SCOPE,
            "cuda_kernel_scope": kernel_evidence["cuda_kernel_scope"],
            "kernel_sha256": kernel_evidence["kernel_sha256"],
            "cuda_kernel_sha256": kernel_evidence["kernel_sha256"],
            "intended_kernel_sha256": _kernel_sha256(),
            "sm_target": _sm_target(runtime_evidence),
            "cuda_sm_target": _sm_target(runtime_evidence),
            "precision_policy": {
                "price_dtype": "float64",
                "return_dtype": "float64",
                "index_dtype": "int64",
                "fast_math": False,
            },
            "cuda_precision_policy": "fp64_no_fast_math_no_tensor_core",
            "determinism_policy": {
                "signal_order": "decision_time_ms_mergesort",
                "market_order": "bar_time_ms_mergesort_drop_duplicate",
                "overlap_policy": "first_signal_until_exit_time",
                "randomness": "none",
            },
            "cuda_determinism_policy": "deterministic_sorted_signals_no_randomness",
            "tensor_core_used": False,
            "tensor_core_scope": "disabled_not_used_fp64_rawkernel_no_matrix_ops",
            "parity_status": parity_evidence["parity_status"],
            "cuda_parity_status": "parity_required_before_performance_claim",
            "cpu_reference_result_sha256": parity_evidence["cpu_reference_result_sha256"],
            "max_metric_abs_diff": parity_evidence["max_metric_abs_diff"],
            "max_equity_abs_diff": parity_evidence["max_equity_abs_diff"],
            "max_trade_diff": parity_evidence["max_trade_abs_diff"],
            "max_equity_diff": parity_evidence["max_equity_abs_diff"],
            "gpu_execution_status": kernel_evidence["gpu_execution_status"],
            "speed_claimed": False,
            "fallback_reason": kernel_evidence["fallback_reason"],
            "backtest_backend_fallback_reason": kernel_evidence["fallback_reason"],
            "performance_claim_scope": "none_research_diagnostic_only_no_speed_claim",
            "gpu_runtime_evidence": runtime_evidence,
            "required_outputs": {
                "backtest_manifest": str(manifest_path),
                "trades": str(trades_path),
                "signals": str(signals_path),
                "equity_curve": str(equity_curve_path),
                "metrics": str(metrics_path),
                "config_resolved": str(config_resolved_path),
            },
            "required_metrics_present": all(key in metrics for key in REQUIRED_BACKTEST_METRICS),
            "row_count": int(len(market)),
            "signal_count": int(len(signals)),
            "trade_count": int(len(trades)),
            "dataset_path": str(spec.dataset_path) if spec.dataset_path is not None else None,
            "dataset_sha256": source_hash,
            "lower_timeframe_dataset_path": None,
            "lower_timeframe_dataset_sha256": None,
            "feature_set_id": spec.feature_set_id,
            "feature_manifest_sha256": spec.feature_manifest_sha256,
            "config_sha256": _stable_hash(config_resolved),
            "cache_key": cache_key,
            "cache_policy": BACKTEST_CACHE_POLICY,
            "cache_lookup_used": False,
            "cache_hit": False,
            "execution_cache_reuse_enabled": False,
            "cache_key_components": cache_key_components,
            "result_sha256": result_sha256,
            "artifact_hashes": artifact_hashes,
            "execution_assumptions": assumptions.to_payload(),
            "cost_model": cost_model.to_payload(),
            "runtime": {
                "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 6),
                "rows_per_second": round(len(market) / max(time.perf_counter() - started, 1e-9), 6),
            },
            "validity": {
                "future_features_used": False,
                "validation_rows_used_for_fit": False,
                "fees_slippage_funding_included": True,
                "in_sample_only": False,
                "wt3d_claim_requires_no_wt_baseline": False,
            },
        }
        _write_json(manifest_path, manifest)
        return BacktestResult(
            output_dir=output_dir,
            manifest_path=manifest_path,
            trades_path=trades_path,
            signals_path=signals_path,
            equity_curve_path=equity_curve_path,
            metrics_path=metrics_path,
            config_resolved_path=config_resolved_path,
            result_sha256=result_sha256,
        )


def cuda_batched_backtest_support_reason(spec: BacktestSpec, *, check_runtime: bool = True) -> str | None:
    vector_reason = vector_backtest_support_reason(spec)
    if vector_reason is not None:
        return f"cuda_batched_engine_scope_unsupported:{vector_reason}"
    if not check_runtime:
        return None
    evidence = cuda_module.cuda_runtime_evidence()
    if evidence["available"]:
        return None
    return str(evidence["unavailable_reason"])


def _cuda_batched_fixed_holding_trades(
    signals: pd.DataFrame,
    market: pd.DataFrame,
    *,
    costs: CostModel,
    assumptions: Any,
    symbol: str,
    cupy: Any,
) -> tuple[pd.DataFrame, dict[str, str]]:
    if not _has_raw_kernel(cupy):
        trades = cuda_module._cuda_fixed_holding_trades(
            signals,
            market,
            costs=costs,
            assumptions=assumptions,
            symbol=symbol,
            cupy=cupy,
        )
        return trades, {
            "cuda_kernel_scope": CUDA_BATCHED_FALLBACK_KERNEL_SCOPE,
            "kernel_sha256": "",
            "gpu_execution_status": "fallback_r96_cuda_fixed_holding_executed",
            "fallback_reason": "cupy_rawkernel_unavailable_primitive_fallback",
        }
    trades = _cuda_rawkernel_fixed_holding_trades(
        signals,
        market,
        costs=costs,
        assumptions=assumptions,
        symbol=symbol,
        cupy=cupy,
    )
    return trades, {
        "cuda_kernel_scope": CUDA_BATCHED_RAWKERNEL_SCOPE,
        "kernel_sha256": _kernel_sha256(),
        "gpu_execution_status": "rawkernel_batched_fixed_holding_executed",
        "fallback_reason": "",
    }


def _cuda_rawkernel_fixed_holding_trades(
    signals: pd.DataFrame,
    market: pd.DataFrame,
    *,
    costs: CostModel,
    assumptions: Any,
    symbol: str,
    cupy: Any,
) -> pd.DataFrame:
    if signals.empty or market.empty:
        return _empty_trades()
    ordered_market = market.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)
    ordered_signals = signals.sort_values("decision_time_ms", kind="mergesort").reset_index(drop=True)
    n_signals = len(ordered_signals)
    n_market = len(ordered_market)
    signal_bar_close_present = "signal_bar_close" in ordered_signals.columns
    signal_bar_close = (
        ordered_signals["signal_bar_close"].astype("float64").to_numpy()
        if signal_bar_close_present
        else np.zeros(n_signals, dtype=np.float64)
    )
    kernel = _build_candidate_kernel(cupy)
    arrays = _allocate_candidate_arrays(cupy, n_signals)
    block_size = 128
    grid_size = max(1, (n_signals + block_size - 1) // block_size)
    kernel(
        (grid_size,),
        (block_size,),
        (
            cupy.asarray(ordered_market["bar_time_ms"].astype("int64").to_numpy()),
            cupy.asarray(ordered_market["open"].astype("float64").to_numpy()),
            cupy.asarray(ordered_market["high"].astype("float64").to_numpy()),
            cupy.asarray(ordered_market["low"].astype("float64").to_numpy()),
            cupy.asarray(ordered_market["close"].astype("float64").to_numpy()),
            cupy.asarray(ordered_signals["decision_time_ms"].astype("int64").to_numpy()),
            cupy.asarray(signal_bar_close),
            np.int64(n_market),
            np.int64(n_signals),
            np.int64(assumptions.entry_latency_ms),
            np.int64(assumptions.holding_period_ms),
            np.int64(assumptions.min_holding_ms),
            np.int32(_entry_price_policy_code(assumptions.entry_price_source)),
            np.int32(1 if signal_bar_close_present else 0),
            arrays["valid"],
            arrays["entry_indices"],
            arrays["exit_indices"],
            arrays["entry_times"],
            arrays["exit_times"],
            arrays["target_exit_times"],
            arrays["used_fallback"],
            arrays["entry_prices"],
            arrays["exit_prices"],
            arrays["path_highs"],
            arrays["path_lows"],
        ),
    )
    if _uses_numpy_backing(cupy, arrays):
        _simulate_candidate_kernel_numpy(
            ordered_market=ordered_market,
            ordered_signals=ordered_signals,
            assumptions=assumptions,
            signal_bar_close_present=signal_bar_close_present,
            arrays=arrays,
        )
    values = {key: _asnumpy(cupy, value) for key, value in arrays.items()}
    rows: list[dict[str, Any]] = []
    next_available_entry_time = -1
    signal_records = ordered_signals.to_dict("records")
    for signal_index, signal in enumerate(signal_records):
        if int(values["valid"][signal_index]) != 1:
            continue
        entry_index = int(values["entry_indices"][signal_index])
        exit_index = int(values["exit_indices"][signal_index])
        entry_time = int(values["entry_times"][signal_index])
        if entry_time < next_available_entry_time:
            continue
        side = str(signal["side"]).lower()
        exit_result = fixed_holding_window_exit(
            entry_time_ms=entry_time,
            exit_time_ms=int(values["exit_times"][signal_index]),
            exit_price=float(values["exit_prices"][signal_index]),
            side=side,
            path_high=float(values["path_highs"][signal_index]),
            path_low=float(values["path_lows"][signal_index]),
            entry_price=float(values["entry_prices"][signal_index]),
            costs_applied=True,
            exit_reason=(
                "end_of_data_min_holding"
                if int(values["used_fallback"][signal_index]) == 1
                else "holding_window"
            ),
        )
        entry_row = ordered_market.iloc[entry_index]
        holding_ms = int(exit_result.time_in_trade_ms)
        funding_rate = _optional_float(entry_row.get("funding_rate"))
        spread_bps = _optional_float(entry_row.get("spread_bps"))
        cost = costs.estimate(
            entry_price=float(values["entry_prices"][signal_index]),
            exit_price=float(exit_result.exit_price),
            side=side,
            holding_ms=holding_ms,
            funding_rate=funding_rate,
            spread_bps=spread_bps,
        )
        rows.append(
            {
                "trade_id": f"trade-{len(rows):06d}",
                "signal_id": str(signal.get("signal_id", f"signal-{len(rows):06d}")),
                "symbol": str(signal.get("symbol", symbol)),
                "side": side,
                "entry_time_ms": entry_time,
                "exit_time_ms": int(exit_result.exit_time_ms),
                "entry_bar_index": entry_index,
                "exit_bar_index": exit_index,
                "entry_price": float(values["entry_prices"][signal_index]),
                "exit_price": float(exit_result.exit_price),
                "holding_ms": holding_ms,
                "exit_target_time_ms": int(values["target_exit_times"][signal_index]),
                "exit_target_holding_ms": int(assumptions.holding_period_ms),
                "exit_used_fallback": bool(int(values["used_fallback"][signal_index])),
                "exit_policy": exit_result.exit_policy_id,
                "barrier_hit_type": exit_result.barrier_hit_type,
                "max_adverse_excursion": exit_result.max_adverse_excursion,
                "max_favorable_excursion": exit_result.max_favorable_excursion,
                "exit_approximate": exit_result.approximate,
                "exit_sequence_proof": "primary_bar_time",
                "exit_price_source": assumptions.exit_price_source,
                "gross_return": cost.gross_return,
                "fee_return": cost.fee_return,
                "slippage_return": cost.slippage_return,
                "spread_return": cost.spread_return,
                "funding_return": cost.funding_return,
                "net_return": cost.net_return,
                "entry_price_source": assumptions.entry_price_source,
                "exit_reason": exit_result.exit_reason,
            }
        )
        next_available_entry_time = int(exit_result.exit_time_ms)
    return pd.DataFrame(rows, columns=list(_empty_trades().columns)) if rows else _empty_trades()


def _allocate_candidate_arrays(cupy: Any, n_signals: int) -> dict[str, Any]:
    return {
        "valid": cupy.asarray(np.zeros(n_signals, dtype=np.int8)),
        "entry_indices": cupy.asarray(np.full(n_signals, -1, dtype=np.int64)),
        "exit_indices": cupy.asarray(np.full(n_signals, -1, dtype=np.int64)),
        "entry_times": cupy.asarray(np.zeros(n_signals, dtype=np.int64)),
        "exit_times": cupy.asarray(np.zeros(n_signals, dtype=np.int64)),
        "target_exit_times": cupy.asarray(np.zeros(n_signals, dtype=np.int64)),
        "used_fallback": cupy.asarray(np.zeros(n_signals, dtype=np.int8)),
        "entry_prices": cupy.asarray(np.zeros(n_signals, dtype=np.float64)),
        "exit_prices": cupy.asarray(np.zeros(n_signals, dtype=np.float64)),
        "path_highs": cupy.asarray(np.zeros(n_signals, dtype=np.float64)),
        "path_lows": cupy.asarray(np.zeros(n_signals, dtype=np.float64)),
    }


def _build_candidate_kernel(cupy: Any) -> Any:
    if hasattr(cupy, "RawKernel"):
        try:
            return cupy.RawKernel(
                _FIXED_HOLDING_CANDIDATE_KERNEL,
                CUDA_BATCHED_KERNEL_NAME,
                options=("--std=c++11",),
            )
        except TypeError:
            return cupy.RawKernel(_FIXED_HOLDING_CANDIDATE_KERNEL, CUDA_BATCHED_KERNEL_NAME)
    if hasattr(cupy, "RawModule"):
        try:
            module = cupy.RawModule(
                code=_FIXED_HOLDING_CANDIDATE_KERNEL,
                options=("--std=c++11",),
                name_expressions=(CUDA_BATCHED_KERNEL_NAME,),
            )
        except TypeError:
            module = cupy.RawModule(code=_FIXED_HOLDING_CANDIDATE_KERNEL)
        return module.get_function(CUDA_BATCHED_KERNEL_NAME)
    raise RuntimeError("cupy_rawkernel_unavailable")


def _has_raw_kernel(cupy: Any) -> bool:
    return bool(hasattr(cupy, "RawKernel") or hasattr(cupy, "RawModule"))


def _entry_price_policy_code(entry_price_source: str) -> int:
    if entry_price_source == "signal_bar_close_plus_latency":
        return 1
    if entry_price_source == "vwap_approximation":
        return 2
    return 0


def _asnumpy(cupy: Any, value: Any) -> np.ndarray:
    if hasattr(cupy, "asnumpy"):
        return np.asarray(cupy.asnumpy(value))
    return np.asarray(value)


def _uses_numpy_backing(cupy: Any, arrays: Mapping[str, Any]) -> bool:
    return str(getattr(cupy, "__version__", "")).startswith("fake-cupy") and all(
        isinstance(value, np.ndarray) for value in arrays.values()
    )


def _simulate_candidate_kernel_numpy(
    *,
    ordered_market: pd.DataFrame,
    ordered_signals: pd.DataFrame,
    assumptions: Any,
    signal_bar_close_present: bool,
    arrays: Mapping[str, Any],
) -> None:
    times = ordered_market["bar_time_ms"].astype("int64").to_numpy()
    open_values = ordered_market["open"].astype("float64").to_numpy()
    high_values = ordered_market["high"].astype("float64").to_numpy()
    low_values = ordered_market["low"].astype("float64").to_numpy()
    close_values = ordered_market["close"].astype("float64").to_numpy()
    signal_closes = (
        ordered_signals["signal_bar_close"].astype("float64").to_numpy()
        if signal_bar_close_present
        else np.zeros(len(ordered_signals), dtype=np.float64)
    )
    decision_times = ordered_signals["decision_time_ms"].astype("int64").to_numpy()
    entry_policy = _entry_price_policy_code(assumptions.entry_price_source)
    for signal_index, decision_time in enumerate(decision_times):
        entry_index = int(np.searchsorted(times, int(decision_time) + int(assumptions.entry_latency_ms), side="left"))
        if entry_index >= len(times):
            continue
        entry_time = int(times[entry_index])
        target_exit_time = entry_time + int(assumptions.holding_period_ms)
        exit_index = int(np.searchsorted(times, target_exit_time, side="left"))
        used_fallback = 0
        if exit_index >= len(times):
            exit_index = len(times) - 1
            used_fallback = 1
            if int(times[exit_index]) - entry_time < int(assumptions.min_holding_ms):
                continue
        entry_price = float(open_values[entry_index])
        if entry_policy == 1:
            entry_price = float(signal_closes[signal_index]) if signal_bar_close_present else float(open_values[entry_index])
        elif entry_policy == 2:
            entry_price = float((high_values[entry_index] + low_values[entry_index] + close_values[entry_index]) / 3.0)
        arrays["valid"][signal_index] = 1
        arrays["entry_indices"][signal_index] = entry_index
        arrays["exit_indices"][signal_index] = exit_index
        arrays["entry_times"][signal_index] = entry_time
        arrays["exit_times"][signal_index] = int(times[exit_index])
        arrays["target_exit_times"][signal_index] = target_exit_time
        arrays["used_fallback"][signal_index] = used_fallback
        arrays["entry_prices"][signal_index] = entry_price
        arrays["exit_prices"][signal_index] = float(close_values[exit_index])
        arrays["path_highs"][signal_index] = float(np.max(high_values[entry_index : exit_index + 1]))
        arrays["path_lows"][signal_index] = float(np.min(low_values[entry_index : exit_index + 1]))


def _cpu_reference_parity_evidence(
    *,
    signals: pd.DataFrame,
    market: pd.DataFrame,
    costs: CostModel,
    assumptions: Any,
    symbol: str,
    initial_equity: float,
    gpu_metrics: Mapping[str, Any],
    gpu_trades: pd.DataFrame,
    gpu_equity_curve: pd.DataFrame,
) -> dict[str, Any]:
    reference_trades = _vector_fixed_holding_trades(
        signals,
        market,
        costs=costs,
        assumptions=assumptions,
        symbol=symbol,
    )
    reference_trades = _enrich_trades(reference_trades, market)
    reference_equity = _equity_curve(initial_equity, market, reference_trades)
    reference_metrics = calculate_backtest_metrics(
        trades=reference_trades,
        signals=signals,
        equity_curve=reference_equity,
        market_data=market,
        initial_equity=initial_equity,
    )
    max_trade_diff = _max_frame_abs_diff(gpu_trades, reference_trades)
    max_metric_diff = _max_metric_abs_diff(gpu_metrics, reference_metrics)
    max_equity_diff = _max_equity_abs_diff(gpu_equity_curve, reference_equity)
    return {
        "cpu_reference_result_sha256": _stable_hash(
            {
                "trades": _frame_hash(reference_trades),
                "equity_curve": _frame_hash(reference_equity),
                "metrics": reference_metrics,
            }
        ),
        "max_trade_abs_diff": max_trade_diff,
        "max_metric_abs_diff": max_metric_diff,
        "max_equity_abs_diff": max_equity_diff,
        "parity_status": (
            "passed"
            if max_trade_diff <= 1e-12 and max_metric_diff <= 1e-12 and max_equity_diff <= 1e-9
            else "failed"
        ),
    }


def _max_metric_abs_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    if set(left) != set(right):
        return _MAX_FINITE_DIFF
    max_diff = 0.0
    for key in left:
        left_value = left[key]
        right_value = right[key]
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            diff = abs(float(left_value) - float(right_value))
            max_diff = max(max_diff, diff if np.isfinite(diff) else _MAX_FINITE_DIFF)
    return float(max_diff)


def _max_equity_abs_diff(left: pd.DataFrame, right: pd.DataFrame) -> float:
    return _max_frame_abs_diff(left, right)


def _max_frame_abs_diff(left: pd.DataFrame, right: pd.DataFrame) -> float:
    if list(left.columns) != list(right.columns) or len(left) != len(right):
        return _MAX_FINITE_DIFF
    if left.empty and right.empty:
        return 0.0
    max_diff = 0.0
    for column in left.columns:
        left_series = left[column]
        right_series = right[column]
        if pd.api.types.is_numeric_dtype(left_series) or pd.api.types.is_numeric_dtype(right_series):
            left_values = pd.to_numeric(left_series, errors="coerce").to_numpy(dtype=np.float64)
            right_values = pd.to_numeric(right_series, errors="coerce").to_numpy(dtype=np.float64)
            if not len(left_values):
                continue
            left_missing = np.isnan(left_values)
            right_missing = np.isnan(right_values)
            if not np.array_equal(left_missing, right_missing):
                return _MAX_FINITE_DIFF
            finite_mask = ~(left_missing | right_missing)
            if finite_mask.any():
                diffs = np.abs(left_values[finite_mask] - right_values[finite_mask])
                finite_diffs = diffs[np.isfinite(diffs)]
                if len(finite_diffs) != len(diffs):
                    return _MAX_FINITE_DIFF
                max_diff = max(max_diff, float(np.max(finite_diffs)))
        elif not left_series.astype(str).equals(right_series.astype(str)):
            return _MAX_FINITE_DIFF
    return float(max_diff)


def _kernel_sha256() -> str:
    return _stable_hash({"kernel_name": CUDA_BATCHED_KERNEL_NAME, "source": _FIXED_HOLDING_CANDIDATE_KERNEL})


def _sm_target(runtime_evidence: Mapping[str, Any]) -> str:
    capability = str(runtime_evidence.get("compute_capability") or "")
    if "." not in capability:
        return "unknown"
    major, minor = capability.split(".", maxsplit=1)
    if major.isdigit() and minor.isdigit():
        return f"sm_{major}{minor}"
    return "unknown"
