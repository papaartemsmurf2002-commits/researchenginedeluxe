from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from tradingbotsuite.optimization.candidate import CandidateConfig, CandidateResult
from tradingbotsuite.optimization.gpu_screening import (
    CUDA_SCREENING_SCOPE,
    merge_wpr97_screening_counters,
)
from tradingbotsuite.optimization.search_space import SearchSpace
from tradingbotsuite.optimization.stability import StabilityRegion, rank_by_stability


StabilityEvaluator = Callable[[CandidateConfig], CandidateResult]
GPU_EXACT_SCREENING_BACKENDS = {"cuda_fixed_holding", "cuda_batched_fixed_holding"}
TENSORCORE_SCREENING_BACKENDS = {CUDA_SCREENING_SCOPE, "tensorcore_screening"}


@dataclass(frozen=True, slots=True)
class StabilityRegionSearchConfig:
    screening_method: str = "grid"
    screening_budget: int = 64
    top_regions: int = 3
    refinement_radius_steps: int = 1
    refinement_budget_per_region: int = 8
    screening_backend: str = "cpu"
    validation_backend: str = "reference"
    pass_score: float = 0.0


@dataclass(frozen=True, slots=True)
class StabilityRegionSearchReport:
    results: tuple[CandidateResult, ...]
    validation_results: tuple[CandidateResult, ...]
    stability_regions: tuple[StabilityRegion, ...]
    selected_candidate_ids: tuple[str, ...]
    counters: dict[str, Any]
    stage_reports: tuple[dict[str, Any], ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "stability_region_search_report_version": "stability-region-search-report-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "counters": dict(self.counters),
            "stage_reports": [dict(stage) for stage in self.stage_reports],
            "results": [result.to_payload() for result in self.results],
            "validation_results": [result.to_payload() for result in self.validation_results],
            "stability_regions": [region.to_payload() for region in self.stability_regions],
        }


class StabilityRegionSearchController:
    """Broad screen plus local region refinement before expensive validation."""

    def __init__(self, search_space: SearchSpace, config: StabilityRegionSearchConfig | None = None) -> None:
        self.search_space = search_space
        self.config = config or StabilityRegionSearchConfig()

    def run(
        self,
        evaluator: StabilityEvaluator,
        *,
        validation_evaluator: StabilityEvaluator | None = None,
    ) -> StabilityRegionSearchReport:
        screened = _unique_candidates(
            self.search_space.expand(
                method=self.config.screening_method,
                max_candidates=max(1, int(self.config.screening_budget)),
            )
        )
        screening_results_by_id = _evaluate_unique(screened, evaluator)
        results_by_id = dict(screening_results_by_id)
        screening_regions = rank_by_stability(results_by_id.values(), pass_score=float(self.config.pass_score))
        refinement_candidates: list[CandidateConfig] = []
        for region in _accepted_regions(screening_regions)[: max(1, int(self.config.top_regions))]:
            refinement_candidates.extend(
                _region_refinement_candidates(
                    region,
                    results_by_id,
                    self.search_space,
                    radius_steps=max(1, int(self.config.refinement_radius_steps)),
                    max_candidates=max(1, int(self.config.refinement_budget_per_region)),
                )
            )
        new_refinement = [
            candidate
            for candidate in _unique_candidates(refinement_candidates)
            if candidate.cache_key() not in results_by_id
        ]
        refinement_results_by_id = _evaluate_unique(new_refinement, evaluator)
        results_by_id.update(refinement_results_by_id)
        final_regions = rank_by_stability(results_by_id.values(), pass_score=float(self.config.pass_score))
        accepted_final_regions = _accepted_regions(final_regions)
        selected = tuple(region.center_candidate_id for region in accepted_final_regions[: max(1, int(self.config.top_regions))])
        validation_candidates = [
            results_by_id[candidate_id].config
            for candidate_id in selected
            if candidate_id in results_by_id
        ]
        validation_results_by_id = (
            _evaluate_unique(validation_candidates, validation_evaluator)
            if validation_evaluator is not None
            else {}
        )
        counters = _search_counters(
            search_space=self.search_space,
            screening_results=[*screening_results_by_id.values(), *refinement_results_by_id.values()],
            validation_results=list(validation_results_by_id.values()),
            broad_screened_count=len(screened),
            refined_count=len(new_refinement),
            selected_count=len(selected),
            total_evaluated=len(results_by_id),
        )
        stage_reports = (
            _stage_report(
                "broad_screen",
                self.config.screening_backend,
                len(screened),
                len(screening_results_by_id),
                screening_results_by_id.values(),
            ),
            _stage_report(
                "local_region_refine",
                self.config.screening_backend,
                len(refinement_candidates),
                len(refinement_results_by_id),
                refinement_results_by_id.values(),
            ),
            _stage_report(
                "cpu_validation_shortlist",
                self.config.validation_backend,
                len(selected),
                len(validation_results_by_id),
                validation_results_by_id.values(),
                execution_status=(
                    "executed"
                    if validation_evaluator is not None
                    else "not_executed_validation_evaluator_missing"
                ),
            ),
        )
        return StabilityRegionSearchReport(
            results=tuple(sorted(results_by_id.values(), key=lambda result: result.candidate_id)),
            validation_results=tuple(sorted(validation_results_by_id.values(), key=lambda result: result.candidate_id)),
            stability_regions=tuple(final_regions),
            selected_candidate_ids=selected,
            counters=counters,
            stage_reports=stage_reports,
        )


