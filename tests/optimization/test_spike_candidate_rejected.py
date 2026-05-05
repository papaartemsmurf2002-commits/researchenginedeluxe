from __future__ import annotations

from tradingbotsuite.optimization import CandidateConfig, CandidateResult, rank_by_stability


def test_isolated_spike_candidate_is_rejected() -> None:
    spike = CandidateResult(
        CandidateConfig("trend_following_v1", {"threshold": 0.90}),
        base_score=1.0,
        split_consistency=0.2,
        side_balance=0.2,
        regime_coverage=0.2,
        cost_stress_survival=0.2,
    )
    plateau = [
        CandidateResult(CandidateConfig("trend_following_v1", {"threshold": value}), base_score=0.30, split_consistency=0.9, side_balance=0.9, regime_coverage=0.9, cost_stress_survival=0.9)
        for value in (0.30, 0.32, 0.34)
    ]

    regions = rank_by_stability([spike, *plateau])
    spike_region = next(region for region in regions if region.center_candidate_id == spike.candidate_id)

    assert spike_region.decision == "rejected_spike_or_unstable_region"
    assert spike_region.connected_region_size == 1
