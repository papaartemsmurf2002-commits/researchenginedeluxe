from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.promotion.artifact_validator import validate_artifact_for_live_input, validate_artifact_for_runtime_mode
from tradingbotsuite.research_artifacts import (
    RESEARCH_CANDIDATE_PACK_VERSION,
    evaluate_research_candidate_gate,
    validate_research_candidate_pack_manifest,
    write_research_candidate_pack,
)

REQUIRED_COST_STRESS_SCENARIOS = (
    "base_costs",
    "slippage_2x",
    "slippage_3x",
    "adverse_funding_shock",
    "wide_spread_stress",
    "missing_optional_context_stress",
    "high_volatility_only",
    "low_volatility_only",
    "trend_only",
    "range_only",
    "shock_transition_only",
)
REMOVED_CHART_SOURCE = "trading" + "view"
REMOVED_CHART_SOURCE_FLAG = REMOVED_CHART_SOURCE + "_source_used"
PUBLIC_ARCHIVE_PROVIDER_CAPABILITY = {
    "registry_version": "provider-capability-registry-v1",
    "source_name": "binance_vision",
    "data_family": "kline",
    "durability_class": "public_archive_partition",
    "retention_limit": "downloaded_public_archive_partition",
    "history_start": "source_partition_dependent",
    "exchange_native": True,
    "normalized": True,
    "health_policy": "checksum_gap_duplicate_evidence_required_for_durable_claims",
    "diagnostic_only_by_default": False,
    "candidate_ready_default": False,
}
DURABLE_PUBLIC_ARCHIVE_READY = {
    "ready": True,
    "status": "durable_public_archive_ready",
    "reasons": [],
    "fixture_id": "btcusdt-local-offline-v1",
    "symbol": "BTCUSDT",
    "base_interval": "15m",
    "required_families": ["bars", "lower_timeframe_bars", "agg_trade"],
    "durable_context_families": ["agg_trade"],
    "diagnostic_context_families": [],
    "research_only": True,
    "observe_only": True,
    "promotion_ready": False,
}


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cost_stress_fixture_rows(candidate_id: str, root: Path) -> list[dict[str, object]]:
    scenario_params = {
        "base_costs": ("cost", 5.0, 5.0, 0.0, 0.0),
        "slippage_2x": ("cost", 5.0, 10.0, 0.0, 0.0),
        "slippage_3x": ("cost", 5.0, 15.0, 0.0, 0.0),
        "adverse_funding_shock": ("funding", 5.0, 5.0, 0.0, 0.00005),
        "wide_spread_stress": ("spread", 5.0, 5.0, 25.0, 0.0),
        "missing_optional_context_stress": ("feature_context", 5.0, 5.0, 0.0, 0.0),
        "high_volatility_only": ("volatility", 5.0, 5.0, 0.0, 0.0),
        "low_volatility_only": ("volatility", 5.0, 5.0, 0.0, 0.0),
        "trend_only": ("regime", 5.0, 5.0, 0.0, 0.0),
        "range_only": ("regime", 5.0, 5.0, 0.0, 0.0),
        "shock_transition_only": ("shock", 5.0, 5.0, 0.0, 0.0),
    }
    manifest_path = root / "backtests" / "candidate-1" / "cost_stress" / "backtest_manifest.json"
    rows: list[dict[str, object]] = []
    for index, scenario_id in enumerate(REQUIRED_COST_STRESS_SCENARIOS):
        scenario_group, fee_bps, slippage_bps, spread_bps, funding_rate = scenario_params[scenario_id]
        stressed_expectancy = 0.01 - (index * 0.0001)
        stressed_net_return = 0.02 - (index * 0.0001)
        stress_survival_score = stressed_expectancy + stressed_net_return
        rows.append(
            {
                "candidate_id": candidate_id,
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "scenario_id": scenario_id,
                "scenario_group": scenario_group,
                "scenario_filter": None,
                "scenario_transform": None,
                "fee_bps": fee_bps,
                "slippage_bps": slippage_bps,
                "spread_bps": spread_bps,
                "funding_rate": funding_rate,
                "source_row_count": 96,
                "stress_dataset_sha256": f"stress-dataset-{index}",
                "scenario_status": "evaluated",
                "trade_count": 5,
                "stressed_expectancy": stressed_expectancy,
                "stressed_net_return": stressed_net_return,
                "stress_survival_score": stress_survival_score,
                "stress_survival_status": "passed",
                "backtest_manifest_path": str(manifest_path),
            }
        )
    return rows


