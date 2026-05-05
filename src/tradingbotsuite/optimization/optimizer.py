from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import random
from dataclasses import dataclass
from statistics import median
from typing import Any, Callable, Iterable

from tradingbotsuite.optimization.cache import CandidateCache
from tradingbotsuite.optimization.candidate import CandidateConfig, CandidateResult
from tradingbotsuite.optimization.search_space import SearchSpace
from tradingbotsuite.optimization.stability import StabilityRegion, rank_by_stability


Evaluator = Callable[[CandidateConfig], CandidateResult]


@dataclass(frozen=True, slots=True)
class OptimizationReport:
    results: tuple[CandidateResult, ...]
    stability_regions: tuple[StabilityRegion, ...]
    total_candidates: int
    effective_candidates: int
    parallel_workers: int
    cache_telemetry: dict[str, Any]
    multiple_comparison_control: dict[str, Any]
    stage_reports: tuple[dict[str, Any], ...] = ()
    bootstrap_validation: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "optimization_report_version": "optimizer-report-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "total_candidates": self.total_candidates,
            "effective_candidates": self.effective_candidates,
            "parallel_workers": self.parallel_workers,
            "cache_telemetry": dict(self.cache_telemetry),
            "multiple_comparison_control": dict(self.multiple_comparison_control),
            "stage_reports": [dict(stage) for stage in self.stage_reports],
            "bootstrap_validation": dict(self.bootstrap_validation or {}),
            "results": [result.to_payload() for result in self.results],
            "stability_regions": [region.to_payload() for region in self.stability_regions],
        }


@dataclass(frozen=True, slots=True)
class OptimizationRun:
    search_space: SearchSpace
    method: str = "grid"
    method_sequence: tuple[str, ...] = ()
    max_candidates: int = 64
    random_seed: int = 17
    workers: int = 1
    refinement_top_k: int = 3
    refinement_radius_steps: int = 1
    bootstrap_repeats: int = 64
    pass_score: float = 0.0

    def run(self, evaluator: Evaluator, *, cache: CandidateCache | None = None) -> OptimizationReport:
        cache_before = cache.telemetry_snapshot() if cache is not None else None
        results, stage_reports, total_candidate_trials = _evaluate_stages(self, evaluator, cache=cache)
        cache_after = cache.telemetry_snapshot() if cache is not None else None
        regions = rank_by_stability(results)
        return OptimizationReport(
            results=tuple(sorted(results, key=lambda result: result.candidate_id)),
            stability_regions=tuple(regions),
            total_candidates=total_candidate_trials,
            effective_candidates=len(results),
            parallel_workers=max(1, self.workers),
            cache_telemetry=_cache_telemetry_delta(cache_before, cache_after),
            multiple_comparison_control=_multiple_comparison_control(
                total_candidate_trials,
                len(results),
                stage_reports=stage_reports,
            ),
            stage_reports=tuple(stage_reports),
            bootstrap_validation=_bootstrap_validation(
                results,
                repeats=max(1, int(self.bootstrap_repeats)),
                random_seed=int(self.random_seed),
                pass_score=float(self.pass_score),
            ),
        )


def _evaluate_stages(
    run: OptimizationRun,
    evaluator: Evaluator,
    *,
    cache: CandidateCache | None,
) -> tuple[list[CandidateResult], list[dict[str, Any]], int]:
    methods = tuple(run.method_sequence) if run.method_sequence else (run.method,)
    reports: list[dict[str, Any]] = []
    seen: set[str] = set()
    results_by_id: dict[str, CandidateResult] = {}
    prior_results: list[CandidateResult] = []
    total_candidate_trials = 0
    for index, raw_method in enumerate(methods, start=1):
        method = str(raw_method).lower()
        if method in {"adaptive_grid", "stability_region_refine"} and not prior_results:
            generated = run.search_space.expand(
                method="grid",
                max_candidates=run.max_candidates,
                random_seed=run.random_seed,
            )
            generation_scope = "fallback_grid_no_prior_stage"
        elif method == "adaptive_grid":
            generated = _adaptive_candidates(run, _top_result_configs(prior_results, limit=max(1, int(run.refinement_top_k))))
            generation_scope = "local_neighbors_of_prior_stage_candidates"
        elif method == "stability_region_refine":
            generated = []
            generation_scope = "stability_report_only"
        else:
            generated = run.search_space.expand(
                method=method,
                max_candidates=run.max_candidates,
                random_seed=run.random_seed,
            )
            generation_scope = "search_space_expand"
        total_candidate_trials += len(generated)
        unique = []
        for candidate in generated:
            key = candidate.cache_key()
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        stage_results = _evaluate(unique, evaluator, cache=cache, workers=max(1, run.workers)) if unique else []
        for result in stage_results:
            results_by_id[result.candidate_id] = result
        prior_results = sorted(results_by_id.values(), key=lambda result: result.final_score, reverse=True)
        reports.append(
            {
                "stage_index": index,
                "method": method,
                "generation_scope": generation_scope,
                "generated_candidate_count": len(generated),
                "unique_candidate_count": len(unique),
                "duplicate_candidate_count": max(0, len(generated) - len(unique)),
                "result_count": len(stage_results),
                "cumulative_effective_candidates": len(results_by_id),
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
            }
        )
    return list(results_by_id.values()), reports, total_candidate_trials


