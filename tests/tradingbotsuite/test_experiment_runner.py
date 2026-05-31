from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from tradingbotsuite import main
from tradingbotsuite.config import AppConfig, ResearchConfig
from tradingbotsuite.research.deterministic_datasets import write_hmm_knn_sweep_dataset
from tradingbotsuite.research.experiment_runner import (
    DatasetSpec,
    ExperimentSpec,
    FeatureSpec,
    StrategySpec,
    BacktestSpec,
    ValidationSpec,
    SearchSpec,
    ReportSpec,
    ResearchExperimentSpec,
    deterministic_experiment_cache_key,
    expand_search_candidates,
    run_research_experiment,
    write_research_experiment_benchmark_report,
)


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_fast_hmm_knn_config(path: Path) -> Path:
    payload = json.loads(Path("configs/v2_btc_hmm_multi_knn_research.json").read_text(encoding="utf-8"))
    payload["version"] = "test-experiment-runner-hmm-knn"
    payload["hmm"]["n_states"] = 3
    payload["hmm"]["posterior_threshold"] = 0.45
    payload["hmm"]["entropy_threshold"] = 0.95
    payload["knn"]["primary_k"] = 12
    payload["knn"]["k_values"] = [8, 12]
    payload["knn"]["min_neighbor_count"] = 3
    payload["evaluation"]["min_training_rows"] = 36
    payload["evaluation"]["walk_forward_splits"] = 2
    payload["evaluation"]["purge_embargo_bars"] = 2
    payload["acceptance"]["min_trade_count"] = 1
    return _write_json(path, payload)


def _write_experiment_matrix_spec(tmp_path: Path, config_path: Path) -> Path:
    return _write_json(
        tmp_path / "specs" / "hmm_knn_matrix.json",
        {
            "name": "experiment runner fixture matrix",
            "base_config_path": str(config_path),
            "experiments": [
                {
                    "name": "small k softmax",
                    "slug": "small-k-softmax",
                    "owning_agent": "KNN",
                    "run_order": 1,
                    "requires_new_data": False,
                    "can_run_on_current_artifacts": True,
                    "mutations": {
                        "knn.primary_k": 8,
                        "knn.k_values": [8, 12],
                        "knn.primary_weighting": "softmax",
                        "knn.neighbor_weighting": ["softmax"],
                    },
                }
            ],
        },
    )


def _write_pipeline_spec(tmp_path: Path, dataset_path: Path, output_dir: Path) -> Path:
    return _write_json(
        tmp_path / "specs" / "pipeline.json",
        {
            "version": "experiment-runner-pipeline",
            "asset_scope": ["BTCUSDT"],
            "output_dir": str(output_dir / "will-be-overridden"),
            "providers": [
                {"source_name": "binance_vision", "enabled": True, "inputs": []},
                {"source_name": "crypto_lake", "enabled": True, "inputs": []},
                {"source_name": "hyperliquid_archive", "enabled": True, "symbol": "BTCUSDT", "data_family": "order_event", "inputs": []},
            ],
            "dataset_stage": {"enabled": False},
            "evidence_stage": {
                "enabled": True,
                "dataset_path": str(dataset_path),
                "workers": 1,
                "write_monitoring": True,
            },
        },
    )


def _write_research_experiment_spec(
    tmp_path: Path,
    *,
    pipeline_spec: Path,
    experiment_spec: Path | None,
    output_dir: Path,
    required_artifacts: dict[str, bool] | None = None,
    pipeline_stage: str = "all",
) -> Path:
    payload: dict[str, object] = {
        "version": "test-research-experiment-run",
        "name": "Test Research Experiment Run",
        "pipeline_spec": str(pipeline_spec),
        "pipeline_stage": pipeline_stage,
        "output_dir": str(output_dir),
        "workers": 1,
        "write_monitoring": True,
        "required_artifacts": required_artifacts or {"data_quality": True, "dataset": False, "evidence": True},
        "conclusion_policy": "default",
    }
    if experiment_spec is not None:
        payload["experiment_spec"] = str(experiment_spec)
    return _write_json(tmp_path / "specs" / "research_experiment.json", payload)


def test_research_experiment_spec_defaults_and_validation(tmp_path: Path) -> None:
    pipeline_spec = _write_json(
        tmp_path / "pipeline.json",
        {
            "version": "pipeline",
            "asset_scope": ["BTCUSDT"],
            "providers": [],
            "dataset_stage": {"enabled": False},
            "evidence_stage": {"enabled": False},
        },
    )
    spec_path = _write_json(
        tmp_path / "experiment.json",
        {
            "version": "exp",
            "name": "Experiment",
            "pipeline_spec": str(pipeline_spec),
        },
    )

    spec = ResearchExperimentSpec.from_payload(json.loads(spec_path.read_text(encoding="utf-8")), spec_path=spec_path)

    assert spec.pipeline_stage == "all"
    assert spec.workers == 1
    assert spec.write_monitoring is True
    assert spec.required_artifacts == {"data_quality": True, "dataset": False, "evidence": True}


