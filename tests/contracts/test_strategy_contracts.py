from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.data.historical_fixture_pack import assert_valid_historical_fixture_pack_manifest
from tradingbotsuite.features.builders import materialize_fixture_family_context, materialize_registered_feature_set
from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset
from tradingbotsuite.strategies.funding_crowding_fade import REQUIRED_FUNDING_CROWDING_FADE_COLUMNS
from tradingbotsuite.strategies.funding_window_timing import REQUIRED_FUNDING_WINDOW_TIMING_COLUMNS
from tradingbotsuite.strategies.hmm_knn_local_analog_filter import REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS
from tradingbotsuite.strategies.hmm_routed_alpha_sleeves import REQUIRED_HMM_ROUTED_ALPHA_COLUMNS
from tradingbotsuite.strategies.liquidation_absorption_classifier import REQUIRED_LIQUIDATION_ABSORPTION_COLUMNS
from tradingbotsuite.strategies.oi_flow_breakout import REQUIRED_OI_FLOW_BREAKOUT_COLUMNS
from tradingbotsuite.strategies.perp_basis_convergence import REQUIRED_PERP_CONTEXT_V2_COLUMNS
from tradingbotsuite.strategies import (
    defaults_for_holding_window,
    get_strategy_plugin,
    load_strategy_config,
    metadata_for_strategy,
    required_signal_columns,
    strategy_registry,
    validate_signal_frame,
)


REQUIRED_STAGE6_STRATEGIES = {
    "trend_following_v1",
    "volatility_breakout_v1",
    "range_reversion_v1",
    "funding_basis_v1",
    "perp_basis_convergence_v2",
    "funding_crowding_fade_v2",
    "funding_window_timing_v1",
    "oi_flow_breakout_v2",
    "hmm_routed_alpha_sleeves_v2",
    "hmm_knn_local_analog_filter_v2",
    "liquidation_absorption_classifier_v1",
    "regime_adaptive_v1",
    "lc_reference_v1",
    "hmm_knn_diagnostic_v1",
    "baseline_no_trade",
}


def test_strategy_registry_contains_stage_six_plugins() -> None:
    registry = strategy_registry()

    assert REQUIRED_STAGE6_STRATEGIES <= set(registry)
    assert "baseline_trend" in registry


def test_strategy_configs_load_and_match_registry() -> None:
    for path in Path("configs/strategies").glob("*.json"):
        config = load_strategy_config(path)
        plugin = get_strategy_plugin(config.strategy_id, config={**config.parameters, "feature_set_id": config.feature_set_id, "holding_period": config.holding_period})

        assert plugin.strategy_id in {config.strategy_id, "trend_following_v1"}
        assert config.holding_period in plugin.allowed_holding_periods
        assert config.feature_set_id in plugin.required_feature_sets


