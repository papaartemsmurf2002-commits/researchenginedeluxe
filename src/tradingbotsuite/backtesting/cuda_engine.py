from __future__ import annotations

import time
import warnings
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from tradingbotsuite.backtesting.costs import CostModel
from tradingbotsuite.backtesting.engine import (
    BACKTEST_CACHE_POLICY,
    BACKTEST_ENGINE_VERSION,
    BACKTEST_MANIFEST_VERSION,
    BacktestEngine,
    BacktestResult,
    BacktestSpec,
    _cache_key_components,
    _cost_model_from_spec,
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
    _entry_price,
    _optional_float,
    vector_backtest_support_reason,
)


CUDA_BACKTEST_ENGINE_VERSION = "research-cuda-fixed-holding-backtest-engine-v1"
CUDA_EXECUTION_SCOPE = "cuda_fixed_holding_primary_bar"


class CudaFixedHoldingBacktestEngine:
    """Optional CuPy-backed fixed-holding research backtest path.

    The CUDA path intentionally mirrors `VectorBacktestEngine` support limits.
    Strategy signal generation and artifact writing remain CPU/pandas so parity
    can be audited against the reference engine.
    """

    def run(
        self,
        spec: BacktestSpec,
        *,
        market_data: pd.DataFrame | None = None,
        dataset: pd.DataFrame | None = None,
    ) -> BacktestResult:
        started = time.perf_counter()
        reason = cuda_backtest_support_reason(spec)
        if reason is not None:
            raise ValueError(reason)
        cp = _load_cupy()
        runtime_evidence = cuda_runtime_evidence()
        output_dir = spec.output_dir / spec.run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        reference_engine = BacktestEngine()
        source_frame = reference_engine._load_source_frame(spec, dataset=dataset, market_data=market_data)
        market = _market_frame(source_frame, symbol=spec.symbol)
        assumptions = _execution_assumptions(spec)
        reference_engine.execution_simulator._validate_assumptions(assumptions, None)
        signals, strategy_metadata = _signals_for_strategy(source_frame, spec)
        cost_model = _cost_model_from_spec(spec)
        trades = _cuda_fixed_holding_trades(
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
        config_resolved = spec.resolved_config()
        config_resolved["engine_version"] = CUDA_BACKTEST_ENGINE_VERSION
        source_hash = _source_hash(spec, source_frame)
        cache_key_components = _cache_key_components(
            dataset_sha256=source_hash,
            lower_timeframe_dataset_sha256=None,
            feature_manifest_sha256=spec.feature_manifest_sha256,
            config_resolved=config_resolved,
            assumptions=assumptions,
            cost_model=cost_model,
        )
        cache_key_components["engine_version"] = CUDA_BACKTEST_ENGINE_VERSION
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
            "engine_version": CUDA_BACKTEST_ENGINE_VERSION,
            "reference_engine_version": BACKTEST_ENGINE_VERSION,
            "vector_reference_engine_version": VECTOR_BACKTEST_ENGINE_VERSION,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "diagnostic_only": True,
            "symbol": spec.symbol,
            "strategy_id": spec.strategy_id,
            "strategy_metadata": strategy_metadata,
            "holding_window": spec.holding_window,
            "entry_price_source": spec.entry_price_source,
            "exit_policy_id": spec.exit_policy_id,
            "exit_price_source": spec.exit_price_source,
            "same_bar_entry_exit_allowed": False,
            "vector_execution_scope": "",
            "cuda_execution_scope": CUDA_EXECUTION_SCOPE,
            "cuda_kernel_scope": "cupy_searchsorted_batches_with_cpu_trade_loop",
            "cuda_parity_status": "parity_required_before_performance_claim",
            "gpu_execution_status": "cuda_fixed_holding_executed",
            "speed_claimed": False,
            "performance_claim_scope": "diagnostic_runtime_observation_only_until_benchmark_and_dataset_parity_evidence",
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


def cuda_backtest_support_reason(spec: BacktestSpec, *, check_runtime: bool = True) -> str | None:
    vector_reason = vector_backtest_support_reason(spec)
    if vector_reason is not None:
        return f"cuda_engine_scope_unsupported:{vector_reason}"
    if not check_runtime:
        return None
    evidence = cuda_runtime_evidence()
    if evidence["available"]:
        return None
    return str(evidence["unavailable_reason"])


def cuda_runtime_evidence() -> dict[str, Any]:
    try:
        cp = _load_cupy()
    except Exception as exc:
        return _unavailable_evidence("cuda_engine_cupy_unavailable", exc)
    try:
        device_count = int(cp.cuda.runtime.getDeviceCount())
        if device_count <= 0:
            return {
                **_base_runtime_evidence(cp),
                "available": False,
                "unavailable_reason": "cuda_engine_no_device",
                "device_count": 0,
            }
        device = cp.cuda.Device(0)
        with device:
            props = cp.cuda.runtime.getDeviceProperties(0)
            free_bytes, total_bytes = device.mem_info
        name = props.get("name", "")
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="replace")
        device_evidence = {
            "device_count": device_count,
            "device_index": 0,
            "gpu_name": str(name),
            "compute_capability": f"{int(props.get('major', 0))}.{int(props.get('minor', 0))}",
            "driver_version": int(cp.cuda.runtime.driverGetVersion()),
            "runtime_version": int(cp.cuda.runtime.runtimeGetVersion()),
            "memory_free_bytes": int(free_bytes),
            "memory_total_bytes": int(total_bytes),
        }
    except Exception as exc:
        return _unavailable_evidence("cuda_engine_runtime_unavailable", exc, cupy=_safe_cupy_module())
    try:
        smoke_evidence = _cuda_runtime_smoke(cp)
    except Exception as exc:
        return {
            **_unavailable_evidence("cuda_engine_runtime_smoke_failed", exc, cupy=cp),
            **device_evidence,
        }
    return {
        **_base_runtime_evidence(cp),
        "available": True,
        "unavailable_reason": "",
        **device_evidence,
        **smoke_evidence,
    }