def test_run_research_experiment_writes_bundle_and_conclusion(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    config_path = _write_fast_hmm_knn_config(tmp_path / "specs" / "hmm_knn_config.json")
    experiment_spec = _write_experiment_matrix_spec(tmp_path, config_path)
    output_dir = tmp_path / "research" / "experiments" / "fixture-run"
    pipeline_spec = _write_pipeline_spec(tmp_path, dataset.parquet_path, output_dir)
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=experiment_spec,
        output_dir=output_dir,
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    conclusion = result.conclusion_path.read_text(encoding="utf-8")

    assert manifest["experiment_run_manifest_version"] == "v2-research-experiment-run-manifest-1"
    assert manifest["research_only"] is True
    assert manifest["observe_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["intended_use"] == "research_observe_only"
    assert manifest["live_signal_input"] is False
    assert manifest["position_sizing_input"] is False
    assert manifest["research_boundary"]["passed"] is True
    assert manifest["conclusion"]["status"] in {"supported", "rejected", "inconclusive"}
    assert Path(manifest["artifact_links"]["pipeline_summary_path"]).exists()
    assert Path(manifest["artifact_links"]["evidence_manifest_path"]).exists()
    assert manifest["provider_statuses"][0]["source_name"] == "binance_vision"
    assert manifest["execution_environment"]["packages"]["cupy_available"] in {True, False}
    assert any("GPU/backend metadata is diagnostic" in note for note in manifest["notes"])
    assert Path(manifest["generic_experiment_outputs"]["experiment_manifest_path"]).exists()
    assert Path(manifest["generic_experiment_outputs"]["metrics_by_split_path"]).exists()
    assert "Status:" in conclusion

    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)
    split = pd.read_parquet(result.metrics_by_split_path)
    regime = pd.read_parquet(result.metrics_by_regime_path)
    side = pd.read_parquet(result.metrics_by_side_path)
    rankings = pd.read_parquet(result.candidate_rankings_path)

    assert experiment_manifest["experiment_manifest_version"] == "v3-generic-research-experiment-manifest-1"
    assert experiment_manifest["empirical_result_scope"] == "aggregate_backtest_validation_incomplete"
    assert experiment_manifest["empirical_evidence"] is False
    assert experiment_manifest["aggregate_backtest_evidence"] is True
    assert experiment_manifest["scoreable_candidate_count"] == 0
    assert experiment_manifest["non_scoreable_candidate_count"] == len(summary)
    assert experiment_manifest["candidate_acceptance_allowed"] is False
    assert experiment_manifest["research_only"] is True
    assert Path(experiment_manifest["resolved_dataset_path"]).exists()
    assert len(experiment_manifest["execution_candidates"]) == len(summary)
    validation_status = {
        item["method"]: item["status"]
        for item in experiment_manifest["validation_method_execution"]
    }
    assert validation_status["anchored_walk_forward"] == "executed_by_split_backtests"
    assert validation_status["rolling_walk_forward"] == "executed_by_split_backtests"
    assert validation_status["purged_embargoed_split"] == "executed_by_split_backtests"
    assert validation_status["nested_validation"] == "unsupported_fail_closed"
    assert validation_status["side_separated_reporting"] == "executed_by_required_output"
    assert validation_status["regime_separated_reporting"] == "executed_by_required_output"
    assert {"baseline_no_trade", "trend_following_v1", "hmm_knn_diagnostic_v1"} == set(summary["strategy_id"])
    assert summary["candidate_id"].is_unique
    assert set(summary["metric_scope"]) == {"real_backtest_validation_incomplete"}
    assert set(summary["metrics_source"]) == {"backtest_engine_validation_incomplete"}
    assert set(summary["empirical_evidence"].astype(str).str.lower()) == {"false"}
    assert set(summary["aggregate_backtest_evidence"].astype(str).str.lower()) == {"true"}
    assert set(summary["validation_evidence_complete"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreable_candidate"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreability_status"]) == {"not_scoreable_validation_incomplete"}
    assert summary["final_score"].isna().all()
    assert summary["costed_expectancy"].isna().all()
    assert summary["trade_count"].isna().all()
    assert rankings["final_score"].isna().all()
    assert rankings["rank"].isna().all()
    assert summary["backtest_manifest_path"].map(lambda value: Path(str(value)).exists()).all()
    assert "purged_embargoed_split" in set(split["validation_method"])
    assert set(regime["metric_scope"]) == {"real_backtest"}
    assert {"long", "short"} == set(side["side"])
    assert set(side["metric_scope"]) == {"real_backtest"}
    assert Path(experiment_manifest["required_outputs"]["candidate_rankings"]).exists()
    assert "generic_real_backtest_not_acceptance_evidence" in experiment_manifest["orchestrator_decision"]["failure_reasons"]
    assert "validation_method_not_executed:nested_validation" in experiment_manifest["orchestrator_decision"]["failure_reasons"]
    assert "research_only_not_promotable" in experiment_manifest["orchestrator_decision"]["failure_reasons"]


def test_run_research_experiment_executes_supplied_generic_experiment_spec(tmp_path: Path) -> None:
    pipeline_dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "pipeline-datasets", row_count=120)
    supplied_dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "supplied-datasets", row_count=120)
    output_dir = tmp_path / "research" / "experiments" / "supplied-generic-spec"
    pipeline_spec = _write_pipeline_spec(tmp_path, pipeline_dataset.parquet_path, output_dir)
    supplied_spec = ExperimentSpec(
        experiment_name="supplied price trend vol execution",
        dataset=DatasetSpec(dataset_path=str(supplied_dataset.parquet_path), dataset_manifest_hash="sha256:will-be-overridden"),
        feature=FeatureSpec(feature_set_id="features_price_trend_vol", feature_manifest_hash="sha256:feature-a"),
        strategies=(
            StrategySpec("trend_following_v1", config={"slope_threshold": 0.05, "spacing_bars": 6}),
        ),
        backtest=BacktestSpec(holding_window="4h", fee_bps=1.0, slippage_bps=2.0, funding_stress_bps=(0.0,)),
        validation=ValidationSpec(
            methods=("anchored_walk_forward", "rolling_walk_forward", "purged_embargoed_split"),
            purge_embargo_bars=1,
            trade_count_floor=1,
        ),
        search=SearchSpec(method="grid", parameter_space={"spacing_bars": (6, 12)}, max_candidates=2),
        report=ReportSpec(),
    )
    supplied_spec_path = _write_json(tmp_path / "specs" / "supplied_generic_spec.json", supplied_spec.to_payload())
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=supplied_spec_path,
        output_dir=output_dir,
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)
    split = pd.read_parquet(result.metrics_by_split_path)
    cost_stress = pd.read_parquet(experiment_manifest["required_outputs"]["metrics_by_cost_stress"])

    assert experiment_manifest["supplied_experiment_spec"]["loaded"] is True
    assert experiment_manifest["spec"]["experiment_name"] == "supplied price trend vol execution"
    assert experiment_manifest["spec"]["feature"]["feature_set_id"] == "features_price_trend_vol"
    assert experiment_manifest["spec"]["backtest"]["holding_window"] == "4h"
    assert experiment_manifest["spec"]["dataset"]["dataset_path"] == str(supplied_dataset.parquet_path)
    assert experiment_manifest["resolved_dataset_path"] == str(supplied_dataset.parquet_path)
    assert experiment_manifest["dataset_identity"]["dataset_artifact_sha256"]
    assert experiment_manifest["dataset_identity"]["dataset_identity_hash"] == experiment_manifest["spec"]["dataset"]["dataset_manifest_hash"]
    assert len(experiment_manifest["execution_candidates"]) == 2
    assert len(experiment_manifest["cache_identity"]["candidate_cache_keys"]) == 2
    assert {
        item["method"]: item["status"]
        for item in experiment_manifest["validation_method_execution"]
    } == {
        "anchored_walk_forward": "executed_by_split_backtests",
        "rolling_walk_forward": "executed_by_split_backtests",
        "purged_embargoed_split": "executed_by_split_backtests",
    }
    assert {
        candidate["engine_strategy_config"]["spacing_bars"]
        for candidate in experiment_manifest["execution_candidates"]
    } == {6, 12}
    assert {
        candidate["feature_manifest_hash"]
        for candidate in experiment_manifest["execution_candidates"]
    } == {"sha256:feature-a"}
    assert len(summary) == 2
    assert summary["candidate_id"].is_unique
    assert set(summary["strategy_id"]) == {"trend_following_v1"}
    assert "hmm_knn_diagnostic_v1" not in set(summary["strategy_id"])
    assert {json.loads(raw)["spacing_bars"] for raw in summary["search_parameters_json"]} == {6, 12}
    assert set(summary["metric_scope"]) == {"real_backtest"}
    assert summary["backtest_manifest_path"].map(lambda value: Path(str(value)).exists()).all()
    assert not split.empty
    assert set(split["validation_method"]) == {"anchored_walk_forward", "rolling_walk_forward", "purged_embargoed_split"}
    assert set(cost_stress["funding_stress_bps"]) == {0.0}
    executed_spacing_bars = set()
    for _, row in summary.iterrows():
        backtest_manifest = json.loads(Path(str(row["backtest_manifest_path"])).read_text(encoding="utf-8"))
        resolved_config_path = Path(backtest_manifest["required_outputs"]["config_resolved"])
        resolved_config = json.loads(resolved_config_path.read_text(encoding="utf-8"))
        executed_spacing_bars.add(int(resolved_config["strategy_config"]["spacing_bars"]))
        assert backtest_manifest["strategy_id"] == "trend_following_v1"
        assert backtest_manifest["holding_window"] == "4h"
        assert backtest_manifest["feature_set_id"] == "features_price_trend_vol"
        assert backtest_manifest["feature_manifest_sha256"] == "sha256:feature-a"
        assert backtest_manifest["cost_model"]["fee_bps"] == 1.0
        assert backtest_manifest["cost_model"]["slippage_bps"] == 2.0
        assert resolved_config["fee_bps"] == 1.0
        assert resolved_config["slippage_bps"] == 2.0
        assert resolved_config["strategy_config"]["slope_threshold"] == 0.05
    assert executed_spacing_bars == {6, 12}


