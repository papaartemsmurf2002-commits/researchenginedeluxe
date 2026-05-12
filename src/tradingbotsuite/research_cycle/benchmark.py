from __future__ import annotations

import json
import shutil
import time
import tracemalloc
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd

from tradingbotsuite.backtesting import cuda_runtime_evidence
from tradingbotsuite.config import AppConfig
from tradingbotsuite.optimization import CandidateConfig, CandidateResult, OptimizationRun, SearchSpace
from tradingbotsuite.research.live_readiness import research_boundary_metadata
from tradingbotsuite.research_cycle.runner import run_historical_research_cycle

RESEARCH_CYCLE_BENCHMARK_REPORT_VERSION = "historical-research-cycle-benchmark-v1"
OPTIMIZER_PARALLEL_BENCHMARK_VERSION = "optimizer-parallel-speedup-benchmark-v1"
BENCHMARK_TIERS: dict[str, dict[str, Any]] = {
    "small": {
        "data_source_kind": "synthetic_fixture",
        "row_count": 120,
        "holding_windows": ["4h"],
        "feature_sets": ["features_price_trend_vol"],
        "strategies": ["baseline_no_trade", "trend_following_v1"],
        "min_splits": 2,
        "top_regions_to_refine": 1,
    },
    "medium": {
        "data_source_kind": "synthetic_fixture",
        "row_count": 240,
        "holding_windows": ["4h", "12h"],
        "feature_sets": ["features_price_trend_vol", "features_full_context_no_wt"],
        "strategies": ["baseline_no_trade", "trend_following_v1", "range_reversion_v1"],
        "min_splits": 3,
        "top_regions_to_refine": 2,
    },
    "provider_latest_month": {
        "data_source_kind": "historical_fixture_pack",
        "dataset_manifest_path": "data/research/fixtures/btcusdt_context_provider_latest_month_v1/fixture_pack_manifest.json",
        "row_count": 2873,
        "holding_windows": ["4h"],
        "feature_sets": ["features_price_trend_vol", "features_full_context_no_wt"],
        "strategies": ["baseline_no_trade", "trend_following_v1"],
        "min_splits": 2,
        "top_regions_to_refine": 1,
    },
}
BENCHMARK_THRESHOLDS: dict[str, dict[str, Any]] = {
    "small": {
        "min_rows_per_second_mean": 1.0,
        "min_candidate_backtests_per_minute_mean": 1.0,
        "max_tracemalloc_memory_peak_bytes": 512 * 1024 * 1024,
        "max_artifact_bytes_per_candidate_backtest": 10 * 1024 * 1024,
        "deterministic_repeat_required": True,
        "feature_cache_reuse_required_when_repeat_at_least": 2,
    },
    "medium": {
        "min_rows_per_second_mean": 1.0,
        "min_candidate_backtests_per_minute_mean": 1.0,
        "max_tracemalloc_memory_peak_bytes": 1536 * 1024 * 1024,
        "max_artifact_bytes_per_candidate_backtest": 10 * 1024 * 1024,
        "deterministic_repeat_required": True,
        "feature_cache_reuse_required_when_repeat_at_least": 2,
    },
    "provider_latest_month": {
        "min_rows_per_second_mean": 1.0,
        "min_candidate_backtests_per_minute_mean": 1.0,
        "max_tracemalloc_memory_peak_bytes": 1536 * 1024 * 1024,
        "max_artifact_bytes_per_candidate_backtest": 10 * 1024 * 1024,
        "deterministic_repeat_required": True,
        "feature_cache_reuse_required_when_repeat_at_least": 2,
    },
}
OPTIMIZER_PARALLEL_BENCHMARK_CANDIDATES = 32
OPTIMIZER_PARALLEL_BENCHMARK_WORKERS = 4
OPTIMIZER_PARALLEL_BENCHMARK_REPEATS = 3
OPTIMIZER_PARALLEL_BENCHMARK_SLEEP_SECONDS = 0.02


@dataclass(frozen=True, slots=True)
class ResearchCycleBenchmarkResult:
    output_dir: Path
    report_path: Path


def _benchmark_data_scope(tier_config: dict[str, Any]) -> str:
    if str(tier_config.get("data_source_kind") or "synthetic_fixture") == "historical_fixture_pack":
        return "local_provider_fixture_pack"
    return "local_synthetic"


def _benchmark_data_payload(tier_config: dict[str, Any]) -> dict[str, Any]:
    if _benchmark_data_scope(tier_config) == "local_provider_fixture_pack":
        manifest_path = _resolve_tier_dataset_manifest_path(tier_config)
        return {
            "dataset_manifest_paths": [str(manifest_path)],
            "synthetic_fixture": False,
        }
    return {
        "synthetic_fixture": True,
        "synthetic_row_count": int(tier_config["row_count"]),
        "synthetic_variant": "balanced",
    }


def _dataset_manifest_evidence(tier_config: dict[str, Any]) -> dict[str, Any]:
    if _benchmark_data_scope(tier_config) != "local_provider_fixture_pack":
        return {
            "used": False,
            "scope": "synthetic_fixture_benchmark_tier",
        }
    manifest_path = _resolve_tier_dataset_manifest_path(tier_config)
    return {
        "used": True,
        "scope": "local_provider_fixture_pack",
        "path": str(manifest_path),
        "exists": manifest_path.exists(),
        "sha256": _file_sha256(manifest_path) if manifest_path.exists() else None,
    }


def _resolve_tier_dataset_manifest_path(tier_config: dict[str, Any]) -> Path:
    raw_path = tier_config.get("dataset_manifest_path")
    if raw_path is None:
        raise ValueError("provider benchmark tier requires dataset_manifest_path")
    path = Path(str(raw_path)).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (Path.cwd() / path).resolve()


def _benchmark_gate_profile_version(benchmark_data_scope: str) -> str:
    if benchmark_data_scope == "local_provider_fixture_pack":
        return "historical-research-cycle-provider-fixture-thresholds-v1"
    return "historical-research-cycle-local-synthetic-thresholds-v1"


def _benchmark_gate_scope(benchmark_data_scope: str) -> str:
    if benchmark_data_scope == "local_provider_fixture_pack":
        return "historical_research_cycle_local_provider_fixture_pack"
    return "historical_research_cycle_local_synthetic"


def _backend_comparison_claim_scope(benchmark_data_scope: str) -> str:
    if benchmark_data_scope == "local_provider_fixture_pack":
        return "local_provider_fixture_runtime_observation_not_speedup_or_production_claim"
    return "local_synthetic_runtime_observation_not_speedup_or_production_claim"


