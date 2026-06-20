from __future__ import annotations

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.backtesting import (
    CUDA_BACKTEST_ENGINE_VERSION,
    CUDA_BATCHED_BACKTEST_ENGINE_VERSION,
    VECTOR_BACKTEST_ENGINE_VERSION,
    BacktestEngine,
    CudaBatchedFixedHoldingBacktestEngine,
    CudaFixedHoldingBacktestEngine,
    VectorBacktestEngine,
    cuda_batched_backtest_support_reason,
    cuda_backtest_support_reason,
    cuda_runtime_evidence,
    research_cost_stress_scenarios,
)
from tradingbotsuite.backtesting.engine import (
    BACKTEST_CACHE_POLICY,
    BACKTEST_ENGINE_VERSION,
    BACKTEST_MANIFEST_VERSION,
    BacktestResult,
    BacktestSpec,
)
from tradingbotsuite.backtesting.vector_engine import vector_backtest_support_reason
from tradingbotsuite.backtesting.splits import (
    SPLIT_ENGINE_VERSION,
    WalkForwardSplit,
    build_anchored_walk_forward_splits,
    build_purged_walk_forward_splits,
    build_rolling_walk_forward_splits,
    build_shifted_walk_forward_splits,
    frame_for_split,
    infer_label_spec,
    month_holdout_splits,
    regime_holdout_splits,
    stress_period_holdout_splits,
)
from tradingbotsuite.config import AppConfig
from tradingbotsuite.data.historical_fixture_pack import (
    HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION,
    assert_valid_historical_fixture_pack_manifest,
    resolve_fixture_pack_cycle_dataset_path,
    validate_public_archive_fixture_readiness,
)
from tradingbotsuite.features.builders import (
    DEFAULT_INTERVAL_MS,
    FEATURE_BUILDER_VERSION,
    FEATURE_MANIFEST_TESTS,
    canonicalize_bar_frame,
    materialize_fixture_family_context,
    materialize_registered_feature_set,
)
from tradingbotsuite.features.cache import (
    FeatureCacheIdentity,
    load_feature_cache_artifact,
    write_feature_cache_artifact,
)
from tradingbotsuite.features.registry import manifest_from_preset
from tradingbotsuite.optimization import CandidateConfig, CandidateResult, SearchSpace, rank_by_stability
from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_artifacts import (
    evaluate_research_candidate_gate,
    evaluate_research_candidate_gate_from_row,
    source_capability_gate_reasons,
    write_research_candidate_pack,
)
from tradingbotsuite.research_cycle.spec import (
    HistoricalResearchCycleSpec,
    MaterializedPredictionOverlaySpec,
    SUPPORTED_RESEARCH_EXIT_POLICIES,
)
from tradingbotsuite.research_cycle.performance import build_candidate_selection_performance_plan
from tradingbotsuite.strategies import (
    defaults_for_holding_window,
    get_strategy_plugin,
    metadata_for_strategy,
    signal_density_controls,
    strategy_parameter_manifest,
)
from tradingbotsuite.strategies.hmm_knn_local_analog_filter import REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS
from tradingbotsuite.strategies.parameters import (
    allowed_parameter_names,
    allowed_parameter_values,
    search_parameter_space_for_holding_window,
    strategy_metadata_sha256,
)


RESEARCH_CYCLE_RUNNER_VERSION = "historical-research-cycle-runner-v1"
RESEARCH_CYCLE_MANIFEST_VERSION = "historical-research-cycle-manifest-v1"
TRIAL_BUDGET_REPORT_VERSION = "trial-budget-report-v1"
OVERFIT_ADJUSTMENT_REPORT_VERSION = "overfit-adjustment-report-v1"
SUPPORTED_SEARCH_METHODS = {"grid", "random", "latin_hypercube", "coarse_lhs", "sobol"}
SEARCH_METHOD_ALIASES = {"adaptive_grid": "grid"}
NO_TRADE_BASELINE_STRATEGY_ID = "baseline_no_trade"
DEFAULT_METADATA_SEARCH_SAMPLE_CAP = 4
TRANSPARENT_BASELINE_STRATEGY_IDS = (
    "trend_following_v1",
    "baseline_trend",
    "volatility_breakout_v1",
    "range_reversion_v1",
    "funding_basis_v1",
)
CUDA_BACKTEST_BACKENDS = {"cuda_fixed_holding", "cuda_batched_fixed_holding"}
R97_CUDA_EXECUTION_PROFILES = {"cuda_exact_batched", "hybrid_tensorcore_screening"}
CPU_VECTOR_EXECUTION_PROFILE_REASONS = {
    "fastest_exact": "gpu_execution_profile_fastest_exact_vector_selected",
    "conservative": "gpu_execution_profile_conservative",
}
SPARSE_EVENT_FILTER_STRATEGY_ID = "sparse_event_filter_v1"
SIDE_VETO_ALLOWED_SIDES = {"long", "short"}
SPARSE_FLOW_ABLATION_PARAMETER_KEYS = frozenset(
    {
        "flow_confirmation",
        "flow_abs_threshold",
        "flow_count_z_min",
    }
)
FAIL_CLOSED_CONTEXT_EXIT_POLICIES = {
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
}


@dataclass(frozen=True, slots=True)
class HistoricalResearchCycleResult:
    output_dir: Path
    manifest_path: Path
    candidate_rankings_path: Path
    backtest_index_path: Path
    rejection_report_path: Path


@dataclass(frozen=True, slots=True)
class FeatureBuildResult:
    manifest: dict[str, Any]
    frames_by_feature_set: dict[str, pd.DataFrame]


@dataclass(frozen=True, slots=True)
class CandidateScopedOverlayContext:
    feature_build_manifest: dict[str, Any]
    frames_by_candidate_id: dict[str, pd.DataFrame]
    records_by_candidate_id: dict[str, dict[str, Any]]
    evidence_by_candidate_id: dict[str, dict[str, Any]]


@dataclass(frozen=True, slots=True)
class CycleBacktestExecution:
    result: BacktestResult
    manifest: dict[str, Any]
    backend_evidence: dict[str, Any]


def _run_cycle_backtest(
    *,
    cycle_spec: HistoricalResearchCycleSpec,
    reference_engine: BacktestEngine,
    vector_engine: VectorBacktestEngine,
    backtest_spec: BacktestSpec,
    dataset: pd.DataFrame,
    cuda_engine: CudaFixedHoldingBacktestEngine | None = None,
    cuda_batched_engine: CudaBatchedFixedHoldingBacktestEngine | None = None,
    allow_cuda: bool = True,
) -> CycleBacktestExecution:
    cuda_engine = cuda_engine or CudaFixedHoldingBacktestEngine()
    cuda_batched_engine = cuda_batched_engine or CudaBatchedFixedHoldingBacktestEngine()
    requested = cycle_spec.backtest_backend
    vector_unsupported_reason = vector_backtest_support_reason(backtest_spec)
    gpu_requested = str(cycle_spec.compute.gpu_acceleration) != "disabled"
    gpu_required = bool(cycle_spec.compute.gpu_required)
    r97_cuda_requested = _r97_batched_cuda_requested(cycle_spec)
    auto_cuda_requested = requested == "auto" and gpu_requested and r97_cuda_requested
    resolved_cuda_backend = "cuda_batched_fixed_holding" if r97_cuda_requested else "cuda_fixed_holding"
    if requested == "cuda_batched_fixed_holding" and not gpu_requested:
        raise ValueError("backtest_backend_cuda_batched_fixed_holding_unavailable:gpu_acceleration_disabled")
    if requested == "cuda_batched_fixed_holding" and not _r97_batched_profile_enabled(cycle_spec):
        raise ValueError("backtest_backend_cuda_batched_fixed_holding_unavailable:gpu_execution_profile_not_enabled")
    if gpu_required and requested not in {"auto", *CUDA_BACKTEST_BACKENDS}:
        raise ValueError("backtest_backend_cuda_required_unavailable:cuda_required_backend_not_selectable")
    if gpu_required and requested == "auto" and not gpu_requested:
        raise ValueError("backtest_backend_cuda_required_unavailable:gpu_acceleration_disabled")
    if gpu_required and requested == "auto" and not _r97_batched_profile_enabled(cycle_spec):
        raise ValueError("backtest_backend_cuda_batched_fixed_holding_required_unavailable:gpu_execution_profile_not_enabled")
    cuda_unsupported_reason: str | None = None
    if allow_cuda and (requested in CUDA_BACKTEST_BACKENDS or auto_cuda_requested):
        support_check = (
            cuda_batched_backtest_support_reason
            if resolved_cuda_backend == "cuda_batched_fixed_holding"
            else cuda_backtest_support_reason
        )
        cuda_unsupported_reason = support_check(backtest_spec)
    fallback_reason = ""
    if requested == "reference":
        result = reference_engine.run(backtest_spec, dataset=dataset)
    elif requested == "vector_fixed_holding":
        if vector_unsupported_reason is not None:
            raise ValueError(f"backtest_backend_vector_fixed_holding_unsupported:{vector_unsupported_reason}")
        result = vector_engine.run(backtest_spec, dataset=dataset)
    elif requested == "cuda_fixed_holding":
        if not allow_cuda:
            fallback_reason = "cuda_fixed_holding_validation_reference_required"
            result = reference_engine.run(backtest_spec, dataset=dataset)
        elif cuda_unsupported_reason is not None:
            raise ValueError(f"backtest_backend_cuda_fixed_holding_unsupported:{cuda_unsupported_reason}")
        else:
            result = cuda_engine.run(backtest_spec, dataset=dataset)
    elif requested == "cuda_batched_fixed_holding":
        if not allow_cuda:
            fallback_reason = "cuda_batched_fixed_holding_validation_reference_required"
            result = reference_engine.run(backtest_spec, dataset=dataset)
        elif cuda_unsupported_reason is not None:
            raise ValueError(f"backtest_backend_cuda_batched_fixed_holding_unsupported:{cuda_unsupported_reason}")
        else:
            result = cuda_batched_engine.run(backtest_spec, dataset=dataset)
    elif requested == "auto":
        if not allow_cuda:
            fallback_reason = (
                f"{resolved_cuda_backend}_validation_reference_required"
                if auto_cuda_requested
                else "auto_validation_reference_required"
            )
            result = reference_engine.run(backtest_spec, dataset=dataset)
        elif auto_cuda_requested and cuda_unsupported_reason is None:
            result = cuda_batched_engine.run(backtest_spec, dataset=dataset)
        elif auto_cuda_requested and gpu_required:
            raise ValueError(f"backtest_backend_{resolved_cuda_backend}_required_unavailable:{cuda_unsupported_reason}")
        elif vector_unsupported_reason is None:
            fallback_reason = (
                ""
                if not gpu_requested
                else str(cuda_unsupported_reason or _cpu_vector_execution_profile_reason(cycle_spec))
            )
            result = vector_engine.run(backtest_spec, dataset=dataset)
        else:
            fallback_reason = _join_backend_reasons(cuda_unsupported_reason, vector_unsupported_reason)
            result = reference_engine.run(backtest_spec, dataset=dataset)
    else:
        raise ValueError(f"unsupported backtest_backend: {requested}")
    manifest = _read_json(result.manifest_path)
    return CycleBacktestExecution(
        result=result,
        manifest=manifest,
        backend_evidence=_backtest_backend_evidence(
            requested=requested,
            fallback_reason=fallback_reason,
            manifest=manifest,
            cuda_backend_used=resolved_cuda_backend,
            compute_policy=cycle_spec.compute.to_payload(include_r97_defaults=True),
        ),
    )


def _backtest_backend_evidence(
    *,
    requested: str,
    fallback_reason: str,
    manifest: Mapping[str, Any],
    cuda_backend_used: str = "cuda_fixed_holding",
    compute_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    engine_version = str(manifest.get("engine_version") or "")
    vector_scope = str(manifest.get("vector_execution_scope") or "")
    cuda_scope = str(manifest.get("cuda_execution_scope") or "")
    if engine_version == CUDA_BATCHED_BACKTEST_ENGINE_VERSION:
        used = "cuda_batched_fixed_holding"
    elif engine_version == CUDA_BACKTEST_ENGINE_VERSION or cuda_scope:
        used = cuda_backend_used if cuda_backend_used in CUDA_BACKTEST_BACKENDS else "cuda_fixed_holding"
    elif engine_version == VECTOR_BACKTEST_ENGINE_VERSION or vector_scope:
        used = "vector_fixed_holding"
    else:
        used = "reference"
    runtime_evidence = dict(manifest.get("gpu_runtime_evidence") or {})
    compute = dict(compute_policy or {})
    return {
        "backtest_backend_requested": requested,
        "backtest_backend_used": used,
        "backtest_backend_fallback_reason": str(fallback_reason or ""),
        "backtest_backend_rejection_reason": "",
        "backtest_engine_version": engine_version,
        "reference_engine_version": str(manifest.get("reference_engine_version") or (engine_version if used == "reference" else "")),
        "vector_execution_scope": vector_scope,
        "cuda_execution_scope": cuda_scope,
        "cuda_parity_status": str(manifest.get("cuda_parity_status") or ""),
        "backtest_parity_status": str(manifest.get("parity_status") or ""),
        "backtest_max_metric_abs_diff": manifest.get("max_metric_abs_diff"),
        "backtest_max_equity_abs_diff": manifest.get("max_equity_abs_diff"),
        "backtest_max_trade_abs_diff": manifest.get("max_trade_diff"),
        "gpu_execution_status": str(manifest.get("gpu_execution_status") or ""),
        "gpu_execution_profile": str(compute.get("gpu_execution_profile") or ""),
        "tensor_core_policy": str(compute.get("tensor_core_policy") or ""),
        "gpu_batch_candidates": compute.get("gpu_batch_candidates"),
        "gpu_memory_fraction_limit": compute.get("gpu_memory_fraction_limit"),
        "gpu_validation_sample_rate": compute.get("gpu_validation_sample_rate"),
        "gpu_device_name": str(runtime_evidence.get("gpu_name") or ""),
        "gpu_compute_capability": str(runtime_evidence.get("compute_capability") or ""),
        "gpu_driver_version": runtime_evidence.get("driver_version"),
        "gpu_runtime_version": runtime_evidence.get("runtime_version"),
        "gpu_memory_total_bytes": runtime_evidence.get("memory_total_bytes"),
        "cupy_version": str(runtime_evidence.get("cupy_version") or ""),
        "backtest_cache_key_components_engine_version": str(
            (manifest.get("cache_key_components") or {}).get("engine_version") or ""
        ),
    }


def _aggregate_backtest_worker_count(spec: HistoricalResearchCycleSpec) -> int:
    requested = str(spec.backtest_backend)
    gpu_requested = str(spec.compute.gpu_acceleration) != "disabled"
    cuda_requested = requested in CUDA_BACKTEST_BACKENDS or (
        requested == "auto" and gpu_requested and _r97_batched_cuda_requested(spec)
    )
    if gpu_requested and cuda_requested:
        runtime = cuda_runtime_evidence()
        if bool(runtime.get("available", False)) and _cycle_has_cuda_screening_scope(spec):
            return 1
    return max(1, int(spec.compute.cpu_threads))


def _join_backend_reasons(*reasons: str | None) -> str:
    values = [str(reason) for reason in reasons if str(reason or "")]
    return ";".join(dict.fromkeys(values))


def _cpu_vector_execution_profile_reason(spec: HistoricalResearchCycleSpec) -> str:
    profile = str(spec.compute.gpu_execution_profile)
    return CPU_VECTOR_EXECUTION_PROFILE_REASONS.get(profile, f"gpu_execution_profile_{profile}_cpu_vector_selected")


def _cycle_has_cuda_screening_scope(spec: HistoricalResearchCycleSpec) -> bool:
    if spec.optimizer.search_spaces:
        exit_policy_ids = [
            str(space.get("exit_policy_id") or "fixed_holding_window")
            for space in spec.optimizer.search_spaces
        ]
    else:
        exit_policy_ids = [
            str(policy.get("exit_policy_id") or "fixed_holding_window")
            for policy in spec.exits.exit_policies
        ]
    return any(_is_cuda_fixed_holding_policy(exit_policy_id) for exit_policy_id in exit_policy_ids)


def _is_cuda_fixed_holding_policy(exit_policy_id: str) -> bool:
    value = str(exit_policy_id).lower()
    return value == "fixed_holding_window" or value.endswith("_time_exit")


def _r97_batched_profile_enabled(spec: HistoricalResearchCycleSpec) -> bool:
    return str(spec.compute.gpu_execution_profile) in R97_CUDA_EXECUTION_PROFILES


def _r97_batched_cuda_requested(spec: HistoricalResearchCycleSpec) -> bool:
    requested = str(spec.backtest_backend)
    gpu_requested = str(spec.compute.gpu_acceleration) != "disabled"
    if requested == "cuda_batched_fixed_holding":
        return True
    return requested == "auto" and gpu_requested and _r97_batched_profile_enabled(spec)


def _validate_compute_backend_request(spec: HistoricalResearchCycleSpec) -> None:
    requested = str(spec.backtest_backend)
    gpu_requested = str(spec.compute.gpu_acceleration) != "disabled"
    gpu_required = bool(spec.compute.gpu_required)
    if requested == "cuda_batched_fixed_holding" and not gpu_requested:
        raise ValueError("backtest_backend_cuda_batched_fixed_holding_unavailable:gpu_acceleration_disabled")
    if requested == "cuda_batched_fixed_holding" and not _r97_batched_profile_enabled(spec):
        raise ValueError("backtest_backend_cuda_batched_fixed_holding_unavailable:gpu_execution_profile_not_enabled")
    if requested == "auto" and gpu_required and not _r97_batched_profile_enabled(spec):
        raise ValueError("backtest_backend_cuda_batched_fixed_holding_required_unavailable:gpu_execution_profile_not_enabled")
    if gpu_required and requested not in {"auto", *CUDA_BACKTEST_BACKENDS}:
        raise ValueError("backtest_backend_cuda_required_unavailable:cuda_required_backend_not_selectable")
    if gpu_required and not gpu_requested:
        raise ValueError("backtest_backend_cuda_required_unavailable:gpu_acceleration_disabled")
    if gpu_required and not _cycle_has_cuda_screening_scope(spec):
        backend = "cuda_batched_fixed_holding" if _r97_batched_cuda_requested(spec) else "cuda_fixed_holding"
        raise ValueError(f"backtest_backend_{backend}_required_unavailable:cuda_fixed_holding_scope_unavailable")
    if gpu_required and (requested in CUDA_BACKTEST_BACKENDS or (requested == "auto" and gpu_requested)):
        runtime = cuda_runtime_evidence()
        if not bool(runtime.get("available", False)):
            backend = "cuda_batched_fixed_holding" if _r97_batched_cuda_requested(spec) else "cuda_fixed_holding"
            raise ValueError(
                f"backtest_backend_{backend}_required_unavailable:"
                f"{runtime.get('unavailable_reason') or 'cuda_runtime_unavailable'}"
            )


def _aggregate_candidate_evaluations(
    *,
    spec: HistoricalResearchCycleSpec,
    candidates: list[dict[str, Any]],
    feature_frames: Mapping[str, pd.DataFrame],
    feature_build_manifest: Mapping[str, Any],
    candidate_overlay_context: CandidateScopedOverlayContext | None,
    data_source: Mapping[str, Any],
    backtest_root: Path,
    workers: int,
) -> list[dict[str, Any]]:
    def run_one(candidate: dict[str, Any]) -> dict[str, Any]:
        candidate = _candidate_with_materialized_overlay_evidence(
            candidate,
            feature_build_manifest,
            candidate_overlay_context,
        )
        candidate_frame = _candidate_feature_frame(feature_frames, candidate, candidate_overlay_context)
        candidate_feature_record = _candidate_feature_record(feature_build_manifest, candidate, candidate_overlay_context)
        candidate_dataset_hash = _validated_feature_frame_hash(candidate_frame, candidate_feature_record, candidate)
        candidate_feature_manifest_sha256 = str(candidate_feature_record["feature_manifest_sha256"])
        lower_timeframe_dataset_path = _candidate_lower_timeframe_dataset_path(candidate, data_source)
        backtest_spec = BacktestSpec(
            run_id=_candidate_backtest_run_id(candidate, "agg"),
            symbol=spec.symbol,
            output_dir=backtest_root,
            strategy_id=str(candidate["strategy_id"]),
            holding_window=str(candidate["holding_window"]),
            feature_set_id=str(candidate["feature_set_id"]),
            feature_manifest_sha256=candidate_feature_manifest_sha256,
            dataset_sha256=candidate_dataset_hash,
            exit_policy_id=str(candidate.get("exit_policy_id", "fixed_holding_window")),
            target_return=_candidate_target_return(candidate),
            stop_return=_candidate_stop_return(candidate),
            exit_policy_params=dict(candidate.get("exit_policy_params") or {}),
            exit_price_source=_candidate_exit_price_source(candidate),
            lower_timeframe_dataset_path=lower_timeframe_dataset_path,
            strategy_config=_strategy_config(candidate),
        )
        execution = _run_cycle_backtest_fail_closed(
            candidate=candidate,
            cycle_spec=spec,
            reference_engine=BacktestEngine(),
            vector_engine=VectorBacktestEngine(),
            cuda_engine=CudaFixedHoldingBacktestEngine(),
            backtest_spec=backtest_spec,
            dataset=candidate_frame,
        )
        return {
            "candidate": candidate,
            "result": execution.result,
            "metrics": _read_json(execution.result.metrics_path),
            "manifest": execution.manifest,
            "backend_evidence": execution.backend_evidence,
        }

    if max(1, int(workers)) == 1 or len(candidates) <= 1:
        return [run_one(candidate) for candidate in candidates]
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        return list(pool.map(run_one, candidates))


def _run_cycle_backtest_fail_closed(
    *,
    candidate: Mapping[str, Any],
    cycle_spec: HistoricalResearchCycleSpec,
    reference_engine: BacktestEngine,
    vector_engine: VectorBacktestEngine,
    backtest_spec: BacktestSpec,
    dataset: pd.DataFrame,
    cuda_engine: CudaFixedHoldingBacktestEngine | None = None,
    cuda_batched_engine: CudaBatchedFixedHoldingBacktestEngine | None = None,
    allow_cuda: bool = True,
) -> CycleBacktestExecution:
    try:
        return _run_cycle_backtest(
            cycle_spec=cycle_spec,
            reference_engine=reference_engine,
            vector_engine=vector_engine,
            backtest_spec=backtest_spec,
            dataset=dataset,
            cuda_engine=cuda_engine,
            cuda_batched_engine=cuda_batched_engine,
            allow_cuda=allow_cuda,
        )
    except ValueError as exc:
        blocker = _context_exit_blocker_reason(candidate, exc)
        if blocker is None:
            raise
        return _blocked_cycle_backtest_execution(
            cycle_spec=cycle_spec,
            backtest_spec=backtest_spec,
            dataset=dataset,
            blocker_reason=blocker,
        )


def _context_exit_blocker_reason(candidate: Mapping[str, Any], exc: ValueError) -> str | None:
    policy = str(candidate.get("exit_policy_id") or "").lower()
    if policy not in FAIL_CLOSED_CONTEXT_EXIT_POLICIES:
        return None
    message = str(exc)
    context_markers = (
        "requires columns:",
        "requires cal_time_to_next_funding_h",
        "requires realized_volatility or atr_percentile",
        "requires finite volatility context",
        "requires spread_bps",
    )
    if not any(marker in message for marker in context_markers):
        return None
    return "exit_policy_context_unavailable:" + policy + ":" + _blocker_message(message)


def _blocked_cycle_backtest_execution(
    *,
    cycle_spec: HistoricalResearchCycleSpec,
    backtest_spec: BacktestSpec,
    dataset: pd.DataFrame,
    blocker_reason: str,
) -> CycleBacktestExecution:
    run_dir = backtest_spec.output_dir / backtest_spec.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = run_dir / "metrics.json"
    trades_path = run_dir / "trades.parquet"
    signals_path = run_dir / "signals.parquet"
    equity_curve_path = run_dir / "equity_curve.parquet"
    config_path = run_dir / "config_resolved.json"
    manifest_path = run_dir / "backtest_manifest.json"

    metrics = _blocked_backtest_metrics(blocker_reason=blocker_reason, dataset=dataset)
    _write_json(metrics_path, metrics)
    _blocked_trades_frame().to_parquet(trades_path, index=False)
    _blocked_signals_frame().to_parquet(signals_path, index=False)
    _blocked_equity_curve(dataset).to_parquet(equity_curve_path, index=False)
    _write_json(config_path, {**backtest_spec.resolved_config(), "blocked": True, "blocker_reason": blocker_reason})

    cache_key_components = {
        "engine_version": BACKTEST_ENGINE_VERSION,
        "cache_policy": BACKTEST_CACHE_POLICY,
        "dataset_sha256": backtest_spec.dataset_sha256,
        "feature_manifest_sha256": backtest_spec.feature_manifest_sha256,
        "config_sha256": backtest_spec.config_sha256(),
        "blocked_reason": blocker_reason,
    }
    result_sha256 = _stable_hash(
        {
            "blocked_reason": blocker_reason,
            "metrics": metrics,
            "trades_sha256": _file_sha256(trades_path),
            "signals_sha256": _file_sha256(signals_path),
            "equity_curve_sha256": _file_sha256(equity_curve_path),
            "config_sha256": _file_sha256(config_path),
        }
    )
    manifest: dict[str, Any] = {
        "backtest_manifest_version": BACKTEST_MANIFEST_VERSION,
        "engine_version": BACKTEST_ENGINE_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "run_id": backtest_spec.run_id,
        "symbol": backtest_spec.symbol,
        "strategy_id": backtest_spec.strategy_id,
        "holding_window": backtest_spec.holding_window,
        "feature_set_id": backtest_spec.feature_set_id,
        "dataset_sha256": backtest_spec.dataset_sha256,
        "feature_manifest_sha256": backtest_spec.feature_manifest_sha256,
        "exit_policy_id": backtest_spec.exit_policy_id,
        "exit_policy_params": dict(backtest_spec.exit_policy_params),
        "exit_price_source": backtest_spec.exit_price_source,
        "lower_timeframe_dataset_path": str(backtest_spec.lower_timeframe_dataset_path)
        if backtest_spec.lower_timeframe_dataset_path is not None
        else None,
        "lower_timeframe_dataset_sha256": None,
        "cache_policy": BACKTEST_CACHE_POLICY,
        "cache_key_components": cache_key_components,
        "cache_key": _stable_hash(cache_key_components),
        "cache_lookup_used": False,
        "cache_hit": False,
        "execution_cache_reuse_enabled": False,
        "trade_count": 0,
        "required_metrics_present": True,
        "blocked": True,
        "blocker_code": "exit_policy_context_unavailable",
        "blocker_reason": blocker_reason,
        "cost_model": {},
        "validity": {
            "backtest_executed": False,
            "blocked_fail_closed": True,
            "reason": blocker_reason,
        },
        "result_sha256": result_sha256,
    }
    _write_json(manifest_path, manifest)
    backend_evidence = _backtest_backend_evidence(
        requested=cycle_spec.backtest_backend,
        fallback_reason="",
        manifest=manifest,
        compute_policy=cycle_spec.compute.to_payload(include_r97_defaults=True),
    )
    backend_evidence["backtest_backend_used"] = "blocked"
    backend_evidence["backtest_backend_rejection_reason"] = blocker_reason
    return CycleBacktestExecution(
        result=BacktestResult(
            output_dir=run_dir,
            manifest_path=manifest_path,
            trades_path=trades_path,
            signals_path=signals_path,
            equity_curve_path=equity_curve_path,
            metrics_path=metrics_path,
            config_resolved_path=config_path,
            result_sha256=result_sha256,
        ),
        manifest=manifest,
        backend_evidence=backend_evidence,
    )


def _blocked_backtest_metrics(*, blocker_reason: str, dataset: pd.DataFrame) -> dict[str, Any]:
    return {
        "net_return_after_fees_slippage_funding": -1.0,
        "gross_return_before_costs": 0.0,
        "trade_count": 0,
        "long_count": 0,
        "short_count": 0,
        "hit_rate": 0.0,
        "expectancy_per_trade": -1.0,
        "average_holding_time_ms": 0.0,
        "median_holding_time_ms": 0.0,
        "max_drawdown": -1.0,
        "profit_factor": 0.0,
        "exposure": 0.0,
        "turnover": 0.0,
        "slippage_sensitivity": 0.0,
        "funding_contribution": 0.0,
        "split_by_regime": {},
        "split_by_month": {},
        "split_by_volatility_bucket": {},
        "capacity_liquidity_flags": {
            "available": False,
            "reason": blocker_reason,
            "signal_count": 0,
            "market_row_count": int(len(dataset)),
        },
        "blocked": True,
        "blocker_reason": blocker_reason,
    }


def _blocked_trades_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "trade_id",
            "signal_id",
            "symbol",
            "side",
            "entry_time_ms",
            "exit_time_ms",
            "entry_bar_index",
            "exit_bar_index",
            "entry_price",
            "exit_price",
            "holding_ms",
            "exit_policy",
            "barrier_hit_type",
            "exit_sequence_proof",
            "exit_price_source",
            "net_return",
        ]
    )