def _cycle_outputs(
    tmp_path: Path,
    *,
    synthetic: bool = False,
    live_adjacent: bool = False,
    lower_timeframe: bool = False,
) -> Path:
    root = tmp_path / "cycle"
    root.mkdir(parents=True, exist_ok=True)
    candidate_id = "candidate-1"
    fixture_dataset_path = root / "fixture_dataset.parquet"
    pd.DataFrame(
        [
            {
                "signal_bar_time_ms": 1,
                "symbol": "BTCUSDT",
                "signal_bar_open": 100.0,
                "signal_bar_high": 101.0,
                "signal_bar_low": 99.0,
                "signal_bar_close": 100.5,
                "signal_bar_volume": 10.0,
            }
        ]
    ).to_parquet(fixture_dataset_path, index=False)
    lower_timeframe_path = root / "lower_timeframe_bars.parquet"
    lower_timeframe_sha256: str | None = None
    if lower_timeframe:
        pd.DataFrame(
            [
                {
                    "bar_time_ms": 2,
                    "symbol": "BTCUSDT",
                    "open": 100.0,
                    "high": 103.0,
                    "low": 99.5,
                    "close": 102.0,
                },
                {
                    "bar_time_ms": 3,
                    "symbol": "BTCUSDT",
                    "open": 102.0,
                    "high": 102.5,
                    "low": 98.0,
                    "close": 99.0,
                },
            ]
        ).to_parquet(lower_timeframe_path, index=False)
        lower_timeframe_sha256 = _file_sha256(lower_timeframe_path)
    exit_policy_id = "triple_barrier_atr" if lower_timeframe else "fixed_holding_window"
    exit_price_source = "lower_timeframe_ohlc_sequence" if lower_timeframe else "primary_close"
    lower_timeframe_evidence = {
        "lower_timeframe_family_present": lower_timeframe,
        "lower_timeframe_dataset_path": str(lower_timeframe_path) if lower_timeframe else None,
        "lower_timeframe_dataset_sha256": lower_timeframe_sha256,
        "lower_timeframe_row_count": 2 if lower_timeframe else None,
        "lower_timeframe_family": (
            {
                "path": str(lower_timeframe_path),
                "sha256": lower_timeframe_sha256,
                "row_count": 2,
                "columns": ["bar_time_ms", "symbol", "open", "high", "low", "close"],
                "interval": "1m",
                "event_time_field": "bar_time_ms",
                "data_family": "lower_timeframe_bars",
                "required": True,
            }
            if lower_timeframe
            else {}
        ),
    }
    fixture_manifest = _write_json(
        root / "fixture_pack_manifest.json",
        {
            "manifest_version": "historical-fixture-pack-manifest-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "fixture_id": "btcusdt-local-offline-v1",
            "fixture_scope": "unit_fixture_not_oos_acceptance_evidence",
            "source": {
                "source_name": "binance_vision",
                "source_raw": "binance_vision_klines",
                "data_family": "kline",
                "provider_capability": dict(PUBLIC_ARCHIVE_PROVIDER_CAPABILITY),
            },
            "derivation": {
                REMOVED_CHART_SOURCE_FLAG: False,
                "synthetic_source_used": False,
                "derivation_type": "unit_test_fixture",
            },
            "omitted_optional_families": {
                "funding_rate": "not_present_in_unit_fixture",
                "premium_index": "not_present_in_unit_fixture",
            },
            "research_evidence_limitations": ["not_sufficient_for_oos_acceptance"],
        },
    )
    cycle_spec = _write_json(
        root / "cycle_spec_resolved.json",
        {
            "cycle_id": "candidate-pack-cycle",
            "symbol": "BTCUSDT",
            "validation": {
                "trade_count_floor": 2,
                "max_single_split_pnl_share": 0.5,
                "min_cost_stress_survival_rate": 1.0,
            },
        },
    )
    for name in ("data_quality_report", "feature_build_manifest"):
        _write_json(root / f"{name}.json", {"research_only": True, "observe_only": True, "promotion_ready": False})
    _write_json(
        root / "split_manifest.json",
        {
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "split_count": 2,
            "validation_method": "purged_embargoed_walk_forward",
            "validation_methods": ["purged_embargoed_walk_forward"],
            "validation_method_counts": {"purged_embargoed_walk_forward": 2},
            "split_mode_counts": {"anchored": 2},
        },
    )
    ablation = _write_json(
        root / "ablation_report.json",
        (
            {"promotion_candidate_manifest_version": "promotion-candidate-v1"}
            if live_adjacent
            else {
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "candidate_rows": [
                    {
                        "candidate_id": candidate_id,
                        "strategy_id": "trend_following_v1",
                        "feature_set_id": "features_price_trend_vol",
                        "holding_window": "4h",
                        "feature_ablation_required": False,
                        "feature_ablation_passed": True,
                        "ablation_evidence_status": "baseline_feature_set_no_optional_claim",
                        "ablation_comparator_feature_set_id": None,
                        "ablation_comparator_candidate_id": None,
                        "ablation_expectancy_delta": None,
                        "ablation_final_score_delta": None,
                        "ablation_failure_reasons": "",
                    }
                ],
            }
        ),
    )
    trial_budget = _write_json(
        root / "trial_budget_report.json",
        {
            "trial_budget_report_version": "trial-budget-report-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "diagnostic_only": True,
            "candidate_pack_metric_gate_enabled": False,
            "effective_trial_count": 1,
            "candidate_counts": {"candidate_count": 1, "comparator_candidate_count": 0},
        },
    )
    overfit_adjustment = _write_json(
        root / "overfit_adjustment_report.json",
        {
            "overfit_adjustment_report_version": "overfit-adjustment-report-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "hard_gate_enabled": False,
            "candidate_pack_gate_enabled": False,
            "candidate_diagnostics": [
                {
                    "candidate_id": candidate_id,
                    "overfit_adjusted_score": 0.01,
                    "diagnostic_status": "clear",
                    "adjustment_scope": "diagnostic_only_not_candidate_gate",
                }
            ],
        },
    )
    rankings = pd.DataFrame(
        [
            {
                "candidate_id": candidate_id,
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "exit_policy_id": exit_policy_id,
                "aggregate_backtest_exit_price_source": exit_price_source,
                "aggregate_backtest_lower_timeframe_required": lower_timeframe,
                "aggregate_backtest_lower_timeframe_dataset_path": str(lower_timeframe_path) if lower_timeframe else None,
                "aggregate_backtest_lower_timeframe_dataset_sha256": lower_timeframe_sha256,
                "aggregate_backtest_lower_timeframe_sequence_used": lower_timeframe,
                "aggregate_backtest_lower_timeframe_cache_key_component": lower_timeframe_sha256,
                "empirical_evidence": True,
                "data_evidence_scope": "synthetic_fixture" if synthetic else "local_historical_fixture",
                "split_evaluated": True,
                "cost_stress_evaluated": True,
                "stability_evaluated": True,
                "stability_validation_scope": "split_cost_stress_enriched",
                "split_evaluation_count": 2,
                "cost_stress_evaluation_count": len(REQUIRED_COST_STRESS_SCENARIOS),
                "required_split_count": 2,
                "required_cost_stress_count": len(REQUIRED_COST_STRESS_SCENARIOS),
                "trade_count": 5,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.02,
                "split_consistency": 0.5,
                "cost_stress_survival": 1.0,
                "baseline_comparator_coverage_status": "complete",
                "expectancy_vs_no_trade": 0.01,
                "side_evidence_status": "complete",
                "side_evidence_count": 2,
                "side_evidence_sides": "long|short",
                "side_evidence_exception": False,
                "regime_evidence_status": "complete",
                "regime_evidence_count": 2,
                "regime_evidence_regimes": "downtrend|uptrend",
                "cost_stress_scenario_count": len(REQUIRED_COST_STRESS_SCENARIOS),
                "cost_stress_scenario_status": "complete",
                "cost_stress_scenarios": "|".join(sorted(REQUIRED_COST_STRESS_SCENARIOS)),
                "cost_stress_survival_floor": 1.0,
                "cost_stress_survival_rate": 1.0,
                "cost_stress_survival_floor_status": "passed",
                "cost_stress_failed_scenarios": "",
                "split_trade_count_floor": 2,
                "min_split_trade_count": 2,
                "split_trade_count_floor_status": "passed",
                "split_validation_method_status": "complete",
                "split_validation_methods": "purged_embargoed_walk_forward",
                "split_missing_validation_methods": "",
                "max_single_split_pnl_share": 0.5,
                "split_dominance_status": "complete",
                "feature_ablation_required": False,
                "feature_ablation_passed": True,
                "ablation_evidence_status": "baseline_feature_set_no_optional_claim",
                "ablation_comparator_feature_set_id": None,
                "ablation_comparator_candidate_id": None,
                "ablation_expectancy_delta": None,
                "ablation_final_score_delta": None,
                "ablation_failure_reasons": "",
                "optimizer_final_score": 0.2,
                "decision": "research_gate_passed",
                "failure_reasons": "",
            }
        ]
    )
    rankings_path = root / "candidate_rankings.parquet"
    rankings.to_parquet(rankings_path, index=False)
    split_metrics_path = root / "metrics_by_split.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": candidate_id,
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "split_id": "split-1",
                "validation_method": "purged_embargoed_walk_forward",
                "trade_count": 2,
                "trade_count_floor": 2,
                "trade_count_floor_status": "passed",
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.01,
                "max_drawdown": -0.001,
                "backtest_manifest_path": str(root / "backtests" / "candidate-1" / "walk_forward_split" / "backtest_manifest.json"),
            },
            {
                "candidate_id": candidate_id,
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "split_id": "split-2",
                "validation_method": "purged_embargoed_walk_forward",
                "trade_count": 3,
                "trade_count_floor": 2,
                "trade_count_floor_status": "passed",
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.01,
                "max_drawdown": -0.001,
                "backtest_manifest_path": str(root / "backtests" / "candidate-1" / "walk_forward_split" / "backtest_manifest.json"),
            },
        ]
    ).to_parquet(split_metrics_path, index=False)
    cost_metrics_path = root / "metrics_by_cost_stress.parquet"
    pd.DataFrame(_cost_stress_fixture_rows(candidate_id, root)).to_parquet(cost_metrics_path, index=False)
    stability_path = root / "stability_regions.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": candidate_id,
                "stability_scope": "candidate_result_region_of_stability",
                "decision": "accepted_region",
                "validation_enriched": True,
                "stability_validation_scope": "split_cost_stress_enriched",
            }
        ]
    ).to_parquet(stability_path, index=False)
    candidate_gate_report_path = root / "candidate_gate_report.parquet"
    pd.DataFrame(
        [
            {
                "candidate_id": candidate_id,
                "gate_status": "passed",
                "pack_eligible": True,
                "gate_reasons": "",
            }
        ]
    ).to_parquet(candidate_gate_report_path, index=False)
    pd.DataFrame(
        [
            {
                "candidate_id": candidate_id,
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "regime": "uptrend",
                "trade_count": 3,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.015,
                "hit_rate": 0.67,
                "backtest_manifest_path": str(root / "backtests" / "candidate-1" / "aggregate" / "backtest_manifest.json"),
            },
            {
                "candidate_id": candidate_id,
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "regime": "downtrend",
                "trade_count": 2,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.005,
                "hit_rate": 0.5,
                "backtest_manifest_path": str(root / "backtests" / "candidate-1" / "aggregate" / "backtest_manifest.json"),
            },
        ]
    ).to_parquet(root / "metrics_by_regime.parquet", index=False)
    pd.DataFrame(
        [
            {
                "candidate_id": candidate_id,
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "side": "long",
                "trade_count": 3,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.015,
                "hit_rate": 0.67,
                "backtest_manifest_path": str(root / "backtests" / "candidate-1" / "aggregate" / "backtest_manifest.json"),
            },
            {
                "candidate_id": candidate_id,
                "strategy_id": "trend_following_v1",
                "feature_set_id": "features_price_trend_vol",
                "holding_window": "4h",
                "side": "short",
                "trade_count": 2,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.005,
                "hit_rate": 0.5,
                "backtest_manifest_path": str(root / "backtests" / "candidate-1" / "aggregate" / "backtest_manifest.json"),
            },
        ]
    ).to_parquet(root / "metrics_by_side.parquet", index=False)
    pd.DataFrame([{"candidate_id": candidate_id, "holding_window": "4h"}]).to_parquet(root / "metrics_by_holding_window.parquet", index=False)
    backtest_records: list[dict[str, object]] = []
    for scope in ("aggregate", "walk_forward_split", "cost_stress"):
        backtest_manifest = _write_json(
            root / "backtests" / "candidate-1" / scope / "backtest_manifest.json",
            {
                "backtest_manifest_version": "backtest-manifest-v1",
                "research_only": True,
                "observe_only": True,
                "promotion_ready": False,
                "evaluation_scope": scope,
                "exit_policy_id": exit_policy_id,
                "exit_price_source": exit_price_source,
                "lower_timeframe_dataset_path": str(lower_timeframe_path) if lower_timeframe else None,
                "lower_timeframe_dataset_sha256": lower_timeframe_sha256,
                "cache_key_components": {
                    "lower_timeframe_dataset_sha256": lower_timeframe_sha256,
                },
                "cache_policy": "identity_only_no_execution_cache",
                "cache_lookup_used": False,
                "cache_hit": False,
                "execution_cache_reuse_enabled": False,
            },
        )
        metrics_json = _write_json(root / "backtests" / "candidate-1" / scope / "metrics.json", {"trade_count": 5, "evaluation_scope": scope})
        backtest_records.append(
            {
                "candidate_id": candidate_id,
                "evaluation_scope": scope,
                "exit_policy_id": exit_policy_id,
                "exit_price_source": exit_price_source,
                "lower_timeframe_required": lower_timeframe,
                "lower_timeframe_sequence_used": lower_timeframe,
                "lower_timeframe_dataset_path": str(lower_timeframe_path) if lower_timeframe else None,
                "lower_timeframe_dataset_sha256": lower_timeframe_sha256,
                "lower_timeframe_cache_key_component": lower_timeframe_sha256,
                "trade_count": 5,
                "exit_sequence_proof_counts_json": (
                    json.dumps({"lower_timeframe_ohlc": 5}, sort_keys=True)
                    if lower_timeframe
                    else "{}"
                ),
                "barrier_hit_type_counts_json": (
                    json.dumps({"target": 3, "stop": 2}, sort_keys=True)
                    if lower_timeframe
                    else "{}"
                ),
                "exit_price_source_counts_json": (
                    json.dumps({"lower_timeframe_ohlc_sequence": 5}, sort_keys=True)
                    if lower_timeframe
                    else "{}"
                ),
                "backtest_manifest_path": str(backtest_manifest),
                "metrics_path": str(metrics_json),
            }
        )
    backtest_index_path = root / "backtest_index.parquet"
    pd.DataFrame(backtest_records).to_parquet(backtest_index_path, index=False)
    rejection_report = root / "rejection_report.md"
    rejection_report.write_text("research-only rejection report\n", encoding="utf-8")
    cycle_manifest = root / "research_cycle_manifest.json"
    _write_json(
        cycle_manifest,
        {
            "research_cycle_manifest_version": "historical-research-cycle-manifest-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
            "live_signal_input": False,
            "position_sizing_input": False,
            "operator_control_input": False,
            "live_execution_input": False,
            "runtime_control_input": False,
            "live_fetch_used": False,
            "order_placement_used": False,
            "cycle_id": "candidate-pack-cycle",
            "symbol": "BTCUSDT",
            "data_source": {
                "source_type": "historical_fixture_pack",
                "fixture_id": "btcusdt-local-offline-v1",
                "fixture_scope": "unit_fixture_not_oos_acceptance_evidence",
                "fixture_source": {
                    "source_name": "binance_vision",
                    "source_raw": "binance_vision_klines",
                    "data_family": "kline",
                    "provider_capability": dict(PUBLIC_ARCHIVE_PROVIDER_CAPABILITY),
                },
                "provider_capability": dict(PUBLIC_ARCHIVE_PROVIDER_CAPABILITY),
                "durable_public_archive_readiness": dict(DURABLE_PUBLIC_ARCHIVE_READY),
                "fixture_derivation": {
                    REMOVED_CHART_SOURCE_FLAG: False,
                    "synthetic_source_used": False,
                    "derivation_type": "unit_test_fixture",
                },
                "omitted_optional_families": {
                    "funding_rate": "not_present_in_unit_fixture",
                    "premium_index": "not_present_in_unit_fixture",
                },
                "research_evidence_limitations": ["not_sufficient_for_oos_acceptance"],
                "manifest_path": str(fixture_manifest),
                "manifest_sha256": _file_sha256(fixture_manifest),
                "dataset_path": str(fixture_dataset_path),
                "synthetic": False,
                **lower_timeframe_evidence,
                "validation": {
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                    "fixture_id": "btcusdt-local-offline-v1",
                    "row_count": 1,
                    "lower_timeframe_dataset_path": str(lower_timeframe_path) if lower_timeframe else None,
                    "lower_timeframe_row_count": 2 if lower_timeframe else None,
                    "lower_timeframe_family": lower_timeframe_evidence["lower_timeframe_family"],
                },
            },
            "lower_timeframe_evidence": lower_timeframe_evidence,
            "required_outputs": {
                "research_cycle_manifest": str(cycle_manifest),
                "cycle_spec_resolved": str(cycle_spec),
                "data_quality_report": str(root / "data_quality_report.json"),
                "feature_build_manifest": str(root / "feature_build_manifest.json"),
                "split_manifest": str(root / "split_manifest.json"),
                "candidate_rankings": str(rankings_path),
                "candidate_gate_report": str(candidate_gate_report_path),
                "backtest_index": str(backtest_index_path),
                "metrics_by_split": str(split_metrics_path),
                "metrics_by_cost_stress": str(cost_metrics_path),
                "metrics_by_regime": str(root / "metrics_by_regime.parquet"),
                "metrics_by_side": str(root / "metrics_by_side.parquet"),
                "metrics_by_holding_window": str(root / "metrics_by_holding_window.parquet"),
                "stability_regions": str(stability_path),
                "ablation_report": str(ablation),
                "trial_budget_report": str(trial_budget),
                "overfit_adjustment_report": str(overfit_adjustment),
                "rejection_report": str(rejection_report),
            },
        },
    )
    return cycle_manifest