def _adaptive_candidates(run: OptimizationRun, centers: list[CandidateConfig]) -> list[CandidateConfig]:
    candidates: list[CandidateConfig] = []
    per_center_budget = max(1, int(run.max_candidates) // max(1, len(centers)))
    for center in centers[: max(1, int(run.refinement_top_k))]:
        candidates.extend(
            run.search_space.local_neighbors(
                center,
                radius_steps=max(1, int(run.refinement_radius_steps)),
                max_candidates=per_center_budget,
            )
        )
    return candidates[: max(1, int(run.max_candidates))]


def _top_result_configs(results: list[CandidateResult], *, limit: int) -> list[CandidateConfig]:
    ordered = sorted(results, key=lambda result: (result.final_score, result.trade_count, result.candidate_id), reverse=True)
    return [result.config for result in ordered[: max(1, int(limit))]]


def _evaluate(
    candidates: Iterable[CandidateConfig],
    evaluator: Evaluator,
    *,
    cache: CandidateCache | None,
    workers: int,
) -> list[CandidateResult]:
    ordered = _unique_candidates(candidates)

    def evaluate_one(config: CandidateConfig) -> CandidateResult:
        cached = cache.get(config) if cache is not None else None
        if cached is not None:
            return cached
        result = evaluator(config)
        if cache is not None:
            cache.put(result)
        return result

    if workers == 1:
        return [evaluate_one(config) for config in ordered]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(evaluate_one, ordered))


def _unique_candidates(candidates: Iterable[CandidateConfig]) -> list[CandidateConfig]:
    seen: set[str] = set()
    ordered: list[CandidateConfig] = []
    for config in candidates:
        key = config.cache_key()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(config)
    return ordered


def _cache_telemetry_delta(before: dict[str, int] | None, after: dict[str, int] | None) -> dict[str, Any]:
    if before is None or after is None:
        return {
            "cache_enabled": False,
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "hit_rate": 0.0,
            "cache_size": 0,
        }
    hits = max(0, int(after["hits"]) - int(before["hits"]))
    misses = max(0, int(after["misses"]) - int(before["misses"]))
    writes = max(0, int(after["writes"]) - int(before["writes"]))
    total_reads = hits + misses
    return {
        "cache_enabled": True,
        "hits": hits,
        "misses": misses,
        "writes": writes,
        "hit_rate": float(hits / total_reads) if total_reads else 0.0,
        "cache_size": int(after["size"]),
    }


def _bootstrap_validation(
    results: list[CandidateResult],
    *,
    repeats: int,
    random_seed: int,
    pass_score: float,
) -> dict[str, Any]:
    rng = random.Random(random_seed)
    summaries = []
    for result in sorted(results, key=lambda item: item.candidate_id):
        scores = _result_resampling_scores(result)
        samples = [
            sum(rng.choice(scores) for _ in range(len(scores))) / len(scores)
            for _ in range(repeats)
        ]
        ordered = sorted(samples)
        lower_index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.25))))
        lower = float(ordered[lower_index])
        summaries.append(
            {
                "candidate_id": result.candidate_id,
                "sample_count": len(scores),
                "bootstrap_mean_score": float(sum(samples) / len(samples)),
                "bootstrap_median_score": float(median(samples)),
                "bootstrap_lower_quantile_score": lower,
                "bootstrap_pass_rate": float(sum(sample >= pass_score for sample in samples) / len(samples)),
            }
        )
    return {
        "bootstrap_validation_version": "optimizer-bootstrap-validation-v1",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "repeats": int(repeats),
        "random_seed": int(random_seed),
        "pass_score": float(pass_score),
        "candidate_count": len(summaries),
        "nested_oos_required_for_acceptance": True,
        "candidate_summaries": summaries,
    }


def _result_resampling_scores(result: CandidateResult) -> list[float]:
    raw_scores = result.metadata.get("split_scores") if isinstance(result.metadata, dict) else None
    if isinstance(raw_scores, (list, tuple)) and raw_scores:
        scores = [float(value) for value in raw_scores]
    else:
        scores = [result.final_score]
    return scores


def _multiple_comparison_control(
    total_candidates: int,
    effective_candidates: int,
    *,
    stage_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "total_candidates_tried": int(total_candidates),
        "effective_candidates": int(effective_candidates),
        "effective_candidates_after_dedup": int(effective_candidates),
        "search_stage_count": int(len(stage_reports)),
        "candidate_trials_by_stage": {
            str(stage["method"]): int(stage["generated_candidate_count"])
            for stage in stage_reports
        },
        "false_discovery_warning": bool(total_candidates >= 100 and effective_candidates < 20),
        "nested_oos_required_for_acceptance": True,
    }
