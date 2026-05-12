from __future__ import annotations

from typing import Any, Mapping

from tradingbotsuite.backtesting import cuda_runtime_evidence
from tradingbotsuite.optimization import SearchSpace
from tradingbotsuite.research.live_readiness import research_boundary_metadata


CANDIDATE_SELECTION_PERFORMANCE_PLAN_VERSION = "candidate-selection-performance-plan-v1"
R97_CUDA_EXECUTION_PROFILES = {"cuda_exact_batched", "hybrid_tensorcore_screening"}
CPU_VECTOR_EXECUTION_PROFILE_STATUSES = {
    "fastest_exact": "gpu_execution_profile_fastest_exact_vector_selected",
    "conservative": "gpu_execution_profile_conservative",
}


def build_candidate_selection_performance_plan(
    *,
    spec: Any,
    candidates: list[Mapping[str, Any]],
    search_mode: str,
    search_method: str,
    aggregate_backtest_workers_used: int,
) -> dict[str, Any]:
    brute_force_count = _bruteforce_equivalent_count(spec)
    research_candidate_count = sum(1 for candidate in candidates if not bool(candidate.get("comparator_injected", False)))
    materialized_optimizer_count = sum(1 for candidate in candidates if str(candidate.get("candidate_source")) == "optimizer_search_space")
    materialized_search_count = materialized_optimizer_count if spec.optimizer.search_spaces else research_candidate_count
    screening_candidates = _screening_candidates(spec, candidates)
    raw_sampled_fraction = float(materialized_search_count / brute_force_count) if brute_force_count > 0 else 1.0
    sampled_fraction = min(1.0, raw_sampled_fraction)
    compute = spec.compute.to_payload(include_r97_defaults=True)
    gpu_requested = compute["gpu_acceleration"] != "disabled"
    r97_batched_profile_requested = str(compute.get("gpu_execution_profile")) in R97_CUDA_EXECUTION_PROFILES
    tensorcore_screening_requested = (
        str(compute.get("gpu_execution_profile")) == "hybrid_tensorcore_screening"
        and str(compute.get("tensor_core_policy")) == "screening_only"
    )
    requested_backend = str(spec.backtest_backend)
    cuda_backend_selectable = requested_backend in {"cuda_fixed_holding", "cuda_batched_fixed_holding"} or (
        requested_backend == "auto" and gpu_requested and r97_batched_profile_requested
    )
    selected_cuda_backend = (
        "cuda_batched_fixed_holding"
        if requested_backend == "cuda_batched_fixed_holding"
        or (requested_backend == "auto" and gpu_requested and r97_batched_profile_requested)
        else "cuda_fixed_holding"
    )
    cuda_runtime_checked = bool(gpu_requested and cuda_backend_selectable)
    cuda_evidence = cuda_runtime_evidence() if cuda_runtime_checked else {}
    cuda_available = bool(cuda_evidence.get("available", False))
    gpu_execution_status = (
        "disabled_by_spec"
        if not gpu_requested
        else CPU_VECTOR_EXECUTION_PROFILE_STATUSES.get(
            str(compute.get("gpu_execution_profile")),
            f"gpu_execution_profile_{compute.get('gpu_execution_profile')}_cpu_vector_selected",
        )
        if requested_backend == "auto" and not r97_batched_profile_requested
        else f"{selected_cuda_backend}_backend_not_selected"
        if not cuda_backend_selectable
        else f"{selected_cuda_backend}_runtime_available"
        if cuda_available
        else str(cuda_evidence.get("unavailable_reason") or "disabled_by_spec")
    )
    planned_cuda_eligible = sum(1 for candidate in screening_candidates if _cuda_fixed_holding_candidate_eligible(candidate))
    planned_gpu_screened = int(planned_cuda_eligible if cuda_available and cuda_backend_selectable else 0)
    planned_cpu_screened = int(max(0, materialized_search_count - planned_gpu_screened))
    planned_cpu_validated = int(min(len(candidates), max(1, int(spec.optimizer.top_regions_to_refine))))
    planned_tensorcore_screened = int(planned_gpu_screened if tensorcore_screening_requested else 0)
    planned_parity_rechecked = int(round(planned_gpu_screened * float(compute["gpu_validation_sample_rate"])))
    return {
        "performance_plan_version": CANDIDATE_SELECTION_PERFORMANCE_PLAN_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "objective": "stable_candidate_region_search_close_to_full_grid_without_exhaustive_bruteforce",
        "candidate_search_mode": search_mode,
        "candidate_search_method": search_method,
        "method_sequence": list(spec.optimizer.method_sequence),
        "bruteforce_equivalent_candidate_count": int(brute_force_count),
        "materialized_search_candidate_count": int(materialized_search_count),
        "materialized_total_candidate_count": int(len(candidates)),
        "sampled_fraction_of_bruteforce": sampled_fraction,
        "raw_sampled_fraction_of_bruteforce": raw_sampled_fraction,
        "materialized_search_exceeds_bruteforce": bool(raw_sampled_fraction > 1.0),
        "bruteforce_avoidance_ratio": (
            max(1.0, float(brute_force_count / max(materialized_search_count, 1)))
            if brute_force_count > 0
            else 1.0
        ),
        "stability_region_policy": {
            "enabled": "stability_region_refine" in {str(item).lower() for item in spec.optimizer.method_sequence},
            "top_regions_to_refine": int(spec.optimizer.top_regions_to_refine),
            "selection_order": "aggregate_score_then_split_cost_stress_then_stability_region_gate",
            "required_validation_scope": "split_cost_stress_enriched",
            "accepted_decision_required": "accepted_region",
        },
        "stability_region_acceleration_counters": {
            "bruteforce_equivalent_count": int(brute_force_count),
            "planned_gpu_screened_count": planned_gpu_screened,
            "planned_cpu_screened_count": planned_cpu_screened,
            "planned_cuda_eligible_screened_count": int(planned_cuda_eligible),
            "planned_cuda_ineligible_screened_count": int(max(0, materialized_search_count - planned_cuda_eligible)),
            "planned_cpu_validated_count": planned_cpu_validated,
            "planned_region_refined_count": int(max(0, int(spec.optimizer.top_regions_to_refine))),
            "tensorcore_screened_count": planned_tensorcore_screened,
            "gpu_exact_screened_count": planned_gpu_screened,
            "cpu_reference_validated_count": planned_cpu_validated,
            "parity_rechecked_count": planned_parity_rechecked,
            "mismatch_count": 0,
            "estimated_bruteforce_avoidance_ratio": (
                max(1.0, float(brute_force_count / max(materialized_search_count, 1)))
                if brute_force_count > 0
                else 1.0
            ),
        },
        "compute_policy": {
            **compute,
            "aggregate_backtest_workers_used": int(aggregate_backtest_workers_used),
            "gpu_requested": bool(gpu_requested),
            "selected_cuda_backend": selected_cuda_backend if cuda_backend_selectable else "",
            "r97_batched_cuda_requested": bool(r97_batched_profile_requested and gpu_requested),
            "tensorcore_screening_requested": bool(tensorcore_screening_requested),
            "gpu_execution_status": gpu_execution_status,
            "cuda_runtime_checked": cuda_runtime_checked,
            "cuda_runtime_available": cuda_available,
            "cuda_runtime_evidence": dict(cuda_evidence),
            "gpu_truthfulness": _gpu_truthfulness(
                gpu_requested=gpu_requested,
                cuda_backend_selectable=cuda_backend_selectable,
            ),
            "cpu_execution_status": "enabled" if aggregate_backtest_workers_used > 1 else "serial",
        },
        "selection_limitations": [
            "This is a candidate-search efficiency plan, not a live-ready candidate claim.",
            "GPU acceleration is not claimed unless a concrete CUDA backend writes backend evidence.",
            "Close-to-bruteforce behavior is inferred from stability-region coverage and validation evidence, not exhaustive enumeration.",
        ],
    }