def test_research_candidate_pack_is_research_only_and_rejected_for_live_input(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)

    result = write_research_candidate_pack(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    live_validation = validate_artifact_for_live_input(manifest, manifest_path=result.manifest_path)
    runtime_validation = validate_artifact_for_runtime_mode(
        manifest,
        runtime_mode=RuntimeMode.LIVE,
        manifest_path=result.manifest_path,
    )

    assert manifest["research_candidate_pack_manifest_version"] == RESEARCH_CANDIDATE_PACK_VERSION
    assert "promotion_candidate_manifest_version" not in manifest
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["operator_control_input"] is False
    assert manifest["runtime_control_input"] is False
    assert manifest["live_fetch_used"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["research_gate_status"] == "passed"
    source = manifest["source_data_evidence"]
    assert source["source_type"] == "historical_fixture_pack"
    assert source["synthetic"] is False
    assert source["fixture_id"] == "btcusdt-local-offline-v1"
    assert source["fixture_scope"] == "unit_fixture_not_oos_acceptance_evidence"
    assert source["fixture_source"] == source["fixture_manifest_source"]
    assert source["fixture_derivation"] == source["fixture_manifest_derivation"]
    assert source["fixture_manifest_scope"] == "unit_fixture_not_oos_acceptance_evidence"
    assert source["fixture_source_matches_manifest"] is True
    assert source["fixture_derivation_matches_manifest"] is True
    assert source["fixture_scope_matches_manifest"] is True
    assert source["fixture_omitted_optional_families_matches_manifest"] is True
    assert source["fixture_research_evidence_limitations_match_manifest"] is True
    assert source["fixture_source"]["source_name"] == "binance_vision"
    assert source["provider_capability"]["candidate_ready_default"] is False
    assert source["durable_public_archive_readiness"]["ready"] is True
    assert source["source_capability_gate_reasons"] == []
    assert source["fixture_derivation"][REMOVED_CHART_SOURCE_FLAG] is False
    assert source["fixture_derivation"]["synthetic_source_used"] is False
    assert source["omitted_optional_families"] == source["fixture_manifest_omitted_optional_families"]
    assert source["research_evidence_limitations"] == source["fixture_manifest_research_evidence_limitations"]
    assert source["validation"]["valid"] is True
    assert source["manifest_sha256"] == _file_sha256(Path(source["manifest_path"]))
    assert source["manifest_sha256_verified"] is True
    assert source["fixture_manifest_safe"] is True
    assert source["fixture_manifest_fixture_id_matches"] is True
    assert source["dataset_exists"] is True
    assert source["evidence_complete"] is True
    assert manifest["evidence_summary"]["artifact_count"] == len(manifest["evidence"])
    assert "candidate_backtest_manifest:aggregate" in manifest["evidence_summary"]["artifact_names"]
    assert live_validation.allowed is False
    assert runtime_validation.allowed is False
    assert "research_only_artifact_rejected_for_live_input" in live_validation.reasons
    assert "research_only_artifact_rejected_for_live_input" in runtime_validation.reasons


def test_research_candidate_gate_rebases_migrated_cycle_required_outputs(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    cycle_root = cycle_manifest.parent.resolve()
    stale_root = Path(r"C:\Users\papaa\Music\tradingbotsuite\unit-test-cycle-portability") / cycle_root.name
    migrated_outputs: dict[str, str] = {}
    for key, raw_path in dict(manifest["required_outputs"]).items():
        current_path = Path(str(raw_path)).resolve()
        migrated_outputs[key] = str(stale_root / current_path.relative_to(cycle_root))
    manifest["required_outputs"] = migrated_outputs
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.passed
    assert not any("required_output_path_missing" in reason for reason in gate.reasons)


def test_research_candidate_pack_treats_overfit_reports_as_diagnostics(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    overfit_path = Path(manifest["required_outputs"]["overfit_adjustment_report"])
    overfit = json.loads(overfit_path.read_text(encoding="utf-8"))
    overfit["candidate_diagnostics"][0]["diagnostic_status"] = "review"
    overfit["candidate_diagnostics"][0]["diagnostic_reasons"] = "weak_family_rank_proxy"
    overfit["candidate_diagnostics"][0]["pbo"] = 1.0
    overfit_path.write_text(json.dumps(overfit, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "passed"
    assert not any("overfit" in reason for reason in gate.reasons)


def test_research_candidate_pack_includes_lower_timeframe_source_evidence(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path, lower_timeframe=True)

    result = write_research_candidate_pack(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    lower = manifest["source_data_evidence"]["lower_timeframe_evidence"]
    assert lower["family_present"] is True
    assert lower["evidence_complete"] is True
    assert lower["path_exists"] is True
    assert lower["sha256_verified"] is True
    assert lower["sha256"] == _file_sha256(Path(lower["path"]))
    assert lower["family"]["data_family"] == "lower_timeframe_bars"


def test_research_candidate_pack_reports_fixture_provenance_mismatch(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    manifest["data_source"]["fixture_source"]["source_name"] = "crypto_lake"
    manifest["data_source"]["fixture_derivation"]["derivation_type"] = "tampered"
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.passed is False
    assert "fixture_source_mismatch" in gate.reasons
    assert "fixture_derivation_mismatch" in gate.reasons
    with pytest.raises(ValueError, match="fixture_source_mismatch"):
        write_research_candidate_pack(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")


def test_research_candidate_pack_blocks_non_candidate_ready_source_capability(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    for source in (
        manifest["data_source"]["fixture_source"],
        manifest["data_source"],
    ):
        source["provider_capability"]["candidate_ready_default"] = False
        source["provider_capability"]["diagnostic_only_by_default"] = True
        source["provider_capability"]["durability_class"] = "latest_window_rest"
    manifest["data_source"]["durable_public_archive_readiness"]["ready"] = False
    manifest["data_source"]["durable_public_archive_readiness"]["status"] = "diagnostic_or_incomplete"
    manifest["data_source"]["durable_public_archive_readiness"]["reasons"] = ["latest_window_context_diagnostic_only:funding_rate"]
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.passed is False
    assert "source_provider_capability_not_candidate_ready" in gate.reasons
    assert "source_provider_capability_diagnostic_only" in gate.reasons
    assert "source_provider_capability_durability_not_candidate_ready" in gate.reasons
    assert "durable_public_archive_readiness_not_ready" in gate.reasons
    with pytest.raises(ValueError, match="source_provider_capability_not_candidate_ready"):
        write_research_candidate_pack(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")


def test_research_candidate_pack_requires_embedded_fixture_provenance(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    for key in (
        "fixture_source",
        "fixture_derivation",
        "fixture_scope",
        "omitted_optional_families",
        "research_evidence_limitations",
    ):
        manifest["data_source"].pop(key)
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.passed is False
    assert "fixture_source_required" in gate.reasons
    assert "fixture_derivation_required" in gate.reasons
    assert "fixture_scope_required" in gate.reasons
    assert "fixture_omitted_optional_families_required" in gate.reasons
    assert "fixture_research_evidence_limitations_required" in gate.reasons


def test_research_candidate_pack_blocks_scope_omission_and_limitation_mismatch(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    manifest["data_source"]["fixture_scope"] = "tampered_scope"
    manifest["data_source"]["omitted_optional_families"]["funding_rate"] = "tampered"
    manifest["data_source"]["research_evidence_limitations"] = ["tampered_limitation"]
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.passed is False
    assert "fixture_scope_mismatch" in gate.reasons
    assert "fixture_omitted_optional_families_mismatch" in gate.reasons
    assert "fixture_research_evidence_limitations_mismatch" in gate.reasons


def test_research_candidate_pack_blocks_lower_timeframe_without_source_evidence(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path, lower_timeframe=True)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    manifest.pop("lower_timeframe_evidence")
    for key in (
        "lower_timeframe_family_present",
        "lower_timeframe_dataset_path",
        "lower_timeframe_dataset_sha256",
        "lower_timeframe_row_count",
        "lower_timeframe_family",
    ):
        manifest["data_source"].pop(key, None)
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_lower_timeframe_source_evidence_required" in gate.reasons
    assert "candidate_lower_timeframe_source_family_required" in gate.reasons
    assert "candidate_lower_timeframe_source_path_required" in gate.reasons


def test_research_candidate_pack_blocks_lower_timeframe_backtest_hash_mismatch(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path, lower_timeframe=True)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    backtest_index_path = Path(manifest["required_outputs"]["backtest_index"])
    backtest_index = pd.read_parquet(backtest_index_path)
    backtest_index.loc[backtest_index["evaluation_scope"] == "aggregate", "lower_timeframe_dataset_sha256"] = "bad-hash"
    backtest_index.to_parquet(backtest_index_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_lower_timeframe_dataset_sha256_mismatch:aggregate" in gate.reasons
    assert "candidate_lower_timeframe_cache_component_mismatch:aggregate" in gate.reasons


def test_research_candidate_pack_blocks_missing_lower_timeframe_sequence_proof_counts(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path, lower_timeframe=True)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    backtest_index_path = Path(manifest["required_outputs"]["backtest_index"])
    backtest_index = pd.read_parquet(backtest_index_path)
    backtest_index.loc[backtest_index["evaluation_scope"] == "aggregate", "exit_sequence_proof_counts_json"] = "{}"
    backtest_index.to_parquet(backtest_index_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_lower_timeframe_sequence_proof_required:aggregate" in gate.reasons


def test_research_candidate_pack_blocks_synthetic_evidence(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path, synthetic=True)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    manifest["data_source"]["synthetic"] = True
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "synthetic_fixture_not_research_pack_evidence" in gate.reasons
    assert "non_synthetic_data_source_required" in gate.reasons
    with pytest.raises(ValueError, match="research candidate gate blocked"):
        write_research_candidate_pack(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")


def test_research_candidate_pack_requires_historical_fixture_source_provenance(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    manifest["data_source"] = {
        "source_type": "dataset_manifest",
        "dataset_path": manifest["data_source"]["dataset_path"],
        "synthetic": False,
    }
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "historical_fixture_pack_source_required" in gate.reasons
    assert "fixture_id_required" in gate.reasons
    assert "fixture_pack_validation_required" in gate.reasons
    assert "fixture_manifest_path_required" in gate.reasons


def test_research_candidate_pack_blocks_unsafe_cycle_manifest_flags(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    manifest["promotion_ready"] = True
    manifest["live_signal_input"] = True
    manifest["operator_control_input"] = True
    manifest["runtime_control_input"] = True
    manifest["order_placement_used"] = True
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "cycle_manifest_promotion_ready_must_be_false" in gate.reasons
    assert "cycle_manifest_live_signal_input_must_be_false" in gate.reasons
    assert "cycle_manifest_operator_control_input_must_be_false" in gate.reasons
    assert "cycle_manifest_runtime_control_input_must_be_false" in gate.reasons
    assert "cycle_manifest_order_placement_used_must_be_false" in gate.reasons


def test_research_candidate_pack_blocks_live_adjacent_cycle_manifest_artifact(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    manifest["promotion_candidate_manifest_version"] = "promotion-candidate-v1"
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "cycle_manifest_live_adjacent_or_invalid" in gate.reasons
    assert "required_output_live_adjacent_or_promotion_ready:research_cycle_manifest" in gate.reasons


def test_research_candidate_pack_validates_fixture_manifest_boundary_and_identity(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    fixture_manifest_path = Path(manifest["data_source"]["manifest_path"])
    fixture_manifest = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["fixture_id"] = "other-fixture"
    fixture_manifest["promotion_ready"] = True
    fixture_manifest_path.write_text(json.dumps(fixture_manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["data_source"]["manifest_sha256"] = _file_sha256(fixture_manifest_path)
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "fixture_manifest_live_adjacent_or_invalid" in gate.reasons


def test_research_candidate_pack_validates_fixture_manifest_identity(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    fixture_manifest_path = Path(manifest["data_source"]["manifest_path"])
    fixture_manifest = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["fixture_id"] = "other-fixture"
    fixture_manifest_path.write_text(json.dumps(fixture_manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["data_source"]["manifest_sha256"] = _file_sha256(fixture_manifest_path)
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "fixture_manifest_fixture_id_mismatch" in gate.reasons


def test_research_candidate_pack_blocks_rejected_ranking_rows(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    rankings_path = Path(manifest["required_outputs"]["candidate_rankings"])
    rankings = pd.read_parquet(rankings_path)
    rankings.loc[0, "decision"] = "rejected"
    rankings.to_parquet(rankings_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "ranking_decision_not_research_gate_passed" in gate.reasons


def test_research_candidate_pack_requires_validated_stability(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    rankings_path = Path(manifest["required_outputs"]["candidate_rankings"])
    rankings = pd.read_parquet(rankings_path)
    rankings.loc[0, "stability_evaluated"] = False
    rankings.loc[0, "stability_validation_scope"] = "aggregate_only_unvalidated_neighborhood"
    rankings.to_parquet(rankings_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "validated_stability_region_required" in gate.reasons
    assert "split_cost_stress_stability_scope_required" in gate.reasons


def test_research_candidate_pack_requires_durable_gate_report(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    gate_report_path = Path(manifest["required_outputs"]["candidate_gate_report"])
    gate_report_path.unlink()

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_gate_report_required" in gate.reasons


def test_research_candidate_pack_requires_clean_passed_gate_report_row(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    gate_report_path = Path(manifest["required_outputs"]["candidate_gate_report"])
    gate_report = pd.read_parquet(gate_report_path)
    gate_report.loc[0, "gate_status"] = "blocked"
    gate_report.loc[0, "gate_reasons"] = "manual_block"
    gate_report.to_parquet(gate_report_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_gate_report_status_not_passed" in gate.reasons
    assert "candidate_gate_report_reasons_not_empty" in gate.reasons


def test_research_candidate_pack_requires_all_required_outputs(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    Path(manifest["required_outputs"]["metrics_by_side"]).unlink()
    del manifest["required_outputs"]["metrics_by_holding_window"]
    cycle_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "required_output_path_missing:metrics_by_side" in gate.reasons
    assert "required_output_missing:metrics_by_holding_window" in gate.reasons


def test_research_candidate_pack_requires_candidate_metric_rows(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    split_metrics_path = Path(manifest["required_outputs"]["metrics_by_split"])
    holding_metrics_path = Path(manifest["required_outputs"]["metrics_by_holding_window"])
    pd.DataFrame([{"candidate_id": "other-candidate", "split_id": "split-1"}]).to_parquet(split_metrics_path, index=False)
    pd.DataFrame([{"candidate_id": "other-candidate", "holding_window": "4h", "candidate_count": 1}]).to_parquet(holding_metrics_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_metric_rows_required:metrics_by_split" in gate.reasons
    assert "candidate_metric_rows_required:metrics_by_holding_window" in gate.reasons


def test_research_candidate_pack_rejects_placeholder_side_and_regime_metrics(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-1",
                "regime": "all",
                "trade_count": 5,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.02,
                "hit_rate": 0.6,
                "backtest_manifest_path": "backtest_manifest.json",
            }
        ]
    ).to_parquet(manifest["required_outputs"]["metrics_by_regime"], index=False)
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-1",
                "side": "all",
                "trade_count": 5,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.02,
                "hit_rate": 0.6,
                "backtest_manifest_path": "backtest_manifest.json",
            }
        ]
    ).to_parquet(manifest["required_outputs"]["metrics_by_side"], index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_regime_metric_aggregate_label_forbidden" in gate.reasons
    assert "candidate_regime_metric_multiple_regimes_required" in gate.reasons
    assert "candidate_side_metric_invalid_side" in gate.reasons
    assert "candidate_side_metric_long_short_required" in gate.reasons


def test_research_candidate_pack_rejects_incomplete_split_and_cost_stress_metrics(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    pd.DataFrame(
        [
            {
                "candidate_id": "candidate-1",
                "split_id": "split-1",
                "trade_count": 5,
                "costed_expectancy": 0.01,
                "net_return_after_fees_slippage_funding": 0.02,
                "max_drawdown": -0.001,
                "backtest_manifest_path": "backtest_manifest.json",
            }
        ]
    ).to_parquet(manifest["required_outputs"]["metrics_by_split"], index=False)
    pd.DataFrame(
        [
                {
                    "candidate_id": "candidate-1",
                    "scenario_id": "base_costs",
                    "scenario_group": "cost",
                    "fee_bps": 5.0,
                    "slippage_bps": 5.0,
                    "spread_bps": 0.0,
                    "funding_rate": 0.0,
                    "source_row_count": 96,
                    "scenario_status": "evaluated",
                    "trade_count": 5,
                    "stressed_expectancy": 0.01,
                    "stressed_net_return": 0.02,
                "backtest_manifest_path": "backtest_manifest.json",
            }
        ]
    ).to_parquet(manifest["required_outputs"]["metrics_by_cost_stress"], index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_split_metric_column_required:validation_method" in gate.reasons
    assert "candidate_cost_stress_metric_count_below_required" in gate.reasons
    assert "candidate_cost_stress_non_base_scenario_required" in gate.reasons


def test_research_candidate_pack_rejects_split_trade_count_below_floor(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    split_metrics_path = Path(manifest["required_outputs"]["metrics_by_split"])
    split_metrics = pd.read_parquet(split_metrics_path)
    split_metrics.loc[0, "trade_count"] = 1
    split_metrics.loc[0, "trade_count_floor_status"] = "failed"
    split_metrics.to_parquet(split_metrics_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_split_metric_trade_count_below_floor" in gate.reasons


def test_research_candidate_pack_rejects_missing_configured_split_method_coverage(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    split_manifest_path = Path(manifest["required_outputs"]["split_manifest"])
    split_manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    split_manifest["validation_method"] = "configured_validation_splits"
    split_manifest["validation_methods"] = ["purged_embargoed_walk_forward", "month_holdout"]
    split_manifest["validation_method_counts"] = {
        "purged_embargoed_walk_forward": 1,
        "month_holdout": 1,
    }
    split_manifest_path.write_text(json.dumps(split_manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_split_metric_validation_method_coverage_incomplete" in gate.reasons
    assert "candidate_split_metric_validation_method_count_below_required" in gate.reasons


def test_research_candidate_pack_recomputes_cost_stress_survival_from_metrics(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    cost_metrics_path = Path(manifest["required_outputs"]["metrics_by_cost_stress"])
    cost_metrics = pd.read_parquet(cost_metrics_path)
    cost_metrics.loc[0, "stressed_expectancy"] = -0.05
    cost_metrics.loc[0, "stressed_net_return"] = -0.02
    cost_metrics.loc[0, "stress_survival_score"] = -0.07
    cost_metrics.loc[0, "stress_survival_status"] = "failed"
    cost_metrics.to_parquet(cost_metrics_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_cost_stress_survival_rate_below_required" in gate.reasons
    assert "candidate_cost_stress_survival_status_failed" in gate.reasons


def test_research_candidate_pack_recomputes_split_dominance_from_metrics(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    split_metrics_path = Path(manifest["required_outputs"]["metrics_by_split"])
    split_metrics = pd.read_parquet(split_metrics_path)
    split_metrics.loc[0, "net_return_after_fees_slippage_funding"] = 0.99
    split_metrics.loc[1, "net_return_after_fees_slippage_funding"] = 0.01
    split_metrics.to_parquet(split_metrics_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_split_metric_max_single_split_pnl_share_above_limit" in gate.reasons


def test_research_candidate_pack_requires_candidate_backtest_evidence(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    backtest_index_path = Path(manifest["required_outputs"]["backtest_index"])
    backtest_index = pd.read_parquet(backtest_index_path)
    backtest_index.loc[0, "backtest_manifest_path"] = str(backtest_index_path.parent / "missing_manifest.json")
    backtest_index.to_parquet(backtest_index_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_backtest_manifest_missing:aggregate" in gate.reasons


def test_research_candidate_pack_blocks_backtest_execution_cache_reuse_claims(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    backtest_index = pd.read_parquet(manifest["required_outputs"]["backtest_index"])
    backtest_manifest_path = Path(str(backtest_index.loc[0, "backtest_manifest_path"]))
    backtest_manifest = json.loads(backtest_manifest_path.read_text(encoding="utf-8"))
    backtest_manifest["cache_lookup_used"] = True
    backtest_manifest["execution_cache_reuse_enabled"] = True
    backtest_manifest_path.write_text(json.dumps(backtest_manifest, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_backtest_cache_lookup_must_be_false:aggregate" in gate.reasons
    assert "candidate_backtest_execution_cache_reuse_must_be_false:aggregate" in gate.reasons


def test_research_candidate_pack_blocks_live_adjacent_backtest_metrics(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    backtest_index = pd.read_parquet(manifest["required_outputs"]["backtest_index"])
    metrics_path = Path(str(backtest_index.loc[0, "metrics_path"]))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["promotion_candidate_manifest_version"] = "promotion-candidate-v1"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_backtest_metrics_live_adjacent_or_invalid:aggregate" in gate.reasons


def test_research_candidate_pack_requires_complete_validation_counts(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    rankings_path = Path(manifest["required_outputs"]["candidate_rankings"])
    rankings = pd.read_parquet(rankings_path)
    rankings.loc[0, "split_evaluation_count"] = 0
    rankings.loc[0, "cost_stress_evaluation_count"] = 0
    rankings.to_parquet(rankings_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "split_evaluation_count_below_required" in gate.reasons
    assert "cost_stress_evaluation_count_below_required" in gate.reasons


def test_research_candidate_pack_refuses_live_adjacent_evidence(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path, live_adjacent=True)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "required_output_live_adjacent_or_promotion_ready:ablation_report" in gate.reasons
    with pytest.raises(ValueError, match="research candidate gate blocked"):
        write_research_candidate_pack(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")


def test_research_candidate_pack_requires_candidate_ablation_evidence(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    ablation_report_path = Path(manifest["required_outputs"]["ablation_report"])
    ablation = json.loads(ablation_report_path.read_text(encoding="utf-8"))
    ablation["candidate_rows"] = []
    ablation_report_path.write_text(json.dumps(ablation, indent=2, sort_keys=True), encoding="utf-8")

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_ablation_row_required" in gate.reasons


def test_research_candidate_pack_blocks_failed_ranking_ablation_status(tmp_path: Path) -> None:
    cycle_manifest = _cycle_outputs(tmp_path)
    manifest = json.loads(cycle_manifest.read_text(encoding="utf-8"))
    rankings_path = Path(manifest["required_outputs"]["candidate_rankings"])
    rankings = pd.read_parquet(rankings_path)
    rankings.loc[0, "feature_ablation_passed"] = False
    rankings.loc[0, "ablation_evidence_status"] = "comparator_feature_set_failed"
    rankings.loc[0, "ablation_failure_reasons"] = "candidate_underperforms_feature_ablation_comparator"
    rankings.to_parquet(rankings_path, index=False)

    gate = evaluate_research_candidate_gate(cycle_manifest_path=cycle_manifest, candidate_id="candidate-1")

    assert gate.status == "blocked"
    assert "candidate_feature_ablation_pass_required" in gate.reasons
    assert "candidate_feature_ablation_status_not_passing" in gate.reasons
    assert "candidate_feature_ablation_failure_reasons_not_empty" in gate.reasons


def test_research_candidate_pack_schema_rejects_promotion_fields() -> None:
    reasons = validate_research_candidate_pack_manifest(
        {
            "research_candidate_pack_manifest_version": RESEARCH_CANDIDATE_PACK_VERSION,
            "promotion_candidate_manifest_version": "promotion-candidate-v1",
            "research_only": True,
            "observe_only": True,
            "promotion_ready": True,
            "live_signal_input": False,
            "position_sizing_input": False,
            "operator_control_input": False,
            "live_execution_input": False,
            "runtime_control_input": False,
            "live_fetch_used": False,
            "order_placement_used": False,
            "intended_use": "research_observe_only",
        }
    )

    assert "live_or_promotion_manifest_version_forbidden" in reasons
    assert "promotion_ready_must_be_false" in reasons
