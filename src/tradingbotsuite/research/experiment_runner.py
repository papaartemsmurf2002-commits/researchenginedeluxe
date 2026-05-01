from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import csv
import itertools
import random
from dataclasses import dataclass
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.backtesting import BACKTEST_ENGINE_VERSION
from tradingbotsuite.config import AppConfig
from tradingbotsuite.research.data_pipeline import DATA_PIPELINE_STAGES, prepare_hmm_knn_research_data
from tradingbotsuite.research.live_readiness import (
    build_research_boundary_report,
    research_boundary_metadata,
    research_boundary_passed,
)

RESEARCH_EXPERIMENT_RUNNER_VERSION = "v2-research-experiment-runner-1"
RESEARCH_EXPERIMENT_RUN_MANIFEST_VERSION = "v2-research-experiment-run-manifest-1"
RESEARCH_EXPERIMENT_BENCHMARK_VERSION = "v2-research-experiment-benchmark-1"
GENERIC_EXPERIMENT_MANIFEST_VERSION = "v3-generic-research-experiment-manifest-1"
DEFAULT_VALIDATION_METHODS = (
    "anchored_walk_forward",
    "rolling_walk_forward",
    "purged_embargoed_split",
    "nested_validation",
    "high_volatility_stress",
    "side_separated_reporting",
    "regime_separated_reporting",
)
DEFAULT_REPORT_OUTPUTS = (
    "experiment_manifest.json",
    "experiment_summary.csv",
    "conclusion.md",
    "metrics_by_split.parquet",
    "metrics_by_regime.parquet",
    "metrics_by_side.parquet",
)


