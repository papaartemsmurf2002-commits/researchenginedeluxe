from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tradingbotsuite import main
from tradingbotsuite.backtesting import (
    BACKTEST_ENGINE_VERSION,
    CUDA_BATCHED_BACKTEST_ENGINE_VERSION,
    VECTOR_BACKTEST_ENGINE_VERSION,
    BacktestEngine,
    BacktestSpec,
    VectorBacktestEngine,
)
from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset
from tradingbotsuite.research_cycle import run_historical_research_cycle
import tradingbotsuite.research_cycle.runner as runner_module
from tradingbotsuite.research_cycle.runner import (
    _build_cycle_validation_splits,
    _cost_stress_evidence_details,
    _cost_stress_scenarios,
    _cycle_market_frame,
    _run_cycle_backtest,
    _split_evidence_details,
)
from tradingbotsuite.research_cycle.spec import HistoricalResearchCycleSpec


def _write_cycle_spec(tmp_path: Path) -> Path:
    payload: dict[str, object] = {
        "cycle_id": "synthetic-cycle",
        "symbol": "BTCUSDT",
        "output_dir": str(tmp_path / "research" / "historical_cycles" / "synthetic-cycle"),
        "holding_windows": ["4h", "12h"],
        "data": {
            "synthetic_fixture": True,
            "synthetic_row_count": 120,
            "synthetic_variant": "balanced",
        },
        "features": {
            "feature_sets": ["features_price_trend_vol", "features_full_context_no_wt"],
        },
        "strategies": ["baseline_no_trade", "trend_following_v1", "range_reversion_v1"],
        "validation": {
            "walk_forward": "rolling_and_anchored",
            "purge_embargo_bars": 2,
            "stress_periods_required": True,
            "min_splits": 2,
            "trade_count_floor": 1,
        },
        "optimizer": {
            "method_sequence": ["coarse_lhs", "adaptive_grid", "stability_region_refine"],
            "max_candidates_per_strategy": 16,
            "top_regions_to_refine": 2,
        },
    }
    spec_path = tmp_path / "specs" / "cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return spec_path


