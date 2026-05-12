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


def _r97_screening_evaluator(config: CandidateConfig) -> CandidateResult:
    threshold = float(config.parameters["threshold"])
    if threshold in {0.1, 0.2}:
        backend = "tensorcore_screening"
    else:
        backend = "cuda_batched_fixed_holding"
    return CandidateResult(
        config,
        base_score=1.0 - min(abs(threshold - 0.3), 1.0),
        trade_count=10,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
        metadata={
            "screening_backend_used": backend,
            "tensorcore_screening_evidence": {
                "screening_module": "cuda_screening_batch_v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "diagnostic_only": True,
                "candidate_gate_eligible": False,
                "speed_claimed": False,
            },
            "parity_rechecked": backend == "cuda_batched_fixed_holding",
            "parity_mismatch": threshold == 0.4,
        },
    )


def _r97_reference_validation_evaluator(config: CandidateConfig) -> CandidateResult:
    threshold = float(config.parameters["threshold"])
    return CandidateResult(
        config,
        base_score=1.0 - min(abs(threshold - 0.3), 1.0),
        trade_count=10,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
        metadata={
            "validation_backend_used": "reference",
            "cpu_reference_validated": True,
            "parity_rechecked": True,
            "parity_mismatch": False,
        },
    )


def test_stability_region_search_r97_counters_distinguish_tensorcore_gpu_exact_and_reference_validation() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 0.3, 0.4)})
    report = StabilityRegionSearchController(
        space,
        StabilityRegionSearchConfig(
            screening_method="grid",
            screening_budget=4,
            top_regions=1,
            refinement_budget_per_region=1,
            screening_backend="tensorcore_screening",
            validation_backend="reference",
            pass_score=0.5,
        ),
    ).run(
        _r97_screening_evaluator,
        validation_evaluator=_r97_reference_validation_evaluator,
    ).to_payload()

    counters = report["counters"]
    assert counters["tensorcore_screened_count"] >= 1
    assert counters["gpu_exact_screened_count"] >= 1
    assert counters["cpu_reference_validated_count"] == len(report["validation_results"])
    assert counters["parity_rechecked_count"] >= counters["gpu_exact_screened_count"]
    assert counters["mismatch_count"] == 1
    assert "gpu_screened_count" in counters
    assert "cpu_screened_count" in counters
    assert "cpu_validated_count" in counters
    assert counters["screening_observed_backend_counts"]["tensorcore_screening"] >= 1
    assert counters["screening_observed_backend_counts"]["cuda_batched_fixed_holding"] >= 1
    assert counters["validation_observed_backend_counts"] == {"reference": len(report["validation_results"])}


def test_tensorcore_screening_stage_evidence_is_diagnostic_only_and_not_promotion_claim() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 0.3)})
    report = StabilityRegionSearchController(
        space,
        StabilityRegionSearchConfig(
            screening_method="grid",
            screening_budget=3,
            top_regions=1,
            screening_backend="tensorcore_screening",
            validation_backend="reference",
            pass_score=0.5,
        ),
    ).run(
        _r97_screening_evaluator,
        validation_evaluator=_r97_reference_validation_evaluator,
    ).to_payload()

    screen_stage = report["stage_reports"][0]
    evidence = screen_stage["tensorcore_screening_evidence"]
    assert evidence["screening_module"] == "cuda_screening_batch_v1"
    assert evidence["research_only"] is True
    assert evidence["observe_only"] is True
    assert evidence["promotion_ready"] is False
    assert evidence["diagnostic_only"] is True
    assert evidence["candidate_gate_eligible"] is False
    assert evidence["speed_claimed"] is False
    assert report["promotion_ready"] is False


def test_tensorcore_screening_no_gpu_fallback_is_stable_cpu_reference_diagnostic() -> None:
    space = SearchSpace("trend_following_v1", {"threshold": (0.1, 0.2, 0.3)})

    def cpu_fallback_evaluator(config: CandidateConfig) -> CandidateResult:
        threshold = float(config.parameters["threshold"])
        return CandidateResult(
            config,
            base_score=1.0 - min(abs(threshold - 0.2), 1.0),
            trade_count=10,
            split_consistency=0.8,
            side_balance=0.8,
            regime_coverage=0.8,
            cost_stress_survival=0.8,
            metadata={
                "screening_backend_used": "reference",
                "tensorcore_screening_evidence": {
                    "screening_module": "cuda_screening_batch_v1",
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "diagnostic_only": True,
                    "candidate_gate_eligible": False,
                    "speed_claimed": False,
                    "execution_status": "fallback_cpu_reference_no_gpu",
                    "fallback_reason": "tensorcore_runtime_unavailable",
                },
            },
        )

    report = StabilityRegionSearchController(
        space,
        StabilityRegionSearchConfig(
            screening_method="grid",
            screening_budget=3,
            top_regions=1,
            screening_backend="tensorcore_screening",
            validation_backend="reference",
            pass_score=0.5,
        ),
    ).run(cpu_fallback_evaluator, validation_evaluator=_r97_reference_validation_evaluator).to_payload()

    counters = report["counters"]
    evidence = report["stage_reports"][0]["tensorcore_screening_evidence"]
    assert counters["tensorcore_screened_count"] == 0
    assert counters["gpu_exact_screened_count"] == 0
    assert counters["cpu_screened_count"] == counters["screening_backend_observed_count"]
    assert evidence["execution_status"] == "fallback_cpu_reference_no_gpu"
    assert evidence["fallback_reason"] == "tensorcore_runtime_unavailable"
    assert evidence["promotion_ready"] is False
