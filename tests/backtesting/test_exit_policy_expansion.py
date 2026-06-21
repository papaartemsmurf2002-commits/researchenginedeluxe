from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from tradingbotsuite.backtesting.exits import fixed_holding_window_exit, primary_bar_research_exit, triple_barrier_exit_from_lower_timeframe


START_MS = 1_712_649_600_000


def _path() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bar_time_ms": [START_MS + index * 900_000 for index in range(6)],
            "open": [100.0, 101.0, 102.0, 103.0, 102.0, 101.0],
            "high": [101.0, 103.0, 105.0, 104.0, 103.0, 102.0],
            "low": [99.0, 100.0, 101.0, 101.0, 99.0, 98.0],
            "close": [100.0, 102.0, 104.0, 102.0, 99.0, 98.0],
            "top_regime_label": ["trend", "trend", "range", "range", "range", "range"],
            "funding_rate": [0.0, 0.00001, 0.00009, 0.00009, 0.00009, 0.00009],
            "directional_slope_atr": [0.4, 0.3, 0.05, -0.1, -0.2, -0.3],
            "spread_bps": [2.0, 5.0, 30.0, 30.0, 30.0, 30.0],
            "primary_signed_imbalance_ratio": [0.2, 0.1, -0.2, -0.3, -0.3, -0.3],
            "top_of_book_imbalance": [0.1, 0.05, -0.15, -0.2, -0.2, -0.2],
            "realized_volatility": [0.01] * 6,
            "perp_mark_index_basis": [-0.0008, -0.0006, -0.00005, 0.0, 0.0001, 0.0001],
            "perp_premium": [-0.0009, -0.0007, -0.00005, 0.0, 0.0001, 0.0001],
            "cal_time_to_next_funding_h": [4.0, 0.75, 0.5, 0.25, 4.0, 3.75],
            "oi_notional": [1_000_000.0, 1_010_000.0, 985_000.0, 970_000.0, 960_000.0, 955_000.0],
            "oi_delta_1h": [0.0, 10_000.0, -25_000.0, -15_000.0, -10_000.0, -5_000.0],
            "oi_delta_z_7d": [0.0, 0.5, -1.25, -1.1, -0.8, -0.4],
            "quality_has_oi_gap": [0.0] * 6,
            "quality_has_premium_gap": [0.0] * 6,
            "quality_provider_backed_all_required": [1.0] * 6,
            "quality_latest_window_context_only": [0.0] * 6,
            "regime_detector_type": ["gmm"] * 6,
            "regime_detector_train_start_ms": [START_MS - 30 * 24 * 60 * 60 * 1000] * 6,
            "regime_detector_train_end_ms": [START_MS - 1] * 6,
            "regime_detector_inference_start_ms": [START_MS] * 6,
            "regime_detector_inference_end_ms": [START_MS + 5 * 900_000] * 6,
            "regime_detector_feature_version": ["features_perp_context_v2"] * 6,
            "regime_detector_params_hash": ["sha256:gmm-params"] * 6,
            "regime_detector_artifact_sha256": ["sha256:gmm-artifact"] * 6,
            "max_regime_probability": [0.82, 0.81, 0.78, 0.76, 0.74, 0.72],
            "posterior_entropy": [0.20, 0.22, 0.31, 0.33, 0.35, 0.37],
            "recent_regime_flip": [False, False, True, False, False, False],
            "regime_no_trade": [False] * 6,
            "hmm_fit_end_row": [5] * 6,
            "source_row_index": [10, 11, 12, 13, 14, 15],
            "p_up_barrier": [0.68, 0.66, 0.54, 0.52, 0.50, 0.48],
            "p_down_barrier": [0.32, 0.34, 0.46, 0.48, 0.50, 0.52],
            "expected_net_return_after_costs": [0.006, 0.004, 0.0001, 0.0001, 0.0, -0.0002],
            "neighbor_agreement": [0.68, 0.66, 0.54, 0.52, 0.50, 0.52],
            "neighbor_distance_quality": [0.35, 0.34, 0.33, 0.32, 0.31, 0.30],
            "neighbor_count": [12] * 6,
            "neighbor_min_source_index": [0] * 6,
            "neighbor_max_source_index": [4] * 6,
            "knn_vote_margin": [0.36, 0.32, 0.08, 0.04, 0.0, 0.04],
            "accepted_by_knn": [True] * 6,
            "knn_skip_reason": [""] * 6,
        }
    )


