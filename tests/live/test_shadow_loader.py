from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.live.shadow_loader import (
    ShadowLoaderError,
    build_shadow_loader_report,
    load_shadow_promotion_candidate,
)
from tradingbotsuite.runtime import build_engine


def _shadow_config() -> AppConfig:
    return AppConfig(runtime_mode=RuntimeMode.SHADOW)


def _promotion_candidate(path: Path, overrides: dict | None = None) -> Path:
    payload = {
        "promotion_candidate_manifest_version": "stage11-shadow-v1",
        "candidate_id": "btc-hmm-knn-shadow-001",
        "source_artifact_manifest_path": "artifact_manifest.json",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "shadow_only": True,
        "allowed_runtime_modes": ["shadow"],
        "intended_use": "shadow_only_promotion_candidate",
        "live_signal_input": False,
        "position_sizing_input": False,
        "live_execution_input": False,
        "dataset_manifest_hash": "sha256:dataset",
        "feature_manifest_hash": "sha256:features",
        "strategy_version": "hmm-knn-research-v1",
        "plan": {
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
        "validation_split_summary": [{"split_index": 0, "trade_count": 42}],
        "cost_assumptions": {"fee_bps": 4.0, "slippage_bps": 2.0, "funding": "observed"},
        "side_metrics": {"long": {"trade_count": 24}, "short": {"trade_count": 18}},
        "regime_metrics": {"trend": {"trade_count": 25}, "chop": {"trade_count": 17}},
        "feature_missingness_summary": {"missing_feature_count": 0},
        "non_promotable_reasons": ["shadow_only_candidate_not_live_order_input"],
        "operator_visible_skip_reasons": ["shadow_only_observation_required"],
        "promotion_failures": [],
        "features": {"required": ["atr_14", "basis_bps", "depth_notional"]},
        "replay": {
            "fill_assumptions": {
                "spread_bps": 6,
                "basis_bps": 20,
                "depth_levels": 10,
                "depth_notional": 50_000,
            },
            "timing": {"expected_latency_ms": 250, "max_drift_ms": 100},
        },
        "drift_thresholds": {
            "feature_drift": {"max_abs": 0.15},
            "calibration_drift": {"max_abs": 0.05},
        },
    }
    if overrides:
        payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_shadow_loader_accepts_validated_candidate_only_in_shadow_and_reports_comparison(tmp_path: Path) -> None:
    manifest_path = _promotion_candidate(tmp_path / "candidate.json")

    loaded = load_shadow_promotion_candidate(
        _shadow_config(),
        manifest_path,
        comparison_inputs={
            "available_features": ["atr_14", "basis_bps", "depth_notional", "unused_feature"],
            "observed_market": {
                "spread_bps": 5,
                "basis_bps": 18,
                "depth_levels": 12,
                "depth_notional": 55_000,
            },
            "observed_timing": {"latency_ms": 300, "max_drift_ms": 100},
            "feature_drift": {"max_abs": 0.10},
            "calibration_drift": {"max_abs": 0.02},
            "skip_reasons": ["operator_shadow_observation_only"],
        },
    )

    report = loaded.report
    assert loaded.validation.allowed
    assert report.permitted
    assert report.blockers == ()
    assert report.runtime_mode == "shadow"
    assert report.execution_intents_created is False
    assert report.runtime_mode_changed is False
    assert report.feature_availability["missing"] == ()
    assert report.feature_availability["extra"] == ("unused_feature",)
    assert report.replay_fill_assumptions_vs_observed["breached"] is False
    assert report.timing_drift["latency_drift_ms"] == 50
    assert report.timing_drift["breached"] is False
    assert report.feature_drift["breached"] is False
    assert report.calibration_drift["breached"] is False
    assert report.skip_reasons == ("operator_shadow_observation_only",)
    assert _shadow_config().runtime_mode == RuntimeMode.SHADOW


def test_runtime_builds_shadow_engine_with_promotion_candidate_without_scorer(tmp_path: Path) -> None:
    manifest_path = _promotion_candidate(tmp_path / "candidate.json")
    config = AppConfig(
        runtime_mode=RuntimeMode.SHADOW,
        db_path=tmp_path / "shadow.sqlite3",
        research=ResearchConfig(artifact_manifest_path=manifest_path),
    )

    engine = build_engine(config)

    assert engine.config.runtime_mode == RuntimeMode.SHADOW
    assert engine.scorer is None
    assert engine.shadow_promotion_report is not None
    assert engine.shadow_promotion_report["permitted"] is True
    assert engine.shadow_promotion_report["execution_intents_created"] is False
    assert engine.shadow_promotion_report["runtime_mode_changed"] is False


def test_shadow_loader_rejects_non_shadow_runtime_without_changing_mode(tmp_path: Path) -> None:
    manifest_path = _promotion_candidate(tmp_path / "candidate.json")
    config = AppConfig(runtime_mode=RuntimeMode.PAPER)

    with pytest.raises(ShadowLoaderError) as exc_info:
        load_shadow_promotion_candidate(config, manifest_path)

    report = exc_info.value.report
    assert "shadow_loader_requires_shadow_runtime:paper" in report.blockers
    assert report.permitted is False
    assert report.runtime_mode_changed is False
    assert config.runtime_mode == RuntimeMode.PAPER


def test_shadow_loader_rejects_candidate_without_explicit_shadow_runtime(tmp_path: Path) -> None:
    manifest_path = _promotion_candidate(tmp_path / "candidate.json", {"allowed_runtime_modes": []})

    report = build_shadow_loader_report(_shadow_config(), manifest_path)

    assert not report.permitted
    assert "candidate_manifest_does_not_permit_shadow_runtime" in report.blockers


def test_shadow_loader_reads_candidate_through_validator_and_rejects_research_artifacts(tmp_path: Path) -> None:
    manifest_path = _promotion_candidate(
        tmp_path / "research.json",
        {
            "promotion_failures": ["insufficient_trade_count"],
            "evidence": {
                "trade_count": 24,
                "baseline_expectancy_after_cost": 0.015,
                "expectancy_after_cost": 0.020,
                "mean_absolute_calibration_error": 0.21,
                "improved_split_ratio": 0.49,
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
        },
    )

    report = build_shadow_loader_report(_shadow_config(), manifest_path)

    assert not report.permitted
    assert "promotion_failures_must_be_empty_for_shadow_acceptance" in report.validator_reasons
    assert "validator_rejected_candidate:insufficient_trade_count" in report.blockers
    assert "validator_rejected_candidate:calibration_error_above_floor" in report.skip_reasons


def test_shadow_loader_surfaces_fill_timing_feature_and_calibration_drift_skip_reasons(tmp_path: Path) -> None:
    manifest_path = _promotion_candidate(tmp_path / "candidate.json")

    report = build_shadow_loader_report(
        _shadow_config(),
        manifest_path,
        comparison_inputs={
            "available_features": ["atr_14"],
            "observed_market": {
                "spread_bps": 8,
                "basis_bps": 25,
                "depth_levels": 8,
                "depth_notional": 40_000,
            },
            "observed_timing": {"latency_ms": 500, "max_drift_ms": 100},
            "feature_drift": {"max_abs": 0.20},
            "calibration_drift": {"max_abs": 0.10},
        },
    )

    assert report.feature_availability["missing"] == ("basis_bps", "depth_notional")
    assert "missing_feature:basis_bps" in report.skip_reasons
    assert report.replay_fill_assumptions_vs_observed["breached"] is True
    assert report.replay_fill_assumptions_vs_observed["metrics"]["spread_bps"]["breached"] is True
    assert report.replay_fill_assumptions_vs_observed["metrics"]["depth_notional"]["breached"] is True
    assert report.timing_drift["max_abs_drift_ms"] == 250
    assert report.timing_drift["breached"] is True
    assert report.feature_drift["breached"] is True
    assert report.calibration_drift["breached"] is True
