from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.research.command_registry import RESEARCH_COMMANDS
from tradingbotsuite.research_cycle.runner import _baseline_comparator_coverage, _candidate_space
from tradingbotsuite.research_cycle.spec import HistoricalResearchCycleSpec


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_historical_research_cycle_spec_contract_defaults(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "contract-cycle",
            "symbol": "btcusdt",
            "data": {"synthetic_fixture": True, "synthetic_row_count": 120},
        },
    )

    spec = HistoricalResearchCycleSpec.from_path(spec_path)

    assert spec.cycle_id == "contract-cycle"
    assert spec.symbol == "BTCUSDT"
    assert spec.holding_windows == ("1h", "4h", "12h", "24h", "72h", "7d")
    assert spec.data.synthetic_fixture is True
    assert spec.data.lower_timeframe_dataset_path is None
    assert spec.validation.min_splits == 6
    assert spec.validation.split_modes == ("purged_embargoed_walk_forward",)
    assert spec.validation.min_cost_stress_survival_rate == 1.0
    assert spec.backtest_backend == "reference"
    assert spec.to_payload()["backtest_backend"] == "reference"
    assert spec.to_payload()["validation"]["split_modes"] == ["purged_embargoed_walk_forward"]
    assert spec.to_payload()["validation"]["min_cost_stress_survival_rate"] == 1.0
    assert spec.exits.exit_policies[0]["exit_policy_id"] == "fixed_holding_window"
    assert spec.to_payload()["exits"]["exit_policies"][0]["exit_policy_id"] == "fixed_holding_window"


@pytest.mark.parametrize("backend", ["reference", "vector_fixed_holding", "auto"])
def test_historical_research_cycle_spec_accepts_backtest_backend(tmp_path: Path, backend: str) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": f"{backend}-cycle",
            "data": {"synthetic_fixture": True, "synthetic_row_count": 120},
            "backtest_backend": backend,
        },
    )

    spec = HistoricalResearchCycleSpec.from_path(spec_path)

    assert spec.backtest_backend == backend
    assert spec.to_payload()["backtest_backend"] == backend


def test_historical_research_cycle_rejects_unknown_backtest_backend(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "bad-backend-cycle",
            "data": {"synthetic_fixture": True, "synthetic_row_count": 120},
            "backtest_backend": "gpu_vector",
        },
    )

    with pytest.raises(ValueError, match="backtest_backend"):
        HistoricalResearchCycleSpec.from_path(spec_path)


def test_historical_research_cycle_spec_accepts_validation_split_modes(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "split-mode-cycle",
            "data": {"synthetic_fixture": True, "synthetic_row_count": 120},
            "validation": {
                "split_modes": [
                    "purged_embargoed_walk_forward",
                    "anchored_walk_forward",
                    "rolling_walk_forward",
                    "shifted_purged_walk_forward",
                    "month_holdout",
                    "stress_period_holdout",
                    "regime_holdout",
                ],
                "rolling_train_window_bars": 24,
                "shifted_anchor_offsets": [1, 3],
                "regime_column": "validation_regime",
                "stress_zscore_threshold": 1.5,
                "min_cost_stress_survival_rate": 0.75,
            },
        },
    )

    spec = HistoricalResearchCycleSpec.from_path(spec_path)
    payload = spec.to_payload()["validation"]

    assert spec.validation.split_modes == (
        "purged_embargoed_walk_forward",
        "anchored_walk_forward",
        "rolling_walk_forward",
        "shifted_purged_walk_forward",
        "month_holdout",
        "stress_period_holdout",
        "regime_holdout",
    )
    assert spec.validation.rolling_train_window_bars == 24
    assert spec.validation.shifted_anchor_offsets == (1, 3)
    assert spec.validation.min_cost_stress_survival_rate == 0.75
    assert payload["split_modes"] == list(spec.validation.split_modes)
    assert payload["regime_column"] == "validation_regime"
    assert payload["stress_zscore_threshold"] == 1.5
    assert payload["min_cost_stress_survival_rate"] == 0.75