def _gpu_truthfulness(*, gpu_requested: bool, cuda_backend_selectable: bool) -> str:
    if not gpu_requested:
        return "GPU disabled by spec."
    if not cuda_backend_selectable:
        return (
            "GPU was not selected by this compute profile. The default fastest_exact route uses CPU vector "
            "aggregate screening unless cuda_exact_batched or hybrid_tensorcore_screening is explicitly requested."
        )
    return "CUDA fixed-holding backend is optional and diagnostic until parity evidence exists for the same spec/backend version."


def _bruteforce_equivalent_count(spec: Any) -> int:
    if spec.optimizer.search_spaces:
        total = 0
        for payload in spec.optimizer.search_spaces:
            total += SearchSpace.from_payload(payload).grid_size()
        return int(total)
    # Metadata search spaces are generated per strategy/feature/window/exit in
    # the runner. The exact supported-combination filter is runner-local, so the
    # honest lower-bound equivalent is the materialized per-strategy cap.
    strategy_count = max(1, len(tuple(spec.strategies)))
    feature_count = max(1, len(tuple(spec.features.feature_sets)))
    window_count = max(1, len(tuple(spec.holding_windows)))
    exit_count = max(1, len(tuple(spec.exits.exit_policies)))
    return int(strategy_count * feature_count * window_count * exit_count * max(1, int(spec.optimizer.max_candidates_per_strategy)))


def _screening_candidates(spec: Any, candidates: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if spec.optimizer.search_spaces:
        pool = [
            candidate
            for candidate in candidates
            if str(candidate.get("candidate_source")) == "optimizer_search_space"
        ]
    else:
        pool = [
            candidate
            for candidate in candidates
            if not bool(candidate.get("comparator_injected", False))
        ]
    return pool or list(candidates)


def _cuda_fixed_holding_candidate_eligible(candidate: Mapping[str, Any]) -> bool:
    exit_policy_id = str(candidate.get("exit_policy_id") or "fixed_holding_window").lower()
    exit_price_source = str(candidate.get("exit_price_source") or "primary_close").lower()
    return (
        (exit_policy_id == "fixed_holding_window" or exit_policy_id.endswith("_time_exit"))
        and exit_price_source == "primary_close"
    )