def _run(
    policy: str,
    *,
    side: str = "long",
    target_return: float | None = None,
    stop_return: float | None = None,
    path: pd.DataFrame | None = None,
    policy_params: dict[str, Any] | None = None,
):
    frame = _path() if path is None else path
    return primary_bar_research_exit(
        entry_time_ms=int(frame.iloc[0]["bar_time_ms"]),
        time_exit_ms=int(frame.iloc[-1]["bar_time_ms"]),
        time_exit_price=float(frame.iloc[-1]["close"]),
        entry_price=100.0,
        side=side,
        primary_path=frame,
        costs_applied=True,
        exit_policy_id=policy,
        target_return=target_return,
        stop_return=stop_return,
        policy_params=policy_params,
    )


def test_volatility_scaled_barrier_long_uses_primary_close_stop() -> None:
    result = _run("volatility_scaled_barrier", target_return=0.10, stop_return=0.01)

    assert result.exit_reason == "volatility_scaled_barrier_stop"
    assert result.barrier_hit_type == "stop"
    assert result.exit_time_ms == int(_path().iloc[4]["bar_time_ms"])
    assert result.approximate is True


def test_volatility_scaled_barrier_short_uses_inverse_thresholds() -> None:
    frame = _path().copy()
    frame["close"] = [100.0, 99.0, 98.0, 101.0, 102.0, 103.0]

    result = _run("volatility_scaled_barrier", side="short", target_return=0.015, stop_return=0.02, path=frame)

    assert result.exit_reason == "volatility_scaled_barrier_target"
    assert result.barrier_hit_type == "target"
    assert result.exit_time_ms == int(frame.iloc[2]["bar_time_ms"])


@pytest.mark.parametrize(
    ("policy", "kwargs", "reason", "barrier", "approximate"),
    [
        ("regime_flip_exit", {}, "regime_flip_exit", "regime_flip", False),
        ("funding_adverse_exit", {"target_return": 0.00005}, "funding_adverse_exit", "funding_adverse", False),
        (
            "funding_aware_exit_v1",
            {"policy_params": {"funding_threshold": 0.00005, "edge_buffer_bps": 500.0}},
            "funding_aware_exit_v1",
            "funding_aware",
            False,
        ),
        (
            "oi_contraction_exit_v1",
            {"policy_params": {"max_unrealized_edge_bps": 500.0}},
            "oi_contraction_exit_v1",
            "oi_contraction",
            False,
        ),
        ("basis_normalization_exit_v1", {}, "basis_normalization_exit_v1", "basis_normalization", False),
        ("premium_normalization_exit_v1", {}, "premium_normalization_exit_v1", "premium_normalization", False),
        ("gmm_transition_exit_v1", {}, "gmm_transition_exit_v1", "gmm_regime_transition", False),
        (
            "knn_remaining_edge_exit_v1",
            {"policy_params": {"min_remaining_edge_bps": 3.0}},
            "knn_remaining_edge_exit_v1",
            "knn_remaining_edge",
            False,
        ),
        (
            "knn_dynamic_barriers_v1",
            {"policy_params": {"target_return": 0.03, "stop_return": 0.02}},
            "knn_dynamic_barriers_v1_target",
            "target",
            True,
        ),
        ("alpha_decay_exit", {"target_return": 0.1}, "alpha_decay_exit", "alpha_decay", False),
        ("adverse_selection_exit", {"target_return": 20.0, "stop_return": 0.1}, "adverse_selection_exit", "adverse_selection", False),
        ("trailing_atr_after_profit", {"target_return": 0.02, "stop_return": 0.015}, "trailing_atr_after_profit", "trailing_stop", True),
        (
            "simple_runner_v1",
            {"policy_params": {"activation_pct": 0.02, "runner_gap_pct": 0.015}},
            "simple_runner_v1_trailing_gap",
            "runner_gap",
            True,
        ),
        ("max_mae_stop", {"stop_return": 0.01}, "max_mae_stop", "stop", True),
    ],
)
def test_primary_bar_research_exit_policies_are_deterministic(
    policy: str,
    kwargs: dict[str, Any],
    reason: str,
    barrier: str,
    approximate: bool,
) -> None:
    result = _run(policy, **kwargs)

    assert result.exit_policy_id == policy
    assert result.exit_reason == reason
    assert result.barrier_hit_type == barrier
    assert result.costs_applied is True
    assert result.time_in_trade_ms > 0
    assert result.max_adverse_excursion >= 0.0
    assert result.max_favorable_excursion >= 0.0
    assert result.approximate is approximate