def test_historical_research_cycle_rejects_unknown_validation_split_mode(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "bad-split-mode-cycle",
            "data": {"synthetic_fixture": True, "synthetic_row_count": 120},
            "validation": {"split_modes": ["live_forward_test"]},
        },
    )

    with pytest.raises(ValueError, match="unsupported validation split_modes"):
        HistoricalResearchCycleSpec.from_path(spec_path)


def test_historical_research_cycle_rejects_rolling_split_without_train_window(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "bad-rolling-split-cycle",
            "data": {"synthetic_fixture": True, "synthetic_row_count": 120},
            "validation": {"split_modes": ["rolling_walk_forward"]},
        },
    )

    with pytest.raises(ValueError, match="rolling_train_window_bars"):
        HistoricalResearchCycleSpec.from_path(spec_path)


def test_historical_research_cycle_rejects_invalid_cost_stress_survival_floor(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "bad-stress-floor-cycle",
            "data": {"synthetic_fixture": True, "synthetic_row_count": 120},
            "validation": {"min_cost_stress_survival_rate": 1.2},
        },
    )

    with pytest.raises(ValueError, match="min_cost_stress_survival_rate"):
        HistoricalResearchCycleSpec.from_path(spec_path)


def test_historical_research_cycle_spec_accepts_optimizer_search_spaces(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "search-space-cycle",
            "data": {"synthetic_fixture": True},
            "optimizer": {
                "method_sequence": ["grid", "stability_region_refine"],
                "max_candidates_per_strategy": 8,
                "search_spaces": [
                    {
                        "strategy_id": "trend_following_v1",
                        "feature_set_id": "features_price_trend_vol",
                        "holding_window": "4h",
                        "parameters": {
                            "slope_threshold": [0.08, 0.12],
                            "spacing_bars": [8, 12],
                        },
                    }
                ],
            },
        },
    )

    spec = HistoricalResearchCycleSpec.from_path(spec_path)
    payload = spec.to_payload()

    assert spec.optimizer.method_sequence == ("grid", "stability_region_refine")
    assert len(spec.optimizer.search_spaces) == 1
    assert payload["optimizer"]["search_spaces"][0]["parameters"]["slope_threshold"] == [0.08, 0.12]


def test_historical_research_cycle_spec_accepts_exit_policy_candidates(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "exit-policy-cycle",
            "data": {"synthetic_fixture": True},
            "exit_policies": [
                "fixed_holding_window",
                {
                    "exit_policy_id": "max_mae_stop",
                    "stop_return": 0.01,
                    "exit_policy_params": {"stop_return": 0.01},
                },
                {
                    "exit_policy_id": "funding_aware_exit_v1",
                    "exit_policy_params": {
                        "funding_threshold": 0.00005,
                        "pre_funding_window_h": 1.0,
                        "min_expected_cost_bps": 0.5,
                        "edge_buffer_bps": 2.0,
                    },
                },
                {
                    "exit_policy_id": "oi_contraction_exit_v1",
                    "exit_policy_params": {
                        "oi_delta_z_threshold": 1.0,
                        "min_oi_delta_abs": 0.0,
                        "max_unrealized_edge_bps": 5.0,
                    },
                },
            ],
        },
    )

    spec = HistoricalResearchCycleSpec.from_path(spec_path)
    payload = spec.to_payload()

    assert [policy["exit_policy_id"] for policy in spec.exits.exit_policies] == [
        "fixed_holding_window",
        "max_mae_stop",
        "funding_aware_exit_v1",
        "oi_contraction_exit_v1",
    ]
    assert payload["exits"]["exit_policies"][1]["exit_policy_params"] == {"stop_return": 0.01}
    assert payload["exits"]["exit_policies"][2]["exit_policy_params"]["pre_funding_window_h"] == 1.0
    assert payload["exits"]["exit_policies"][3]["exit_policy_params"]["max_unrealized_edge_bps"] == 5.0