def _cuda_fixed_holding_trades(
    signals: pd.DataFrame,
    market: pd.DataFrame,
    *,
    costs: CostModel,
    assumptions: Any,
    symbol: str,
    cupy: Any,
) -> pd.DataFrame:
    if signals.empty:
        return _empty_trades()
    ordered_market = market.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)
    ordered_signals = signals.sort_values("decision_time_ms", kind="mergesort").reset_index(drop=True)
    times_np = ordered_market["bar_time_ms"].astype("int64").to_numpy()
    times_gpu = cupy.asarray(times_np)
    decision_times_gpu = cupy.asarray(ordered_signals["decision_time_ms"].astype("int64").to_numpy())
    entry_indices = cupy.asnumpy(
        cupy.searchsorted(
            times_gpu,
            decision_times_gpu + int(assumptions.entry_latency_ms),
            side="left",
        )
    ).astype(np.int64)
    open_gpu = cupy.asarray(ordered_market["open"].astype("float64").to_numpy())
    high_gpu = cupy.asarray(ordered_market["high"].astype("float64").to_numpy())
    low_gpu = cupy.asarray(ordered_market["low"].astype("float64").to_numpy())
    close_gpu = cupy.asarray(ordered_market["close"].astype("float64").to_numpy())
    valid_entry_mask = entry_indices < len(ordered_market)
    target_exit_times_np = np.zeros(len(entry_indices), dtype=np.int64)
    if valid_entry_mask.any():
        target_exit_times_np[valid_entry_mask] = times_np[entry_indices[valid_entry_mask]] + int(assumptions.holding_period_ms)
    exit_indices = cupy.asnumpy(
        cupy.searchsorted(
            times_gpu,
            cupy.asarray(target_exit_times_np),
            side="left",
        )
    ).astype(np.int64)
    rows: list[dict[str, Any]] = []
    next_available_entry_time = -1
    signal_records = ordered_signals.to_dict("records")
    for signal_index, signal in enumerate(signal_records):
        target_entry_time = int(signal["decision_time_ms"]) + int(assumptions.entry_latency_ms)
        entry_index = int(entry_indices[signal_index])
        if entry_index >= len(ordered_market):
            continue
        entry_row = ordered_market.iloc[entry_index]
        entry_time = int(times_np[entry_index])
        if entry_time < next_available_entry_time:
            continue
        side = str(signal["side"]).lower()
        entry_price = _cuda_entry_price(signal, entry_index, entry_row, assumptions, open_gpu, high_gpu, low_gpu, close_gpu)
        target_exit_time = entry_time + int(assumptions.holding_period_ms)
        exit_index = int(exit_indices[signal_index])
        exit_reason = "holding_window"
        used_fallback = False
        if exit_index >= len(ordered_market):
            exit_index = len(ordered_market) - 1
            exit_time = int(times_np[exit_index])
            if exit_time - entry_time < int(assumptions.min_holding_ms):
                continue
            exit_reason = "end_of_data_min_holding"
            used_fallback = True
        exit_time = int(times_np[exit_index])
        exit_price = float(close_gpu[exit_index].item())
        path_high = float(cupy.max(high_gpu[entry_index : exit_index + 1]).item())
        path_low = float(cupy.min(low_gpu[entry_index : exit_index + 1]).item())
        exit_result = fixed_holding_window_exit(
            entry_time_ms=entry_time,
            exit_time_ms=exit_time,
            exit_price=exit_price,
            side=side,
            path_high=path_high,
            path_low=path_low,
            entry_price=entry_price,
            costs_applied=True,
            exit_reason=exit_reason,
        )
        holding_ms = int(exit_result.time_in_trade_ms)
        funding_rate = _optional_float(entry_row.get("funding_rate"))
        spread_bps = _optional_float(entry_row.get("spread_bps"))
        cost = costs.estimate(
            entry_price=entry_price,
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
                "entry_price": float(entry_price),
                "exit_price": float(exit_result.exit_price),
                "holding_ms": holding_ms,
                "entry_target_time_ms": target_entry_time,
                "entry_primary_bar_time_ms": entry_time,
                "entry_sequence_proof": "primary_bar_time",
                "exit_target_time_ms": target_exit_time,
                "exit_target_holding_ms": int(assumptions.holding_period_ms),
                "exit_used_fallback": bool(used_fallback),
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


def _cuda_entry_price(
    signal: Mapping[str, Any],
    entry_index: int,
    entry_row: pd.Series,
    assumptions: Any,
    open_gpu: Any,
    high_gpu: Any,
    low_gpu: Any,
    close_gpu: Any,
) -> float:
    if assumptions.entry_price_source == "signal_bar_close_plus_latency":
        return _entry_price(dict(signal), entry_row, assumptions)
    if assumptions.entry_price_source == "vwap_approximation":
        return float(((high_gpu[entry_index] + low_gpu[entry_index] + close_gpu[entry_index]) / 3.0).item())
    return float(open_gpu[entry_index].item())


def _load_cupy() -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="CUDA path could not be detected.*",
            category=UserWarning,
        )
        import cupy as cp  # type: ignore[import-not-found]

    return cp


