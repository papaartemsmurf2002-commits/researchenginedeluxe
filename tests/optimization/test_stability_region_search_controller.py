from __future__ import annotations

from tradingbotsuite.optimization import (
    CandidateConfig,
    CandidateResult,
    SearchSpace,
    StabilityRegionSearchConfig,
    StabilityRegionSearchController,
)


def _plateau_evaluator(config: CandidateConfig, *, backend: str = "cuda_fixed_holding") -> CandidateResult:
    threshold = float(config.parameters["threshold"])
    score = 1.0 - min(abs(threshold - 0.5), 1.0)
    return CandidateResult(
        config,
        base_score=score,
        trade_count=10,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
        metadata={"split_scores": [score - 0.01, score, score + 0.01], "backtest_backend_used": backend},
    )


def test_stability_region_search_refines_plateau_without_full_grid() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)})
    report = StabilityRegionSearchController(
        space,
        StabilityRegionSearchConfig(
            screening_method="grid",
            screening_budget=4,
            top_regions=1,
            refinement_budget_per_region=3,
            screening_backend="cuda_fixed_holding",
            validation_backend="reference",
        ),
    ).run(
        _plateau_evaluator,
        validation_evaluator=lambda config: _plateau_evaluator(config, backend="reference"),
    ).to_payload()

    evaluated_thresholds = {result["config"]["parameters"]["threshold"] for result in report["results"]}
    counters = report["counters"]

    assert 0.5 in evaluated_thresholds
    assert counters["bruteforce_equivalent_count"] == 6
    assert counters["materialized_evaluation_count"] < counters["bruteforce_equivalent_count"]
    assert counters["gpu_screened_count"] == 5
    assert counters["screening_observed_backend_counts"] == {"cuda_fixed_holding": 5}
    assert counters["cpu_validated_count"] == 1
    assert counters["validation_evaluation_count"] == 1
    assert counters["validation_observed_backend_counts"] == {"reference": 1}
    assert counters["region_refined_count"] == 1
    assert counters["estimated_bruteforce_avoidance_ratio"] > 1.0
    assert report["stage_reports"][2]["stage"] == "cpu_validation_shortlist"
    assert report["stage_reports"][2]["execution_status"] == "executed"
    assert report["research_only"] is True
    assert report["promotion_ready"] is False


def test_stability_region_search_does_not_select_rejected_spike() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 1.0)})

    def evaluate(config: CandidateConfig) -> CandidateResult:
        threshold = float(config.parameters["threshold"])
        score = 1.0 if threshold == 1.0 else 0.8
        return CandidateResult(
            config,
            base_score=score,
            trade_count=10,
            split_consistency=0.8,
            side_balance=0.8,
            regime_coverage=0.8,
            cost_stress_survival=0.8,
            metadata={"backtest_backend_used": "reference"},
        )

    report = StabilityRegionSearchController(
        space,
        StabilityRegionSearchConfig(
            screening_method="grid",
            screening_budget=3,
            top_regions=1,
            refinement_budget_per_region=3,
            pass_score=0.7,
        ),
    ).run(evaluate, validation_evaluator=evaluate).to_payload()

    selected_thresholds = {
        result["config"]["parameters"]["threshold"]
        for result in report["results"]
        if result["candidate_id"] in set(report["selected_candidate_ids"])
    }
    selected_regions = [
        region
        for region in report["stability_regions"]
        if region["center_candidate_id"] in set(report["selected_candidate_ids"])
    ]

    assert selected_thresholds != {1.0}
    assert selected_regions
    assert {region["decision"] for region in selected_regions} == {"accepted_region"}


def test_stability_region_search_does_not_count_unexecuted_validation() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 0.3)})
    report = StabilityRegionSearchController(
        space,
        StabilityRegionSearchConfig(screening_method="grid", screening_budget=3, top_regions=1),
    ).run(_plateau_evaluator).to_payload()

    assert report["counters"]["cpu_validated_count"] == 0
    assert report["counters"]["validation_evaluation_count"] == 0
    assert report["stage_reports"][2]["execution_status"] == "not_executed_validation_evaluator_missing"