def test_historical_research_cycle_spec_accepts_lower_timeframe_triple_barrier_exit(tmp_path: Path) -> None:
    lower_path = tmp_path / "lower_timeframe_bars.parquet"
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "triple-barrier-cycle",
            "data": {
                "synthetic_fixture": True,
                "lower_timeframe_dataset_path": str(lower_path),
            },
            "features": {"feature_sets": ["features_price_trend_vol"]},
            "holding_windows": ["4h"],
            "strategies": ["trend_following_v1"],
            "exit_policies": [
                {
                    "exit_policy_id": "triple_barrier_atr",
                    "exit_policy_params": {
                        "target_return": 0.015,
                        "stop_return": 0.01,
                    },
                }
            ],
        },
    )

    spec = HistoricalResearchCycleSpec.from_path(spec_path)
    candidates = _candidate_space(spec)
    payload = spec.to_payload()

    assert spec.data.lower_timeframe_dataset_path == lower_path
    policy = spec.exits.exit_policies[0]
    assert policy["exit_policy_id"] == "triple_barrier_atr"
    assert policy["target_return"] == 0.015
    assert policy["stop_return"] == 0.01
    assert policy["exit_policy_params"] == {"target_return": 0.015, "stop_return": 0.01}
    assert payload["data"]["lower_timeframe_dataset_path"] == str(lower_path)
    assert set(candidate["exit_policy_id"] for candidate in candidates) == {"triple_barrier_atr"}
    assert all(candidate["target_return"] == 0.015 for candidate in candidates)
    assert all(candidate["stop_return"] == 0.01 for candidate in candidates)


@pytest.mark.parametrize(
    ("exit_policy", "message"),
    [
        ({"exit_policy_id": "triple_barrier", "target_return": 0.01}, "triple_barrier.stop_return is required"),
        (
            {
                "exit_policy_id": "triple_barrier_atr",
                "target_return": 0.01,
                "stop_return": 0.0,
            },
            "triple_barrier_atr.stop_return must be positive",
        ),
    ],
)
def test_historical_research_cycle_rejects_invalid_triple_barrier_exit_policy(
    tmp_path: Path,
    exit_policy: dict[str, object],
    message: str,
) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "bad-triple-barrier-cycle",
            "data": {"synthetic_fixture": True},
            "exit_policies": [exit_policy],
        },
    )

    with pytest.raises(ValueError, match=message):
        HistoricalResearchCycleSpec.from_path(spec_path)


def test_historical_research_cycle_rejects_unknown_exit_policy(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "bad-exit-policy-cycle",
            "data": {"synthetic_fixture": True},
            "exit_policies": ["live_order_exit"],
        },
    )

    with pytest.raises(ValueError, match="unsupported exit_policy_id"):
        HistoricalResearchCycleSpec.from_path(spec_path)


def test_explicit_search_space_candidates_receive_baseline_comparators(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "search-space-cycle",
            "data": {"synthetic_fixture": True},
            "features": {"feature_sets": ["features_price_trend_vol"]},
            "holding_windows": ["4h"],
            "strategies": ["trend_following_v1"],
            "optimizer": {
                "method_sequence": ["grid", "stability_region_refine"],
                "max_candidates_per_strategy": 4,
                "search_spaces": [
                    {
                        "strategy_id": "trend_following_v1",
                        "feature_set_id": "features_price_trend_vol",
                        "holding_window": "4h",
                        "parameters": {
                            "slope_threshold": [0.08, 0.12],
                            "spacing_bars": [8, 12],
                        },
                    }
                ],
            },
        },
    )

    candidates = _candidate_space(HistoricalResearchCycleSpec.from_path(spec_path))

    assert {candidate["comparator_role"] for candidate in candidates} >= {"no_trade_baseline", "transparent_baseline"}
    assert any(candidate["candidate_source"] == "no_trade_comparator_injected" for candidate in candidates)
    assert any(candidate["candidate_source"] == "transparent_default_comparator_injected" for candidate in candidates)
    assert all(candidate["resolved_parameters"] == candidate["parameters"] for candidate in candidates)
    assert all(candidate["strategy_metadata_sha256"] for candidate in candidates)


