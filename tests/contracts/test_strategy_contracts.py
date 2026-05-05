from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset
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
