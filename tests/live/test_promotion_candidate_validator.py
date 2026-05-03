from __future__ import annotations

import json
from pathlib import Path

from tradingbotsuite.promotion import (
    load_promotion_candidate_manifest,
    validate_promotion_candidate_for_live_input,
    validate_promotion_candidate_for_shadow,
)


def _candidate_payload() -> dict:
    return {
        "promotion_candidate_manifest_version": "stage11-shadow-v1",
        "candidate_id": "btc-hmm-knn-shadow-001",
        "source_artifact_manifest_path": "artifact_manifest.json",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "shadow_only": True,
        "intended_use": "shadow_only_promotion_candidate",
        "live_signal_input": False,
        "position_sizing_input": False,
        "live_execution_input": False,
        "dataset_manifest_hash": "sha256:dataset",
        "feature_manifest_hash": "sha256:features",
        "strategy_version": "hmm-knn-research-v1",
        "plan": {
            "version": "v2-btc-research",
            "promotion": {
                "min_trade_count": 25,
                "min_expectancy_improvement": 0.01,
                "max_mean_absolute_calibration_error": 0.20,
                "min_improved_split_ratio": 0.50,
            },
        },
        "evidence": {
            "trade_count": 42,
            "baseline_expectancy_after_cost": 0.015,
            "expectancy_after_cost": 0.031,
            "mean_absolute_calibration_error": 0.12,
            "improved_split_ratio": 0.75,
            "event_rows_by_asset": {"BTCUSDT": 12000},
            "uses_regime_model": True,
            "regime_rows": {"trend": 1500, "chop": 1400},
            "labeled_trades_by_side": {"long": 350, "short": 340},
            "accepted_trades_by_validation_split": {
                "wf_0": 60,
                "wf_1": 62,
                "wf_2": 64,
                "wf_3": 66,
                "wf_4": 68,
                "wf_5": 70,
            },
            "volatility_regimes": ["low", "high"],
            "stress_periods": ["2024-08"],
            "costed_expectancy_after_fees_slippage_funding": 0.031,
            "max_split_pnl_share": 0.30,
            "side_outcomes": {"long": {"expectancy": 0.02}, "short": {"expectancy": 0.018}},
            "slippage_stress_passed": True,
            "funding_stress_passed": True,
            "feature_missingness_max_rate": 0.02,
            "feature_missingness_threshold": 0.05,
            "wt3d_claimed": True,
            "wt3d_ablation_passed": True,
        },
        "validation_split_summary": [
            {"split_index": 0, "trade_count": 20, "v2_expectancy_after_cost": 0.03},
            {"split_index": 1, "trade_count": 22, "v2_expectancy_after_cost": 0.032},
        ],
        "cost_assumptions": {"fee_bps": 4.0, "slippage_bps": 2.0, "funding": "observed"},
        "side_metrics": {"long": {"trade_count": 24}, "short": {"trade_count": 18}},
        "regime_metrics": {"trend": {"trade_count": 25}, "chop": {"trade_count": 17}},
        "feature_missingness_summary": {"missing_feature_count": 0},
        "non_promotable_reasons": ["shadow_only_candidate_not_live_order_input"],
        "operator_visible_skip_reasons": ["shadow_only_observation_required"],
        "promotion_failures": [],
    }


def _write_candidate(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_shadow_only_promotion_candidate_is_accepted_when_evidence_floors_pass(tmp_path: Path) -> None:
    manifest_path = _write_candidate(tmp_path / "promotion_candidate.json", _candidate_payload())

    manifest = load_promotion_candidate_manifest(manifest_path)
    result = validate_promotion_candidate_for_shadow(manifest)

    assert result.allowed
    assert result.reasons == ()
    assert result.manifest_path == manifest_path
    assert result.candidate_id == "btc-hmm-knn-shadow-001"


def test_shadow_only_promotion_candidate_rejects_failed_evidence_floors(tmp_path: Path) -> None:
    payload = _candidate_payload()
    payload["evidence"] = {
        "trade_count": 24,
        "baseline_expectancy_after_cost": 0.015,
        "expectancy_after_cost": 0.020,
        "mean_absolute_calibration_error": 0.21,
        "improved_split_ratio": 0.49,
        "event_rows_by_asset": {"BTCUSDT": 9999},
        "uses_regime_model": True,
        "regime_rows": {"trend": 999},
        "labeled_trades_by_side": {"long": 299, "short": 100},
        "accepted_trades_by_validation_split": {"wf_0": 49},
        "volatility_regimes": ["low"],
        "stress_periods": [],
        "costed_expectancy_after_fees_slippage_funding": -0.01,
        "max_split_pnl_share": 0.80,
        "side_outcomes": {"long": {}},
        "slippage_stress_passed": False,
        "funding_stress_passed": False,
        "feature_missingness_max_rate": 0.06,
        "feature_missingness_threshold": 0.05,
        "wt3d_claimed": True,
        "wt3d_ablation_passed": False,
    }
    manifest_path = _write_candidate(tmp_path / "promotion_candidate.json", payload)

    result = validate_promotion_candidate_for_shadow(load_promotion_candidate_manifest(manifest_path))

    assert not result.allowed
    assert "insufficient_trade_count" in result.reasons
    assert "expectancy_improvement_below_floor" in result.reasons
    assert "calibration_error_above_floor" in result.reasons
    assert "improved_split_ratio_below_floor" in result.reasons
    assert "event_rows_floor_not_met:BTCUSDT" in result.reasons
    assert "regime_rows_floor_not_met:trend" in result.reasons
    assert "labeled_trades_floor_not_met:short" in result.reasons
    assert "walk_forward_split_floor_not_met" in result.reasons
    assert "positive_costed_expectancy_required" in result.reasons


def test_shadow_only_promotion_candidate_is_rejected_as_live_order_input(tmp_path: Path) -> None:
    manifest_path = _write_candidate(tmp_path / "promotion_candidate.json", _candidate_payload())
    manifest = load_promotion_candidate_manifest(manifest_path)

    shadow_result = validate_promotion_candidate_for_shadow(manifest)
    live_result = validate_promotion_candidate_for_live_input(manifest)

    assert shadow_result.allowed
    assert not live_result.allowed
    assert "promotion_candidate_rejected_for_live_input" in live_result.reasons
    assert "research_only_artifact_rejected_for_live_input" in live_result.reasons
    assert "observe_only_artifact_rejected_for_live_input" in live_result.reasons
    assert "manifest_declares_not_live_signal_input" in live_result.reasons