def write_research_cycle_benchmark_report(
    *,
    output_dir: Path | None = None,
    tier: str = "small",
    repeat: int = 2,
    app_config: AppConfig | None = None,
) -> ResearchCycleBenchmarkResult:
    tier_id = str(tier).strip().lower()
    if tier_id not in BENCHMARK_TIERS:
        raise ValueError(f"tier must be one of: {', '.join(sorted(BENCHMARK_TIERS))}")
    repeat_count = max(int(repeat), 1)
    app_config = app_config or AppConfig.from_env()
    benchmark_dir = (
        output_dir
        or app_config.research.output_dir / "benchmarks" / "historical_research_cycle" / tier_id
    ).expanduser().resolve()
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    tier_config = BENCHMARK_TIERS[tier_id]
    benchmark_data_scope = _benchmark_data_scope(tier_config)
    dataset_evidence = _dataset_manifest_evidence(tier_config)
    runs_root = benchmark_dir / "runs"
    if runs_root.exists():
        shutil.rmtree(runs_root)
    feature_cache_root = benchmark_dir / "feature_cache"
    if feature_cache_root.exists():
        shutil.rmtree(feature_cache_root)

    runs: list[dict[str, Any]] = []
    for repeat_index in range(repeat_count):
        run_dir = runs_root / f"repeat_{repeat_index:02d}"
        spec_path = _write_benchmark_spec(run_dir, tier_id=tier_id, tier_config=tier_config)

        tracemalloc.start()
        started = time.perf_counter()
        result = run_historical_research_cycle(
            spec_path=spec_path,
            app_config=app_config,
            feature_cache_dir=feature_cache_root,
        )
        elapsed_seconds = max(time.perf_counter() - started, 1e-9)
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        cycle_manifest = _read_json(result.manifest_path)
        feature_manifest = _read_json(Path(str(cycle_manifest["required_outputs"]["feature_build_manifest"])))
        feature_timing = _feature_timing_from_manifest(feature_manifest)
        backtest_index = pd.read_parquet(result.backtest_index_path)
        rankings = pd.read_parquet(result.candidate_rankings_path)
        backtest_manifests = [_read_json(Path(str(path))) for path in backtest_index["backtest_manifest_path"]]
        row_count_processed = int(sum(int(manifest.get("row_count", 0)) for manifest in backtest_manifests))
        candidate_backtest_count = int(len(backtest_index))
        result_hashes = sorted(str(manifest.get("result_sha256")) for manifest in backtest_manifests)
        cache_keys = sorted(str(manifest.get("cache_key")) for manifest in backtest_manifests)
        cache_policy_values = sorted({str(manifest.get("cache_policy")) for manifest in backtest_manifests})
        cache_lookup_used = any(bool(manifest.get("cache_lookup_used", False)) for manifest in backtest_manifests)
        cache_hit = any(bool(manifest.get("cache_hit", False)) for manifest in backtest_manifests)
        execution_cache_reuse_enabled = any(
            bool(manifest.get("execution_cache_reuse_enabled", False))
            for manifest in backtest_manifests
        )
        live_fetch_used = bool(cycle_manifest.get("live_fetch_used", False))
        order_placement_used = bool(cycle_manifest.get("order_placement_used", False))
        ranking_identity_hash = _ranking_identity_hash(rankings)
        run_digest = _stable_hash(
            {
                "result_hashes": result_hashes,
                "cache_keys": cache_keys,
                "ranking_identity_hash": ranking_identity_hash,
                "candidate_backtest_count": candidate_backtest_count,
                "row_count_processed": row_count_processed,
            }
        )
        runs.append(
            {
                "repeat_index": repeat_index,
                "output_dir": str(result.output_dir),
                "spec_path": str(spec_path),
                "research_cycle_manifest_path": str(result.manifest_path),
                "elapsed_seconds": round(elapsed_seconds, 6),
                "tracemalloc_memory_peak_bytes": int(peak_bytes),
                "memory_measurement": _memory_measurement(int(peak_bytes)),
                "candidate_backtest_count": candidate_backtest_count,
                "row_count_processed": row_count_processed,
                "rows_per_second": round(row_count_processed / elapsed_seconds, 6),
                "candidate_backtests_per_minute": round(candidate_backtest_count / (elapsed_seconds / 60.0), 6),
                "feature_rows_per_second": feature_timing["feature_rows_per_second"],
                "feature_timing": feature_timing,
                "backtest_identity": {
                    "cache_policy": cache_policy_values[0] if len(cache_policy_values) == 1 else "mixed_cache_policy",
                    "cache_policy_values": cache_policy_values,
                    "cache_lookup_used": cache_lookup_used,
                    "cache_hit": cache_hit,
                    "execution_cache_reuse_enabled": execution_cache_reuse_enabled,
                    "cache_keys_sha256": _stable_hash({"cache_keys": cache_keys}),
                    "result_hashes_sha256": _stable_hash({"result_hashes": result_hashes}),
                    "ranking_identity_sha256": ranking_identity_hash,
                },
                "live_fetch_used": live_fetch_used,
                "order_placement_used": order_placement_used,
                "deterministic_result_hash": run_digest,
            }
        )

    reference_vs_vector_backend_comparison = _reference_vs_vector_backend_comparison(
        benchmark_dir=benchmark_dir,
        tier_id=tier_id,
        tier_config=tier_config,
        repeat_count=repeat_count,
        app_config=app_config,
    )
    deterministic_hashes = [run["deterministic_result_hash"] for run in runs]
    summary = _summary(runs)
    feature_cache_reuse = _feature_cache_reuse(runs)
    backtest_identity = _backtest_identity_repeat_consistent(runs)
    optimizer_parallel_speedup = _optimizer_parallel_speedup_benchmark()
    deterministic_repeat_consistent = len(set(deterministic_hashes)) == 1
    cycle_repeat_memory_peak_bytes = max(int(run["tracemalloc_memory_peak_bytes"]) for run in runs)
    report = {
        "benchmark_report_version": RESEARCH_CYCLE_BENCHMARK_REPORT_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "benchmark_scope": "historical_research_cycle",
        "benchmark_data_scope": benchmark_data_scope,
        "dataset_manifest": dataset_evidence,
        "tier": tier_id,
        "tier_dimensions": dict(tier_config),
        "regression_threshold_policy": dict(BENCHMARK_THRESHOLDS[tier_id]),
        "repeat": repeat_count,
        "runs": runs,
        "summary": summary,
        "cycle_repeat_tracemalloc_memory_peak_bytes": cycle_repeat_memory_peak_bytes,
        "memory_measurement": _memory_measurement(cycle_repeat_memory_peak_bytes),
        "artifact_overhead": {},
        "feature_cache_reuse": feature_cache_reuse,
        "backtest_identity_repeat_consistent": backtest_identity,
        "reference_vs_vector_backend_comparison": reference_vs_vector_backend_comparison,
        "optimizer_parallel_speedup": optimizer_parallel_speedup,
        "benchmark_gate": {},
        "deterministic_repeat_hash": _stable_hash({"run_hashes": deterministic_hashes}),
        "deterministic_repeat_consistent": deterministic_repeat_consistent,
        "live_fetch_used": any(bool(run["live_fetch_used"]) for run in runs),
        "order_placement_used": any(bool(run["order_placement_used"]) for run in runs),
    }
    report_path = benchmark_dir / "research_cycle_benchmark_report.json"
    _finalize_benchmark_report(
        report_path,
        report,
        benchmark_dir=benchmark_dir,
        tier_id=tier_id,
        repeat_count=repeat_count,
        candidate_backtest_count=sum(int(run["candidate_backtest_count"]) for run in runs),
        summary=summary,
        tracemalloc_memory_peak_bytes=cycle_repeat_memory_peak_bytes,
        feature_cache_reuse=feature_cache_reuse,
        backtest_identity=backtest_identity,
        deterministic_repeat_consistent=deterministic_repeat_consistent,
        optimizer_parallel_speedup=optimizer_parallel_speedup,
        live_fetch_used=any(bool(run["live_fetch_used"]) for run in runs),
        order_placement_used=any(bool(run["order_placement_used"]) for run in runs),
        backtest_cache_lookup_used=any(bool(run["backtest_identity"]["cache_lookup_used"]) for run in runs),
        backtest_cache_hit=any(bool(run["backtest_identity"]["cache_hit"]) for run in runs),
        execution_cache_reuse_enabled=any(
            bool(run["backtest_identity"]["execution_cache_reuse_enabled"])
            for run in runs
        ),
        backend_comparison=reference_vs_vector_backend_comparison,
        benchmark_data_scope=benchmark_data_scope,
    )
    return ResearchCycleBenchmarkResult(output_dir=benchmark_dir, report_path=report_path)