def _cuda_runtime_smoke(cupy: Any) -> dict[str, Any]:
    values = cupy.asarray(np.asarray([1.0, 3.0, 5.0], dtype=np.float64))
    probes = cupy.asarray(np.asarray([0.0, 4.0, 6.0], dtype=np.float64))
    indices = cupy.asnumpy(cupy.searchsorted(values, probes, side="left")).astype(np.int64)
    reduced = float((cupy.max(values) + cupy.min(values)).item())
    first_index = int(indices[0].item())
    if list(indices) != [0, 2, 3] or reduced != 6.0 or first_index != 0:
        raise RuntimeError("cuda runtime smoke returned unexpected primitive results")
    return {
        "runtime_smoke_test": "passed",
        "runtime_smoke_scope": "asarray_searchsorted_reduction_asnumpy_item",
    }


def _safe_cupy_module() -> Any | None:
    try:
        return _load_cupy()
    except Exception:
        return None


def _base_runtime_evidence(cupy: Any | None) -> dict[str, Any]:
    return {
        "runtime_evidence_version": "cuda-runtime-evidence-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "cupy_version": str(getattr(cupy, "__version__", "")) if cupy is not None else "",
    }


def _unavailable_evidence(reason: str, exc: Exception, *, cupy: Any | None = None) -> dict[str, Any]:
    return {
        **_base_runtime_evidence(cupy),
        "available": False,
        "unavailable_reason": reason,
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "device_count": 0,
        "device_index": None,
        "gpu_name": "",
        "compute_capability": "",
        "driver_version": None,
        "runtime_version": None,
        "memory_free_bytes": None,
        "memory_total_bytes": None,
    }


def __getattr__(name: str) -> Any:
    if name in {
        "CUDA_BATCHED_BACKEND_NAME",
        "CUDA_BATCHED_BACKTEST_ENGINE_VERSION",
        "CUDA_BATCHED_EXECUTION_SCOPE",
        "CudaBatchedFixedHoldingBacktestEngine",
        "cuda_batched_backtest_support_reason",
        "cuda_batched_fixed_holding_support_reason",
        "cuda_batched_fixed_holding_backtest_support_reason",
    }:
        from tradingbotsuite.backtesting import cuda_batched_engine

        aliases = {
            "cuda_batched_fixed_holding_support_reason": "cuda_batched_backtest_support_reason",
            "cuda_batched_fixed_holding_backtest_support_reason": "cuda_batched_backtest_support_reason",
        }
        return getattr(cuda_batched_engine, aliases.get(name, name))
    raise AttributeError(name)