def _blocked_signals_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["signal_id", "symbol", "decision_time_ms", "side", "strategy_id"])


def _blocked_equity_curve(dataset: pd.DataFrame) -> pd.DataFrame:
    time_column = next((column for column in ("bar_time_ms", "signal_bar_time_ms", "time_ms") if column in dataset.columns), None)
    if time_column is None:
        return pd.DataFrame(columns=["time_ms", "equity", "realized_net_return"])
    times = pd.to_numeric(dataset[time_column], errors="coerce").dropna().astype("int64")
    return pd.DataFrame(
        {
            "time_ms": times,
            "equity": 10_000.0,
            "realized_net_return": 0.0,
        }
    )


def _blocker_message(message: str) -> str:
    return str(message).replace("\\", "/").replace("\n", " ")[:240]


def _validate_cycle_lower_timeframe_requirements(
    spec: HistoricalResearchCycleSpec,
    data_source: Mapping[str, Any],
) -> None:
    if not any(_exit_policy_requires_lower_timeframe(policy["exit_policy_id"]) for policy in spec.exits.exit_policies):
        return
    path = _lower_timeframe_dataset_path(data_source)
    if path is None:
        raise ValueError("lower_timeframe_dataset_required_for_triple_barrier_exit")
    if not path.exists():
        raise ValueError(f"lower_timeframe_dataset_path_missing:{path}")
    _validate_lower_timeframe_dataset_schema(path)


def _candidate_lower_timeframe_dataset_path(
    candidate: Mapping[str, Any],
    data_source: Mapping[str, Any],
) -> Path | None:
    if not _candidate_requires_lower_timeframe(candidate):
        return None
    path = _lower_timeframe_dataset_path(data_source)
    if path is None:
        raise ValueError(f"lower_timeframe_dataset_required_for_exit_policy:{candidate.get('exit_policy_id')}")
    if not path.exists():
        raise ValueError(f"lower_timeframe_dataset_path_missing:{path}")
    return path


def _lower_timeframe_dataset_path(data_source: Mapping[str, Any]) -> Path | None:
    raw_path = data_source.get("lower_timeframe_dataset_path")
    if not raw_path:
        return None
    return Path(str(raw_path)).expanduser()


def _validate_lower_timeframe_dataset_schema(path: Path) -> None:
    required_columns = {"bar_time_ms", "high", "low", "close"}
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:
        raise ValueError(f"lower_timeframe_dataset_unreadable:{path}:{exc}") from exc
    if frame.empty:
        raise ValueError(f"lower_timeframe_dataset_empty:{path}")
    missing = sorted(required_columns - set(str(column) for column in frame.columns))
    if missing:
        raise ValueError(f"lower_timeframe_dataset_missing_columns:{','.join(missing)}")
    checked = frame.loc[:, sorted(required_columns)].copy()
    for column in required_columns:
        checked[column] = pd.to_numeric(checked[column], errors="coerce")
    if checked.dropna(subset=sorted(required_columns)).empty:
        raise ValueError(f"lower_timeframe_dataset_no_valid_ohlc_rows:{path}")


def _candidate_requires_lower_timeframe(candidate: Mapping[str, Any]) -> bool:
    return _exit_policy_requires_lower_timeframe(str(candidate.get("exit_policy_id") or ""))


def _exit_policy_requires_lower_timeframe(exit_policy_id: str) -> bool:
    return str(exit_policy_id).lower() in {"triple_barrier", "triple_barrier_atr"}


def _candidate_exit_price_source(candidate: Mapping[str, Any]) -> str:
    if _candidate_requires_lower_timeframe(candidate):
        return "lower_timeframe_ohlc_sequence"
    return "primary_close"


def _candidate_target_return(candidate: Mapping[str, Any]) -> float | None:
    value = candidate.get("target_return")
    if value is None:
        value = dict(candidate.get("exit_policy_params") or {}).get("target_return")
    return _optional_float(value)


def _candidate_stop_return(candidate: Mapping[str, Any]) -> float | None:
    value = candidate.get("stop_return")
    if value is None:
        value = dict(candidate.get("exit_policy_params") or {}).get("stop_return")
    return _optional_float(value)


def _build_cycle_validation_splits(
    market_frame: pd.DataFrame,
    *,
    spec: HistoricalResearchCycleSpec,
) -> tuple[WalkForwardSplit, ...]:
    splits: list[WalkForwardSplit] = []
    label_spec = infer_label_spec(
        market_frame,
        time_column="bar_time_ms",
        interval_ms=_infer_uniform_bar_interval_ms(market_frame),
        require_event_end_time=False,
        label_id="historical_cycle",
    )
    for mode in spec.validation.split_modes:
        if mode == "purged_embargoed_walk_forward":
            mode_splits = build_purged_walk_forward_splits(
                market_frame,
                min_splits=spec.validation.min_splits,
                purge_embargo_bars=spec.validation.purge_embargo_bars,
                label_spec=label_spec,
            )
        elif mode == "anchored_walk_forward":
            mode_splits = build_anchored_walk_forward_splits(
                market_frame,
                min_splits=spec.validation.min_splits,
                purge_embargo_bars=spec.validation.purge_embargo_bars,
                label_spec=label_spec,
            )
        elif mode == "rolling_walk_forward":
            train_window = int(spec.validation.rolling_train_window_bars or 0)
            if train_window <= 0:
                raise ValueError("validation.rolling_train_window_bars is required for rolling_walk_forward")
            mode_splits = build_rolling_walk_forward_splits(
                market_frame,
                min_splits=spec.validation.min_splits,
                train_window_bars=train_window,
                purge_embargo_bars=spec.validation.purge_embargo_bars,
                label_spec=label_spec,
            )
        elif mode == "shifted_purged_walk_forward":
            shifted: list[WalkForwardSplit] = []
            for offset in spec.validation.shifted_anchor_offsets:
                shifted.extend(
                    build_shifted_walk_forward_splits(
                        market_frame,
                        min_splits=spec.validation.min_splits,
                        anchor_offset_bars=int(offset),
                        purge_embargo_bars=spec.validation.purge_embargo_bars,
                        label_spec=label_spec,
                    )
                )
            mode_splits = tuple(shifted)
        elif mode == "month_holdout":
            mode_splits = month_holdout_splits(market_frame)
        elif mode == "stress_period_holdout":
            mode_splits = stress_period_holdout_splits(
                market_frame,
                volatility_column=spec.validation.stress_volatility_column,
                threshold=spec.validation.stress_zscore_threshold,
            )
        elif mode == "regime_holdout":
            mode_splits = regime_holdout_splits(
                market_frame,
                regime_column=spec.validation.regime_column,
            )
        else:
            raise ValueError(f"unsupported validation split mode: {mode}")
        if not mode_splits:
            raise ValueError(f"validation_split_mode_unavailable:{mode}")
        splits.extend(mode_splits)
    return _namespace_cycle_split_ids(tuple(splits))


def _namespace_cycle_split_ids(splits: tuple[WalkForwardSplit, ...]) -> tuple[WalkForwardSplit, ...]:
    split_ids = [split.split_id for split in splits]
    methods = {split.validation_method for split in splits}
    if len(methods) == 1 and len(split_ids) == len(set(split_ids)):
        return splits
    prefixes = {
        "purged_embargoed_walk_forward": "purged",
        "anchored_walk_forward": "anchored",
        "rolling_walk_forward": "rolling",
        "shifted_purged_walk_forward": "shifted",
        "month_holdout": "month",
        "stress_period_holdout": "stress",
        "regime_holdout": "regime",
    }
    used: dict[str, int] = {}
    namespaced: list[WalkForwardSplit] = []
    for split in splits:
        prefix = prefixes.get(split.validation_method, split.validation_method)
        base = f"{prefix}-{split.split_id}"
        count = used.get(base, 0) + 1
        used[base] = count
        split_id = base if count == 1 else f"{base}-{count:02d}"
        namespaced.append(replace(split, split_id=split_id))
    return tuple(namespaced)


def _cycle_split_manifest(
    splits: tuple[WalkForwardSplit, ...],
    *,
    spec: HistoricalResearchCycleSpec,
) -> dict[str, Any]:
    validation_methods = list(dict.fromkeys(split.validation_method for split in splits))
    validation_method = validation_methods[0] if len(validation_methods) == 1 else "configured_validation_splits"
    return {
        "split_manifest_version": SPLIT_ENGINE_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "split_count": len(splits),
        "validation_method": validation_method,
        "validation_methods": validation_methods,
        "validation_method_counts": _count_values(split.validation_method for split in splits),
        "split_mode_counts": _count_values(split.split_mode for split in splits),
        "purge_method_counts": _count_values(split.purge_method for split in splits),
        "label_event_end_time_columns": sorted(
            {
                str(split.label_event_end_time_column)
                for split in splits
                if split.label_event_end_time_column
            }
        ),
        "split_modes_requested": list(spec.validation.split_modes),
        "purge_embargo_bars": int(spec.validation.purge_embargo_bars),
        "purge_embargo_ms_values": sorted(
            {
                int(split.purge_embargo_ms)
                for split in splits
                if split.purge_embargo_ms is not None
            }
        ),
        "min_splits": int(spec.validation.min_splits),
        "rolling_train_window_bars": spec.validation.rolling_train_window_bars,
        "shifted_anchor_offsets": list(spec.validation.shifted_anchor_offsets),
        "regime_column": spec.validation.regime_column,
        "stress_volatility_column": spec.validation.stress_volatility_column,
        "stress_zscore_threshold": float(spec.validation.stress_zscore_threshold),
        "splits": [split.to_payload() for split in splits],
    }


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def run_historical_research_cycle(
    *,
    spec_path: Path,
    app_config: AppConfig | None = None,
    feature_cache_dir: Path | None = None,
) -> HistoricalResearchCycleResult:
    started = time.perf_counter()
    app_config = app_config or AppConfig.from_env()
    spec_path = Path(spec_path).expanduser().resolve()
    spec = HistoricalResearchCycleSpec.from_path(spec_path)
    _validate_compute_backend_request(spec)
    repo_root = _repo_root_from_path(spec_path)
    research_root = _resolve_research_root(app_config.research.output_dir, repo_root=repo_root)
    output_dir = spec.output_dir or research_root / "historical_cycles" / _run_id(spec.cycle_id)
    output_dir = output_dir.resolve()
    _ensure_inside_research_root(
        output_dir,
        research_root=research_root,
        field_name="historical cycle output_dir",
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset, data_source = _load_cycle_dataset(spec, output_dir=output_dir)
    dataset = _sort_cycle_dataset(dataset)
    _validate_cycle_lower_timeframe_requirements(spec, data_source)
    dataset_hash = _frame_hash(dataset)
    resolved_spec_path = output_dir / "cycle_spec_resolved.json"
    _write_json(resolved_spec_path, spec.to_payload())

    data_quality_report = _data_quality_report(dataset, spec=spec, data_source=data_source, dataset_hash=dataset_hash)
    data_quality_path = output_dir / "data_quality_report.json"
    _write_json(data_quality_path, data_quality_report)

    feature_build = _feature_build_manifest(
        spec=spec,
        dataset=dataset,
        dataset_hash=dataset_hash,
        data_source=data_source,
        output_dir=output_dir,
        feature_cache_dir=feature_cache_dir,
    )
    if _feature_set_prediction_overlays(spec.features.materialized_prediction_overlays):
        feature_build = _apply_materialized_prediction_overlays(feature_build, spec=spec)
    feature_build_manifest = feature_build.manifest
    feature_frames = feature_build.frames_by_feature_set
    candidates = _candidate_space(spec)
    candidate_overlay_context = _candidate_scoped_prediction_overlay_context(
        feature_build,
        spec=spec,
        candidates=candidates,
    )
    feature_build_manifest = candidate_overlay_context.feature_build_manifest
    feature_build_path = output_dir / "feature_build_manifest.json"
    _write_json(feature_build_path, feature_build_manifest)

    market_frame = _cycle_market_frame(dataset)
    splits = _build_cycle_validation_splits(market_frame, spec=spec)
    split_manifest = _cycle_split_manifest(splits, spec=spec)
    split_manifest_path = output_dir / "split_manifest.json"
    _write_json(split_manifest_path, split_manifest)

    search_mode = "explicit_search_spaces" if spec.optimizer.search_spaces else "metadata_default_search"
    search_method = _candidate_search_method(spec) if spec.optimizer.search_spaces else "metadata_capped_grid"
    generated_strategy_ids = _candidate_strategy_ids(candidates)
    comparator_coverage = _baseline_comparator_coverage(candidates)
    candidate_space_manifest = {
        "candidate_space_manifest_version": "historical-research-candidate-space-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_count": len(candidates),
        "candidate_id_scheme": "candidate_config_sha256",
        "search_mode": search_mode,
        "search_method": search_method,
        "method_sequence": list(spec.optimizer.method_sequence),
        "search_spaces": [dict(space) for space in spec.optimizer.search_spaces],
        "default_search_policy": _default_search_policy(spec, candidates),
        "strategy_parameter_metadata": strategy_parameter_manifest(generated_strategy_ids),
        "declared_strategies": list(spec.strategies),
        "generated_strategy_ids": generated_strategy_ids,
        "strategies": generated_strategy_ids,
        "feature_sets": list(spec.features.feature_sets),
        "holding_windows": list(spec.holding_windows),
        "exit_policies": [dict(policy) for policy in spec.exits.exit_policies],
        "lower_timeframe_evidence": _cycle_lower_timeframe_evidence(data_source),
        "baseline_comparator_policy": {
            "policy_version": "baseline-comparator-policy-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "scope": "baseline_comparator_evidence_only",
            "no_trade_strategy_id": NO_TRADE_BASELINE_STRATEGY_ID,
            "transparent_baseline_strategy_ids": list(TRANSPARENT_BASELINE_STRATEGY_IDS),
            "injection_enabled": True,
            "candidate_group_key": "feature_set_id|holding_window",
            "coverage": comparator_coverage,
        },
        "baseline_comparator_coverage": comparator_coverage,
        "candidates": candidates,
    }
    candidate_space_path = output_dir / "candidate_space_manifest.json"

    backtest_root = output_dir / "backtests"
    reference_engine = BacktestEngine()
    vector_engine = VectorBacktestEngine()
    cuda_engine = CudaFixedHoldingBacktestEngine()
    aggregate_records: list[dict[str, Any]] = []
    backtest_index_records: list[dict[str, Any]] = []
    regime_metric_records: list[dict[str, Any]] = []
    side_metric_records: list[dict[str, Any]] = []
    candidate_results_by_id: dict[str, CandidateResult] = {}
    aggregate_workers = _aggregate_backtest_worker_count(spec)
    performance_plan = build_candidate_selection_performance_plan(
        spec=spec,
        candidates=candidates,
        search_mode=search_mode,
        search_method=search_method,
        aggregate_backtest_workers_used=aggregate_workers,
    )
    candidate_space_manifest["performance_plan"] = performance_plan
    candidate_space_manifest["compute_policy"] = performance_plan["compute_policy"]
    _write_json(candidate_space_path, candidate_space_manifest)

    aggregate_evaluations = _aggregate_candidate_evaluations(
        spec=spec,
        candidates=candidates,
        feature_frames=feature_frames,
        feature_build_manifest=feature_build_manifest,
        candidate_overlay_context=candidate_overlay_context,
        data_source=data_source,
        backtest_root=backtest_root,
        workers=aggregate_workers,
    )
    for evaluation in aggregate_evaluations:
        candidate = evaluation["candidate"]
        result = evaluation["result"]
        metrics = evaluation["metrics"]
        manifest = evaluation["manifest"]
        backend_evidence = evaluation["backend_evidence"]
        aggregate_records.append(
            _ranking_record(
                spec=spec,
                candidate=candidate,
                metrics=metrics,
                manifest_path=result.manifest_path,
                metrics_path=result.metrics_path,
                data_source=data_source,
                split_evaluated=False,
                manifest=manifest,
                backend_evidence=backend_evidence,
            )
        )
        regime_metric_records.extend(
            _regime_metric_records(
                candidate,
                metrics=metrics,
                manifest_path=result.manifest_path,
                trades_path=result.trades_path,
            )
        )
        side_metric_records.extend(_side_metric_records(candidate, trades_path=result.trades_path, manifest_path=result.manifest_path))
        candidate_results_by_id[str(candidate["candidate_id"])] = _candidate_result_from_metrics(
            candidate,
            metrics=metrics,
            feature_missingness=_feature_missingness_for_candidate(feature_build_manifest, candidate),
        )
        backtest_index_records.append(
            _backtest_index_record(
                candidate,
                result.manifest_path,
                result.metrics_path,
                manifest,
                "aggregate",
                trades_path=result.trades_path,
                backend_evidence=backend_evidence,
            )
        )

    rankings = _annotate_rankings_with_comparator_evidence(pd.DataFrame(aggregate_records))
    rankings = _annotate_rankings_with_ablation_evidence(rankings)
    rankings = rankings.sort_values(["final_score", "trade_count"], ascending=[False, False], kind="mergesort").reset_index(drop=True)
    rankings["rank"] = range(1, len(rankings) + 1)
    candidate_rankings_path = output_dir / "candidate_rankings.parquet"

    refinable_rankings = rankings.loc[
        rankings["aggregate_backtest_backend_rejection_reason"].fillna("").astype(str) == ""
    ]
    shortlisted_ids = set(
        refinable_rankings.head(max(1, int(spec.optimizer.top_regions_to_refine)))["candidate_id"].astype(str)
    )
    split_records: list[dict[str, Any]] = []
    cost_stress_records: list[dict[str, Any]] = []
    for candidate in candidates:
        if str(candidate["candidate_id"]) not in shortlisted_ids:
            continue
        candidate = _candidate_with_materialized_overlay_evidence(
            candidate,
            feature_build_manifest,
            candidate_overlay_context,
        )
        candidate_frame = _candidate_feature_frame(feature_frames, candidate, candidate_overlay_context)
        candidate_feature_record = _candidate_feature_record(feature_build_manifest, candidate, candidate_overlay_context)
        candidate_dataset_hash = _validated_feature_frame_hash(candidate_frame, candidate_feature_record, candidate)
        candidate_feature_manifest_sha256 = str(candidate_feature_record["feature_manifest_sha256"])
        lower_timeframe_dataset_path = _candidate_lower_timeframe_dataset_path(candidate, data_source)
        for split in splits:
            split_payload = split.to_payload()
            split_frame = frame_for_split(candidate_frame, split)
            split_dataset_hash = _frame_hash(split_frame)
            split_execution = _run_cycle_backtest_fail_closed(
                candidate=candidate,
                cycle_spec=spec,
                reference_engine=reference_engine,
                vector_engine=vector_engine,
                cuda_engine=cuda_engine,
                backtest_spec=BacktestSpec(
                    run_id=_candidate_backtest_run_id(candidate, "split", str(split.split_id)),
                    symbol=spec.symbol,
                    output_dir=backtest_root / "splits",
                    strategy_id=str(candidate["strategy_id"]),
                    holding_window=str(candidate["holding_window"]),
                    feature_set_id=str(candidate["feature_set_id"]),
                    feature_manifest_sha256=candidate_feature_manifest_sha256,
                    dataset_sha256=split_dataset_hash,
                    exit_policy_id=str(candidate.get("exit_policy_id", "fixed_holding_window")),
                    target_return=_candidate_target_return(candidate),
                    stop_return=_candidate_stop_return(candidate),
                    exit_policy_params=dict(candidate.get("exit_policy_params") or {}),
                    exit_price_source=_candidate_exit_price_source(candidate),
                    lower_timeframe_dataset_path=lower_timeframe_dataset_path,
                    strategy_config=_strategy_config(candidate),
                ),
                dataset=split_frame,
                allow_cuda=False,
            )
            split_result = split_execution.result
            metrics = _read_json(split_result.metrics_path)
            split_records.append(
                _split_metric_record(
                    candidate,
                    split_payload,
                    metrics,
                    split_result.manifest_path,
                    trade_count_floor=spec.validation.trade_count_floor,
                )
            )
            backtest_index_records.append(
                _backtest_index_record(
                    candidate,
                    split_result.manifest_path,
                    split_result.metrics_path,
                    split_execution.manifest,
                    "walk_forward_split",
                    trades_path=split_result.trades_path,
                    backend_evidence=split_execution.backend_evidence,
                    split=split_payload,
                )
            )
        for scenario in _cost_stress_scenarios():
            stress_frame = _cost_stress_frame(candidate_frame, scenario)
            stress_dataset_hash = _frame_hash(stress_frame)
            stress_execution = _run_cycle_backtest_fail_closed(
                candidate=candidate,
                cycle_spec=spec,
                reference_engine=reference_engine,
                vector_engine=vector_engine,
                cuda_engine=cuda_engine,
                backtest_spec=BacktestSpec(
                    run_id=_candidate_backtest_run_id(candidate, "cost", _short_scenario_id(str(scenario["scenario_id"]))),
                    symbol=spec.symbol,
                    output_dir=backtest_root / "cost_stress",
                    strategy_id=str(candidate["strategy_id"]),
                    holding_window=str(candidate["holding_window"]),
                    feature_set_id=str(candidate["feature_set_id"]),
                    feature_manifest_sha256=candidate_feature_manifest_sha256,
                    dataset_sha256=stress_dataset_hash,
                    fee_bps=float(scenario["fee_bps"]),
                    slippage_bps=float(scenario["slippage_bps"]),
                    spread_bps=float(scenario.get("spread_bps", 0.0)),
                    funding_rate=float(scenario["funding_rate"]),
                    cost_profile_id=str(scenario["cost_profile_id"]),
                    fill_profile_id=str(scenario["fill_profile_id"]),
                    exit_policy_id=str(candidate.get("exit_policy_id", "fixed_holding_window")),
                    target_return=_candidate_target_return(candidate),
                    stop_return=_candidate_stop_return(candidate),
                    exit_policy_params=dict(candidate.get("exit_policy_params") or {}),
                    exit_price_source=_candidate_exit_price_source(candidate),
                    lower_timeframe_dataset_path=lower_timeframe_dataset_path,
                    strategy_config=_strategy_config(candidate),
                ),
                dataset=stress_frame,
                allow_cuda=False,
            )
            stress_result = stress_execution.result
            metrics = _read_json(stress_result.metrics_path)
            cost_stress_records.append(
                _cost_stress_record(
                    candidate,
                    scenario,
                    metrics,
                    stress_result.manifest_path,
                    source_row_count=len(stress_frame),
                    stress_dataset_sha256=stress_dataset_hash,
                )
            )
            backtest_index_records.append(
                _backtest_index_record(
                    candidate,
                    stress_result.manifest_path,
                    stress_result.metrics_path,
                    stress_execution.manifest,
                    "cost_stress",
                    trades_path=stress_result.trades_path,
                    backend_evidence=stress_execution.backend_evidence,
                )
            )

    candidate_results = _enriched_candidate_results(candidate_results_by_id, split_records, cost_stress_records)
    rankings = _annotate_rankings_with_validation(
        rankings,
        candidate_results,
        shortlisted_ids,
        required_split_count=len(splits),
        required_cost_stress_count=len(_cost_stress_scenarios()),
    )
    stability_regions = _stability_regions(candidate_results)
    rankings = _annotate_rankings_with_research_gate(
        rankings,
        stability_regions=stability_regions,
        regime_metric_records=regime_metric_records,
        side_metric_records=side_metric_records,
        split_records=split_records,
        cost_stress_records=cost_stress_records,
        spec=spec,
        data_source=data_source,
    )
    rankings.to_parquet(candidate_rankings_path, index=False)

    backtest_index_path = output_dir / "backtest_index.parquet"
    pd.DataFrame(backtest_index_records).to_parquet(backtest_index_path, index=False)
    metrics_by_split_path = output_dir / "metrics_by_split.parquet"
    pd.DataFrame(split_records).to_parquet(metrics_by_split_path, index=False)
    metrics_by_regime_path = output_dir / "metrics_by_regime.parquet"
    _metric_frame(regime_metric_records, columns=_regime_metric_columns()).to_parquet(metrics_by_regime_path, index=False)
    metrics_by_side_path = output_dir / "metrics_by_side.parquet"
    _metric_frame(side_metric_records, columns=_side_metric_columns()).to_parquet(metrics_by_side_path, index=False)
    metrics_by_holding_path = output_dir / "metrics_by_holding_window.parquet"
    _metrics_by_holding_window(rankings).to_parquet(metrics_by_holding_path, index=False)
    metrics_by_cost_stress_path = output_dir / "metrics_by_cost_stress.parquet"
    pd.DataFrame(cost_stress_records).to_parquet(metrics_by_cost_stress_path, index=False)
    stability_regions_path = output_dir / "stability_regions.parquet"
    stability_regions.to_parquet(stability_regions_path, index=False)
    candidate_gate_report_path = output_dir / "candidate_gate_report.parquet"
    _candidate_gate_report(rankings, stability_regions, spec=spec).to_parquet(candidate_gate_report_path, index=False)

    ablation_report_path = output_dir / "ablation_report.json"
    _write_json(ablation_report_path, _ablation_report(rankings, spec=spec))
    trial_budget_report_path = output_dir / "trial_budget_report.json"
    trial_budget_report = _trial_budget_report(
        spec=spec,
        candidates=candidates,
        rankings=rankings,
        backtest_index_records=backtest_index_records,
        split_records=split_records,
        cost_stress_records=cost_stress_records,
        search_mode=search_mode,
        search_method=search_method,
        performance_plan=performance_plan,
    )
    _write_json(trial_budget_report_path, trial_budget_report)
    overfit_adjustment_report_path = output_dir / "overfit_adjustment_report.json"
    _write_json(
        overfit_adjustment_report_path,
        _overfit_adjustment_report(
            spec=spec,
            rankings=rankings,
            stability_regions=stability_regions,
            split_records=split_records,
            cost_stress_records=cost_stress_records,
            trial_budget_report=trial_budget_report,
        ),
    )
    rejection_report_path = output_dir / "rejection_report.md"
    rejection_report_path.write_text(_rejection_report(rankings, spec=spec, data_source=data_source), encoding="utf-8")
    source_selection_path = output_dir / "source_selection_manifest.json"
    _write_json(source_selection_path, dict(data_source.get("source_selection") or {}))
    required_outputs = {
        "research_cycle_manifest": str(output_dir / "research_cycle_manifest.json"),
        "cycle_spec_resolved": str(resolved_spec_path),
        "source_selection_manifest": str(source_selection_path),
        "data_quality_report": str(data_quality_path),
        "feature_build_manifest": str(feature_build_path),
        "split_manifest": str(split_manifest_path),
        "candidate_space_manifest": str(candidate_space_path),
        "backtest_index": str(backtest_index_path),
        "candidate_rankings": str(candidate_rankings_path),
        "candidate_gate_report": str(candidate_gate_report_path),
        "stability_regions": str(stability_regions_path),
        "metrics_by_split": str(metrics_by_split_path),
        "metrics_by_regime": str(metrics_by_regime_path),
        "metrics_by_side": str(metrics_by_side_path),
        "metrics_by_holding_window": str(metrics_by_holding_path),
        "metrics_by_cost_stress": str(metrics_by_cost_stress_path),
        "ablation_report": str(ablation_report_path),
        "trial_budget_report": str(trial_budget_report_path),
        "overfit_adjustment_report": str(overfit_adjustment_report_path),
        "rejection_report": str(rejection_report_path),
    }
    manifest = {
        "research_cycle_manifest_version": RESEARCH_CYCLE_MANIFEST_VERSION,
        "runner_version": RESEARCH_CYCLE_RUNNER_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "cycle_id": spec.cycle_id,
        "symbol": spec.symbol,
        "spec_path": str(spec_path),
        "spec_sha256": _file_sha256(spec_path),
        "output_dir": str(output_dir),
        "data_source": data_source,
        "lower_timeframe_evidence": _cycle_lower_timeframe_evidence(data_source),
        "dataset_sha256": dataset_hash,
        "candidate_count": len(candidates),
        "candidate_search_mode": search_mode,
        "candidate_search_method": search_method,
        "candidate_selection_performance_plan": performance_plan,
        "compute_policy": performance_plan["compute_policy"],
        "backtest_backend_requested": spec.backtest_backend,
        "backtest_backend_summary": _backtest_backend_summary(backtest_index_records),
        "aggregate_backtest_count": len(candidates),
        "split_backtest_count": len(split_records),
        "cost_stress_backtest_count": len(cost_stress_records),
        "candidate_pack_written": False,
        "candidate_pack_scope": "research_only_evidence_pack",
        "candidate_pack_paths": [],
        "candidate_acceptance_scope": "research_gate_evaluated_fail_closed",
        "live_fetch_used": False,
        "order_placement_used": False,
        "position_sizing_used": False,
        "runtime_mode_changed": False,
        "live_config_written": False,
        "required_outputs": required_outputs,
        "runtime": {"elapsed_seconds": round(time.perf_counter() - started, 6)},
    }
    manifest_path = output_dir / "research_cycle_manifest.json"
    _write_json(manifest_path, manifest)
    candidate_pack_ids = _research_pack_candidate_ids(rankings, cycle_manifest_path=manifest_path)
    candidate_pack_manifest_paths = [
        _candidate_pack_output_dir(output_dir, candidate_id) / "research_candidate_pack_manifest.json"
        for candidate_id in candidate_pack_ids
    ]
    if candidate_pack_ids:
        manifest["candidate_pack_written"] = True
        manifest["candidate_pack_paths"] = [str(path) for path in candidate_pack_manifest_paths]
        manifest["candidate_acceptance_scope"] = "research_only_pack_eligible_candidates_written"
        _write_json(manifest_path, manifest)
        try:
            for candidate_id in candidate_pack_ids:
                write_research_candidate_pack(
                    cycle_manifest_path=manifest_path,
                    candidate_id=candidate_id,
                    output_dir=_candidate_pack_output_dir(output_dir, candidate_id),
                )
        except Exception:
            manifest["candidate_pack_written"] = False
            manifest["candidate_pack_paths"] = []
            manifest["candidate_acceptance_scope"] = "research_gate_evaluated_pack_write_failed"
            _write_json(manifest_path, manifest)
            raise
        missing_pack_paths = [path for path in candidate_pack_manifest_paths if not path.exists()]
        if missing_pack_paths:
            manifest["candidate_pack_written"] = False
            manifest["candidate_pack_paths"] = []
            manifest["candidate_acceptance_scope"] = "research_gate_evaluated_pack_write_failed"
            _write_json(manifest_path, manifest)
            raise ValueError(
                "candidate pack writer did not create expected manifests: "
                + "|".join(str(path) for path in missing_pack_paths)
            )
    return HistoricalResearchCycleResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        candidate_rankings_path=candidate_rankings_path,
        backtest_index_path=backtest_index_path,
        rejection_report_path=rejection_report_path,
    )