def test_strategy_config_loader_rejects_unknown_parameters(tmp_path: Path) -> None:
    path = tmp_path / "bad_strategy.json"
    path.write_text(
        """
{
  "strategy_id": "trend_following_v1",
  "strategy_version": "v1",
  "enabled": true,
  "feature_set_id": "features_price_trend_vol",
  "holding_period": "24h",
  "parameters": {"unknown_threshold": 1.0}
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown_strategy_parameters:unknown_threshold"):
        load_strategy_config(path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "strategy_id": "unknown_strategy",
                "strategy_version": "v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_period": "24h",
                "parameters": {},
            },
            "unknown_strategy_id:unknown_strategy",
        ),
        (
            {
                "strategy_id": "range_reversion_v1",
                "strategy_version": "v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_period": "72h",
                "parameters": {},
            },
            "invalid_holding_period:range_reversion_v1:72h",
        ),
        (
            {
                "strategy_id": "range_reversion_v1",
                "strategy_version": "v1",
                "feature_set_id": "features_perp_context_only",
                "holding_period": "4h",
                "parameters": {},
            },
            "invalid_feature_set:range_reversion_v1:features_perp_context_only",
        ),
        (
            {
                "strategy_id": "perp_basis_convergence_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_perp_context_v2",
                "holding_period": "1h",
                "parameters": {},
            },
            "invalid_holding_period:perp_basis_convergence_v2:1h",
        ),
        (
            {
                "strategy_id": "perp_basis_convergence_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_full_context_no_wt",
                "holding_period": "24h",
                "parameters": {},
            },
            "invalid_feature_set:perp_basis_convergence_v2:features_full_context_no_wt",
        ),
        (
            {
                "strategy_id": "funding_crowding_fade_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_perp_context_v2",
                "holding_period": "1h",
                "parameters": {},
            },
            "invalid_holding_period:funding_crowding_fade_v2:1h",
        ),
        (
            {
                "strategy_id": "funding_crowding_fade_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_full_context_no_wt",
                "holding_period": "24h",
                "parameters": {},
            },
            "invalid_feature_set:funding_crowding_fade_v2:features_full_context_no_wt",
        ),
        (
            {
                "strategy_id": "oi_flow_breakout_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_perp_context_v2",
                "holding_period": "1h",
                "parameters": {},
            },
            "invalid_holding_period:oi_flow_breakout_v2:1h",
        ),
        (
            {
                "strategy_id": "oi_flow_breakout_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_full_context_no_wt",
                "holding_period": "24h",
                "parameters": {},
            },
            "invalid_feature_set:oi_flow_breakout_v2:features_full_context_no_wt",
        ),
        (
            {
                "strategy_id": "funding_window_timing_v1",
                "strategy_version": "v1",
                "feature_set_id": "features_perp_context_v2",
                "holding_period": "1h",
                "parameters": {},
            },
            "invalid_holding_period:funding_window_timing_v1:1h",
        ),
        (
            {
                "strategy_id": "funding_window_timing_v1",
                "strategy_version": "v1",
                "feature_set_id": "features_full_context_no_wt",
                "holding_period": "24h",
                "parameters": {},
            },
            "invalid_feature_set:funding_window_timing_v1:features_full_context_no_wt",
        ),
        (
            {
                "strategy_id": "hmm_routed_alpha_sleeves_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_perp_context_v2",
                "holding_period": "1h",
                "parameters": {},
            },
            "invalid_holding_period:hmm_routed_alpha_sleeves_v2:1h",
        ),
        (
            {
                "strategy_id": "hmm_routed_alpha_sleeves_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_full_context_no_wt",
                "holding_period": "24h",
                "parameters": {},
            },
            "invalid_feature_set:hmm_routed_alpha_sleeves_v2:features_full_context_no_wt",
        ),
        (
            {
                "strategy_id": "hmm_knn_local_analog_filter_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_perp_context_v2",
                "holding_period": "1h",
                "parameters": {},
            },
            "invalid_holding_period:hmm_knn_local_analog_filter_v2:1h",
        ),
        (
            {
                "strategy_id": "hmm_knn_local_analog_filter_v2",
                "strategy_version": "v1",
                "feature_set_id": "features_full_context_no_wt",
                "holding_period": "24h",
                "parameters": {},
            },
            "invalid_feature_set:hmm_knn_local_analog_filter_v2:features_full_context_no_wt",
        ),
        (
            {
                "strategy_id": "liquidation_absorption_classifier_v1",
                "strategy_version": "v1",
                "feature_set_id": "features_liquidation_context_v1",
                "holding_period": "72h",
                "parameters": {},
            },
            "invalid_holding_period:liquidation_absorption_classifier_v1:72h",
        ),
        (
            {
                "strategy_id": "liquidation_absorption_classifier_v1",
                "strategy_version": "v1",
                "feature_set_id": "features_perp_context_v2",
                "holding_period": "4h",
                "parameters": {},
            },
            "invalid_feature_set:liquidation_absorption_classifier_v1:features_perp_context_v2",
        ),
    ],
)
def test_strategy_config_loader_rejects_invalid_strategy_feature_or_window(
    tmp_path: Path,
    payload: dict[str, object],
    message: str,
) -> None:
    path = tmp_path / "bad_strategy.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_strategy_config(path)


def test_strategy_parameter_metadata_covers_stage_six_plugins() -> None:
    for strategy_id in REQUIRED_STAGE6_STRATEGIES - {"baseline_no_trade"}:
        plugin = get_strategy_plugin(strategy_id)
        metadata = metadata_for_strategy(strategy_id)

        assert metadata.parameter_space
        assert metadata.failure_modes
        for holding_window in plugin.allowed_holding_periods:
            defaults = defaults_for_holding_window(strategy_id, holding_window)
            assert isinstance(defaults, dict)
            assert "spacing_bars" in defaults
        assert 0.0 <= metadata.signal_density.min_signal_rate <= metadata.signal_density.max_signal_rate <= 1.0


def test_perp_basis_convergence_metadata_covers_required_contract() -> None:
    plugin = get_strategy_plugin("perp_basis_convergence_v2")
    metadata = metadata_for_strategy("perp_basis_convergence_v2")

    assert plugin.allowed_holding_periods == ("4h", "12h", "24h", "72h")
    assert plugin.required_feature_sets == ("features_perp_context_v2",)
    assert set(metadata.default_parameters) == {
        "basis_vol_threshold",
        "premium_z_threshold",
        "min_edge_bps",
        "funding_policy",
        "spacing_bars",
    }
    assert set(metadata.parameter_space) == set(metadata.default_parameters)
    assert metadata.default_parameters["funding_policy"] == "require_aligned_or_neutral"


def test_funding_crowding_fade_metadata_covers_required_contract() -> None:
    plugin = get_strategy_plugin("funding_crowding_fade_v2")
    metadata = metadata_for_strategy("funding_crowding_fade_v2")

    assert plugin.allowed_holding_periods == ("4h", "12h", "24h", "72h")
    assert plugin.required_feature_sets == ("features_perp_context_v2",)
    assert set(metadata.default_parameters) == {
        "funding_z_threshold",
        "funding_rate_abs_bps_threshold",
        "premium_confirmation_bps",
        "min_edge_bps",
        "oi_confirmation_z_min",
        "funding_momentum_policy",
        "spacing_bars",
    }
    assert set(metadata.parameter_space) == set(metadata.default_parameters)
    assert metadata.default_parameters["funding_momentum_policy"] == "against_fade_filter"


def test_oi_flow_breakout_metadata_covers_required_contract() -> None:
    plugin = get_strategy_plugin("oi_flow_breakout_v2")
    metadata = metadata_for_strategy("oi_flow_breakout_v2")

    assert plugin.allowed_holding_periods == ("4h", "12h", "24h", "72h")
    assert plugin.required_feature_sets == ("features_perp_context_v2",)
    assert set(metadata.default_parameters) == {
        "oi_delta_z_threshold",
        "oi_delta_min_notional",
        "premium_confirmation_bps",
        "premium_slope_min_bps",
        "flow_z_threshold",
        "flow_confirmation_policy",
        "spacing_bars",
    }
    assert set(metadata.parameter_space) == set(metadata.default_parameters)
    assert metadata.default_parameters["flow_confirmation_policy"] == "optional_when_missing"


def test_funding_window_timing_metadata_covers_required_contract() -> None:
    plugin = get_strategy_plugin("funding_window_timing_v1")
    metadata = metadata_for_strategy("funding_window_timing_v1")

    assert plugin.allowed_holding_periods == ("4h", "12h", "24h", "72h")
    assert plugin.required_feature_sets == ("features_perp_context_v2",)
    assert set(metadata.default_parameters) == {
        "funding_z_threshold",
        "funding_rate_abs_bps_threshold",
        "premium_confirmation_bps",
        "entry_window_h",
        "window_mode",
        "funding_momentum_policy",
        "oi_confirmation_z_min",
        "spacing_bars",
    }
    assert set(metadata.parameter_space) == set(metadata.default_parameters)
    assert metadata.default_parameters["window_mode"] == "pre_funding"
    assert metadata.default_parameters["funding_momentum_policy"] == "avoid_acceleration"


def test_hmm_routed_alpha_sleeves_metadata_covers_required_contract() -> None:
    plugin = get_strategy_plugin("hmm_routed_alpha_sleeves_v2")
    metadata = metadata_for_strategy("hmm_routed_alpha_sleeves_v2")

    assert plugin.allowed_holding_periods == ("4h", "12h", "24h", "72h")
    assert plugin.required_feature_sets == ("features_perp_context_v2",)
    assert set(metadata.default_parameters) == {
        "posterior_threshold",
        "entropy_threshold",
        "basis_bps_threshold",
        "premium_z_threshold",
        "funding_z_threshold",
        "oi_delta_z_threshold",
        "oi_delta_min_notional",
        "premium_slope_min_bps",
        "flow_alignment_z_min",
        "min_edge_bps",
        "spacing_bars",
    }
    assert set(metadata.parameter_space) == set(metadata.default_parameters)
    assert "hmm_router_non_prior_fit_posteriors" in metadata.failure_modes


def test_hmm_knn_local_analog_filter_metadata_covers_required_contract() -> None:
    plugin = get_strategy_plugin("hmm_knn_local_analog_filter_v2")
    metadata = metadata_for_strategy("hmm_knn_local_analog_filter_v2")

    assert plugin.allowed_holding_periods == ("4h", "12h", "24h", "72h")
    assert plugin.required_feature_sets == ("features_perp_context_v2",)
    assert set(metadata.default_parameters) == {
        "probability_threshold",
        "expected_value_threshold",
        "min_neighbor_count",
        "min_neighbor_agreement",
        "min_neighbor_distance_quality",
        "min_vote_margin",
        "posterior_threshold",
        "entropy_threshold",
        "spacing_bars",
    }
    assert set(metadata.parameter_space) == set(metadata.default_parameters)
    assert "hmm_knn_future_neighbor_boundary" in metadata.failure_modes


def test_liquidation_absorption_classifier_metadata_covers_required_contract() -> None:
    plugin = get_strategy_plugin("liquidation_absorption_classifier_v1")
    metadata = metadata_for_strategy("liquidation_absorption_classifier_v1")

    assert plugin.allowed_holding_periods == ("1h", "4h", "12h", "24h")
    assert plugin.required_feature_sets == ("features_liquidation_context_v1",)
    assert set(metadata.default_parameters) == {
        "notional_z_threshold",
        "imbalance_abs_threshold",
        "reclaim_bps_threshold",
        "min_event_count",
        "max_event_age_h",
        "allow_latest_window_context",
        "spacing_bars",
    }
    assert set(metadata.parameter_space) == set(metadata.default_parameters)
    assert metadata.default_parameters["allow_latest_window_context"] is False
    assert "liquidation_context_missing_or_not_provider_backed" in metadata.failure_modes


def test_no_trade_comparator_supports_perp_context_v2_feature_set() -> None:
    plugin = get_strategy_plugin(
        "baseline_no_trade",
        config={"feature_set_id": "features_perp_context_v2", "holding_period": "24h"},
    )

    assert plugin.predict(_perp_context_v2_signal_frame(row_count=24)).empty
    assert "features_perp_context_v2" in plugin.required_feature_sets


def test_no_trade_comparator_supports_liquidation_context_feature_set() -> None:
    plugin = get_strategy_plugin(
        "baseline_no_trade",
        config={"feature_set_id": "features_liquidation_context_v1", "holding_period": "4h"},
    )

    assert plugin.predict(_liquidation_absorption_signal_frame(row_count=24)).empty
    assert "features_liquidation_context_v1" in plugin.required_feature_sets


def test_strategy_plugin_construction_merges_holding_window_defaults() -> None:
    plugin = get_strategy_plugin(
        "hmm_knn_diagnostic_v1",
        config={"feature_set_id": "features_full_context_no_wt", "holding_period": "7d"},
    )

    assert plugin.config["spacing_bars"] == defaults_for_holding_window("hmm_knn_diagnostic_v1", "7d")["spacing_bars"]


def test_strategy_plugin_construction_rejects_invalid_feature_or_window() -> None:
    with pytest.raises(ValueError, match="invalid_holding_period:trend_following_v1:1h"):
        get_strategy_plugin("trend_following_v1", config={"feature_set_id": "features_price_trend_vol", "holding_period": "1h"})
    with pytest.raises(ValueError, match="invalid_feature_set:range_reversion_v1:features_perp_context_only"):
        get_strategy_plugin("range_reversion_v1", config={"feature_set_id": "features_perp_context_only", "holding_period": "4h"})
    with pytest.raises(ValueError, match="invalid_holding_period:perp_basis_convergence_v2:1h"):
        get_strategy_plugin("perp_basis_convergence_v2", config={"feature_set_id": "features_perp_context_v2", "holding_period": "1h"})
    with pytest.raises(ValueError, match="invalid_feature_set:perp_basis_convergence_v2:features_full_context_no_wt"):
        get_strategy_plugin("perp_basis_convergence_v2", config={"feature_set_id": "features_full_context_no_wt", "holding_period": "24h"})
    with pytest.raises(ValueError, match="invalid_holding_period:funding_crowding_fade_v2:1h"):
        get_strategy_plugin("funding_crowding_fade_v2", config={"feature_set_id": "features_perp_context_v2", "holding_period": "1h"})
    with pytest.raises(ValueError, match="invalid_feature_set:funding_crowding_fade_v2:features_full_context_no_wt"):
        get_strategy_plugin("funding_crowding_fade_v2", config={"feature_set_id": "features_full_context_no_wt", "holding_period": "24h"})
    with pytest.raises(ValueError, match="invalid_holding_period:oi_flow_breakout_v2:1h"):
        get_strategy_plugin("oi_flow_breakout_v2", config={"feature_set_id": "features_perp_context_v2", "holding_period": "1h"})
    with pytest.raises(ValueError, match="invalid_feature_set:oi_flow_breakout_v2:features_full_context_no_wt"):
        get_strategy_plugin("oi_flow_breakout_v2", config={"feature_set_id": "features_full_context_no_wt", "holding_period": "24h"})
    with pytest.raises(ValueError, match="invalid_holding_period:funding_window_timing_v1:1h"):
        get_strategy_plugin("funding_window_timing_v1", config={"feature_set_id": "features_perp_context_v2", "holding_period": "1h"})
    with pytest.raises(ValueError, match="invalid_feature_set:funding_window_timing_v1:features_full_context_no_wt"):
        get_strategy_plugin("funding_window_timing_v1", config={"feature_set_id": "features_full_context_no_wt", "holding_period": "24h"})
    with pytest.raises(ValueError, match="invalid_holding_period:hmm_routed_alpha_sleeves_v2:1h"):
        get_strategy_plugin("hmm_routed_alpha_sleeves_v2", config={"feature_set_id": "features_perp_context_v2", "holding_period": "1h"})
    with pytest.raises(ValueError, match="invalid_feature_set:hmm_routed_alpha_sleeves_v2:features_full_context_no_wt"):
        get_strategy_plugin("hmm_routed_alpha_sleeves_v2", config={"feature_set_id": "features_full_context_no_wt", "holding_period": "24h"})
    with pytest.raises(ValueError, match="invalid_holding_period:hmm_knn_local_analog_filter_v2:1h"):
        get_strategy_plugin("hmm_knn_local_analog_filter_v2", config={"feature_set_id": "features_perp_context_v2", "holding_period": "1h"})
    with pytest.raises(ValueError, match="invalid_feature_set:hmm_knn_local_analog_filter_v2:features_full_context_no_wt"):
        get_strategy_plugin("hmm_knn_local_analog_filter_v2", config={"feature_set_id": "features_full_context_no_wt", "holding_period": "24h"})
    with pytest.raises(ValueError, match="invalid_holding_period:liquidation_absorption_classifier_v1:72h"):
        get_strategy_plugin(
            "liquidation_absorption_classifier_v1",
            config={"feature_set_id": "features_liquidation_context_v1", "holding_period": "72h"},
        )
    with pytest.raises(ValueError, match="invalid_feature_set:liquidation_absorption_classifier_v1:features_perp_context_v2"):
        get_strategy_plugin(
            "liquidation_absorption_classifier_v1",
            config={"feature_set_id": "features_perp_context_v2", "holding_period": "4h"},
        )


def test_baseline_strategy_outputs_follow_standard_signal_contract() -> None:
    frame = build_hmm_knn_sweep_dataset(row_count=120, variant="balanced")

    for strategy_id in ["trend_following_v1", "volatility_breakout_v1", "range_reversion_v1", "funding_basis_v1"]:
        plugin = get_strategy_plugin(
            strategy_id,
            config={"symbol": "BTCUSDT", "holding_period": "24h", "feature_set_id": "features_full_context_no_wt", "spacing_bars": 10},
        )
        signals = plugin.predict(frame)
        validation = validate_signal_frame(signals)

        assert validation.valid is True, validation.errors
        assert set(required_signal_columns()) <= set(signals.columns)
        assert len(signals) > 0
        assert signals["research_only"].all()
        assert set(signals["side"]).issubset({"long", "short", "flat"})


def test_hmm_knn_plugin_is_feature_agnostic_and_wt3d_optional() -> None:
    frame = build_hmm_knn_sweep_dataset(row_count=120, variant="balanced")
    frame["p_up_barrier"] = [0.65 if index % 2 == 0 else 0.35 for index in range(len(frame))]
    frame["p_down_barrier"] = 1.0 - frame["p_up_barrier"]
    frame["expected_net_return_after_costs"] = 0.002
    frame["regime_no_trade"] = False
    no_wt_frame = frame.drop(columns=[column for column in frame.columns if column.startswith("wt3d_")], errors="ignore")

    plugin = get_strategy_plugin(
        "hmm_knn_diagnostic_v1",
        config={"symbol": "BTCUSDT", "holding_period": "24h", "feature_set_id": "features_full_context_no_wt", "spacing_bars": 10},
    )
    signals = plugin.predict(no_wt_frame)

    assert validate_signal_frame(signals).valid is True
    assert len(signals) > 0
    assert signals["feature_set_id"].eq("features_full_context_no_wt").all()


def test_perp_basis_convergence_v2_outputs_research_only_signals() -> None:
    frame = _perp_context_v2_signal_frame(row_count=48)
    plugin = get_strategy_plugin(
        "perp_basis_convergence_v2",
        config={
            "symbol": "BTCUSDT",
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "basis_vol_threshold": 2.0,
            "premium_z_threshold": 0.75,
            "min_edge_bps": 1.0,
            "funding_policy": "carry_adjusted",
            "spacing_bars": 1,
        },
    )

    signals = plugin.predict(frame)
    validation = validate_signal_frame(signals)

    assert validation.valid is True, validation.errors
    assert len(signals) > 0
    assert set(signals["side"]) == {"long", "short"}
    assert signals["feature_set_id"].eq("features_perp_context_v2").all()
    assert signals["strategy_id"].eq("perp_basis_convergence_v2").all()
    assert signals["research_only"].all()


@pytest.mark.parametrize("missing_column", REQUIRED_PERP_CONTEXT_V2_COLUMNS)
def test_perp_basis_convergence_v2_fails_closed_when_required_columns_are_missing(missing_column: str) -> None:
    plugin = get_strategy_plugin(
        "perp_basis_convergence_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    complete = _perp_context_v2_signal_frame(row_count=24)

    assert plugin.predict(complete.drop(columns=[missing_column])).empty


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("quality_context_missing_count", 1.0),
        ("quality_has_funding_gap", 1.0),
        ("quality_has_oi_gap", 1.0),
        ("quality_has_premium_gap", 1.0),
        ("quality_provider_backed_all_required", 0.0),
        ("quality_provider_backed_all_required", float("nan")),
        ("perp_mark_index_basis", float("nan")),
        ("perp_premium", float("inf")),
        ("perp_premium_z_7d", None),
        ("perp_last_funding_rate", "not-numeric"),
    ],
)
def test_perp_basis_convergence_v2_fails_closed_on_invalid_context_values(column: str, value: object) -> None:
    plugin = get_strategy_plugin(
        "perp_basis_convergence_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _perp_context_v2_signal_frame(row_count=24)
    frame[column] = value

    assert plugin.predict(frame).empty


def test_perp_basis_convergence_v2_allows_latest_window_context_provenance() -> None:
    plugin = get_strategy_plugin(
        "perp_basis_convergence_v2",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "basis_vol_threshold": 2.0,
            "premium_z_threshold": 0.75,
            "min_edge_bps": 1.0,
            "funding_policy": "carry_adjusted",
            "spacing_bars": 1,
        },
    )
    frame = _perp_context_v2_signal_frame(row_count=24)
    frame["quality_latest_window_context_only"] = 1.0

    assert not plugin.predict(frame).empty


def test_funding_crowding_fade_v2_outputs_research_only_signals() -> None:
    frame = _funding_crowding_v2_signal_frame(row_count=48)
    plugin = get_strategy_plugin(
        "funding_crowding_fade_v2",
        config={
            "symbol": "BTCUSDT",
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "spacing_bars": 1,
        },
    )

    signals = plugin.predict(frame)
    validation = validate_signal_frame(signals)

    assert validation.valid is True, validation.errors
    assert len(signals) > 0
    assert set(signals["side"]) == {"long", "short"}
    assert signals["feature_set_id"].eq("features_perp_context_v2").all()
    assert signals["strategy_id"].eq("funding_crowding_fade_v2").all()
    assert signals["research_only"].all()


@pytest.mark.parametrize("missing_column", REQUIRED_FUNDING_CROWDING_FADE_COLUMNS)
def test_funding_crowding_fade_v2_fails_closed_when_required_columns_are_missing(missing_column: str) -> None:
    plugin = get_strategy_plugin(
        "funding_crowding_fade_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    complete = _funding_crowding_v2_signal_frame(row_count=24)

    assert plugin.predict(complete.drop(columns=[missing_column])).empty


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("quality_context_missing_count", 1.0),
        ("quality_has_funding_gap", 1.0),
        ("quality_has_oi_gap", 1.0),
        ("quality_has_premium_gap", 1.0),
        ("quality_provider_backed_all_required", 0.0),
        ("quality_provider_backed_all_required", float("nan")),
        ("perp_last_funding_rate", "not-numeric"),
        ("perp_funding_z_7d", float("inf")),
        ("perp_funding_momentum", None),
        ("perp_mark_index_basis", float("nan")),
        ("perp_premium", "bad-premium"),
        ("oi_delta_z_7d", float("-inf")),
    ],
)
def test_funding_crowding_fade_v2_fails_closed_on_invalid_context_values(column: str, value: object) -> None:
    plugin = get_strategy_plugin(
        "funding_crowding_fade_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _funding_crowding_v2_signal_frame(row_count=24)
    frame[column] = value

    assert plugin.predict(frame).empty


def test_funding_crowding_fade_v2_requires_oi_confirmation() -> None:
    plugin = get_strategy_plugin(
        "funding_crowding_fade_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _funding_crowding_v2_signal_frame(row_count=24)
    frame["oi_delta_z_7d"] = 0.0

    assert plugin.predict(frame).empty


def test_funding_crowding_fade_v2_allows_latest_window_context_provenance() -> None:
    plugin = get_strategy_plugin(
        "funding_crowding_fade_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _funding_crowding_v2_signal_frame(row_count=24)
    frame["quality_latest_window_context_only"] = 1.0

    assert not plugin.predict(frame).empty


def test_oi_flow_breakout_v2_outputs_research_only_signals() -> None:
    frame = _oi_flow_breakout_v2_signal_frame(row_count=48)
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={
            "symbol": "BTCUSDT",
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "spacing_bars": 1,
        },
    )

    signals = plugin.predict(frame)
    validation = validate_signal_frame(signals)

    assert validation.valid is True, validation.errors
    assert len(signals) > 0
    assert set(signals["side"]) == {"long", "short"}
    assert signals["feature_set_id"].eq("features_perp_context_v2").all()
    assert signals["strategy_id"].eq("oi_flow_breakout_v2").all()
    assert signals["research_only"].all()


@pytest.mark.parametrize("missing_column", REQUIRED_OI_FLOW_BREAKOUT_COLUMNS)
def test_oi_flow_breakout_v2_fails_closed_when_required_columns_are_missing(missing_column: str) -> None:
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    complete = _oi_flow_breakout_v2_signal_frame(row_count=24)

    assert plugin.predict(complete.drop(columns=[missing_column])).empty


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("quality_context_missing_count", 1.0),
        ("quality_has_funding_gap", 1.0),
        ("quality_has_oi_gap", 1.0),
        ("quality_has_premium_gap", 1.0),
        ("quality_provider_backed_all_required", 0.0),
        ("quality_provider_backed_all_required", float("nan")),
        ("perp_mark_index_basis", float("nan")),
        ("perp_premium", "bad-premium"),
        ("perp_premium_slope_8h", None),
        ("oi_notional", "bad-notional"),
        ("oi_delta_1h", float("inf")),
        ("oi_delta_z_7d", float("-inf")),
    ],
)
def test_oi_flow_breakout_v2_fails_closed_on_invalid_context_values(column: str, value: object) -> None:
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _oi_flow_breakout_v2_signal_frame(row_count=24)
    frame[column] = value

    assert plugin.predict(frame).empty


def test_oi_flow_breakout_v2_requires_positive_oi_expansion() -> None:
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _oi_flow_breakout_v2_signal_frame(row_count=24)
    frame["oi_delta_1h"] = -1_000_000.0

    assert plugin.predict(frame).empty


def test_oi_flow_breakout_v2_allows_missing_flow_when_optional() -> None:
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _oi_flow_breakout_v2_signal_frame(row_count=24).drop(
        columns=["flow_buy_sell_ratio", "flow_signed_taker_notional", "flow_signed_taker_z_7d"],
    )

    assert not plugin.predict(frame).empty


def test_oi_flow_breakout_v2_requires_flow_when_policy_is_required() -> None:
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "flow_confirmation_policy": "required",
            "spacing_bars": 1,
        },
    )
    frame = _oi_flow_breakout_v2_signal_frame(row_count=24)
    frame["flow_signed_taker_z_7d"] = float("nan")

    assert plugin.predict(frame).empty


def test_oi_flow_breakout_v2_filters_misaligned_flow_when_present() -> None:
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "flow_confirmation_policy": "require_when_present",
            "spacing_bars": 1,
        },
    )
    frame = _oi_flow_breakout_v2_signal_frame(row_count=24)
    frame["flow_signed_taker_z_7d"] = frame["flow_signed_taker_z_7d"] * -1.0

    assert plugin.predict(frame).empty


def test_oi_flow_breakout_v2_fails_closed_on_invalid_spacing_bars() -> None:
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "spacing_bars": "not-an-integer",
        },
    )
    frame = _oi_flow_breakout_v2_signal_frame(row_count=24)

    assert plugin.predict(frame).empty


def test_oi_flow_breakout_v2_allows_latest_window_context_provenance() -> None:
    plugin = get_strategy_plugin(
        "oi_flow_breakout_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _oi_flow_breakout_v2_signal_frame(row_count=24)
    frame["quality_latest_window_context_only"] = 1.0

    assert not plugin.predict(frame).empty


def test_funding_window_timing_v1_outputs_research_only_signals() -> None:
    frame = _funding_window_timing_v1_signal_frame(row_count=48)
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={
            "symbol": "BTCUSDT",
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "spacing_bars": 1,
        },
    )

    signals = plugin.predict(frame)
    validation = validate_signal_frame(signals)

    assert validation.valid is True, validation.errors
    assert len(signals) > 0
    assert set(signals["side"]) == {"long", "short"}
    assert signals["feature_set_id"].eq("features_perp_context_v2").all()
    assert signals["strategy_id"].eq("funding_window_timing_v1").all()
    assert signals["research_only"].all()


@pytest.mark.parametrize("missing_column", REQUIRED_FUNDING_WINDOW_TIMING_COLUMNS)
def test_funding_window_timing_v1_fails_closed_when_required_columns_are_missing(missing_column: str) -> None:
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    complete = _funding_window_timing_v1_signal_frame(row_count=24)

    assert plugin.predict(complete.drop(columns=[missing_column])).empty


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("quality_context_missing_count", 1.0),
        ("quality_has_funding_gap", 1.0),
        ("quality_has_oi_gap", 1.0),
        ("quality_has_premium_gap", 1.0),
        ("quality_provider_backed_all_required", 0.0),
        ("quality_provider_backed_all_required", float("nan")),
        ("perp_last_funding_rate", "bad-funding"),
        ("perp_funding_z_7d", float("inf")),
        ("perp_funding_momentum", None),
        ("cal_time_since_last_funding_h", float("nan")),
        ("cal_time_to_next_funding_h", "bad-time"),
        ("perp_mark_index_basis", float("-inf")),
        ("perp_premium", "bad-premium"),
        ("oi_delta_z_7d", None),
    ],
)
def test_funding_window_timing_v1_fails_closed_on_invalid_context_values(column: str, value: object) -> None:
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _funding_window_timing_v1_signal_frame(row_count=24)
    frame[column] = value

    assert plugin.predict(frame).empty


def test_funding_window_timing_v1_requires_funding_window() -> None:
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _funding_window_timing_v1_signal_frame(row_count=24)
    frame["cal_time_to_next_funding_h"] = 4.0
    frame["cal_time_since_last_funding_h"] = 4.0

    assert plugin.predict(frame).empty


def test_funding_window_timing_v1_supports_post_funding_window_mode() -> None:
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "window_mode": "post_funding",
            "spacing_bars": 1,
        },
    )
    frame = _funding_window_timing_v1_signal_frame(row_count=24)
    frame["cal_time_to_next_funding_h"] = 6.0
    frame["cal_time_since_last_funding_h"] = 0.25

    assert not plugin.predict(frame).empty


def test_funding_window_timing_v1_filters_momentum_acceleration() -> None:
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _funding_window_timing_v1_signal_frame(row_count=24)
    long_rows = frame["perp_last_funding_rate"] < 0.0
    short_rows = frame["perp_last_funding_rate"] > 0.0
    frame.loc[long_rows, "perp_funding_momentum"] = -0.00001
    frame.loc[short_rows, "perp_funding_momentum"] = 0.00001

    assert plugin.predict(frame).empty


def test_funding_window_timing_v1_fails_closed_on_invalid_spacing_bars() -> None:
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "spacing_bars": "not-an-integer",
        },
    )
    frame = _funding_window_timing_v1_signal_frame(row_count=24)

    assert plugin.predict(frame).empty


def test_funding_window_timing_v1_fails_closed_on_invalid_numeric_parameters() -> None:
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "funding_z_threshold": "bad-threshold",
            "spacing_bars": 1,
        },
    )
    frame = _funding_window_timing_v1_signal_frame(row_count=24)

    assert plugin.predict(frame).empty


def test_funding_window_timing_v1_allows_latest_window_context_provenance() -> None:
    plugin = get_strategy_plugin(
        "funding_window_timing_v1",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _funding_window_timing_v1_signal_frame(row_count=24)
    frame["quality_latest_window_context_only"] = 1.0

    assert not plugin.predict(frame).empty


def test_hmm_routed_alpha_sleeves_v2_outputs_research_only_signals() -> None:
    frame = _hmm_routed_alpha_sleeves_v2_signal_frame(row_count=48)
    plugin = get_strategy_plugin(
        "hmm_routed_alpha_sleeves_v2",
        config={
            "symbol": "BTCUSDT",
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "spacing_bars": 1,
        },
    )

    signals = plugin.predict(frame)
    validation = validate_signal_frame(signals)

    assert validation.valid is True, validation.errors
    assert len(signals) > 0
    assert set(signals["side"]) == {"long", "short"}
    assert signals["feature_set_id"].eq("features_perp_context_v2").all()
    assert signals["strategy_id"].eq("hmm_routed_alpha_sleeves_v2").all()
    assert signals["research_only"].all()
    assert set(signals["skip_reason"]) == {
        "hmm_router_bull_trend_oi_flow",
        "hmm_router_bear_trend_oi_flow",
        "hmm_router_range_basis_funding_fade",
    }


@pytest.mark.parametrize("missing_column", REQUIRED_HMM_ROUTED_ALPHA_COLUMNS)
def test_hmm_routed_alpha_sleeves_v2_fails_closed_when_required_columns_are_missing(missing_column: str) -> None:
    plugin = get_strategy_plugin(
        "hmm_routed_alpha_sleeves_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    complete = _hmm_routed_alpha_sleeves_v2_signal_frame(row_count=24)

    assert plugin.predict(complete.drop(columns=[missing_column])).empty


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("quality_context_missing_count", 1.0),
        ("quality_has_funding_gap", 1.0),
        ("quality_has_oi_gap", 1.0),
        ("quality_has_premium_gap", 1.0),
        ("quality_provider_backed_all_required", 0.0),
        ("quality_latest_window_context_only", float("nan")),
        ("max_regime_probability", 0.40),
        ("posterior_entropy", 0.99),
        ("recent_regime_flip", True),
        ("recent_regime_flip", None),
        ("regime_no_trade", True),
        ("regime_no_trade", None),
        ("hmm_fit_end_row", -1),
        ("hmm_fit_end_row", 1.5),
        ("hmm_fit_end_row", 200),
        ("source_row_index", 1.5),
        ("source_row_index", -1),
        ("top_regime_label", "shock_transition"),
    ],
)
def test_hmm_routed_alpha_sleeves_v2_fails_closed_on_unsafe_or_invalid_router_context(
    column: str,
    value: object,
) -> None:
    plugin = get_strategy_plugin(
        "hmm_routed_alpha_sleeves_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _hmm_routed_alpha_sleeves_v2_signal_frame(row_count=24)
    frame[column] = value

    assert plugin.predict(frame).empty


def test_hmm_routed_alpha_sleeves_v2_trend_sleeve_filters_invalid_oi_context() -> None:
    plugin = get_strategy_plugin(
        "hmm_routed_alpha_sleeves_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _hmm_routed_alpha_sleeves_v2_signal_frame(row_count=24)
    frame["top_regime_label"] = "bull_trend"
    frame["oi_delta_z_7d"] = float("nan")

    assert plugin.predict(frame).empty


def test_hmm_routed_alpha_sleeves_v2_range_sleeve_filters_invalid_basis_context() -> None:
    plugin = get_strategy_plugin(
        "hmm_routed_alpha_sleeves_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _hmm_routed_alpha_sleeves_v2_signal_frame(row_count=24)
    frame["top_regime_label"] = "range_chop"
    frame["perp_mark_index_basis"] = float("nan")

    assert plugin.predict(frame).empty


def test_hmm_routed_alpha_sleeves_v2_requires_flow_when_alignment_threshold_is_positive() -> None:
    plugin = get_strategy_plugin(
        "hmm_routed_alpha_sleeves_v2",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "flow_alignment_z_min": 0.25,
            "spacing_bars": 1,
        },
    )
    frame = _hmm_routed_alpha_sleeves_v2_signal_frame(row_count=24).drop(columns=["flow_signed_taker_z_7d"])
    frame["top_regime_label"] = "bull_trend"
    frame["perp_premium"] = 0.0003
    frame["perp_premium_slope_8h"] = 0.00002
    frame["oi_delta_1h"] = 50_000_000.0
    frame["oi_delta_z_7d"] = 1.2

    assert plugin.predict(frame).empty


def test_hmm_routed_alpha_sleeves_v2_allows_missing_flow_when_alignment_threshold_is_zero() -> None:
    plugin = get_strategy_plugin(
        "hmm_routed_alpha_sleeves_v2",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "flow_alignment_z_min": 0.0,
            "spacing_bars": 1,
        },
    )
    frame = _hmm_routed_alpha_sleeves_v2_signal_frame(row_count=24).drop(columns=["flow_signed_taker_z_7d"])
    frame["top_regime_label"] = "bull_trend"
    frame["perp_premium"] = 0.0003
    frame["perp_premium_slope_8h"] = 0.00002
    frame["oi_delta_1h"] = 50_000_000.0
    frame["oi_delta_z_7d"] = 1.2

    assert not plugin.predict(frame).empty


def test_hmm_routed_alpha_sleeves_v2_fails_closed_on_invalid_numeric_parameters() -> None:
    plugin = get_strategy_plugin(
        "hmm_routed_alpha_sleeves_v2",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "posterior_threshold": "bad-threshold",
            "spacing_bars": 1,
        },
    )
    frame = _hmm_routed_alpha_sleeves_v2_signal_frame(row_count=24)

    assert plugin.predict(frame).empty


def test_hmm_knn_local_analog_filter_v2_outputs_research_only_signals() -> None:
    frame = _hmm_knn_local_analog_filter_v2_signal_frame(row_count=48)
    plugin = get_strategy_plugin(
        "hmm_knn_local_analog_filter_v2",
        config={
            "symbol": "BTCUSDT",
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "spacing_bars": 1,
        },
    )

    signals = plugin.predict(frame)
    validation = validate_signal_frame(signals)

    assert validation.valid is True, validation.errors
    assert len(signals) > 0
    assert set(signals["side"]) == {"long", "short"}
    assert signals["feature_set_id"].eq("features_perp_context_v2").all()
    assert signals["strategy_id"].eq("hmm_knn_local_analog_filter_v2").all()
    assert signals["skip_reason"].eq("hmm_knn_local_analog_filter").all()
    assert signals["research_only"].all()


@pytest.mark.parametrize("missing_column", REQUIRED_HMM_KNN_LOCAL_ANALOG_COLUMNS)
def test_hmm_knn_local_analog_filter_v2_fails_closed_when_required_columns_are_missing(missing_column: str) -> None:
    plugin = get_strategy_plugin(
        "hmm_knn_local_analog_filter_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    complete = _hmm_knn_local_analog_filter_v2_signal_frame(row_count=24)

    assert plugin.predict(complete.drop(columns=[missing_column])).empty


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("accepted_by_knn", False),
        ("accepted_by_knn", None),
        ("knn_skip_reason", "insufficient_neighbors"),
        ("regime_no_trade", True),
        ("regime_no_trade", None),
        ("recent_regime_flip", True),
        ("recent_regime_flip", None),
        ("hmm_fit_end_row", 200),
        ("hmm_fit_end_row", -1),
        ("hmm_fit_end_row", 99.5),
        ("source_row_index", -1),
        ("source_row_index", 99.5),
        ("neighbor_min_source_index", None),
        ("neighbor_min_source_index", -1),
        ("neighbor_max_source_index", 250),
        ("neighbor_max_source_index", 99.5),
        ("max_regime_probability", 0.40),
        ("posterior_entropy", 0.99),
        ("p_up_barrier", float("nan")),
        ("p_down_barrier", "bad-probability"),
        ("neighbor_count", 2),
        ("neighbor_distance_quality", 0.0),
        ("neighbor_agreement", 0.40),
        ("knn_vote_margin", 0.0),
        ("expected_net_return_after_costs", -1.0),
    ],
)
def test_hmm_knn_local_analog_filter_v2_fails_closed_on_unsafe_or_invalid_context(
    column: str,
    value: object,
) -> None:
    plugin = get_strategy_plugin(
        "hmm_knn_local_analog_filter_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _hmm_knn_local_analog_filter_v2_signal_frame(row_count=24)
    frame[column] = value

    assert plugin.predict(frame).empty


def test_hmm_knn_local_analog_filter_v2_rejects_neighbors_after_hmm_fit_boundary() -> None:
    plugin = get_strategy_plugin(
        "hmm_knn_local_analog_filter_v2",
        config={"holding_period": "24h", "feature_set_id": "features_perp_context_v2", "spacing_bars": 1},
    )
    frame = _hmm_knn_local_analog_filter_v2_signal_frame(row_count=24)
    frame["hmm_fit_end_row"] = 120
    frame["neighbor_max_source_index"] = 121
    frame["source_row_index"] = 150

    assert plugin.predict(frame).empty


def test_hmm_knn_local_analog_filter_v2_fails_closed_on_invalid_numeric_parameters() -> None:
    plugin = get_strategy_plugin(
        "hmm_knn_local_analog_filter_v2",
        config={
            "holding_period": "24h",
            "feature_set_id": "features_perp_context_v2",
            "min_neighbor_count": "bad-count",
            "spacing_bars": 1,
        },
    )
    frame = _hmm_knn_local_analog_filter_v2_signal_frame(row_count=24)

    assert plugin.predict(frame).empty


def test_liquidation_absorption_classifier_v1_outputs_research_only_signals() -> None:
    frame = _liquidation_absorption_signal_frame(row_count=48)
    plugin = get_strategy_plugin(
        "liquidation_absorption_classifier_v1",
        config={
            "symbol": "BTCUSDT",
            "holding_period": "4h",
            "feature_set_id": "features_liquidation_context_v1",
            "spacing_bars": 1,
        },
    )

    signals = plugin.predict(frame)
    validation = validate_signal_frame(signals)

    assert validation.valid is True, validation.errors
    assert len(signals) > 0
    assert set(signals["side"]) == {"long", "short"}
    assert signals["feature_set_id"].eq("features_liquidation_context_v1").all()
    assert signals["strategy_id"].eq("liquidation_absorption_classifier_v1").all()
    assert signals["skip_reason"].eq("").all()
    assert signals["research_only"].all()


@pytest.mark.parametrize("missing_column", REQUIRED_LIQUIDATION_ABSORPTION_COLUMNS)
def test_liquidation_absorption_classifier_v1_fails_closed_when_required_columns_are_missing(
    missing_column: str,
) -> None:
    plugin = get_strategy_plugin(
        "liquidation_absorption_classifier_v1",
        config={"holding_period": "4h", "feature_set_id": "features_liquidation_context_v1", "spacing_bars": 1},
    )
    complete = _liquidation_absorption_signal_frame(row_count=24)

    assert plugin.predict(complete.drop(columns=[missing_column])).empty


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("quality_has_liquidation_gap", 1.0),
        ("quality_has_liquidation_gap", float("nan")),
        ("quality_liquidation_provider_backed", 0.0),
        ("quality_liquidation_provider_backed", None),
        ("quality_liquidation_latest_window_context_only", 1.0),
        ("liq_event_count_1h", 0.0),
        ("liq_total_notional_1h", 0.0),
        ("liq_total_notional_z_7d", 0.25),
        ("liq_imbalance_ratio_1h", 0.1),
        ("liq_time_since_last_event_h", 2.0),
        ("liq_absorption_reclaim_bps", 1.0),
        ("liq_absorption_reclaim_bps", float("nan")),
    ],
)
def test_liquidation_absorption_classifier_v1_fails_closed_on_unsafe_or_invalid_context(
    column: str,
    value: object,
) -> None:
    plugin = get_strategy_plugin(
        "liquidation_absorption_classifier_v1",
        config={"holding_period": "4h", "feature_set_id": "features_liquidation_context_v1", "spacing_bars": 1},
    )
    frame = _liquidation_absorption_signal_frame(row_count=24)
    frame[column] = value

    assert plugin.predict(frame).empty


def test_liquidation_absorption_classifier_v1_can_opt_into_latest_window_context() -> None:
    plugin = get_strategy_plugin(
        "liquidation_absorption_classifier_v1",
        config={
            "holding_period": "4h",
            "feature_set_id": "features_liquidation_context_v1",
            "allow_latest_window_context": True,
            "spacing_bars": 1,
        },
    )
    frame = _liquidation_absorption_signal_frame(row_count=24)
    frame["quality_liquidation_latest_window_context_only"] = 1.0

    assert not plugin.predict(frame).empty


def test_liquidation_absorption_classifier_v1_fails_closed_on_invalid_parameters() -> None:
    plugin = get_strategy_plugin(
        "liquidation_absorption_classifier_v1",
        config={
            "holding_period": "4h",
            "feature_set_id": "features_liquidation_context_v1",
            "imbalance_abs_threshold": 2.0,
            "spacing_bars": 1,
        },
    )

    assert plugin.predict(_liquidation_absorption_signal_frame(row_count=24)).empty


def test_liquidation_absorption_classifier_v1_runs_on_checked_wpr64_fixture() -> None:
    frame = _wpr64_liquidation_feature_frame()
    plugin = get_strategy_plugin(
        "liquidation_absorption_classifier_v1",
        config={
            "symbol": "BTCUSDT",
            "holding_period": "1h",
            "feature_set_id": "features_liquidation_context_v1",
            "notional_z_threshold": 1.0,
            "imbalance_abs_threshold": 0.5,
            "reclaim_bps_threshold": 10.0,
            "min_event_count": 1.0,
            "max_event_age_h": 1.0,
            "spacing_bars": 1,
        },
    )

    signals = plugin.predict(frame)
    validation = validate_signal_frame(signals)

    assert validation.valid is True, validation.errors
    assert len(signals) > 0
    assert signals["research_only"].all()
    assert signals["feature_set_id"].eq("features_liquidation_context_v1").all()
    assert signals["strategy_id"].eq("liquidation_absorption_classifier_v1").all()
    assert signals["skip_reason"].eq("").all()
    assert set(signals["side"]).issubset({"long", "short"})


def test_invalid_signal_frame_is_rejected() -> None:
    validation = validate_signal_frame(pd.DataFrame({"side": ["buy"], "research_only": [False]}))

    assert validation.valid is False
    assert any(error.startswith("missing_signal_columns") for error in validation.errors)
    assert "invalid_signal_sides:buy" in validation.errors


def test_malformed_signal_frame_is_rejected_even_with_required_columns() -> None:
    frame = pd.DataFrame(
        {
            "signal_time_ms": [float("nan")],
            "symbol": [""],
            "side": ["long"],
            "strength": [2.0],
            "confidence": [-0.5],
            "target_holding_min_ms": [float("nan")],
            "target_holding_max_ms": [24 * 60 * 60 * 1000],
            "entry_policy": [""],
            "exit_policy_id": ["24h_time_exit"],
            "target_return": [None],
            "stop_return": [None],
            "feature_set_id": ["features_price_trend_vol"],
            "model_version": ["v1"],
            "skip_reason": [""],
            "research_only": ["False"],
        }
    )

    validation = validate_signal_frame(frame)

    assert validation.valid is False
    assert "signal_time_ms_non_finite" in validation.errors
    assert "strength_outside_unit_interval" in validation.errors
    assert "confidence_outside_unit_interval" in validation.errors
    assert "signals_must_be_research_only" in validation.errors
    assert "target_holding_ms_non_finite" in validation.errors


def _liquidation_absorption_signal_frame(*, row_count: int) -> pd.DataFrame:
    rows = []
    start_ms = 1_672_531_200_000
    interval_ms = 60_000
    price = 23_000.0
    for index in range(row_count):
        signal_time_ms = start_ms + index * interval_ms
        close = price + index * 2.0
        liquidation_payload = {
            "liq_event_count_1h": 0.0,
            "liq_total_notional_1h": 0.0,
            "liq_buy_notional_1h": 0.0,
            "liq_sell_notional_1h": 0.0,
            "liq_net_notional_1h": 0.0,
            "liq_total_notional_z_7d": 0.0,
            "liq_imbalance_ratio_1h": 0.0,
            "liq_time_since_last_event_h": 0.1,
            "liq_absorption_reclaim_bps": 0.0,
            "quality_has_liquidation_gap": 0.0,
            "quality_liquidation_provider_backed": 1.0,
            "quality_liquidation_latest_window_context_only": 0.0,
        }
        if index % 12 == 0:
            liquidation_payload.update(
                {
                    "liq_event_count_1h": 24.0,
                    "liq_total_notional_1h": 250_000.0,
                    "liq_sell_notional_1h": 230_000.0,
                    "liq_buy_notional_1h": 20_000.0,
                    "liq_net_notional_1h": -210_000.0,
                    "liq_total_notional_z_7d": 2.0,
                    "liq_imbalance_ratio_1h": -0.84,
                    "liq_absorption_reclaim_bps": 35.0,
                }
            )
        elif index % 12 == 6:
            liquidation_payload.update(
                {
                    "liq_event_count_1h": 18.0,
                    "liq_total_notional_1h": 180_000.0,
                    "liq_buy_notional_1h": 160_000.0,
                    "liq_sell_notional_1h": 20_000.0,
                    "liq_net_notional_1h": 140_000.0,
                    "liq_total_notional_z_7d": 1.7,
                    "liq_imbalance_ratio_1h": 0.78,
                    "liq_absorption_reclaim_bps": 28.0,
                }
            )
        rows.append(
            {
                "bar_time_ms": signal_time_ms,
                "feature_time_ms": signal_time_ms,
                "symbol": "BTCUSDT",
                "open": close - 1.0,
                "high": close + 5.0,
                "low": close - 5.0,
                "close": close,
                "volume": 1_000.0 + index,
                **liquidation_payload,
            }
        )
    return pd.DataFrame(rows)


def _wpr64_liquidation_feature_frame() -> pd.DataFrame:
    manifest_path = Path("data/research/fixtures/btcusdt_liquidation_free_sample_v1/fixture_pack_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = assert_valid_historical_fixture_pack_manifest(manifest, manifest_path=manifest_path)
    payload = validation.to_payload()
    cycle = pd.read_parquet(validation.cycle_dataset_path)
    context = materialize_fixture_family_context(
        cycle,
        optional_context_families=payload["optional_context_families"],
    )
    return materialize_registered_feature_set(
        context.frame,
        feature_set_id="features_liquidation_context_v1",
        interval_ms=60_000,
    ).frame


def _perp_context_v2_signal_frame(*, row_count: int) -> pd.DataFrame:
    rows = []
    start_ms = 1_712_649_600_000
    interval_ms = 900_000
    price = 70_000.0
    for index in range(row_count):
        signal_time_ms = start_ms + index * interval_ms
        close = price + index * 12.0
        basis = 0.0
        premium_z = 0.0
        funding = 0.0
        if index % 12 == 0:
            basis = -0.00045
            premium_z = -1.25
            funding = -0.00001
        elif index % 12 == 6:
            basis = 0.00045
            premium_z = 1.25
            funding = 0.00001
        rows.append(
            {
                "bar_time_ms": signal_time_ms,
                "feature_time_ms": signal_time_ms,
                "symbol": "BTCUSDT",
                "open": close - 10.0,
                "high": close + 40.0,
                "low": close - 40.0,
                "close": close,
                "volume": 1_000.0 + index,
                "perp_mark_index_basis": basis,
                "perp_premium": basis,
                "perp_premium_z_7d": premium_z,
                "perp_premium_slope_8h": basis / 8.0,
                "perp_last_funding_rate": funding,
                "perp_funding_z_7d": funding * 10_000.0,
                "perp_funding_momentum": funding / 2.0,
                "cal_time_since_last_funding_h": float(index % 32) / 4.0,
                "cal_time_to_next_funding_h": 8.0 - (float(index % 32) / 4.0),
                "oi_notional": 1_000_000_000.0 + index * 100_000.0,
                "oi_delta_1h": 10_000.0 if basis else 0.0,
                "oi_delta_z_7d": 0.4 if basis else 0.0,
                "oi_volume_ratio": 0.9,
                "flow_buy_sell_ratio": 1.1 if basis > 0.0 else (0.9 if basis < 0.0 else 1.0),
                "flow_signed_taker_notional": 25_000.0 if basis > 0.0 else (-25_000.0 if basis < 0.0 else 0.0),
                "flow_signed_taker_z_7d": 0.7 if basis > 0.0 else (-0.7 if basis < 0.0 else 0.0),
                "quality_context_missing_count": 0.0,
                "quality_has_funding_gap": 0.0,
                "quality_has_oi_gap": 0.0,
                "quality_has_premium_gap": 0.0,
                "quality_provider_backed_all_required": 1.0,
                "quality_latest_window_context_only": 0.0,
            }
        )
    return pd.DataFrame(rows)


def _funding_crowding_v2_signal_frame(*, row_count: int) -> pd.DataFrame:
    frame = _perp_context_v2_signal_frame(row_count=row_count)
    frame.loc[:, [
        "perp_mark_index_basis",
        "perp_premium",
        "perp_premium_z_7d",
        "perp_last_funding_rate",
        "perp_funding_z_7d",
        "perp_funding_momentum",
        "oi_delta_z_7d",
        "flow_signed_taker_z_7d",
    ]] = 0.0
    short_rows = frame.index[frame.index % 12 == 6]
    long_rows = frame.index[frame.index % 12 == 0]
    frame.loc[short_rows, "perp_mark_index_basis"] = 0.00035
    frame.loc[short_rows, "perp_premium"] = 0.00035
    frame.loc[short_rows, "perp_premium_z_7d"] = 1.5
    frame.loc[short_rows, "perp_last_funding_rate"] = 0.00008
    frame.loc[short_rows, "perp_funding_z_7d"] = 1.8
    frame.loc[short_rows, "perp_funding_momentum"] = -0.00001
    frame.loc[short_rows, "oi_delta_z_7d"] = 0.8
    frame.loc[short_rows, "flow_signed_taker_z_7d"] = 0.8
    frame.loc[long_rows, "perp_mark_index_basis"] = -0.00035
    frame.loc[long_rows, "perp_premium"] = -0.00035
    frame.loc[long_rows, "perp_premium_z_7d"] = -1.5
    frame.loc[long_rows, "perp_last_funding_rate"] = -0.00008
    frame.loc[long_rows, "perp_funding_z_7d"] = -1.8
    frame.loc[long_rows, "perp_funding_momentum"] = 0.00001
    frame.loc[long_rows, "oi_delta_z_7d"] = 0.8
    frame.loc[long_rows, "flow_signed_taker_z_7d"] = -0.8
    return frame


def _oi_flow_breakout_v2_signal_frame(*, row_count: int) -> pd.DataFrame:
    frame = _perp_context_v2_signal_frame(row_count=row_count)
    frame.loc[:, [
        "perp_mark_index_basis",
        "perp_premium",
        "perp_premium_z_7d",
        "perp_premium_slope_8h",
        "oi_delta_1h",
        "oi_delta_z_7d",
        "flow_signed_taker_z_7d",
    ]] = 0.0
    long_rows = frame.index[frame.index % 12 == 0]
    short_rows = frame.index[frame.index % 12 == 6]
    frame.loc[long_rows, "perp_mark_index_basis"] = 0.0006
    frame.loc[long_rows, "perp_premium"] = 0.0006
    frame.loc[long_rows, "perp_premium_z_7d"] = 1.5
    frame.loc[long_rows, "perp_premium_slope_8h"] = 0.00001
    frame.loc[long_rows, "oi_delta_1h"] = 50_000_000.0
    frame.loc[long_rows, "oi_delta_z_7d"] = 1.4
    frame.loc[long_rows, "flow_signed_taker_z_7d"] = 1.0
    frame.loc[short_rows, "perp_mark_index_basis"] = -0.0006
    frame.loc[short_rows, "perp_premium"] = -0.0006
    frame.loc[short_rows, "perp_premium_z_7d"] = -1.5
    frame.loc[short_rows, "perp_premium_slope_8h"] = -0.00001
    frame.loc[short_rows, "oi_delta_1h"] = 50_000_000.0
    frame.loc[short_rows, "oi_delta_z_7d"] = 1.4
    frame.loc[short_rows, "flow_signed_taker_z_7d"] = -1.0
    return frame


def _funding_window_timing_v1_signal_frame(*, row_count: int) -> pd.DataFrame:
    frame = _perp_context_v2_signal_frame(row_count=row_count)
    frame.loc[:, [
        "perp_mark_index_basis",
        "perp_premium",
        "perp_premium_z_7d",
        "perp_last_funding_rate",
        "perp_funding_z_7d",
        "perp_funding_momentum",
        "cal_time_since_last_funding_h",
        "cal_time_to_next_funding_h",
        "oi_delta_z_7d",
    ]] = 0.0
    long_rows = frame.index[frame.index % 12 == 0]
    short_rows = frame.index[frame.index % 12 == 6]
    frame.loc[long_rows, "perp_mark_index_basis"] = -0.00035
    frame.loc[long_rows, "perp_premium"] = -0.00035
    frame.loc[long_rows, "perp_premium_z_7d"] = -1.5
    frame.loc[long_rows, "perp_last_funding_rate"] = -0.00008
    frame.loc[long_rows, "perp_funding_z_7d"] = -1.5
    frame.loc[long_rows, "perp_funding_momentum"] = 0.00001
    frame.loc[long_rows, "cal_time_since_last_funding_h"] = 7.0
    frame.loc[long_rows, "cal_time_to_next_funding_h"] = 0.5
    frame.loc[long_rows, "oi_delta_z_7d"] = 0.2
    frame.loc[short_rows, "perp_mark_index_basis"] = 0.00035
    frame.loc[short_rows, "perp_premium"] = 0.00035
    frame.loc[short_rows, "perp_premium_z_7d"] = 1.5
    frame.loc[short_rows, "perp_last_funding_rate"] = 0.00008
    frame.loc[short_rows, "perp_funding_z_7d"] = 1.5
    frame.loc[short_rows, "perp_funding_momentum"] = -0.00001
    frame.loc[short_rows, "cal_time_since_last_funding_h"] = 7.0
    frame.loc[short_rows, "cal_time_to_next_funding_h"] = 0.5
    frame.loc[short_rows, "oi_delta_z_7d"] = 0.2
    return frame


def _hmm_routed_alpha_sleeves_v2_signal_frame(*, row_count: int) -> pd.DataFrame:
    frame = _perp_context_v2_signal_frame(row_count=row_count)
    frame.loc[:, [
        "perp_mark_index_basis",
        "perp_premium",
        "perp_premium_z_7d",
        "perp_premium_slope_8h",
        "perp_last_funding_rate",
        "perp_funding_z_7d",
        "oi_delta_1h",
        "oi_delta_z_7d",
        "flow_signed_taker_z_7d",
    ]] = 0.0
    frame["top_regime_label"] = "shock_transition"
    frame["max_regime_probability"] = 0.85
    frame["posterior_entropy"] = 0.25
    frame["recent_regime_flip"] = False
    frame["regime_no_trade"] = False
    frame["source_row_index"] = [100 + index for index in range(row_count)]
    frame["hmm_fit_end_row"] = 99

    bull_rows = frame.index[frame.index % 12 == 0]
    bear_rows = frame.index[frame.index % 12 == 4]
    range_short_rows = frame.index[frame.index % 12 == 8]
    range_long_rows = frame.index[frame.index % 12 == 10]

    frame.loc[bull_rows, "top_regime_label"] = "bull_trend"
    frame.loc[bull_rows, "perp_premium"] = 0.0003
    frame.loc[bull_rows, "perp_premium_slope_8h"] = 0.00002
    frame.loc[bull_rows, "oi_delta_1h"] = 50_000_000.0
    frame.loc[bull_rows, "oi_delta_z_7d"] = 1.2
    frame.loc[bull_rows, "flow_signed_taker_z_7d"] = 1.0

    frame.loc[bear_rows, "top_regime_label"] = "bear_trend"
    frame.loc[bear_rows, "perp_premium"] = -0.0003
    frame.loc[bear_rows, "perp_premium_slope_8h"] = -0.00002
    frame.loc[bear_rows, "oi_delta_1h"] = 50_000_000.0
    frame.loc[bear_rows, "oi_delta_z_7d"] = 1.2
    frame.loc[bear_rows, "flow_signed_taker_z_7d"] = -1.0

    frame.loc[range_short_rows, "top_regime_label"] = "range_chop"
    frame.loc[range_short_rows, "perp_mark_index_basis"] = 0.001
    frame.loc[range_short_rows, "perp_premium_z_7d"] = 1.4
    frame.loc[range_short_rows, "perp_last_funding_rate"] = 0.00008
    frame.loc[range_short_rows, "perp_funding_z_7d"] = 1.2

    frame.loc[range_long_rows, "top_regime_label"] = "range_chop"
    frame.loc[range_long_rows, "perp_mark_index_basis"] = -0.001
    frame.loc[range_long_rows, "perp_premium_z_7d"] = -1.4
    frame.loc[range_long_rows, "perp_last_funding_rate"] = -0.00008
    frame.loc[range_long_rows, "perp_funding_z_7d"] = -1.2
    return frame


def _hmm_knn_local_analog_filter_v2_signal_frame(*, row_count: int) -> pd.DataFrame:
    frame = _perp_context_v2_signal_frame(row_count=row_count)
    frame["top_regime_label"] = "bull_trend"
    frame["max_regime_probability"] = 0.85
    frame["posterior_entropy"] = 0.25
    frame["recent_regime_flip"] = False
    frame["regime_no_trade"] = False
    frame["source_row_index"] = [150 + index for index in range(row_count)]
    frame["hmm_fit_end_row"] = 120
    frame["p_up_barrier"] = 0.64
    frame["p_down_barrier"] = 0.36
    frame["expected_net_return_after_costs"] = 0.001
    frame["neighbor_agreement"] = 0.64
    frame["neighbor_distance_quality"] = 0.35
    frame["neighbor_count"] = 12
    frame["neighbor_min_source_index"] = 80
    frame["neighbor_max_source_index"] = 119
    frame["knn_vote_margin"] = 0.28
    frame["accepted_by_knn"] = True
    frame["knn_skip_reason"] = None

    short_rows = frame.index[frame.index % 2 == 1]
    frame.loc[short_rows, "top_regime_label"] = "bear_trend"
    frame.loc[short_rows, "p_up_barrier"] = 0.34
    frame.loc[short_rows, "p_down_barrier"] = 0.66
    return frame