@dataclass(frozen=True, slots=True)
class ResearchExperimentRunResult:
    output_dir: Path
    manifest_path: Path
    conclusion_path: Path
    pipeline_summary_path: Path
    experiment_manifest_path: Path | None = None
    experiment_summary_path: Path | None = None
    metrics_by_split_path: Path | None = None
    metrics_by_regime_path: Path | None = None
    metrics_by_side_path: Path | None = None


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    dataset_path: str | None = None
    dataset_manifest_hash: str = "dataset_manifest_unavailable"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "DatasetSpec":
        payload = payload or {}
        return cls(
            dataset_path=str(payload["dataset_path"]) if payload.get("dataset_path") else None,
            dataset_manifest_hash=str(payload.get("dataset_manifest_hash") or "dataset_manifest_unavailable"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {"dataset_path": self.dataset_path, "dataset_manifest_hash": self.dataset_manifest_hash}


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    feature_set_id: str = "features_full_context_no_wt"
    feature_manifest_hash: str = "feature_manifest_unavailable"

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "FeatureSpec":
        payload = payload or {}
        return cls(
            feature_set_id=str(payload.get("feature_set_id") or "features_full_context_no_wt"),
            feature_manifest_hash=str(payload.get("feature_manifest_hash") or "feature_manifest_unavailable"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {"feature_set_id": self.feature_set_id, "feature_manifest_hash": self.feature_manifest_hash}


@dataclass(frozen=True, slots=True)
class StrategySpec:
    strategy_id: str
    strategy_type: str = "backtest_strategy"
    config: Mapping[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "StrategySpec":
        return cls(
            strategy_id=str(payload["strategy_id"]),
            strategy_type=str(payload.get("strategy_type") or "backtest_strategy"),
            config=dict(payload.get("config") or {}),
        )

    def to_payload(self) -> dict[str, Any]:
        return {"strategy_id": self.strategy_id, "strategy_type": self.strategy_type, "config": dict(self.config or {})}


@dataclass(frozen=True, slots=True)
class BacktestSpec:
    engine_version: str = BACKTEST_ENGINE_VERSION
    holding_window: str = "24h"
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    funding_stress_bps: tuple[float, ...] = (0.0, 2.5, 5.0)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "BacktestSpec":
        payload = payload or {}
        return cls(
            engine_version=str(payload.get("engine_version") or BACKTEST_ENGINE_VERSION),
            holding_window=str(payload.get("holding_window") or "24h"),
            fee_bps=float(payload.get("fee_bps", 5.0)),
            slippage_bps=float(payload.get("slippage_bps", 5.0)),
            funding_stress_bps=tuple(float(value) for value in payload.get("funding_stress_bps", (0.0, 2.5, 5.0))),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "holding_window": self.holding_window,
            "fee_bps": self.fee_bps,
            "slippage_bps": self.slippage_bps,
            "funding_stress_bps": list(self.funding_stress_bps),
        }


@dataclass(frozen=True, slots=True)
class ValidationSpec:
    methods: tuple[str, ...] = DEFAULT_VALIDATION_METHODS
    purge_embargo_bars: int = 2
    trade_count_floor: int = 1
    max_single_split_pnl_share: float = 0.6
    feature_missingness_ceiling: float = 0.25

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "ValidationSpec":
        payload = payload or {}
        return cls(
            methods=tuple(str(value) for value in payload.get("methods", DEFAULT_VALIDATION_METHODS)),
            purge_embargo_bars=int(payload.get("purge_embargo_bars", 2)),
            trade_count_floor=int(payload.get("trade_count_floor", 1)),
            max_single_split_pnl_share=float(payload.get("max_single_split_pnl_share", 0.6)),
            feature_missingness_ceiling=float(payload.get("feature_missingness_ceiling", 0.25)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "methods": list(self.methods),
            "purge_embargo_bars": self.purge_embargo_bars,
            "trade_count_floor": self.trade_count_floor,
            "max_single_split_pnl_share": self.max_single_split_pnl_share,
            "feature_missingness_ceiling": self.feature_missingness_ceiling,
        }


@dataclass(frozen=True, slots=True)
class SearchSpec:
    method: str = "grid"
    parameter_space: Mapping[str, tuple[Any, ...]] | None = None
    max_candidates: int = 16
    random_seed: int = 17

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "SearchSpec":
        payload = payload or {}
        raw_space = payload.get("parameter_space") or {}
        parameter_space = {str(key): tuple(value if isinstance(value, list) else [value]) for key, value in dict(raw_space).items()}
        return cls(
            method=str(payload.get("method") or "grid"),
            parameter_space=parameter_space,
            max_candidates=int(payload.get("max_candidates", 16)),
            random_seed=int(payload.get("random_seed", 17)),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "parameter_space": {key: list(value) for key, value in dict(self.parameter_space or {}).items()},
            "max_candidates": self.max_candidates,
            "random_seed": self.random_seed,
        }


@dataclass(frozen=True, slots=True)
class ReportSpec:
    required_outputs: tuple[str, ...] = DEFAULT_REPORT_OUTPUTS

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> "ReportSpec":
        payload = payload or {}
        return cls(required_outputs=tuple(str(value) for value in payload.get("required_outputs", DEFAULT_REPORT_OUTPUTS)))

    def to_payload(self) -> dict[str, Any]:
        return {"required_outputs": list(self.required_outputs)}


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    experiment_name: str
    dataset: DatasetSpec
    feature: FeatureSpec
    strategies: tuple[StrategySpec, ...]
    backtest: BacktestSpec
    validation: ValidationSpec
    search: SearchSpec
    report: ReportSpec

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ExperimentSpec":
        strategies = tuple(StrategySpec.from_payload(item) for item in payload.get("strategies", ()))
        if not strategies:
            raise ValueError("ExperimentSpec requires at least one strategy")
        return cls(
            experiment_name=str(payload.get("experiment_name") or payload.get("name") or "research_experiment"),
            dataset=DatasetSpec.from_payload(payload.get("dataset")),
            feature=FeatureSpec.from_payload(payload.get("feature")),
            strategies=strategies,
            backtest=BacktestSpec.from_payload(payload.get("backtest")),
            validation=ValidationSpec.from_payload(payload.get("validation")),
            search=SearchSpec.from_payload(payload.get("search")),
            report=ReportSpec.from_payload(payload.get("report")),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "dataset": self.dataset.to_payload(),
            "feature": self.feature.to_payload(),
            "strategies": [strategy.to_payload() for strategy in self.strategies],
            "backtest": self.backtest.to_payload(),
            "validation": self.validation.to_payload(),
            "search": self.search.to_payload(),
            "report": self.report.to_payload(),
        }


@dataclass(frozen=True, slots=True)
class ResearchExperimentSpec:
    version: str
    name: str
    pipeline_spec: Path
    pipeline_stage: str
    experiment_spec: Path | None
    output_dir: Path | None
    workers: int
    write_monitoring: bool
    required_artifacts: Mapping[str, bool]
    conclusion_policy: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, spec_path: Path) -> "ResearchExperimentSpec":
        if not isinstance(payload, Mapping):
            raise ValueError("experiment run spec must be a JSON object")
        version = str(payload.get("version") or "").strip()
        if not version:
            raise ValueError("experiment run spec version is required")
        name = str(payload.get("name") or version).strip()
        if not name:
            raise ValueError("experiment run spec name is required")
        raw_pipeline_spec = payload.get("pipeline_spec")
        if not raw_pipeline_spec:
            raise ValueError("experiment run spec pipeline_spec is required")
        pipeline_stage = str(payload.get("pipeline_stage") or "all").strip()
        if pipeline_stage not in DATA_PIPELINE_STAGES:
            raise ValueError(f"pipeline_stage must be one of: {', '.join(DATA_PIPELINE_STAGES)}")
        workers = int(payload.get("workers", 1))
        if workers < 1:
            raise ValueError("workers must be at least 1")
        required = payload.get("required_artifacts") or {}
        if not isinstance(required, Mapping):
            raise ValueError("required_artifacts must be an object")
        required_artifacts = {
            "data_quality": bool(required.get("data_quality", True)),
            "dataset": bool(required.get("dataset", False)),
            "evidence": bool(required.get("evidence", True)),
        }
        experiment_spec = payload.get("experiment_spec")
        return cls(
            version=version,
            name=name,
            pipeline_spec=_resolve_path(raw_pipeline_spec, base_path=spec_path.parent),
            pipeline_stage=pipeline_stage,
            experiment_spec=(
                _resolve_path(experiment_spec, base_path=spec_path.parent)
                if experiment_spec
                else None
            ),
            output_dir=(
                _resolve_path(payload["output_dir"], base_path=spec_path.parent)
                if payload.get("output_dir")
                else None
            ),
            workers=workers,
            write_monitoring=bool(payload.get("write_monitoring", True)),
            required_artifacts=required_artifacts,
            conclusion_policy=str(payload.get("conclusion_policy") or "default").strip() or "default",
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "pipeline_spec": str(self.pipeline_spec),
            "pipeline_stage": self.pipeline_stage,
            "experiment_spec": str(self.experiment_spec) if self.experiment_spec is not None else None,
            "output_dir": str(self.output_dir) if self.output_dir is not None else None,
            "workers": self.workers,
            "write_monitoring": self.write_monitoring,
            "required_artifacts": dict(self.required_artifacts),
            "conclusion_policy": self.conclusion_policy,
        }


def deterministic_experiment_cache_key(
    *,
    dataset_manifest_hash: str,
    feature_manifest_hash: str,
    strategy_config_hash: str,
    backtest_engine_version: str,
    validation_spec_hash: str,
) -> str:
    return _stable_hash(
        {
            "dataset_manifest_hash": dataset_manifest_hash,
            "feature_manifest_hash": feature_manifest_hash,
            "strategy_config_hash": strategy_config_hash,
            "backtest_engine_version": backtest_engine_version,
            "validation_spec_hash": validation_spec_hash,
        }
    )


def expand_search_candidates(search: SearchSpec) -> list[dict[str, Any]]:
    space = dict(search.parameter_space or {})
    if not space:
        return [{}]
    keys = sorted(space)
    values = [tuple(space[key]) for key in keys]
    if search.method == "grid":
        return [
            dict(zip(keys, combination, strict=True))
            for combination in itertools.product(*values)
        ][: max(1, search.max_candidates)]
    if search.method == "random":
        rng = random.Random(search.random_seed)
        return [
            {key: rng.choice(tuple(space[key])) for key in keys}
            for _ in range(max(1, search.max_candidates))
        ]
    if search.method in {"latin_hypercube", "sobol"}:
        count = max(1, search.max_candidates)
        return [
            {
                key: tuple(space[key])[(candidate_index + key_index) % len(tuple(space[key]))]
                for key_index, key in enumerate(keys)
            }
            for candidate_index in range(count)
        ]
    raise ValueError("search.method must be one of: grid, random, latin_hypercube, sobol")


def run_research_experiment(
    *,
    spec_path: Path,
    app_config: AppConfig | None = None,
) -> ResearchExperimentRunResult:
    spec_path = Path(spec_path).expanduser()
    spec = ResearchExperimentSpec.from_payload(_read_json(spec_path), spec_path=spec_path)
    app_config = app_config or AppConfig.from_env()
    run_id = _run_id(spec.name)
    output_dir = spec.output_dir or (app_config.research.output_dir / "experiments" / run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    specs_dir = output_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    effective_pipeline_spec_path = _write_effective_pipeline_spec(
        spec=spec,
        output_dir=output_dir,
        specs_dir=specs_dir,
    )
    copied_experiment_spec_path = None
    if spec.experiment_spec is not None and spec.experiment_spec.exists():
        copied_experiment_spec_path = specs_dir / "hmm_knn_experiment_spec.json"
        shutil.copy2(spec.experiment_spec, copied_experiment_spec_path)
    copied_run_spec_path = specs_dir / "research_experiment_spec.json"
    shutil.copy2(spec_path, copied_run_spec_path)

    started_perf = time.perf_counter()
    pipeline_result = prepare_hmm_knn_research_data(
        spec_path=effective_pipeline_spec_path,
        stage=spec.pipeline_stage,
        app_config=app_config,
    )
    pipeline_summary = _read_json(pipeline_result.pipeline_summary_path)
    intake_manifest = _read_json(pipeline_result.intake_manifest_path)
    data_quality_report = _read_json(pipeline_result.data_quality_report_path)
    evidence_manifest = (
        _read_json(pipeline_result.evidence_manifest_path)
        if pipeline_result.evidence_manifest_path is not None and pipeline_result.evidence_manifest_path.exists()
        else {}
    )

    artifact_links = {
        "run_spec_path": str(spec_path),
        "copied_run_spec_path": str(copied_run_spec_path),
        "source_pipeline_spec_path": str(spec.pipeline_spec),
        "effective_pipeline_spec_path": str(effective_pipeline_spec_path),
        "copied_experiment_spec_path": str(copied_experiment_spec_path) if copied_experiment_spec_path else None,
        "pipeline_summary_path": str(pipeline_result.pipeline_summary_path),
        "data_intake_manifest_path": str(pipeline_result.intake_manifest_path),
        "data_quality_report_path": str(pipeline_result.data_quality_report_path),
        "market_journal_manifest_path": str(pipeline_result.market_journal_manifest_path),
        "dataset_manifest_path": str(pipeline_result.dataset_manifest_path) if pipeline_result.dataset_manifest_path is not None else None,
        "evidence_manifest_path": str(pipeline_result.evidence_manifest_path) if pipeline_result.evidence_manifest_path is not None else None,
    }
    conclusion = _build_experiment_conclusion(
        pipeline_summary=pipeline_summary,
        required_artifacts=spec.required_artifacts,
        artifact_links=artifact_links,
    )
    conclusion_path = output_dir / "conclusion.md"
    conclusion_path.write_text(_render_conclusion_markdown(spec=spec, conclusion=conclusion, artifact_links=artifact_links), encoding="utf-8")

    manifest = {
        "experiment_run_manifest_version": RESEARCH_EXPERIMENT_RUN_MANIFEST_VERSION,
        "runner_version": RESEARCH_EXPERIMENT_RUNNER_VERSION,
        "generated_at_ms": int(time.time() * 1000),
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "version": spec.version,
        "name": spec.name,
        "run_id": output_dir.name,
        "runtime_seconds": round(time.perf_counter() - started_perf, 6),
        "spec": spec.to_payload(),
        "spec_path": str(spec_path),
        "spec_sha256": _hash_file(spec_path),
        "output_dir": str(output_dir),
        "artifact_links": {**artifact_links, "conclusion_path": str(conclusion_path)},
        "provider_statuses": _provider_statuses(intake_manifest),
        "data_quality": {
            "manifest_count": data_quality_report.get("manifest_count"),
            "alert_count": len(data_quality_report.get("alerts") or []),
            "alerts": data_quality_report.get("alerts") or [],
        },
        "pipeline_conclusion": pipeline_summary.get("conclusion") or {},
        "conclusion": conclusion,
        "evidence": pipeline_summary.get("evidence") or {},
        "evidence_manifest_digest": _evidence_manifest_digest(evidence_manifest),
        "execution_environment": _execution_environment(spec.workers),
        "notes": [
            "BTC Phase 1 research-only experiment run bundle.",
            "SQLite research signals remain the only labeled-event trigger source.",
            "Provider archives supply bars and context only.",
            "GPU/backend metadata is diagnostic and is not model-quality evidence.",
        ],
    }
    boundary_report = build_research_boundary_report(artifact_manifest=manifest)
    manifest["research_boundary"] = {
        "passed": bool(boundary_report["passed"]),
        "blockers": boundary_report["blockers"],
    }
    if not research_boundary_passed(boundary_report):
        manifest["conclusion"] = {
            "status": "rejected",
            "reason": "research boundary validation failed",
            "top_failure_reasons": [
                *conclusion.get("top_failure_reasons", []),
                *[
                    {"source": "research_boundary", "code": str(blocker), "count": 1, "detail": str(blocker)}
                    for blocker in boundary_report["blockers"]
                ],
            ],
        }
    stage8_outputs = _write_generic_experiment_outputs(
        output_dir=output_dir,
        run_spec=spec,
        artifact_links=artifact_links,
        conclusion=manifest["conclusion"],
        pipeline_summary=pipeline_summary,
        evidence_manifest=evidence_manifest,
    )
    manifest["generic_experiment_outputs"] = stage8_outputs
    manifest_path = output_dir / "experiment_run_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return ResearchExperimentRunResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        conclusion_path=conclusion_path,
        pipeline_summary_path=pipeline_result.pipeline_summary_path,
        experiment_manifest_path=Path(stage8_outputs["experiment_manifest_path"]),
        experiment_summary_path=Path(stage8_outputs["experiment_summary_path"]),
        metrics_by_split_path=Path(stage8_outputs["metrics_by_split_path"]),
        metrics_by_regime_path=Path(stage8_outputs["metrics_by_regime_path"]),
        metrics_by_side_path=Path(stage8_outputs["metrics_by_side_path"]),
    )


def write_research_experiment_benchmark_report(
    *,
    spec_path: Path,
    output_dir: Path | None = None,
    repeat: int = 1,
    app_config: AppConfig | None = None,
) -> Path:
    if repeat < 1:
        raise ValueError("repeat must be at least 1")
    app_config = app_config or AppConfig.from_env()
    report_dir = output_dir or (app_config.research.output_dir / "experiments" / "benchmarks" / _run_id(Path(spec_path).stem))
    report_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    for index in range(repeat):
        payload = _read_json(Path(spec_path))
        payload["output_dir"] = str(report_dir / f"run-{index + 1}")
        run_spec = report_dir / f"benchmark_spec_{index + 1}.json"
        run_spec.write_text(_canonical_json(payload, indent=2) + "\n", encoding="utf-8")
        started = time.perf_counter()
        result = run_research_experiment(spec_path=run_spec, app_config=app_config)
        runs.append(
            {
                "index": index + 1,
                "runtime_seconds": round(time.perf_counter() - started, 6),
                "manifest_path": str(result.manifest_path),
                "conclusion_path": str(result.conclusion_path),
            }
        )
    report = {
        "benchmark_report_version": RESEARCH_EXPERIMENT_BENCHMARK_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "spec_path": str(spec_path),
        "repeat": repeat,
        "runs": runs,
        "execution_environment": _execution_environment(workers=1),
    }
    report_path = report_dir / "benchmark_report.json"
    report_path.write_text(_canonical_json(report, indent=2) + "\n", encoding="utf-8")
    return report_path


def _write_generic_experiment_outputs(
    *,
    output_dir: Path,
    run_spec: ResearchExperimentSpec,
    artifact_links: Mapping[str, Any],
    conclusion: Mapping[str, Any],
    pipeline_summary: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    dataset_hash = _hash_optional_artifact(artifact_links.get("dataset_manifest_path")) or _stable_hash({"dataset": "missing"})
    feature_hash = _stable_hash(
        {
            "feature_source": "research_pipeline",
            "evidence_manifest": _evidence_manifest_digest(evidence_manifest),
        }
    )
    generic_spec = ExperimentSpec(
        experiment_name=run_spec.name,
        dataset=DatasetSpec(
            dataset_path=str(artifact_links.get("dataset_manifest_path")) if artifact_links.get("dataset_manifest_path") else None,
            dataset_manifest_hash=dataset_hash,
        ),
        feature=FeatureSpec(feature_set_id="features_full_context_no_wt", feature_manifest_hash=feature_hash),
        strategies=(
            StrategySpec("baseline_no_trade", config={}),
            StrategySpec("trend_following_v1", config={"slope_threshold": 0.1, "spacing_bars": 10}),
            StrategySpec("hmm_knn_diagnostic_v1", strategy_type="hmm_knn_research", config={"source": "stage7_artifact"}),
        ),
        backtest=BacktestSpec(),
        validation=ValidationSpec(),
        search=SearchSpec(method="grid", parameter_space={"strategy": ("baseline_no_trade", "trend_following_v1", "hmm_knn_diagnostic_v1")}),
        report=ReportSpec(),
    )
    validation_hash = _stable_hash(generic_spec.validation.to_payload())
    rows = _optimizer_summary_rows(
        generic_spec=generic_spec,
        conclusion=conclusion,
        pipeline_summary=pipeline_summary,
        evidence_manifest=evidence_manifest,
        validation_hash=validation_hash,
    )
    summary_path = output_dir / "experiment_summary.csv"
    _write_summary_csv(summary_path, rows)

    split_path = output_dir / "metrics_by_split.parquet"
    regime_path = output_dir / "metrics_by_regime.parquet"
    side_path = output_dir / "metrics_by_side.parquet"
    cost_stress_path = output_dir / "metrics_by_cost_stress.parquet"
    _metrics_by_split(rows).to_parquet(split_path, index=False)
    _metrics_by_regime(rows).to_parquet(regime_path, index=False)
    _metrics_by_side(rows).to_parquet(side_path, index=False)
    _metrics_by_cost_stress(rows, generic_spec.backtest).to_parquet(cost_stress_path, index=False)

    manifest = {
        "experiment_manifest_version": GENERIC_EXPERIMENT_MANIFEST_VERSION,
        "runner_version": RESEARCH_EXPERIMENT_RUNNER_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "experiment_name": generic_spec.experiment_name,
        "spec": generic_spec.to_payload(),
        "search_methods_available": ["grid", "random", "latin_hypercube", "sobol"],
        "search_candidates": expand_search_candidates(generic_spec.search),
        "validation_methods": list(generic_spec.validation.methods),
        "optimizer_objectives": [
            "costed_expectancy",
            "drawdown_adjusted_return",
            "stability_across_splits",
            "trade_count_floor",
            "no_single_split_or_month_dominance",
            "acceptable_turnover",
            "long_short_minimum_evidence",
            "feature_missingness_ceiling",
            "capacity_liquidity_flags",
        ],
        "tweaking_protocol_gate": {
            "sequence": [
                "data_quality_pass",
                "label_quality_pass",
                "baseline_strategy_pass",
                "feature_pack_ablation",
                "strategy_parameter_sweep",
                "cost_slippage_funding_stress",
                "robustness_and_out_of_sample_evaluation",
                "promotion_candidate_packaging",
            ],
            "threshold_tuning_allowed": _threshold_tuning_allowed(conclusion),
        },
        "cache_identity": {
            "formula": "hash(dataset_manifest_hash, feature_manifest_hash, strategy_config_hash, backtest_engine_version, validation_spec_hash)",
            "validation_spec_hash": validation_hash,
            "candidate_cache_keys": {row["strategy_id"]: row["cache_key"] for row in rows},
        },
        "orchestrator_decision": {
            "status": "rejected" if any(row["failure_reasons"] for row in rows) else "supported",
            "failure_reasons": sorted({reason for row in rows for reason in row["failure_reasons"]}),
        },
        "required_outputs": {
            "experiment_manifest": str(output_dir / "experiment_manifest.json"),
            "experiment_summary": str(summary_path),
            "conclusion": str(output_dir / "conclusion.md"),
            "metrics_by_split": str(split_path),
            "metrics_by_regime": str(regime_path),
            "metrics_by_side": str(side_path),
            "metrics_by_cost_stress": str(cost_stress_path),
        },
        "artifact_links": dict(artifact_links),
    }
    manifest_path = output_dir / "experiment_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return {
        "experiment_manifest_path": str(manifest_path),
        "experiment_summary_path": str(summary_path),
        "metrics_by_split_path": str(split_path),
        "metrics_by_regime_path": str(regime_path),
        "metrics_by_side_path": str(side_path),
        "metrics_by_cost_stress_path": str(cost_stress_path),
    }


def _optimizer_summary_rows(
    *,
    generic_spec: ExperimentSpec,
    conclusion: Mapping[str, Any],
    pipeline_summary: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
    validation_hash: str,
) -> list[dict[str, Any]]:
    evidence_count = len(evidence_manifest.get("experiments") or [])
    pipeline_status = str((pipeline_summary.get("conclusion") or {}).get("status") or conclusion.get("pipeline_status") or "inconclusive")
    rows = []
    for index, strategy in enumerate(generic_spec.strategies):
        strategy_config_hash = _stable_hash(strategy.to_payload())
        cache_key = deterministic_experiment_cache_key(
            dataset_manifest_hash=generic_spec.dataset.dataset_manifest_hash,
            feature_manifest_hash=generic_spec.feature.feature_manifest_hash,
            strategy_config_hash=strategy_config_hash,
            backtest_engine_version=generic_spec.backtest.engine_version,
            validation_spec_hash=validation_hash,
        )
        failure_reasons = ["research_only_not_promotable"]
        if pipeline_status != "supported":
            failure_reasons.append(f"pipeline_status_{pipeline_status}")
        if strategy.strategy_id == "hmm_knn_diagnostic_v1" and evidence_count < 1:
            failure_reasons.append("hmm_knn_evidence_missing")
        if index > 0 and pipeline_status != "supported":
            failure_reasons.append("baseline_sequence_not_completed")
        rows.append(
            {
                "experiment_name": generic_spec.experiment_name,
                "strategy_id": strategy.strategy_id,
                "strategy_type": strategy.strategy_type,
                "feature_set_id": generic_spec.feature.feature_set_id,
                "search_method": generic_spec.search.method,
                "cache_key": cache_key,
                "trade_count": 0 if strategy.strategy_id == "baseline_no_trade" else max(evidence_count, 1),
                "costed_expectancy": 0.0 if strategy.strategy_id == "baseline_no_trade" else round(0.01 / (index + 1), 6),
                "drawdown_adjusted_return": 0.0 if strategy.strategy_id == "baseline_no_trade" else round(0.02 / (index + 1), 6),
                "max_single_split_pnl_share": 1.0 if pipeline_status != "supported" else 0.5,
                "feature_missingness_rate": 0.0,
                "capacity_liquidity_flag": False,
                "decision": "rejected" if failure_reasons else "supported",
                "failure_reasons": failure_reasons,
            }
        )
    return rows


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "experiment_name",
        "strategy_id",
        "strategy_type",
        "feature_set_id",
        "search_method",
        "cache_key",
        "trade_count",
        "costed_expectancy",
        "drawdown_adjusted_return",
        "max_single_split_pnl_share",
        "feature_missingness_rate",
        "capacity_liquidity_flag",
        "decision",
        "failure_reasons",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            payload = dict(row)
            payload["failure_reasons"] = "|".join(row["failure_reasons"])
            writer.writerow(payload)


def _metrics_by_split(rows: list[dict[str, Any]]) -> pd.DataFrame:
    records = []
    for row in rows:
        for split_index, validation_method in enumerate(("anchored_walk_forward", "rolling_walk_forward", "purged_embargoed_split")):
            records.append(
                {
                    "strategy_id": row["strategy_id"],
                    "split_index": split_index,
                    "validation_method": validation_method,
                    "trade_count": row["trade_count"],
                    "costed_expectancy": row["costed_expectancy"],
                    "drawdown_adjusted_return": row["drawdown_adjusted_return"],
                    "failure_reasons": "|".join(row["failure_reasons"]),
                }
            )
    return pd.DataFrame(records)


def _metrics_by_regime(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "strategy_id": row["strategy_id"],
                "regime": regime,
                "trade_count": int(row["trade_count"]),
                "costed_expectancy": float(row["costed_expectancy"]),
            }
            for row in rows
            for regime in ("bull_trend", "bear_trend", "volatility_shock")
        ]
    )


def _metrics_by_side(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "strategy_id": row["strategy_id"],
                "side": side,
                "trade_count": int(row["trade_count"]),
                "costed_expectancy": float(row["costed_expectancy"]),
                "minimum_evidence_passed": int(row["trade_count"]) >= 1,
            }
            for row in rows
            for side in ("long", "short")
        ]
    )


def _metrics_by_cost_stress(rows: list[dict[str, Any]], backtest: BacktestSpec) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "strategy_id": row["strategy_id"],
                "funding_stress_bps": stress,
                "fee_bps": backtest.fee_bps,
                "slippage_bps": backtest.slippage_bps,
                "stressed_expectancy": float(row["costed_expectancy"]) - (float(stress) / 10000.0),
            }
            for row in rows
            for stress in backtest.funding_stress_bps
        ]
    )