@pytest.mark.parametrize(
    ("policy", "drop_columns", "kwargs", "message"),
    [
        ("regime_flip_exit", ["top_regime_label"], {}, "regime_flip_exit requires"),
        ("funding_adverse_exit", ["funding_rate"], {"target_return": 0.00005}, "funding_adverse_exit requires columns"),
        ("funding_aware_exit_v1", ["funding_rate"], {"target_return": 0.00005}, "funding_aware_exit_v1 requires columns"),
        ("funding_aware_exit_v1", ["cal_time_to_next_funding_h"], {"target_return": 0.00005}, "funding_aware_exit_v1 requires"),
        ("oi_contraction_exit_v1", ["oi_delta_1h"], {}, "oi_contraction_exit_v1 requires columns"),
        ("oi_contraction_exit_v1", ["quality_has_oi_gap"], {}, "oi_contraction_exit_v1 requires columns"),
        ("basis_normalization_exit_v1", ["perp_mark_index_basis"], {}, "basis_normalization_exit_v1 requires columns"),
        ("premium_normalization_exit_v1", ["perp_premium"], {}, "premium_normalization_exit_v1 requires columns"),
        ("gmm_transition_exit_v1", ["top_regime_label"], {}, "gmm_transition_exit_v1 requires"),
        ("gmm_transition_exit_v1", ["hmm_fit_end_row"], {}, "gmm_transition_exit_v1 requires columns"),
        ("knn_remaining_edge_exit_v1", ["p_up_barrier"], {}, "knn_remaining_edge_exit_v1 requires columns"),
        ("knn_dynamic_barriers_v1", ["neighbor_count"], {}, "knn_dynamic_barriers_v1 requires columns"),
        ("alpha_decay_exit", ["directional_slope_atr"], {"target_return": 0.1}, "alpha_decay_exit requires columns"),
        ("adverse_selection_exit", ["primary_signed_imbalance_ratio", "top_of_book_imbalance"], {"target_return": 20.0, "stop_return": 0.1}, "adverse_selection_exit requires"),
        ("trailing_atr_after_profit", ["realized_volatility"], {"target_return": 0.02}, "trailing_atr_after_profit requires"),
    ],
)
def test_context_dependent_exit_policies_reject_missing_columns(
    policy: str,
    drop_columns: list[str],
    kwargs: dict[str, Any],
    message: str,
) -> None:
    frame = _path().drop(columns=drop_columns)

    with pytest.raises(ValueError, match=message):
        _run(policy, path=frame, **kwargs)


def test_funding_aware_exit_waits_when_edge_exceeds_expected_funding_cost() -> None:
    frame = _path().copy()
    frame["close"] = [100.0, 101.0, 103.0, 104.0, 105.0, 106.0]

    result = _run(
        "funding_aware_exit_v1",
        target_return=0.00005,
        stop_return=2.0,
        path=frame,
    )

    assert result.barrier_hit_type == "time"
    assert result.exit_reason == "holding_window"


def test_funding_aware_exit_defaults_ignore_generic_target_stop_fallbacks() -> None:
    frame = _path().copy()
    frame["close"] = [100.0] * len(frame)

    result = _run(
        "funding_aware_exit_v1",
        target_return=0.25,
        stop_return=500.0,
        path=frame,
    )

    assert result.exit_reason == "funding_aware_exit_v1"
    assert result.barrier_hit_type == "funding_aware"
    assert result.exit_time_ms == int(frame.iloc[2]["bar_time_ms"])


def test_funding_aware_exit_supports_short_adverse_funding() -> None:
    frame = _path().copy()
    frame["funding_rate"] = [0.0, -0.00009, -0.00009, -0.00009, -0.00009, -0.00009]
    frame["close"] = [100.0, 100.0, 100.1, 100.2, 100.3, 100.4]

    result = _run("funding_aware_exit_v1", side="short", path=frame)

    assert result.exit_reason == "funding_aware_exit_v1"
    assert result.barrier_hit_type == "funding_aware"
    assert result.exit_time_ms == int(frame.iloc[1]["bar_time_ms"])