def test_run_research_experiment_marks_unsupported_configured_validation_non_scoreable(tmp_path: Path) -> None:
    pipeline_dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "pipeline-datasets", row_count=120)
    supplied_dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "supplied-datasets", row_count=120)
    output_dir = tmp_path / "research" / "experiments" / "unsupported-validation-spec"
    pipeline_spec = _write_pipeline_spec(tmp_path, pipeline_dataset.parquet_path, output_dir)
    supplied_spec = ExperimentSpec(
        experiment_name="unsupported validation fail closed",
        dataset=DatasetSpec(dataset_path=str(supplied_dataset.parquet_path), dataset_manifest_hash="sha256:will-be-overridden"),
        feature=FeatureSpec(feature_set_id="features_price_trend_vol", feature_manifest_hash="sha256:feature-a"),
        strategies=(StrategySpec("trend_following_v1", config={"slope_threshold": 0.05, "spacing_bars": 6}),),
        backtest=BacktestSpec(holding_window="4h", fee_bps=1.0, slippage_bps=2.0, funding_stress_bps=(0.0,)),
        validation=ValidationSpec(methods=("anchored_walk_forward", "nested_validation"), purge_embargo_bars=1, trade_count_floor=1),
        search=SearchSpec(method="grid", parameter_space={}, max_candidates=1),
        report=ReportSpec(),
    )
    supplied_spec_path = _write_json(tmp_path / "specs" / "unsupported_validation_generic_spec.json", supplied_spec.to_payload())
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=supplied_spec_path,
        output_dir=output_dir,
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)
    split = pd.read_parquet(result.metrics_by_split_path)
    rankings = pd.read_parquet(result.candidate_rankings_path)

    assert experiment_manifest["empirical_result_scope"] == "aggregate_backtest_validation_incomplete"
    assert experiment_manifest["aggregate_backtest_evidence"] is True
    assert experiment_manifest["scoreable_candidate_count"] == 0
    assert {
        item["method"]: item["status"]
        for item in experiment_manifest["validation_method_execution"]
    } == {
        "anchored_walk_forward": "executed_by_split_backtests",
        "nested_validation": "unsupported_fail_closed",
    }
    assert "anchored_walk_forward" in set(split["validation_method"])
    assert "validation_method_not_executed:nested_validation" in experiment_manifest["orchestrator_decision"]["failure_reasons"]
    assert summary["failure_reasons"].str.contains("validation_method_not_executed:nested_validation", regex=False).all()
    assert set(summary["metric_scope"]) == {"real_backtest_validation_incomplete"}
    assert set(summary["aggregate_backtest_evidence"].astype(str).str.lower()) == {"true"}
    assert set(summary["validation_evidence_complete"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreable_candidate"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreability_status"]) == {"not_scoreable_validation_incomplete"}
    assert summary["final_score"].isna().all()
    assert rankings["rank"].isna().all()


