from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pandas as pd
import pytest

from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.data.historical_fixture_pack import HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION, build_provider_kline_fixture_pack
from tradingbotsuite.research.deterministic_datasets import build_hmm_knn_sweep_dataset
from tradingbotsuite.research_cycle import run_historical_research_cycle
from tradingbotsuite.research_cycle.spec import HistoricalResearchCycleSpec


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKED_IN_FULL_CYCLE_SPEC = REPO_ROOT / "configs" / "research" / "full_cycle_btc_v1.json"
CHECKED_IN_PERP_CONTEXT_V2_CYCLE_SPEC = REPO_ROOT / "configs" / "research" / "full_cycle_btcusdt_perp_context_v2.json"
CHECKED_IN_ETH_PERP_CONTEXT_V2_CYCLE_SPEC = REPO_ROOT / "configs" / "research" / "full_cycle_ethusdt_perp_context_v2.json"
CHECKED_IN_FIXTURE_MANIFEST = REPO_ROOT / "data" / "research" / "fixtures" / "btcusdt_v1" / "fixture_pack_manifest.json"
CHECKED_IN_PERP_CONTEXT_FIXTURE_MANIFEST = (
    REPO_ROOT / "data" / "research" / "fixtures" / "btcusdt_context_provider_latest_month_v1" / "fixture_pack_manifest.json"
)
CHECKED_IN_ETH_PERP_CONTEXT_FIXTURE_MANIFEST = (
    REPO_ROOT / "data" / "research" / "fixtures" / "ethusdt_context_provider_latest_month_v1" / "fixture_pack_manifest.json"
)
CHECKED_IN_LIQUIDATION_FIXTURE_MANIFEST = (
    REPO_ROOT / "data" / "research" / "fixtures" / "btcusdt_liquidation_free_sample_v1" / "fixture_pack_manifest.json"
)
REMOVED_CHART_SOURCE_FLAG = "trading" + "view" + "_source_used"