def _stage_report(
    stage: str,
    backend: str,
    generated: int,
    result_count: int,
    results: Iterable[CandidateResult],
    *,
    execution_status: str = "executed",
) -> dict[str, Any]:
    result_list = list(results)
    report = {
        "stage": stage,
        "requested_backend": backend,
        "observed_backend_counts": _backend_counts(result_list),
        "generated_candidate_count": int(generated),
        "result_count": int(result_count),
        "execution_status": execution_status,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
    }
    tensorcore_evidence = _first_screening_evidence(result_list, key="tensorcore_screening_evidence")
    if tensorcore_evidence:
        report["tensorcore_screening_evidence"] = dict(tensorcore_evidence)
    gpu_evidence = _first_screening_evidence(result_list, key="gpu_screening_evidence")
    if gpu_evidence:
        report["gpu_screening_evidence"] = dict(gpu_evidence)
    return report


def _evaluate_unique(
    candidates: Iterable[CandidateConfig],
    evaluator: StabilityEvaluator,
) -> dict[str, CandidateResult]:
    results: dict[str, CandidateResult] = {}
    for candidate in candidates:
        key = candidate.cache_key()
        if key not in results:
            results[key] = evaluator(candidate)
    return results


def _unique_candidates(candidates: Iterable[CandidateConfig]) -> list[CandidateConfig]:
    seen: set[str] = set()
    unique: list[CandidateConfig] = []
    for candidate in candidates:
        key = candidate.cache_key()
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _region_refinement_candidates(
    region: StabilityRegion,
    results_by_id: dict[str, CandidateResult],
    search_space: SearchSpace,
    *,
    radius_steps: int,
    max_candidates: int,
) -> list[CandidateConfig]:
    members = [
        results_by_id[candidate_id]
        for candidate_id in region.member_candidate_ids
        if candidate_id in results_by_id
    ]
    if not members and region.center_candidate_id in results_by_id:
        members = [results_by_id[region.center_candidate_id]]
    members = sorted(members, key=lambda result: result.final_score, reverse=True)
    candidates: list[CandidateConfig] = []
    for member in members:
        candidates.extend(
            search_space.local_neighbors(
                member.config,
                radius_steps=radius_steps,
                max_candidates=max_candidates,
            )
        )
        unique = _unique_candidates(candidates)
        if len(unique) >= max_candidates:
            return unique[:max_candidates]
    return _unique_candidates(candidates)[:max_candidates]


def _accepted_regions(regions: Iterable[StabilityRegion]) -> list[StabilityRegion]:
    return [region for region in regions if str(region.decision) == "accepted_region"]


