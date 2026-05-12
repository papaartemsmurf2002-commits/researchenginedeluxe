from __future__ import annotations

from typing import Any, Mapping

from tradingbotsuite.optimization import SearchSpace
from tradingbotsuite.research.live_readiness import research_boundary_metadata


CANDIDATE_SELECTION_PERFORMANCE_PLAN_VERSION = "candidate-selection-performance-plan-v1"


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
    raw_sampled_fraction = float(materialized_search_count / brute_force_count) if brute_force_count > 0 else 1.0
    sampled_fraction = min(1.0, raw_sampled_fraction)
    compute = spec.compute.to_payload()
    gpu_requested = compute["gpu_acceleration"] != "disabled"
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
        "compute_policy": {
            **compute,
            "aggregate_backtest_workers_used": int(aggregate_backtest_workers_used),
            "gpu_requested": bool(gpu_requested),
            "gpu_execution_status": (
                "blocked_no_cuda_backtest_backend_registered"
                if gpu_requested
                else "disabled_by_spec"
            ),
            "gpu_truthfulness": (
                "NVIDIA/CUDA preference is recorded for scheduling only; this runner has no CUDA execution backend yet."
                if gpu_requested
                else "GPU disabled by spec."
            ),
            "cpu_execution_status": "enabled" if aggregate_backtest_workers_used > 1 else "serial",
        },
        "selection_limitations": [
            "This is a candidate-search efficiency plan, not a live-ready candidate claim.",
            "GPU acceleration is not claimed unless a concrete CUDA backend writes backend evidence.",
            "Close-to-bruteforce behavior is inferred from stability-region coverage and validation evidence, not exhaustive enumeration.",
        ],
    }


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