def test_full_cycle_uses_validated_local_fixture_pack_without_synthetic_fallback(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path)
    spec_path = tmp_path / "specs" / "local-fixture-pack-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "cycle_id": "local-fixture-pack-cycle",
                "symbol": "BTCUSDT",
                "output_dir": str(tmp_path / "research" / "historical_cycles" / "local-fixture-pack-cycle"),
                "holding_windows": ["4h"],
                "data": {
                    "dataset_manifest_paths": [str(manifest_path)],
                },
                "features": {
                    "feature_sets": ["features_price_trend_vol"],
                },
                "strategies": ["baseline_no_trade", "trend_following_v1"],
                "validation": {
                    "walk_forward": "rolling_and_anchored",
                    "purge_embargo_bars": 2,
                    "stress_periods_required": True,
                    "min_splits": 2,
                    "trade_count_floor": 1,
                },
                "optimizer": {
                    "top_regions_to_refine": 1,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    candidate_space_manifest = json.loads(Path(manifest["required_outputs"]["candidate_space_manifest"]).read_text(encoding="utf-8"))
    feature_build_manifest = json.loads(Path(manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    candidate_gate_report = pd.read_parquet(manifest["required_outputs"]["candidate_gate_report"])

    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["operator_control_input"] is False
    assert manifest["live_execution_input"] is False
    assert manifest["runtime_control_input"] is False
    assert manifest["live_fetch_used"] is False
    assert manifest["order_placement_used"] is False
    assert manifest["data_source"]["source_type"] == "historical_fixture_pack"
    assert manifest["data_source"]["synthetic"] is False
    assert manifest["data_source"]["fixture_id"] == "btcusdt-local-offline-v1"
    assert manifest["data_source"]["manifest_path"] == str(manifest_path)
    assert manifest["data_source"]["manifest_sha256"] == _file_sha256(manifest_path)
    assert Path(manifest["data_source"]["dataset_path"]).exists()
    assert manifest["data_source"]["validation"]["valid"] is True
    assert manifest["data_source"]["validation"]["errors"] == []
    assert manifest["candidate_pack_written"] is False
    assert manifest["candidate_pack_paths"] == []
    assert manifest["candidate_acceptance_scope"] == "research_gate_evaluated_fail_closed"
    assert not candidate_gate_report["pack_eligible"].any()
    assert manifest["candidate_count"] == 6
    assert manifest["candidate_search_mode"] == "metadata_default_search"
    assert manifest["candidate_search_method"] == "metadata_capped_grid"
    assert candidate_space_manifest["default_search_policy"]["candidate_source_counts"]["metadata_default_seed"] == 2
    assert candidate_space_manifest["default_search_policy"]["candidate_source_counts"]["metadata_default_search"] == 4
    assert {"metadata_default_seed", "metadata_default_search"} <= set(rankings["candidate_source"])
    assert "synthetic_fixture_not_real_oos_evidence" not in "|".join(rankings["failure_reasons"].astype(str))
    assert feature_build_manifest["feature_computation_scope"] == "materialized_registered_feature_sets"
    assert feature_build_manifest["primary_interval_ms"] == 900_000
    assert feature_build_manifest["primary_interval_source"] == "data_source.base_interval"
    assert feature_build_manifest["feature_sets"][0]["feature_cache_key"]
    assert feature_build_manifest["feature_sets"][0]["feature_frame_sha256"]
    assert feature_build_manifest["feature_sets"][0]["feature_artifact_sha256"]
    assert feature_build_manifest["feature_sets"][0]["interval_ms"] == 900_000
    assert Path(feature_build_manifest["feature_sets"][0]["feature_path"]).exists()
    assert Path(feature_build_manifest["feature_sets"][0]["cache_manifest_path"]).exists()
    for output_path in manifest["required_outputs"].values():
        assert Path(output_path).exists()


def test_checked_in_full_cycle_config_consumes_btcusdt_fixture_pack(tmp_path: Path) -> None:
    spec = HistoricalResearchCycleSpec.from_path(CHECKED_IN_FULL_CYCLE_SPEC)
    fixture_manifest = json.loads(CHECKED_IN_FIXTURE_MANIFEST.read_text(encoding="utf-8"))

    assert spec.data.synthetic_fixture is False
    assert spec.data.local_fixture_dir is None
    assert spec.data.dataset_manifest_paths == (CHECKED_IN_FIXTURE_MANIFEST,)
    assert "synthetic_row_count" not in spec.to_payload()["data"]
    assert "synthetic_variant" not in spec.to_payload()["data"]

    result = run_historical_research_cycle(
        spec_path=CHECKED_IN_FULL_CYCLE_SPEC,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    feature_build_manifest = json.loads(Path(manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8"))

    assert manifest["data_source"]["source_type"] == "historical_fixture_pack"
    assert manifest["data_source"]["synthetic"] is False
    assert manifest["data_source"]["manifest_path"] == str(CHECKED_IN_FIXTURE_MANIFEST)
    assert manifest["data_source"]["fixture_id"] == "btcusdt-v1-checked-in-binance-usdm-klines"
    assert manifest["data_source"]["fixture_scope"] == "checked_in_small_provider_ohlcv_fixture_not_oos_acceptance_evidence"
    assert manifest["data_source"]["fixture_source"]["source_name"] == "binance_rest"
    assert manifest["data_source"]["fixture_source"]["source_raw"] == "binance_usdm_klines"
    assert manifest["data_source"]["fixture_source"]["data_family"] == "kline"
    assert manifest["data_source"]["fixture_derivation"][REMOVED_CHART_SOURCE_FLAG] is False
    assert manifest["data_source"]["fixture_derivation"]["synthetic_source_used"] is False
    assert manifest["data_source"]["omitted_optional_families"] == fixture_manifest["omitted_optional_families"]
    assert "not_sufficient_for_oos_acceptance" in manifest["data_source"]["research_evidence_limitations"]
    assert manifest["data_source"]["validation"]["valid"] is True
    assert manifest["data_source"]["validation"]["row_count"] == fixture_manifest["cycle_dataset"]["row_count"]
    assert 96 <= int(manifest["data_source"]["validation"]["row_count"]) <= 240
    assert manifest["data_source"]["validation"]["lower_timeframe_row_count"] is None
    assert manifest["data_source"]["validation"]["optional_context_families"] == {}
    assert manifest["data_source"]["lower_timeframe_family_present"] is False
    assert manifest["data_source"]["lower_timeframe_dataset_path"] is None
    assert manifest["candidate_count"] > 0
    assert not rankings.empty
    assert "synthetic_fixture_not_real_oos_evidence" not in "|".join(rankings["failure_reasons"].astype(str))
    assert feature_build_manifest["primary_interval_ms"] == 900_000
    assert feature_build_manifest["primary_interval_source"] == "data_source.base_interval"
    assert feature_build_manifest["feature_sets"][0]["interval_ms"] == 900_000
    assert feature_build_manifest["fixture_family_context"]["joined_families"] == []
    assert feature_build_manifest["fixture_family_context"]["family_count"] == 0


def test_liquidation_fixture_cycle_builds_features_with_declared_1m_interval(tmp_path: Path) -> None:
    fixture_manifest = json.loads(CHECKED_IN_LIQUIDATION_FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    assert fixture_manifest["base_interval"] == "1m"

    spec_path = tmp_path / "specs" / "wpr66-liquidation-interval-aware-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "cycle_id": "wpr66-liquidation-interval-aware-cycle",
                "symbol": "BTCUSDT",
                "output_dir": str(
                    tmp_path / "research" / "historical_cycles" / "wpr66-liquidation-interval-aware-cycle"
                ),
                "backtest_backend": "auto",
                "holding_windows": ["1h"],
                "data": {
                    "dataset_manifest_paths": [str(CHECKED_IN_LIQUIDATION_FIXTURE_MANIFEST)],
                },
                "features": {
                    "feature_sets": ["features_liquidation_context_v1"],
                },
                "strategies": [
                    "baseline_no_trade",
                    "liquidation_absorption_classifier_v1",
                ],
                "validation": {
                    "walk_forward": "rolling_and_anchored",
                    "purge_embargo_bars": 2,
                    "stress_periods_required": True,
                    "min_splits": 2,
                    "trade_count_floor": 1,
                },
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

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    feature_build_manifest = json.loads(
        Path(manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8")
    )
    candidate_space_manifest = json.loads(
        Path(manifest["required_outputs"]["candidate_space_manifest"]).read_text(encoding="utf-8")
    )
    candidate_gate_report = pd.read_parquet(manifest["required_outputs"]["candidate_gate_report"])
    feature_record = feature_build_manifest["feature_sets"][0]
    cache_manifest = json.loads(Path(feature_record["cache_manifest_path"]).read_text(encoding="utf-8"))
    feature_frame = pd.read_parquet(feature_record["feature_path"])

    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["data_source"]["source_type"] == "historical_fixture_pack"
    assert manifest["data_source"]["synthetic"] is False
    assert manifest["data_source"]["fixture_id"] == "btcusdt-liquidation-free-sample-v1"
    assert manifest["data_source"]["base_interval"] == "1m"
    assert manifest["data_source"]["fixture_source"]["source_name"] == "crypto_lake"
    assert manifest["data_source"]["fixture_source"]["source_access_mode"] == "free_sample"
    assert manifest["data_source"]["fixture_source"]["diagnostic_only"] is True
    assert manifest["data_source"]["fixture_source"]["free_sample_data"] is True
    assert manifest["data_source"]["fixture_family_context"]["joined_families"] == ["liquidation"]
    assert (
        manifest["data_source"]["fixture_family_context"]["family_records"][0]["coverage_scope"]
        == "free_sample_diagnostic"
    )
    assert manifest["candidate_pack_written"] is False
    assert manifest["candidate_pack_paths"] == []
    assert not candidate_gate_report["pack_eligible"].any()

    assert feature_build_manifest["feature_computation_scope"] == "materialized_registered_feature_sets"
    assert feature_build_manifest["primary_interval_ms"] == 60_000
    assert feature_build_manifest["primary_interval_source"] == "data_source.base_interval"
    assert feature_build_manifest["declared_base_interval"] == "1m"
    assert feature_record["feature_set_id"] == "features_liquidation_context_v1"
    assert feature_record["interval_ms"] == 60_000
    assert cache_manifest["interval_ms"] == 60_000
    assert cache_manifest["feature_cache_key"] == feature_record["feature_cache_key"]
    assert feature_record["fixture_family_joined_families"] == ["liquidation"]
    assert feature_frame["feature_time_ms"].sub(feature_frame["bar_time_ms"]).eq(60_000).all()
    assert {
        "liq_total_notional_1h",
        "liq_total_notional_z_7d",
        "liq_absorption_reclaim_bps",
        "quality_liquidation_provider_backed",
    } <= set(feature_frame.columns)
    assert feature_frame["liq_total_notional_1h"].notna().any()
    assert feature_frame["liq_total_notional_z_7d"].notna().any()
    assert feature_frame["quality_liquidation_provider_backed"].eq(1.0).any()

    assert candidate_space_manifest["feature_sets"] == ["features_liquidation_context_v1"]
    assert {record["coverage_status"] for record in candidate_space_manifest["baseline_comparator_coverage"]} == {"complete"}
    assert {"baseline_no_trade", "liquidation_absorption_classifier_v1"} <= set(
        candidate_space_manifest["generated_strategy_ids"]
    )


def test_checked_in_perp_context_v2_cycle_consumes_provider_context_fixture(tmp_path: Path) -> None:
    spec = HistoricalResearchCycleSpec.from_path(CHECKED_IN_PERP_CONTEXT_V2_CYCLE_SPEC)
    fixture_manifest = json.loads(CHECKED_IN_PERP_CONTEXT_FIXTURE_MANIFEST.read_text(encoding="utf-8"))

    assert spec.data.synthetic_fixture is False
    assert spec.data.local_fixture_dir is None
    assert spec.data.dataset_manifest_paths == (CHECKED_IN_PERP_CONTEXT_FIXTURE_MANIFEST,)
    assert spec.features.feature_sets == ("features_perp_context_v2",)
    expected_strategies = {
        "baseline_no_trade",
        "perp_basis_convergence_v2",
        "funding_crowding_fade_v2",
        "oi_flow_breakout_v2",
        "funding_window_timing_v1",
    }
    assert set(spec.strategies) == expected_strategies
    assert [policy["exit_policy_id"] for policy in spec.exits.exit_policies] == [
        "fixed_holding_window",
        "funding_aware_exit_v1",
        "oi_contraction_exit_v1",
    ]
    assert spec.output_dir == REPO_ROOT / "data" / "research" / "historical_cycles" / "btcusdt_perp_context_v2_foundation"

    payload = json.loads(CHECKED_IN_PERP_CONTEXT_V2_CYCLE_SPEC.read_text(encoding="utf-8"))
    payload["output_dir"] = str(tmp_path / "research" / "historical_cycles" / "btcusdt_perp_context_v2_foundation")
    payload["data"]["dataset_manifest_paths"] = [str(CHECKED_IN_PERP_CONTEXT_FIXTURE_MANIFEST)]
    spec_path = tmp_path / "specs" / "full_cycle_btcusdt_perp_context_v2.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    candidate_space_manifest = json.loads(Path(manifest["required_outputs"]["candidate_space_manifest"]).read_text(encoding="utf-8"))
    feature_build_manifest = json.loads(Path(manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    backtest_index = pd.read_parquet(result.backtest_index_path)
    candidate_gate_report = pd.read_parquet(manifest["required_outputs"]["candidate_gate_report"])
    feature_record = feature_build_manifest["feature_sets"][0]
    feature_frame = pd.read_parquet(feature_record["feature_path"])

    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["data_source"]["source_type"] == "historical_fixture_pack"
    assert manifest["data_source"]["synthetic"] is False
    assert manifest["data_source"]["fixture_id"] == fixture_manifest["fixture_id"]
    assert manifest["data_source"]["fixture_derivation"][REMOVED_CHART_SOURCE_FLAG] is False
    assert manifest["data_source"]["fixture_derivation"]["synthetic_source_used"] is False
    assert manifest["data_source"]["validation"]["valid"] is True
    assert manifest["data_source"]["fixture_family_context"]["joined_families"] == [
        "funding_rate",
        "premium_index",
        "open_interest",
    ]
    assert feature_record["feature_set_id"] == "features_perp_context_v2"
    assert feature_record["fixture_family_joined_families"] == ["funding_rate", "premium_index", "open_interest"]
    assert {
        "perp_mark_index_basis",
        "perp_premium_z_7d",
        "perp_last_funding_rate",
        "perp_funding_z_7d",
        "cal_time_since_last_funding_h",
        "cal_time_to_next_funding_h",
        "oi_notional",
        "oi_delta_1h",
        "oi_delta_z_7d",
        "quality_has_oi_gap",
        "quality_provider_backed_all_required",
    } <= set(feature_frame.columns)
    assert feature_frame["quality_provider_backed_all_required"].eq(1.0).any()
    assert feature_frame["quality_latest_window_context_only"].eq(1.0).all()
    assert candidate_space_manifest["feature_sets"] == ["features_perp_context_v2"]
    assert [policy["exit_policy_id"] for policy in candidate_space_manifest["exit_policies"]] == [
        "fixed_holding_window",
        "funding_aware_exit_v1",
        "oi_contraction_exit_v1",
    ]
    assert expected_strategies <= set(candidate_space_manifest["generated_strategy_ids"])
    assert {record["coverage_status"] for record in candidate_space_manifest["baseline_comparator_coverage"]} == {"complete"}
    assert expected_strategies <= set(rankings["strategy_id"])
    assert expected_strategies <= set(backtest_index["strategy_id"])
    assert {"fixed_holding_window", "funding_aware_exit_v1", "oi_contraction_exit_v1"} <= set(rankings["exit_policy_id"])
    assert {"fixed_holding_window", "funding_aware_exit_v1", "oi_contraction_exit_v1"} <= set(backtest_index["exit_policy_id"])
    assert set(rankings["ablation_evidence_status"]) == {"baseline_feature_set_no_optional_claim"}
    assert set(rankings["feature_ablation_required"]) == {False}
    assert rankings["feature_ablation_passed"].all()
    assert "feature_ablation_comparator_missing" not in "|".join(rankings["failure_reasons"].astype(str))
    funding_rows = rankings.loc[rankings["strategy_id"].astype(str) == "funding_crowding_fade_v2"]
    assert not funding_rows.empty
    if int(funding_rows["trade_count"].sum()) == 0:
        assert funding_rows["failure_reasons"].astype(str).str.contains("low_signal_density|trade_count").any()
    oi_flow_rows = rankings.loc[rankings["strategy_id"].astype(str) == "oi_flow_breakout_v2"]
    assert not oi_flow_rows.empty
    if int(oi_flow_rows["trade_count"].sum()) == 0:
        assert oi_flow_rows["failure_reasons"].astype(str).str.contains(
            "low_signal_density|trade_count|flow_confirmation",
        ).any()
    funding_window_rows = rankings.loc[rankings["strategy_id"].astype(str) == "funding_window_timing_v1"]
    assert not funding_window_rows.empty
    if int(funding_window_rows["trade_count"].sum()) == 0:
        assert funding_window_rows["failure_reasons"].astype(str).str.contains(
            "low_signal_density|trade_count|funding_window|timing",
        ).any()
    assert "synthetic_fixture_not_real_oos_evidence" not in "|".join(rankings["failure_reasons"].astype(str))
    assert manifest["candidate_pack_written"] is False
    assert manifest["candidate_pack_paths"] == []
    assert not candidate_gate_report["pack_eligible"].any()


def test_checked_in_eth_perp_context_v2_cycle_consumes_provider_context_fixture(tmp_path: Path) -> None:
    spec = HistoricalResearchCycleSpec.from_path(CHECKED_IN_ETH_PERP_CONTEXT_V2_CYCLE_SPEC)
    fixture_manifest = json.loads(CHECKED_IN_ETH_PERP_CONTEXT_FIXTURE_MANIFEST.read_text(encoding="utf-8"))

    assert spec.symbol == "ETHUSDT"
    assert spec.data.synthetic_fixture is False
    assert spec.data.local_fixture_dir is None
    assert spec.data.dataset_manifest_paths == (CHECKED_IN_ETH_PERP_CONTEXT_FIXTURE_MANIFEST,)
    assert spec.features.feature_sets == ("features_perp_context_v2",)
    expected_strategies = {
        "baseline_no_trade",
        "perp_basis_convergence_v2",
        "funding_crowding_fade_v2",
        "oi_flow_breakout_v2",
        "funding_window_timing_v1",
    }
    assert set(spec.strategies) == expected_strategies
    assert [policy["exit_policy_id"] for policy in spec.exits.exit_policies] == [
        "fixed_holding_window",
        "funding_aware_exit_v1",
        "oi_contraction_exit_v1",
    ]
    assert spec.output_dir == REPO_ROOT / "data" / "research" / "historical_cycles" / "ethusdt_perp_context_v2_foundation"

    payload = json.loads(CHECKED_IN_ETH_PERP_CONTEXT_V2_CYCLE_SPEC.read_text(encoding="utf-8"))
    payload["output_dir"] = str(tmp_path / "research" / "historical_cycles" / "ethusdt_perp_context_v2_foundation")
    payload["data"]["dataset_manifest_paths"] = [str(CHECKED_IN_ETH_PERP_CONTEXT_FIXTURE_MANIFEST)]
    spec_path = tmp_path / "specs" / "full_cycle_ethusdt_perp_context_v2.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    candidate_space_manifest = json.loads(Path(manifest["required_outputs"]["candidate_space_manifest"]).read_text(encoding="utf-8"))
    feature_build_manifest = json.loads(Path(manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    backtest_index = pd.read_parquet(result.backtest_index_path)
    candidate_gate_report = pd.read_parquet(manifest["required_outputs"]["candidate_gate_report"])
    feature_record = feature_build_manifest["feature_sets"][0]
    feature_frame = pd.read_parquet(feature_record["feature_path"])

    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["data_source"]["source_type"] == "historical_fixture_pack"
    assert manifest["data_source"]["synthetic"] is False
    assert manifest["data_source"]["fixture_id"] == fixture_manifest["fixture_id"]
    assert manifest["data_source"]["fixture_derivation"][REMOVED_CHART_SOURCE_FLAG] is False
    assert manifest["data_source"]["fixture_derivation"]["synthetic_source_used"] is False
    assert manifest["data_source"]["validation"]["valid"] is True
    assert manifest["data_source"]["validation"]["row_count"] == fixture_manifest["cycle_dataset"]["row_count"]
    assert manifest["data_source"]["fixture_family_context"]["joined_families"] == [
        "funding_rate",
        "premium_index",
        "open_interest",
    ]
    assert feature_record["feature_set_id"] == "features_perp_context_v2"
    assert feature_record["fixture_family_joined_families"] == ["funding_rate", "premium_index", "open_interest"]
    assert {
        "perp_mark_index_basis",
        "perp_premium_z_7d",
        "perp_last_funding_rate",
        "perp_funding_z_7d",
        "cal_time_since_last_funding_h",
        "cal_time_to_next_funding_h",
        "oi_notional",
        "oi_delta_1h",
        "oi_delta_z_7d",
        "quality_has_oi_gap",
        "quality_provider_backed_all_required",
    } <= set(feature_frame.columns)
    assert feature_frame["quality_provider_backed_all_required"].eq(1.0).any()
    assert feature_frame["quality_latest_window_context_only"].eq(1.0).all()
    assert candidate_space_manifest["feature_sets"] == ["features_perp_context_v2"]
    assert [policy["exit_policy_id"] for policy in candidate_space_manifest["exit_policies"]] == [
        "fixed_holding_window",
        "funding_aware_exit_v1",
        "oi_contraction_exit_v1",
    ]
    assert expected_strategies <= set(candidate_space_manifest["generated_strategy_ids"])
    assert {record["coverage_status"] for record in candidate_space_manifest["baseline_comparator_coverage"]} == {"complete"}
    assert expected_strategies <= set(rankings["strategy_id"])
    assert expected_strategies <= set(backtest_index["strategy_id"])
    assert {"fixed_holding_window", "funding_aware_exit_v1", "oi_contraction_exit_v1"} <= set(rankings["exit_policy_id"])
    assert {"fixed_holding_window", "funding_aware_exit_v1", "oi_contraction_exit_v1"} <= set(backtest_index["exit_policy_id"])
    assert set(rankings["ablation_evidence_status"]) == {"baseline_feature_set_no_optional_claim"}
    assert set(rankings["feature_ablation_required"]) == {False}
    assert rankings["feature_ablation_passed"].all()
    assert "feature_ablation_comparator_missing" not in "|".join(rankings["failure_reasons"].astype(str))
    zero_trade_patterns = {
        "funding_crowding_fade_v2": "low_signal_density|trade_count",
        "oi_flow_breakout_v2": "low_signal_density|trade_count|flow_confirmation",
        "funding_window_timing_v1": "low_signal_density|trade_count|funding_window|timing",
    }
    for strategy_id, failure_pattern in zero_trade_patterns.items():
        strategy_rows = rankings.loc[rankings["strategy_id"].astype(str) == strategy_id]
        assert not strategy_rows.empty
        if int(strategy_rows["trade_count"].sum()) == 0:
            assert strategy_rows["failure_reasons"].astype(str).str.contains(failure_pattern).any()
    assert "synthetic_fixture_not_real_oos_evidence" not in "|".join(rankings["failure_reasons"].astype(str))
    assert manifest["candidate_pack_written"] is False
    assert manifest["candidate_pack_paths"] == []
    assert not candidate_gate_report["pack_eligible"].any()


def test_checked_in_full_cycle_config_does_not_synthesize_when_manifest_missing(tmp_path: Path) -> None:
    payload = json.loads(CHECKED_IN_FULL_CYCLE_SPEC.read_text(encoding="utf-8"))
    payload["output_dir"] = str(tmp_path / "research" / "historical_cycles" / "missing-checked-in-fixture")
    payload["data"]["dataset_manifest_paths"] = [str(tmp_path / "missing_fixture_pack_manifest.json")]
    payload["data"]["local_fixture_dir"] = None
    payload["data"]["synthetic_fixture"] = False
    spec_path = tmp_path / "specs" / "missing-checked-in-fixture.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="no usable dataset path"):
        run_historical_research_cycle(
            spec_path=spec_path,
            app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
        )

    assert not (Path(payload["output_dir"]) / "synthetic_fixture.parquet").exists()


def test_full_cycle_writes_research_candidate_pack_for_complete_fixture_evidence(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(
        tmp_path,
        fixture_id="btcusdt-local-complete-evidence-v1",
        row_count=360,
        include_regime_labels=True,
    )
    spec_path = tmp_path / "specs" / "complete-fixture-pack-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "cycle_id": "complete-fixture-pack-cycle",
                "symbol": "BTCUSDT",
                "output_dir": str(tmp_path / "research" / "historical_cycles" / "complete-fixture-pack-cycle"),
                "holding_windows": ["4h"],
                "data": {
                    "dataset_manifest_paths": [str(manifest_path)],
                },
                "features": {
                    "feature_sets": ["features_price_trend_vol"],
                },
                "strategies": ["baseline_no_trade", "volatility_breakout_v1"],
                "validation": {
                    "walk_forward": "rolling_and_anchored",
                    "purge_embargo_bars": 2,
                    "stress_periods_required": True,
                    "min_splits": 4,
                    "trade_count_floor": 1,
                    "max_single_split_pnl_share": 0.5,
                    "min_cost_stress_survival_rate": 0.7,
                },
                "optimizer": {
                    "top_regions_to_refine": 20,
                    "max_candidates_per_strategy": 4,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    candidate_gate_report = pd.read_parquet(manifest["required_outputs"]["candidate_gate_report"])
    metrics_by_side = pd.read_parquet(manifest["required_outputs"]["metrics_by_side"])
    metrics_by_regime = pd.read_parquet(manifest["required_outputs"]["metrics_by_regime"])

    assert manifest["candidate_pack_written"] is True
    assert manifest["candidate_pack_paths"]
    assert manifest["candidate_acceptance_scope"] == "research_only_pack_eligible_candidates_written"
    passed = rankings.loc[rankings["decision"] == "research_gate_passed"]
    assert not passed.empty
    candidate_id = str(passed.iloc[0]["candidate_id"])
    assert passed.iloc[0]["failure_reasons"] == ""
    assert passed.iloc[0]["side_evidence_status"] == "complete"
    assert passed.iloc[0]["regime_evidence_status"] == "complete"
    assert passed.iloc[0]["cost_stress_scenario_status"] == "complete"
    assert float(passed.iloc[0]["cost_stress_survival_rate"]) >= 0.7
    assert bool(passed.iloc[0]["feature_ablation_passed"]) is True
    assert passed.iloc[0]["ablation_evidence_status"] == "baseline_feature_set_no_optional_claim"
    assert float(passed.iloc[0]["max_single_split_pnl_share"]) <= 0.5
    gate_row = candidate_gate_report.loc[candidate_gate_report["candidate_id"].astype(str) == candidate_id].iloc[0]
    assert gate_row["gate_status"] == "passed"
    assert bool(gate_row["pack_eligible"]) is True
    assert gate_row["candidate_acceptance_scope"] == "research_only_pack_eligible_not_promotion_ready"
    assert gate_row["gate_reasons"] == ""
    side_rows = metrics_by_side.loc[metrics_by_side["candidate_id"].astype(str) == candidate_id]
    assert set(side_rows["side"]) == {"long", "short"}
    regime_rows = metrics_by_regime.loc[metrics_by_regime["candidate_id"].astype(str) == candidate_id]
    assert len(set(regime_rows["regime"]) - {"unknown", "missing", "all", "aggregate"}) >= 2
    pack_manifest = json.loads(Path(manifest["candidate_pack_paths"][0]).read_text(encoding="utf-8"))
    assert pack_manifest["research_only"] is True
    assert pack_manifest["observe_only"] is True
    assert pack_manifest["promotion_ready"] is False
    assert pack_manifest["live_signal_input"] is False
    assert pack_manifest["order_placement_used"] is False


def test_full_cycle_triple_barrier_uses_fixture_lower_timeframe_evidence(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(
        tmp_path,
        fixture_id="btcusdt-local-lower-timeframe-v1",
        row_count=144,
        include_lower_timeframe_bars=True,
    )
    spec_path = tmp_path / "specs" / "lower-timeframe-triple-barrier-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "cycle_id": "lower-timeframe-triple-barrier-cycle",
                "symbol": "BTCUSDT",
                "output_dir": str(tmp_path / "research" / "historical_cycles" / "lower-timeframe-triple-barrier-cycle"),
                "holding_windows": ["4h"],
                "data": {
                    "dataset_manifest_paths": [str(manifest_path)],
                },
                "features": {
                    "feature_sets": ["features_price_trend_vol"],
                },
                "strategies": ["trend_following_v1"],
                "exit_policies": [
                    {
                        "exit_policy_id": "triple_barrier_atr",
                        "target_return": 0.002,
                        "stop_return": 0.002,
                    }
                ],
                "backtest_backend": "auto",
                "validation": {
                    "walk_forward": "rolling_and_anchored",
                    "purge_embargo_bars": 2,
                    "stress_periods_required": True,
                    "min_splits": 2,
                    "trade_count_floor": 1,
                },
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

    result = run_historical_research_cycle(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    candidate_space_manifest = json.loads(Path(manifest["required_outputs"]["candidate_space_manifest"]).read_text(encoding="utf-8"))
    rankings = pd.read_parquet(result.candidate_rankings_path)
    backtest_index = pd.read_parquet(result.backtest_index_path)

    lower_evidence = manifest["lower_timeframe_evidence"]
    assert manifest["data_source"]["source_type"] == "historical_fixture_pack"
    assert lower_evidence["lower_timeframe_family_present"] is True
    assert lower_evidence["lower_timeframe_dataset_sha256"]
    assert Path(lower_evidence["lower_timeframe_dataset_path"]).exists()
    assert candidate_space_manifest["lower_timeframe_evidence"]["lower_timeframe_dataset_sha256"] == lower_evidence["lower_timeframe_dataset_sha256"]
    assert [policy["exit_policy_id"] for policy in candidate_space_manifest["exit_policies"]] == ["triple_barrier_atr"]
    assert set(backtest_index["exit_policy_id"]) == {"triple_barrier_atr"}
    assert set(backtest_index["exit_price_source"]) == {"lower_timeframe_ohlc_sequence"}
    assert set(backtest_index["lower_timeframe_required"]) == {True}
    assert set(backtest_index["lower_timeframe_sequence_used"]) == {True}
    assert set(backtest_index["lower_timeframe_dataset_sha256"]) == {lower_evidence["lower_timeframe_dataset_sha256"]}
    assert set(backtest_index["lower_timeframe_cache_key_component"]) == {lower_evidence["lower_timeframe_dataset_sha256"]}
    assert set(backtest_index["backtest_backend_requested"]) == {"auto"}
    assert set(backtest_index["backtest_backend_used"]) == {"reference"}
    expected_fallback_reason = (
        "cuda_engine_scope_unsupported:vector_engine_lower_timeframe_not_supported;"
        "vector_engine_lower_timeframe_not_supported"
    )
    aggregate_backend_rows = backtest_index.loc[backtest_index["evaluation_scope"] == "aggregate"]
    validation_backend_rows = backtest_index.loc[backtest_index["evaluation_scope"].isin(["walk_forward_split", "cost_stress"])]
    assert set(aggregate_backend_rows["backtest_backend_fallback_reason"]) == {expected_fallback_reason}
    assert set(validation_backend_rows["backtest_backend_fallback_reason"]) == {"cuda_fixed_holding_validation_reference_required"}
    assert manifest["backtest_backend_summary"]["used_counts"] == {"reference": len(backtest_index)}
    assert manifest["backtest_backend_summary"]["fallback_reasons"] == {
        expected_fallback_reason: len(aggregate_backend_rows),
        "cuda_fixed_holding_validation_reference_required": len(validation_backend_rows),
    }
    assert set(rankings["aggregate_backtest_exit_price_source"]) == {"lower_timeframe_ohlc_sequence"}
    assert set(rankings["aggregate_backtest_lower_timeframe_required"]) == {True}
    assert set(rankings["aggregate_backtest_lower_timeframe_sequence_used"]) == {True}
    assert set(rankings["aggregate_backtest_lower_timeframe_dataset_sha256"]) == {lower_evidence["lower_timeframe_dataset_sha256"]}

    trade_rows = aggregate_backend_rows.loc[aggregate_backend_rows["trade_count"] > 0]
    assert not trade_rows.empty
    row = trade_rows.iloc[0]
    backtest_manifest = json.loads(Path(str(row["backtest_manifest_path"])).read_text(encoding="utf-8"))
    assert backtest_manifest["exit_price_source"] == "lower_timeframe_ohlc_sequence"
    assert backtest_manifest["lower_timeframe_dataset_sha256"] == lower_evidence["lower_timeframe_dataset_sha256"]
    assert backtest_manifest["cache_key_components"]["lower_timeframe_dataset_sha256"] == lower_evidence["lower_timeframe_dataset_sha256"]
    proof_counts = json.loads(str(row["exit_sequence_proof_counts_json"]))
    price_source_counts = json.loads(str(row["exit_price_source_counts_json"]))
    barrier_counts = json.loads(str(row["barrier_hit_type_counts_json"]))
    assert proof_counts["lower_timeframe_ohlc"] == int(row["trade_count"])
    assert price_source_counts["lower_timeframe_ohlc_sequence"] == int(row["trade_count"])
    assert barrier_counts
    trades = pd.read_parquet(row["trades_path"])
    assert set(trades["exit_policy"]) == {"triple_barrier_atr"}
    assert set(trades["exit_sequence_proof"]) == {"lower_timeframe_ohlc"}
    assert set(trades["exit_price_source"]) == {"lower_timeframe_ohlc_sequence"}


def test_full_cycle_triple_barrier_requires_fixture_lower_timeframe_data(tmp_path: Path) -> None:
    manifest_path = _write_fixture_pack(tmp_path, fixture_id="btcusdt-local-without-lower-timeframe-v1", row_count=96)
    spec_path = tmp_path / "specs" / "missing-lower-timeframe-cycle.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "cycle_id": "missing-lower-timeframe-cycle",
                "symbol": "BTCUSDT",
                "output_dir": str(tmp_path / "research" / "historical_cycles" / "missing-lower-timeframe-cycle"),
                "holding_windows": ["4h"],
                "data": {
                    "dataset_manifest_paths": [str(manifest_path)],
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

    with pytest.raises(ValueError, match="lower_timeframe_dataset_required_for_triple_barrier_exit"):
        run_historical_research_cycle(
            spec_path=spec_path,
            app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
        )


def test_full_cycle_materializes_fixture_context_families_and_cache_identity(tmp_path: Path) -> None:
    first_manifest_path = _write_fixture_pack(
        tmp_path / "first",
        fixture_id="btcusdt-local-context-v1",
        row_count=120,
        include_context_families=True,
        funding_rate_shift=0.0,
    )
    second_manifest_path = _write_fixture_pack(
        tmp_path / "second",
        fixture_id="btcusdt-local-context-v2",
        row_count=120,
        include_context_families=True,
        funding_rate_shift=0.01,
    )

    first_result = run_historical_research_cycle(
        spec_path=_write_context_cycle_spec(tmp_path / "first", first_manifest_path, cycle_id="fixture-context-cycle-a"),
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    second_result = run_historical_research_cycle(
        spec_path=_write_context_cycle_spec(tmp_path / "second", second_manifest_path, cycle_id="fixture-context-cycle-b"),
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    first_manifest = json.loads(first_result.manifest_path.read_text(encoding="utf-8"))
    second_manifest = json.loads(second_result.manifest_path.read_text(encoding="utf-8"))
    first_feature_build = json.loads(Path(first_manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8"))
    second_feature_build = json.loads(Path(second_manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8"))
    feature_record = first_feature_build["feature_sets"][0]
    feature_frame = pd.read_parquet(feature_record["feature_path"])

    context = first_manifest["data_source"]["fixture_family_context"]
    assert context["joined_families"] == ["funding_rate", "premium_index", "open_interest", "agg_trade"]
    assert {"funding_rate", "premium_basis_rate", "basis_bps", "open_interest_change_pct"} <= set(context["joined_columns"])
    assert {"primary_signed_imbalance_ratio", "top_of_book_imbalance", "spread_bps"} <= set(context["joined_columns"])
    assert first_feature_build["fixture_family_context_sha256"] == context["fixture_family_context_sha256"]
    assert feature_record["fixture_family_context_sha256"] == context["fixture_family_context_sha256"]
    assert feature_record["fixture_family_joined_families"] == context["joined_families"]
    assert Path(feature_record["cache_manifest_path"]).exists()
    cache_manifest = json.loads(Path(feature_record["cache_manifest_path"]).read_text(encoding="utf-8"))
    assert cache_manifest["fixture_family_context"]["joined_families"] == context["joined_families"]
    assert not pd.isna(feature_frame["funding_rate"].iloc[0])
    assert feature_frame["funding_rate"].max() < 0.5
    assert feature_frame["premium_basis_rate"].notna().any()
    assert feature_frame["open_interest_change_pct"].notna().any()
    assert feature_frame["primary_signed_imbalance_ratio"].notna().any()

    assert first_manifest["data_source"]["fixture_family_context_sha256"] != second_manifest["data_source"]["fixture_family_context_sha256"]
    assert first_feature_build["feature_sets"][0]["feature_cache_key"] != second_feature_build["feature_sets"][0]["feature_cache_key"]


def test_full_cycle_consumes_provider_builder_context_fixture_pack(tmp_path: Path) -> None:
    cycle = build_hmm_knn_sweep_dataset(row_count=120, variant="balanced")
    source_manifest_path = _write_provider_kline_manifest_from_cycle(tmp_path / "provider", cycle)
    context_manifest_paths = _write_provider_context_manifests_from_cycle(tmp_path / "provider_context", cycle)
    fixture_result = build_provider_kline_fixture_pack(
        source_manifest_path=source_manifest_path,
        output_dir=tmp_path / "provider_fixture_pack",
        fixture_id="btcusdt-provider-built-context-v1",
        row_limit=120,
        context_manifest_paths=context_manifest_paths,
    )

    fixture_manifest = json.loads(fixture_result.manifest_path.read_text(encoding="utf-8"))
    assert set(fixture_manifest["families"]) == {"bars", "funding_rate", "premium_index", "open_interest", "agg_trade"}
    assert set(fixture_manifest["omitted_optional_families"]) == {"lower_timeframe_bars", "liquidation"}
    assert fixture_manifest["derivation"][REMOVED_CHART_SOURCE_FLAG] is False
    assert fixture_manifest["derivation"]["synthetic_source_used"] is False

    result = run_historical_research_cycle(
        spec_path=_write_context_cycle_spec(
            tmp_path / "provider_cycle",
            fixture_result.manifest_path,
            cycle_id="provider-built-context-cycle",
        ),
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    feature_build = json.loads(Path(manifest["required_outputs"]["feature_build_manifest"]).read_text(encoding="utf-8"))
    feature_record = feature_build["feature_sets"][0]
    feature_frame = pd.read_parquet(feature_record["feature_path"])
    context = manifest["data_source"]["fixture_family_context"]

    assert context["joined_families"] == ["funding_rate", "premium_index", "open_interest", "agg_trade"]
    assert {"funding_rate", "premium_basis_rate", "open_interest_change_pct", "primary_signed_imbalance_ratio"} <= set(
        context["joined_columns"]
    )
    assert not pd.isna(feature_frame["funding_rate"].iloc[0])
    assert feature_frame["funding_rate"].max() < 0.5
    assert feature_record["fixture_family_joined_families"] == context["joined_families"]
    assert feature_record["fixture_family_context_sha256"] == context["fixture_family_context_sha256"]


def _write_fixture_pack(
    tmp_path: Path,
    *,
    fixture_id: str = "btcusdt-local-offline-v1",
    row_count: int = 96,
    include_regime_labels: bool = False,
    include_lower_timeframe_bars: bool = False,
    include_context_families: bool = False,
    funding_rate_shift: float = 0.0,
) -> Path:
    pack_dir = tmp_path / "fixture_pack"
    pack_dir.mkdir(parents=True, exist_ok=True)
    cycle = build_hmm_knn_sweep_dataset(row_count=row_count, variant="balanced")
    if include_regime_labels:
        labels = ["uptrend", "downtrend", "range"]
        cycle["top_regime_label"] = [labels[index % len(labels)] for index in range(len(cycle))]
        cycle["regime"] = cycle["top_regime_label"]
        low_volatility_rows = cycle["realized_volatility"] <= cycle["realized_volatility"].quantile(0.34)
        cycle.loc[low_volatility_rows, "atr_percentile"] = 0.70
        cycle.loc[low_volatility_rows, "volatility_shock_zscore"] = 3.2
        cycle.loc[low_volatility_rows, "directional_slope_atr"] = cycle.loc[
            low_volatility_rows,
            "direction_long",
        ].map(lambda value: 0.12 if float(value) >= 0.5 else -0.12)
    context_family_frames = _fixture_context_family_frames(cycle, funding_rate_shift=funding_rate_shift) if include_context_families else {}
    if include_context_families:
        cycle = _without_prejoined_context_columns(cycle)
    cycle_path = pack_dir / "cycle_dataset.parquet"
    cycle.to_parquet(cycle_path, index=False)
    bars = pd.DataFrame(
        {
            "event_time_ms": cycle["signal_bar_time_ms"],
            "symbol": cycle["symbol"],
            "interval": "15m",
            "open_price": cycle["signal_bar_open"],
            "high_price": cycle["signal_bar_high"],
            "low_price": cycle["signal_bar_low"],
            "close_price": cycle["signal_bar_close"],
            "volume": cycle["signal_bar_volume"],
        }
    )
    bars_path = pack_dir / "bars_15m.parquet"
    bars.to_parquet(bars_path, index=False)
    lower_path: Path | None = None
    lower: pd.DataFrame | None = None
    if include_lower_timeframe_bars:
        lower = _lower_timeframe_bars_from_cycle(cycle)
        lower_path = pack_dir / "lower_timeframe_bars_5m.parquet"
        lower.to_parquet(lower_path, index=False)
    context_family_paths: dict[str, Path] = {}
    for family, family_frame in context_family_frames.items():
        family_path = pack_dir / f"{family}.parquet"
        family_frame.to_parquet(family_path, index=False)
        context_family_paths[family] = family_path
    manifest = {
        "manifest_version": HISTORICAL_FIXTURE_PACK_MANIFEST_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "fixture_id": fixture_id,
        "symbol": "BTCUSDT",
        "base_interval": "15m",
        "cycle_dataset": {
            "path": "cycle_dataset.parquet",
            "sha256": f"sha256:{_file_sha256(cycle_path)}",
            "row_count": len(cycle),
            "time_field": "signal_bar_time_ms",
        },
        "families": {
            "bars": {
                "path": "bars_15m.parquet",
                "data_family": "kline",
                "interval": "15m",
                "event_time_field": "event_time_ms",
                "sha256": f"sha256:{_file_sha256(bars_path)}",
                "row_count": len(bars),
                "required": True,
                "columns": list(bars.columns),
            }
        },
    }
    if lower_path is not None and lower is not None:
        manifest["families"]["lower_timeframe_bars"] = {
            "path": lower_path.name,
            "data_family": "lower_timeframe_bars",
            "interval": "5m",
            "event_time_field": "bar_time_ms",
            "sha256": f"sha256:{_file_sha256(lower_path)}",
            "row_count": len(lower),
            "required": True,
            "columns": list(lower.columns),
        }
    for family, family_path in context_family_paths.items():
        family_frame = context_family_frames[family]
        manifest["families"][family] = {
            "path": family_path.name,
            "data_family": family,
            "event_time_field": "event_time_ms",
            "sha256": f"sha256:{_file_sha256(family_path)}",
            "row_count": len(family_frame),
            "required": False,
            "columns": list(family_frame.columns),
        }
    manifest_path = pack_dir / "fixture_pack_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def _write_context_cycle_spec(tmp_path: Path, manifest_path: Path, *, cycle_id: str) -> Path:
    spec_path = tmp_path / "specs" / f"{cycle_id}.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(
            {
                "cycle_id": cycle_id,
                "symbol": "BTCUSDT",
                "output_dir": str(tmp_path / "research" / "historical_cycles" / cycle_id),
                "holding_windows": ["4h"],
                "data": {
                    "dataset_manifest_paths": [str(manifest_path)],
                },
                "features": {
                    "feature_sets": ["features_full_context_no_wt"],
                },
                "strategies": ["funding_basis_v1"],
                "validation": {
                    "walk_forward": "rolling_and_anchored",
                    "purge_embargo_bars": 2,
                    "stress_periods_required": True,
                    "min_splits": 2,
                    "trade_count_floor": 1,
                },
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
    return spec_path


def _write_provider_kline_manifest_from_cycle(tmp_path: Path, cycle: pd.DataFrame) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "time_ms": int(row["signal_bar_time_ms"]),
            "symbol": str(row["symbol"]),
            "interval": "15m",
            "open": float(row["signal_bar_open"]),
            "high": float(row["signal_bar_high"]),
            "low": float(row["signal_bar_low"]),
            "close": float(row["signal_bar_close"]),
            "volume": float(row["signal_bar_volume"]),
        }
        for row in cycle.to_dict("records")
    ]
    data_path = tmp_path / "BTCUSDT_15m_provider_cycle.jsonl"
    data_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    manifest_path = tmp_path / "BTCUSDT_15m_provider_cycle.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source": "binance_usdm_klines",
                "symbol": "BTCUSDT",
                "interval": "15m",
                "data_family": "kline",
                "data_path": str(data_path),
                "row_count": len(rows),
                "sha256": _file_sha256(data_path),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return manifest_path


def _write_provider_context_manifests_from_cycle(tmp_path: Path, cycle: pd.DataFrame) -> list[Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    frames = _fixture_context_family_frames(cycle, funding_rate_shift=0.0)
    source_names = {
        "funding_rate": "crypto_lake",
        "premium_index": "binance_vision",
        "open_interest": "crypto_lake",
        "agg_trade": "binance_vision",
    }
    manifest_paths: list[Path] = []
    for family, frame in frames.items():
        records = _json_safe_records(frame)
        data_path = tmp_path / f"{family}.jsonl"
        data_path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")
        manifest_path = tmp_path / f"{family}.manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "research_only": True,
                    "observe_only": True,
                    "promotion_ready": False,
                    "source_name": source_names[family],
                    "symbol": "BTCUSDT",
                    "data_family": family,
                    "event_time_field": "event_time_ms",
                    "data_path": str(data_path),
                    "row_count": len(records),
                    "content_hash": f"sha256:{_file_sha256(data_path)}",
                    "receive_time_unavailable_reason": "unit provider context fixture has no receive timestamps",
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        manifest_paths.append(manifest_path)
    return manifest_paths


def _json_safe_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return json.loads(frame.to_json(orient="records"))


def _fixture_context_family_frames(cycle: pd.DataFrame, *, funding_rate_shift: float) -> dict[str, pd.DataFrame]:
    event_time = pd.to_numeric(cycle["signal_bar_time_ms"], errors="coerce") - 60_000
    symbol = cycle["symbol"].astype(str)
    index = pd.Series(range(len(cycle)), index=cycle.index, dtype="float64")
    close = pd.to_numeric(cycle["signal_bar_close"], errors="coerce")
    funding = pd.DataFrame(
        {
            "event_time_ms": event_time,
            "symbol": symbol,
            "funding_rate": 0.0001 + funding_rate_shift + (index * 0.000001),
        }
    )
    funding["funding_rate_change"] = funding["funding_rate"].diff()
    future_funding = pd.DataFrame(
        {
            "event_time_ms": [int(cycle["signal_bar_time_ms"].max()) + 60_000],
            "symbol": ["BTCUSDT"],
            "funding_rate": [0.999],
            "funding_rate_change": [0.0],
        }
    )
    premium_basis_rate = 0.0002 + (index * 0.0000005)
    premium = pd.DataFrame(
        {
            "event_time_ms": event_time,
            "symbol": symbol,
            "mark_price": close * (1.0 + premium_basis_rate),
            "index_price": close,
            "premium_index": premium_basis_rate,
        }
    )
    open_interest = pd.DataFrame(
        {
            "event_time_ms": event_time,
            "symbol": symbol,
            "open_interest": 100_000.0 + (index * 25.0),
        }
    )
    open_interest["open_interest_change"] = open_interest["open_interest"].diff()
    open_interest["open_interest_change_pct"] = open_interest["open_interest"].pct_change()
    agg_trade = pd.DataFrame(
        {
            "event_time_ms": event_time,
            "symbol": symbol,
            "taker_buy_quote_volume": 600.0 + index,
            "quote_volume": 1_000.0 + (index * 2.0),
            "top_of_book_imbalance": 0.15,
            "spread_bps": 2.5,
        }
    )
    return {
        "funding_rate": pd.concat([funding, future_funding], ignore_index=True),
        "premium_index": premium,
        "open_interest": open_interest,
        "agg_trade": agg_trade,
    }


def _without_prejoined_context_columns(cycle: pd.DataFrame) -> pd.DataFrame:
    return cycle.drop(
        columns=[
            "basis_bps",
            "funding_rate",
            "funding_rate_change",
            "open_interest",
            "open_interest_change",
            "open_interest_change_pct",
            "open_interest_value",
            "premium_basis_rate",
            "premium_basis_abs",
            "premium_close",
            "mark_price",
            "index_price",
            "primary_signed_imbalance_ratio",
            "primary_sqrt_signed_imbalance_ratio",
            "top_of_book_imbalance",
            "spread_bps",
        ],
        errors="ignore",
    )


def _lower_timeframe_bars_from_cycle(cycle: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for primary in cycle.to_dict("records"):
        base_time = int(primary["signal_bar_time_ms"])
        base_open = float(primary["signal_bar_open"])
        for offset_ms in (5 * 60_000, 10 * 60_000):
            rows.append(
                {
                    "bar_time_ms": base_time + offset_ms,
                    "symbol": str(primary["symbol"]),
                    "open": base_open,
                    "high": base_open * 1.03,
                    "low": base_open * 0.97,
                    "close": base_open * 1.002,
                    "volume": float(primary.get("signal_bar_volume", 0.0)) / 3.0,
                }
            )
    return pd.DataFrame(rows)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