def _write_benchmark_spec(
    run_dir: Path,
    *,
    tier_id: str,
    tier_config: dict[str, Any],
    backtest_backend: str | None = None,
    compute: dict[str, Any] | None = None,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    spec_path = run_dir / "cycle_spec.json"
    payload = {
        "cycle_id": f"benchmark-{tier_id}-{run_dir.name}",
        "symbol": "BTCUSDT",
        "output_dir": str((run_dir / "cycle_output").resolve()),
        "holding_windows": list(tier_config["holding_windows"]),
        "data": _benchmark_data_payload(tier_config),
        "features": {
            "feature_sets": list(tier_config["feature_sets"]),
        },
        "strategies": list(tier_config["strategies"]),
        "validation": {
            "walk_forward": "rolling_and_anchored",
            "purge_embargo_bars": 2,
            "stress_periods_required": True,
            "min_splits": int(tier_config["min_splits"]),
            "trade_count_floor": 1,
        },
        "optimizer": {
            "method_sequence": ["coarse_lhs", "adaptive_grid", "stability_region_refine"],
            "max_candidates_per_strategy": 16,
            "top_regions_to_refine": int(tier_config["top_regions_to_refine"]),
        },
    }
    if backtest_backend is not None:
        payload["backtest_backend"] = backtest_backend
    if compute is not None:
        payload["compute"] = dict(compute)
    _write_json(spec_path, payload)
    return spec_path


def _reference_vs_vector_backend_comparison(
    *,
    benchmark_dir: Path,
    tier_id: str,
    tier_config: dict[str, Any],
    repeat_count: int,
    app_config: AppConfig,
) -> dict[str, Any]:
    comparison_root = benchmark_dir / "backend_comparison"
    if comparison_root.exists():
        shutil.rmtree(comparison_root)
    pairs: list[dict[str, Any]] = []
    cuda_evidence = cuda_runtime_evidence()
    cuda_available = bool(cuda_evidence.get("available", False))
    for repeat_index in range(repeat_count):
        pair_dir = comparison_root / f"pair_{repeat_index:02d}"
        reference = _run_backend_comparison_cycle(
            pair_dir=pair_dir,
            tier_id=tier_id,
            tier_config=tier_config,
            backend="reference",
            backend_label="reference_serial_cpu",
            compute={
                "cpu_threads": 1,
                "gpu_acceleration": "disabled",
                "gpu_required": False,
            },
            app_config=app_config,
        )
        reference_cpu48 = _run_backend_comparison_cycle(
            pair_dir=pair_dir,
            tier_id=tier_id,
            tier_config=tier_config,
            backend="reference",
            backend_label="reference_cpu48",
            compute={
                "cpu_threads": 48,
                "gpu_acceleration": "disabled",
                "gpu_required": False,
            },
            app_config=app_config,
        )
        vector = _run_backend_comparison_cycle(
            pair_dir=pair_dir,
            tier_id=tier_id,
            tier_config=tier_config,
            backend="vector_fixed_holding",
            backend_label="vector_fixed_holding_cpu48",
            compute={
                "cpu_threads": 48,
                "gpu_acceleration": "disabled",
                "gpu_required": False,
            },
            app_config=app_config,
        )
        artifact_equivalence = _behavioral_artifact_hashes_equal(reference["backtest_index"], vector["backtest_index"])
        reference_runtime = float(reference["backtest_runtime_ms_sum"])
        reference_cpu48_runtime = float(reference_cpu48["backtest_runtime_ms_sum"])
        vector_runtime = float(vector["backtest_runtime_ms_sum"])
        cuda: dict[str, Any] | None = None
        cuda_artifact_equivalence = {"equal": False, "checked": 0}
        cuda_runtime = 0.0
        if cuda_available:
            cuda = _run_backend_comparison_cycle(
                pair_dir=pair_dir,
                tier_id=tier_id,
                tier_config=tier_config,
                backend="cuda_fixed_holding",
                backend_label="cuda_fixed_holding_gpu",
                compute={
                    "cpu_threads": 15,
                    "gpu_acceleration": "prefer_nvidia_cuda_when_backend_available",
                    "gpu_required": True,
                },
                app_config=app_config,
            )
            cuda_artifact_equivalence = _behavioral_artifact_hashes_equal(reference["backtest_index"], cuda["backtest_index"])
            cuda_runtime = float(cuda["backtest_runtime_ms_sum"])
        pairs.append(
            {
                "repeat_index": repeat_index,
                "reference": _backend_comparison_payload(reference),
                "reference_cpu48": _backend_comparison_payload(reference_cpu48),
                "vector": _backend_comparison_payload(vector),
                "cuda": _backend_comparison_payload(cuda) if cuda is not None else None,
                "candidate_backtest_count_equal": reference["candidate_backtest_count"] == vector["candidate_backtest_count"],
                "row_count_processed_equal": reference["row_count_processed"] == vector["row_count_processed"],
                "candidate_ids_equal": reference["candidate_ids"] == vector["candidate_ids"],
                "evaluation_scope_counts_equal": reference["evaluation_scope_counts"] == vector["evaluation_scope_counts"],
                "behavioral_artifact_hashes_equal": artifact_equivalence["equal"],
                "behavioral_artifact_hashes_checked": artifact_equivalence["checked"],
                "observed_runtime_ratio_reference_over_vector": round(reference_runtime / max(vector_runtime, 1e-9), 6),
                "observed_runtime_ratio_reference_serial_over_cpu48": round(reference_runtime / max(reference_cpu48_runtime, 1e-9), 6),
                "cuda_candidate_backtest_count_equal": (
                    cuda is not None and reference["candidate_backtest_count"] == cuda["candidate_backtest_count"]
                ),
                "cuda_row_count_processed_equal": (
                    cuda is not None and reference["row_count_processed"] == cuda["row_count_processed"]
                ),
                "cuda_candidate_ids_equal": (
                    cuda is not None and reference["candidate_ids"] == cuda["candidate_ids"]
                ),
                "cuda_evaluation_scope_counts_equal": (
                    cuda is not None and reference["evaluation_scope_counts"] == cuda["evaluation_scope_counts"]
                ),
                "cuda_behavioral_artifact_hashes_equal": bool(cuda_artifact_equivalence["equal"]),
                "cuda_behavioral_artifact_hashes_checked": int(cuda_artifact_equivalence["checked"]),
                "observed_runtime_ratio_reference_over_cuda": (
                    round(reference_runtime / max(cuda_runtime, 1e-9), 6)
                    if cuda is not None
                    else None
                ),
                "observed_runtime_ratio_vector_over_cuda": (
                    round(vector_runtime / max(cuda_runtime, 1e-9), 6)
                    if cuda is not None
                    else None
                ),
            }
        )
    reference_runtimes = [float(pair["reference"]["backtest_runtime_ms_sum"]) for pair in pairs]
    reference_cpu48_runtimes = [float(pair["reference_cpu48"]["backtest_runtime_ms_sum"]) for pair in pairs]
    vector_runtimes = [float(pair["vector"]["backtest_runtime_ms_sum"]) for pair in pairs]
    cuda_runtimes = [
        float(pair["cuda"]["backtest_runtime_ms_sum"])
        for pair in pairs
        if isinstance(pair.get("cuda"), dict)
    ]
    ratios = [float(pair["observed_runtime_ratio_reference_over_vector"]) for pair in pairs]
    benchmark_data_scope = _benchmark_data_scope(tier_config)
    return {
        "benchmark_version": "reference-vs-vector-backend-benchmark-v1",
        "measured": bool(pairs),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "benchmark_data_scope": benchmark_data_scope,
        "scope": "fixed_holding_primary_bar_historical_cycle",
        "claim_scope": _backend_comparison_claim_scope(benchmark_data_scope),
        "speed_claimed": False,
        "default_backend_verified": "reference",
        "cpu_thread_comparison_measured": bool(pairs),
        "cpu_parallel_workers": 48,
        "cuda_runtime_available": cuda_available,
        "cuda_runtime_evidence": dict(cuda_evidence),
        "cuda_measured": bool(cuda_available and cuda_runtimes),
        "cuda_skip_reason": "" if cuda_available else str(cuda_evidence.get("unavailable_reason") or "cuda_runtime_unavailable"),
        "cuda_claim_scope": "diagnostic_runtime_observation_not_live_readiness_or_speed_claim",
        "pairs": pairs,
        "summary": {
            "reference_backtest_runtime_ms_sum_median": round(float(median(reference_runtimes)), 6) if reference_runtimes else 0.0,
            "reference_cpu48_backtest_runtime_ms_sum_median": round(float(median(reference_cpu48_runtimes)), 6) if reference_cpu48_runtimes else 0.0,
            "vector_backtest_runtime_ms_sum_median": round(float(median(vector_runtimes)), 6) if vector_runtimes else 0.0,
            "cuda_backtest_runtime_ms_sum_median": round(float(median(cuda_runtimes)), 6) if cuda_runtimes else 0.0,
            "observed_runtime_ratio_reference_over_vector_median": round(float(median(ratios)), 6) if ratios else 0.0,
        },
    }


def _run_backend_comparison_cycle(
    *,
    pair_dir: Path,
    tier_id: str,
    tier_config: dict[str, Any],
    backend: str,
    backend_label: str | None = None,
    compute: dict[str, Any] | None = None,
    app_config: AppConfig,
) -> dict[str, Any]:
    run_dir = pair_dir / str(backend_label or backend)
    spec_path = _write_benchmark_spec(
        run_dir,
        tier_id=f"{tier_id}-{backend_label or backend}",
        tier_config=tier_config,
        backtest_backend=backend,
        compute=compute,
    )
    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=app_config,
        feature_cache_dir=run_dir / "feature_cache",
    )
    cycle_manifest = _read_json(result.manifest_path)
    backtest_index = pd.read_parquet(result.backtest_index_path)
    backtest_manifests = [_read_json(Path(str(path))) for path in backtest_index["backtest_manifest_path"]]
    return {
        "backend": backend,
        "backend_label": str(backend_label or backend),
        "output_dir": str(result.output_dir),
        "spec_path": str(spec_path),
        "research_cycle_manifest_path": str(result.manifest_path),
        "backtest_index": backtest_index,
        "compute_policy": dict(cycle_manifest.get("compute_policy") or {}),
        "backend_used_counts": dict(cycle_manifest["backtest_backend_summary"]["used_counts"]),
        "fallback_count": int(cycle_manifest["backtest_backend_summary"]["fallback_count"]),
        "fallback_reasons": dict(cycle_manifest["backtest_backend_summary"]["fallback_reasons"]),
        "vector_scope_counts": dict(cycle_manifest["backtest_backend_summary"]["vector_scope_counts"]),
        "cuda_scope_counts": dict(cycle_manifest["backtest_backend_summary"].get("cuda_scope_counts") or {}),
        "gpu_status_counts": dict(cycle_manifest["backtest_backend_summary"].get("gpu_status_counts") or {}),
        "candidate_backtest_count": int(len(backtest_index)),
        "row_count_processed": int(sum(int(manifest.get("row_count", 0)) for manifest in backtest_manifests)),
        "candidate_ids": sorted(str(value) for value in backtest_index["candidate_id"].unique()),
        "evaluation_scope_counts": {
            str(key): int(value)
            for key, value in backtest_index["evaluation_scope"].value_counts().sort_index().to_dict().items()
        },
        "backend_used_counts_by_scope": _backend_used_counts_by_scope(backtest_index),
        "backtest_runtime_ms_sum": round(
            sum(float((manifest.get("runtime") or {}).get("elapsed_ms", 0.0)) for manifest in backtest_manifests),
            6,
        ),
    }