def test_perp_context_v2_candidate_space_includes_transparent_perp_strategies_with_baseline_coverage(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "perp-context-v2-strategy-family-cycle",
            "data": {"synthetic_fixture": True},
            "features": {"feature_sets": ["features_perp_context_v2"]},
            "holding_windows": ["4h"],
            "strategies": [
                "baseline_no_trade",
                "perp_basis_convergence_v2",
                "funding_crowding_fade_v2",
                "oi_flow_breakout_v2",
                "funding_window_timing_v1",
            ],
            "optimizer": {
                "max_candidates_per_strategy": 1,
                "top_regions_to_refine": 1,
            },
        },
    )

    candidates = _candidate_space(HistoricalResearchCycleSpec.from_path(spec_path))
    coverage = _baseline_comparator_coverage(candidates)
    strategy_ids = {candidate["strategy_id"] for candidate in candidates}

    assert {
        "baseline_no_trade",
        "perp_basis_convergence_v2",
        "funding_crowding_fade_v2",
        "oi_flow_breakout_v2",
        "funding_window_timing_v1",
    } <= strategy_ids
    assert {record["coverage_status"] for record in coverage} == {"complete"}
    assert any(candidate["comparator_role"] == "no_trade_baseline" for candidate in candidates)
    oi_flow_candidates = [candidate for candidate in candidates if candidate["strategy_id"] == "oi_flow_breakout_v2"]
    assert oi_flow_candidates
    assert all(candidate["feature_set_id"] == "features_perp_context_v2" for candidate in oi_flow_candidates)
    assert all(candidate["holding_window"] == "4h" for candidate in oi_flow_candidates)
    funding_window_candidates = [candidate for candidate in candidates if candidate["strategy_id"] == "funding_window_timing_v1"]
    assert funding_window_candidates
    assert all(candidate["feature_set_id"] == "features_perp_context_v2" for candidate in funding_window_candidates)
    assert all(candidate["holding_window"] == "4h" for candidate in funding_window_candidates)
    assert all(candidate["resolved_parameters"] == candidate["parameters"] for candidate in candidates)
    assert all(candidate["strategy_metadata_sha256"] for candidate in candidates)


def test_advanced_only_explicit_search_space_receives_transparent_comparator(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "advanced-search-space-cycle",
            "data": {"synthetic_fixture": True},
            "features": {"feature_sets": ["features_full_context_no_wt"]},
            "holding_windows": ["4h"],
            "strategies": ["regime_adaptive_v1"],
            "optimizer": {
                "method_sequence": ["grid"],
                "search_spaces": [
                    {
                        "strategy_id": "regime_adaptive_v1",
                        "feature_set_id": "features_full_context_no_wt",
                        "holding_window": "4h",
                        "parameters": {"spacing_bars": [8]},
                    }
                ],
            },
        },
    )

    candidates = _candidate_space(HistoricalResearchCycleSpec.from_path(spec_path))

    roles = {candidate["comparator_role"] for candidate in candidates}
    assert {"no_trade_baseline", "transparent_baseline", "research_candidate"} <= roles
    transparent = [candidate for candidate in candidates if candidate["comparator_role"] == "transparent_baseline"]
    assert transparent
    assert all(candidate["candidate_source"] == "transparent_default_comparator_injected" for candidate in transparent)