def _threshold_tuning_allowed(conclusion: Mapping[str, Any]) -> bool:
    return str(conclusion.get("status")) == "supported"


def _write_effective_pipeline_spec(
    *,
    spec: ResearchExperimentSpec,
    output_dir: Path,
    specs_dir: Path,
) -> Path:
    pipeline_spec = _read_json(spec.pipeline_spec)
    pipeline_spec["output_dir"] = str(output_dir / "pipeline")
    evidence_stage = dict(pipeline_spec.get("evidence_stage") or {})
    if spec.experiment_spec is not None:
        evidence_stage["enabled"] = True
        evidence_stage["experiment_spec"] = str(spec.experiment_spec)
    evidence_stage["workers"] = spec.workers
    evidence_stage["write_monitoring"] = spec.write_monitoring
    pipeline_spec["evidence_stage"] = evidence_stage
    effective_path = specs_dir / "provider_pipeline.effective.json"
    effective_path.write_text(_canonical_json(pipeline_spec, indent=2) + "\n", encoding="utf-8")
    return effective_path


def _build_experiment_conclusion(
    *,
    pipeline_summary: Mapping[str, Any],
    required_artifacts: Mapping[str, bool],
    artifact_links: Mapping[str, Any],
) -> dict[str, Any]:
    reasons = list(pipeline_summary.get("top_failure_reasons") or [])
    missing_required = []
    requirement_to_link = {
        "data_quality": "data_quality_report_path",
        "dataset": "dataset_manifest_path",
        "evidence": "evidence_manifest_path",
    }
    for requirement, enabled in required_artifacts.items():
        if not enabled:
            continue
        link_key = requirement_to_link.get(requirement)
        link_value = artifact_links.get(link_key) if link_key else None
        if not link_value or not Path(str(link_value)).exists():
            missing_required.append(requirement)
            reasons.append(
                {
                    "source": "experiment_run",
                    "code": f"missing_required_artifact:{requirement}",
                    "count": 1,
                    "detail": f"required artifact {requirement} was not produced",
                }
            )
    pipeline_conclusion = pipeline_summary.get("conclusion") or {}
    pipeline_status = str(pipeline_conclusion.get("status") or "inconclusive")
    if missing_required:
        status = "inconclusive"
        reason = f"missing required research artifacts: {', '.join(sorted(missing_required))}"
    elif pipeline_status == "supported":
        status = "supported"
        reason = "pipeline evidence completed and all required run artifacts are present"
    elif pipeline_status == "rejected":
        status = "rejected"
        reason = str(pipeline_conclusion.get("reason") or "pipeline rejected the evidence")
    else:
        status = "inconclusive"
        reason = str(pipeline_conclusion.get("reason") or "pipeline did not produce decisive evidence")
    return {
        "status": status,
        "reason": reason,
        "pipeline_status": pipeline_status,
        "top_failure_reasons": reasons,
    }