def _backend_comparison_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    return {
        "backend": payload["backend"],
        "backend_label": payload["backend_label"],
        "output_dir": payload["output_dir"],
        "spec_path": payload["spec_path"],
        "research_cycle_manifest_path": payload["research_cycle_manifest_path"],
        "compute_policy": payload["compute_policy"],
        "backend_used_counts": payload["backend_used_counts"],
        "fallback_count": payload["fallback_count"],
        "fallback_reasons": payload["fallback_reasons"],
        "vector_scope_counts": payload["vector_scope_counts"],
        "cuda_scope_counts": payload["cuda_scope_counts"],
        "gpu_status_counts": payload["gpu_status_counts"],
        "candidate_backtest_count": payload["candidate_backtest_count"],
        "row_count_processed": payload["row_count_processed"],
        "evaluation_scope_counts": payload["evaluation_scope_counts"],
        "backend_used_counts_by_scope": payload["backend_used_counts_by_scope"],
        "backtest_runtime_ms_sum": payload["backtest_runtime_ms_sum"],
    }


def _backend_used_counts_by_scope(index: pd.DataFrame) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    if "evaluation_scope" not in index.columns or "backtest_backend_used" not in index.columns:
        return counts
    grouped = index.groupby(["evaluation_scope", "backtest_backend_used"], dropna=False).size()
    for (scope, backend), value in grouped.to_dict().items():
        scope_key = str(scope)
        backend_key = str(backend)
        counts.setdefault(scope_key, {})[backend_key] = int(value)
    return {scope: dict(sorted(backends.items())) for scope, backends in sorted(counts.items())}