def test_simple_runner_v1_falls_back_to_time_exit_before_activation() -> None:
    frame = _path().copy()
    frame["close"] = [100.0, 100.5, 100.8, 100.7, 100.6, 100.4]

    result = _run(
        "simple_runner_v1",
        path=frame,
        policy_params={"activation_pct": 0.02, "runner_gap_pct": 0.005},
    )

    assert result.exit_reason == "holding_window"
    assert result.barrier_hit_type == "time"
    assert result.exit_time_ms == int(frame.iloc[-1]["bar_time_ms"])


def test_simple_runner_v1_supports_short_runner_gap() -> None:
    frame = _path().copy()
    frame["close"] = [100.0, 98.0, 96.0, 97.0, 98.0, 99.0]

    result = _run(
        "simple_runner_v1",
        side="short",
        path=frame,
        policy_params={"activation_pct": 0.02, "runner_gap_pct": 0.005},
    )

    assert result.exit_reason == "simple_runner_v1_trailing_gap"
    assert result.barrier_hit_type == "runner_gap"
    assert result.exit_time_ms == int(frame.iloc[3]["bar_time_ms"])


def test_simple_runner_v1_rejects_non_positive_params() -> None:
    with pytest.raises(ValueError, match="exit threshold must be positive"):
        _run(
            "simple_runner_v1",
            policy_params={"activation_pct": 0.0, "runner_gap_pct": 0.005},
        )


def test_funding_aware_exit_accepts_registered_perp_funding_column() -> None:
    frame = _path().drop(columns=["funding_rate"]).copy()
    frame["perp_last_funding_rate"] = [0.0, 0.00009, 0.00009, 0.00009, 0.00009, 0.00009]

    result = _run("funding_aware_exit_v1", policy_params={"edge_buffer_bps": 500.0}, path=frame)

    assert result.exit_reason == "funding_aware_exit_v1"
    assert result.barrier_hit_type == "funding_aware"


def test_oi_contraction_exit_waits_when_unrealized_edge_is_large() -> None:
    frame = _path().copy()
    frame["close"] = [100.0, 101.0, 104.0, 105.0, 106.0, 107.0]

    result = _run("oi_contraction_exit_v1", path=frame)

    assert result.barrier_hit_type == "time"
    assert result.exit_reason == "holding_window"


def test_oi_contraction_exit_skips_rows_with_oi_quality_gap() -> None:
    frame = _path().copy()
    frame["quality_has_oi_gap"] = [0.0, 0.0, 1.0, 1.0, 1.0, 1.0]

    result = _run("oi_contraction_exit_v1", path=frame)

    assert result.barrier_hit_type == "time"
    assert result.exit_reason == "holding_window"


def test_oi_contraction_exit_skips_non_finite_oi_context() -> None:
    frame = _path().copy()
    frame["oi_notional"] = [1_000_000.0, 1_010_000.0, float("inf"), float("inf"), float("inf"), float("inf")]
    frame["oi_delta_1h"] = [0.0, 10_000.0, float("-inf"), float("-inf"), float("-inf"), float("-inf")]
    frame["oi_delta_z_7d"] = [0.0, 0.5, float("-inf"), float("-inf"), float("-inf"), float("-inf")]

    result = _run("oi_contraction_exit_v1", path=frame)

    assert result.barrier_hit_type == "time"
    assert result.exit_reason == "holding_window"


def test_oi_contraction_exit_supports_short_side_momentum_decay() -> None:
    frame = _path().copy()
    frame["close"] = [100.0, 100.0, 99.98, 99.96, 99.94, 99.92]

    result = _run("oi_contraction_exit_v1", side="short", path=frame)

    assert result.exit_reason == "oi_contraction_exit_v1"
    assert result.barrier_hit_type == "oi_contraction"
    assert result.exit_time_ms == int(frame.iloc[2]["bar_time_ms"])