def _load_cycle_dataset(spec: HistoricalResearchCycleSpec, *, output_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_selection: list[dict[str, Any]] = []
    if spec.data.dataset_path is not None:
        source_selection.append(
            _source_selection_record(
                "local_dataset_path",
                "selected",
                dataset_path=str(spec.data.dataset_path),
            )
        )
        frame = pd.read_parquet(spec.data.dataset_path)
        return frame, {
            "source_type": "local_dataset_path",
            "dataset_path": str(spec.data.dataset_path),
            "synthetic": False,
            "synthetic_fallback_allowed": bool(spec.data.synthetic_fallback_allowed),
            "source_selection": _source_selection_payload(
                spec,
                source_selection,
                selected_source_type="local_dataset_path",
            ),
            **_explicit_lower_timeframe_evidence(spec.data.lower_timeframe_dataset_path),
        }
    for manifest_path in spec.data.dataset_manifest_paths:
        if not manifest_path.exists():
            source_selection.append(
                _source_selection_record(
                    "dataset_manifest",
                    "skipped",
                    reason="manifest_path_missing",
                    manifest_path=str(manifest_path),
                )
            )
            continue
        manifest = _read_json(manifest_path)
        manifest_version = str(manifest.get("manifest_version") or manifest.get("fixture_pack_manifest_version") or "")
        if manifest_version == HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION:
            validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
            public_archive_readiness = validate_public_archive_fixture_readiness(manifest, manifest_path=manifest_path)
            parquet_path = resolve_fixture_pack_cycle_dataset_path(manifest, manifest_path=manifest_path)
            frame = pd.read_parquet(parquet_path)
            context = materialize_fixture_family_context(
                frame,
                optional_context_families=getattr(validation, "optional_context_families", None),
            )
            fixture_source = dict(manifest.get("source") or {})
            source_selection.append(
                _source_selection_record(
                    "historical_fixture_pack",
                    "selected",
                    manifest_path=str(manifest_path),
                    dataset_path=str(parquet_path),
                    fixture_id=manifest.get("fixture_id"),
                )
            )
            return context.frame, {
                "source_type": "historical_fixture_pack",
                "manifest_path": str(manifest_path),
                "manifest_sha256": _file_sha256(manifest_path),
                "dataset_path": str(parquet_path),
                "fixture_id": manifest.get("fixture_id"),
                "symbol": manifest.get("symbol"),
                "base_interval": manifest.get("base_interval"),
                "fixture_scope": manifest.get("fixture_scope"),
                "fixture_source": fixture_source,
                "provider_capability": dict(fixture_source.get("provider_capability") or {}),
                "durable_public_archive_readiness": public_archive_readiness.to_payload(),
                "fixture_derivation": dict(manifest.get("derivation") or {}),
                "omitted_optional_families": dict(manifest.get("omitted_optional_families") or {}),
                "research_evidence_limitations": list(manifest.get("research_evidence_limitations") or []),
                "synthetic": False,
                "synthetic_fallback_allowed": bool(spec.data.synthetic_fallback_allowed),
                "source_selection": _source_selection_payload(
                    spec,
                    source_selection,
                    selected_source_type="historical_fixture_pack",
                ),
                "validation": validation.to_payload(),
                "fixture_family_context": dict(context.evidence),
                "fixture_family_context_sha256": context.context_sha256,
                **_fixture_lower_timeframe_evidence(validation),
            }
        parquet_path = _resolve_manifest_data_path(manifest_path, manifest)
        if parquet_path is not None:
            source_selection.append(
                _source_selection_record(
                    "dataset_manifest",
                    "selected",
                    manifest_path=str(manifest_path),
                    dataset_path=str(parquet_path),
                )
            )
            frame = pd.read_parquet(parquet_path)
            return frame, {
                "source_type": "dataset_manifest",
                "manifest_path": str(manifest_path),
                "dataset_path": str(parquet_path),
                "synthetic": False,
                "synthetic_fallback_allowed": bool(spec.data.synthetic_fallback_allowed),
                "source_selection": _source_selection_payload(
                    spec,
                    source_selection,
                    selected_source_type="dataset_manifest",
                ),
                **_explicit_lower_timeframe_evidence(spec.data.lower_timeframe_dataset_path),
            }
        source_selection.append(
            _source_selection_record(
                "dataset_manifest",
                "rejected",
                reason="manifest_data_path_missing_or_unusable",
                manifest_path=str(manifest_path),
            )
        )
    if spec.data.local_fixture_dir is not None and spec.data.local_fixture_dir.exists():
        parquet_files = sorted(spec.data.local_fixture_dir.glob("*.parquet"))
        if len(parquet_files) == 1:
            source_selection.append(
                _source_selection_record(
                    "local_fixture_dir",
                    "selected",
                    fixture_dir=str(spec.data.local_fixture_dir),
                    dataset_path=str(parquet_files[0]),
                )
            )
            frame = pd.read_parquet(parquet_files[0])
            return frame, {
                "source_type": "local_fixture_dir",
                "fixture_dir": str(spec.data.local_fixture_dir),
                "dataset_path": str(parquet_files[0]),
                "synthetic": False,
                "synthetic_fallback_allowed": bool(spec.data.synthetic_fallback_allowed),
                "source_selection": _source_selection_payload(
                    spec,
                    source_selection,
                    selected_source_type="local_fixture_dir",
                ),
                **_explicit_lower_timeframe_evidence(spec.data.lower_timeframe_dataset_path),
            }
        if len(parquet_files) > 1:
            source_selection.append(
                _source_selection_record(
                    "local_fixture_dir",
                    "rejected",
                    reason="local_fixture_dir_ambiguous_multiple_parquet_files",
                    fixture_dir=str(spec.data.local_fixture_dir),
                    parquet_count=len(parquet_files),
                )
            )
            raise ValueError("local_fixture_dir_ambiguous_multiple_parquet_files")
        source_selection.append(
            _source_selection_record(
                "local_fixture_dir",
                "rejected",
                reason="local_fixture_dir_has_no_parquet",
                fixture_dir=str(spec.data.local_fixture_dir),
            )
        )
    elif spec.data.local_fixture_dir is not None:
        source_selection.append(
            _source_selection_record(
                "local_fixture_dir",
                "skipped",
                reason="local_fixture_dir_missing",
                fixture_dir=str(spec.data.local_fixture_dir),
            )
        )
    declared_source = (
        spec.data.dataset_path is not None
        or spec.data.local_fixture_dir is not None
        or bool(spec.data.dataset_manifest_paths)
    )
    if spec.data.synthetic_fixture:
        source_selection.append(
            _source_selection_record(
                "synthetic_deterministic_fixture",
                "selected",
                reason="explicit_synthetic_fixture_requested",
                synthetic_use_case=spec.data.synthetic_use_case,
            )
        )
        frame = build_hmm_knn_sweep_dataset(row_count=spec.data.synthetic_row_count, variant=spec.data.synthetic_variant)
        fixture_path = output_dir / "synthetic_fixture.parquet"
        frame.to_parquet(fixture_path, index=False)
        return frame, {
            "source_type": "synthetic_deterministic_fixture",
            "dataset_path": str(fixture_path),
            "synthetic": True,
            "synthetic_fixture_requested": True,
            "synthetic_fallback_allowed": bool(spec.data.synthetic_fallback_allowed),
            "synthetic_use_case": spec.data.synthetic_use_case,
            "demo_or_test_only": True,
            "source_selection": _source_selection_payload(
                spec,
                source_selection,
                selected_source_type="synthetic_deterministic_fixture",
            ),
            **_explicit_lower_timeframe_evidence(spec.data.lower_timeframe_dataset_path),
        }
    if not declared_source:
        raise ValueError("cycle_data_source_required: explicit dataset path, manifest, local fixture parquet, or synthetic_fixture=true is required")
    raise ValueError("no usable dataset path, manifest, local fixture parquet, or explicit synthetic fixture flag was supplied")


def _source_selection_record(source_type: str, status: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_type": source_type,
        "status": status,
    }
    for key, value in fields.items():
        if value is None:
            payload[key] = None
        elif isinstance(value, (str, int, float, bool)):
            payload[key] = value
        else:
            payload[key] = str(value)
    return payload


def _source_selection_payload(
    spec: HistoricalResearchCycleSpec,
    records: list[dict[str, Any]],
    *,
    selected_source_type: str,
) -> dict[str, Any]:
    return {
        "source_selection_manifest_version": "research-cycle-source-selection-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "selected_source_type": selected_source_type,
        "declared_source_count": int(
            (1 if spec.data.dataset_path is not None else 0)
            + len(spec.data.dataset_manifest_paths)
            + (1 if spec.data.local_fixture_dir is not None else 0)
        ),
        "synthetic_fixture_requested": bool(spec.data.synthetic_fixture),
        "synthetic_fallback_allowed": bool(spec.data.synthetic_fallback_allowed),
        "synthetic_use_case": spec.data.synthetic_use_case if spec.data.synthetic_fixture else None,
        "records": [dict(record) for record in records],
    }


def _resolve_manifest_data_path(manifest_path: Path, manifest: Mapping[str, Any]) -> Path | None:
    raw_path = manifest.get("dataset_path") or manifest.get("parquet_path") or manifest.get("data_path")
    if not raw_path:
        return None
    candidate = Path(str(raw_path)).expanduser()
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    resolved = (manifest_path.parent / candidate).resolve()
    return resolved if resolved.exists() else None


def _fixture_lower_timeframe_evidence(validation: Any) -> dict[str, Any]:
    path = getattr(validation, "lower_timeframe_dataset_path", None)
    family = dict(getattr(validation, "lower_timeframe_family", None) or {})
    if path is None:
        return {
            "lower_timeframe_family_present": False,
            "lower_timeframe_dataset_path": None,
            "lower_timeframe_dataset_sha256": None,
            "lower_timeframe_row_count": None,
            "lower_timeframe_family": {},
        }
    path = Path(path)
    return {
        "lower_timeframe_family_present": True,
        "lower_timeframe_dataset_path": str(path),
        "lower_timeframe_dataset_sha256": _file_sha256(path) if path.exists() else None,
        "lower_timeframe_row_count": getattr(validation, "lower_timeframe_row_count", None),
        "lower_timeframe_family": family,
    }


def _explicit_lower_timeframe_evidence(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "lower_timeframe_family_present": False,
            "lower_timeframe_dataset_path": None,
            "lower_timeframe_dataset_sha256": None,
            "lower_timeframe_row_count": None,
            "lower_timeframe_family": {},
        }
    frame = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    return {
        "lower_timeframe_family_present": bool(path.exists()),
        "lower_timeframe_dataset_path": str(path),
        "lower_timeframe_dataset_sha256": _file_sha256(path) if path.exists() else None,
        "lower_timeframe_row_count": int(len(frame)) if path.exists() else None,
        "lower_timeframe_family": {
            "path": str(path),
            "sha256": _file_sha256(path) if path.exists() else None,
            "row_count": int(len(frame)) if path.exists() else None,
            "columns": list(frame.columns) if path.exists() else [],
            "data_family": "explicit_lower_timeframe_bars",
            "event_time_field": "bar_time_ms",
        },
    }


def _cycle_lower_timeframe_evidence(data_source: Mapping[str, Any]) -> dict[str, Any]:
    family = dict(data_source.get("lower_timeframe_family") or {})
    return {
        "lower_timeframe_family_present": bool(data_source.get("lower_timeframe_family_present", False)),
        "lower_timeframe_dataset_path": data_source.get("lower_timeframe_dataset_path"),
        "lower_timeframe_dataset_sha256": data_source.get("lower_timeframe_dataset_sha256"),
        "lower_timeframe_row_count": data_source.get("lower_timeframe_row_count"),
        "lower_timeframe_family": family,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _cycle_market_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "bar_time_ms" not in result.columns:
        if "signal_bar_time_ms" in result.columns:
            result["bar_time_ms"] = pd.to_numeric(result["signal_bar_time_ms"], errors="coerce").astype("int64")
        elif "time_ms" in result.columns:
            result["bar_time_ms"] = pd.to_numeric(result["time_ms"], errors="coerce").astype("int64")
        else:
            raise ValueError("cycle dataset requires bar_time_ms, signal_bar_time_ms, or time_ms")
    if "validation_regime" not in result.columns:
        if "top_regime_label" in result.columns:
            result["validation_regime"] = result["top_regime_label"].astype(str)
        elif "regime" in result.columns:
            result["validation_regime"] = result["regime"].astype(str)
        else:
            result["validation_regime"] = _validation_regime_labels(result)
    return result.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)


def _validation_regime_labels(frame: pd.DataFrame) -> list[str]:
    volatility = (
        pd.to_numeric(frame["volatility_shock_zscore"], errors="coerce")
        if "volatility_shock_zscore" in frame.columns
        else pd.Series([float("nan")] * len(frame), index=frame.index)
    )
    slope = (
        pd.to_numeric(frame["directional_slope_atr"], errors="coerce")
        if "directional_slope_atr" in frame.columns
        else pd.Series([float("nan")] * len(frame), index=frame.index)
    )
    labels: list[str] = []
    for vol_value, slope_value in zip(volatility.tolist(), slope.tolist()):
        if pd.notna(vol_value) and abs(float(vol_value)) >= 2.0:
            labels.append("shock")
        elif pd.notna(slope_value) and abs(float(slope_value)) >= 0.04:
            labels.append("trend")
        elif pd.notna(slope_value) or pd.notna(vol_value):
            labels.append("range")
        else:
            labels.append("unknown")
    return labels


def _sort_cycle_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    for column in ("bar_time_ms", "signal_bar_time_ms", "time_ms"):
        if column in frame.columns:
            result = frame.copy()
            result[column] = pd.to_numeric(result[column], errors="coerce")
            return result.sort_values(column, kind="mergesort").reset_index(drop=True)
    return frame.reset_index(drop=True)


def _data_quality_report(
    frame: pd.DataFrame,
    *,
    spec: HistoricalResearchCycleSpec,
    data_source: Mapping[str, Any],
    dataset_hash: str,
) -> dict[str, Any]:
    market = _cycle_market_frame(frame)
    missingness = {column: float(frame[column].isna().mean()) for column in frame.columns if frame[column].isna().any()}
    return {
        "data_quality_report_version": "historical-research-data-quality-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "symbol": spec.symbol,
        "dataset_sha256": dataset_hash,
        "data_source": dict(data_source),
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "missingness": missingness,
        "time_span": {
            "first_bar_time_ms": int(market["bar_time_ms"].min()),
            "last_bar_time_ms": int(market["bar_time_ms"].max()),
        },
        "live_fetch_used": False,
        "order_placement_used": False,
    }


def _feature_build_manifest(
    *,
    spec: HistoricalResearchCycleSpec,
    dataset: pd.DataFrame,
    dataset_hash: str,
    data_source: Mapping[str, Any] | None = None,
    output_dir: Path | None = None,
    feature_cache_dir: Path | None = None,
) -> FeatureBuildResult:
    started = time.perf_counter()
    cache_root = (feature_cache_dir or (output_dir / "feature_cache" if output_dir is not None else None))
    _, source_mapping = canonicalize_bar_frame(dataset)
    interval_evidence = _cycle_feature_interval_evidence(dataset, data_source=data_source)
    primary_interval_ms = int(interval_evidence["primary_interval_ms"])
    fixture_family_context = dict((data_source or {}).get("fixture_family_context") or {})
    fixture_family_context_sha256 = (data_source or {}).get("fixture_family_context_sha256")
    require_continuous_features = _cycle_feature_requires_continuous(
        dataset,
        data_source=data_source,
        interval_ms=primary_interval_ms,
    )
    records: list[dict[str, Any]] = []
    identity_records: list[dict[str, Any]] = []
    frames_by_feature_set: dict[str, pd.DataFrame] = {}
    for feature_set in spec.features.feature_sets:
        feature_started = time.perf_counter()
        preset_manifest = manifest_from_preset(feature_set, tests=FEATURE_MANIFEST_TESTS)
        identity = FeatureCacheIdentity(
            dataset_sha256=dataset_hash,
            feature_set_id=feature_set,
            feature_manifest_sha256=preset_manifest.manifest_sha256,
            builder_version=FEATURE_BUILDER_VERSION,
            interval_ms=primary_interval_ms,
            source_column_mapping=source_mapping,
            require_continuous=require_continuous_features,
            fixture_family_context_sha256=(
                str(fixture_family_context_sha256)
                if fixture_family_context_sha256 is not None
                else None
            ),
        )
        cache_status = "disabled"
        cached = load_feature_cache_artifact(cache_root, identity) if cache_root is not None else None
        if cached is not None:
            frame, cache_manifest = cached
            cache_status = "hit"
        else:
            materialized = materialize_registered_feature_set(
                dataset,
                feature_set_id=feature_set,
                interval_ms=primary_interval_ms,
                require_continuous=require_continuous_features,
            )
            frame = materialized.frame
            if cache_root is not None:
                cache_manifest = write_feature_cache_artifact(
                    cache_root,
                    identity,
                    frame=frame,
                    feature_columns=materialized.feature_columns,
                    availability_columns=materialized.availability_columns,
                    feature_manifest=materialized.built.result.manifest.to_payload(),
                    availability_report=materialized.built.result.availability_report.to_payload(),
                    materialization_scope=materialized.materialization_scope,
                    fixture_family_context=fixture_family_context,
                )
                cache_status = "miss"
            else:
                cache_manifest = {
                    **identity.to_payload(),
                    "feature_cache_key": identity.key(),
                    "row_count": int(len(frame)),
                    "feature_path": None,
                    "feature_frame_sha256": _frame_hash(frame),
                    "feature_artifact_sha256": None,
                    "feature_columns": list(materialized.feature_columns),
                    "availability_columns": list(materialized.availability_columns),
                    "feature_manifest": materialized.built.result.manifest.to_payload(),
                    "availability_report": materialized.built.result.availability_report.to_payload(),
                    "materialization_scope": materialized.materialization_scope,
                    "fixture_family_context": fixture_family_context,
                }
        frames_by_feature_set[feature_set] = frame
        record = _feature_build_record(
            feature_set_id=feature_set,
            cache_status=cache_status,
            cache_manifest=cache_manifest,
            frame=frame,
            elapsed_seconds=time.perf_counter() - feature_started,
        )
        records.append(record)
        identity_records.append(
            {
                "feature_set_id": feature_set,
                "feature_cache_key": record["feature_cache_key"],
                "feature_manifest_sha256": record["feature_manifest_sha256"],
                "feature_frame_sha256": record["feature_frame_sha256"],
                "interval_ms": record["interval_ms"],
                "row_count": record["row_count"],
            }
        )
    cache_status_counts = {
        status: sum(1 for record in records if record["cache_status"] == status)
        for status in sorted({str(record["cache_status"]) for record in records})
    }
    payload = {
        "feature_build_manifest_version": "historical-research-feature-build-v2",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "feature_computation_scope": "materialized_registered_feature_sets",
        "dataset_sha256": dataset_hash,
        **interval_evidence,
        "fixture_family_context_sha256": fixture_family_context_sha256,
        "fixture_family_context": fixture_family_context,
        "feature_continuity_required": require_continuous_features,
        "feature_gap_policy": (
            "continuous_completed_bar_series_required"
            if require_continuous_features
            else "segment_on_intentional_multi_window_fixture_gaps"
        ),
        "row_count": int(len(dataset)),
        "feature_cache_root": str(cache_root) if cache_root is not None else None,
        "feature_sets": records,
        "cache_status_counts": cache_status_counts,
        "runtime": {"elapsed_seconds": round(time.perf_counter() - started, 6)},
    }
    payload["feature_build_sha256"] = _stable_hash(
        {
            "feature_build_manifest_version": payload["feature_build_manifest_version"],
            "feature_computation_scope": payload["feature_computation_scope"],
            "dataset_sha256": dataset_hash,
            "primary_interval_ms": payload["primary_interval_ms"],
            "fixture_family_context_sha256": fixture_family_context_sha256,
            "feature_sets": identity_records,
        }
    )
    return FeatureBuildResult(manifest=payload, frames_by_feature_set=frames_by_feature_set)


def _cycle_feature_requires_continuous(
    dataset: pd.DataFrame,
    *,
    data_source: Mapping[str, Any] | None,
    interval_ms: int,
) -> bool:
    if not _cycle_data_source_is_intentional_multi_window_fixture(data_source):
        return True
    if "bar_time_ms" not in dataset.columns or len(dataset) <= 1:
        return True
    times = pd.to_numeric(dataset["bar_time_ms"], errors="coerce").dropna().astype("int64").sort_values()
    if len(times) <= 1:
        return True
    return not bool((times.diff().iloc[1:] > int(interval_ms)).any())


def _cycle_data_source_is_intentional_multi_window_fixture(data_source: Mapping[str, Any] | None) -> bool:
    if not isinstance(data_source, Mapping):
        return False
    derivation = data_source.get("fixture_derivation")
    if not isinstance(derivation, Mapping):
        return False
    derivation_type = str(derivation.get("derivation_type") or "")
    window_labels = derivation.get("window_labels")
    return derivation_type == "multi_window_public_archive_selection" and bool(window_labels)


def _feature_set_prediction_overlays(
    overlays: tuple[MaterializedPredictionOverlaySpec, ...],
) -> tuple[MaterializedPredictionOverlaySpec, ...]:
    return tuple(overlay for overlay in overlays if overlay.scope == "feature_set")


def _candidate_prediction_overlays(
    overlays: tuple[MaterializedPredictionOverlaySpec, ...],
) -> tuple[MaterializedPredictionOverlaySpec, ...]:
    return tuple(overlay for overlay in overlays if overlay.scope == "candidate")


def _apply_materialized_prediction_overlays(
    feature_build: FeatureBuildResult,
    *,
    spec: HistoricalResearchCycleSpec,
) -> FeatureBuildResult:
    frames = {feature_set_id: frame.copy() for feature_set_id, frame in feature_build.frames_by_feature_set.items()}
    manifest = dict(feature_build.manifest)
    records = [dict(record) for record in manifest.get("feature_sets", [])]
    overlay_records: list[dict[str, Any]] = []
    for overlay in _feature_set_prediction_overlays(spec.features.materialized_prediction_overlays):
        feature_set_id = overlay.feature_set_id
        if feature_set_id not in frames:
            raise ValueError(f"materialized_prediction_overlay_missing_feature_frame:{feature_set_id}")
        if not overlay.predictions_path.exists():
            raise ValueError(f"materialized_prediction_overlay_missing_predictions:{overlay.predictions_path}")
        predictions = pd.read_parquet(overlay.predictions_path)
        overlay_manifest = _materialized_prediction_overlay_manifest(overlay.manifest_path)
        frame_before = frames[feature_set_id]
        frame_after, evidence = _merge_materialized_prediction_overlay(
            frame_before,
            predictions,
            feature_set_id=feature_set_id,
            kind=overlay.kind,
            join_key=overlay.join_key,
        )
        evidence.update(
            {
                "overlay_scope": "feature_set",
                "predictions_path": str(overlay.predictions_path),
                "predictions_sha256": _file_sha256(overlay.predictions_path),
                "manifest_path": str(overlay.manifest_path) if overlay.manifest_path is not None else None,
                "manifest_sha256": _file_sha256(overlay.manifest_path) if overlay.manifest_path is not None else None,
                "manifest_version": overlay_manifest.get("knn_study_manifest_version"),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
        frames[feature_set_id] = frame_after
        overlay_records.append(evidence)
        _update_feature_record_for_overlay(records, feature_set_id=feature_set_id, frame=frame_after, evidence=evidence)

    identity_records = [
        {
            "feature_set_id": record["feature_set_id"],
            "feature_cache_key": record.get("feature_cache_key"),
            "feature_manifest_sha256": record.get("feature_manifest_sha256"),
            "feature_frame_sha256": record.get("feature_frame_sha256"),
            "interval_ms": record.get("interval_ms"),
            "row_count": record.get("row_count"),
            "materialized_prediction_overlays": record.get("materialized_prediction_overlays", []),
        }
        for record in records
    ]
    manifest["feature_computation_scope"] = "materialized_registered_feature_sets_with_prediction_overlays"
    manifest["feature_sets"] = records
    manifest["materialized_prediction_overlay_count"] = len(overlay_records)
    manifest["materialized_prediction_overlays"] = overlay_records
    manifest["feature_build_sha256"] = _stable_hash(
        {
            "feature_build_manifest_version": manifest["feature_build_manifest_version"],
            "feature_computation_scope": manifest["feature_computation_scope"],
            "dataset_sha256": manifest["dataset_sha256"],
            "primary_interval_ms": manifest["primary_interval_ms"],
            "fixture_family_context_sha256": manifest.get("fixture_family_context_sha256"),
            "feature_sets": identity_records,
        }
    )
    return FeatureBuildResult(manifest=manifest, frames_by_feature_set=frames)


def _candidate_scoped_prediction_overlay_context(
    feature_build: FeatureBuildResult,
    *,
    spec: HistoricalResearchCycleSpec,
    candidates: list[dict[str, Any]],
) -> CandidateScopedOverlayContext:
    overlays = _candidate_prediction_overlays(spec.features.materialized_prediction_overlays)
    if not overlays:
        return CandidateScopedOverlayContext(
            feature_build_manifest=dict(feature_build.manifest),
            frames_by_candidate_id={},
            records_by_candidate_id={},
            evidence_by_candidate_id={},
        )

    candidates_by_key = _candidate_overlay_match_index(candidates)
    frames_by_candidate_id: dict[str, pd.DataFrame] = {}
    records_by_candidate_id: dict[str, dict[str, Any]] = {}
    evidence_by_candidate_id: dict[str, dict[str, Any]] = {}
    overlay_records: list[dict[str, Any]] = []
    for overlay in overlays:
        match_key = overlay.candidate_id or overlay.candidate_cache_key or ""
        candidate = candidates_by_key.get(match_key)
        if candidate is None:
            raise ValueError(f"materialized_prediction_overlay_candidate_unmatched:{match_key}")
        candidate_id = str(candidate["candidate_id"])
        if candidate_id in frames_by_candidate_id:
            raise ValueError(f"duplicate materialized prediction overlay candidate: {candidate_id}")
        feature_set_id = overlay.feature_set_id
        if feature_set_id != str(candidate.get("feature_set_id") or ""):
            raise ValueError(f"materialized_prediction_overlay_candidate_feature_set_mismatch:{candidate_id}")
        if feature_set_id not in feature_build.frames_by_feature_set:
            raise ValueError(f"materialized_prediction_overlay_missing_feature_frame:{feature_set_id}")
        if not overlay.predictions_path.exists():
            raise ValueError(f"materialized_prediction_overlay_missing_predictions:{overlay.predictions_path}")
        predictions = pd.read_parquet(overlay.predictions_path)
        overlay_manifest = _materialized_prediction_overlay_manifest(overlay.manifest_path)
        frame_after, evidence = _merge_materialized_prediction_overlay(
            feature_build.frames_by_feature_set[feature_set_id],
            predictions,
            feature_set_id=feature_set_id,
            kind=overlay.kind,
            join_key=overlay.join_key,
        )
        evidence.update(
            {
                "overlay_scope": "candidate",
                "candidate_id": candidate_id,
                "candidate_cache_key": str(candidate.get("candidate_cache_key") or candidate_id),
                "materialized_candidate_id": overlay.materialized_candidate_id,
                "candidate_strategy_id": str(candidate.get("strategy_id") or ""),
                "candidate_holding_window": str(candidate.get("holding_window") or ""),
                "predictions_path": str(overlay.predictions_path),
                "predictions_sha256": _file_sha256(overlay.predictions_path),
                "manifest_path": str(overlay.manifest_path) if overlay.manifest_path is not None else None,
                "manifest_sha256": _file_sha256(overlay.manifest_path) if overlay.manifest_path is not None else None,
                "manifest_version": overlay_manifest.get("knn_study_manifest_version"),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
        candidate_record = _candidate_scoped_feature_record(
            feature_build.manifest,
            feature_set_id=feature_set_id,
            frame=frame_after,
            evidence=evidence,
        )
        evidence["pre_overlay_feature_frame_sha256"] = candidate_record.get("pre_overlay_feature_frame_sha256")
        evidence["post_overlay_feature_frame_sha256"] = candidate_record.get("feature_frame_sha256")
        evidence["candidate_feature_frame_sha256"] = candidate_record.get("feature_frame_sha256")
        frames_by_candidate_id[candidate_id] = frame_after
        records_by_candidate_id[candidate_id] = candidate_record
        evidence_by_candidate_id[candidate_id] = dict(evidence)
        overlay_records.append(dict(evidence))

    manifest = dict(feature_build.manifest)
    manifest["feature_computation_scope"] = _candidate_overlay_feature_computation_scope(
        str(manifest.get("feature_computation_scope") or "materialized_registered_feature_sets")
    )
    manifest["candidate_scoped_materialized_prediction_overlay_count"] = len(overlay_records)
    manifest["candidate_scoped_materialized_prediction_overlays"] = overlay_records
    manifest["feature_build_sha256"] = _feature_build_hash_with_candidate_overlays(manifest)
    return CandidateScopedOverlayContext(
        feature_build_manifest=manifest,
        frames_by_candidate_id=frames_by_candidate_id,
        records_by_candidate_id=records_by_candidate_id,
        evidence_by_candidate_id=evidence_by_candidate_id,
    )


def _materialized_prediction_overlay_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        raise ValueError(f"materialized_prediction_overlay_missing_manifest:{path}")
    payload = _read_json(path)
    if payload.get("research_only") is not True or payload.get("observe_only") is not True:
        raise ValueError("materialized_prediction_overlay_manifest_not_research_observe_only")
    if payload.get("promotion_ready") is not False:
        raise ValueError("materialized_prediction_overlay_manifest_promotion_ready")
    if payload.get("split_safety_passed") is False:
        raise ValueError("materialized_prediction_overlay_manifest_split_safety_failed")
    return payload


def _merge_materialized_prediction_overlay(
    frame: pd.DataFrame,
    predictions: pd.DataFrame,
    *,
    feature_set_id: str,
    kind: str,
    join_key: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    missing = [column for column in REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS if column not in predictions.columns]
    if missing:
        raise ValueError(f"materialized_prediction_overlay_missing_columns:{','.join(missing)}")
    if join_key not in predictions.columns:
        raise ValueError(f"materialized_prediction_overlay_missing_join_key:{join_key}")
    if len(predictions) != len(frame):
        raise ValueError(f"materialized_prediction_overlay_row_count_mismatch:{feature_set_id}")
    _validate_materialized_prediction_split_safety(predictions)

    base = frame.copy()
    if join_key == "source_row_index" and join_key not in base.columns:
        base[join_key] = range(len(base))
    if join_key not in base.columns:
        raise ValueError(f"materialized_prediction_overlay_feature_frame_missing_join_key:{join_key}")
    if base[join_key].isna().any() or predictions[join_key].isna().any():
        raise ValueError(f"materialized_prediction_overlay_null_join_key:{join_key}")
    if base[join_key].duplicated().any() or predictions[join_key].duplicated().any():
        raise ValueError(f"materialized_prediction_overlay_duplicate_join_key:{join_key}")
    if set(base[join_key].tolist()) != set(predictions[join_key].tolist()):
        raise ValueError(f"materialized_prediction_overlay_unmatched_rows:{feature_set_id}")

    overlay_columns = [column for column in REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS if column != join_key]
    selected = predictions[[join_key, *overlay_columns]].copy()
    drop_existing = [column for column in overlay_columns if column in base.columns]
    if drop_existing:
        base = base.drop(columns=drop_existing)
    merged = base.merge(selected, on=join_key, how="left", sort=False, validate="one_to_one")
    if len(merged) != len(base):
        raise ValueError(f"materialized_prediction_overlay_merge_row_count_changed:{feature_set_id}")
    if merged[join_key].isna().any():
        raise ValueError(f"materialized_prediction_overlay_unmatched_rows:{feature_set_id}")
    return merged, {
        "overlay_version": "historical-cycle-materialized-prediction-overlay-v1",
        "feature_set_id": feature_set_id,
        "kind": kind,
        "join_key": join_key,
        "row_count": int(len(merged)),
        "overlay_column_count": int(len(overlay_columns) + 1),
        "overlay_columns": [join_key, *overlay_columns],
        "raw_knn_accepted_row_count": int(_accepted_knn_rows(merged).sum()),
        "split_safety_rule": "neighbor_min_source_index <= neighbor_max_source_index <= hmm_fit_end_row < source_row_index",
        "split_safety_passed": True,
    }


def _validate_materialized_prediction_split_safety(predictions: pd.DataFrame) -> None:
    accepted = _accepted_knn_rows(predictions)
    if not accepted.any():
        return
    numeric = {
        column: pd.to_numeric(predictions[column], errors="coerce")
        for column in ("neighbor_min_source_index", "neighbor_max_source_index", "hmm_fit_end_row", "source_row_index")
    }
    safe = (
        numeric["neighbor_min_source_index"].notna()
        & numeric["neighbor_max_source_index"].notna()
        & numeric["hmm_fit_end_row"].notna()
        & numeric["source_row_index"].notna()
        & (numeric["neighbor_min_source_index"] >= 0)
        & (numeric["neighbor_max_source_index"] >= 0)
        & (numeric["hmm_fit_end_row"] >= 0)
        & (numeric["source_row_index"] >= 0)
        & (numeric["neighbor_min_source_index"] <= numeric["neighbor_max_source_index"])
        & (numeric["neighbor_max_source_index"] <= numeric["hmm_fit_end_row"])
        & (numeric["hmm_fit_end_row"] < numeric["source_row_index"])
    )
    if bool((accepted & ~safe).any()):
        raise ValueError("materialized_prediction_overlay_split_safety_failed")


def _accepted_knn_rows(frame: pd.DataFrame) -> pd.Series:
    accepted = frame["accepted_by_knn"].map(_strict_bool_flag)
    skip_clear = frame["knn_skip_reason"].map(_skip_reason_clear)
    return accepted & skip_clear


def _strict_bool_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return bool(value)
    if pd.isna(value):
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y"}


def _skip_reason_clear(value: Any) -> bool:
    if value is None or pd.isna(value):
        return True
    return str(value).strip().lower() in {"", "none", "nan", "null"}


def _update_feature_record_for_overlay(
    records: list[dict[str, Any]],
    *,
    feature_set_id: str,
    frame: pd.DataFrame,
    evidence: Mapping[str, Any],
) -> None:
    for record in records:
        if str(record.get("feature_set_id")) != feature_set_id:
            continue
        overlays = list(record.get("materialized_prediction_overlays") or [])
        previous_hash = record.get("feature_frame_sha256")
        frame_hash = _frame_hash(frame)
        if isinstance(evidence, dict):
            evidence.setdefault("pre_overlay_feature_frame_sha256", previous_hash)
            evidence.setdefault("post_overlay_feature_frame_sha256", frame_hash)
        overlays.append(dict(evidence))
        record["pre_overlay_feature_frame_sha256"] = previous_hash
        record["feature_frame_sha256"] = frame_hash
        record["column_count"] = int(len(frame.columns))
        record["materialized_prediction_overlay_count"] = len(overlays)
        record["materialized_prediction_overlays"] = overlays
        record["materialized_prediction_columns"] = sorted(
            {
                column
                for overlay in overlays
                for column in overlay.get("overlay_columns", [])
            }
        )
        record["feature_artifact_sha256"] = None
        record["cache_status"] = f"{record.get('cache_status')}_with_prediction_overlay"
        return
    raise ValueError(f"materialized_prediction_overlay_missing_feature_record:{feature_set_id}")


def _candidate_overlay_match_index(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        candidate_cache_key = str(candidate.get("candidate_cache_key") or "")
        for key in (candidate_id, candidate_cache_key):
            if not key:
                continue
            existing = by_key.get(key)
            if existing is not None and str(existing.get("candidate_id")) != candidate_id:
                raise ValueError(f"duplicate materialized prediction overlay candidate key: {key}")
            by_key[key] = candidate
    return by_key


def _candidate_scoped_feature_record(
    feature_build_manifest: Mapping[str, Any],
    *,
    feature_set_id: str,
    frame: pd.DataFrame,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    for record in feature_build_manifest.get("feature_sets", []):
        if isinstance(record, Mapping) and str(record.get("feature_set_id")) == feature_set_id:
            candidate_record = dict(record)
            _update_feature_record_for_overlay(
                [candidate_record],
                feature_set_id=feature_set_id,
                frame=frame,
                evidence=evidence,
            )
            candidate_record["materialized_prediction_overlay_scope"] = "candidate"
            return candidate_record
    raise ValueError(f"materialized_prediction_overlay_missing_feature_record:{feature_set_id}")


def _candidate_overlay_feature_computation_scope(current_scope: str) -> str:
    if current_scope.endswith("_with_candidate_prediction_overlays"):
        return current_scope
    return f"{current_scope}_with_candidate_prediction_overlays"


def _feature_build_hash_with_candidate_overlays(manifest: Mapping[str, Any]) -> str:
    identity_records = [
        {
            "feature_set_id": record["feature_set_id"],
            "feature_cache_key": record.get("feature_cache_key"),
            "feature_manifest_sha256": record.get("feature_manifest_sha256"),
            "feature_frame_sha256": record.get("feature_frame_sha256"),
            "interval_ms": record.get("interval_ms"),
            "row_count": record.get("row_count"),
            "materialized_prediction_overlays": record.get("materialized_prediction_overlays", []),
        }
        for record in manifest.get("feature_sets", [])
        if isinstance(record, Mapping)
    ]
    return _stable_hash(
        {
            "feature_build_manifest_version": manifest["feature_build_manifest_version"],
            "feature_computation_scope": manifest["feature_computation_scope"],
            "dataset_sha256": manifest["dataset_sha256"],
            "primary_interval_ms": manifest["primary_interval_ms"],
            "fixture_family_context_sha256": manifest.get("fixture_family_context_sha256"),
            "feature_sets": identity_records,
            "candidate_scoped_materialized_prediction_overlays": manifest.get(
                "candidate_scoped_materialized_prediction_overlays",
                [],
            ),
        }
    )


def _cycle_feature_interval_evidence(
    dataset: pd.DataFrame,
    *,
    data_source: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = dict(data_source or {})
    declared_raw = _optional_text(source.get("base_interval"))
    declared_ms = (
        _parse_interval_ms(declared_raw, context="data_source.base_interval")
        if declared_raw is not None
        else None
    )
    source_interval_raw = _constant_dataset_interval(dataset)
    source_interval_ms = (
        _parse_interval_ms(source_interval_raw, context="dataset.source_interval")
        if source_interval_raw is not None
        else None
    )
    inferred_interval_ms = _infer_uniform_bar_interval_ms(dataset)

    if declared_ms is not None:
        if source_interval_ms is not None and source_interval_ms != declared_ms:
            raise ValueError(
                f"cycle_feature_interval_mismatch:base_interval:{declared_ms}:source_interval:{source_interval_ms}"
            )
        if inferred_interval_ms is not None and inferred_interval_ms != declared_ms:
            raise ValueError(
                f"cycle_feature_interval_mismatch:base_interval:{declared_ms}:bar_time_diff:{inferred_interval_ms}"
            )
        interval_ms = declared_ms
        interval_source = "data_source.base_interval"
    elif source_interval_ms is not None:
        if inferred_interval_ms is not None and inferred_interval_ms != source_interval_ms:
            raise ValueError(
                f"cycle_feature_interval_mismatch:source_interval:{source_interval_ms}:bar_time_diff:{inferred_interval_ms}"
            )
        interval_ms = source_interval_ms
        interval_source = "dataset.source_interval"
    elif inferred_interval_ms is not None:
        interval_ms = inferred_interval_ms
        interval_source = "dataset.bar_time_diff"
    else:
        interval_ms = DEFAULT_INTERVAL_MS
        interval_source = "default"

    return {
        "primary_interval_ms": int(interval_ms),
        "primary_interval_source": interval_source,
        "declared_base_interval": declared_raw,
        "dataset_source_interval": source_interval_raw,
        "inferred_bar_interval_ms": inferred_interval_ms,
        "default_interval_ms": int(DEFAULT_INTERVAL_MS),
    }


def _constant_dataset_interval(dataset: pd.DataFrame) -> str | None:
    if "source_interval" not in dataset.columns:
        return None
    values = sorted(
        {
            str(value).strip()
            for value in dataset["source_interval"].dropna().tolist()
            if str(value).strip()
        }
    )
    if not values:
        return None
    if len(values) > 1:
        raise ValueError(f"cycle_feature_interval_mixed_source_intervals:{','.join(values)}")
    return values[0]


def _infer_uniform_bar_interval_ms(dataset: pd.DataFrame) -> int | None:
    time_column = next(
        (column for column in ("bar_time_ms", "signal_bar_time_ms", "time_ms") if column in dataset.columns),
        None,
    )
    if time_column is None:
        return None
    times = pd.to_numeric(dataset[time_column], errors="coerce").dropna()
    if len(times) < 2:
        return None
    ordered = times.astype("int64").drop_duplicates().sort_values(kind="mergesort").reset_index(drop=True)
    diffs = ordered.diff().iloc[1:]
    positive_diffs = sorted(
        {
            int(value)
            for value in diffs.tolist()
            if pd.notna(value) and math.isfinite(float(value)) and int(value) > 0
        }
    )
    if len(positive_diffs) == 1:
        return positive_diffs[0]
    return None


def _parse_interval_ms(value: object, *, context: str) -> int:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if not math.isfinite(numeric) or numeric % 1:
            raise ValueError(f"unsupported_cycle_feature_interval:{context}:{value}")
        interval_ms = int(numeric)
        if interval_ms <= 0:
            raise ValueError(f"unsupported_cycle_feature_interval:{context}:{value}")
        return interval_ms
    text = str(value).strip().lower()
    if not text:
        raise ValueError(f"unsupported_cycle_feature_interval:{context}:empty")
    if text.isdigit():
        interval_ms = int(text)
        if interval_ms <= 0:
            raise ValueError(f"unsupported_cycle_feature_interval:{context}:{text}")
        return interval_ms
    prefix_length = 0
    while prefix_length < len(text) and text[prefix_length].isdigit():
        prefix_length += 1
    digits = text[:prefix_length]
    unit = text[prefix_length:].strip()
    if not digits or not unit:
        raise ValueError(f"unsupported_cycle_feature_interval:{context}:{text}")
    multiplier = {
        "ms": 1,
        "s": 1_000,
        "sec": 1_000,
        "secs": 1_000,
        "second": 1_000,
        "seconds": 1_000,
        "m": 60_000,
        "min": 60_000,
        "mins": 60_000,
        "minute": 60_000,
        "minutes": 60_000,
        "h": 3_600_000,
        "hr": 3_600_000,
        "hrs": 3_600_000,
        "hour": 3_600_000,
        "hours": 3_600_000,
        "d": 86_400_000,
        "day": 86_400_000,
        "days": 86_400_000,
    }.get(unit)
    if multiplier is None:
        raise ValueError(f"unsupported_cycle_feature_interval:{context}:{text}")
    interval_ms = int(digits) * int(multiplier)
    if interval_ms <= 0:
        raise ValueError(f"unsupported_cycle_feature_interval:{context}:{text}")
    return interval_ms


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _feature_build_record(
    *,
    feature_set_id: str,
    cache_status: str,
    cache_manifest: Mapping[str, Any],
    frame: pd.DataFrame,
    elapsed_seconds: float,
) -> dict[str, Any]:
    feature_manifest = dict(cache_manifest.get("feature_manifest") or {})
    availability_report = dict(cache_manifest.get("availability_report") or {})
    fixture_family_context = dict(cache_manifest.get("fixture_family_context") or {})
    return {
        "feature_set_id": feature_set_id,
        "status": "cache_hit" if cache_status == "hit" else "built",
        "cache_status": cache_status,
        "feature_cache_key": cache_manifest.get("feature_cache_key"),
        "feature_cache_version": cache_manifest.get("cache_version"),
        "feature_path": cache_manifest.get("feature_path"),
        "cache_manifest_path": _cache_manifest_path_from_feature_path(cache_manifest.get("feature_path")),
        "feature_frame_sha256": cache_manifest.get("feature_frame_sha256"),
        "feature_artifact_sha256": cache_manifest.get("feature_artifact_sha256"),
        "feature_manifest_sha256": feature_manifest.get("manifest_sha256") or cache_manifest.get("feature_manifest_sha256"),
        "builder_version": cache_manifest.get("builder_version"),
        "interval_ms": int(cache_manifest.get("interval_ms") or DEFAULT_INTERVAL_MS),
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "feature_columns": list(cache_manifest.get("feature_columns") or feature_manifest.get("feature_columns") or ()),
        "availability_columns": list(cache_manifest.get("availability_columns") or feature_manifest.get("availability_columns") or ()),
        "availability_report": availability_report,
        "source_column_mapping": dict(cache_manifest.get("source_column_mapping") or {}),
        "materialization_scope": cache_manifest.get("materialization_scope"),
        "fixture_family_context_sha256": cache_manifest.get("fixture_family_context_sha256"),
        "fixture_family_joined_families": list(fixture_family_context.get("joined_families") or []),
        "fixture_family_joined_columns": list(fixture_family_context.get("joined_columns") or []),
        "fixture_family_context": fixture_family_context,
        "fit_scope": feature_manifest.get("fit_scope"),
        "train_only_transform_fit": False,
        "missingness_rate": _feature_set_missingness(frame),
        "elapsed_seconds": round(float(elapsed_seconds), 6),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }


def _cache_manifest_path_from_feature_path(feature_path: object) -> str | None:
    if feature_path is None:
        return None
    return str(Path(str(feature_path)).parent / "feature_cache_manifest.json")


def _candidate_feature_frame(
    frames_by_feature_set: Mapping[str, pd.DataFrame],
    candidate: Mapping[str, Any],
    candidate_overlay_context: CandidateScopedOverlayContext | None = None,
) -> pd.DataFrame:
    candidate_id = str(candidate.get("candidate_id") or "")
    if candidate_overlay_context is not None and candidate_id in candidate_overlay_context.frames_by_candidate_id:
        return candidate_overlay_context.frames_by_candidate_id[candidate_id]
    feature_set_id = str(candidate["feature_set_id"])
    if feature_set_id not in frames_by_feature_set:
        raise ValueError(f"missing_materialized_feature_frame:{feature_set_id}")
    return frames_by_feature_set[feature_set_id]


def _candidate_feature_record(
    feature_build_manifest: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_overlay_context: CandidateScopedOverlayContext | None = None,
) -> Mapping[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or "")
    if candidate_overlay_context is not None and candidate_id in candidate_overlay_context.records_by_candidate_id:
        return candidate_overlay_context.records_by_candidate_id[candidate_id]
    feature_set_id = str(candidate["feature_set_id"])
    for record in feature_build_manifest.get("feature_sets", []):
        if isinstance(record, Mapping) and str(record.get("feature_set_id")) == feature_set_id:
            return record
    raise ValueError(f"missing_materialized_feature_record:{feature_set_id}")


def _candidate_with_materialized_overlay_evidence(
    candidate: dict[str, Any],
    feature_build_manifest: Mapping[str, Any],
    candidate_overlay_context: CandidateScopedOverlayContext | None,
) -> dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or "")
    evidence: Mapping[str, Any] | None = None
    if candidate_overlay_context is not None and candidate_id in candidate_overlay_context.evidence_by_candidate_id:
        evidence = candidate_overlay_context.evidence_by_candidate_id[candidate_id]
    else:
        evidence = _feature_set_materialized_overlay_evidence(feature_build_manifest, candidate)
    if not isinstance(evidence, Mapping):
        return candidate
    enriched = dict(candidate)
    enriched["materialized_prediction_overlay_evidence"] = dict(evidence)
    return enriched


def _feature_set_materialized_overlay_evidence(
    feature_build_manifest: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    feature_set_id = str(candidate.get("feature_set_id") or "")
    for record in feature_build_manifest.get("feature_sets", []):
        if not isinstance(record, Mapping) or str(record.get("feature_set_id") or "") != feature_set_id:
            continue
        overlays = record.get("materialized_prediction_overlays")
        if not isinstance(overlays, list) or not overlays:
            return None
        evidence = dict(overlays[0])
        evidence.setdefault("overlay_scope", "feature_set")
        evidence["candidate_id"] = str(candidate.get("candidate_id") or "")
        evidence["candidate_cache_key"] = str(candidate.get("candidate_cache_key") or candidate.get("candidate_id") or "")
        evidence.setdefault("materialized_candidate_id", None)
        evidence["candidate_feature_frame_sha256"] = str(record.get("feature_frame_sha256") or "")
        evidence.setdefault("post_overlay_feature_frame_sha256", record.get("feature_frame_sha256"))
        evidence.setdefault("pre_overlay_feature_frame_sha256", record.get("pre_overlay_feature_frame_sha256"))
        return evidence
    return None


def _validated_feature_frame_hash(
    frame: pd.DataFrame,
    feature_record: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> str:
    frame_hash = _frame_hash(frame)
    expected_hash = str(feature_record.get("feature_frame_sha256") or "")
    if not expected_hash:
        raise ValueError(f"missing_feature_frame_hash:{candidate['feature_set_id']}")
    if frame_hash != expected_hash:
        raise ValueError(f"feature_frame_hash_mismatch:{candidate['feature_set_id']}")
    return frame_hash


def _candidate_space(spec: HistoricalResearchCycleSpec) -> list[dict[str, Any]]:
    if spec.optimizer.search_spaces:
        return _with_baseline_comparators(_search_space_candidates(spec))

    return _with_baseline_comparators(_metadata_default_candidates(spec))


def _metadata_default_candidates(spec: HistoricalResearchCycleSpec) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for strategy_id in spec.strategies:
        for feature_set_id in spec.features.feature_sets:
            for holding_window in spec.holding_windows:
                for exit_policy in spec.exits.exit_policies:
                    if not _is_candidate_supported(strategy_id, feature_set_id, holding_window):
                        continue
                    default_payload = _candidate_payload(
                        CandidateConfig(
                            strategy_id=strategy_id,
                            parameters={},
                            feature_set_id=feature_set_id,
                            holding_window=holding_window,
                            exit_policy_id=str(exit_policy["exit_policy_id"]),
                            exit_policy_params=dict(exit_policy.get("exit_policy_params") or {}),
                        ),
                        search_method="metadata_default_seed",
                        source="metadata_default_seed",
                        search_space_index=None,
                        declared_strategy_ids=spec.strategies,
                        exit_policy=exit_policy,
                    )
                    _append_unique_candidate(candidates, default_payload, seen)
                    if strategy_id == NO_TRADE_BASELINE_STRATEGY_ID:
                        continue
                    space = SearchSpace(
                        strategy_id=strategy_id,
                        parameters=search_parameter_space_for_holding_window(strategy_id, holding_window),
                        feature_set_id=feature_set_id,
                        holding_window=holding_window,
                        exit_policy_id=str(exit_policy["exit_policy_id"]),
                        exit_policy_params=dict(exit_policy.get("exit_policy_params") or {}),
                    )
                    if not space.parameters:
                        continue
                    sample_budget = min(DEFAULT_METADATA_SEARCH_SAMPLE_CAP, max(0, int(spec.optimizer.max_candidates_per_strategy)))
                    if sample_budget <= 0:
                        continue
                    metadata_candidate_count = 0
                    for config in space.iter_grid():
                        if metadata_candidate_count >= sample_budget:
                            break
                        _validate_explicit_candidate_config(config)
                        payload = _candidate_payload(
                            config,
                            search_method="metadata_capped_grid",
                            source="metadata_default_search",
                            search_space_index=None,
                            declared_strategy_ids=spec.strategies,
                            exit_policy=exit_policy,
                        )
                        if _append_unique_candidate(candidates, payload, seen):
                            metadata_candidate_count += 1
    return candidates


def _append_unique_candidate(candidates: list[dict[str, Any]], payload: dict[str, Any], seen: set[str]) -> bool:
    candidate_id = str(payload["candidate_id"])
    if candidate_id in seen:
        return False
    seen.add(candidate_id)
    candidates.append(payload)
    return True


def _search_space_candidates(spec: HistoricalResearchCycleSpec) -> list[dict[str, Any]]:
    search_method = _candidate_search_method(spec)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for search_space_index, payload in enumerate(spec.optimizer.search_spaces):
        space = SearchSpace.from_payload(payload)
        expanded = space.expand(
            method=search_method,
            max_candidates=spec.optimizer.max_candidates_per_strategy,
        )
        for config in expanded:
            _validate_explicit_candidate_config(config)
            payload = _candidate_payload(
                config,
                search_method=search_method,
                source="optimizer_search_space",
                search_space_index=search_space_index,
                declared_strategy_ids=spec.strategies,
            )
            candidate_id = str(payload["candidate_id"])
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            candidates.append(payload)
    return candidates


def _candidate_search_method(spec: HistoricalResearchCycleSpec) -> str:
    for method in spec.optimizer.method_sequence:
        normalized = str(method).lower()
        normalized = SEARCH_METHOD_ALIASES.get(normalized, normalized)
        if normalized in SUPPORTED_SEARCH_METHODS:
            return normalized
    return "grid"


def _candidate_payload(
    config: CandidateConfig,
    *,
    search_method: str,
    source: str,
    search_space_index: int | None,
    declared_strategy_ids: tuple[str, ...] | list[str] = (),
    exit_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    exit_policy_record = _candidate_exit_policy_record(config, exit_policy)
    specified_parameters = dict(sorted(dict(config.parameters).items()))
    resolved_parameters = _resolved_candidate_parameters(config.strategy_id, config.holding_window, specified_parameters)
    resolved_config = CandidateConfig(
        strategy_id=config.strategy_id,
        parameters=resolved_parameters,
        feature_set_id=config.feature_set_id,
        holding_window=config.holding_window,
        exit_policy_id=str(exit_policy_record["exit_policy_id"]),
        exit_policy_params=dict(exit_policy_record.get("exit_policy_params") or {}),
    )
    candidate_id = resolved_config.cache_key()
    comparator_role = _comparator_role(config.strategy_id)
    metadata = metadata_for_strategy(config.strategy_id)
    return {
        "candidate_id": candidate_id,
        "candidate_cache_key": candidate_id,
        "human_readable_candidate_id": f"{config.strategy_id}__{config.feature_set_id}__{config.holding_window}__{candidate_id[:12]}",
        "strategy_id": config.strategy_id,
        "strategy_version": "v1",
        "strategy_role": "baseline_comparator" if comparator_role != "research_candidate" else "research_candidate",
        "comparator_role": comparator_role,
        "baseline_group_key": _baseline_group_key(
            config.feature_set_id,
            config.holding_window,
            str(exit_policy_record["exit_policy_id"]),
            dict(exit_policy_record.get("exit_policy_params") or {}),
        ),
        "strategy_metadata_sha256": strategy_metadata_sha256(config.strategy_id),
        "strategy_metadata_strategy_id": metadata.strategy_id,
        "feature_set_id": config.feature_set_id,
        "holding_window": config.holding_window,
        "exit_policy_id": str(exit_policy_record["exit_policy_id"]),
        "exit_policy_params": dict(exit_policy_record.get("exit_policy_params") or {}),
        "exit_policy_params_json": _stable_json(dict(exit_policy_record.get("exit_policy_params") or {})),
        "exit_policy_source": str(exit_policy_record.get("exit_policy_source") or "configured_exit_policy"),
        "target_return": exit_policy_record.get("target_return"),
        "stop_return": exit_policy_record.get("stop_return"),
        "parameters": resolved_parameters,
        "resolved_parameters": resolved_parameters,
        "specified_parameters": specified_parameters,
        "parameter_resolution_policy": "holding_window_defaults_plus_explicit_overrides",
        "is_default_parameter_candidate": resolved_parameters == defaults_for_holding_window(config.strategy_id, config.holding_window),
        "strategy_requested_in_spec": config.strategy_id in set(declared_strategy_ids),
        "comparator_injected": source.endswith("_injected"),
        "search_method": search_method,
        "candidate_source": source,
        "search_space_index": search_space_index,
    }


def _with_baseline_comparators(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {str(candidate["candidate_id"]) for candidate in candidates}
    result = list(candidates)
    groups = sorted(
        {
            (
                str(candidate["feature_set_id"]),
                str(candidate["holding_window"]),
                str(candidate.get("exit_policy_id", "fixed_holding_window")),
                str(candidate.get("exit_policy_params_json", "{}")),
            )
            for candidate in result
        }
    )
    for feature_set_id, holding_window, exit_policy_id, exit_policy_params_json in groups:
        exit_policy = {
            "exit_policy_id": exit_policy_id,
            "exit_policy_params": json.loads(exit_policy_params_json),
            "exit_policy_source": "baseline_comparator_exit_policy_inherited",
        }
        transparent_strategy_id = _transparent_baseline_strategy_for_group(feature_set_id, holding_window)
        if _is_candidate_supported(NO_TRADE_BASELINE_STRATEGY_ID, feature_set_id, holding_window):
            payload = _candidate_payload(
                CandidateConfig(
                    strategy_id=NO_TRADE_BASELINE_STRATEGY_ID,
                    parameters={},
                    feature_set_id=feature_set_id,
                    holding_window=holding_window,
                    exit_policy_id=exit_policy_id,
                    exit_policy_params=dict(exit_policy["exit_policy_params"]),
                ),
                search_method="baseline_comparator",
                source="no_trade_comparator_injected",
                search_space_index=None,
                exit_policy=exit_policy,
            )
            if str(payload["candidate_id"]) not in seen:
                seen.add(str(payload["candidate_id"]))
                result.append(payload)
        if transparent_strategy_id is not None:
            payload = _candidate_payload(
                CandidateConfig(
                    strategy_id=transparent_strategy_id,
                    parameters={},
                    feature_set_id=feature_set_id,
                    holding_window=holding_window,
                    exit_policy_id=exit_policy_id,
                    exit_policy_params=dict(exit_policy["exit_policy_params"]),
                ),
                search_method="transparent_default_comparator",
                source="transparent_default_comparator_injected",
                search_space_index=None,
                exit_policy=exit_policy,
            )
            if str(payload["candidate_id"]) not in seen:
                seen.add(str(payload["candidate_id"]))
                result.append(payload)
    for candidate in list(result):
        strategy_id = str(candidate["strategy_id"])
        if strategy_id not in TRANSPARENT_BASELINE_STRATEGY_IDS:
            continue
        payload = _candidate_payload(
            CandidateConfig(
                strategy_id=strategy_id,
                parameters={},
                feature_set_id=str(candidate["feature_set_id"]),
                holding_window=str(candidate["holding_window"]),
                exit_policy_id=str(candidate.get("exit_policy_id", "fixed_holding_window")),
                exit_policy_params=dict(candidate.get("exit_policy_params") or {}),
            ),
            search_method="transparent_default_comparator",
            source="transparent_default_comparator_injected",
            search_space_index=None,
            exit_policy={
                "exit_policy_id": str(candidate.get("exit_policy_id", "fixed_holding_window")),
                "exit_policy_params": dict(candidate.get("exit_policy_params") or {}),
                "exit_policy_source": "transparent_default_exit_policy_inherited",
            },
        )
        if str(payload["candidate_id"]) not in seen:
            seen.add(str(payload["candidate_id"]))
            result.append(payload)
    return result


def _transparent_baseline_strategy_for_group(feature_set_id: str, holding_window: str) -> str | None:
    for strategy_id in TRANSPARENT_BASELINE_STRATEGY_IDS:
        if _is_candidate_supported(strategy_id, feature_set_id, holding_window):
            return strategy_id
    return None


def _is_candidate_supported(strategy_id: str, feature_set_id: str, holding_window: str) -> bool:
    try:
        plugin = get_strategy_plugin(
            strategy_id,
            config={
                "feature_set_id": feature_set_id,
                "holding_period": holding_window,
            },
        )
    except ValueError:
        return False
    return holding_window in getattr(plugin, "allowed_holding_periods", ()) and feature_set_id in getattr(plugin, "required_feature_sets", ())


def _validate_explicit_candidate_config(config: CandidateConfig) -> None:
    if not _is_candidate_supported(config.strategy_id, config.feature_set_id, config.holding_window):
        raise ValueError(
            "optimizer.search_spaces contains unsupported strategy/feature/holding combination: "
            f"{config.strategy_id}/{config.feature_set_id}/{config.holding_window}"
        )
    if config.exit_policy_id not in SUPPORTED_RESEARCH_EXIT_POLICIES:
        raise ValueError(f"optimizer.search_spaces contains unsupported exit_policy_id: {config.exit_policy_id}")
    allowed = allowed_parameter_names(config.strategy_id)
    unknown = sorted(set(config.parameters) - allowed)
    if unknown:
        raise ValueError(
            f"optimizer.search_spaces contains unknown parameters for {config.strategy_id}: "
            + ", ".join(unknown)
        )
    for name, value in dict(config.parameters).items():
        allowed_values = allowed_parameter_values(config.strategy_id, config.holding_window, name)
        if allowed_values and value not in allowed_values:
            raise ValueError(
                "optimizer.search_spaces contains out-of-domain parameter value for "
                f"{config.strategy_id}.{name}: {value}"
            )


def _candidate_config(candidate: Mapping[str, Any]) -> CandidateConfig:
    return CandidateConfig(
        strategy_id=str(candidate["strategy_id"]),
        parameters=dict(candidate.get("resolved_parameters") or candidate.get("parameters") or {}),
        feature_set_id=str(candidate["feature_set_id"]),
        holding_window=str(candidate["holding_window"]),
        exit_policy_id=str(candidate.get("exit_policy_id", "fixed_holding_window")),
        exit_policy_params=dict(candidate.get("exit_policy_params") or {}),
    )


def _strategy_config(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(candidate.get("resolved_parameters") or candidate.get("parameters") or {}),
        "feature_set_id": str(candidate["feature_set_id"]),
        "holding_period": str(candidate["holding_window"]),
    }


def _candidate_parameters_json(candidate: Mapping[str, Any], key: str) -> str:
    payload = dict(candidate.get(key) or {})
    return _stable_json(payload)


def _materialized_prediction_overlay_provenance(candidate: Mapping[str, Any]) -> dict[str, Any]:
    evidence = candidate.get("materialized_prediction_overlay_evidence")
    if not isinstance(evidence, Mapping):
        return {
            "materialized_prediction_overlay_used": False,
            "materialized_prediction_overlay_scope": "",
            "materialized_prediction_overlay_candidate_id": "",
            "materialized_prediction_overlay_candidate_cache_key": "",
            "materialized_prediction_overlay_materialized_candidate_id": "",
            "materialized_prediction_overlay_feature_set_id": "",
            "materialized_prediction_overlay_kind": "",
            "materialized_prediction_overlay_join_key": "",
            "materialized_prediction_overlay_predictions_path": "",
            "materialized_prediction_overlay_predictions_sha256": "",
            "materialized_prediction_overlay_manifest_path": "",
            "materialized_prediction_overlay_manifest_sha256": "",
            "materialized_prediction_overlay_manifest_version": "",
            "materialized_prediction_overlay_row_count": 0,
            "materialized_prediction_overlay_raw_knn_accepted_row_count": 0,
            "materialized_prediction_overlay_split_safety_rule": "",
            "materialized_prediction_overlay_split_safety_passed": False,
            "materialized_prediction_overlay_pre_feature_frame_sha256": "",
            "materialized_prediction_overlay_post_feature_frame_sha256": "",
            "materialized_prediction_overlay_feature_frame_sha256": "",
            "materialized_prediction_overlay_research_only": False,
            "materialized_prediction_overlay_observe_only": False,
            "materialized_prediction_overlay_promotion_ready": False,
        }
    return {
        "materialized_prediction_overlay_used": True,
        "materialized_prediction_overlay_scope": str(evidence.get("overlay_scope") or ""),
        "materialized_prediction_overlay_candidate_id": str(evidence.get("candidate_id") or ""),
        "materialized_prediction_overlay_candidate_cache_key": str(evidence.get("candidate_cache_key") or ""),
        "materialized_prediction_overlay_materialized_candidate_id": str(evidence.get("materialized_candidate_id") or ""),
        "materialized_prediction_overlay_feature_set_id": str(evidence.get("feature_set_id") or ""),
        "materialized_prediction_overlay_kind": str(evidence.get("kind") or ""),
        "materialized_prediction_overlay_join_key": str(evidence.get("join_key") or ""),
        "materialized_prediction_overlay_predictions_path": str(evidence.get("predictions_path") or ""),
        "materialized_prediction_overlay_predictions_sha256": str(evidence.get("predictions_sha256") or ""),
        "materialized_prediction_overlay_manifest_path": str(evidence.get("manifest_path") or ""),
        "materialized_prediction_overlay_manifest_sha256": str(evidence.get("manifest_sha256") or ""),
        "materialized_prediction_overlay_manifest_version": str(evidence.get("manifest_version") or ""),
        "materialized_prediction_overlay_row_count": int(evidence.get("row_count") or 0),
        "materialized_prediction_overlay_raw_knn_accepted_row_count": int(evidence.get("raw_knn_accepted_row_count") or 0),
        "materialized_prediction_overlay_split_safety_rule": str(evidence.get("split_safety_rule") or ""),
        "materialized_prediction_overlay_split_safety_passed": bool(evidence.get("split_safety_passed", False)),
        "materialized_prediction_overlay_pre_feature_frame_sha256": str(evidence.get("pre_overlay_feature_frame_sha256") or ""),
        "materialized_prediction_overlay_post_feature_frame_sha256": str(evidence.get("post_overlay_feature_frame_sha256") or ""),
        "materialized_prediction_overlay_feature_frame_sha256": str(evidence.get("candidate_feature_frame_sha256") or ""),
        "materialized_prediction_overlay_research_only": bool(evidence.get("research_only", False)),
        "materialized_prediction_overlay_observe_only": bool(evidence.get("observe_only", False)),
        "materialized_prediction_overlay_promotion_ready": bool(evidence.get("promotion_ready", False)),
    }


def _resolved_candidate_parameters(strategy_id: str, holding_window: str, specified_parameters: Mapping[str, Any]) -> dict[str, Any]:
    return dict(
        sorted(
            {
                **defaults_for_holding_window(strategy_id, holding_window),
                **dict(specified_parameters),
            }.items()
        )
    )


def _comparator_role(strategy_id: str) -> str:
    if strategy_id == NO_TRADE_BASELINE_STRATEGY_ID:
        return "no_trade_baseline"
    if strategy_id in TRANSPARENT_BASELINE_STRATEGY_IDS:
        return "transparent_baseline"
    return "research_candidate"


def _candidate_exit_policy_record(config: CandidateConfig, exit_policy: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = dict(exit_policy or {})
    params = dict(raw.get("exit_policy_params") or config.exit_policy_params or {})
    target_return = raw.get("target_return", params.get("target_return"))
    stop_return = raw.get("stop_return", params.get("stop_return"))
    if target_return is not None:
        params.setdefault("target_return", target_return)
    if stop_return is not None:
        params.setdefault("stop_return", stop_return)
    return {
        "exit_policy_id": str(raw.get("exit_policy_id") or config.exit_policy_id or "fixed_holding_window"),
        "exit_policy_params": params,
        "exit_policy_source": str(raw.get("exit_policy_source") or "configured_exit_policy"),
        "target_return": target_return,
        "stop_return": stop_return,
    }


def _stable_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), default=str)


def _baseline_group_key(
    feature_set_id: str,
    holding_window: str,
    exit_policy_id: str = "fixed_holding_window",
    exit_policy_params: Mapping[str, Any] | None = None,
) -> str:
    return f"{feature_set_id}|{holding_window}|{exit_policy_id}|{_stable_json(dict(exit_policy_params or {}))}"


def _candidate_strategy_ids(candidates: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    strategy_ids: list[str] = []
    for candidate in candidates:
        strategy_id = str(candidate["strategy_id"])
        if strategy_id in seen:
            continue
        seen.add(strategy_id)
        strategy_ids.append(strategy_id)
    return strategy_ids


def _candidate_backtest_run_id(candidate: Mapping[str, Any], scope: str, suffix: str | None = None) -> str:
    candidate_hash = str(candidate.get("candidate_id") or candidate.get("candidate_cache_key") or "candidate")
    parts = [str(scope), candidate_hash[:12]]
    if suffix:
        parts.append(_safe_run_id_part(suffix))
    return "-".join(parts)


def _short_scenario_id(scenario_id: str) -> str:
    abbreviations = {
        "base_costs": "base",
        "slippage_2x": "slip2",
        "slippage_3x": "slip3",
        "adverse_funding_shock": "fund",
        "wide_spread_stress": "spread",
        "missing_optional_context_stress": "ctxmiss",
        "high_volatility_only": "hivol",
        "low_volatility_only": "lovol",
        "trend_only": "trend",
        "range_only": "range",
        "shock_transition_only": "shock",
    }
    return abbreviations.get(str(scenario_id), str(scenario_id)[:16])


def _safe_run_id_part(value: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in str(value))[:32]


def _baseline_comparator_coverage(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_group: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_group.setdefault(str(candidate["baseline_group_key"]), []).append(candidate)
    coverage: list[dict[str, Any]] = []
    for group_key, group in sorted(by_group.items()):
        no_trade = [candidate for candidate in group if candidate.get("comparator_role") == "no_trade_baseline"]
        transparent = [candidate for candidate in group if candidate.get("comparator_role") == "transparent_baseline"]
        feature_set_id, holding_window, exit_policy_id, exit_policy_params_json = _parse_baseline_group_key(group_key)
        transparent_applicable = _transparent_baseline_strategy_for_group(feature_set_id, holding_window) is not None
        missing_reasons: list[str] = []
        if not no_trade:
            missing_reasons.append("missing_no_trade_baseline")
        if transparent_applicable and not transparent:
            missing_reasons.append("missing_transparent_baseline")
        coverage.append(
            {
                "baseline_group_key": group_key,
                "feature_set_id": feature_set_id,
                "holding_window": holding_window,
                "exit_policy_id": exit_policy_id,
                "exit_policy_params_json": exit_policy_params_json,
                "candidate_count": len(group),
                "transparent_baseline_applicable": transparent_applicable,
                "no_trade_candidate_ids": [str(candidate["candidate_id"]) for candidate in no_trade],
                "transparent_baseline_candidate_ids": [str(candidate["candidate_id"]) for candidate in transparent],
                "coverage_status": "complete" if not missing_reasons else "incomplete",
                "missing_reasons": missing_reasons,
            }
        )
    return coverage


def _parse_baseline_group_key(group_key: str) -> tuple[str, str, str, str]:
    parts = str(group_key).split("|", 3)
    if len(parts) == 2:
        return parts[0], parts[1], "fixed_holding_window", "{}"
    if len(parts) == 4:
        return parts[0], parts[1], parts[2], parts[3]
    return str(group_key), "", "fixed_holding_window", "{}"


def _default_search_policy(spec: HistoricalResearchCycleSpec, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    enabled = not bool(spec.optimizer.search_spaces)
    source_counts = _candidate_source_counts(candidates)
    return {
        "enabled": enabled,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "default_search_source": "strategy_parameter_metadata" if enabled else "disabled_explicit_search_spaces_supplied",
        "default_seed_included": enabled,
        "metadata_sample_method": "grid_prefix_with_default_seed" if enabled else None,
        "metadata_sample_cap_per_strategy_feature_holding": DEFAULT_METADATA_SEARCH_SAMPLE_CAP if enabled else 0,
        "configured_max_candidates_per_strategy": int(spec.optimizer.max_candidates_per_strategy),
        "effective_metadata_sample_cap": (
            min(DEFAULT_METADATA_SEARCH_SAMPLE_CAP, max(0, int(spec.optimizer.max_candidates_per_strategy)))
            if enabled
            else 0
        ),
        "candidate_generation_scope": "strategy_feature_holding_window",
        "candidate_source_counts": source_counts,
    }


def _candidate_source_counts(candidates: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        source = str(candidate.get("candidate_source", "unknown"))
        counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items()))


def _default_strategy_parameters(strategy_id: str) -> dict[str, Any]:
    return defaults_for_holding_window(strategy_id, "24h")


def _ranking_record(
    *,
    spec: HistoricalResearchCycleSpec,
    candidate: Mapping[str, Any],
    metrics: Mapping[str, Any],
    manifest_path: Path,
    metrics_path: Path,
    data_source: Mapping[str, Any],
    split_evaluated: bool,
    manifest: Mapping[str, Any],
    backend_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    net_return = float(metrics.get("net_return_after_fees_slippage_funding", 0.0))
    expectancy = float(metrics.get("expectancy_per_trade", 0.0))
    max_drawdown = float(metrics.get("max_drawdown", 0.0))
    trade_count = int(metrics.get("trade_count", 0))
    turnover = float(metrics.get("turnover", 0.0))
    density = signal_density_controls(str(candidate["strategy_id"]))
    final_score = expectancy + net_return + max_drawdown
    cache_key_components = dict(manifest.get("cache_key_components") or {})
    cost_model = dict(manifest.get("cost_model") or {})
    lower_timeframe_required = _candidate_requires_lower_timeframe(candidate)
    lower_timeframe_dataset_sha256 = manifest.get("lower_timeframe_dataset_sha256")
    overlay_provenance = _materialized_prediction_overlay_provenance(candidate)
    reasons: list[str] = []
    if bool(data_source.get("synthetic")):
        reasons.append("synthetic_fixture_not_real_oos_evidence")
    if trade_count < spec.validation.trade_count_floor:
        reasons.append("trade_count_below_research_floor")
    if turnover < density.min_signal_rate:
        reasons.append("low_signal_density")
    if turnover > density.max_signal_rate:
        reasons.append("high_signal_density")
    if turnover > density.max_turnover:
        reasons.append("turnover_above_window_cap")
    if not split_evaluated:
        reasons.append("full_split_stability_not_evaluated_for_r1_aggregate_ranking")
    backend_rejection_reason = str(backend_evidence.get("backtest_backend_rejection_reason") or "")
    if backend_rejection_reason:
        reasons.append(backend_rejection_reason)
    blocker_code = str(manifest.get("blocker_code") or "")
    if blocker_code:
        reasons.append(blocker_code)
    blocked_backtest = bool(manifest.get("blocked", False))
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_cache_key": candidate.get("candidate_cache_key", candidate["candidate_id"]),
        "human_readable_candidate_id": candidate.get("human_readable_candidate_id", candidate["candidate_id"]),
        "strategy_id": candidate["strategy_id"],
        "strategy_version": candidate.get("strategy_version", "unknown"),
        "strategy_role": candidate.get("strategy_role", "research_candidate"),
        "comparator_role": candidate.get("comparator_role", "research_candidate"),
        "baseline_group_key": candidate.get("baseline_group_key", _baseline_group_key(str(candidate["feature_set_id"]), str(candidate["holding_window"]))),
        "strategy_metadata_sha256": candidate.get("strategy_metadata_sha256", ""),
        "strategy_metadata_strategy_id": candidate.get("strategy_metadata_strategy_id", candidate["strategy_id"]),
        "feature_set_id": candidate["feature_set_id"],
        "holding_window": candidate["holding_window"],
        "exit_policy_id": candidate.get("exit_policy_id", "fixed_holding_window"),
        "exit_policy_params_json": candidate.get("exit_policy_params_json", "{}"),
        "exit_policy_source": candidate.get("exit_policy_source", "unknown"),
        "target_return": _optional_float(candidate.get("target_return")),
        "stop_return": _optional_float(candidate.get("stop_return")),
        "parameters_json": _candidate_parameters_json(candidate, "resolved_parameters"),
        "resolved_parameters_json": _candidate_parameters_json(candidate, "resolved_parameters"),
        "specified_parameters_json": _candidate_parameters_json(candidate, "specified_parameters"),
        "parameter_resolution_policy": candidate.get("parameter_resolution_policy", "unknown"),
        "is_default_parameter_candidate": bool(candidate.get("is_default_parameter_candidate", False)),
        "strategy_requested_in_spec": bool(candidate.get("strategy_requested_in_spec", False)),
        "comparator_injected": bool(candidate.get("comparator_injected", False)),
        "search_method": candidate.get("search_method", "unknown"),
        "candidate_source": candidate.get("candidate_source", "unknown"),
        "metric_scope": "blocked_backtest" if blocked_backtest else "real_backtest",
        "metrics_source": "blocked_fail_closed_backtest" if blocked_backtest else "backtest_engine",
        "empirical_evidence": not blocked_backtest,
        "data_evidence_scope": "synthetic_fixture" if bool(data_source.get("synthetic")) else "local_historical_fixture",
        "backtest_manifest_path": str(manifest_path),
        "aggregate_backtest_cache_key": str(manifest["cache_key"]),
        "aggregate_backtest_result_sha256": str(manifest["result_sha256"]),
        "aggregate_backtest_identity_scope": "aggregate",
        "aggregate_backtest_cache_policy": str(manifest["cache_policy"]),
        "aggregate_backtest_cache_hit": bool(manifest.get("cache_hit", False)),
        "aggregate_backtest_cache_lookup_used": bool(manifest.get("cache_lookup_used", False)),
        "aggregate_backtest_execution_cache_reuse_enabled": bool(manifest.get("execution_cache_reuse_enabled", False)),
        "aggregate_backtest_exit_price_source": str(manifest.get("exit_price_source") or ""),
        "aggregate_backtest_lower_timeframe_required": bool(lower_timeframe_required),
        "aggregate_backtest_lower_timeframe_dataset_path": manifest.get("lower_timeframe_dataset_path"),
        "aggregate_backtest_lower_timeframe_dataset_sha256": lower_timeframe_dataset_sha256,
        "aggregate_backtest_lower_timeframe_sequence_used": bool(lower_timeframe_dataset_sha256),
        "aggregate_backtest_lower_timeframe_cache_key_component": cache_key_components.get("lower_timeframe_dataset_sha256"),
        "aggregate_backtest_backend_requested": str(backend_evidence["backtest_backend_requested"]),
        "aggregate_backtest_backend_used": str(backend_evidence["backtest_backend_used"]),
        "aggregate_backtest_backend_fallback_reason": str(backend_evidence["backtest_backend_fallback_reason"]),
        "aggregate_backtest_backend_rejection_reason": str(backend_evidence["backtest_backend_rejection_reason"]),
        "aggregate_backtest_engine_version": str(backend_evidence["backtest_engine_version"]),
        "aggregate_backtest_reference_engine_version": str(backend_evidence["reference_engine_version"]),
        "aggregate_backtest_vector_execution_scope": str(backend_evidence["vector_execution_scope"]),
        "aggregate_backtest_cuda_execution_scope": str(backend_evidence.get("cuda_execution_scope", "")),
        "aggregate_backtest_cuda_parity_status": str(backend_evidence.get("cuda_parity_status", "")),
        "aggregate_backtest_gpu_execution_status": str(backend_evidence.get("gpu_execution_status", "")),
        "aggregate_backtest_gpu_device_name": str(backend_evidence.get("gpu_device_name", "")),
        "aggregate_backtest_gpu_compute_capability": str(backend_evidence.get("gpu_compute_capability", "")),
        "aggregate_backtest_cache_key_components_engine_version": str(
            backend_evidence["backtest_cache_key_components_engine_version"]
        ),
        **overlay_provenance,
        "metrics_path": str(metrics_path),
        "trade_count": trade_count,
        "long_count": int(metrics.get("long_count", 0)),
        "short_count": int(metrics.get("short_count", 0)),
        "costed_expectancy": expectancy,
        "net_return_after_fees_slippage_funding": net_return,
        "drawdown_adjusted_return": net_return + max_drawdown,
        "max_drawdown": max_drawdown,
        "hit_rate": float(metrics.get("hit_rate", 0.0)),
        "profit_factor": float(metrics.get("profit_factor", 0.0)),
        "turnover": turnover,
        "signal_rate": turnover,
        "min_signal_rate": density.min_signal_rate,
        "max_signal_rate": density.max_signal_rate,
        "max_turnover": density.max_turnover,
        "final_score": float(final_score),
        "decision": "rejected",
        "failure_reasons": "|".join(reasons),
        "regime": "aggregate",
        "side": "all",
    }


def _annotate_rankings_with_comparator_evidence(rankings: pd.DataFrame) -> pd.DataFrame:
    if rankings.empty:
        return rankings
    frame = rankings.copy()
    no_trade_by_group: dict[str, dict[str, Any]] = {}
    transparent_default_by_strategy_group: dict[tuple[str, str], dict[str, Any]] = {}
    transparent_default_by_group: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict("records"):
        group_key = str(row.get("baseline_group_key", ""))
        role = str(row.get("comparator_role", ""))
        if role == "no_trade_baseline":
            no_trade_by_group[group_key] = row
        if role == "transparent_baseline" and bool(row.get("is_default_parameter_candidate", False)):
            transparent_default_by_strategy_group[(str(row["strategy_id"]), group_key)] = row
            transparent_default_by_group.setdefault(group_key, row)

    no_trade_ids: list[str | None] = []
    no_trade_metrics_paths: list[str | None] = []
    no_trade_expectancies: list[float | None] = []
    expectancy_vs_no_trade: list[float | None] = []
    transparent_ids: list[str | None] = []
    transparent_metrics_paths: list[str | None] = []
    transparent_expectancies: list[float | None] = []
    expectancy_vs_transparent: list[float | None] = []
    coverage_statuses: list[str] = []
    updated_reasons: list[str] = []

    for row in frame.to_dict("records"):
        group_key = str(row.get("baseline_group_key", ""))
        expectancy = float(row.get("costed_expectancy", 0.0))
        no_trade = no_trade_by_group.get(group_key)
        transparent = transparent_default_by_strategy_group.get((str(row["strategy_id"]), group_key)) or transparent_default_by_group.get(group_key)
        transparent_applicable = _transparent_baseline_strategy_for_group(str(row["feature_set_id"]), str(row["holding_window"])) is not None
        missing: list[str] = []
        if no_trade is None:
            missing.append("missing_no_trade_baseline_comparator")
            no_trade_ids.append(None)
            no_trade_metrics_paths.append(None)
            no_trade_expectancies.append(None)
            expectancy_vs_no_trade.append(None)
        else:
            no_trade_ids.append(str(no_trade["candidate_id"]))
            no_trade_metrics_paths.append(str(no_trade["metrics_path"]))
            no_trade_expectancy = float(no_trade.get("costed_expectancy", 0.0))
            no_trade_expectancies.append(no_trade_expectancy)
            expectancy_vs_no_trade.append(float(expectancy - no_trade_expectancy))
        if transparent is None and transparent_applicable:
            missing.append("missing_transparent_baseline_comparator")
            transparent_ids.append(None)
            transparent_metrics_paths.append(None)
            transparent_expectancies.append(None)
            expectancy_vs_transparent.append(None)
        elif transparent is None:
            transparent_ids.append(None)
            transparent_metrics_paths.append(None)
            transparent_expectancies.append(None)
            expectancy_vs_transparent.append(None)
        else:
            transparent_ids.append(str(transparent["candidate_id"]))
            transparent_metrics_paths.append(str(transparent["metrics_path"]))
            transparent_expectancy = float(transparent.get("costed_expectancy", 0.0))
            transparent_expectancies.append(transparent_expectancy)
            expectancy_vs_transparent.append(float(expectancy - transparent_expectancy))
        coverage_statuses.append("complete" if not missing else "incomplete")
        reasons = [reason for reason in str(row.get("failure_reasons", "")).split("|") if reason]
        reasons.extend(missing)
        updated_reasons.append("|".join(dict.fromkeys(reasons)))

    frame["no_trade_comparator_candidate_id"] = no_trade_ids
    frame["no_trade_comparator_metrics_path"] = no_trade_metrics_paths
    frame["no_trade_costed_expectancy"] = no_trade_expectancies
    frame["expectancy_vs_no_trade"] = expectancy_vs_no_trade
    frame["transparent_default_comparator_candidate_id"] = transparent_ids
    frame["transparent_default_comparator_metrics_path"] = transparent_metrics_paths
    frame["transparent_default_costed_expectancy"] = transparent_expectancies
    frame["expectancy_vs_transparent_default"] = expectancy_vs_transparent
    frame["baseline_comparator_coverage_status"] = coverage_statuses
    frame["failure_reasons"] = updated_reasons
    return frame


def _annotate_rankings_with_ablation_evidence(rankings: pd.DataFrame) -> pd.DataFrame:
    if rankings.empty:
        return rankings
    frame = rankings.copy()
    by_feature_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in frame.to_dict("records"):
        by_feature_key[_ablation_feature_key(row, str(row.get("feature_set_id") or ""))] = row

    statuses: list[str] = []
    required_values: list[bool] = []
    passed_values: list[bool] = []
    comparator_feature_sets: list[str | None] = []
    comparator_candidate_ids: list[str | None] = []
    expectancy_deltas: list[float | None] = []
    final_score_deltas: list[float | None] = []
    failure_reasons: list[str] = []

    for row in frame.to_dict("records"):
        feature_set_id = str(row.get("feature_set_id") or "")
        comparator_feature_set = _ablation_comparator_feature_set(feature_set_id)
        comparator_feature_sets.append(comparator_feature_set)
        if comparator_feature_set is None:
            statuses.append("baseline_feature_set_no_optional_claim")
            required_values.append(False)
            passed_values.append(True)
            comparator_candidate_ids.append(None)
            expectancy_deltas.append(None)
            final_score_deltas.append(None)
            failure_reasons.append("")
            continue

        required_values.append(True)
        comparator = by_feature_key.get(_ablation_feature_key(row, comparator_feature_set))
        if comparator is None:
            statuses.append("comparator_feature_set_missing")
            passed_values.append(False)
            comparator_candidate_ids.append(None)
            expectancy_deltas.append(None)
            final_score_deltas.append(None)
            failure_reasons.append("feature_ablation_comparator_missing")
            continue

        expectancy_delta = float(row.get("costed_expectancy", 0.0)) - float(comparator.get("costed_expectancy", 0.0))
        final_score_delta = float(row.get("final_score", 0.0)) - float(comparator.get("final_score", 0.0))
        comparator_candidate_ids.append(str(comparator.get("candidate_id")))
        expectancy_deltas.append(float(expectancy_delta))
        final_score_deltas.append(float(final_score_delta))
        if expectancy_delta >= 0.0 and final_score_delta >= 0.0:
            statuses.append("comparator_feature_set_passed")
            passed_values.append(True)
            failure_reasons.append("")
        else:
            statuses.append("comparator_feature_set_failed")
            passed_values.append(False)
            failure_reasons.append("candidate_underperforms_feature_ablation_comparator")

    frame["feature_ablation_required"] = required_values
    frame["feature_ablation_passed"] = passed_values
    frame["ablation_evidence_status"] = statuses
    frame["ablation_comparator_feature_set_id"] = comparator_feature_sets
    frame["ablation_comparator_candidate_id"] = comparator_candidate_ids
    frame["ablation_expectancy_delta"] = expectancy_deltas
    frame["ablation_final_score_delta"] = final_score_deltas
    frame["ablation_failure_reasons"] = failure_reasons
    return frame


def _ablation_feature_key(row: Mapping[str, Any], feature_set_id: str) -> tuple[str, str, str, str, str, str]:
    return (
        str(row.get("strategy_id") or ""),
        str(row.get("holding_window") or ""),
        str(row.get("exit_policy_id") or "fixed_holding_window"),
        str(row.get("exit_policy_params_json") or "{}"),
        _ablation_parameters_json(row, feature_set_id),
        str(feature_set_id),
    )


def _ablation_parameters_json(row: Mapping[str, Any], feature_set_id: str) -> str:
    params = _row_parameters(row)
    if (
        str(row.get("strategy_id") or "") == SPARSE_EVENT_FILTER_STRATEGY_ID
        and str(feature_set_id) in {"features_price_trend_vol", "features_price_perp_aggflow_no_wt"}
    ):
        for key in SPARSE_FLOW_ABLATION_PARAMETER_KEYS:
            params.pop(key, None)
    return json.dumps(dict(sorted(params.items())), sort_keys=True, separators=(",", ":"), default=str)


def _ablation_comparator_feature_set(feature_set_id: str) -> str | None:
    if feature_set_id in {"features_price_trend_vol", "features_perp_context_v2", "features_liquidation_context_v1"}:
        return None
    return {
        "features_price_trend_vol_wt3d": "features_price_trend_vol",
        "features_full_context_wt3d": "features_full_context_no_wt",
        "features_full_context_no_wt": "features_price_trend_vol",
        "features_perp_context_only": "features_price_trend_vol",
        "features_microstructure_filter_only": "features_price_trend_vol",
    }.get(feature_set_id, "features_price_trend_vol")


def _backtest_index_record(
    candidate: Mapping[str, Any],
    manifest_path: Path,
    metrics_path: Path,
    manifest: Mapping[str, Any],
    evaluation_scope: str,
    *,
    trades_path: Path | None = None,
    backend_evidence: Mapping[str, Any] | None = None,
    split: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    trades_path_value = str(trades_path) if trades_path is not None else None
    backend = dict(backend_evidence or _backtest_backend_evidence(requested="reference", fallback_reason="", manifest=manifest))
    split_payload = dict(split or {})
    cache_key_components = dict(manifest.get("cache_key_components") or {})
    cost_model = dict(manifest.get("cost_model") or {})
    lower_timeframe_required = _candidate_requires_lower_timeframe(candidate)
    lower_timeframe_dataset_sha256 = manifest.get("lower_timeframe_dataset_sha256")
    exit_sequence_counts = _trade_column_counts(trades_path, "exit_sequence_proof") if lower_timeframe_required else {}
    barrier_counts = _trade_column_counts(trades_path, "barrier_hit_type") if lower_timeframe_required else {}
    exit_price_source_counts = _trade_column_counts(trades_path, "exit_price_source") if lower_timeframe_required else {}
    overlay_provenance = _materialized_prediction_overlay_provenance(candidate)
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_cache_key": candidate.get("candidate_cache_key", candidate["candidate_id"]),
        "strategy_id": candidate["strategy_id"],
        "strategy_version": candidate.get("strategy_version", "unknown"),
        "strategy_role": candidate.get("strategy_role", "research_candidate"),
        "comparator_role": candidate.get("comparator_role", "research_candidate"),
        "baseline_group_key": candidate.get("baseline_group_key", _baseline_group_key(str(candidate["feature_set_id"]), str(candidate["holding_window"]))),
        "strategy_metadata_sha256": candidate.get("strategy_metadata_sha256", ""),
        "feature_set_id": candidate["feature_set_id"],
        "holding_window": candidate["holding_window"],
        "exit_policy_id": candidate.get("exit_policy_id", "fixed_holding_window"),
        "exit_policy_params_json": candidate.get("exit_policy_params_json", "{}"),
        "exit_policy_source": candidate.get("exit_policy_source", "unknown"),
        "target_return": _optional_float(candidate.get("target_return")),
        "stop_return": _optional_float(candidate.get("stop_return")),
        "parameters_json": _candidate_parameters_json(candidate, "resolved_parameters"),
        "resolved_parameters_json": _candidate_parameters_json(candidate, "resolved_parameters"),
        "specified_parameters_json": _candidate_parameters_json(candidate, "specified_parameters"),
        "evaluation_scope": evaluation_scope,
        "split_id": split_payload.get("split_id"),
        "validation_method": split_payload.get("validation_method"),
        "split_mode": split_payload.get("split_mode"),
        "train_window_bars": split_payload.get("train_window_bars"),
        "validation_size_bars": split_payload.get("validation_size_bars"),
        "anchor_offset_bars": split_payload.get("anchor_offset_bars"),
        "purge_embargo_bars": split_payload.get("purge_embargo_bars"),
        "train_start_time_ms": split_payload.get("train_start_time_ms"),
        "train_end_time_ms": split_payload.get("train_end_time_ms"),
        "validation_start_time_ms": split_payload.get("validation_start_time_ms"),
        "validation_end_time_ms": split_payload.get("validation_end_time_ms"),
        "backtest_manifest_path": str(manifest_path),
        "metrics_path": str(metrics_path),
        "trades_path": trades_path_value,
        "trades_sha256": _file_sha256(trades_path) if trades_path is not None and trades_path.exists() else None,
        "trade_count": int(manifest.get("trade_count", 0)),
        "exit_price_source": str(manifest.get("exit_price_source") or ""),
        "lower_timeframe_required": bool(lower_timeframe_required),
        "lower_timeframe_dataset_path": manifest.get("lower_timeframe_dataset_path"),
        "lower_timeframe_dataset_sha256": lower_timeframe_dataset_sha256,
        "lower_timeframe_sequence_used": bool(lower_timeframe_dataset_sha256),
        "lower_timeframe_cache_key_component": cache_key_components.get("lower_timeframe_dataset_sha256"),
        "exit_sequence_proof_counts_json": _stable_json(exit_sequence_counts),
        "barrier_hit_type_counts_json": _stable_json(barrier_counts),
        "exit_price_source_counts_json": _stable_json(exit_price_source_counts),
        "result_sha256": manifest.get("result_sha256"),
        "cache_key": manifest.get("cache_key"),
        "cache_policy": str(manifest.get("cache_policy", "")),
        "cache_hit": bool(manifest.get("cache_hit", False)),
        "cache_lookup_used": bool(manifest.get("cache_lookup_used", False)),
        "execution_cache_reuse_enabled": bool(manifest.get("execution_cache_reuse_enabled", False)),
        "cost_profile_contract_version": cost_model.get("cost_profile_contract_version"),
        "cost_profile_id": cost_model.get("cost_profile_id"),
        "cost_profile_source": cost_model.get("cost_profile_source"),
        "fill_profile_id": cost_model.get("fill_profile_id"),
        "cost_profile_venue": cost_model.get("venue"),
        "cost_profile_source_venue": cost_model.get("source_venue"),
        "cost_profile_execution_venue": cost_model.get("execution_venue"),
        "cost_profile_evidence_scope": cost_model.get("evidence_scope"),
        "cost_profile_execution_proof_scope": cost_model.get("execution_proof_scope"),
        "not_hyperliquid_execution_proof": "hyperliquid" in set(cost_model.get("not_execution_proof_for") or ()),
        **overlay_provenance,
        **backend,
    }


def _trade_column_counts(trades_path: Path | None, column: str) -> dict[str, int]:
    if trades_path is None or not trades_path.exists():
        return {}
    frame = pd.read_parquet(trades_path, columns=[column])
    if column not in frame.columns or frame.empty:
        return {}
    counts: dict[str, int] = {}
    for value in frame[column].dropna().astype(str):
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _backtest_backend_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    requested_counts: dict[str, int] = {}
    used_counts: dict[str, int] = {}
    fallback_reasons: dict[str, int] = {}
    vector_scope_counts: dict[str, int] = {}
    cuda_scope_counts: dict[str, int] = {}
    gpu_status_counts: dict[str, int] = {}
    for record in records:
        requested = str(record.get("backtest_backend_requested") or "")
        used = str(record.get("backtest_backend_used") or "")
        fallback_reason = str(record.get("backtest_backend_fallback_reason") or "")
        vector_scope = str(record.get("vector_execution_scope") or "")
        cuda_scope = str(record.get("cuda_execution_scope") or "")
        gpu_status = str(record.get("gpu_execution_status") or "")
        if requested:
            requested_counts[requested] = requested_counts.get(requested, 0) + 1
        if used:
            used_counts[used] = used_counts.get(used, 0) + 1
        if fallback_reason:
            fallback_reasons[fallback_reason] = fallback_reasons.get(fallback_reason, 0) + 1
        if vector_scope:
            vector_scope_counts[vector_scope] = vector_scope_counts.get(vector_scope, 0) + 1
        if cuda_scope:
            cuda_scope_counts[cuda_scope] = cuda_scope_counts.get(cuda_scope, 0) + 1
        if gpu_status:
            gpu_status_counts[gpu_status] = gpu_status_counts.get(gpu_status, 0) + 1
    return {
        "summary_version": "research-cycle-backtest-backend-summary-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "backtest_count": int(len(records)),
        "requested_counts": dict(sorted(requested_counts.items())),
        "used_counts": dict(sorted(used_counts.items())),
        "fallback_count": int(sum(fallback_reasons.values())),
        "fallback_reasons": dict(sorted(fallback_reasons.items())),
        "vector_scope_counts": dict(sorted(vector_scope_counts.items())),
        "cuda_scope_counts": dict(sorted(cuda_scope_counts.items())),
        "gpu_status_counts": dict(sorted(gpu_status_counts.items())),
    }


def _split_metric_record(
    candidate: Mapping[str, Any],
    split: Mapping[str, Any],
    metrics: Mapping[str, Any],
    manifest_path: Path,
    *,
    trade_count_floor: int,
) -> dict[str, Any]:
    trade_count = int(metrics.get("trade_count", 0))
    return {
        "candidate_id": candidate["candidate_id"],
        "strategy_id": candidate["strategy_id"],
        "feature_set_id": candidate["feature_set_id"],
        "holding_window": candidate["holding_window"],
        "split_id": split["split_id"],
        "validation_method": split["validation_method"],
        "split_mode": split.get("split_mode"),
        "train_window_bars": split.get("train_window_bars"),
        "validation_size_bars": split.get("validation_size_bars"),
        "anchor_offset_bars": split.get("anchor_offset_bars"),
        "purge_embargo_bars": split.get("purge_embargo_bars"),
        "train_start_index": split.get("train_start_index"),
        "train_end_index": split.get("train_end_index"),
        "validation_start_index": split.get("validation_start_index"),
        "validation_end_index": split.get("validation_end_index"),
        "train_start_time_ms": split.get("train_start_time_ms"),
        "train_end_time_ms": split.get("train_end_time_ms"),
        "validation_start_time_ms": split.get("validation_start_time_ms"),
        "validation_end_time_ms": split.get("validation_end_time_ms"),
        "trade_count": trade_count,
        "trade_count_floor": int(trade_count_floor),
        "trade_count_floor_status": "passed" if trade_count >= int(trade_count_floor) else "failed",
        "costed_expectancy": float(metrics.get("expectancy_per_trade", 0.0)),
        "net_return_after_fees_slippage_funding": float(metrics.get("net_return_after_fees_slippage_funding", 0.0)),
        "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
        "backtest_manifest_path": str(manifest_path),
    }


def _cost_stress_scenarios() -> tuple[dict[str, Any], ...]:
    return tuple(dict(scenario) for scenario in research_cost_stress_scenarios())


def _cost_stress_frame(frame: pd.DataFrame, scenario: Mapping[str, Any]) -> pd.DataFrame:
    stressed = frame.copy()
    transform = str(scenario.get("transform") or "")
    if transform == "wide_spread":
        stressed["spread_bps"] = float(scenario.get("spread_bps", 25.0))
    elif transform == "missing_optional_context":
        stressed = _missing_optional_context_frame(stressed)

    filter_id = str(scenario.get("filter") or "")
    if filter_id:
        stressed = _filtered_stress_frame(stressed, filter_id)
    if stressed.empty:
        return frame.iloc[0:0].copy()
    return stressed.sort_values("bar_time_ms", kind="mergesort").reset_index(drop=True)


def _filtered_stress_frame(frame: pd.DataFrame, filter_id: str) -> pd.DataFrame:
    if filter_id == "high_volatility":
        if "atr_percentile" in frame.columns:
            return frame.loc[pd.to_numeric(frame["atr_percentile"], errors="coerce").fillna(-1.0) >= 0.65].copy()
        if "realized_volatility" in frame.columns:
            threshold = float(pd.to_numeric(frame["realized_volatility"], errors="coerce").quantile(0.67))
            return frame.loc[pd.to_numeric(frame["realized_volatility"], errors="coerce").fillna(-1.0) >= threshold].copy()
    if filter_id == "low_volatility":
        if "realized_volatility" in frame.columns:
            threshold = 0.015
            return frame.loc[pd.to_numeric(frame["realized_volatility"], errors="coerce").fillna(999.0) <= threshold].copy()
        if "atr_percentile" in frame.columns:
            return frame.loc[pd.to_numeric(frame["atr_percentile"], errors="coerce").fillna(999.0) <= 0.35].copy()
    if filter_id == "trend":
        if "choppiness" in frame.columns:
            return frame.loc[pd.to_numeric(frame["choppiness"], errors="coerce").fillna(999.0) <= 45.0].copy()
        if "directional_slope_atr" in frame.columns:
            return frame.loc[pd.to_numeric(frame["directional_slope_atr"], errors="coerce").abs().fillna(0.0) >= 0.08].copy()
    if filter_id == "range":
        if "choppiness" in frame.columns:
            return frame.loc[pd.to_numeric(frame["choppiness"], errors="coerce").fillna(-1.0) >= 50.0].copy()
        if "range_width" in frame.columns:
            return frame.loc[pd.to_numeric(frame["range_width"], errors="coerce").fillna(0.0) >= 0.008].copy()
    if filter_id == "shock_transition":
        if "volatility_shock_zscore" in frame.columns:
            return frame.loc[pd.to_numeric(frame["volatility_shock_zscore"], errors="coerce").abs().fillna(0.0) >= 2.0].copy()
    return frame.iloc[0:0].copy()


def _missing_optional_context_frame(frame: pd.DataFrame) -> pd.DataFrame:
    stressed = frame.copy()
    optional_columns = {
        "basis_bps",
        "funding_rate",
        "funding_rate_change",
        "open_interest",
        "open_interest_change",
        "open_interest_change_pct",
        "open_interest_value",
        "premium_basis_rate",
        "premium_basis_abs",
        "premium_close",
        "mark_price",
        "spread_bps",
    }
    for column in list(stressed.columns):
        if column in optional_columns or column.startswith("raw_"):
            stressed[column] = pd.NA
        if column.startswith("missing_"):
            stressed[column] = True
    for column in (
        "funding_context_json",
        "open_interest_context_json",
        "premium_context_json",
        "basis_context_json",
        "microstructure_context_json",
    ):
        if column in stressed.columns:
            stressed[column] = "{}"
    return stressed


def _cost_stress_record(
    candidate: Mapping[str, Any],
    scenario: Mapping[str, Any],
    metrics: Mapping[str, Any],
    manifest_path: Path,
    *,
    source_row_count: int,
    stress_dataset_sha256: str,
) -> dict[str, Any]:
    stressed_expectancy = float(metrics.get("expectancy_per_trade", 0.0))
    stressed_net_return = float(metrics.get("net_return_after_fees_slippage_funding", 0.0))
    stress_survival_score = stressed_expectancy + stressed_net_return
    return {
        "candidate_id": candidate["candidate_id"],
        "strategy_id": candidate["strategy_id"],
        "feature_set_id": candidate["feature_set_id"],
        "holding_window": candidate["holding_window"],
        "scenario_id": scenario["scenario_id"],
        "scenario_group": scenario.get("scenario_group", "cost"),
        "cost_profile_contract_version": scenario.get("cost_profile_contract_version"),
        "cost_profile_id": scenario.get("cost_profile_id"),
        "fill_profile_id": scenario.get("fill_profile_id"),
        "venue": scenario.get("venue"),
        "source_venue": scenario.get("source_venue"),
        "execution_venue": scenario.get("execution_venue"),
        "evidence_scope": scenario.get("evidence_scope"),
        "execution_proof_scope": scenario.get("execution_proof_scope"),
        "not_hyperliquid_execution_proof": "hyperliquid" in set(scenario.get("not_execution_proof_for") or ()),
        "scenario_filter": scenario.get("filter"),
        "scenario_transform": scenario.get("transform"),
        "fee_bps": float(scenario["fee_bps"]),
        "slippage_bps": float(scenario["slippage_bps"]),
        "spread_bps": float(scenario.get("spread_bps", 0.0)),
        "funding_rate": float(scenario["funding_rate"]),
        "source_row_count": int(source_row_count),
        "stress_dataset_sha256": str(stress_dataset_sha256),
        "scenario_status": "evaluated" if int(source_row_count) > 0 else "no_source_rows",
        "trade_count": int(metrics.get("trade_count", 0)),
        "stressed_expectancy": stressed_expectancy,
        "stressed_net_return": stressed_net_return,
        "stress_survival_score": stress_survival_score,
        "stress_survival_status": "passed" if stress_survival_score > 0.0 else "failed",
        "backtest_manifest_path": str(manifest_path),
    }


def _candidate_result_from_metrics(
    candidate: Mapping[str, Any],
    *,
    metrics: Mapping[str, Any],
    feature_missingness: float,
) -> CandidateResult:
    expectancy = float(metrics.get("expectancy_per_trade", 0.0))
    net_return = float(metrics.get("net_return_after_fees_slippage_funding", 0.0))
    max_drawdown = float(metrics.get("max_drawdown", 0.0))
    return CandidateResult(
        config=_candidate_config(candidate),
        base_score=float(expectancy + net_return),
        risk_score=max_drawdown,
        trade_count=int(metrics.get("trade_count", 0)),
        side_balance=_side_balance(
            int(metrics.get("long_count", 0)),
            int(metrics.get("short_count", 0)),
        ),
        regime_coverage=_regime_coverage(metrics.get("split_by_regime", {})),
        missingness_rate=float(feature_missingness),
        turnover=float(metrics.get("turnover", 0.0)),
        max_drawdown=max_drawdown,
        metadata={
            "metric_scope": "real_backtest",
            "candidate_source": candidate.get("candidate_source", "unknown"),
            "search_method": candidate.get("search_method", "unknown"),
        },
    )


def _enriched_candidate_results(
    candidate_results_by_id: Mapping[str, CandidateResult],
    split_records: list[dict[str, Any]],
    cost_stress_records: list[dict[str, Any]],
) -> dict[str, CandidateResult]:
    split_records_by_id = _records_by_candidate(split_records)
    cost_records_by_id = _records_by_candidate(cost_stress_records)
    enriched: dict[str, CandidateResult] = {}
    for candidate_id, result in candidate_results_by_id.items():
        candidate_split_records = split_records_by_id.get(candidate_id, [])
        candidate_cost_records = cost_records_by_id.get(candidate_id, [])
        split_consistency = _split_consistency(candidate_split_records)
        cost_stress_survival = _cost_stress_survival(candidate_cost_records)
        enriched[candidate_id] = replace(
            result,
            robustness_score=float(0.05 * split_consistency + 0.05 * cost_stress_survival),
            split_consistency=split_consistency,
            cost_stress_survival=cost_stress_survival,
            metadata={
                **dict(result.metadata),
                "split_evaluation_count": len(candidate_split_records),
                "cost_stress_evaluation_count": len(candidate_cost_records),
            },
        )
    return enriched


def _annotate_rankings_with_validation(
    rankings: pd.DataFrame,
    candidate_results: Mapping[str, CandidateResult],
    shortlisted_ids: set[str],
    *,
    required_split_count: int,
    required_cost_stress_count: int,
) -> pd.DataFrame:
    frame = rankings.copy()
    frame["aggregate_rank"] = frame["rank"].astype(int)
    frame["split_evaluated"] = frame["candidate_id"].astype(str).isin(shortlisted_ids)
    frame["cost_stress_evaluated"] = frame["split_evaluated"]
    frame["aggregate_stability_region_evaluated"] = True
    frame["stability_evaluated"] = frame["split_evaluated"] & frame["cost_stress_evaluated"]
    frame["stability_validation_scope"] = frame["stability_evaluated"].map(
        {
            True: "split_cost_stress_enriched",
            False: "aggregate_only_unvalidated_neighborhood",
        }
    )
    frame["split_evaluation_count"] = frame["candidate_id"].map(
        lambda value: int(candidate_results[str(value)].metadata.get("split_evaluation_count", 0))
    )
    frame["cost_stress_evaluation_count"] = frame["candidate_id"].map(
        lambda value: int(candidate_results[str(value)].metadata.get("cost_stress_evaluation_count", 0))
    )
    frame["required_split_count"] = int(required_split_count)
    frame["required_cost_stress_count"] = int(required_cost_stress_count)
    frame["split_consistency"] = frame["candidate_id"].map(lambda value: candidate_results[str(value)].split_consistency)
    frame["cost_stress_survival"] = frame["candidate_id"].map(lambda value: candidate_results[str(value)].cost_stress_survival)
    frame["optimizer_final_score"] = frame["candidate_id"].map(lambda value: candidate_results[str(value)].final_score)
    optimizer_order = frame.sort_values(
        ["optimizer_final_score", "trade_count"],
        ascending=[False, False],
        kind="mergesort",
    ).index
    frame["optimizer_rank"] = 0
    frame.loc[optimizer_order, "optimizer_rank"] = range(1, len(frame) + 1)
    frame["ranking_scope"] = "aggregate_rank_with_validation_annotations"

    def update_failure_reasons(row: pd.Series) -> str:
        reasons = [
            reason
            for reason in str(row["failure_reasons"]).split("|")
            if reason and reason != "full_split_stability_not_evaluated_for_r1_aggregate_ranking"
        ]
        if not bool(row["split_evaluated"]):
            reasons.append("split_and_cost_stress_evaluation_reserved_for_shortlist")
        if not bool(row["stability_evaluated"]):
            reasons.append("validated_stability_region_reserved_for_shortlist")
        return "|".join(dict.fromkeys(reasons))

    frame["failure_reasons"] = frame.apply(update_failure_reasons, axis=1)
    return frame


def _annotate_rankings_with_research_gate(
    rankings: pd.DataFrame,
    *,
    stability_regions: pd.DataFrame,
    regime_metric_records: list[dict[str, Any]],
    side_metric_records: list[dict[str, Any]],
    split_records: list[dict[str, Any]],
    cost_stress_records: list[dict[str, Any]],
    spec: HistoricalResearchCycleSpec,
    data_source: Mapping[str, Any],
) -> pd.DataFrame:
    frame = rankings.copy()
    stability_by_candidate = {
        str(row["candidate_id"]): row
        for row in stability_regions.to_dict("records")
    }
    regime_by_candidate = _records_by_candidate(regime_metric_records)
    side_by_candidate = _records_by_candidate(side_metric_records)
    split_by_candidate = _records_by_candidate(split_records)
    cost_by_candidate = _records_by_candidate(cost_stress_records)
    rows = frame.to_dict("records")
    side_veto_controls = _side_veto_control_lookup(rows, side_by_candidate)

    annotated: list[dict[str, Any]] = []
    for row in rows:
        candidate_id = str(row["candidate_id"])
        details = _research_gate_details(
            row,
            stability=stability_by_candidate.get(candidate_id, {}),
            regime_records=regime_by_candidate.get(candidate_id, []),
            side_records=side_by_candidate.get(candidate_id, []),
            side_veto_controls=side_veto_controls,
            split_records=split_by_candidate.get(candidate_id, []),
            cost_stress_records=cost_by_candidate.get(candidate_id, []),
            spec=spec,
            data_source=data_source,
        )
        reasons = [
            reason
            for reason in str(row.get("failure_reasons") or "").split("|")
            if reason
        ]
        reasons.extend(details.pop("gate_reasons"))
        unique_reasons = list(dict.fromkeys(reasons))
        row.update(details)
        row["decision"] = "research_gate_passed" if not unique_reasons else "rejected"
        row["failure_reasons"] = "" if not unique_reasons else "|".join(unique_reasons)
        row["research_gate_reason_count"] = len(unique_reasons)
        annotated.append(row)
    return pd.DataFrame(annotated)


def _research_gate_details(
    row: Mapping[str, Any],
    *,
    stability: Mapping[str, Any],
    regime_records: list[dict[str, Any]],
    side_records: list[dict[str, Any]],
    side_veto_controls: Mapping[tuple[tuple[str, str, str, str, str, str], str], Mapping[str, Any]],
    split_records: list[dict[str, Any]],
    cost_stress_records: list[dict[str, Any]],
    spec: HistoricalResearchCycleSpec,
    data_source: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if data_source.get("source_type") != "historical_fixture_pack":
        reasons.append("historical_fixture_pack_source_required")
    if data_source.get("synthetic") is not False:
        reasons.append("non_synthetic_fixture_evidence_required")
    if not isinstance(data_source.get("validation"), Mapping) or data_source["validation"].get("valid") is not True:
        reasons.append("validated_fixture_pack_required")
    reasons.extend(source_capability_gate_reasons(data_source))
    if str(row.get("baseline_comparator_coverage_status") or "") != "complete":
        reasons.append("baseline_comparator_coverage_incomplete")
    if str(row.get("comparator_role") or "") == "no_trade_baseline":
        reasons.append("no_trade_baseline_cannot_be_research_pack_candidate")
    expectancy_vs_no_trade = _optional_float(row.get("expectancy_vs_no_trade"))
    if expectancy_vs_no_trade is None or expectancy_vs_no_trade <= 0.0:
        reasons.append("no_trade_baseline_not_beaten")
    if bool(row.get("feature_ablation_passed")) is not True:
        reasons.append("candidate_feature_ablation_evidence_required")
    ablation_failure_reasons = [
        reason for reason in str(row.get("ablation_failure_reasons") or "").split("|") if reason
    ]
    reasons.extend(ablation_failure_reasons)

    side_details = _side_evidence_details(row, side_records, side_veto_controls=side_veto_controls)
    reasons.extend(side_details["reasons"])
    regime_details = _regime_evidence_details(regime_records)
    reasons.extend(regime_details["reasons"])
    split_details = _split_evidence_details(
        split_records,
        max_single_split_pnl_share=float(spec.validation.max_single_split_pnl_share),
        required_split_count=int(row.get("required_split_count", spec.validation.min_splits)),
        trade_count_floor=int(spec.validation.trade_count_floor),
        required_validation_methods=spec.validation.split_modes,
    )
    reasons.extend(split_details["reasons"])
    cost_details = _cost_stress_evidence_details(
        cost_stress_records,
        min_survival_rate=float(spec.validation.min_cost_stress_survival_rate),
    )
    reasons.extend(cost_details["reasons"])
    stability_reasons = _stability_row_gate_reasons(stability)
    reasons.extend(stability_reasons)
    return {
        "gate_reasons": list(dict.fromkeys(reasons)),
        "side_evidence_evaluated": bool(side_records),
        "side_evidence_count": int(side_details["count"]),
        "side_evidence_status": side_details["status"],
        "side_evidence_sides": "|".join(side_details["sides"]),
        "side_evidence_policy": side_details["policy"],
        "side_evidence_required_sides": "|".join(side_details["required_sides"]),
        "side_evidence_exception": bool(side_details["exception"]),
        "side_veto_declared": bool(side_details["side_veto_declared"]),
        "side_veto_allowed_side": side_details["side_veto_allowed_side"],
        "side_veto_stage": side_details["side_veto_stage"],
        "side_veto_control_candidate_id": side_details["side_veto_control_candidate_id"],
        "side_veto_control_side": side_details["side_veto_control_side"],
        "side_veto_control_status": side_details["side_veto_control_status"],
        "side_veto_control_trade_count": int(side_details["side_veto_control_trade_count"]),
        "side_veto_control_expectancy_vs_no_trade": side_details["side_veto_control_expectancy_vs_no_trade"],
        "side_veto_control_net_return": side_details["side_veto_control_net_return"],
        "side_veto_control_reasons": "|".join(side_details["side_veto_control_reasons"]),
        "regime_evidence_evaluated": bool(regime_records),
        "regime_evidence_count": int(regime_details["count"]),
        "regime_evidence_status": regime_details["status"],
        "regime_evidence_regimes": "|".join(regime_details["regimes"]),
        "cost_stress_scenario_count": int(cost_details["count"]),
        "cost_stress_scenario_status": cost_details["status"],
        "cost_stress_scenarios": "|".join(cost_details["scenarios"]),
        "cost_stress_survival_floor": float(cost_details["min_survival_rate"]),
        "cost_stress_survival_rate": float(cost_details["survival_rate"]),
        "cost_stress_survival_floor_status": cost_details["survival_status"],
        "cost_stress_failed_scenarios": "|".join(cost_details["failed_scenarios"]),
        "split_trade_count_floor": int(split_details["trade_count_floor"]),
        "min_split_trade_count": int(split_details["min_split_trade_count"]),
        "split_trade_count_floor_status": split_details["trade_count_floor_status"],
        "split_validation_method_status": split_details["validation_method_status"],
        "split_validation_methods": "|".join(split_details["validation_methods"]),
        "split_missing_validation_methods": "|".join(split_details["missing_validation_methods"]),
        "max_single_split_pnl_share": float(split_details["max_single_split_pnl_share"]),
        "split_dominance_status": split_details["status"],
        "stability_region_decision": stability.get("decision"),
        "stability_region_validation_enriched": bool(stability.get("validation_enriched", False)),
    }


def _side_evidence_details(
    row: Mapping[str, Any],
    records: list[dict[str, Any]],
    *,
    side_veto_controls: Mapping[tuple[tuple[str, str, str, str, str, str], str], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    sides = sorted(
        str(record.get("side") or "").lower()
        for record in records
        if int(record.get("trade_count", 0)) > 0
    )
    real_sides = sorted({side for side in sides if side in {"long", "short"}})
    reasons: list[str] = []
    exception = False
    policy = "long_short_pair_required"
    required_sides = ["long", "short"]
    side_veto_declared = False
    side_veto_allowed_side = ""
    side_veto_stage = ""
    side_veto_control_candidate_id = ""
    side_veto_control_side = ""
    side_veto_control_status = "not_applicable"
    side_veto_control_trade_count = 0
    side_veto_control_expectancy_vs_no_trade: float | None = None
    side_veto_control_net_return: float | None = None
    side_veto_control_reasons: list[str] = []
    side_veto = _explicit_side_veto_contract(row)
    if side_veto is not None:
        policy = "explicit_one_sided_side_veto"
        side_veto_declared = True
        side_veto_allowed_side = side_veto["allowed_side"]
        side_veto_stage = side_veto["stage"]
        required_sides = [side_veto_allowed_side]
    if not records:
        reasons.append("candidate_side_evidence_required")
    if real_sides != sorted(set(sides)):
        reasons.append("candidate_side_evidence_invalid_labels")
    if str(row.get("strategy_id") or "") == NO_TRADE_BASELINE_STRATEGY_ID:
        policy = "no_trade_baseline_exception"
        exception = True
    elif side_veto is not None:
        if set(real_sides) != {side_veto_allowed_side}:
            side_veto_control_reasons.append("candidate_side_veto_declared_side_evidence_mismatch")
        control = _side_veto_control_row(row, side_veto_controls or {})
        if control is None:
            side_veto_control_reasons.append("candidate_side_veto_control_evidence_required")
        else:
            side_veto_control_candidate_id = str(control.get("candidate_id") or "")
            side_veto_control_side = str(control.get("side_veto_allowed_side") or _opposite_side(side_veto_allowed_side))
            side_veto_control_trade_count = int(control.get("trade_count", 0) or 0)
            side_veto_control_expectancy_vs_no_trade = _optional_float(control.get("expectancy_vs_no_trade"))
            side_veto_control_net_return = _optional_float(control.get("net_return_after_fees_slippage_funding"))
            metric_sides = {item for item in str(control.get("side_veto_metric_sides") or "").split("|") if item}
            if metric_sides != {_opposite_side(side_veto_allowed_side)}:
                side_veto_control_reasons.append("candidate_side_veto_control_side_evidence_mismatch")
            if side_veto_control_trade_count <= 0:
                side_veto_control_reasons.append("candidate_side_veto_control_trade_count_required")
            if side_veto_control_expectancy_vs_no_trade is None or side_veto_control_expectancy_vs_no_trade > 0.0:
                side_veto_control_reasons.append("candidate_side_veto_control_not_negative_vs_no_trade")
            if side_veto_control_net_return is None or side_veto_control_net_return > 0.0:
                side_veto_control_reasons.append("candidate_side_veto_control_net_return_not_negative")
        transparent_delta = _optional_float(row.get("expectancy_vs_transparent_default"))
        if not str(row.get("transparent_default_comparator_candidate_id") or ""):
            side_veto_control_reasons.append("transparent_baseline_evidence_required")
        elif transparent_delta is None or transparent_delta <= 0.0:
            side_veto_control_reasons.append("transparent_baseline_not_beaten")
        side_veto_control_status = "passed" if not side_veto_control_reasons else "failed"
        reasons.extend(side_veto_control_reasons)
    elif set(real_sides) != {"long", "short"}:
        reasons.append("candidate_side_evidence_long_short_required")
    return {
        "status": "complete" if not reasons else "incomplete",
        "count": len(real_sides),
        "sides": real_sides,
        "policy": policy,
        "required_sides": required_sides,
        "exception": exception,
        "side_veto_declared": side_veto_declared,
        "side_veto_allowed_side": side_veto_allowed_side,
        "side_veto_stage": side_veto_stage,
        "side_veto_control_candidate_id": side_veto_control_candidate_id,
        "side_veto_control_side": side_veto_control_side,
        "side_veto_control_status": side_veto_control_status,
        "side_veto_control_trade_count": side_veto_control_trade_count,
        "side_veto_control_expectancy_vs_no_trade": side_veto_control_expectancy_vs_no_trade,
        "side_veto_control_net_return": side_veto_control_net_return,
        "side_veto_control_reasons": side_veto_control_reasons,
        "reasons": reasons,
    }


def _explicit_side_veto_contract(row: Mapping[str, Any]) -> dict[str, str] | None:
    if str(row.get("strategy_id") or "") != SPARSE_EVENT_FILTER_STRATEGY_ID:
        return None
    params = _row_parameters(row)
    allowed_side = str(params.get("allowed_sides") or "").strip().lower()
    if allowed_side not in SIDE_VETO_ALLOWED_SIDES:
        return None
    stage = str(params.get("side_filter_stage") or "").strip().lower()
    if stage not in {"pre_selection", "post_selection"}:
        return None
    return {"allowed_side": allowed_side, "stage": stage}


def _row_parameters(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("resolved_parameters_json") or row.get("parameters_json") or "{}"
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        payload = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _side_veto_control_lookup(
    rows: list[Mapping[str, Any]],
    side_by_candidate: Mapping[str, list[dict[str, Any]]],
) -> dict[tuple[tuple[str, str, str, str, str, str], str], Mapping[str, Any]]:
    controls: dict[tuple[tuple[str, str, str, str, str, str], str], Mapping[str, Any]] = {}
    for row in rows:
        contract = _explicit_side_veto_contract(row)
        if contract is None:
            continue
        candidate_id = str(row.get("candidate_id") or "")
        enriched = dict(row)
        enriched["side_veto_allowed_side"] = contract["allowed_side"]
        enriched["side_veto_stage"] = contract["stage"]
        enriched["trade_count"] = int(row.get("trade_count", 0) or 0)
        control_sides = {
            str(record.get("side") or "").lower()
            for record in side_by_candidate.get(candidate_id, [])
            if int(record.get("trade_count", 0) or 0) > 0
        }
        enriched["side_veto_metric_sides"] = "|".join(sorted(side for side in control_sides if side in {"long", "short"}))
        controls[(_side_veto_pair_key(row), contract["allowed_side"])] = enriched
    return controls


def _side_veto_control_row(
    row: Mapping[str, Any],
    controls: Mapping[tuple[tuple[str, str, str, str, str, str], str], Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    contract = _explicit_side_veto_contract(row)
    if contract is None:
        return None
    return controls.get((_side_veto_pair_key(row), _opposite_side(contract["allowed_side"])))


def _side_veto_pair_key(row: Mapping[str, Any]) -> tuple[str, str, str, str, str, str]:
    params = _row_parameters(row)
    params.pop("allowed_sides", None)
    return (
        str(row.get("strategy_id") or ""),
        str(row.get("feature_set_id") or ""),
        str(row.get("holding_window") or ""),
        str(row.get("exit_policy_id") or "fixed_holding_window"),
        str(row.get("exit_policy_params_json") or "{}"),
        json.dumps(dict(sorted(params.items())), sort_keys=True, separators=(",", ":"), default=str),
    )


def _opposite_side(side: str) -> str:
    return "short" if str(side).lower() == "long" else "long"


def _regime_evidence_details(records: list[dict[str, Any]]) -> dict[str, Any]:
    invalid = {"", "all", "aggregate"}
    regimes = sorted(
        str(record.get("regime") or "").lower()
        for record in records
        if int(record.get("trade_count", 0)) > 0
    )
    real_regimes = sorted({regime for regime in regimes if regime not in invalid and regime not in {"missing", "unknown"}})
    reasons: list[str] = []
    if not records:
        reasons.append("candidate_regime_evidence_required")
    if any(regime in invalid for regime in regimes):
        reasons.append("candidate_regime_evidence_aggregate_label_forbidden")
    if len(real_regimes) < 2:
        reasons.append("candidate_regime_evidence_multiple_regimes_required")
    return {
        "status": "complete" if not reasons else "incomplete",
        "count": len(real_regimes),
        "regimes": real_regimes,
        "reasons": reasons,
    }


def _split_evidence_details(
    records: list[dict[str, Any]],
    *,
    max_single_split_pnl_share: float,
    required_split_count: int,
    trade_count_floor: int,
    required_validation_methods: tuple[str, ...],
) -> dict[str, Any]:
    reasons: list[str] = []
    if not records:
        reasons.append("candidate_split_evidence_required")
        return {
            "status": "incomplete",
            "max_single_split_pnl_share": 1.0,
            "trade_count_floor": int(trade_count_floor),
            "min_split_trade_count": 0,
            "trade_count_floor_status": "failed",
            "validation_method_status": "incomplete",
            "validation_methods": [],
            "missing_validation_methods": list(required_validation_methods),
            "reasons": reasons,
        }
    split_ids = {str(record.get("split_id") or "") for record in records if str(record.get("split_id") or "")}
    if len(split_ids) < int(required_split_count):
        reasons.append("candidate_split_evidence_count_below_required")
    if any(int(record.get("trade_count", 0)) <= 0 for record in records):
        reasons.append("candidate_split_evidence_trade_count_required")
    trade_counts = [int(record.get("trade_count", 0)) for record in records]
    min_split_trade_count = min(trade_counts) if trade_counts else 0
    if min_split_trade_count < int(trade_count_floor):
        reasons.append("candidate_split_trade_count_below_floor")
    validation_methods = sorted({str(record.get("validation_method") or "") for record in records if str(record.get("validation_method") or "")})
    missing_validation_methods = sorted(set(required_validation_methods) - set(validation_methods))
    if missing_validation_methods:
        reasons.append("candidate_split_validation_method_coverage_incomplete")
    returns = [abs(float(record.get("net_return_after_fees_slippage_funding", 0.0))) for record in records]
    total = sum(returns)
    max_share = max(returns) / total if total > 0.0 else 0.0
    if max_share > float(max_single_split_pnl_share):
        reasons.append("max_single_split_pnl_share_above_limit")
    return {
        "status": "complete" if not reasons else "incomplete",
        "max_single_split_pnl_share": float(max_share),
        "trade_count_floor": int(trade_count_floor),
        "min_split_trade_count": int(min_split_trade_count),
        "trade_count_floor_status": "passed" if min_split_trade_count >= int(trade_count_floor) else "failed",
        "validation_method_status": "complete" if not missing_validation_methods else "incomplete",
        "validation_methods": validation_methods,
        "missing_validation_methods": missing_validation_methods,
        "reasons": reasons,
    }


def _cost_stress_evidence_details(records: list[dict[str, Any]], *, min_survival_rate: float) -> dict[str, Any]:
    required = {str(scenario["scenario_id"]) for scenario in _cost_stress_scenarios()}
    scenarios = sorted({str(record.get("scenario_id") or "") for record in records})
    reasons: list[str] = []
    missing = sorted(required - set(scenarios))
    if missing:
        reasons.append("cost_stress_scenario_set_incomplete")
    if any(int(record.get("trade_count", 0)) <= 0 for record in records):
        reasons.append("candidate_cost_stress_evidence_trade_count_required")
    required_records = [
        record for record in records
        if str(record.get("scenario_id") or "") in required
    ]
    survival_by_scenario = {
        str(record.get("scenario_id") or ""): _cost_stress_record_survived(record)
        for record in required_records
    }
    failed_scenarios = sorted(
        scenario for scenario, survived in survival_by_scenario.items()
        if scenario and not survived
    )
    survival_rate = (
        sum(1 for survived in survival_by_scenario.values() if survived) / len(required)
        if required
        else 0.0
    )
    if survival_rate < float(min_survival_rate):
        reasons.append("cost_stress_survival_rate_below_floor")
    return {
        "status": "complete" if not reasons else "incomplete",
        "count": len(set(scenarios) & required),
        "scenarios": [scenario for scenario in scenarios if scenario],
        "min_survival_rate": float(min_survival_rate),
        "survival_rate": float(survival_rate),
        "survival_status": "passed" if survival_rate >= float(min_survival_rate) else "failed",
        "failed_scenarios": failed_scenarios,
        "reasons": reasons,
    }


def _cost_stress_record_survived(record: Mapping[str, Any]) -> bool:
    if "stress_survival_score" in record:
        score = float(record.get("stress_survival_score", 0.0))
    else:
        score = float(record.get("stressed_expectancy", 0.0)) + float(record.get("stressed_net_return", 0.0))
    return score > 0.0 and str(record.get("scenario_status") or "evaluated") == "evaluated"


def _feature_missingness_for_candidate(
    feature_build_manifest: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> float:
    feature_set_id = str(candidate["feature_set_id"])
    for row in feature_build_manifest.get("feature_sets", []):
        if isinstance(row, Mapping) and str(row.get("feature_set_id")) == feature_set_id:
            return float(row.get("missingness_rate", 0.0))
    return 0.0


def _records_by_candidate(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record["candidate_id"]), []).append(record)
    return grouped


def _split_consistency(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    scores = [
        float(record.get("costed_expectancy", 0.0))
        + float(record.get("net_return_after_fees_slippage_funding", 0.0))
        + float(record.get("max_drawdown", 0.0))
        for record in records
    ]
    pass_rate = sum(score >= 0.0 for score in scores) / len(scores)
    mean_score = sum(scores) / len(scores)
    dispersion = _std_float(scores) / (abs(mean_score) + 1.0)
    return float(pass_rate * max(0.0, 1.0 - min(1.0, dispersion)))


def _cost_stress_survival(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    scores = [
        (
            float(record.get("stress_survival_score", 0.0))
            if "stress_survival_score" in record
            else float(record.get("stressed_expectancy", 0.0)) + float(record.get("stressed_net_return", 0.0))
        )
        for record in records
    ]
    return float(sum(score > 0.0 for score in scores) / len(scores))


def _side_balance(long_count: int, short_count: int) -> float:
    total = max(0, long_count) + max(0, short_count)
    if total == 0:
        return 0.0
    return float(1.0 - abs(long_count - short_count) / total)


def _regime_coverage(split_by_regime: Any) -> float:
    if not isinstance(split_by_regime, Mapping):
        return 0.0
    non_empty = sum(
        int(value.get("trade_count", 0)) > 0
        for value in split_by_regime.values()
        if isinstance(value, Mapping)
    )
    return float(min(1.0, non_empty / 3.0))


def _std_float(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return float((sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5)


def _optional_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        numeric = float(value)
        if not math.isfinite(numeric):
            return None
        return numeric
    except (TypeError, ValueError):
        return None


def _regime_metric_records(
    candidate: Mapping[str, Any],
    *,
    metrics: Mapping[str, Any],
    manifest_path: Path,
    trades_path: Path,
) -> list[dict[str, Any]]:
    if trades_path.exists():
        trades = pd.read_parquet(trades_path)
        if not trades.empty and "regime" in trades.columns:
            records: list[dict[str, Any]] = []
            for regime, group in trades.groupby(trades["regime"].astype(str).str.lower(), dropna=False):
                returns = pd.to_numeric(group.get("net_return", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
                records.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "strategy_id": candidate["strategy_id"],
                        "feature_set_id": candidate["feature_set_id"],
                        "holding_window": candidate["holding_window"],
                        "regime": str(regime).lower(),
                        "trade_count": int(len(group)),
                        "costed_expectancy": float(returns.mean()) if len(returns) else 0.0,
                        "net_return_after_fees_slippage_funding": (
                            float((1.0 + returns).prod() - 1.0) if len(returns) else 0.0
                        ),
                        "summed_net_return_after_fees_slippage_funding": float(returns.sum()),
                        "hit_rate": float((returns > 0.0).mean()) if len(returns) else 0.0,
                        "metric_scope": "aggregate_backtest_regime",
                        "backtest_manifest_path": str(manifest_path),
                    }
                )
            return records
    split_by_regime = metrics.get("split_by_regime", {})
    if not isinstance(split_by_regime, Mapping):
        return []
    records: list[dict[str, Any]] = []
    for regime, payload in sorted(split_by_regime.items(), key=lambda item: str(item[0])):
        if not isinstance(payload, Mapping):
            continue
        net_return_sum = float(payload.get("net_return_sum", 0.0))
        records.append(
            {
                "candidate_id": candidate["candidate_id"],
                "strategy_id": candidate["strategy_id"],
                "feature_set_id": candidate["feature_set_id"],
                "holding_window": candidate["holding_window"],
                "regime": str(regime).lower(),
                "trade_count": int(payload.get("trade_count", 0)),
                "costed_expectancy": float(payload.get("expectancy", 0.0)),
                "net_return_after_fees_slippage_funding": net_return_sum,
                "summed_net_return_after_fees_slippage_funding": net_return_sum,
                "hit_rate": float(payload.get("hit_rate", 0.0)),
                "metric_scope": "aggregate_backtest_regime",
                "backtest_manifest_path": str(manifest_path),
            }
        )
    return records


def _side_metric_records(
    candidate: Mapping[str, Any],
    *,
    trades_path: Path,
    manifest_path: Path,
) -> list[dict[str, Any]]:
    if not trades_path.exists():
        return []
    trades = pd.read_parquet(trades_path)
    if trades.empty or "side" not in trades.columns:
        return []
    records: list[dict[str, Any]] = []
    for side, group in trades.groupby(trades["side"].astype(str).str.lower(), dropna=False):
        returns = pd.to_numeric(group.get("net_return", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
        compounded_return = float((1.0 + returns).prod() - 1.0) if len(returns) else 0.0
        records.append(
            {
                "candidate_id": candidate["candidate_id"],
                "strategy_id": candidate["strategy_id"],
                "feature_set_id": candidate["feature_set_id"],
                "holding_window": candidate["holding_window"],
                "side": str(side).lower(),
                "trade_count": int(len(group)),
                "costed_expectancy": float(returns.mean()) if len(returns) else 0.0,
                "net_return_after_fees_slippage_funding": compounded_return,
                "summed_net_return_after_fees_slippage_funding": float(returns.sum()),
                "hit_rate": float((returns > 0.0).mean()) if len(returns) else 0.0,
                "metric_scope": "aggregate_backtest_side",
                "backtest_manifest_path": str(manifest_path),
                "trades_path": str(trades_path),
                "trades_sha256": _file_sha256(trades_path),
            }
        )
    return records


def _metric_frame(records: list[dict[str, Any]], *, columns: list[str]) -> pd.DataFrame:
    if records:
        return pd.DataFrame(records).reindex(columns=columns)
    return pd.DataFrame(columns=columns)


def _regime_metric_columns() -> list[str]:
    return [
        "candidate_id",
        "strategy_id",
        "feature_set_id",
        "holding_window",
        "regime",
        "trade_count",
        "costed_expectancy",
        "net_return_after_fees_slippage_funding",
        "summed_net_return_after_fees_slippage_funding",
        "hit_rate",
        "metric_scope",
        "backtest_manifest_path",
    ]


def _side_metric_columns() -> list[str]:
    return [
        "candidate_id",
        "strategy_id",
        "feature_set_id",
        "holding_window",
        "side",
        "trade_count",
        "costed_expectancy",
        "net_return_after_fees_slippage_funding",
        "summed_net_return_after_fees_slippage_funding",
        "hit_rate",
        "metric_scope",
        "backtest_manifest_path",
        "trades_path",
        "trades_sha256",
    ]


def _metrics_by_holding_window(rankings: pd.DataFrame) -> pd.DataFrame:
    stats_by_window: dict[str, dict[str, Any]] = {}
    for holding_window, group in rankings.groupby("holding_window", dropna=False):
        stats_by_window[str(holding_window)] = {
            "candidate_count": int(len(group)),
            "holding_window_trade_count": int(group["trade_count"].sum()),
            "median_costed_expectancy": float(group["costed_expectancy"].median()),
            "best_final_score": float(group["final_score"].max()),
        }
    records = []
    for row in rankings.to_dict("records"):
        holding_window = str(row["holding_window"])
        stats = stats_by_window[holding_window]
        records.append(
            {
                "candidate_id": row["candidate_id"],
                "strategy_id": row["strategy_id"],
                "feature_set_id": row["feature_set_id"],
                "holding_window": holding_window,
                "trade_count": int(row["trade_count"]),
                "costed_expectancy": float(row["costed_expectancy"]),
                "net_return_after_fees_slippage_funding": float(row["net_return_after_fees_slippage_funding"]),
                **stats,
            }
        )
    return pd.DataFrame(records)


def _stability_regions(candidate_results: Mapping[str, CandidateResult]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for region in rank_by_stability(candidate_results.values(), require_validation_evidence=True):
        result = candidate_results[region.center_candidate_id]
        config = result.config
        records.append(
            {
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_id": region.center_candidate_id,
                "strategy_id": config.strategy_id,
                "feature_set_id": config.feature_set_id,
                "holding_window": config.holding_window,
                "exit_policy_id": config.exit_policy_id,
                "exit_policy_params_json": _stable_json(dict(config.exit_policy_params or {})),
                "parameters_json": json.dumps(dict(config.parameters), sort_keys=True, separators=(",", ":"), default=str),
                "stability_scope": "candidate_result_region_of_stability",
                **region.to_payload(),
            }
        )
    return pd.DataFrame(records)


def _candidate_gate_report(
    rankings: pd.DataFrame,
    stability_regions: pd.DataFrame,
    *,
    spec: HistoricalResearchCycleSpec,
) -> pd.DataFrame:
    stability_by_candidate = {
        str(row["candidate_id"]): row
        for row in stability_regions.to_dict("records")
    }
    cycle_spec = spec.to_payload()
    records: list[dict[str, Any]] = []
    for row in rankings.to_dict("records"):
        candidate_id = str(row["candidate_id"])
        gate = evaluate_research_candidate_gate_from_row(
            candidate_id=candidate_id,
            ranking_row=row,
            cycle_spec=cycle_spec,
        )
        stability = stability_by_candidate.get(candidate_id, {})
        gate_reasons = [
            *gate.reasons,
            *[reason for reason in str(row.get("failure_reasons") or "").split("|") if reason],
            *_stability_row_gate_reasons(stability),
        ]
        gate_status = "passed" if not gate_reasons else "blocked"
        records.append(
            {
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_id": candidate_id,
                "strategy_id": row["strategy_id"],
                "feature_set_id": row["feature_set_id"],
                "holding_window": row["holding_window"],
                "aggregate_rank": int(row.get("aggregate_rank", row.get("rank", 0))),
                "optimizer_rank": int(row.get("optimizer_rank", 0)),
                "gate_status": gate_status,
                "pack_eligible": gate_status == "passed",
                "gate_reasons": "|".join(dict.fromkeys(gate_reasons)),
                "ranking_decision": row.get("decision"),
                "ranking_failure_reasons": row.get("failure_reasons"),
                "split_evaluated": bool(row.get("split_evaluated")),
                "cost_stress_evaluated": bool(row.get("cost_stress_evaluated")),
                "stability_evaluated": bool(row.get("stability_evaluated")),
                "side_evidence_policy": row.get("side_evidence_policy"),
                "side_evidence_required_sides": row.get("side_evidence_required_sides"),
                "side_veto_declared": bool(row.get("side_veto_declared", False)),
                "side_veto_allowed_side": row.get("side_veto_allowed_side"),
                "side_veto_stage": row.get("side_veto_stage"),
                "side_veto_control_candidate_id": row.get("side_veto_control_candidate_id"),
                "side_veto_control_side": row.get("side_veto_control_side"),
                "side_veto_control_status": row.get("side_veto_control_status"),
                "side_veto_control_trade_count": int(row.get("side_veto_control_trade_count", 0) or 0),
                "side_veto_control_expectancy_vs_no_trade": row.get("side_veto_control_expectancy_vs_no_trade"),
                "side_veto_control_net_return": row.get("side_veto_control_net_return"),
                "side_veto_control_reasons": row.get("side_veto_control_reasons"),
                "split_evaluation_count": int(row.get("split_evaluation_count", 0)),
                "cost_stress_evaluation_count": int(row.get("cost_stress_evaluation_count", 0)),
                "required_split_count": int(row.get("required_split_count", 0)),
                "required_cost_stress_count": int(row.get("required_cost_stress_count", 0)),
                "split_trade_count_floor": int(row.get("split_trade_count_floor", 0)),
                "min_split_trade_count": int(row.get("min_split_trade_count", 0)),
                "cost_stress_survival_floor": float(row.get("cost_stress_survival_floor", 0.0)),
                "cost_stress_survival_rate": float(row.get("cost_stress_survival_rate", 0.0)),
                "stability_region_decision": stability.get("decision"),
                "stability_validation_scope": stability.get(
                    "stability_validation_scope",
                    row.get("stability_validation_scope"),
                ),
                "stability_validation_enriched": bool(stability.get("validation_enriched", False)),
                **_ranking_materialized_prediction_overlay_provenance(row),
                "candidate_acceptance_scope": (
                    "research_only_pack_eligible_not_promotion_ready"
                    if gate_status == "passed"
                    else "research_gate_failed_closed"
                ),
            }
        )
    return pd.DataFrame(records)


def _ranking_materialized_prediction_overlay_provenance(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in row.items()
        if str(key).startswith("materialized_prediction_overlay_")
    }


def _stability_row_gate_reasons(stability: Mapping[str, Any]) -> list[str]:
    if not stability:
        return ["stability_region_row_required"]
    reasons: list[str] = []
    if bool(stability.get("validation_enriched")) is not True:
        reasons.append("stability_region_validation_enriched_required")
    if str(stability.get("stability_validation_scope") or "") != "split_cost_stress_enriched":
        reasons.append("stability_region_split_cost_stress_scope_required")
    if str(stability.get("decision") or "") != "accepted_region":
        reasons.append("stability_region_accepted_decision_required")
    return reasons


def _trial_budget_report(
    *,
    spec: HistoricalResearchCycleSpec,
    candidates: list[dict[str, Any]],
    rankings: pd.DataFrame,
    backtest_index_records: list[dict[str, Any]],
    split_records: list[dict[str, Any]],
    cost_stress_records: list[dict[str, Any]],
    search_mode: str,
    search_method: str,
    performance_plan: Mapping[str, Any],
) -> dict[str, Any]:
    source_counts = _candidate_source_counts(candidates)
    comparator_count = sum(1 for candidate in candidates if bool(candidate.get("comparator_injected", False)))
    shortlisted_count = int(rankings["split_evaluated"].fillna(False).astype(bool).sum()) if "split_evaluated" in rankings else 0
    stability_acceleration = _stability_region_acceleration_counters(
        performance_plan=performance_plan,
        backtest_index_records=backtest_index_records,
        shortlisted_count=shortlisted_count,
    )
    return {
        "trial_budget_report_version": TRIAL_BUDGET_REPORT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "intended_use": "research_diagnostic_only",
        "diagnostic_only": True,
        "candidate_pack_metric_gate_enabled": False,
        "cycle_id": spec.cycle_id,
        "symbol": spec.symbol,
        "candidate_search_mode": search_mode,
        "candidate_search_method": search_method,
        "performance_plan": dict(performance_plan),
        "bruteforce_equivalent_candidate_count": int(
            performance_plan.get("bruteforce_equivalent_candidate_count", 0)
        ),
        "sampled_fraction_of_bruteforce": float(
            performance_plan.get("sampled_fraction_of_bruteforce", 0.0)
        ),
        "bruteforce_avoidance_ratio": float(
            performance_plan.get("bruteforce_avoidance_ratio", 1.0)
        ),
        "compute_policy": dict(performance_plan.get("compute_policy") or {}),
        "stability_region_acceleration_counters": stability_acceleration,
        "optimizer_method_sequence": list(spec.optimizer.method_sequence),
        "budget_policy": {
            "max_candidates_per_strategy": int(spec.optimizer.max_candidates_per_strategy),
            "top_regions_to_refine": int(spec.optimizer.top_regions_to_refine),
            "shortlist_policy": "top_regions_to_refine_candidates_receive_split_and_cost_stress",
            "deduplication_scope": "candidate_config_sha256_unique_candidate_space",
        },
        "candidate_counts": {
            "candidate_count": int(len(candidates)),
            "research_candidate_count": int(max(0, len(candidates) - comparator_count)),
            "comparator_candidate_count": int(comparator_count),
            "shortlisted_candidate_count": int(shortlisted_count),
            "pre_dedup_candidate_count": None,
            "deduplicated_candidate_count": int(len(candidates)),
            "duplicate_candidate_count": None,
            "duplicate_count_scope": "pre-dedup_generation_attempts_not_materialized_by_historical_runner",
        },
        "effective_trial_count": int(len(candidates)),
        "aggregate_backtest_count": int(len(candidates)),
        "split_backtest_count": int(len(split_records)),
        "cost_stress_backtest_count": int(len(cost_stress_records)),
        "total_backtest_evaluation_count": int(len(backtest_index_records)),
        "trials_by_strategy": _candidate_counts(candidates, "strategy_id"),
        "trials_by_feature_set": _candidate_counts(candidates, "feature_set_id"),
        "trials_by_holding_window": _candidate_counts(candidates, "holding_window"),
        "trials_by_exit_policy": _candidate_counts(candidates, "exit_policy_id"),
        "trials_by_candidate_source": source_counts,
        "trials_by_search_method": _candidate_counts(candidates, "search_method"),
        "trials_by_optimizer_stage": source_counts,
        "budget_status": "diagnostic_only_reported",
        "budget_reasons": [],
        "limitations": [
            "Trial accounting is candidate-space based and does not claim independent OOS trials.",
            "Injected comparators are counted because they affect ranking and candidate-family comparisons.",
            "Duplicate generation attempts before candidate-id deduplication are not materialized by the historical runner.",
        ],
    }


def _stability_region_acceleration_counters(
    *,
    performance_plan: Mapping[str, Any],
    backtest_index_records: list[dict[str, Any]],
    shortlisted_count: int,
) -> dict[str, Any]:
    aggregate_records = [
        record
        for record in backtest_index_records
        if str(record.get("evaluation_scope") or "") == "aggregate"
    ]
    gpu_screened = sum(str(record.get("backtest_backend_used") or "") in CUDA_BACKTEST_BACKENDS for record in aggregate_records)
    tensorcore_screened = sum(
        str(record.get("backtest_backend_used") or "") == "cuda_batched_fixed_holding"
        and str(record.get("gpu_execution_profile") or "") == "hybrid_tensorcore_screening"
        for record in aggregate_records
    )
    parity_rechecked = sum(
        str(record.get("backtest_backend_used") or "") in CUDA_BACKTEST_BACKENDS
        and str(record.get("backtest_parity_status") or "") in {"passed", "failed"}
        for record in aggregate_records
    )
    mismatch_count = sum(
        str(record.get("backtest_backend_used") or "") in CUDA_BACKTEST_BACKENDS
        and str(record.get("backtest_parity_status") or "") == "failed"
        for record in aggregate_records
    )
    cpu_screened = len(aggregate_records) - gpu_screened
    validation_records = [
        record
        for record in backtest_index_records
        if str(record.get("evaluation_scope") or "") in {"walk_forward_split", "cost_stress"}
        and str(record.get("candidate_id") or "")
    ]
    cpu_validated_ids = {
        str(record.get("candidate_id"))
        for record in validation_records
        if str(record.get("backtest_backend_used") or "") not in CUDA_BACKTEST_BACKENDS
    }
    gpu_validated_ids = {
        str(record.get("candidate_id"))
        for record in validation_records
        if str(record.get("backtest_backend_used") or "") in CUDA_BACKTEST_BACKENDS
    }
    cpu_reference_validated_ids = {
        str(record.get("candidate_id"))
        for record in validation_records
        if str(record.get("backtest_backend_used") or "") == "reference"
    }
    validation_backend_counts: dict[str, int] = {}
    for record in validation_records:
        backend = str(record.get("backtest_backend_used") or "unknown")
        validation_backend_counts[backend] = validation_backend_counts.get(backend, 0) + 1
    brute_force_count = int(performance_plan.get("bruteforce_equivalent_candidate_count", 0))
    materialized_count = int(performance_plan.get("materialized_search_candidate_count", len(aggregate_records)))
    return {
        "counter_version": "stability-region-acceleration-counters-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "bruteforce_equivalent_count": brute_force_count,
        "aggregate_screened_count": int(len(aggregate_records)),
        "gpu_screened_count": int(gpu_screened),
        "cpu_screened_count": int(cpu_screened),
        "cpu_validated_count": int(len(cpu_validated_ids)),
        "gpu_validated_count": int(len(gpu_validated_ids)),
        "tensorcore_screened_count": int(tensorcore_screened),
        "gpu_exact_screened_count": int(gpu_screened),
        "cpu_reference_validated_count": int(len(cpu_reference_validated_ids)),
        "parity_rechecked_count": int(parity_rechecked),
        "mismatch_count": int(mismatch_count),
        "validation_backend_counts": dict(sorted(validation_backend_counts.items())),
        "region_refined_count": int(shortlisted_count),
        "estimated_bruteforce_avoidance_ratio": (
            max(1.0, float(brute_force_count / max(materialized_count, 1)))
            if brute_force_count > 0
            else 1.0
        ),
    }


def _overfit_adjustment_report(
    *,
    spec: HistoricalResearchCycleSpec,
    rankings: pd.DataFrame,
    stability_regions: pd.DataFrame,
    split_records: list[dict[str, Any]],
    cost_stress_records: list[dict[str, Any]],
    trial_budget_report: Mapping[str, Any],
) -> dict[str, Any]:
    effective_trial_count = int(trial_budget_report.get("effective_trial_count", len(rankings)))
    stability_by_candidate = {str(row["candidate_id"]): row for row in stability_regions.to_dict("records")}
    split_by_candidate = _records_by_candidate(split_records)
    cost_by_candidate = _records_by_candidate(cost_stress_records)
    family_scores = _overfit_family_scores(rankings)
    candidate_rows: list[dict[str, Any]] = []
    for row in rankings.to_dict("records"):
        diagnostic = _overfit_candidate_diagnostic(
            row,
            stability=stability_by_candidate.get(str(row.get("candidate_id")), {}),
            split_records=split_by_candidate.get(str(row.get("candidate_id")), []),
            cost_stress_records=cost_by_candidate.get(str(row.get("candidate_id")), []),
            family_scores=family_scores,
            effective_trial_count=effective_trial_count,
        )
        candidate_rows.append(diagnostic)
    ordered = sorted(
        range(len(candidate_rows)),
        key=lambda index: (
            float(candidate_rows[index]["overfit_adjusted_score"]),
            str(candidate_rows[index]["candidate_id"]),
        ),
        reverse=True,
    )
    for rank, index in enumerate(ordered, start=1):
        candidate_rows[index]["overfit_adjusted_rank"] = rank

    family_rows = _overfit_family_diagnostics(rankings, family_scores)
    adjusted_scores = [float(row["overfit_adjusted_score"]) for row in candidate_rows]
    return {
        "overfit_adjustment_report_version": OVERFIT_ADJUSTMENT_REPORT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "intended_use": "research_diagnostic_only",
        "diagnostic_scope": "candidate_rankings_trial_budget_stability_split_cost_stress",
        "hard_gate_enabled": False,
        "candidate_pack_gate_enabled": False,
        "cycle_id": spec.cycle_id,
        "symbol": spec.symbol,
        "trial_budget_summary": {
            "effective_trial_count": effective_trial_count,
            "candidate_count": int(len(rankings)),
            "shortlisted_candidate_count": int(
                rankings["split_evaluated"].fillna(False).astype(bool).sum()
            )
            if "split_evaluated" in rankings
            else 0,
        },
        "adjustment_methods": [
            "trial_count_log_penalty_proxy",
            "family_rank_pbo_proxy",
            "split_cost_stress_cpcv_proxy",
            "stability_decision_penalty",
        ],
        "candidate_diagnostics": candidate_rows,
        "family_diagnostics": family_rows,
        "summary": {
            "candidate_count": int(len(candidate_rows)),
            "best_overfit_adjusted_score": max(adjusted_scores) if adjusted_scores else None,
            "median_overfit_adjusted_score": _median(adjusted_scores),
            "gate_decisions_changed": False,
        },
        "limitations": [
            "Deflated Sharpe, PBO, and CPCV values are deterministic diagnostics derived from available cycle artifacts, not formal OOS acceptance tests.",
            "No candidate-pack metric gate, promotion gate, or live-readiness gate is enabled by this report.",
            "Latest-window provider fixtures remain local research evidence and do not establish production performance.",
        ],
    }


def _overfit_candidate_diagnostic(
    row: Mapping[str, Any],
    *,
    stability: Mapping[str, Any],
    split_records: list[dict[str, Any]],
    cost_stress_records: list[dict[str, Any]],
    family_scores: Mapping[str, list[float]],
    effective_trial_count: int,
) -> dict[str, Any]:
    raw_score = _optional_float(row.get("optimizer_final_score"))
    if raw_score is None:
        raw_score = _optional_float(row.get("final_score")) or 0.0
    family_key = _overfit_family_key(row)
    scores = family_scores.get(family_key, [raw_score])
    sorted_scores = sorted(scores, reverse=True)
    family_count = len(sorted_scores)
    family_rank = sorted_scores.index(raw_score) + 1 if raw_score in sorted_scores else family_count
    family_median = _median(sorted_scores) or 0.0
    pbo_proxy = float((family_rank - 1) / max(1, family_count - 1)) if family_count > 1 else 0.0
    split_consistency = _bounded_unit(_optional_float(row.get("split_consistency")), default=0.0)
    cost_survival = _bounded_unit(_optional_float(row.get("cost_stress_survival")), default=0.0)
    cpcv_score_proxy = float(split_consistency * cost_survival)
    stability_decision = str(stability.get("decision") or row.get("stability_region_decision") or "")
    stability_penalty = 0.005 if stability_decision != "accepted_region" else 0.0
    trial_penalty = 0.001 * math.log1p(max(0, int(effective_trial_count) - 1))
    family_penalty = 0.001 * math.log1p(max(0, family_count - 1))
    pbo_penalty = 0.005 * pbo_proxy
    cpcv_penalty = 0.005 * (1.0 - cpcv_score_proxy)
    adjusted_score = raw_score - trial_penalty - family_penalty - pbo_penalty - cpcv_penalty - stability_penalty
    reasons = _overfit_diagnostic_reasons(
        row,
        split_records=split_records,
        cost_stress_records=cost_stress_records,
        pbo_proxy=pbo_proxy,
        cpcv_score_proxy=cpcv_score_proxy,
        stability_decision=stability_decision,
    )
    return {
        "candidate_id": str(row.get("candidate_id")),
        "strategy_id": str(row.get("strategy_id")),
        "feature_set_id": str(row.get("feature_set_id")),
        "holding_window": str(row.get("holding_window")),
        "exit_policy_id": str(row.get("exit_policy_id", "fixed_holding_window")),
        "raw_rank_score": float(raw_score),
        "raw_expectancy": _json_nullable(_optional_float(row.get("costed_expectancy"))),
        "trade_count": int(row.get("trade_count", 0) or 0),
        "split_count": int(len(split_records)),
        "cost_stress_survival_score": _json_nullable(_optional_float(row.get("cost_stress_survival"))),
        "stability_decision": stability_decision,
        "effective_trial_count": int(effective_trial_count),
        "family_trial_count": int(family_count),
        "family_rank": int(family_rank),
        "family_best_to_median_gap": float((sorted_scores[0] if sorted_scores else raw_score) - family_median),
        "deflated_sharpe": float(raw_score / math.sqrt(max(1.0, math.log1p(max(1, effective_trial_count))))),
        "pbo": pbo_proxy,
        "cpcv_score": cpcv_score_proxy,
        "overfit_adjusted_score": float(adjusted_score),
        "overfit_adjusted_rank": None,
        "diagnostic_status": "review" if reasons else "clear",
        "diagnostic_reasons": "|".join(reasons),
        "adjustment_scope": "diagnostic_only_not_candidate_gate",
    }


def _overfit_diagnostic_reasons(
    row: Mapping[str, Any],
    *,
    split_records: list[dict[str, Any]],
    cost_stress_records: list[dict[str, Any]],
    pbo_proxy: float,
    cpcv_score_proxy: float,
    stability_decision: str,
) -> list[str]:
    reasons: list[str] = []
    if int(row.get("trade_count", 0) or 0) <= 0:
        reasons.append("no_trades")
    if not split_records:
        reasons.append("split_validation_not_evaluated")
    if not cost_stress_records:
        reasons.append("cost_stress_not_evaluated")
    if pbo_proxy >= 0.75:
        reasons.append("weak_family_rank_proxy")
    if cpcv_score_proxy < 0.25:
        reasons.append("weak_split_cost_stress_proxy")
    if stability_decision != "accepted_region":
        reasons.append("stability_region_not_accepted")
    return reasons


def _overfit_family_scores(rankings: pd.DataFrame) -> dict[str, list[float]]:
    scores: dict[str, list[float]] = {}
    for row in rankings.to_dict("records"):
        score = _optional_float(row.get("optimizer_final_score"))
        if score is None:
            score = _optional_float(row.get("final_score")) or 0.0
        scores.setdefault(_overfit_family_key(row), []).append(float(score))
    return scores


def _overfit_family_diagnostics(rankings: pd.DataFrame, family_scores: Mapping[str, list[float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    family_meta: dict[str, Mapping[str, Any]] = {}
    for row in rankings.to_dict("records"):
        family_meta.setdefault(_overfit_family_key(row), row)
    for family_key, scores in sorted(family_scores.items()):
        meta = family_meta.get(family_key, {})
        ordered = sorted(scores, reverse=True)
        median_score = _median(ordered) or 0.0
        rows.append(
            {
                "family_key": family_key,
                "strategy_id": str(meta.get("strategy_id", "")),
                "feature_set_id": str(meta.get("feature_set_id", "")),
                "holding_window": str(meta.get("holding_window", "")),
                "exit_policy_id": str(meta.get("exit_policy_id", "fixed_holding_window")),
                "candidate_count": int(len(scores)),
                "best_optimizer_score": float(ordered[0]) if ordered else None,
                "median_optimizer_score": float(median_score),
                "best_to_median_gap": float((ordered[0] if ordered else 0.0) - median_score),
            }
        )
    return rows


def _overfit_family_key(row: Mapping[str, Any]) -> str:
    parts = [
        str(row.get("strategy_id", "")),
        str(row.get("feature_set_id", "")),
        str(row.get("holding_window", "")),
        str(row.get("exit_policy_id", "fixed_holding_window")),
    ]
    return "|".join(parts)


def _candidate_counts(candidates: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        key = str(candidate.get(field, "unknown"))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _bounded_unit(value: float | None, *, default: float) -> float:
    if value is None:
        return float(default)
    return float(max(0.0, min(1.0, value)))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return float((ordered[midpoint - 1] + ordered[midpoint]) / 2.0)


def _ablation_report(rankings: pd.DataFrame, *, spec: HistoricalResearchCycleSpec) -> dict[str, Any]:
    feature_rows = []
    for feature_set, group in rankings.groupby("feature_set_id", dropna=False):
        feature_rows.append(
            {
                "feature_set_id": str(feature_set),
                "candidate_count": int(len(group)),
                "best_final_score": float(group["final_score"].max()),
                "median_costed_expectancy": float(group["costed_expectancy"].median()),
                "wt3d_claim_accepted": False,
            }
        )
    candidate_rows = []
    for row in rankings.to_dict("records"):
        candidate_rows.append(
            {
                "candidate_id": row["candidate_id"],
                "strategy_id": row["strategy_id"],
                "feature_set_id": row["feature_set_id"],
                "holding_window": row["holding_window"],
                "feature_ablation_required": bool(row.get("feature_ablation_required", False)),
                "feature_ablation_passed": bool(row.get("feature_ablation_passed", False)),
                "ablation_evidence_status": _json_nullable(row.get("ablation_evidence_status")),
                "ablation_comparator_feature_set_id": _json_nullable(row.get("ablation_comparator_feature_set_id")),
                "ablation_comparator_candidate_id": _json_nullable(row.get("ablation_comparator_candidate_id")),
                "ablation_expectancy_delta": _json_nullable(row.get("ablation_expectancy_delta")),
                "ablation_final_score_delta": _json_nullable(row.get("ablation_final_score_delta")),
                "ablation_failure_reasons": _json_nullable(row.get("ablation_failure_reasons", "")) or "",
            }
        )
    return {
        "ablation_report_version": "historical-research-ablation-report-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "cycle_id": spec.cycle_id,
        "feature_rows": feature_rows,
        "candidate_rows": candidate_rows,
        "decision": "no_feature_claim_accepted",
        "reason": "Feature claims are not accepted here; research candidate pack eligibility is evaluated separately and remains observe-only and not promotion-ready.",
    }


def _json_nullable(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return value
    return value


def _research_pack_candidate_ids(rankings: pd.DataFrame, *, cycle_manifest_path: Path) -> list[str]:
    candidate_ids: list[str] = []
    for candidate_id in rankings["candidate_id"].astype(str).tolist():
        gate = evaluate_research_candidate_gate(
            cycle_manifest_path=cycle_manifest_path,
            candidate_id=candidate_id,
        )
        if gate.passed:
            candidate_ids.append(candidate_id)
    return candidate_ids


def _candidate_pack_output_dir(output_dir: Path, candidate_id: str) -> Path:
    return output_dir / "research_candidate_pack" / _safe_path_part(candidate_id)


def _safe_path_part(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in str(value)).strip("-")
    return "-".join(part for part in safe.split("-") if part) or "candidate"


def _rejection_report(rankings: pd.DataFrame, *, spec: HistoricalResearchCycleSpec, data_source: Mapping[str, Any]) -> str:
    lines = [
        f"# {spec.cycle_id} Rejection Report",
        "",
        "Research-only, observe-only, and not promotion-ready.",
        "",
        f"Data source: `{data_source.get('source_type')}`",
        "",
        "## Summary",
        "",
        f"- Candidate rows: `{len(rankings)}`",
        "- Candidate pack eligibility: evaluated in `candidate_gate_report.parquet` and the cycle manifest.",
        "- Scope: passing candidates are research-only evidence packs, not promotion or live-readiness artifacts.",
        "",
        "## Top Ranked Rejected Candidates",
    ]
    for row in rankings.head(10).to_dict("records"):
        lines.append(
            f"- `{row['candidate_id']}` score `{row['final_score']:.8f}` rejected: `{row['failure_reasons']}`"
        )
    lines.append("")
    return "\n".join(lines)


def _feature_set_missingness(frame: pd.DataFrame) -> float:
    missing_columns = [column for column in frame.columns if column.startswith("missing_")]
    if not missing_columns:
        return 0.0
    return float(frame[missing_columns].mean().mean())


def _run_id(cycle_id: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in cycle_id).strip("-")
    safe = "-".join(part for part in safe.split("-") if part) or "historical-cycle"
    return f"{safe}-{int(time.time() * 1000)}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str, allow_nan=False) + "\n", encoding="utf-8")


def _resolve_research_root(path: Path, *, repo_root: Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _repo_root_from_path(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent.resolve()
    return Path.cwd().resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _ensure_inside_research_root(path: Path, *, research_root: Path, field_name: str) -> None:
    resolved_path = path.resolve()
    resolved_root = research_root.resolve()
    if not _is_relative_to(resolved_path, resolved_root):
        raise ValueError(f"{field_name} must be inside the configured research output directory")


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_hash(frame: pd.DataFrame) -> str:
    if frame.empty:
        return _stable_hash({"columns": list(frame.columns), "rows": []})
    normalized = frame.reindex(sorted(frame.columns), axis=1)
    payload = normalized.to_csv(index=False, lineterminator="\n", float_format="%.12g")
    return sha256(payload.encode("utf-8")).hexdigest()