def _behavioral_artifact_hashes_equal(reference_index: pd.DataFrame, vector_index: pd.DataFrame) -> dict[str, Any]:
    reference_hashes = _behavioral_hashes_by_pair_key(reference_index)
    vector_hashes = _behavioral_hashes_by_pair_key(vector_index)
    keys_equal = set(reference_hashes) == set(vector_hashes)
    matching = keys_equal and all(reference_hashes[key] == vector_hashes[key] for key in reference_hashes)
    return {
        "equal": bool(matching),
        "checked": int(len(reference_hashes) if keys_equal else 0),
    }


def _behavioral_hashes_by_pair_key(index: pd.DataFrame) -> dict[str, dict[str, str]]:
    hashes: dict[str, dict[str, str]] = {}
    for row in index.to_dict("records"):
        manifest = _read_json(Path(str(row["backtest_manifest_path"])))
        artifact_hashes = dict(manifest.get("artifact_hashes") or {})
        pair_key = "|".join(
            [
                str(row["candidate_id"]),
                str(row["evaluation_scope"]),
                Path(str(row["backtest_manifest_path"])).parent.name,
            ]
        )
        hashes[pair_key] = {
            key: str(artifact_hashes.get(key) or "")
            for key in ("trades_sha256", "signals_sha256", "equity_curve_sha256", "metrics_sha256")
        }
    return hashes


def _memory_measurement(peak_bytes: int) -> dict[str, Any]:
    return {
        "scope": "historical_cycle_repeat_python_tracemalloc_peak_bytes",
        "phase": "main_historical_cycle_repeats_only",
        "measurement_phase": "main_historical_cycle_repeats_only",
        "peak_bytes": int(peak_bytes),
        "rss_measured": False,
        "native_allocator_memory_measured": False,
        "benchmark_wide_memory_measured": False,
        "claim_scope": "repeat_phase_python_allocation_guardrail_not_benchmark_wide_or_total_process_memory",
    }


def _optimizer_parallel_speedup_benchmark() -> dict[str, Any]:
    parameter_values = tuple(round(0.01 * index, 4) for index in range(1, OPTIMIZER_PARALLEL_BENCHMARK_CANDIDATES + 1))
    space = SearchSpace(
        "trend_following_v1",
        {"slope_threshold": parameter_values},
        feature_set_id="features_price_trend_vol",
        holding_window="4h",
    )

    def evaluate(config: CandidateConfig) -> CandidateResult:
        time.sleep(OPTIMIZER_PARALLEL_BENCHMARK_SLEEP_SECONDS)
        threshold = float(config.parameters["slope_threshold"])
        return CandidateResult(
            config,
            base_score=threshold,
            risk_score=threshold / 10.0,
            robustness_score=threshold / 20.0,
            trade_count=10,
            split_consistency=0.8,
            side_balance=0.7,
            regime_coverage=0.6,
            cost_stress_survival=0.75,
            metadata={"benchmark_scope": "synthetic_optimizer_parallel_evaluator"},
        )

    serial_samples: list[float] = []
    parallel_samples: list[float] = []
    serial_report = None
    parallel_report = None
    for _ in range(OPTIMIZER_PARALLEL_BENCHMARK_REPEATS):
        serial_elapsed, serial_report = _timed_optimizer_run(space, evaluate, workers=1)
        parallel_elapsed, parallel_report = _timed_optimizer_run(
            space,
            evaluate,
            workers=OPTIMIZER_PARALLEL_BENCHMARK_WORKERS,
        )
        serial_samples.append(serial_elapsed)
        parallel_samples.append(parallel_elapsed)

    if serial_report is None or parallel_report is None:
        raise ValueError("optimizer parallel benchmark did not produce reports")
    serial_payload = serial_report.to_payload()
    parallel_payload = parallel_report.to_payload()
    serial_median = max(float(median(serial_samples)), 1e-9)
    parallel_median = max(float(median(parallel_samples)), 1e-9)
    serial_results_hash = _stable_hash({"results": serial_payload["results"]})
    parallel_results_hash = _stable_hash({"results": parallel_payload["results"]})
    serial_regions_hash = _stable_hash({"stability_regions": serial_payload["stability_regions"]})
    parallel_regions_hash = _stable_hash({"stability_regions": parallel_payload["stability_regions"]})
    possible_active_workers = min(OPTIMIZER_PARALLEL_BENCHMARK_WORKERS, int(parallel_payload["effective_candidates"]))
    return {
        "benchmark_version": OPTIMIZER_PARALLEL_BENCHMARK_VERSION,
        "measured": True,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "scope": "optimizer_candidate_evaluator_parallelism",
        "synthetic_evaluator": True,
        "historical_cycle_backtest_parallel_measured": False,
        "backtest_execution_cache_measured": False,
        "candidate_count": OPTIMIZER_PARALLEL_BENCHMARK_CANDIDATES,
        "repeat": OPTIMIZER_PARALLEL_BENCHMARK_REPEATS,
        "serial_workers": 1,
        "parallel_workers": OPTIMIZER_PARALLEL_BENCHMARK_WORKERS,
        "possible_active_parallel_workers": possible_active_workers,
        "evaluator_sleep_seconds": OPTIMIZER_PARALLEL_BENCHMARK_SLEEP_SECONDS,
        "serial_elapsed_seconds_samples": [round(value, 6) for value in serial_samples],
        "parallel_elapsed_seconds_samples": [round(value, 6) for value in parallel_samples],
        "serial_elapsed_seconds_median": round(serial_median, 6),
        "parallel_elapsed_seconds_median": round(parallel_median, 6),
        "serial_elapsed_seconds": round(serial_median, 6),
        "parallel_elapsed_seconds": round(parallel_median, 6),
        "speedup_factor": round(serial_median / parallel_median, 6),
        "result_hashes_equal": serial_results_hash == parallel_results_hash,
        "stability_region_hashes_equal": serial_regions_hash == parallel_regions_hash,
        "serial_results_sha256": serial_results_hash,
        "parallel_results_sha256": parallel_results_hash,
        "serial_stability_regions_sha256": serial_regions_hash,
        "parallel_stability_regions_sha256": parallel_regions_hash,
        "serial_total_candidates": int(serial_payload["total_candidates"]),
        "parallel_total_candidates": int(parallel_payload["total_candidates"]),
        "serial_effective_candidates": int(serial_payload["effective_candidates"]),
        "parallel_effective_candidates": int(parallel_payload["effective_candidates"]),
    }


def _timed_optimizer_run(
    space: SearchSpace,
    evaluator: Any,
    *,
    workers: int,
) -> tuple[float, Any]:
    started = time.perf_counter()
    report = OptimizationRun(
        space,
        method="grid",
        max_candidates=OPTIMIZER_PARALLEL_BENCHMARK_CANDIDATES,
        workers=workers,
    ).run(evaluator)
    return max(time.perf_counter() - started, 1e-9), report


def _feature_timing_from_manifest(feature_manifest: dict[str, Any]) -> dict[str, Any]:
    feature_sets = list(feature_manifest.get("feature_sets", ()))
    elapsed = max(float((feature_manifest.get("runtime") or {}).get("elapsed_seconds", 0.0)), 1e-9)
    logical_rows = int(sum(int(record.get("row_count", 0)) for record in feature_sets))
    return {
        "feature_computation_scope": feature_manifest["feature_computation_scope"],
        "dataset_rows": int(feature_manifest.get("row_count", 0)),
        "feature_set_count": int(len(feature_sets)),
        "elapsed_seconds": round(elapsed, 6),
        "feature_rows_per_second": round(logical_rows / elapsed, 6),
        "cache_status_counts": dict(feature_manifest.get("cache_status_counts") or {}),
        "feature_frame_sha256_by_set": {
            str(record.get("feature_set_id")): record.get("feature_frame_sha256")
            for record in feature_sets
        },
    }