def test_run_research_experiment_ignores_malformed_supplied_spec_safely(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    output_dir = tmp_path / "research" / "experiments" / "malformed-supplied-spec"
    pipeline_spec = _write_pipeline_spec(tmp_path, dataset.parquet_path, output_dir)
    malformed_spec = tmp_path / "specs" / "malformed_generic_spec.json"
    malformed_spec.parent.mkdir(parents=True, exist_ok=True)
    malformed_spec.write_text("{not valid json", encoding="utf-8")
    pipeline_payload = json.loads(pipeline_spec.read_text(encoding="utf-8"))
    pipeline_payload["evidence_stage"]["experiment_spec"] = str(malformed_spec)
    pipeline_spec.write_text(json.dumps(pipeline_payload, indent=2, sort_keys=True), encoding="utf-8")
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=malformed_spec,
        output_dir=output_dir,
        required_artifacts={"data_quality": True, "dataset": False, "evidence": False},
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)

    assert experiment_manifest["supplied_experiment_spec"]["loaded"] is False
    assert experiment_manifest["supplied_experiment_spec"]["status"] == "ignored_non_generic_experiment_spec"
    assert "JSONDecodeError" in experiment_manifest["supplied_experiment_spec"]["reason"]
    assert experiment_manifest["resolved_dataset_path"] == str(dataset.parquet_path)
    effective_pipeline_spec = json.loads(Path(experiment_manifest["artifact_links"]["effective_pipeline_spec_path"]).read_text(encoding="utf-8"))
    assert "experiment_spec" not in effective_pipeline_spec["evidence_stage"]
    assert experiment_manifest["empirical_result_scope"] == "aggregate_backtest_validation_incomplete"
    assert experiment_manifest["scoreable_candidate_count"] == 0
    assert "validation_method_not_executed:nested_validation" in experiment_manifest["orchestrator_decision"]["failure_reasons"]
    assert {"baseline_no_trade", "trend_following_v1", "hmm_knn_diagnostic_v1"} == set(summary["strategy_id"])
    assert set(summary["metric_scope"]) == {"real_backtest_validation_incomplete"}
    assert set(summary["scoreable_candidate"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreability_status"]) == {"not_scoreable_validation_incomplete"}


def test_run_research_experiment_reports_missing_required_dataset_as_inconclusive(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    config_path = _write_fast_hmm_knn_config(tmp_path / "specs" / "hmm_knn_config.json")
    experiment_spec = _write_experiment_matrix_spec(tmp_path, config_path)
    output_dir = tmp_path / "research" / "experiments" / "missing-dataset-run"
    pipeline_spec = _write_pipeline_spec(tmp_path, dataset.parquet_path, output_dir)
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=experiment_spec,
        output_dir=output_dir,
        required_artifacts={"data_quality": True, "dataset": True, "evidence": True},
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["conclusion"]["status"] == "inconclusive"
    assert any(
        reason["code"] == "missing_required_artifact:dataset"
        for reason in manifest["conclusion"]["top_failure_reasons"]
    )


def test_run_research_experiment_blocks_generic_outputs_without_dataset(tmp_path: Path) -> None:
    output_dir = tmp_path / "research" / "experiments" / "contract-only-run"
    pipeline_spec = _write_json(
        tmp_path / "specs" / "pipeline_no_dataset.json",
        {
            "version": "experiment-runner-no-dataset",
            "asset_scope": ["BTCUSDT"],
            "output_dir": str(output_dir / "will-be-overridden"),
            "providers": [],
            "dataset_stage": {"enabled": False},
            "evidence_stage": {"enabled": False},
        },
    )
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=None,
        output_dir=output_dir,
        required_artifacts={"data_quality": True, "dataset": False, "evidence": False},
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)
    split = pd.read_parquet(result.metrics_by_split_path)
    regime = pd.read_parquet(result.metrics_by_regime_path)
    side = pd.read_parquet(result.metrics_by_side_path)
    cost_stress = pd.read_parquet(experiment_manifest["required_outputs"]["metrics_by_cost_stress"])
    rankings = pd.read_parquet(result.candidate_rankings_path)

    assert experiment_manifest["empirical_result_scope"] == "not_run_missing_dataset"
    assert experiment_manifest["empirical_evidence"] is False
    assert experiment_manifest["metrics_source"] == "not_run_no_dataset"
    assert {
        item["status"]
        for item in experiment_manifest["validation_method_execution"]
    } == {"not_run_missing_dataset"}
    assert set(summary["metric_scope"]) == {"not_run_missing_dataset"}
    assert set(summary["metrics_source"]) == {"not_run_no_dataset"}
    assert set(summary["scoreable_candidate"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreability_status"]) == {"not_scoreable_missing_dataset"}
    assert summary["final_score"].isna().all()
    assert summary["costed_expectancy"].isna().all()
    assert summary["trade_count"].isna().all()
    assert set(summary["backtest_manifest_path"].fillna("")) == {""}
    assert split.empty
    assert regime.empty
    assert side.empty
    assert cost_stress.empty
    assert set(rankings["metric_scope"]) == {"not_run_missing_dataset"}
    assert set(rankings["empirical_evidence"].astype(str).str.lower()) == {"false"}
    assert set(rankings["scoreable_candidate"].astype(str).str.lower()) == {"false"}
    assert rankings["final_score"].isna().all()
    assert rankings["rank"].isna().all()
    assert "generic_experiment_not_run_dataset_missing" in experiment_manifest["orchestrator_decision"]["failure_reasons"]


def test_run_research_experiment_fails_closed_when_validation_splits_do_not_run(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "short-datasets-source", row_count=80)
    short_dataset_path = tmp_path / "short-datasets" / "short_dataset.parquet"
    short_dataset_path.parent.mkdir(parents=True, exist_ok=True)
    pd.read_parquet(dataset.parquet_path).head(10).to_parquet(short_dataset_path, index=False)
    output_dir = tmp_path / "research" / "experiments" / "short-validation-run"
    pipeline_spec = _write_pipeline_spec(tmp_path, short_dataset_path, output_dir)
    supplied_spec = ExperimentSpec(
        experiment_name="short validation execution",
        dataset=DatasetSpec(dataset_path=str(short_dataset_path), dataset_manifest_hash="sha256:short-dataset"),
        feature=FeatureSpec(feature_set_id="features_price_trend_vol", feature_manifest_hash="sha256:short-feature"),
        strategies=(StrategySpec("trend_following_v1", config={"slope_threshold": 0.05, "spacing_bars": 2}),),
        backtest=BacktestSpec(holding_window="4h", fee_bps=1.0, slippage_bps=1.0, funding_stress_bps=(0.0,)),
        validation=ValidationSpec(methods=("anchored_walk_forward", "purged_embargoed_split"), trade_count_floor=1),
        search=SearchSpec(method="grid", parameter_space={}, max_candidates=1),
        report=ReportSpec(),
    )
    supplied_spec_path = _write_json(tmp_path / "specs" / "short_validation_generic_spec.json", supplied_spec.to_payload())
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=supplied_spec_path,
        output_dir=output_dir,
        required_artifacts={"data_quality": True, "dataset": False, "evidence": False},
        pipeline_stage="intake",
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)
    split = pd.read_parquet(result.metrics_by_split_path)
    rankings = pd.read_parquet(result.candidate_rankings_path)

    assert experiment_manifest["empirical_result_scope"] == "aggregate_backtest_validation_incomplete"
    assert experiment_manifest["empirical_evidence"] is False
    assert experiment_manifest["aggregate_backtest_evidence"] is True
    assert experiment_manifest["scoreable_candidate_count"] == 0
    assert split.empty
    assert {
        item["status"]
        for item in experiment_manifest["validation_method_execution"]
    } == {"not_executed_fail_closed"}
    assert "validation_method_not_executed:anchored_walk_forward" in experiment_manifest["orchestrator_decision"]["failure_reasons"]
    assert "validation_method_not_executed:purged_embargoed_split" in experiment_manifest["orchestrator_decision"]["failure_reasons"]
    assert summary["failure_reasons"].str.contains("validation_method_not_executed:anchored_walk_forward", regex=False).all()
    assert set(summary["metric_scope"]) == {"real_backtest_validation_incomplete"}
    assert set(summary["scoreable_candidate"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreability_status"]) == {"not_scoreable_validation_incomplete"}
    assert summary["final_score"].isna().all()
    assert rankings["final_score"].isna().all()
    assert rankings["rank"].isna().all()


def test_run_research_experiment_does_not_count_failed_split_validation_as_executed(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    output_dir = tmp_path / "research" / "experiments" / "failed-split-validation-run"
    pipeline_spec = _write_pipeline_spec(tmp_path, dataset.parquet_path, output_dir)
    supplied_spec = ExperimentSpec(
        experiment_name="failed split validation execution",
        dataset=DatasetSpec(dataset_path=str(dataset.parquet_path), dataset_manifest_hash="sha256:dataset"),
        feature=FeatureSpec(feature_set_id="features_price_trend_vol", feature_manifest_hash="sha256:feature"),
        strategies=(StrategySpec("trend_following_v1", config={"slope_threshold": 0.05, "spacing_bars": 2}),),
        backtest=BacktestSpec(holding_window="1h", fee_bps=1.0, slippage_bps=1.0, funding_stress_bps=(0.0,)),
        validation=ValidationSpec(methods=("anchored_walk_forward",), trade_count_floor=1),
        search=SearchSpec(method="grid", parameter_space={}, max_candidates=1),
        report=ReportSpec(),
    )
    supplied_spec_path = _write_json(tmp_path / "specs" / "failed_split_generic_spec.json", supplied_spec.to_payload())
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=supplied_spec_path,
        output_dir=output_dir,
        required_artifacts={"data_quality": True, "dataset": False, "evidence": False},
        pipeline_stage="intake",
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)
    split = pd.read_parquet(result.metrics_by_split_path)
    rankings = pd.read_parquet(result.candidate_rankings_path)

    assert set(split["metric_scope"]) == {"real_backtest_failed"}
    assert experiment_manifest["empirical_result_scope"] == "real_backtest_failed"
    assert experiment_manifest["empirical_evidence"] is False
    assert experiment_manifest["aggregate_backtest_evidence"] is False
    assert experiment_manifest["scoreable_candidate_count"] == 0
    assert {
        item["status"]
        for item in experiment_manifest["validation_method_execution"]
    } == {"not_executed_fail_closed"}
    assert "validation_method_not_executed:anchored_walk_forward" in experiment_manifest["orchestrator_decision"]["failure_reasons"]
    assert summary["failure_reasons"].str.contains("validation_method_not_executed:anchored_walk_forward", regex=False).all()
    assert set(summary["metric_scope"]) == {"real_backtest_failed"}
    assert set(summary["scoreable_candidate"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreability_status"]) == {"not_scoreable_backtest_failed"}
    assert summary["final_score"].isna().all()
    assert rankings["rank"].isna().all()


def test_run_research_experiment_report_validation_status_requires_real_rows(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    output_dir = tmp_path / "research" / "experiments" / "failed-report-validation-run"
    pipeline_spec = _write_pipeline_spec(tmp_path, dataset.parquet_path, output_dir)
    supplied_spec = ExperimentSpec(
        experiment_name="failed report validation execution",
        dataset=DatasetSpec(dataset_path=str(dataset.parquet_path), dataset_manifest_hash="sha256:dataset"),
        feature=FeatureSpec(feature_set_id="features_price_trend_vol", feature_manifest_hash="sha256:feature"),
        strategies=(StrategySpec("trend_following_v1", config={"slope_threshold": 0.05, "spacing_bars": 2}),),
        backtest=BacktestSpec(holding_window="15m", fee_bps=1.0, slippage_bps=1.0, funding_stress_bps=(0.0,)),
        validation=ValidationSpec(
            methods=("side_separated_reporting", "regime_separated_reporting", "cost_slippage_funding_stress"),
            trade_count_floor=1,
        ),
        search=SearchSpec(method="grid", parameter_space={}, max_candidates=1),
        report=ReportSpec(),
    )
    supplied_spec_path = _write_json(tmp_path / "specs" / "failed_report_generic_spec.json", supplied_spec.to_payload())
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=supplied_spec_path,
        output_dir=output_dir,
        required_artifacts={"data_quality": True, "dataset": False, "evidence": False},
        pipeline_stage="intake",
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)
    cost_stress = pd.read_parquet(experiment_manifest["required_outputs"]["metrics_by_cost_stress"])

    assert experiment_manifest["empirical_result_scope"] == "real_backtest_failed"
    assert experiment_manifest["empirical_evidence"] is False
    assert experiment_manifest["aggregate_backtest_evidence"] is False
    assert {
        item["method"]: item["status"]
        for item in experiment_manifest["validation_method_execution"]
    } == {
        "side_separated_reporting": "not_executed_fail_closed",
        "regime_separated_reporting": "not_executed_fail_closed",
        "cost_slippage_funding_stress": "not_executed_fail_closed",
    }
    assert set(summary["metric_scope"]) == {"real_backtest_failed"}
    assert set(summary["scoreability_status"]) == {"not_scoreable_backtest_failed"}
    assert summary["final_score"].isna().all()
    assert cost_stress.empty


def test_run_research_experiment_report_validation_not_executed_blocks_scoreability(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    output_dir = tmp_path / "research" / "experiments" / "missing-cost-stress-validation-run"
    pipeline_spec = _write_pipeline_spec(tmp_path, dataset.parquet_path, output_dir)
    supplied_spec = ExperimentSpec(
        experiment_name="missing cost stress validation execution",
        dataset=DatasetSpec(dataset_path=str(dataset.parquet_path), dataset_manifest_hash="sha256:dataset"),
        feature=FeatureSpec(feature_set_id="features_price_trend_vol", feature_manifest_hash="sha256:feature"),
        strategies=(StrategySpec("trend_following_v1", config={"slope_threshold": 0.05, "spacing_bars": 6}),),
        backtest=BacktestSpec(holding_window="4h", fee_bps=1.0, slippage_bps=1.0, funding_stress_bps=()),
        validation=ValidationSpec(methods=("cost_slippage_funding_stress",), trade_count_floor=1),
        search=SearchSpec(method="grid", parameter_space={}, max_candidates=1),
        report=ReportSpec(),
    )
    supplied_spec_path = _write_json(tmp_path / "specs" / "missing_cost_stress_generic_spec.json", supplied_spec.to_payload())
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=supplied_spec_path,
        output_dir=output_dir,
        required_artifacts={"data_quality": True, "dataset": False, "evidence": False},
        pipeline_stage="intake",
    )

    result = run_research_experiment(
        spec_path=spec_path,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    experiment_manifest = json.loads(result.experiment_manifest_path.read_text(encoding="utf-8"))
    summary = pd.read_csv(result.experiment_summary_path)
    cost_stress = pd.read_parquet(experiment_manifest["required_outputs"]["metrics_by_cost_stress"])
    rankings = pd.read_parquet(result.candidate_rankings_path)

    assert experiment_manifest["empirical_result_scope"] == "aggregate_backtest_validation_incomplete"
    assert experiment_manifest["aggregate_backtest_evidence"] is True
    assert experiment_manifest["scoreable_candidate_count"] == 0
    assert {
        item["method"]: item["status"]
        for item in experiment_manifest["validation_method_execution"]
    } == {"cost_slippage_funding_stress": "not_executed_fail_closed"}
    assert "validation_method_not_executed:cost_slippage_funding_stress" in experiment_manifest["orchestrator_decision"]["failure_reasons"]
    assert summary["failure_reasons"].str.contains("validation_method_not_executed:cost_slippage_funding_stress", regex=False).all()
    assert set(summary["metric_scope"]) == {"real_backtest_validation_incomplete"}
    assert set(summary["aggregate_backtest_evidence"].astype(str).str.lower()) == {"true"}
    assert set(summary["validation_evidence_complete"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreable_candidate"].astype(str).str.lower()) == {"false"}
    assert set(summary["scoreability_status"]) == {"not_scoreable_validation_incomplete"}
    assert summary["final_score"].isna().all()
    assert rankings["rank"].isna().all()
    assert cost_stress.empty


def test_research_experiment_cli_command_runs(tmp_path: Path, monkeypatch) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    config_path = _write_fast_hmm_knn_config(tmp_path / "specs" / "hmm_knn_config.json")
    experiment_spec = _write_experiment_matrix_spec(tmp_path, config_path)
    output_dir = tmp_path / "research" / "experiments" / "cli-run"
    pipeline_spec = _write_pipeline_spec(tmp_path, dataset.parquet_path, output_dir)
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=experiment_spec,
        output_dir=output_dir,
    )
    monkeypatch.setattr(sys, "argv", ["tradingbot", "run-research-experiment", "--spec", str(spec_path)])

    args = main.parse_args()
    payload = main._run_research_experiment_command(args)

    assert Path(str(payload["experiment_run_manifest_path"])).exists()
    assert Path(str(payload["conclusion_path"])).exists()


def test_research_experiment_benchmark_report_records_runs(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    config_path = _write_fast_hmm_knn_config(tmp_path / "specs" / "hmm_knn_config.json")
    experiment_spec = _write_experiment_matrix_spec(tmp_path, config_path)
    output_dir = tmp_path / "research" / "experiments" / "benchmark-source"
    pipeline_spec = _write_pipeline_spec(tmp_path, dataset.parquet_path, output_dir)
    spec_path = _write_research_experiment_spec(
        tmp_path,
        pipeline_spec=pipeline_spec,
        experiment_spec=experiment_spec,
        output_dir=output_dir,
    )

    report_path = write_research_experiment_benchmark_report(
        spec_path=spec_path,
        output_dir=tmp_path / "research" / "benchmarks",
        repeat=1,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["benchmark_report_version"] == "v2-research-experiment-benchmark-1"
    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["promotion_ready"] is False
    assert len(report["runs"]) == 1
    assert Path(report["runs"][0]["manifest_path"]).exists()


def test_research_experiment_benchmark_resolves_source_relative_specs_before_copy(tmp_path: Path) -> None:
    dataset = write_hmm_knn_sweep_dataset(output_dir=tmp_path / "datasets", row_count=120)
    repo_like = tmp_path / "repo-like"
    repo_dataset = repo_like / "data" / "dataset.parquet"
    repo_dataset.parent.mkdir(parents=True)
    pd.read_parquet(dataset.parquet_path).to_parquet(repo_dataset, index=False)
    config_path = _write_fast_hmm_knn_config(repo_like / "configs" / "experiments" / "hmm_knn_config.json")
    experiment_spec = _write_experiment_matrix_spec(repo_like / "configs", config_path)
    output_dir = tmp_path / "research" / "experiments" / "source-relative"
    pipeline_spec = _write_json(
        repo_like / "configs" / "specs" / "pipeline.json",
        {
            "version": "experiment-runner-pipeline",
            "asset_scope": ["BTCUSDT"],
            "output_dir": str(output_dir / "will-be-overridden"),
            "providers": [
                {"source_name": "binance_vision", "enabled": True, "inputs": []},
            ],
            "dataset_stage": {"enabled": False},
            "evidence_stage": {
                "enabled": True,
                "dataset_path": "../../data/dataset.parquet",
                "hmm_knn_config": "../experiments/hmm_knn_config.json",
                "workers": 1,
                "write_monitoring": True,
            },
        },
    )
    spec_dir = repo_like / "configs" / "experiments"
    spec_path = _write_json(
        spec_dir / "research_experiment.json",
        {
            "version": "test-research-experiment-relative-run",
            "name": "Test Research Experiment Relative Run",
            "pipeline_spec": "../specs/pipeline.json",
            "pipeline_stage": "all",
            "experiment_spec": "../specs/hmm_knn_matrix.json",
            "output_dir": str(output_dir),
            "workers": 1,
            "write_monitoring": True,
            "required_artifacts": {"data_quality": True, "dataset": False, "evidence": True},
            "conclusion_policy": "default",
        },
    )

    report_path = write_research_experiment_benchmark_report(
        spec_path=spec_path,
        output_dir=tmp_path / "research" / "benchmarks",
        repeat=1,
        app_config=AppConfig(research=ResearchConfig(output_dir=tmp_path / "research")),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    benchmark_spec = json.loads((report_path.parent / "benchmark_spec_1.json").read_text(encoding="utf-8"))
    run_manifest = json.loads(Path(report["runs"][0]["manifest_path"]).read_text(encoding="utf-8"))
    effective_pipeline = json.loads(Path(run_manifest["artifact_links"]["effective_pipeline_spec_path"]).read_text(encoding="utf-8"))

    assert Path(benchmark_spec["pipeline_spec"]).exists()
    assert Path(benchmark_spec["experiment_spec"]).exists()
    assert Path(report["runs"][0]["manifest_path"]).exists()
    assert Path(effective_pipeline["evidence_stage"]["dataset_path"]).resolve() == repo_dataset.resolve()
    assert Path(effective_pipeline["evidence_stage"]["hmm_knn_config"]).resolve() == config_path.resolve()


def test_generic_experiment_specs_cache_and_search_are_deterministic() -> None:
    spec = ExperimentSpec(
        experiment_name="deterministic generic experiment",
        dataset=DatasetSpec(dataset_manifest_hash="dataset-a"),
        feature=FeatureSpec(feature_manifest_hash="feature-a"),
        strategies=(StrategySpec("baseline_no_trade"), StrategySpec("hmm_knn_diagnostic_v1", strategy_type="hmm_knn_research")),
        backtest=BacktestSpec(engine_version="engine-a"),
        validation=ValidationSpec(purge_embargo_bars=3),
        search=SearchSpec(method="latin_hypercube", parameter_space={"k": (8, 12), "distance": ("lorentzian", "euclidean_robust_z")}, max_candidates=3),
        report=ReportSpec(),
    )
    validation_hash = deterministic_experiment_cache_key(
        dataset_manifest_hash=spec.dataset.dataset_manifest_hash,
        feature_manifest_hash=spec.feature.feature_manifest_hash,
        strategy_config_hash="strategy-a",
        backtest_engine_version=spec.backtest.engine_version,
        validation_spec_hash="validation-a",
    )

    assert validation_hash == deterministic_experiment_cache_key(
        dataset_manifest_hash="dataset-a",
        feature_manifest_hash="feature-a",
        strategy_config_hash="strategy-a",
        backtest_engine_version="engine-a",
        validation_spec_hash="validation-a",
    )
    assert len(expand_search_candidates(spec.search)) == 3
    assert ExperimentSpec.from_payload(spec.to_payload()).to_payload() == spec.to_payload()
