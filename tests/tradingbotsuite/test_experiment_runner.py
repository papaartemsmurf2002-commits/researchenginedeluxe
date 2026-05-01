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
) -> Path:
    payload: dict[str, object] = {
        "version": "test-research-experiment-run",
        "name": "Test Research Experiment Run",
        "pipeline_spec": str(pipeline_spec),
        "pipeline_stage": "all",
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

    assert experiment_manifest["experiment_manifest_version"] == "v3-generic-research-experiment-manifest-1"
    assert experiment_manifest["research_only"] is True
    assert {"baseline_no_trade", "trend_following_v1", "hmm_knn_diagnostic_v1"} == set(summary["strategy_id"])
    assert {"anchored_walk_forward", "rolling_walk_forward", "purged_embargoed_split"}.issubset(set(split["validation_method"]))
    assert {"bull_trend", "bear_trend", "volatility_shock"}.issubset(set(regime["regime"]))
    assert {"long", "short"} == set(side["side"])
    assert "research_only_not_promotable" in experiment_manifest["orchestrator_decision"]["failure_reasons"]


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