def test_full_cycle_synthetic_writes_required_research_artifacts(tmp_path: Path) -> None:
    spec_path = _write_cycle_spec(tmp_path)

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    candidate_space_manifest = json.loads(Path(manifest["required_outputs"]["candidate_space_manifest"]).read_text(encoding="utf-8"))
    feature_build_manifest = json.loads(Path(manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8"))
    split_manifest = json.loads(Path(manifest["required_outputs"]["split_manifest"]).read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    backtest_index = pd.read_parquet(result.backtest_index_path)
    candidate_gate_report = pd.read_parquet(manifest["required_outputs"]["candidate_gate_report"])
    metrics_by_split = pd.read_parquet(manifest["required_outputs"]["metrics_by_split"])
    metrics_by_regime = pd.read_parquet(manifest["required_outputs"]["metrics_by_regime"])
    metrics_by_side = pd.read_parquet(manifest["required_outputs"]["metrics_by_side"])
    trial_budget_report = json.loads(Path(manifest["required_outputs"]["trial_budget_report"]).read_text(encoding="utf-8"))
    overfit_report = json.loads(Path(manifest["required_outputs"]["overfit_adjustment_report"]).read_text(encoding="utf-8"))

    assert manifest["research_cycle_manifest_version"] == "historical-research-cycle-manifest-v1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["candidate_pack_written"] is False
    assert manifest["candidate_pack_paths"] == []
    assert manifest["candidate_pack_scope"] == "research_only_evidence_pack"
    assert manifest["candidate_count"] == 44
    assert manifest["candidate_search_mode"] == "metadata_default_search"
    assert manifest["candidate_search_method"] == "metadata_capped_grid"
    assert manifest["backtest_backend_requested"] == "auto"
    assert manifest["aggregate_backtest_count"] == 44
    assert manifest["split_backtest_count"] == 4
    assert manifest["cost_stress_backtest_count"] == 22
    aggregate_index = backtest_index.loc[backtest_index["evaluation_scope"] == "aggregate"]
    validation_index = backtest_index.loc[backtest_index["evaluation_scope"] != "aggregate"]
    aggregate_backend_values = set(aggregate_index["backtest_backend_used"])
    assert aggregate_backend_values <= {"cuda_batched_fixed_holding", "vector_fixed_holding"}
    assert aggregate_backend_values
    assert set(validation_index["backtest_backend_used"]) == {"reference"}
    assert manifest["backtest_backend_summary"]["used_counts"]["reference"] == len(validation_index)
    assert sum(manifest["backtest_backend_summary"]["used_counts"].values()) == len(backtest_index)
    assert manifest["backtest_backend_summary"]["fallback_count"] == int(
        backtest_index["backtest_backend_fallback_reason"].astype(str).ne("").sum()
    )
    for output_path in manifest["required_outputs"].values():
        assert Path(output_path).exists()
    assert trial_budget_report["trial_budget_report_version"] == "trial-budget-report-v1"
    assert trial_budget_report["research_only"] is True
    assert trial_budget_report["candidate_pack_metric_gate_enabled"] is False
    assert trial_budget_report["effective_trial_count"] == manifest["candidate_count"]
    assert trial_budget_report["total_backtest_evaluation_count"] == len(backtest_index)
    assert sum(trial_budget_report["trials_by_candidate_source"].values()) == manifest["candidate_count"]
    assert "metadata_default_seed" in trial_budget_report["trials_by_candidate_source"]
    assert "metadata_default_search" in trial_budget_report["trials_by_candidate_source"]
    assert overfit_report["overfit_adjustment_report_version"] == "overfit-adjustment-report-v1"
    assert overfit_report["hard_gate_enabled"] is False
    assert overfit_report["candidate_pack_gate_enabled"] is False
    assert len(overfit_report["candidate_diagnostics"]) == len(rankings)
    assert {row["adjustment_scope"] for row in overfit_report["candidate_diagnostics"]} == {
        "diagnostic_only_not_candidate_gate"
    }
    assert feature_build_manifest["feature_build_manifest_version"] == "historical-research-feature-build-v2"
    assert feature_build_manifest["feature_computation_scope"] == "materialized_registered_feature_sets"
    assert {record["cache_status"] for record in feature_build_manifest["feature_sets"]} == {"miss"}
    assert {record["status"] for record in feature_build_manifest["feature_sets"]} == {"built"}
    trend_feature_record = next(record for record in feature_build_manifest["feature_sets"] if record["feature_set_id"] == "features_price_trend_vol")
    trend_features = pd.read_parquet(trend_feature_record["feature_path"])
    source_fixture = pd.read_parquet(manifest["data_source"]["dataset_path"])
    assert trend_feature_record["feature_frame_sha256"]
    assert Path(trend_feature_record["cache_manifest_path"]).exists()
    assert "directional_slope_atr" in trend_features.columns
    assert not trend_features["directional_slope_atr"].fillna(0.0).equals(source_fixture["directional_slope_atr"].fillna(0.0))
    assert split_manifest["validation_method"] == "purged_embargoed_walk_forward"
    assert split_manifest["validation_methods"] == ["purged_embargoed_walk_forward"]
    assert split_manifest["split_modes_requested"] == ["purged_embargoed_walk_forward"]
    assert split_manifest["validation_method_counts"] == {"purged_embargoed_walk_forward": 2}
    assert split_manifest["split_mode_counts"] == {"anchored": 2}
    assert split_manifest["split_count"] == 2

    assert set(rankings["metric_scope"]) == {"real_backtest"}
    assert set(rankings["metrics_source"]) == {"backtest_engine"}
    assert set(rankings["empirical_evidence"]) == {True}
    assert set(rankings["decision"]) == {"rejected"}
    assert rankings["backtest_manifest_path"].map(lambda value: Path(str(value)).exists()).all()
    assert set(rankings["aggregate_stability_region_evaluated"]) == {True}
    assert rankings.loc[rankings["split_evaluated"], "stability_evaluated"].all()
    assert not rankings.loc[~rankings["split_evaluated"], "stability_evaluated"].any()
    assert set(rankings["stability_validation_scope"]) == {
        "split_cost_stress_enriched",
        "aggregate_only_unvalidated_neighborhood",
    }
    assert set(rankings["ranking_scope"]) == {"aggregate_rank_with_validation_annotations"}
    assert rankings["aggregate_rank"].is_monotonic_increasing
    assert rankings["optimizer_rank"].between(1, len(rankings)).all()
    assert rankings["aggregate_backtest_cache_key"].astype(str).str.len().gt(0).all()
    assert rankings["aggregate_backtest_result_sha256"].astype(str).str.len().gt(0).all()
    assert set(rankings["aggregate_backtest_identity_scope"]) == {"aggregate"}
    assert set(rankings["aggregate_backtest_cache_policy"]) == {"identity_only_no_execution_cache"}
    assert set(rankings["aggregate_backtest_cache_hit"]) == {False}
    assert set(rankings["aggregate_backtest_cache_lookup_used"]) == {False}
    assert set(rankings["aggregate_backtest_backend_requested"]) == {"auto"}
    assert set(rankings["aggregate_backtest_backend_used"]) == aggregate_backend_values
    if aggregate_backend_values == {"cuda_batched_fixed_holding"}:
        assert set(rankings["aggregate_backtest_engine_version"]) == {CUDA_BATCHED_BACKTEST_ENGINE_VERSION}
        assert set(rankings["aggregate_backtest_vector_execution_scope"]) == {""}
        assert set(rankings["aggregate_backtest_backend_fallback_reason"]) == {""}
    else:
        assert aggregate_backend_values == {"vector_fixed_holding"}
        assert set(rankings["aggregate_backtest_engine_version"]) == {VECTOR_BACKTEST_ENGINE_VERSION}
        assert set(rankings["aggregate_backtest_vector_execution_scope"]) == {"fixed_holding_primary_bar"}
        assert all(rankings["aggregate_backtest_backend_fallback_reason"].astype(str).str.len().gt(0))
    assert set(rankings["aggregate_backtest_reference_engine_version"]) == {BACKTEST_ENGINE_VERSION}
    assert set(rankings["aggregate_backtest_backend_rejection_reason"]) == {""}
    assert set(rankings["required_split_count"]) == {2}
    assert set(rankings["required_cost_stress_count"]) == {11}
    assert {"signal_rate", "min_signal_rate", "max_signal_rate", "max_turnover"} <= set(rankings.columns)
    assert candidate_space_manifest["search_mode"] == "metadata_default_search"
    assert candidate_space_manifest["search_method"] == "metadata_capped_grid"
    assert candidate_space_manifest["exit_policies"][0]["exit_policy_id"] == "fixed_holding_window"
    default_search_policy = candidate_space_manifest["default_search_policy"]
    assert default_search_policy["enabled"] is True
    assert default_search_policy["research_only"] is True
    assert default_search_policy["observe_only"] is True
    assert default_search_policy["promotion_ready"] is False
    assert default_search_policy["default_search_source"] == "strategy_parameter_metadata"
    assert default_search_policy["default_seed_included"] is True
    assert default_search_policy["effective_metadata_sample_cap"] == 4
    assert default_search_policy["candidate_source_counts"]["metadata_default_seed"] == 12
    assert default_search_policy["candidate_source_counts"]["metadata_default_search"] == 32
    assert sum(default_search_policy["candidate_source_counts"].values()) == candidate_space_manifest["candidate_count"]
    assert {"metadata_default_seed", "metadata_default_search"} <= set(rankings["candidate_source"])
    assert rankings.loc[rankings["candidate_source"] == "metadata_default_seed", "is_default_parameter_candidate"].all()
    assert candidate_space_manifest["strategy_parameter_metadata"]
    assert set(candidate_space_manifest["generated_strategy_ids"]) == set(rankings["strategy_id"])
    assert {record["coverage_status"] for record in candidate_space_manifest["baseline_comparator_coverage"]} == {"complete"}
    assert candidate_space_manifest["baseline_comparator_policy"]["scope"] == "baseline_comparator_evidence_only"
    assert {"strategy_role", "comparator_role", "baseline_group_key", "strategy_metadata_sha256"} <= set(rankings.columns)
    assert {"exit_policy_id", "exit_policy_params_json", "exit_policy_source"} <= set(rankings.columns)
    assert set(rankings["exit_policy_id"]) == {"fixed_holding_window"}
    assert set(rankings["exit_policy_params_json"]) == {"{}"}
    assert {"no_trade_comparator_candidate_id", "expectancy_vs_no_trade", "transparent_default_comparator_candidate_id"} <= set(rankings.columns)
    assert set(rankings["baseline_comparator_coverage_status"]) == {"complete"}
    assert rankings["strategy_metadata_sha256"].astype(str).str.len().gt(0).all()
    ranking_reasons = "|".join(rankings["failure_reasons"].astype(str))
    assert "synthetic_fixture_not_real_oos_evidence" in ranking_reasons
    assert "non_synthetic_fixture_evidence_required" in ranking_reasons
    assert {
        "side_evidence_status",
        "regime_evidence_status",
        "max_single_split_pnl_share",
        "split_trade_count_floor",
        "min_split_trade_count",
        "split_trade_count_floor_status",
        "split_validation_method_status",
        "cost_stress_survival_floor",
        "cost_stress_survival_rate",
        "cost_stress_survival_floor_status",
        "feature_ablation_passed",
        "ablation_evidence_status",
    } <= set(rankings.columns)
    assert {"aggregate", "walk_forward_split", "cost_stress"} <= set(backtest_index["evaluation_scope"])
    assert {
        "comparator_role",
        "baseline_group_key",
        "strategy_metadata_sha256",
        "resolved_parameters_json",
        "trades_path",
        "trades_sha256",
        "backtest_backend_requested",
        "backtest_backend_used",
        "backtest_engine_version",
        "reference_engine_version",
        "vector_execution_scope",
        "cuda_execution_scope",
        "cuda_parity_status",
        "gpu_execution_status",
        "gpu_device_name",
        "gpu_compute_capability",
        "backtest_backend_fallback_reason",
        "backtest_backend_rejection_reason",
        "exit_policy_id",
        "exit_policy_params_json",
        "exit_policy_source",
        "exit_price_source",
        "lower_timeframe_required",
        "lower_timeframe_dataset_path",
        "lower_timeframe_dataset_sha256",
        "lower_timeframe_sequence_used",
        "lower_timeframe_cache_key_component",
        "exit_sequence_proof_counts_json",
        "barrier_hit_type_counts_json",
        "exit_price_source_counts_json",
        "split_id",
        "validation_method",
        "split_mode",
        "validation_size_bars",
        "validation_start_time_ms",
        "validation_end_time_ms",
    } <= set(backtest_index.columns)
    split_index = backtest_index.loc[backtest_index["evaluation_scope"] == "walk_forward_split"]
    assert set(split_index["validation_method"]) == {"purged_embargoed_walk_forward"}
    assert set(split_index["split_mode"]) == {"anchored"}
    assert set(metrics_by_split["validation_method"]) == {"purged_embargoed_walk_forward"}
    assert set(metrics_by_split["split_mode"]) == {"anchored"}
    assert {"trade_count_floor", "trade_count_floor_status"} <= set(metrics_by_split.columns)
    assert metrics_by_split["validation_size_bars"].gt(0).all()
    assert set(backtest_index["exit_policy_id"]) == {"fixed_holding_window"}
    assert set(backtest_index["exit_policy_params_json"]) == {"{}"}
    assert set(backtest_index["exit_price_source"]) == {"primary_close"}
    assert set(backtest_index["lower_timeframe_required"]) == {False}
    assert set(backtest_index["lower_timeframe_sequence_used"]) == {False}
    assert backtest_index["lower_timeframe_dataset_path"].isna().all()
    assert backtest_index["lower_timeframe_dataset_sha256"].isna().all()
    assert backtest_index["lower_timeframe_cache_key_component"].isna().all()
    assert set(backtest_index["backtest_backend_requested"]) == {"auto"}
    assert set(aggregate_index["backtest_backend_used"]) == aggregate_backend_values
    assert set(validation_index["backtest_backend_used"]) == {"reference"}
    assert set(validation_index["backtest_engine_version"]) == {BACKTEST_ENGINE_VERSION}
    assert set(backtest_index["reference_engine_version"]) == {BACKTEST_ENGINE_VERSION}
    if aggregate_backend_values == {"cuda_batched_fixed_holding"}:
        assert set(aggregate_index["backtest_engine_version"]) == {CUDA_BATCHED_BACKTEST_ENGINE_VERSION}
        assert set(aggregate_index["cuda_execution_scope"]) == {"cuda_batched_fixed_holding_primary_bar"}
    else:
        assert set(aggregate_index["backtest_engine_version"]) == {VECTOR_BACKTEST_ENGINE_VERSION}
        assert set(aggregate_index["vector_execution_scope"]) == {"fixed_holding_primary_bar"}
    assert set(validation_index["cuda_execution_scope"]) == {""}
    assert set(validation_index["gpu_execution_status"]) == {""}
    assert set(validation_index["backtest_backend_fallback_reason"]) == {"cuda_batched_fixed_holding_validation_reference_required"}
    assert set(backtest_index["backtest_backend_rejection_reason"]) == {""}
    assert backtest_index.loc[backtest_index["trade_count"] > 0, "trades_path"].map(lambda value: Path(str(value)).exists()).all()
    assert set(metrics_by_side["side"].dropna().astype(str)) <= {"long", "short"}
    assert "all" not in set(metrics_by_side["side"].dropna().astype(str))
    assert not {"all", "aggregate"} & set(metrics_by_regime["regime"].dropna().astype(str))
    feature_records_by_set = {record["feature_set_id"]: record for record in feature_build_manifest["feature_sets"]}
    for row in aggregate_index.to_dict("records"):
        backtest_manifest = json.loads(Path(str(row["backtest_manifest_path"])).read_text(encoding="utf-8"))
        feature_record = feature_records_by_set[str(row["feature_set_id"])]
        assert backtest_manifest["feature_manifest_sha256"] == feature_record["feature_manifest_sha256"]
        assert backtest_manifest["dataset_sha256"] == feature_record["feature_frame_sha256"]
        ranking_row = rankings.loc[rankings["candidate_id"].astype(str) == str(row["candidate_id"])].iloc[0]
        assert ranking_row["aggregate_backtest_cache_key"] == row["cache_key"]
        assert ranking_row["aggregate_backtest_result_sha256"] == row["result_sha256"]
        assert ranking_row["aggregate_backtest_exit_price_source"] == "primary_close"
        assert bool(ranking_row["aggregate_backtest_lower_timeframe_required"]) is False
        assert bool(ranking_row["aggregate_backtest_lower_timeframe_sequence_used"]) is False
        assert pd.isna(ranking_row["aggregate_backtest_lower_timeframe_dataset_sha256"])
    for _, group in backtest_index.loc[backtest_index["evaluation_scope"] == "walk_forward_split"].groupby("candidate_id"):
        assert group["cache_key"].nunique() == len(group)
    for _, group in backtest_index.loc[backtest_index["evaluation_scope"] == "cost_stress"].groupby("candidate_id"):
        assert group["cache_key"].nunique() == len(group)
    assert len(candidate_gate_report) == len(rankings)
    assert set(candidate_gate_report["gate_status"]) == {"blocked"}
    assert set(candidate_gate_report["pack_eligible"]) == {False}
    assert candidate_gate_report["gate_reasons"].str.contains("ranking_decision_not_research_gate_passed").all()
    incomplete_gate_rows = candidate_gate_report.loc[candidate_gate_report["stability_region_decision"] != "accepted_region"]
    assert incomplete_gate_rows["gate_reasons"].str.contains("stability_region_accepted_decision_required").all()


def test_full_cycle_explicit_validation_split_modes_write_evidence(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "cycle_id": "validation-split-mode-cycle",
        "symbol": "BTCUSDT",
        "output_dir": str(tmp_path / "research" / "historical_cycles" / "validation-split-mode-cycle"),
        "holding_windows": ["4h"],
        "data": {
            "synthetic_fixture": True,
            "synthetic_row_count": 120,
            "synthetic_variant": "balanced",
        },
        "features": {
            "feature_sets": ["features_price_trend_vol"],
        },
        "strategies": ["trend_following_v1"],
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
            "shifted_anchor_offsets": [1],
            "purge_embargo_bars": 2,
            "stress_periods_required": True,
            "min_splits": 2,
            "trade_count_floor": 1,
        },
        "optimizer": {
            "max_candidates_per_strategy": 2,
            "top_regions_to_refine": 1,
        },
    }
    spec_path = tmp_path / "specs" / "validation-split-mode-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    split_manifest = json.loads(Path(manifest["required_outputs"]["split_manifest"]).read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    metrics_by_split = pd.read_parquet(manifest["required_outputs"]["metrics_by_split"])
    backtest_index = pd.read_parquet(result.backtest_index_path)
    split_index = backtest_index.loc[backtest_index["evaluation_scope"] == "walk_forward_split"]

    assert split_manifest["validation_method"] == "configured_validation_splits"
    assert set(split_manifest["validation_methods"]) == set(payload["validation"]["split_modes"])  # type: ignore[index]
    assert split_manifest["split_modes_requested"] == payload["validation"]["split_modes"]  # type: ignore[index]
    assert split_manifest["validation_method_counts"]["purged_embargoed_walk_forward"] == 2
    assert split_manifest["validation_method_counts"]["anchored_walk_forward"] == 2
    assert split_manifest["validation_method_counts"]["rolling_walk_forward"] == 2
    assert split_manifest["validation_method_counts"]["shifted_purged_walk_forward"] == 2
    assert split_manifest["validation_method_counts"]["month_holdout"] == 1
    assert split_manifest["validation_method_counts"]["stress_period_holdout"] == 1
    assert split_manifest["validation_method_counts"]["regime_holdout"] >= 2
    assert split_manifest["split_mode_counts"]["rolling"] == 2
    assert split_manifest["split_mode_counts"]["shifted"] == 2
    assert split_manifest["split_mode_counts"]["holdout"] >= 4
    assert manifest["split_backtest_count"] == split_manifest["split_count"]
    assert len(metrics_by_split) == split_manifest["split_count"]
    assert len(split_index) == split_manifest["split_count"]
    assert set(metrics_by_split["validation_method"]) == set(split_manifest["validation_methods"])
    assert set(split_index["validation_method"]) == set(split_manifest["validation_methods"])
    assert set(split_index["split_id"]) == set(metrics_by_split["split_id"])
    assert split_index["split_id"].is_unique
    assert set(rankings["required_split_count"]) == {split_manifest["split_count"]}
    assert set(split_index["evaluation_scope"]) == {"walk_forward_split"}


def test_configured_unavailable_validation_split_mode_fails_closed(tmp_path: Path) -> None:
    spec = HistoricalResearchCycleSpec.from_payload(
        {
            "cycle_id": "missing-regime-cycle",
            "data": {"synthetic_fixture": True},
            "validation": {
                "split_modes": ["regime_holdout"],
                "regime_column": "missing_regime",
            },
        },
        spec_path=tmp_path / "missing-regime-cycle.json",
    )
    market_frame = _cycle_market_frame(build_hmm_knn_sweep_dataset(row_count=96, variant="balanced"))

    with pytest.raises(ValueError, match="validation_split_mode_unavailable:regime_holdout"):
        _build_cycle_validation_splits(market_frame, spec=spec)


def test_research_gate_split_details_enforce_trade_floor_and_method_coverage() -> None:
    details = _split_evidence_details(
        [
            {
                "split_id": "purged-split-01",
                "validation_method": "purged_embargoed_walk_forward",
                "trade_count": 1,
                "net_return_after_fees_slippage_funding": 0.01,
            },
            {
                "split_id": "purged-split-02",
                "validation_method": "purged_embargoed_walk_forward",
                "trade_count": 3,
                "net_return_after_fees_slippage_funding": 0.01,
            },
        ],
        max_single_split_pnl_share=0.5,
        required_split_count=2,
        trade_count_floor=2,
        required_validation_methods=("purged_embargoed_walk_forward", "month_holdout"),
    )

    assert details["status"] == "incomplete"
    assert details["trade_count_floor_status"] == "failed"
    assert details["validation_method_status"] == "incomplete"
    assert "candidate_split_trade_count_below_floor" in details["reasons"]
    assert "candidate_split_validation_method_coverage_incomplete" in details["reasons"]


def test_research_gate_cost_stress_details_require_full_survival() -> None:
    records = []
    for index, scenario in enumerate(_cost_stress_scenarios()):
        score = -0.01 if index == 0 else 0.01
        records.append(
            {
                "scenario_id": scenario["scenario_id"],
                "scenario_status": "evaluated",
                "trade_count": 2,
                "stress_survival_score": score,
            }
        )

    details = _cost_stress_evidence_details(records, min_survival_rate=1.0)

    assert details["status"] == "incomplete"
    assert details["survival_status"] == "failed"
    assert details["survival_rate"] < 1.0
    assert "cost_stress_survival_rate_below_floor" in details["reasons"]
    assert details["failed_scenarios"] == [str(_cost_stress_scenarios()[0]["scenario_id"])]


def test_full_cycle_resolves_relative_dataset_manifest_paths(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = data_dir / "bars.parquet"
    build_hmm_knn_sweep_dataset(row_count=96, variant="balanced").to_parquet(dataset_path, index=False)
    manifest_path = data_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps({"parquet_path": "bars.parquet"}, indent=2, sort_keys=True), encoding="utf-8")
    payload: dict[str, object] = {
        "cycle_id": "relative-manifest-cycle",
        "symbol": "BTCUSDT",
        "output_dir": str(tmp_path / "research" / "historical_cycles" / "relative-manifest-cycle"),
        "holding_windows": ["4h"],
        "data": {
            "dataset_manifest_paths": [str(manifest_path)],
        },
        "features": {
            "feature_sets": ["features_price_trend_vol"],
        },
        "strategies": ["baseline_no_trade"],
        "validation": {
            "purge_embargo_bars": 2,
            "min_splits": 2,
            "trade_count_floor": 1,
        },
        "optimizer": {
            "top_regions_to_refine": 1,
        },
    }
    spec_path = tmp_path / "specs" / "relative-manifest-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["data_source"]["source_type"] == "dataset_manifest"
    assert manifest["data_source"]["dataset_path"] == str(dataset_path.resolve())


def test_full_cycle_expands_optimizer_search_spaces_and_writes_stability_regions(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "cycle_id": "search-space-cycle",
        "symbol": "BTCUSDT",
        "output_dir": str(tmp_path / "research" / "historical_cycles" / "search-space-cycle"),
        "data": {
            "synthetic_fixture": True,
            "synthetic_row_count": 120,
            "synthetic_variant": "balanced",
        },
        "features": {
            "feature_sets": ["features_price_trend_vol"],
        },
        "strategies": ["trend_following_v1"],
        "validation": {
            "walk_forward": "rolling_and_anchored",
            "purge_embargo_bars": 2,
            "stress_periods_required": True,
            "min_splits": 2,
            "trade_count_floor": 1,
        },
        "optimizer": {
            "method_sequence": ["grid", "stability_region_refine"],
            "max_candidates_per_strategy": 4,
            "top_regions_to_refine": 2,
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
        "compute": {
            "cpu_threads": 2,
            "gpu_acceleration": "prefer_nvidia_cuda_when_backend_available",
            "gpu_device_class": "nvidia_50_series",
            "gpu_required": False,
            "gpu_execution_profile": "conservative",
        },
    }
    spec_path = tmp_path / "specs" / "search-space-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    candidate_space_manifest = json.loads(Path(manifest["required_outputs"]["candidate_space_manifest"]).read_text(encoding="utf-8"))
    trial_budget_report = json.loads(Path(manifest["required_outputs"]["trial_budget_report"]).read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    stability_regions = pd.read_parquet(manifest["required_outputs"]["stability_regions"])

    assert manifest["candidate_count"] == 6
    assert manifest["candidate_search_mode"] == "explicit_search_spaces"
    assert manifest["candidate_search_method"] == "grid"
    assert manifest["compute_policy"]["aggregate_backtest_workers_used"] == 2
    assert manifest["compute_policy"]["gpu_execution_status"] == "gpu_execution_profile_conservative"
    assert candidate_space_manifest["candidate_id_scheme"] == "candidate_config_sha256"
    assert candidate_space_manifest["search_mode"] == "explicit_search_spaces"
    performance_plan = candidate_space_manifest["performance_plan"]
    assert performance_plan["performance_plan_version"] == "candidate-selection-performance-plan-v1"
    assert performance_plan["bruteforce_equivalent_candidate_count"] == 4
    assert performance_plan["materialized_search_candidate_count"] == 4
    assert performance_plan["sampled_fraction_of_bruteforce"] == 1.0
    assert performance_plan["raw_sampled_fraction_of_bruteforce"] == 1.0
    assert performance_plan["materialized_search_exceeds_bruteforce"] is False
    assert performance_plan["compute_policy"]["cpu_threads"] == 2
    assert performance_plan["compute_policy"]["aggregate_backtest_workers_used"] == 2
    assert performance_plan["compute_policy"]["gpu_device_class"] == "nvidia_50_series"
    assert performance_plan["compute_policy"]["gpu_execution_status"] == "gpu_execution_profile_conservative"
    assert performance_plan["stability_region_acceleration_counters"]["planned_gpu_screened_count"] == 0
    explicit_policy = candidate_space_manifest["default_search_policy"]
    assert explicit_policy["enabled"] is False
    assert explicit_policy["default_search_source"] == "disabled_explicit_search_spaces_supplied"
    assert sum(explicit_policy["candidate_source_counts"].values()) == candidate_space_manifest["candidate_count"]
    assert trial_budget_report["candidate_search_mode"] == "explicit_search_spaces"
    assert trial_budget_report["effective_trial_count"] == 6
    assert trial_budget_report["bruteforce_equivalent_candidate_count"] == 4
    assert trial_budget_report["sampled_fraction_of_bruteforce"] == 1.0
    assert trial_budget_report["bruteforce_avoidance_ratio"] == 1.0
    assert trial_budget_report["compute_policy"] == performance_plan["compute_policy"]
    assert trial_budget_report["stability_region_acceleration_counters"]["gpu_screened_count"] == 0
    assert trial_budget_report["stability_region_acceleration_counters"]["cpu_validated_count"] == 2
    assert trial_budget_report["trials_by_candidate_source"]["optimizer_search_space"] == 4
    assert trial_budget_report["trials_by_candidate_source"]["no_trade_comparator_injected"] == 1
    assert trial_budget_report["trials_by_candidate_source"]["transparent_default_comparator_injected"] == 1
    assert {record["coverage_status"] for record in candidate_space_manifest["baseline_comparator_coverage"]} == {"complete"}
    assert {"no_trade_comparator_injected", "transparent_default_comparator_injected"} <= set(rankings["candidate_source"])
    assert not {"metadata_default_seed", "metadata_default_search"} & set(rankings["candidate_source"])
    optimizer_rows = rankings.loc[rankings["candidate_source"] == "optimizer_search_space"]
    assert set(optimizer_rows["specified_parameters_json"]) == {
        '{"slope_threshold":0.08,"spacing_bars":8}',
        '{"slope_threshold":0.08,"spacing_bars":12}',
        '{"slope_threshold":0.12,"spacing_bars":8}',
        '{"slope_threshold":0.12,"spacing_bars":12}',
    }
    assert optimizer_rows["resolved_parameters_json"].str.contains("max_choppiness").all()
    assert set(rankings["baseline_comparator_coverage_status"]) == {"complete"}
    assert set(stability_regions["stability_scope"]) == {"candidate_result_region_of_stability"}
    assert "aggregate_only_unvalidated_neighborhood" in set(stability_regions["stability_validation_scope"])
    incomplete_regions = stability_regions.loc[~stability_regions["validation_enriched"]]
    assert set(incomplete_regions["decision"]) == {"rejected_incomplete_validation"}
    assert "rejected_incomplete_validation" in set(stability_regions["decision"])
    assert "not_evaluated_r1_foundation" not in set(stability_regions.get("stability_scope", []))


def test_full_cycle_explicit_vector_backend_writes_backend_evidence(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "cycle_id": "vector-backend-cycle",
        "symbol": "BTCUSDT",
        "output_dir": str(tmp_path / "research" / "historical_cycles" / "vector-backend-cycle"),
        "backtest_backend": "vector_fixed_holding",
        "holding_windows": ["4h"],
        "data": {
            "synthetic_fixture": True,
            "synthetic_row_count": 120,
            "synthetic_variant": "balanced",
        },
        "features": {
            "feature_sets": ["features_price_trend_vol"],
        },
        "strategies": ["trend_following_v1"],
        "validation": {
            "walk_forward": "rolling_and_anchored",
            "purge_embargo_bars": 2,
            "stress_periods_required": True,
            "min_splits": 2,
            "trade_count_floor": 1,
        },
        "optimizer": {
            "method_sequence": ["grid", "stability_region_refine"],
            "max_candidates_per_strategy": 4,
            "top_regions_to_refine": 1,
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
    }
    spec_path = tmp_path / "specs" / "vector-backend-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    backtest_index = pd.read_parquet(result.backtest_index_path)

    assert manifest["backtest_backend_requested"] == "vector_fixed_holding"
    assert manifest["backtest_backend_summary"]["used_counts"] == {"vector_fixed_holding": len(backtest_index)}
    assert manifest["backtest_backend_summary"]["fallback_count"] == 0
    assert manifest["backtest_backend_summary"]["vector_scope_counts"] == {"fixed_holding_primary_bar": len(backtest_index)}
    assert set(backtest_index["backtest_backend_requested"]) == {"vector_fixed_holding"}
    assert set(backtest_index["backtest_backend_used"]) == {"vector_fixed_holding"}
    assert set(backtest_index["backtest_engine_version"]) == {VECTOR_BACKTEST_ENGINE_VERSION}
    assert set(backtest_index["vector_execution_scope"]) == {"fixed_holding_primary_bar"}
    assert set(backtest_index["backtest_backend_fallback_reason"]) == {""}
    assert set(backtest_index["backtest_backend_rejection_reason"]) == {""}
    assert set(rankings["aggregate_backtest_backend_requested"]) == {"vector_fixed_holding"}
    assert set(rankings["aggregate_backtest_backend_used"]) == {"vector_fixed_holding"}
    assert set(rankings["aggregate_backtest_engine_version"]) == {VECTOR_BACKTEST_ENGINE_VERSION}
    assert set(rankings["aggregate_backtest_vector_execution_scope"]) == {"fixed_holding_primary_bar"}
    aggregate_rows = backtest_index.loc[backtest_index["evaluation_scope"] == "aggregate"]
    for row in aggregate_rows.to_dict("records"):
        backtest_manifest = json.loads(Path(str(row["backtest_manifest_path"])).read_text(encoding="utf-8"))
        assert backtest_manifest["engine_version"] == VECTOR_BACKTEST_ENGINE_VERSION
        assert backtest_manifest["reference_engine_version"] == BACKTEST_ENGINE_VERSION
        assert backtest_manifest["vector_execution_scope"] == "fixed_holding_primary_bar"
        ranking_row = rankings.loc[rankings["candidate_id"].astype(str) == str(row["candidate_id"])].iloc[0]
        assert ranking_row["aggregate_backtest_cache_key"] == row["cache_key"]
        assert ranking_row["aggregate_backtest_result_sha256"] == row["result_sha256"]
        assert ranking_row["aggregate_backtest_backend_used"] == row["backtest_backend_used"]
        assert ranking_row["aggregate_backtest_engine_version"] == row["backtest_engine_version"]


def test_cycle_auto_backend_keeps_conservative_vector_route_when_gpu_preferred(tmp_path: Path) -> None:
    dataset = build_hmm_knn_sweep_dataset(row_count=80, variant="balanced")
    common = {
        "run_id": "auto-cuda-routing",
        "symbol": "BTCUSDT",
        "output_dir": tmp_path / "backtests",
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
        "strategy_config": {},
    }
    auto = HistoricalResearchCycleSpec.from_payload(
        {
            "cycle_id": "auto-cuda",
            "data": {"synthetic_fixture": True},
            "strategies": ["baseline_no_trade"],
            "backtest_backend": "auto",
            "compute": {
                "gpu_acceleration": "prefer_nvidia_cuda_when_backend_available",
                "gpu_device_class": "nvidia_50_series",
                "gpu_execution_profile": "conservative",
            },
        },
        spec_path=tmp_path / "auto-cuda.json",
    )

    execution = _run_cycle_backtest(
        cycle_spec=auto,
        reference_engine=BacktestEngine(),
        vector_engine=VectorBacktestEngine(),
        backtest_spec=BacktestSpec(**common),
        dataset=dataset,
    )
    assert execution.backend_evidence["backtest_backend_requested"] == "auto"
    assert execution.backend_evidence["backtest_backend_used"] == "vector_fixed_holding"
    assert execution.backend_evidence["backtest_backend_fallback_reason"] == "gpu_execution_profile_conservative"
    assert execution.backend_evidence["vector_execution_scope"] == "fixed_holding_primary_bar"
    assert execution.backend_evidence["gpu_execution_profile"] == "conservative"


def test_cycle_auto_backend_uses_batched_cuda_only_when_r97_profile_requests_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = build_hmm_knn_sweep_dataset(row_count=80, variant="balanced")
    common = {
        "run_id": "auto-cuda-batched-routing",
        "symbol": "BTCUSDT",
        "output_dir": tmp_path / "backtests",
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
        "strategy_config": {},
    }
    auto = HistoricalResearchCycleSpec.from_payload(
        {
            "cycle_id": "auto-cuda-batched",
            "data": {"synthetic_fixture": True},
            "strategies": ["baseline_no_trade"],
            "backtest_backend": "auto",
            "compute": {
                "gpu_acceleration": "prefer_nvidia_cuda_when_backend_available",
                "gpu_execution_profile": "cuda_exact_batched",
            },
        },
        spec_path=tmp_path / "auto-cuda-batched.json",
    )

    class _FakeBatchedEngine:
        def run(self, spec: BacktestSpec, *, dataset: pd.DataFrame) -> object:
            result = VectorBacktestEngine().run(spec, dataset=dataset)
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            manifest.update(
                {
                    "backend_name": "cuda_batched_fixed_holding",
                    "engine_version": CUDA_BATCHED_BACKTEST_ENGINE_VERSION,
                    "cuda_execution_scope": "cuda_batched_fixed_holding_primary_bar",
                    "cuda_parity_status": "parity_required_before_performance_claim",
                    "gpu_execution_status": "rawkernel_batched_fixed_holding_executed",
                    "gpu_runtime_evidence": {
                        "gpu_name": "Fake RTX 50",
                        "compute_capability": "12.0",
                        "driver_version": 13020,
                        "runtime_version": 12090,
                        "memory_total_bytes": 16,
                        "cupy_version": "fake",
                    },
                }
            )
            result.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
            return result

    monkeypatch.setattr(runner_module, "cuda_batched_backtest_support_reason", lambda _spec: None)

    execution = _run_cycle_backtest(
        cycle_spec=auto,
        reference_engine=BacktestEngine(),
        vector_engine=VectorBacktestEngine(),
        cuda_batched_engine=_FakeBatchedEngine(),  # type: ignore[arg-type]
        backtest_spec=BacktestSpec(**common),
        dataset=dataset,
    )

    assert execution.backend_evidence["backtest_backend_requested"] == "auto"
    assert execution.backend_evidence["backtest_backend_used"] == "cuda_batched_fixed_holding"
    assert execution.backend_evidence["cuda_execution_scope"] == "cuda_batched_fixed_holding_primary_bar"
    assert execution.backend_evidence["backtest_backend_fallback_reason"] == ""
    assert execution.backend_evidence["gpu_execution_profile"] == "cuda_exact_batched"


def test_cycle_auto_backend_required_gpu_fails_without_r97_gpu_profile(tmp_path: Path) -> None:
    dataset = build_hmm_knn_sweep_dataset(row_count=80, variant="balanced")
    spec = HistoricalResearchCycleSpec.from_payload(
        {
            "cycle_id": "required-cuda",
            "data": {"synthetic_fixture": True},
            "strategies": ["baseline_no_trade"],
            "backtest_backend": "auto",
            "compute": {
                "gpu_acceleration": "require_nvidia_cuda_backend",
                "gpu_device_class": "nvidia_50_series",
                "gpu_execution_profile": "conservative",
            },
        },
        spec_path=tmp_path / "required-cuda.json",
    )

    with pytest.raises(ValueError, match="gpu_execution_profile_not_enabled"):
        _run_cycle_backtest(
            cycle_spec=spec,
            reference_engine=BacktestEngine(),
            vector_engine=VectorBacktestEngine(),
            backtest_spec=BacktestSpec(
                run_id="required-cuda",
                symbol="BTCUSDT",
                output_dir=tmp_path / "backtests",
                strategy_id="baseline_no_trade",
                holding_window="1h",
                feature_set_id="features_price_trend_vol",
                strategy_config={},
            ),
            dataset=dataset,
        )


def test_cycle_required_cuda_rejects_explicit_cpu_backend(tmp_path: Path) -> None:
    dataset = build_hmm_knn_sweep_dataset(row_count=80, variant="balanced")
    spec = HistoricalResearchCycleSpec.from_payload(
        {
            "cycle_id": "required-cuda-cpu-backend",
            "data": {"synthetic_fixture": True},
            "strategies": ["baseline_no_trade"],
            "backtest_backend": "reference",
            "compute": {
                "gpu_acceleration": "require_nvidia_cuda_backend",
                "gpu_required": True,
            },
        },
        spec_path=tmp_path / "required-cuda-cpu-backend.json",
    )

    with pytest.raises(ValueError, match="cuda_required_backend_not_selectable"):
        _run_cycle_backtest(
            cycle_spec=spec,
            reference_engine=BacktestEngine(),
            vector_engine=VectorBacktestEngine(),
            backtest_spec=BacktestSpec(
                run_id="required-cuda-cpu-backend",
                symbol="BTCUSDT",
                output_dir=tmp_path / "backtests",
                strategy_id="baseline_no_trade",
                holding_window="1h",
                feature_set_id="features_price_trend_vol",
                strategy_config={},
            ),
            dataset=dataset,
        )


def test_full_cycle_explicit_exit_policy_candidates_write_identity_evidence(tmp_path: Path) -> None:
    payload: dict[str, object] = {
        "cycle_id": "exit-policy-cycle",
        "symbol": "BTCUSDT",
        "output_dir": str(tmp_path / "research" / "historical_cycles" / "exit-policy-cycle"),
        "holding_windows": ["4h"],
        "data": {
            "synthetic_fixture": True,
            "synthetic_row_count": 120,
            "synthetic_variant": "balanced",
        },
        "features": {
            "feature_sets": ["features_price_trend_vol"],
        },
        "strategies": ["trend_following_v1"],
        "exit_policies": [
            "fixed_holding_window",
            {
                "exit_policy_id": "max_mae_stop",
                "stop_return": 0.01,
                "exit_policy_params": {"stop_return": 0.01},
            },
        ],
        "validation": {
            "walk_forward": "rolling_and_anchored",
            "purge_embargo_bars": 2,
            "stress_periods_required": True,
            "min_splits": 2,
            "trade_count_floor": 1,
        },
        "optimizer": {
            "max_candidates_per_strategy": 4,
            "top_regions_to_refine": 1,
        },
    }
    spec_path = tmp_path / "specs" / "exit-policy-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    candidate_space_manifest = json.loads(Path(manifest["required_outputs"]["candidate_space_manifest"]).read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    backtest_index = pd.read_parquet(result.backtest_index_path)

    assert manifest["candidate_count"] == 12
    assert [policy["exit_policy_id"] for policy in candidate_space_manifest["exit_policies"]] == [
        "fixed_holding_window",
        "max_mae_stop",
    ]
    assert {record["coverage_status"] for record in candidate_space_manifest["baseline_comparator_coverage"]} == {"complete"}
    assert {record["holding_window"] for record in candidate_space_manifest["baseline_comparator_coverage"]} == {"4h"}
    assert {record["exit_policy_id"] for record in candidate_space_manifest["baseline_comparator_coverage"]} == {
        "fixed_holding_window",
        "max_mae_stop",
    }
    assert '{"stop_return":0.01}' in {
        record["exit_policy_params_json"]
        for record in candidate_space_manifest["baseline_comparator_coverage"]
    }
    assert set(rankings["exit_policy_id"]) == {"fixed_holding_window", "max_mae_stop"}
    assert '{"stop_return":0.01}' in set(rankings["exit_policy_params_json"])
    assert set(backtest_index["exit_policy_id"]) == {"fixed_holding_window", "max_mae_stop"}
    max_mae_rows = backtest_index.loc[backtest_index["exit_policy_id"] == "max_mae_stop"]
    assert not max_mae_rows.empty
    assert set(max_mae_rows["exit_policy_params_json"]) == {'{"stop_return":0.01}'}
    aggregate_rows = backtest_index.loc[backtest_index["evaluation_scope"] == "aggregate"]
    for row in aggregate_rows.to_dict("records"):
        backtest_manifest = json.loads(Path(str(row["backtest_manifest_path"])).read_text(encoding="utf-8"))
        assert backtest_manifest["exit_policy_id"] == row["exit_policy_id"]
        ranking_row = rankings.loc[rankings["candidate_id"].astype(str) == str(row["candidate_id"])].iloc[0]
        assert ranking_row["exit_policy_id"] == row["exit_policy_id"]
        assert ranking_row["exit_policy_params_json"] == row["exit_policy_params_json"]


def test_cycle_backtest_backend_resolver_fails_or_falls_back_for_unsupported_vector_scope(tmp_path: Path) -> None:
    dataset = build_hmm_knn_sweep_dataset(row_count=80, variant="balanced")
    lower_path = tmp_path / "lower.parquet"
    dataset.to_parquet(lower_path, index=False)
    common = {
        "run_id": "unsupported-vector-scope",
        "symbol": "BTCUSDT",
        "output_dir": tmp_path / "backtests",
        "strategy_id": "baseline_no_trade",
        "holding_window": "1h",
        "feature_set_id": "features_price_trend_vol",
        "entry_price_source": "lower_timeframe_execution_path",
        "lower_timeframe_dataset_path": lower_path,
        "strategy_config": {},
    }
    explicit_vector = HistoricalResearchCycleSpec.from_payload(
        {
            "cycle_id": "explicit-vector",
            "data": {"synthetic_fixture": True},
            "strategies": ["baseline_no_trade"],
            "backtest_backend": "vector_fixed_holding",
        },
        spec_path=tmp_path / "explicit-vector.json",
    )
    auto = HistoricalResearchCycleSpec.from_payload(
        {
            "cycle_id": "auto-vector",
            "data": {"synthetic_fixture": True},
            "strategies": ["baseline_no_trade"],
            "backtest_backend": "auto",
        },
        spec_path=tmp_path / "auto-vector.json",
    )

    with pytest.raises(ValueError, match="backtest_backend_vector_fixed_holding_unsupported:vector_engine_lower_timeframe_not_supported"):
        _run_cycle_backtest(
            cycle_spec=explicit_vector,
            reference_engine=BacktestEngine(),
            vector_engine=VectorBacktestEngine(),
            backtest_spec=BacktestSpec(**common),
            dataset=dataset,
        )

    execution = _run_cycle_backtest(
        cycle_spec=auto,
        reference_engine=BacktestEngine(),
        vector_engine=VectorBacktestEngine(),
        backtest_spec=BacktestSpec(**{**common, "run_id": "auto-fallback"}),
        dataset=dataset,
    )

    assert execution.backend_evidence["backtest_backend_requested"] == "auto"
    assert execution.backend_evidence["backtest_backend_used"] == "reference"
    assert execution.backend_evidence["backtest_backend_fallback_reason"] == (
        "cuda_batched_engine_scope_unsupported:vector_engine_lower_timeframe_not_supported;"
        "vector_engine_lower_timeframe_not_supported"
    )
    assert execution.backend_evidence["backtest_engine_version"] == BACKTEST_ENGINE_VERSION


def test_triple_barrier_cycle_rejects_bad_explicit_lower_timeframe_dataset(tmp_path: Path) -> None:
    lower_path = tmp_path / "bad_lower_timeframe.parquet"
    pd.DataFrame({"event_time_ms": [1, 2], "symbol": ["BTCUSDT", "BTCUSDT"], "value": [1.0, 2.0]}).to_parquet(lower_path, index=False)
    spec_path = tmp_path / "specs" / "bad-lower-timeframe-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "cycle_id": "bad-lower-timeframe-cycle",
                "symbol": "BTCUSDT",
                "output_dir": str(tmp_path / "research" / "historical_cycles" / "bad-lower-timeframe-cycle"),
                "holding_windows": ["4h"],
                "data": {
                    "synthetic_fixture": True,
                    "synthetic_row_count": 96,
                    "lower_timeframe_dataset_path": str(lower_path),
                },
                "features": {
                    "feature_sets": ["features_price_trend_vol"],
                },
                "strategies": ["trend_following_v1"],
                "exit_policies": [
                    {
                        "exit_policy_id": "triple_barrier",
                        "target_return": 0.002,
                        "stop_return": 0.002,
                    }
                ],
                "optimizer": {
                    "max_candidates_per_strategy": 1,
                    "top_regions_to_refine": 1,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="lower_timeframe_dataset_missing_columns:bar_time_ms,close,high,low"):
        run_historical_research_cycle(
            spec_path=spec_path,
            app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
        )


def test_historical_research_cycle_cli_command_runs(tmp_path: Path) -> None:
    spec_path = _write_cycle_spec(tmp_path)
    args = argparse.Namespace(spec=str(spec_path))

    payload = main._run_historical_research_cycle_command(args)

    assert Path(str(payload["research_cycle_manifest_path"])).exists()
    assert Path(str(payload["candidate_rankings_path"])).exists()


def test_historical_research_cycle_cli_resolves_repo_relative_spec(monkeypatch, tmp_path: Path) -> None:
    observed: dict[str, Path] = {}
    output_dir = tmp_path / "cli-relative-output"
    output_dir.mkdir()
    manifest_path = output_dir / "research_cycle_manifest.json"
    rankings_path = output_dir / "candidate_rankings.parquet"
    backtest_index_path = output_dir / "backtest_index.parquet"
    rejection_report_path = output_dir / "rejection_report.md"
    for path in (manifest_path, rankings_path, backtest_index_path, rejection_report_path):
        path.write_text("{}", encoding="utf-8")

    def fake_run_historical_research_cycle(*, spec_path, app_config):
        observed["spec_path"] = Path(spec_path)
        return SimpleNamespace(
            output_dir=output_dir,
            manifest_path=manifest_path,
            candidate_rankings_path=rankings_path,
            backtest_index_path=backtest_index_path,
            rejection_report_path=rejection_report_path,
        )

    monkeypatch.setattr(main, "run_historical_research_cycle", fake_run_historical_research_cycle)
    args = argparse.Namespace(spec="configs/research/full_cycle_btcusdt_perp_context_v2.json")

    payload = main._run_historical_research_cycle_command(args)

    assert observed["spec_path"] == (main.REPO_ROOT / args.spec).resolve()
    assert Path(str(payload["research_cycle_manifest_path"])).exists()