def _feature_cache_reuse(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runs) < 2:
        return {
            "measured": False,
            "evidence_type": "feature_cache_reuse",
            "scope": "feature_build_cache",
            "backtest_cache_measured": False,
            "reason": "repeat_count_below_two",
            "speed_claimed": False,
            "timing_observation_scope": "not_measured_repeat_count_below_two",
        }
    cold = runs[0]["feature_timing"]
    warm = runs[1]["feature_timing"]
    cold_misses = int(cold.get("cache_status_counts", {}).get("miss", 0))
    warm_hits = int(warm.get("cache_status_counts", {}).get("hit", 0))
    cold_elapsed = max(float(cold.get("elapsed_seconds", 0.0)), 1e-9)
    warm_elapsed = max(float(warm.get("elapsed_seconds", 0.0)), 1e-9)
    expected_feature_sets = int(warm.get("feature_set_count", 0))
    cold_build_complete = expected_feature_sets > 0 and cold_misses == expected_feature_sets
    warm_reuse_complete = expected_feature_sets > 0 and warm_hits == expected_feature_sets
    feature_output_hashes_match = cold.get("feature_frame_sha256_by_set") == warm.get("feature_frame_sha256_by_set")
    return {
        "measured": bool(cold_build_complete and warm_reuse_complete and feature_output_hashes_match),
        "evidence_type": "feature_cache_reuse",
        "scope": "feature_build_cache",
        "backtest_cache_measured": False,
        "speed_claimed": False,
        "timing_observation_scope": "observed_local_cold_vs_warm_timing_not_regression_gate_or_speed_claim",
        "cold_elapsed_seconds": round(cold_elapsed, 6),
        "warm_elapsed_seconds": round(warm_elapsed, 6),
        "cold_misses": cold_misses,
        "warm_hits": warm_hits,
        "expected_feature_sets": expected_feature_sets,
        "cold_build_complete": cold_build_complete,
        "warm_reuse_complete": warm_reuse_complete,
        "observed_cold_over_warm_timing_ratio": round(cold_elapsed / warm_elapsed, 6),
        "feature_output_hashes_match": feature_output_hashes_match,
    }


def _finalize_benchmark_report(
    report_path: Path,
    report: dict[str, Any],
    *,
    benchmark_dir: Path,
    tier_id: str,
    repeat_count: int,
    candidate_backtest_count: int,
    summary: dict[str, float],
    tracemalloc_memory_peak_bytes: int,
    feature_cache_reuse: dict[str, Any],
    backtest_identity: dict[str, Any],
    deterministic_repeat_consistent: bool,
    optimizer_parallel_speedup: dict[str, Any],
    live_fetch_used: bool,
    order_placement_used: bool,
    backtest_cache_lookup_used: bool,
    backtest_cache_hit: bool,
    execution_cache_reuse_enabled: bool,
    backend_comparison: dict[str, Any] | None,
    benchmark_data_scope: str,
) -> None:
    for _ in range(100):
        _write_json(report_path, report)
        artifact_overhead = _artifact_overhead(benchmark_dir)
        artifact_overhead_payload = {
            **artifact_overhead,
            "bytes_per_candidate_backtest": round(
                artifact_overhead["total_bytes"] / max(int(candidate_backtest_count), 1),
                6,
            ),
        }
        benchmark_gate = _benchmark_gate(
            tier_id=tier_id,
            repeat_count=repeat_count,
            summary=summary,
            tracemalloc_memory_peak_bytes=tracemalloc_memory_peak_bytes,
            artifact_overhead=artifact_overhead_payload,
            feature_cache_reuse=feature_cache_reuse,
            backtest_identity=backtest_identity,
            deterministic_repeat_consistent=deterministic_repeat_consistent,
            optimizer_parallel_speedup=optimizer_parallel_speedup,
            live_fetch_used=live_fetch_used,
            order_placement_used=order_placement_used,
            backtest_cache_lookup_used=backtest_cache_lookup_used,
            backtest_cache_hit=backtest_cache_hit,
            execution_cache_reuse_enabled=execution_cache_reuse_enabled,
            backend_comparison=backend_comparison,
            benchmark_data_scope=benchmark_data_scope,
        )
        report["artifact_overhead"] = artifact_overhead_payload
        report["benchmark_gate"] = benchmark_gate
        _write_json(report_path, report)
        if int(report["artifact_overhead"].get("final_report_bytes", 0)) == int(report_path.stat().st_size):
            return
    _write_json(report_path, report)


def _backtest_identity_repeat_consistent(runs: list[dict[str, Any]]) -> dict[str, Any]:
    cache_policies = sorted(
        {
            str(policy)
            for run in runs
            for policy in run["backtest_identity"].get("cache_policy_values", ())
        }
    )
    cache_lookup_used = any(bool(run["backtest_identity"].get("cache_lookup_used", False)) for run in runs)
    cache_hit = any(bool(run["backtest_identity"].get("cache_hit", False)) for run in runs)
    execution_cache_reuse_enabled = any(
        bool(run["backtest_identity"].get("execution_cache_reuse_enabled", False))
        for run in runs
    )
    if len(runs) < 2:
        return {
            "measured": False,
            "backtest_cache_measured": bool(cache_lookup_used or cache_hit or execution_cache_reuse_enabled),
            "scope": "backtest_identity_repeat_consistency",
            "reason": "repeat_count_below_two",
            "cache_policy": cache_policies[0] if len(cache_policies) == 1 else "insufficient_repeat_evidence",
            "cache_policy_values": cache_policies,
            "cache_lookup_used": cache_lookup_used,
            "cache_hit": cache_hit,
            "execution_cache_reuse_enabled": execution_cache_reuse_enabled,
        }
    cache_key_hashes = {str(run["backtest_identity"]["cache_keys_sha256"]) for run in runs}
    result_hashes = {str(run["backtest_identity"]["result_hashes_sha256"]) for run in runs}
    ranking_hashes = {str(run["backtest_identity"]["ranking_identity_sha256"]) for run in runs}
    return {
        "measured": True,
        "backtest_cache_measured": bool(cache_lookup_used or cache_hit or execution_cache_reuse_enabled),
        "scope": "backtest_identity_repeat_consistency",
        "cache_policy": cache_policies[0] if len(cache_policies) == 1 else "mixed_cache_policy",
        "cache_policy_values": cache_policies,
        "cache_lookup_used": cache_lookup_used,
        "cache_hit": cache_hit,
        "execution_cache_reuse_enabled": execution_cache_reuse_enabled,
        "cache_keys_consistent": len(cache_key_hashes) == 1,
        "result_hashes_consistent": len(result_hashes) == 1,
        "ranking_identity_consistent": len(ranking_hashes) == 1,
    }


