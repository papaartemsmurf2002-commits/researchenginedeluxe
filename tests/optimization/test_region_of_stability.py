from __future__ import annotations

from tradingbotsuite.optimization import CandidateConfig, CandidateResult, rank_by_stability


def _result(value: float, score: float) -> CandidateResult:
    return CandidateResult(
        CandidateConfig("trend_following_v1", {"threshold": value}),
        base_score=score,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
    )


def _validated_result(value: float, score: float) -> CandidateResult:
    return CandidateResult(
        CandidateConfig("trend_following_v1", {"threshold": value}),
        base_score=score,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
        metadata={"split_evaluation_count": 2, "cost_stress_evaluation_count": 4},
    )


def test_region_of_stability_groups_local_neighbors() -> None:
    regions = rank_by_stability([_result(0.30, 0.20), _result(0.32, 0.21), _result(0.34, 0.19)])

    assert regions[0].connected_region_size == 3
    assert regions[0].region_pass_rate == 1.0
    assert regions[0].decision == "accepted_region"


def test_region_of_stability_requires_validation_when_requested() -> None:
    regions = rank_by_stability(
        [_result(0.30, 0.20), _result(0.32, 0.21), _result(0.34, 0.19)],
        require_validation_evidence=True,
    )

    assert regions[0].decision == "rejected_incomplete_validation"
    assert regions[0].validation_enriched is False
    assert regions[0].stability_validation_scope == "aggregate_only_unvalidated_neighborhood"


def test_region_of_stability_accepts_validated_plateau_when_requested() -> None:
    regions = rank_by_stability(
        [_validated_result(0.30, 0.20), _validated_result(0.32, 0.21), _validated_result(0.34, 0.19)],
        require_validation_evidence=True,
    )

    assert regions[0].decision == "accepted_region"
    assert regions[0].validation_enriched is True
    assert regions[0].validated_member_count == 3
    assert regions[0].aggregate_only_member_count == 0


def test_region_of_stability_rejects_mixed_validation_region_when_requested() -> None:
    validated_center = _validated_result(0.30, 0.20)
    aggregate_neighbor = _result(0.32, 0.21)

    regions = rank_by_stability(
        [validated_center, aggregate_neighbor],
        require_validation_evidence=True,
    )
    center_region = next(region for region in regions if region.center_candidate_id == validated_center.candidate_id)

    assert center_region.decision == "rejected_incomplete_validation"
    assert center_region.validation_enriched is False
    assert center_region.stability_validation_scope == "mixed_validation_neighborhood"
    assert center_region.validated_member_count == 1
    assert center_region.aggregate_only_member_count == 1


def test_duplicate_candidate_results_do_not_inflate_region_size() -> None:
    duplicate = _result(0.30, 0.20)
    regions = rank_by_stability([duplicate, duplicate, _result(0.32, 0.21)])

    assert regions[0].connected_region_size == 2


def test_region_of_stability_keeps_exit_policy_identity_separate() -> None:
    fixed = _result(0.30, 0.20)
    max_mae = CandidateResult(
        CandidateConfig(
            "trend_following_v1",
            {"threshold": 0.31},
            exit_policy_id="max_mae_stop",
            exit_policy_params={"stop_return": 0.01},
        ),
        base_score=0.21,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
    )
    tighter_mae = CandidateResult(
        CandidateConfig(
            "trend_following_v1",
            {"threshold": 0.32},
            exit_policy_id="max_mae_stop",
            exit_policy_params={"stop_return": 0.02},
        ),
        base_score=0.22,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
    )

    regions = rank_by_stability([fixed, max_mae, tighter_mae])
    by_center = {region.center_candidate_id: set(region.member_candidate_ids) for region in regions}

    assert by_center[fixed.candidate_id] == {fixed.candidate_id}
    assert by_center[max_mae.candidate_id] == {max_mae.candidate_id}
    assert by_center[tighter_mae.candidate_id] == {tighter_mae.candidate_id}


def test_sparse_side_veto_stability_keeps_allowed_side_separate() -> None:
    long_a = CandidateResult(
        CandidateConfig(
            "sparse_event_filter_v1",
            {"allowed_sides": "long", "side_filter_stage": "post_selection", "threshold": 0.30},
        ),
        base_score=0.20,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
    )
    long_b = CandidateResult(
        CandidateConfig(
            "sparse_event_filter_v1",
            {"allowed_sides": "long", "side_filter_stage": "post_selection", "threshold": 0.31},
        ),
        base_score=0.21,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
    )
    short_control = CandidateResult(
        CandidateConfig(
            "sparse_event_filter_v1",
            {"allowed_sides": "short", "side_filter_stage": "post_selection", "threshold": 0.30},
        ),
        base_score=-0.10,
        split_consistency=0.8,
        side_balance=0.8,
        regime_coverage=0.8,
        cost_stress_survival=0.8,
    )

    regions = rank_by_stability([long_a, long_b, short_control])
    by_center = {region.center_candidate_id: set(region.member_candidate_ids) for region in regions}

    assert by_center[long_a.candidate_id] == {long_a.candidate_id, long_b.candidate_id}
    assert by_center[long_b.candidate_id] == {long_a.candidate_id, long_b.candidate_id}
    assert by_center[short_control.candidate_id] == {short_control.candidate_id}
