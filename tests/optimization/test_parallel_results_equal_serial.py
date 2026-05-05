from __future__ import annotations

from tradingbotsuite.optimization import CandidateCache, CandidateConfig, CandidateResult, OptimizationRun, SearchSpace


def _evaluate(config: CandidateConfig) -> CandidateResult:
    threshold = float(config.parameters["threshold"])
    return CandidateResult(
        config,
        base_score=threshold,
        split_consistency=threshold,
        side_balance=0.7,
        regime_coverage=0.7,
        cost_stress_survival=0.7,
    )


def test_parallel_results_equal_serial() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 0.3, 0.4)})

    serial = OptimizationRun(space, workers=1).run(_evaluate).to_payload()
    parallel = OptimizationRun(space, workers=3).run(_evaluate).to_payload()

    assert serial["results"] == parallel["results"]
    assert serial["stability_regions"] == parallel["stability_regions"]


def test_optimizer_report_records_per_run_cache_telemetry() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 0.3)})
    cache = CandidateCache(
        dataset_hash="dataset",
        feature_hash="feature",
        engine_version="engine",
        validation_hash="validation",
    )

    cold = OptimizationRun(space, workers=1).run(_evaluate, cache=cache).to_payload()
    warm = OptimizationRun(space, workers=2).run(_evaluate, cache=cache).to_payload()

    assert cold["cache_telemetry"] == {
        "cache_enabled": True,
        "hits": 0,
        "misses": 3,
        "writes": 3,
        "hit_rate": 0.0,
        "cache_size": 3,
    }
    assert warm["cache_telemetry"] == {
        "cache_enabled": True,
        "hits": 3,
        "misses": 0,
        "writes": 0,
        "hit_rate": 1.0,
        "cache_size": 3,
    }
    assert warm["multiple_comparison_control"]["nested_oos_required_for_acceptance"] is True


def test_optimizer_evaluates_duplicate_candidates_once() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.1, 0.1)})
    calls = 0

    def evaluate(config: CandidateConfig) -> CandidateResult:
        nonlocal calls
        calls += 1
        return _evaluate(config)

    report = OptimizationRun(space, workers=3).run(evaluate).to_payload()

    assert calls == 1
    assert report["total_candidates"] == 3
    assert report["effective_candidates"] == 1


def test_optimizer_staged_adaptive_refinement_reports_bootstrap_evidence() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 0.3, 0.4, 0.5)})

    def evaluate(config: CandidateConfig) -> CandidateResult:
        threshold = float(config.parameters["threshold"])
        return CandidateResult(
            config,
            base_score=threshold,
            trade_count=10,
            split_consistency=0.8,
            side_balance=0.7,
            regime_coverage=0.7,
            cost_stress_survival=0.7,
            metadata={"split_scores": [threshold - 0.01, threshold, threshold + 0.01]},
        )

    report = OptimizationRun(
        space,
        method_sequence=("coarse_lhs", "adaptive_grid", "stability_region_refine"),
        max_candidates=3,
        refinement_top_k=1,
        bootstrap_repeats=8,
        workers=2,
    ).run(evaluate).to_payload()

    thresholds = {result["config"]["parameters"]["threshold"] for result in report["results"]}
    stage_methods = [stage["method"] for stage in report["stage_reports"]]

    assert thresholds == {0.1, 0.2, 0.3, 0.4}
    assert stage_methods == ["coarse_lhs", "adaptive_grid", "stability_region_refine"]
    assert report["stage_reports"][1]["generation_scope"] == "local_neighbors_of_prior_stage_candidates"
    assert report["stage_reports"][1]["unique_candidate_count"] == 1
    assert report["multiple_comparison_control"]["search_stage_count"] == 3
    assert report["multiple_comparison_control"]["candidate_trials_by_stage"]["adaptive_grid"] == 3
    assert report["bootstrap_validation"]["bootstrap_validation_version"] == "optimizer-bootstrap-validation-v1"
    assert report["bootstrap_validation"]["candidate_count"] == len(report["results"])
    assert report["bootstrap_validation"]["nested_oos_required_for_acceptance"] is True