def _search_counters(
    *,
    search_space: SearchSpace,
    screening_results: list[CandidateResult],
    validation_results: list[CandidateResult],
    broad_screened_count: int,
    refined_count: int,
    selected_count: int,
    total_evaluated: int,
) -> dict[str, Any]:
    brute_force = search_space.grid_size()
    screening_backend_counts = _backend_counts(screening_results)
    validation_backend_counts = _backend_counts(validation_results)
    gpu_screened = int(
        sum(
            count
            for backend, count in screening_backend_counts.items()
            if backend in GPU_EXACT_SCREENING_BACKENDS
        )
    )
    cpu_validated = int(
        sum(
            count
            for backend, count in validation_backend_counts.items()
            if backend not in GPU_EXACT_SCREENING_BACKENDS
        )
    )
    observed_screened = sum(screening_backend_counts.values())
    counters = {
        "counter_version": "stability-region-search-counters-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "bruteforce_equivalent_count": int(brute_force),
        "materialized_evaluation_count": int(total_evaluated),
        "broad_screened_count": int(broad_screened_count),
        "gpu_screened_count": int(gpu_screened),
        "cpu_screened_count": int(
            sum(
                count
                for backend, count in screening_backend_counts.items()
                if backend not in GPU_EXACT_SCREENING_BACKENDS
                and backend not in TENSORCORE_SCREENING_BACKENDS
            )
        ),
        "screening_backend_observed_count": int(observed_screened),
        "screening_backend_unknown_count": int(max(0, len(screening_results) - observed_screened)),
        "screening_observed_backend_counts": dict(screening_backend_counts),
        "selected_candidate_count": int(selected_count),
        "cpu_validated_count": int(cpu_validated),
        "validation_evaluation_count": int(len(validation_results)),
        "validation_observed_backend_counts": dict(validation_backend_counts),
        "region_refined_count": int(refined_count),
        "estimated_bruteforce_avoidance_ratio": (
            max(1.0, float(brute_force / max(total_evaluated, 1)))
            if brute_force > 0
            else 1.0
        ),
    }
    return merge_wpr97_screening_counters(
        counters,
        tensorcore_screened_count=sum(_is_tensorcore_screening_result(result) for result in screening_results),
        gpu_exact_screened_count=gpu_screened,
        cpu_reference_validated_count=cpu_validated,
        parity_rechecked_count=sum(_parity_rechecked_count(result) for result in screening_results),
        mismatch_count=sum(_mismatch_count(result) for result in screening_results),
    )


def _backend_counts(results: Iterable[CandidateResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        backend = _observed_backend(result)
        if not backend:
            continue
        counts[backend] = counts.get(backend, 0) + 1
    return dict(sorted(counts.items()))


def _observed_backend(result: CandidateResult) -> str:
    metadata = dict(result.metadata or {})
    for key in ("backtest_backend_used", "screening_backend_used", "validation_backend_used", "backend_used"):
        backend = str(metadata.get(key) or "").strip()
        if backend:
            return backend
    return ""


def _is_tensorcore_screening_result(result: CandidateResult) -> bool:
    metadata = dict(result.metadata or {})
    if _observed_backend(result) in TENSORCORE_SCREENING_BACKENDS:
        return True
    evidence = _screening_evidence(metadata)
    return (
        bool(evidence.get("tensor_core_used"))
        or str(evidence.get("tensor_core_scope") or "") == CUDA_SCREENING_SCOPE
    )


def _parity_rechecked_count(result: CandidateResult) -> int:
    metadata = dict(result.metadata or {})
    if bool(metadata.get("parity_rechecked")):
        return 1
    evidence = _screening_evidence(metadata)
    if bool(evidence.get("parity_rechecked")):
        return 1
    parity_status = str(evidence.get("parity_status") or "").strip()
    return int(bool(parity_status and not parity_status.startswith("not_checked")))


def _mismatch_count(result: CandidateResult) -> int:
    metadata = dict(result.metadata or {})
    if bool(metadata.get("parity_mismatch")):
        return 1
    evidence = _screening_evidence(metadata)
    raw_count = evidence.get("mismatch_count")
    if raw_count is not None:
        try:
            return int(raw_count)
        except (TypeError, ValueError):
            return 0
    return int(str(evidence.get("parity_status") or "") == "mismatch")


def _screening_evidence(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in (
        "gpu_screening_evidence",
        "tensorcore_screening_evidence",
        "cuda_screening_evidence",
        "screening_evidence",
    ):
        evidence = metadata.get(key)
        if isinstance(evidence, Mapping):
            return evidence
    return metadata


def _first_screening_evidence(results: Iterable[CandidateResult], *, key: str) -> Mapping[str, Any]:
    for result in results:
        evidence = dict(result.metadata or {}).get(key)
        if isinstance(evidence, Mapping):
            return evidence
    return {}