def _benchmark_gate(
    *,
    tier_id: str,
    repeat_count: int,
    summary: dict[str, float],
    tracemalloc_memory_peak_bytes: int,
    artifact_overhead: dict[str, Any],
    feature_cache_reuse: dict[str, Any],
    backtest_identity: dict[str, Any],
    deterministic_repeat_consistent: bool,
    optimizer_parallel_speedup: dict[str, Any],
    live_fetch_used: bool,
    order_placement_used: bool,
    backtest_cache_lookup_used: bool,
    backtest_cache_hit: bool,
    execution_cache_reuse_enabled: bool,
    backend_comparison: dict[str, Any] | None = None,
    benchmark_data_scope: str | None = None,
) -> dict[str, Any]:
    thresholds = dict(BENCHMARK_THRESHOLDS[tier_id])
    resolved_data_scope = benchmark_data_scope or _benchmark_data_scope(BENCHMARK_TIERS.get(tier_id, {}))
    feature_cache_repeat_required = int(thresholds["feature_cache_reuse_required_when_repeat_at_least"])
    repeat_evidence_available = repeat_count >= 2
    backend_comparison = backend_comparison or {}
    backend_pairs = list(backend_comparison.get("pairs") or [])
    backend_comparison_measured = bool(backend_comparison.get("measured", False) and backend_pairs)
    vector_supported_scope_used = bool(backend_pairs) and all(
        int(pair.get("vector", {}).get("fallback_count", 0)) == 0
        and pair.get("vector", {}).get("backend_used_counts", {}).get("vector_fixed_holding") == pair.get("vector", {}).get("candidate_backtest_count")
        and pair.get("vector", {}).get("vector_scope_counts", {}).get("fixed_holding_primary_bar") == pair.get("vector", {}).get("candidate_backtest_count")
        for pair in backend_pairs
    )
    behavioral_equivalence = bool(backend_pairs) and all(
        bool(pair.get("candidate_backtest_count_equal"))
        and bool(pair.get("row_count_processed_equal"))
        and bool(pair.get("candidate_ids_equal"))
        and bool(pair.get("evaluation_scope_counts_equal"))
        and bool(pair.get("behavioral_artifact_hashes_equal"))
        for pair in backend_pairs
    )
    speed_claim_not_made = "speed_claimed" in backend_comparison and bool(backend_comparison.get("speed_claimed")) is False
    checks = [
        _threshold_check(
            "rows_per_second_mean",
            actual=float(summary["rows_per_second_mean"]),
            threshold=float(thresholds["min_rows_per_second_mean"]),
            operator=">=",
            passed=float(summary["rows_per_second_mean"]) >= float(thresholds["min_rows_per_second_mean"]),
        ),
        _threshold_check(
            "candidate_backtests_per_minute_mean",
            actual=float(summary["candidate_backtests_per_minute_mean"]),
            threshold=float(thresholds["min_candidate_backtests_per_minute_mean"]),
            operator=">=",
            passed=float(summary["candidate_backtests_per_minute_mean"]) >= float(thresholds["min_candidate_backtests_per_minute_mean"]),
        ),
        _threshold_check(
            "tracemalloc_memory_peak_bytes",
            actual=int(tracemalloc_memory_peak_bytes),
            threshold=int(thresholds["max_tracemalloc_memory_peak_bytes"]),
            operator="<=",
            passed=int(tracemalloc_memory_peak_bytes) <= int(thresholds["max_tracemalloc_memory_peak_bytes"]),
        ),
        _threshold_check(
            "artifact_bytes_per_candidate_backtest",
            actual=float(artifact_overhead["bytes_per_candidate_backtest"]),
            threshold=float(thresholds["max_artifact_bytes_per_candidate_backtest"]),
            operator="<=",
            passed=float(artifact_overhead["bytes_per_candidate_backtest"]) <= float(thresholds["max_artifact_bytes_per_candidate_backtest"]),
        ),
        _threshold_check(
            "artifact_overhead_includes_backend_comparison",
            actual=bool(artifact_overhead.get("includes_backend_comparison", False)),
            threshold=True,
            operator="is",
            passed=bool(artifact_overhead.get("includes_backend_comparison", False)),
            failure_reason="missing_artifact_overhead_backend_comparison_evidence",
            evidence_required=True,
        ),
        _threshold_check(
            "artifact_overhead_includes_final_report",
            actual=bool(artifact_overhead.get("includes_final_report", False)),
            threshold=True,
            operator="is",
            passed=bool(artifact_overhead.get("includes_final_report", False)),
            failure_reason="missing_artifact_overhead_final_report_evidence",
            evidence_required=True,
        ),
        _threshold_check(
            "deterministic_repeat_consistent",
            actual=deterministic_repeat_consistent,
            threshold=bool(thresholds["deterministic_repeat_required"]),
            operator="is",
            passed=(not bool(thresholds["deterministic_repeat_required"])) or bool(deterministic_repeat_consistent),
            status="skipped" if not repeat_evidence_available else None,
            failure_reason="repeat_count_below_determinism_evidence_requirement" if not repeat_evidence_available else None,
        ),
        _threshold_check(
            "backtest_identity_repeat_consistent",
            actual=bool(
                backtest_identity.get("cache_keys_consistent", False)
                and backtest_identity.get("result_hashes_consistent", False)
                and backtest_identity.get("ranking_identity_consistent", False)
            ),
            threshold=True,
            operator="is",
            passed=bool(
                backtest_identity.get("cache_keys_consistent", False)
                and backtest_identity.get("result_hashes_consistent", False)
                and backtest_identity.get("ranking_identity_consistent", False)
            ),
            status="skipped" if not repeat_evidence_available else None,
            failure_reason="repeat_count_below_backtest_identity_evidence_requirement" if not repeat_evidence_available else None,
        ),
        _threshold_check(
            "feature_cache_reuse_measured",
            actual=bool(feature_cache_reuse.get("measured", False)),
            threshold=True,
            operator="is",
            passed=bool(feature_cache_reuse.get("measured", False)),
            status="skipped" if repeat_count < feature_cache_repeat_required else None,
            failure_reason="repeat_count_below_feature_cache_reuse_requirement" if repeat_count < feature_cache_repeat_required else None,
        ),
        _threshold_check(
            "feature_output_hashes_match",
            actual=bool(feature_cache_reuse.get("feature_output_hashes_match", False)),
            threshold=True,
            operator="is",
            passed=bool(feature_cache_reuse.get("feature_output_hashes_match", False)),
            status="skipped" if repeat_count < feature_cache_repeat_required else None,
            failure_reason="repeat_count_below_feature_cache_reuse_requirement" if repeat_count < feature_cache_repeat_required else None,
        ),
        _threshold_check(
            "optimizer_parallel_result_equivalence",
            actual=bool(
                optimizer_parallel_speedup.get("result_hashes_equal", False)
                and optimizer_parallel_speedup.get("stability_region_hashes_equal", False)
            ),
            threshold=True,
            operator="is",
            passed=bool(
                optimizer_parallel_speedup.get("result_hashes_equal", False)
                and optimizer_parallel_speedup.get("stability_region_hashes_equal", False)
            ),
        ),
        _threshold_check(
            "optimizer_parallel_timing_measured",
            actual=bool(
                optimizer_parallel_speedup.get("measured", False)
                and float(optimizer_parallel_speedup.get("serial_elapsed_seconds_median", 0.0)) > 0.0
                and float(optimizer_parallel_speedup.get("parallel_elapsed_seconds_median", 0.0)) > 0.0
                and float(optimizer_parallel_speedup.get("speedup_factor", 0.0)) > 0.0
            ),
            threshold=True,
            operator="is",
            passed=bool(
                optimizer_parallel_speedup.get("measured", False)
                and float(optimizer_parallel_speedup.get("serial_elapsed_seconds_median", 0.0)) > 0.0
                and float(optimizer_parallel_speedup.get("parallel_elapsed_seconds_median", 0.0)) > 0.0
                and float(optimizer_parallel_speedup.get("speedup_factor", 0.0)) > 0.0
            ),
        ),
        _threshold_check(
            "reference_vs_vector_backend_comparison_measured",
            actual=backend_comparison_measured,
            threshold=True,
            operator="is",
            passed=backend_comparison_measured,
            failure_reason="missing_reference_vs_vector_backend_comparison_evidence",
            evidence_required=True,
        ),
        _threshold_check(
            "reference_vs_vector_behavioral_equivalence",
            actual=behavioral_equivalence,
            threshold=True,
            operator="is",
            passed=behavioral_equivalence,
        ),
        _threshold_check(
            "vector_supported_scope_used",
            actual=vector_supported_scope_used,
            threshold=True,
            operator="is",
            passed=vector_supported_scope_used,
        ),
        _threshold_check(
            "vector_speed_claim_not_made",
            actual=speed_claim_not_made,
            threshold=True,
            operator="is",
            passed=speed_claim_not_made,
        ),
        _threshold_check(
            "live_fetch_used",
            actual=bool(live_fetch_used),
            threshold=False,
            operator="is",
            passed=not bool(live_fetch_used),
        ),
        _threshold_check(
            "order_placement_used",
            actual=bool(order_placement_used),
            threshold=False,
            operator="is",
            passed=not bool(order_placement_used),
        ),
        _threshold_check(
            "backtest_cache_lookup_used",
            actual=bool(backtest_cache_lookup_used),
            threshold=False,
            operator="is",
            passed=not bool(backtest_cache_lookup_used),
        ),
        _threshold_check(
            "backtest_cache_hit",
            actual=bool(backtest_cache_hit),
            threshold=False,
            operator="is",
            passed=not bool(backtest_cache_hit),
        ),
        _threshold_check(
            "execution_cache_reuse_enabled",
            actual=bool(execution_cache_reuse_enabled),
            threshold=False,
            operator="is",
            passed=not bool(execution_cache_reuse_enabled),
        ),
    ]
    failure_reasons = [
        str(check["failure_reason"])
        for check in checks
        if str(check["status"]) == "failed" and str(check["failure_reason"])
    ]
    skipped_reasons = [
        str(check["failure_reason"])
        for check in checks
        if str(check["status"]) == "skipped" and str(check["failure_reason"])
    ]
    incomplete_evidence_reasons = [
        str(check["failure_reason"])
        for check in checks
        if bool(check.get("evidence_required", False))
        and str(check["status"]) == "failed"
        and str(check["failure_reason"])
    ]
    return {
        "gate_version": "historical-research-cycle-benchmark-gate-v1",
        "profile_version": _benchmark_gate_profile_version(resolved_data_scope),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "benchmark_data_scope": resolved_data_scope,
        "scope": _benchmark_gate_scope(resolved_data_scope),
        "claim_scope": "regression_guardrail_not_live_or_profit_claim",
        "thresholds": thresholds,
        "checks": checks,
        "evidence_complete": not skipped_reasons and not incomplete_evidence_reasons,
        "passed": not failure_reasons and not skipped_reasons and not incomplete_evidence_reasons,
        "failure_reasons": failure_reasons,
        "skipped_reasons": skipped_reasons,
        "incomplete_evidence_reasons": incomplete_evidence_reasons,
    }