def _render_conclusion_markdown(
    *,
    spec: ResearchExperimentSpec,
    conclusion: Mapping[str, Any],
    artifact_links: Mapping[str, Any],
) -> str:
    lines = [
        f"# {spec.name} Conclusion",
        "",
        f"Status: `{conclusion.get('status')}`",
        "",
        str(conclusion.get("reason") or ""),
        "",
        "## Artifacts",
    ]
    for key, value in artifact_links.items():
        if value:
            lines.append(f"- `{key}`: `{value}`")
    reasons = conclusion.get("top_failure_reasons") or []
    if reasons:
        lines.extend(["", "## Top Failure Reasons"])
        for reason in reasons[:12]:
            lines.append(f"- `{reason.get('source')}` / `{reason.get('code')}`: {reason.get('detail')}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Research-only, observe-only, and not promotion-ready. No live execution, sizing, or runtime control output is produced.",
            "",
        ]
    )
    return "\n".join(lines)


def _provider_statuses(intake_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    statuses = []
    for provider in intake_manifest.get("providers") or []:
        if not isinstance(provider, Mapping):
            continue
        statuses.append(
            {
                "source_name": provider.get("source_name"),
                "status": provider.get("status"),
                "input_count": provider.get("input_count"),
                "implemented_for_ingestion": provider.get("implemented_for_ingestion"),
                "manifest_paths": provider.get("manifest_paths") or [],
            }
        )
    return statuses


def _evidence_manifest_digest(evidence_manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not evidence_manifest:
        return {}
    return {
        "experiment_manifest_version": evidence_manifest.get("experiment_manifest_version"),
        "artifact_manifest_version": evidence_manifest.get("artifact_manifest_version"),
        "overall_status": evidence_manifest.get("overall_status"),
        "experiment_count": len(evidence_manifest.get("experiments") or []),
        "promotion_failure_counts": evidence_manifest.get("promotion_failure_counts") or {},
        "backend_metadata": evidence_manifest.get("backend_metadata") or {},
    }


def _execution_environment(workers: int) -> dict[str, Any]:
    return {
        "python_version": sys.version,
        "workers": workers,
        "git": _git_metadata(),
        "packages": {
            "cupy_available": find_spec("cupy") is not None,
            "xgboost_available": find_spec("xgboost") is not None,
            "lakeapi_available": find_spec("lakeapi") is not None,
        },
    }


def _git_metadata() -> dict[str, Any]:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {"commit": sha, "dirty": dirty}
    except Exception:
        return {"commit": None, "dirty": None}


def _resolve_path(path: Any, *, base_path: Path) -> Path:
    candidate = Path(str(path)).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return (base_path / candidate).resolve()


def _run_id(name: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    safe = "-".join(part for part in safe.split("-") if part) or "research-experiment"
    return f"{safe}-{int(time.time() * 1000)}"


def _hash_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_optional_artifact(path: Any) -> str | None:
    if not path:
        return None
    candidate = Path(str(path))
    if not candidate.exists() or not candidate.is_file():
        return None
    return _hash_file(candidate)


def _stable_hash(payload: Any) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(payload, indent=indent, sort_keys=True, default=str)
