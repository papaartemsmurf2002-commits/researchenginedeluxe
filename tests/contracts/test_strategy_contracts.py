from __future__ import annotations

from pathlib import Path

import pandas as pd

from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset
from tradingbotsuite.strategies import (
    get_strategy_plugin,
    load_strategy_config,
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