def test_default_candidate_space_expands_strategy_metadata_parameter_space(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "metadata-default-cycle",
            "data": {"synthetic_fixture": True},
            "features": {"feature_sets": ["features_price_trend_vol"]},
            "holding_windows": ["4h"],
            "strategies": ["trend_following_v1"],
            "optimizer": {
                "max_candidates_per_strategy": 16,
                "top_regions_to_refine": 1,
            },
        },
    )

    candidates = _candidate_space(HistoricalResearchCycleSpec.from_path(spec_path))
    trend_candidates = [candidate for candidate in candidates if candidate["strategy_id"] == "trend_following_v1"]

    assert len(candidates) == 6
    assert len(trend_candidates) == 5
    assert {candidate["candidate_source"] for candidate in trend_candidates} == {"metadata_default_seed", "metadata_default_search"}
    assert any(candidate["is_default_parameter_candidate"] for candidate in trend_candidates)
    assert {candidate["comparator_role"] for candidate in candidates} >= {"no_trade_baseline", "transparent_baseline"}
    assert all(candidate["resolved_parameters"] == candidate["parameters"] for candidate in candidates)


def test_default_candidate_space_respects_metadata_sample_cap(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "metadata-default-cap-cycle",
            "data": {"synthetic_fixture": True},
            "features": {"feature_sets": ["features_price_trend_vol"]},
            "holding_windows": ["4h"],
            "strategies": ["trend_following_v1"],
            "optimizer": {
                "max_candidates_per_strategy": 2,
            },
        },
    )

    candidates = _candidate_space(HistoricalResearchCycleSpec.from_path(spec_path))
    trend_candidates = [candidate for candidate in candidates if candidate["strategy_id"] == "trend_following_v1"]

    assert len(trend_candidates) == 3
    assert sum(candidate["candidate_source"] == "metadata_default_search" for candidate in trend_candidates) == 2


def test_historical_research_cycle_rejects_unsupported_holding_window(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "bad-cycle",
            "holding_windows": ["15m"],
            "data": {"synthetic_fixture": True},
            "strategies": ["baseline_no_trade"],
        },
    )

    with pytest.raises(ValueError, match="unsupported holding windows"):
        HistoricalResearchCycleSpec.from_path(spec_path)


def test_explicit_search_space_rejects_out_of_domain_parameter_values(tmp_path: Path) -> None:
    spec_path = _write_json(
        tmp_path / "cycle.json",
        {
            "cycle_id": "bad-search-space-cycle",
            "data": {"synthetic_fixture": True},
            "features": {"feature_sets": ["features_price_trend_vol"]},
            "holding_windows": ["4h"],
            "strategies": ["trend_following_v1"],
            "optimizer": {
                "method_sequence": ["grid"],
                "search_spaces": [
                    {
                        "strategy_id": "trend_following_v1",
                        "feature_set_id": "features_price_trend_vol",
                        "holding_window": "4h",
                        "parameters": {"slope_threshold": [9.0]},
                    }
                ],
            },
        },
    )

    with pytest.raises(ValueError, match="out-of-domain parameter value"):
        _candidate_space(HistoricalResearchCycleSpec.from_path(spec_path))


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "cycle_id": "empty-holding-cycle",
                "holding_windows": [],
                "data": {"synthetic_fixture": True},
                "strategies": ["baseline_no_trade"],
            },
            "at least one holding window",
        ),
        (
            {
                "cycle_id": "empty-feature-cycle",
                "data": {"synthetic_fixture": True},
                "features": {"feature_sets": []},
                "strategies": ["baseline_no_trade"],
            },
            "at least one feature set",
        ),
    ],
)
def test_historical_research_cycle_rejects_empty_candidate_dimensions(
    tmp_path: Path,
    payload: dict[str, object],
    message: str,
) -> None:
    spec_path = _write_json(tmp_path / "cycle.json", payload)

    with pytest.raises(ValueError, match=message):
        HistoricalResearchCycleSpec.from_path(spec_path)


def test_historical_research_cycle_is_registered_as_research_command() -> None:
    assert "run-historical-research-cycle" in RESEARCH_COMMANDS
    assert "benchmark-historical-research-cycle" in RESEARCH_COMMANDS
