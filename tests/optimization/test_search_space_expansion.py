from __future__ import annotations

from tradingbotsuite.optimization import SearchSpace
from tradingbotsuite.strategies.parameters import search_parameter_space_for_holding_window


def test_search_space_expands_grid_and_lhs_deterministically() -> None:
    space = SearchSpace(
        strategy_id="trend_following_v1",
        parameters={"slope_threshold": (0.1, 0.2), "spacing_bars": (8, 12)},
        holding_window="24h",
    )

    grid = space.expand(method="grid", max_candidates=10)
    lhs = space.expand(method="latin_hypercube", max_candidates=3)

    assert grid == space.expand(method="grid", max_candidates=10)
    assert len(grid) == 4
    assert {tuple(sorted(candidate.parameters.items())) for candidate in grid} == {
        (("slope_threshold", 0.1), ("spacing_bars", 8)),
        (("slope_threshold", 0.2), ("spacing_bars", 8)),
        (("slope_threshold", 0.1), ("spacing_bars", 12)),
        (("slope_threshold", 0.2), ("spacing_bars", 12)),
    }
    assert lhs == space.expand(method="latin_hypercube", max_candidates=3)
    assert len(lhs) == 3


def test_search_space_reports_full_grid_size_independent_of_sample_cap() -> None:
    space = SearchSpace(
        strategy_id="trend_following_v1",
        parameters={"slope_threshold": (0.1, 0.2), "spacing_bars": (8, 12, 16)},
        holding_window="24h",
    )
    empty_space = SearchSpace(strategy_id="baseline_no_trade", parameters={})

    assert space.grid_size() == 6
    assert len(space.expand(method="grid", max_candidates=2)) == 2
    assert empty_space.grid_size() == 1


def test_search_space_local_neighbors_are_deterministic() -> None:
    space = SearchSpace(
        "trend_following_v1",
        {"threshold": (0.1, 0.2, 0.3, 0.4), "spacing": (4, 8, 12)},
    )
    center = space._candidate({"threshold": 0.3, "spacing": 8})

    neighbors = space.local_neighbors(center, radius_steps=1, max_candidates=9)

    assert [candidate.to_payload()["parameters"] for candidate in neighbors] == [
        {"spacing": 4, "threshold": 0.2},
        {"spacing": 4, "threshold": 0.3},
        {"spacing": 4, "threshold": 0.4},
        {"spacing": 8, "threshold": 0.2},
        {"spacing": 8, "threshold": 0.3},
        {"spacing": 8, "threshold": 0.4},
        {"spacing": 12, "threshold": 0.2},
        {"spacing": 12, "threshold": 0.3},
        {"spacing": 12, "threshold": 0.4},
    ]


def test_search_space_expansion_preserves_exit_policy_identity() -> None:
    space = SearchSpace.from_payload(
        {
            "strategy_id": "trend_following_v1",
            "feature_set_id": "features_price_trend_vol",
            "holding_window": "4h",
            "exit_policy_id": "max_mae_stop",
            "exit_policy_params": {"stop_return": 0.01},
            "parameters": {"slope_threshold": [0.08]},
        }
    )

    candidates = space.expand(method="grid", max_candidates=4)

    assert len(candidates) == 1
    assert candidates[0].exit_policy_id == "max_mae_stop"
    assert candidates[0].exit_policy_params == {"stop_return": 0.01}
    assert candidates[0].to_payload()["exit_policy_params"] == {"stop_return": 0.01}


def test_holding_window_search_space_includes_metadata_and_window_defaults() -> None:
    trend_4h = search_parameter_space_for_holding_window("trend_following_v1", "4h")

    assert trend_4h["funding_penalty_threshold"] == (0.00025,)
    assert trend_4h["max_choppiness"] == (52.0, 58.0, 64.0)
    assert trend_4h["slope_threshold"] == (0.08, 0.12, 0.16, 0.10)
    assert trend_4h["spacing_bars"] == (8, 12, 16)

    range_12h = search_parameter_space_for_holding_window("range_reversion_v1", "12h")

    assert range_12h["spacing_bars"] == (6, 8, 12, 10)