def _threshold_check(
    name: str,
    *,
    actual: Any,
    threshold: Any,
    operator: str,
    passed: bool,
    status: str | None = None,
    failure_reason: str | None = None,
    evidence_required: bool = False,
) -> dict[str, Any]:
    resolved_status = status or ("passed" if passed else "failed")
    resolved_failure_reason = failure_reason if failure_reason is not None else ("" if passed else f"{name}_threshold_failed")
    return {
        "check_id": name,
        "name": name,
        "metric": name,
        "observed": actual,
        "actual": actual,
        "threshold": threshold,
        "comparator": operator,
        "operator": operator,
        "passed": bool(passed) if resolved_status != "skipped" else True,
        "status": resolved_status,
        "failure_reason": resolved_failure_reason,
        "evidence_required": bool(evidence_required),
    }


def _ranking_identity_hash(rankings: pd.DataFrame) -> str:
    columns = [
        "candidate_id",
        "aggregate_rank",
        "optimizer_rank",
        "aggregate_backtest_cache_key",
        "aggregate_backtest_result_sha256",
    ]
    missing = [column for column in columns if column not in rankings.columns]
    if missing:
        raise ValueError("candidate rankings missing identity columns: " + ",".join(missing))
    records = (
        rankings.loc[:, columns]
        .sort_values("candidate_id", kind="mergesort")
        .to_dict("records")
    )
    return _stable_hash({"ranking_identity_records": records})


def _summary(runs: list[dict[str, Any]]) -> dict[str, float]:
    fields = ("elapsed_seconds", "rows_per_second", "candidate_backtests_per_minute", "feature_rows_per_second")
    return {
        f"{field}_mean": round(sum(float(run[field]) for run in runs) / max(len(runs), 1), 6)
        for field in fields
    }


def _artifact_overhead(root: Path) -> dict[str, Any]:
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    section_file_counts: dict[str, int] = {}
    section_bytes: dict[str, int] = {}
    total_bytes = 0
    for path in files:
        relative = path.relative_to(root)
        section = relative.parts[0] if relative.parts else path.name
        size = int(path.stat().st_size)
        section_file_counts[section] = section_file_counts.get(section, 0) + 1
        section_bytes[section] = section_bytes.get(section, 0) + size
        total_bytes += size

    final_report_path = root / "research_cycle_benchmark_report.json"
    backend_section = "backend_comparison"
    return {
        "scope": "benchmark_directory_after_all_benchmark_artifacts_exist",
        "measurement_phase": "post_backend_comparison_and_final_report_write",
        "root": str(root),
        "file_count": int(len(files)),
        "total_bytes": int(total_bytes),
        "section_file_counts": dict(sorted(section_file_counts.items())),
        "section_bytes": dict(sorted(section_bytes.items())),
        "included_sections": sorted(section_file_counts),
        "includes_backend_comparison": section_file_counts.get(backend_section, 0) > 0,
        "backend_comparison_file_count": int(section_file_counts.get(backend_section, 0)),
        "backend_comparison_bytes": int(section_bytes.get(backend_section, 0)),
        "includes_final_report": final_report_path.is_file(),
        "final_report_path": str(final_report_path),
        "final_report_bytes": int(final_report_path.stat().st_size) if final_report_path.is_file() else 0,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _stable_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode("utf-8")).hexdigest()