def test_basis_and_premium_normalization_skip_rows_with_context_quality_gap() -> None:
    frame = _path().copy()
    frame.loc[1:, "quality_has_premium_gap"] = 1.0

    basis = _run("basis_normalization_exit_v1", path=frame)
    premium = _run("premium_normalization_exit_v1", path=frame)

    assert basis.barrier_hit_type == "time"
    assert basis.exit_reason == "holding_window"
    assert premium.barrier_hit_type == "time"
    assert premium.exit_reason == "holding_window"


def test_basis_and_premium_normalization_skip_latest_window_context() -> None:
    frame = _path().copy()
    frame.loc[1:, "quality_latest_window_context_only"] = 1.0

    basis = _run("basis_normalization_exit_v1", path=frame)
    premium = _run("premium_normalization_exit_v1", path=frame)

    assert basis.barrier_hit_type == "time"
    assert basis.exit_reason == "holding_window"
    assert premium.barrier_hit_type == "time"
    assert premium.exit_reason == "holding_window"


def test_gmm_transition_exit_rejects_non_gmm_detector_context() -> None:
    frame = _path().copy()
    frame["regime_detector_type"] = "none"

    with pytest.raises(ValueError, match="gmm_transition_exit_v1 requires gmm regime_detector_type"):
        _run("gmm_transition_exit_v1", path=frame)


@pytest.mark.parametrize(
    "missing_column",
    [
        "regime_detector_train_start_ms",
        "regime_detector_train_end_ms",
        "regime_detector_inference_start_ms",
        "regime_detector_inference_end_ms",
        "regime_detector_feature_version",
        "regime_detector_params_hash",
        "regime_detector_artifact_sha256",
    ],
)
def test_gmm_transition_exit_rejects_missing_detector_metadata(missing_column: str) -> None:
    frame = _path().drop(columns=[missing_column])

    with pytest.raises(ValueError, match="GMM detector metadata"):
        _run("gmm_transition_exit_v1", path=frame)


def test_knn_remaining_edge_exit_skips_unsafe_neighbor_context() -> None:
    frame = _path().copy()
    frame["neighbor_max_source_index"] = 8

    result = _run("knn_remaining_edge_exit_v1", path=frame, policy_params={"min_remaining_edge_bps": 3.0})

    assert result.barrier_hit_type == "time"
    assert result.exit_reason == "holding_window"


def test_knn_dynamic_barriers_supports_short_primary_close_stop() -> None:
    frame = _path().copy()
    frame["close"] = [100.0, 101.0, 103.0, 104.0, 104.0, 104.0]
    frame["p_up_barrier"] = [0.32, 0.34, 0.36, 0.38, 0.40, 0.42]
    frame["p_down_barrier"] = [0.68, 0.66, 0.64, 0.62, 0.60, 0.58]

    result = _run(
        "knn_dynamic_barriers_v1",
        side="short",
        path=frame,
        policy_params={"target_return": 0.03, "stop_return": 0.02},
    )

    assert result.exit_reason == "knn_dynamic_barriers_v1_stop"
    assert result.barrier_hit_type == "stop"
    assert result.approximate is True


def test_fixed_holding_and_lower_timeframe_triple_barrier_outputs_are_preserved() -> None:
    fixed = fixed_holding_window_exit(
        entry_time_ms=START_MS,
        exit_time_ms=START_MS + 3_600_000,
        exit_price=104.0,
        side="long",
        path_high=105.0,
        path_low=99.0,
        entry_price=100.0,
        costs_applied=True,
    )
    lower = pd.DataFrame(
        {
            "bar_time_ms": [START_MS + 60_000],
            "high": [103.0],
            "low": [98.5],
            "close": [100.0],
        }
    )
    triple = triple_barrier_exit_from_lower_timeframe(
        entry_time_ms=START_MS,
        entry_price=100.0,
        side="long",
        time_exit_ms=START_MS + 3_600_000,
        time_exit_price=104.0,
        target_return=0.02,
        stop_return=0.01,
        lower_timeframe_market_data=lower,
        costs_applied=True,
        exit_policy_id="triple_barrier_atr",
    )

    assert fixed.exit_policy_id == "fixed_holding_window"
    assert fixed.barrier_hit_type == "time"
    assert triple.exit_policy_id == "triple_barrier_atr"
    assert triple.barrier_hit_type == "ambiguous_stop_conservative"
    assert triple.approximate is True
