from __future__ import annotations

from tradingbotsuite.optimization import CandidateConfig, CandidateResult, rank_by_stability


def test_plateau_candidate_ranks_above_higher_peak_spike() -> None:
    spike = CandidateResult(
        CandidateConfig("trend_following_v1", {"threshold": 0.90}),
        base_score=1.0,
        split_consistency=0.1,
        side_balance=0.1,
        regime_coverage=0.1,
        cost_stress_survival=0.1,
    )
    plateau = [
        CandidateResult(
            CandidateConfig("trend_following_v1", {"threshold": value}),
            base_score=0.35,
            split_consistency=1.0,
            side_balance=1.0,
            regime_coverage=1.0,
            cost_stress_survival=1.0,
        )
        for value in (0.30, 0.32, 0.34, 0.36)
    ]

    regions = rank_by_stability([spike, *plateau])

    assert regions[0].center_candidate_id in {result.candidate_id for result in plateau}
    assert regions[0].stability_score > next(region.stability_score for region in regions if region.center_candidate_id == spike.candidate_id)
