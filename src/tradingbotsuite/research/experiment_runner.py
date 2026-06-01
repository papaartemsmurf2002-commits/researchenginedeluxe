from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import csv
import itertools
import random
from dataclasses import dataclass, replace
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from tradingbotsuite.backtesting import BACKTEST_ENGINE_VERSION, BacktestEngine
from tradingbotsuite.backtesting.engine import BacktestSpec as EngineBacktestSpec
from tradingbotsuite.backtesting.splits import (
    build_anchored_walk_forward_splits,
    build_purged_walk_forward_splits,
    build_rolling_walk_forward_splits,
)
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
EXECUTABLE_VALIDATION_METHODS = {
    "anchored_walk_forward",
    "rolling_walk_forward",
    "purged_embargoed_split",
    "purged_embargoed_walk_forward",
}
REPORT_OUTPUT_VALIDATION_METHODS = {
    "side_separated_reporting",
    "regime_separated_reporting",
    "cost_slippage_funding_stress",
}


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
    candidate_rankings_path: Path | None = None


@dataclass(frozen=True, slots=True)
class GenericExecutionCandidate:
    candidate_id: str
    candidate_index: int
    strategy: StrategySpec
    search_parameters: Mapping[str, Any]
    strategy_config: Mapping[str, Any]
    feature_set_id: str
    feature_manifest_hash: str
    holding_window: str
    fee_bps: float
    slippage_bps: float
    funding_stress_bps: tuple[float, ...]


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
                _resolve_output_path(payload["output_dir"], base_path=spec_path.parent)
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
    spec_path = Path(spec_path).expanduser().resolve()
    spec = ResearchExperimentSpec.from_payload(_read_json(spec_path), spec_path=spec_path)
    app_config = app_config or AppConfig.from_env()
    run_id = _run_id(spec.name)
    repo_root = _repo_root_from_path(spec_path)
    research_root = _resolve_path(app_config.research.output_dir, base_path=repo_root)
    output_dir = spec.output_dir or (research_root / "experiments" / run_id)
    output_dir = output_dir.resolve()
    _ensure_inside_research_root(
        output_dir,
        research_root=research_root,
        field_name="experiment output_dir",
    )
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
        candidate_rankings_path=Path(stage8_outputs["candidate_rankings_path"]),
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
    source_spec_path = Path(spec_path).expanduser()
    source_spec = ResearchExperimentSpec.from_payload(_read_json(source_spec_path), spec_path=source_spec_path)
    report_dir = output_dir or (app_config.research.output_dir / "experiments" / "benchmarks" / _run_id(source_spec_path.stem))
    report_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    for index in range(repeat):
        payload = source_spec.to_payload()
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
        "spec_path": str(source_spec_path),
        "resolved_source_spec": source_spec.to_payload(),
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
    supplied_spec, supplied_spec_status = _load_supplied_experiment_spec(run_spec.experiment_spec)
    resolved_dataset_path = _resolve_generic_dataset_path(
        run_spec=run_spec,
        supplied_spec=supplied_spec,
        artifact_links=artifact_links,
        evidence_manifest=evidence_manifest,
    )
    dataset_identity = _generic_dataset_identity(
        resolved_dataset_path=resolved_dataset_path,
        supplied_spec=supplied_spec,
        artifact_links=artifact_links,
    )
    generic_spec, supplied_spec_status = _executable_generic_spec(
        run_spec=run_spec,
        supplied_spec=supplied_spec,
        supplied_spec_status=supplied_spec_status,
        resolved_dataset_path=resolved_dataset_path,
        dataset_hash=str(dataset_identity["dataset_identity_hash"]),
        artifact_links=artifact_links,
        evidence_manifest=evidence_manifest,
    )
    validation_hash = _stable_hash(generic_spec.validation.to_payload())
    if resolved_dataset_path is not None:
        generic_outputs = _real_generic_backtest_outputs(
            output_dir=output_dir,
            generic_spec=generic_spec,
            dataset_path=resolved_dataset_path,
            conclusion=conclusion,
            pipeline_summary=pipeline_summary,
            evidence_manifest=evidence_manifest,
            validation_hash=validation_hash,
        )
        rows = generic_outputs["rows"]
        split_frame = generic_outputs["metrics_by_split"]
        regime_frame = generic_outputs["metrics_by_regime"]
        side_frame = generic_outputs["metrics_by_side"]
        cost_stress_frame = generic_outputs["metrics_by_cost_stress"]
        validation_method_execution = _validation_method_execution(
            generic_spec.validation,
            empirical_result_scope="real_backtest",
            split_frame=split_frame,
            regime_frame=regime_frame,
            side_frame=side_frame,
            cost_stress_frame=cost_stress_frame,
        )
        _apply_validation_execution_failures(rows, validation_method_execution)
        _finalize_generic_row_scoreability(rows, validation=generic_spec.validation)
        scoreable_rows = [row for row in rows if bool(row.get("scoreable_candidate", False))]
        aggregate_real_rows = [row for row in rows if bool(row.get("aggregate_backtest_evidence", False))]
        failed_rows = [row for row in rows if row.get("metric_scope") == "real_backtest_failed"]
        empirical_result_scope = (
            "real_backtest_partial"
            if scoreable_rows and failed_rows
            else "real_backtest"
            if scoreable_rows
            else "aggregate_backtest_validation_incomplete"
            if aggregate_real_rows
            else "real_backtest_failed"
        )
        empirical_evidence = bool(scoreable_rows)
        metrics_source = (
            "backtest_engine"
            if scoreable_rows
            else "backtest_engine_validation_incomplete"
            if aggregate_real_rows
            else "backtest_engine_failed"
        )
        orchestrator_reason = (
            "generic experiment rows include validated real backtest outputs but remain research-only and not acceptance evidence"
            if scoreable_rows
            else "generic experiment rows include aggregate backtests but required validation evidence is incomplete"
            if aggregate_real_rows
            else "generic experiment attempted real backtests but no candidate produced empirical metrics"
        )
    else:
        rows = _not_run_missing_dataset_rows(
            generic_spec=generic_spec,
            conclusion=conclusion,
            pipeline_summary=pipeline_summary,
            validation_hash=validation_hash,
        )
        split_frame = _empty_split_metrics_frame()
        regime_frame = _empty_regime_metrics_frame()
        side_frame = _empty_side_metrics_frame()
        cost_stress_frame = _empty_cost_stress_metrics_frame()
        validation_method_execution = _validation_method_execution(
            generic_spec.validation,
            empirical_result_scope="not_run_missing_dataset",
            split_frame=split_frame,
            regime_frame=regime_frame,
            side_frame=side_frame,
            cost_stress_frame=cost_stress_frame,
        )
        _finalize_generic_row_scoreability(rows, validation=generic_spec.validation)
        empirical_result_scope = "not_run_missing_dataset"
        empirical_evidence = False
        metrics_source = "not_run_no_dataset"
        orchestrator_reason = "generic experiment was not run because no parquet dataset could be resolved"
    summary_path = output_dir / "experiment_summary.csv"
    _write_summary_csv(summary_path, rows)

    split_path = output_dir / "metrics_by_split.parquet"
    regime_path = output_dir / "metrics_by_regime.parquet"
    side_path = output_dir / "metrics_by_side.parquet"
    cost_stress_path = output_dir / "metrics_by_cost_stress.parquet"
    ranking_path = output_dir / "candidate_rankings.parquet"
    split_frame.to_parquet(split_path, index=False)
    regime_frame.to_parquet(regime_path, index=False)
    side_frame.to_parquet(side_path, index=False)
    cost_stress_frame.to_parquet(cost_stress_path, index=False)
    _candidate_rankings(rows).to_parquet(ranking_path, index=False)

    manifest = {
        "experiment_manifest_version": GENERIC_EXPERIMENT_MANIFEST_VERSION,
        "runner_version": RESEARCH_EXPERIMENT_RUNNER_VERSION,
        "empirical_result_scope": empirical_result_scope,
        "empirical_evidence": empirical_evidence,
        "metrics_source": metrics_source,
        "aggregate_backtest_evidence": any(bool(row.get("aggregate_backtest_evidence", False)) for row in rows),
        "scoreable_candidate_count": sum(1 for row in rows if bool(row.get("scoreable_candidate", False))),
        "non_scoreable_candidate_count": sum(1 for row in rows if not bool(row.get("scoreable_candidate", False))),
        "candidate_acceptance_allowed": False,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        **research_boundary_metadata(),
        "experiment_name": generic_spec.experiment_name,
        "spec": generic_spec.to_payload(),
        "supplied_experiment_spec": supplied_spec_status,
        "search_methods_available": ["grid", "random", "latin_hypercube", "sobol"],
        "search_candidates": expand_search_candidates(generic_spec.search),
        "execution_candidates": [_candidate_manifest_payload(candidate) for candidate in _generic_execution_candidates(generic_spec)],
        "validation_methods": list(generic_spec.validation.methods),
        "validation_method_execution": validation_method_execution,
        "dataset_identity": dataset_identity,
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
            "formula": "hash(dataset_identity_hash, feature_manifest_hash, strategy_config_hash, backtest_engine_version, validation_spec_hash)",
            "validation_spec_hash": validation_hash,
            "dataset_identity_hash": dataset_identity["dataset_identity_hash"],
            "candidate_cache_keys": {str(row.get("candidate_id") or row["strategy_id"]): row["cache_key"] for row in rows},
            "backtest_result_hashes": {
                str(row.get("candidate_id") or row["strategy_id"]): row.get("result_sha256")
                for row in rows
                if row.get("result_sha256")
            },
        },
        "orchestrator_decision": {
            "status": "rejected",
            "failure_reasons": sorted({reason for row in rows for reason in row["failure_reasons"]}),
            "reason": orchestrator_reason,
        },
        "required_outputs": {
            "experiment_manifest": str(output_dir / "experiment_manifest.json"),
            "experiment_summary": str(summary_path),
            "conclusion": str(output_dir / "conclusion.md"),
            "candidate_rankings": str(ranking_path),
            "metrics_by_split": str(split_path),
            "metrics_by_regime": str(regime_path),
            "metrics_by_side": str(side_path),
            "metrics_by_cost_stress": str(cost_stress_path),
        },
        "artifact_links": dict(artifact_links),
        "resolved_dataset_path": str(resolved_dataset_path) if resolved_dataset_path is not None else None,
    }
    manifest_path = output_dir / "experiment_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return {
        "experiment_manifest_path": str(manifest_path),
        "experiment_summary_path": str(summary_path),
        "candidate_rankings_path": str(ranking_path),
        "metrics_by_split_path": str(split_path),
        "metrics_by_regime_path": str(regime_path),
        "metrics_by_side_path": str(side_path),
        "metrics_by_cost_stress_path": str(cost_stress_path),
    }


def _default_generic_experiment_spec(
    *,
    run_spec: ResearchExperimentSpec,
    resolved_dataset_path: Path | None,
    dataset_hash: str,
    artifact_links: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
) -> ExperimentSpec:
    feature_hash = _stable_hash(
        {
            "feature_source": "research_pipeline",
            "evidence_manifest": _evidence_manifest_digest(evidence_manifest),
        }
    )
    return ExperimentSpec(
        experiment_name=run_spec.name,
        dataset=DatasetSpec(
            dataset_path=str(resolved_dataset_path) if resolved_dataset_path is not None else (
                str(artifact_links.get("dataset_manifest_path")) if artifact_links.get("dataset_manifest_path") else None
            ),
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


def _executable_generic_spec(
    *,
    run_spec: ResearchExperimentSpec,
    supplied_spec: ExperimentSpec | None,
    supplied_spec_status: Mapping[str, Any],
    resolved_dataset_path: Path | None,
    dataset_hash: str,
    artifact_links: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
) -> tuple[ExperimentSpec, dict[str, Any]]:
    generic_spec = supplied_spec or _default_generic_experiment_spec(
        run_spec=run_spec,
        resolved_dataset_path=resolved_dataset_path,
        dataset_hash=dataset_hash,
        artifact_links=artifact_links,
        evidence_manifest=evidence_manifest,
    )
    if resolved_dataset_path is not None:
        generic_spec = replace(
            generic_spec,
            dataset=DatasetSpec(
                dataset_path=str(resolved_dataset_path),
                dataset_manifest_hash=dataset_hash,
            ),
        )
    return generic_spec, dict(supplied_spec_status)


def _load_supplied_experiment_spec(path: Path | None) -> tuple[ExperimentSpec | None, dict[str, Any]]:
    status: dict[str, Any] = {
        "path": str(path) if path is not None else None,
        "loaded": False,
        "status": "not_supplied" if path is None else "not_loaded",
        "reason": None,
    }
    if path is None:
        return None, status
    if not path.exists():
        status["status"] = "missing"
        status["reason"] = "supplied experiment spec path does not exist"
        return None, status
    try:
        payload = _read_json(path)
        spec = ExperimentSpec.from_payload(payload)
    except Exception as exc:
        status["status"] = "ignored_non_generic_experiment_spec"
        status["reason"] = f"{type(exc).__name__}: {exc}"
        return None, status
    status["loaded"] = True
    status["status"] = "loaded_generic_experiment_spec"
    return spec, status


def _generic_execution_candidates(generic_spec: ExperimentSpec) -> tuple[GenericExecutionCandidate, ...]:
    records: list[GenericExecutionCandidate] = []
    for search_payload in expand_search_candidates(generic_spec.search):
        search_parameters = dict(search_payload)
        strategy_filter = search_parameters.get("strategy_id", search_parameters.get("strategy"))
        for strategy in generic_spec.strategies:
            if strategy_filter is not None and str(strategy_filter) != strategy.strategy_id:
                continue
            candidate = _build_generic_execution_candidate(
                generic_spec=generic_spec,
                strategy=strategy,
                candidate_index=len(records),
                search_parameters=search_parameters,
            )
            records.append(candidate)
    return tuple(records)


def _build_generic_execution_candidate(
    *,
    generic_spec: ExperimentSpec,
    strategy: StrategySpec,
    candidate_index: int,
    search_parameters: Mapping[str, Any],
) -> GenericExecutionCandidate:
    config = dict(strategy.config or {})
    configurable_parameters = dict(search_parameters)
    configurable_parameters.pop("strategy", None)
    configurable_parameters.pop("strategy_id", None)

    feature_set_id = str(configurable_parameters.pop("feature_set_id", generic_spec.feature.feature_set_id))
    feature_manifest_hash = str(configurable_parameters.pop("feature_manifest_hash", generic_spec.feature.feature_manifest_hash))
    holding_window = str(configurable_parameters.pop("holding_window", generic_spec.backtest.holding_window))
    fee_bps = float(configurable_parameters.pop("fee_bps", generic_spec.backtest.fee_bps))
    slippage_bps = float(configurable_parameters.pop("slippage_bps", generic_spec.backtest.slippage_bps))
    funding_stress_bps = generic_spec.backtest.funding_stress_bps
    if "funding_stress_bps" in configurable_parameters:
        raw_stress = configurable_parameters.pop("funding_stress_bps")
        if isinstance(raw_stress, (list, tuple)):
            funding_stress_bps = tuple(float(value) for value in raw_stress)
        else:
            funding_stress_bps = (float(raw_stress),)

    config.update(configurable_parameters)
    config["feature_set_id"] = feature_set_id
    identity_seed = {
        "candidate_index": candidate_index,
        "strategy": strategy.to_payload(),
        "search_parameters": dict(search_parameters),
        "feature_set_id": feature_set_id,
        "feature_manifest_hash": feature_manifest_hash,
        "holding_window": holding_window,
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "funding_stress_bps": list(funding_stress_bps),
    }
    candidate_id = _safe_artifact_name(f"{strategy.strategy_id}-{candidate_index + 1}-{_stable_hash(identity_seed)[:12]}")
    return GenericExecutionCandidate(
        candidate_id=candidate_id,
        candidate_index=candidate_index,
        strategy=strategy,
        search_parameters=dict(search_parameters),
        strategy_config=config,
        feature_set_id=feature_set_id,
        feature_manifest_hash=feature_manifest_hash,
        holding_window=holding_window,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        funding_stress_bps=tuple(funding_stress_bps),
    )


def _candidate_identity_payload(candidate: GenericExecutionCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_index": candidate.candidate_index,
        "strategy": candidate.strategy.to_payload(),
        "search_parameters": dict(candidate.search_parameters),
        "strategy_config": dict(candidate.strategy_config),
        "engine_strategy_config": _engine_strategy_config(candidate),
        "feature_set_id": candidate.feature_set_id,
        "feature_manifest_hash": candidate.feature_manifest_hash,
        "holding_window": candidate.holding_window,
        "fee_bps": candidate.fee_bps,
        "slippage_bps": candidate.slippage_bps,
        "funding_stress_bps": list(candidate.funding_stress_bps),
    }


def _candidate_manifest_payload(candidate: GenericExecutionCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "strategy_id": candidate.strategy.strategy_id,
        "strategy_type": candidate.strategy.strategy_type,
        "feature_set_id": candidate.feature_set_id,
        "feature_manifest_hash": candidate.feature_manifest_hash,
        "holding_window": candidate.holding_window,
        "fee_bps": candidate.fee_bps,
        "slippage_bps": candidate.slippage_bps,
        "funding_stress_bps": list(candidate.funding_stress_bps),
        "search_parameters": dict(candidate.search_parameters),
        "strategy_config": dict(candidate.strategy_config),
        "engine_strategy_config": _engine_strategy_config(candidate),
        "strategy_config_hash": _stable_hash(_candidate_identity_payload(candidate)),
    }


def _engine_strategy_config(candidate: GenericExecutionCandidate) -> dict[str, Any]:
    strategy_config = dict(candidate.strategy_config)
    if candidate.strategy.strategy_id == "hmm_knn_diagnostic_v1":
        strategy_config = {
            "probability_threshold": 0.55,
            "expected_value_threshold": 0.0,
            "spacing_bars": 8,
            **strategy_config,
        }
    return strategy_config


def _not_run_missing_dataset_rows(
    *,
    generic_spec: ExperimentSpec,
    conclusion: Mapping[str, Any],
    pipeline_summary: Mapping[str, Any],
    validation_hash: str,
) -> list[dict[str, Any]]:
    pipeline_status = str((pipeline_summary.get("conclusion") or {}).get("status") or conclusion.get("pipeline_status") or "inconclusive")
    rows = []
    for candidate in _generic_execution_candidates(generic_spec):
        strategy_config_hash = _stable_hash(_candidate_identity_payload(candidate))
        cache_key = deterministic_experiment_cache_key(
            dataset_manifest_hash=generic_spec.dataset.dataset_manifest_hash,
            feature_manifest_hash=candidate.feature_manifest_hash,
            strategy_config_hash=strategy_config_hash,
            backtest_engine_version=generic_spec.backtest.engine_version,
            validation_spec_hash=validation_hash,
        )
        failure_reasons = [
            "research_only_not_promotable",
            "generic_experiment_not_run_dataset_missing",
            "real_backtest_dataset_required",
        ]
        if pipeline_status != "supported":
            failure_reasons.append(f"pipeline_status_{pipeline_status}")
        if candidate.candidate_index > 0 and pipeline_status != "supported":
            failure_reasons.append("baseline_sequence_not_completed")
        failure_reasons.extend(_unsupported_validation_failure_reasons(generic_spec.validation))
        failure_reasons.extend(_not_executed_validation_failure_reasons(generic_spec.validation, observed_methods=set()))
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "experiment_name": generic_spec.experiment_name,
                "strategy_id": candidate.strategy.strategy_id,
                "strategy_type": candidate.strategy.strategy_type,
                "feature_set_id": candidate.feature_set_id,
                "search_method": generic_spec.search.method,
                "search_parameters_json": _canonical_json(candidate.search_parameters),
                "cache_key": cache_key,
                "metric_scope": "not_run_missing_dataset",
                "metrics_source": "not_run_no_dataset",
                "empirical_evidence": False,
                "backtest_manifest_path": "",
                "metrics_path": "",
                "result_sha256": "",
                "trade_count": None,
                "long_count": None,
                "short_count": None,
                "costed_expectancy": None,
                "net_return_after_fees_slippage_funding": None,
                "drawdown_adjusted_return": None,
                "max_drawdown": None,
                "hit_rate": None,
                "profit_factor": None,
                "final_score": None,
                "max_single_split_pnl_share": None,
                "feature_missingness_rate": None,
                "capacity_liquidity_flag": False,
                "decision": "rejected",
                "failure_reasons": failure_reasons,
            }
        )
    return rows


def _real_generic_backtest_outputs(
    *,
    output_dir: Path,
    generic_spec: ExperimentSpec,
    dataset_path: Path,
    conclusion: Mapping[str, Any],
    pipeline_summary: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
    validation_hash: str,
) -> dict[str, Any]:
    _ = evidence_manifest
    pipeline_status = str((pipeline_summary.get("conclusion") or {}).get("status") or conclusion.get("pipeline_status") or "inconclusive")
    backtest_dir = output_dir / "generic_backtests"
    engine = BacktestEngine()
    rows: list[dict[str, Any]] = []
    split_records: list[dict[str, Any]] = []
    cost_stress_records: list[dict[str, Any]] = []
    regime_records: list[dict[str, Any]] = []
    side_records: list[dict[str, Any]] = []
    dataset = pd.read_parquet(dataset_path)
    dataset_sha256 = _hash_file(dataset_path)

    execution_candidates = _generic_execution_candidates(generic_spec)
    for candidate in execution_candidates:
        try:
            result = engine.run(
                EngineBacktestSpec(
                    run_id=_safe_artifact_name(f"{candidate.candidate_index + 1}-{candidate.candidate_id}-{candidate.holding_window}"),
                    symbol="BTCUSDT",
                    output_dir=backtest_dir,
                    dataset_path=dataset_path,
                    dataset_sha256=dataset_sha256,
                    strategy_id=candidate.strategy.strategy_id,
                    holding_window=candidate.holding_window,
                    fee_bps=candidate.fee_bps,
                    slippage_bps=candidate.slippage_bps,
                    feature_set_id=candidate.feature_set_id,
                    feature_manifest_sha256=candidate.feature_manifest_hash,
                    strategy_config=_engine_strategy_config(candidate),
                )
            )
            metrics = _read_json(result.metrics_path)
            manifest = _read_json(result.manifest_path)
            row = _real_summary_row(
                generic_spec=generic_spec,
                candidate=candidate,
                metrics=metrics,
                manifest=manifest,
                manifest_path=result.manifest_path,
                metrics_path=result.metrics_path,
                validation_hash=validation_hash,
                pipeline_status=pipeline_status,
            )
        except Exception as exc:
            row = _failed_real_summary_row(
                generic_spec=generic_spec,
                candidate=candidate,
                validation_hash=validation_hash,
                pipeline_status=pipeline_status,
                error=exc,
            )
            rows.append(row)
            regime_records.extend(_regime_records_from_metrics(row, {}))
            side_records.extend(_empty_side_records(row))
            continue
        rows.append(row)
        regime_records.extend(_regime_records_from_metrics(row, metrics))
        side_records.extend(_side_records_from_trades(row, result.trades_path))
        cost_stress_records.extend(
            _real_cost_stress_records(
                engine=engine,
                generic_spec=generic_spec,
                dataset_path=dataset_path,
                dataset_sha256=dataset_sha256,
                candidate=candidate,
                backtest_dir=backtest_dir,
            )
        )

    split_records = _real_split_records(
        engine=engine,
        generic_spec=generic_spec,
        dataset=dataset,
        dataset_path=dataset_path,
        dataset_sha256=dataset_sha256,
        backtest_dir=backtest_dir,
        execution_candidates=execution_candidates,
    )
    _apply_validation_outcomes(
        rows=rows,
        split_records=split_records,
        dataset=dataset,
        validation=generic_spec.validation,
    )
    return {
        "rows": rows,
        "metrics_by_split": pd.DataFrame(split_records),
        "metrics_by_regime": pd.DataFrame(regime_records),
        "metrics_by_side": pd.DataFrame(side_records),
        "metrics_by_cost_stress": pd.DataFrame(cost_stress_records),
    }


def _real_summary_row(
    *,
    generic_spec: ExperimentSpec,
    candidate: GenericExecutionCandidate,
    metrics: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_path: Path,
    metrics_path: Path,
    validation_hash: str,
    pipeline_status: str,
) -> dict[str, Any]:
    strategy = candidate.strategy
    strategy_config_hash = _stable_hash(_candidate_identity_payload(candidate))
    cache_key = deterministic_experiment_cache_key(
        dataset_manifest_hash=generic_spec.dataset.dataset_manifest_hash,
        feature_manifest_hash=candidate.feature_manifest_hash,
        strategy_config_hash=strategy_config_hash,
        backtest_engine_version=generic_spec.backtest.engine_version,
        validation_spec_hash=validation_hash,
    )
    net_return = float(metrics.get("net_return_after_fees_slippage_funding", 0.0))
    expectancy = float(metrics.get("expectancy_per_trade", 0.0))
    max_drawdown = float(metrics.get("max_drawdown", 0.0))
    final_score = expectancy + net_return + max_drawdown
    failure_reasons = ["research_only_not_promotable", "generic_real_backtest_not_acceptance_evidence"]
    if pipeline_status != "supported":
        failure_reasons.append(f"pipeline_status_{pipeline_status}")
    if int(metrics.get("trade_count", 0)) == 0 and strategy.strategy_id != "baseline_no_trade":
        failure_reasons.append("no_trades_generated")
    if candidate.candidate_index > 0 and pipeline_status != "supported":
        failure_reasons.append("baseline_sequence_not_completed")
    failure_reasons.extend(_unsupported_validation_failure_reasons(generic_spec.validation))
    return {
        "candidate_id": candidate.candidate_id,
        "experiment_name": generic_spec.experiment_name,
        "strategy_id": strategy.strategy_id,
        "strategy_type": strategy.strategy_type,
        "feature_set_id": candidate.feature_set_id,
        "search_method": generic_spec.search.method,
        "search_parameters_json": _canonical_json(candidate.search_parameters),
        "cache_key": cache_key,
        "metric_scope": "real_backtest",
        "metrics_source": "backtest_engine",
        "empirical_evidence": True,
        "aggregate_backtest_evidence": True,
        "backtest_manifest_path": str(manifest_path),
        "metrics_path": str(metrics_path),
        "result_sha256": str(manifest.get("result_sha256") or ""),
        "trade_count": int(metrics.get("trade_count", 0)),
        "long_count": int(metrics.get("long_count", 0)),
        "short_count": int(metrics.get("short_count", 0)),
        "costed_expectancy": expectancy,
        "net_return_after_fees_slippage_funding": net_return,
        "drawdown_adjusted_return": net_return + max_drawdown,
        "max_drawdown": max_drawdown,
        "hit_rate": float(metrics.get("hit_rate", 0.0)),
        "profit_factor": float(metrics.get("profit_factor", 0.0)),
        "final_score": final_score,
        "max_single_split_pnl_share": 1.0,
        "feature_missingness_rate": 0.0,
        "capacity_liquidity_flag": bool((metrics.get("capacity_liquidity_flags") or {}).get("wide_spread_trade_count", 0)),
        "decision": "rejected",
        "failure_reasons": failure_reasons,
    }


def _failed_real_summary_row(
    *,
    generic_spec: ExperimentSpec,
    candidate: GenericExecutionCandidate,
    validation_hash: str,
    pipeline_status: str,
    error: Exception,
) -> dict[str, Any]:
    strategy = candidate.strategy
    strategy_config_hash = _stable_hash(_candidate_identity_payload(candidate))
    cache_key = deterministic_experiment_cache_key(
        dataset_manifest_hash=generic_spec.dataset.dataset_manifest_hash,
        feature_manifest_hash=candidate.feature_manifest_hash,
        strategy_config_hash=strategy_config_hash,
        backtest_engine_version=generic_spec.backtest.engine_version,
        validation_spec_hash=validation_hash,
    )
    failure_reasons = [
        "research_only_not_promotable",
        "generic_real_backtest_not_acceptance_evidence",
        f"backtest_failed:{type(error).__name__}",
    ]
    if pipeline_status != "supported":
        failure_reasons.append(f"pipeline_status_{pipeline_status}")
    if candidate.candidate_index > 0 and pipeline_status != "supported":
        failure_reasons.append("baseline_sequence_not_completed")
    failure_reasons.extend(_unsupported_validation_failure_reasons(generic_spec.validation))
    return {
        "candidate_id": candidate.candidate_id,
        "experiment_name": generic_spec.experiment_name,
        "strategy_id": strategy.strategy_id,
        "strategy_type": strategy.strategy_type,
        "feature_set_id": candidate.feature_set_id,
        "search_method": generic_spec.search.method,
        "search_parameters_json": _canonical_json(candidate.search_parameters),
        "cache_key": cache_key,
        "metric_scope": "real_backtest_failed",
        "metrics_source": "backtest_engine_failed",
        "empirical_evidence": False,
        "aggregate_backtest_evidence": False,
        "backtest_manifest_path": "",
        "metrics_path": "",
        "result_sha256": "",
        "trade_count": 0,
        "long_count": 0,
        "short_count": 0,
        "costed_expectancy": 0.0,
        "net_return_after_fees_slippage_funding": 0.0,
        "drawdown_adjusted_return": 0.0,
        "max_drawdown": 0.0,
        "hit_rate": 0.0,
        "profit_factor": 0.0,
        "final_score": 0.0,
        "max_single_split_pnl_share": 1.0,
        "feature_missingness_rate": 0.0,
        "capacity_liquidity_flag": False,
        "decision": "rejected",
        "failure_reasons": failure_reasons,
    }


def _real_split_records(
    *,
    engine: BacktestEngine,
    generic_spec: ExperimentSpec,
    dataset: pd.DataFrame,
    dataset_path: Path,
    dataset_sha256: str,
    backtest_dir: Path,
    execution_candidates: tuple[GenericExecutionCandidate, ...],
) -> list[dict[str, Any]]:
    if len(dataset) < 12:
        return []
    time_column = "bar_time_ms" if "bar_time_ms" in dataset.columns else (
        "signal_bar_time_ms" if "signal_bar_time_ms" in dataset.columns else "time_ms"
    )
    records: list[dict[str, Any]] = []
    ordered = dataset.sort_values(time_column, kind="mergesort").reset_index(drop=True)
    for candidate in execution_candidates:
        for split in _validation_splits(
            ordered,
            validation=generic_spec.validation,
            time_column=time_column,
        ):
            split_frame = ordered.iloc[split.validation_start_index : split.validation_end_index + 1].copy()
            if split_frame.empty:
                continue
            try:
                result = engine.run(
                    EngineBacktestSpec(
                        run_id=_safe_artifact_name(f"{candidate.candidate_index + 1}-{candidate.candidate_id}-{split.split_id}"),
                        symbol="BTCUSDT",
                        output_dir=backtest_dir / "splits",
                        dataset_path=dataset_path,
                        dataset_sha256=dataset_sha256,
                        strategy_id=candidate.strategy.strategy_id,
                        holding_window=candidate.holding_window,
                        fee_bps=candidate.fee_bps,
                        slippage_bps=candidate.slippage_bps,
                        feature_set_id=candidate.feature_set_id,
                        feature_manifest_sha256=candidate.feature_manifest_hash,
                        strategy_config=_engine_strategy_config(candidate),
                    ),
                    dataset=split_frame,
                )
                metrics = _read_json(result.metrics_path)
                metric_scope = "real_backtest"
                manifest_path = str(result.manifest_path)
                failure_reasons = "research_only_not_promotable"
            except Exception as exc:
                metrics = {}
                metric_scope = "real_backtest_failed"
                manifest_path = ""
                failure_reasons = f"research_only_not_promotable|split_backtest_failed:{type(exc).__name__}"
            records.append(
                {
                    "strategy_id": candidate.strategy.strategy_id,
                    "candidate_id": candidate.candidate_id,
                    "split_index": int(split.split_id.rsplit("-", 1)[-1]),
                    "split_id": split.split_id,
                    "validation_method": split.validation_method,
                    "metric_scope": metric_scope,
                    "trade_count": int(metrics.get("trade_count", 0)),
                    "costed_expectancy": float(metrics.get("expectancy_per_trade", 0.0)),
                    "drawdown_adjusted_return": float(metrics.get("net_return_after_fees_slippage_funding", 0.0)) + float(metrics.get("max_drawdown", 0.0)),
                    "backtest_manifest_path": manifest_path,
                    "failure_reasons": failure_reasons,
                }
            )
    return records


def _validation_splits(
    dataset: pd.DataFrame,
    *,
    validation: ValidationSpec,
    time_column: str,
) -> tuple[Any, ...]:
    splits = []
    for method in validation.methods:
        if method == "anchored_walk_forward":
            splits.extend(
                build_anchored_walk_forward_splits(
                    dataset,
                    min_splits=3,
                    purge_embargo_bars=validation.purge_embargo_bars,
                    time_column=time_column,
                )
            )
        elif method == "rolling_walk_forward":
            splits.extend(
                build_rolling_walk_forward_splits(
                    dataset,
                    min_splits=3,
                    train_window_bars=max(6, len(dataset) // 2),
                    purge_embargo_bars=validation.purge_embargo_bars,
                    time_column=time_column,
                )
            )
        elif method in {"purged_embargoed_split", "purged_embargoed_walk_forward"}:
            splits.extend(
                build_purged_walk_forward_splits(
                    dataset,
                    min_splits=3,
                    purge_embargo_bars=validation.purge_embargo_bars,
                    time_column=time_column,
                    validation_method=method,
                )
            )
    return tuple(splits)


def _apply_validation_outcomes(
    *,
    rows: list[dict[str, Any]],
    split_records: list[dict[str, Any]],
    dataset: pd.DataFrame,
    validation: ValidationSpec,
) -> None:
    missingness_rate = _feature_missingness_rate(dataset)
    split_share_by_candidate = _max_split_share_by_candidate(split_records)
    unsupported_reasons = _unsupported_validation_failure_reasons(validation)
    for row in rows:
        failure_reasons = list(row.get("failure_reasons") or [])
        for reason in unsupported_reasons:
            if reason not in failure_reasons:
                failure_reasons.append(reason)
        candidate_id = str(row.get("candidate_id") or row.get("strategy_id") or "")
        not_executed_reasons = _not_executed_validation_failure_reasons(
            validation,
            observed_methods=_observed_split_validation_methods(split_records, candidate_id=candidate_id),
        )
        for reason in not_executed_reasons:
            if reason not in failure_reasons:
                failure_reasons.append(reason)
        row["feature_missingness_rate"] = missingness_rate
        if missingness_rate > validation.feature_missingness_ceiling:
            _append_unique(failure_reasons, "feature_missingness_above_ceiling")
        if int(row.get("trade_count", 0)) < validation.trade_count_floor:
            _append_unique(failure_reasons, "trade_count_below_floor")
        split_share = split_share_by_candidate.get(candidate_id)
        if split_share is not None:
            row["max_single_split_pnl_share"] = split_share
            if split_share > validation.max_single_split_pnl_share:
                _append_unique(failure_reasons, "single_split_pnl_dominance")
        row["failure_reasons"] = failure_reasons


def _feature_missingness_rate(dataset: pd.DataFrame) -> float:
    if dataset.empty:
        return 1.0
    feature_columns = [
        column
        for column in dataset.columns
        if column
        not in {
            "bar_time_ms",
            "signal_bar_time_ms",
            "time_ms",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }
    ]
    if not feature_columns:
        return 0.0
    total_cells = len(dataset) * len(feature_columns)
    if total_cells <= 0:
        return 0.0
    missing_cells = int(dataset[feature_columns].isna().sum().sum())
    return round(float(missing_cells) / float(total_cells), 8)


def _max_split_share_by_candidate(split_records: list[dict[str, Any]]) -> dict[str, float]:
    frame = pd.DataFrame(split_records)
    if frame.empty or "candidate_id" not in frame.columns:
        return {}
    if "metric_scope" in frame.columns:
        frame = frame.loc[frame["metric_scope"].astype(str) == "real_backtest"].copy()
    if frame.empty:
        return {}
    shares: dict[str, float] = {}
    for candidate_id, group in frame.groupby("candidate_id"):
        scores = pd.to_numeric(group.get("drawdown_adjusted_return", 0.0), errors="coerce").fillna(0.0).abs()
        total = float(scores.sum())
        shares[str(candidate_id)] = 0.0 if total <= 0.0 else round(float(scores.max()) / total, 8)
    return shares


def _validation_method_execution(
    validation: ValidationSpec,
    *,
    empirical_result_scope: str,
    split_frame: pd.DataFrame | None,
    regime_frame: pd.DataFrame | None = None,
    side_frame: pd.DataFrame | None = None,
    cost_stress_frame: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    observed_methods = (
        set()
        if split_frame is None or split_frame.empty or "validation_method" not in split_frame.columns
        else _observed_split_validation_methods(split_frame.to_dict("records"))
    )
    records = []
    for method in validation.methods:
        if empirical_result_scope == "not_run_missing_dataset":
            status = "not_run_missing_dataset"
        elif method in EXECUTABLE_VALIDATION_METHODS and method in observed_methods:
            status = "executed_by_split_backtests"
        elif method in EXECUTABLE_VALIDATION_METHODS:
            status = "not_executed_fail_closed"
        elif method in REPORT_OUTPUT_VALIDATION_METHODS and _report_validation_method_executed(
            method,
            regime_frame=regime_frame,
            side_frame=side_frame,
            cost_stress_frame=cost_stress_frame,
        ):
            status = "executed_by_required_output"
        elif method in REPORT_OUTPUT_VALIDATION_METHODS:
            status = "not_executed_fail_closed"
        else:
            status = "unsupported_fail_closed"
        records.append({"method": method, "status": status})
    return records


def _report_validation_method_executed(
    method: str,
    *,
    regime_frame: pd.DataFrame | None,
    side_frame: pd.DataFrame | None,
    cost_stress_frame: pd.DataFrame | None,
) -> bool:
    if method == "side_separated_reporting":
        return _frame_has_real_backtest_rows(side_frame)
    if method == "regime_separated_reporting":
        return _frame_has_real_backtest_rows(regime_frame)
    if method == "cost_slippage_funding_stress":
        return _frame_has_real_backtest_rows(cost_stress_frame)
    return False


def _frame_has_real_backtest_rows(frame: pd.DataFrame | None) -> bool:
    if frame is None or frame.empty or "metric_scope" not in frame.columns:
        return False
    return bool(frame["metric_scope"].astype(str).eq("real_backtest").any())


def _apply_validation_execution_failures(
    rows: list[dict[str, Any]],
    validation_method_execution: list[dict[str, Any]],
) -> None:
    for reason in _validation_execution_failure_reasons(validation_method_execution):
        for row in rows:
            failure_reasons = list(row.get("failure_reasons") or [])
            _append_unique(failure_reasons, reason)
            row["failure_reasons"] = failure_reasons


def _validation_execution_failure_reasons(validation_method_execution: list[dict[str, Any]]) -> list[str]:
    fail_closed_statuses = {"not_executed_fail_closed", "unsupported_fail_closed"}
    return [
        f"validation_method_not_executed:{record['method']}"
        for record in validation_method_execution
        if str(record.get("status") or "") in fail_closed_statuses
        and str(record.get("method") or "")
    ]


def _unsupported_validation_failure_reasons(validation: ValidationSpec) -> list[str]:
    return [
        f"validation_method_not_executed:{method}"
        for method in validation.methods
        if method not in EXECUTABLE_VALIDATION_METHODS and method not in REPORT_OUTPUT_VALIDATION_METHODS
    ]


def _not_executed_validation_failure_reasons(
    validation: ValidationSpec,
    *,
    observed_methods: set[str],
) -> list[str]:
    return [
        f"validation_method_not_executed:{method}"
        for method in validation.methods
        if method in EXECUTABLE_VALIDATION_METHODS and method not in observed_methods
    ]


def _observed_split_validation_methods(
    split_records: list[dict[str, Any]],
    *,
    candidate_id: str | None = None,
) -> set[str]:
    return {
        str(record.get("validation_method"))
        for record in split_records
        if record.get("validation_method")
        and str(record.get("metric_scope")) == "real_backtest"
        and (candidate_id is None or str(record.get("candidate_id")) == candidate_id)
    }


def _append_unique(values: list[str], item: str) -> None:
    if item not in values:
        values.append(item)


EMPIRICAL_METRIC_FIELDS = (
    "trade_count",
    "long_count",
    "short_count",
    "costed_expectancy",
    "net_return_after_fees_slippage_funding",
    "drawdown_adjusted_return",
    "max_drawdown",
    "hit_rate",
    "profit_factor",
    "final_score",
    "max_single_split_pnl_share",
    "feature_missingness_rate",
)


def _finalize_generic_row_scoreability(rows: list[dict[str, Any]], *, validation: ValidationSpec) -> None:
    for row in rows:
        failure_reasons = list(row.get("failure_reasons") or [])
        aggregate_backtest_evidence = str(row.get("metric_scope") or "") == "real_backtest" and bool(row.get("backtest_manifest_path"))
        missing_configured_validation = _missing_configured_validation_reasons(failure_reasons, validation)
        scoreable = bool(aggregate_backtest_evidence and not missing_configured_validation)
        row["aggregate_backtest_evidence"] = bool(aggregate_backtest_evidence)
        row["validation_evidence_complete"] = bool(scoreable)
        row["scoreable_candidate"] = bool(scoreable)
        if scoreable:
            row["scoreability_status"] = "scoreable_real_backtest_with_required_validation"
            continue
        if str(row.get("metric_scope") or "") == "not_run_missing_dataset":
            row["scoreability_status"] = "not_scoreable_missing_dataset"
        elif str(row.get("metric_scope") or "") == "real_backtest_failed":
            row["scoreability_status"] = "not_scoreable_backtest_failed"
        elif aggregate_backtest_evidence and missing_configured_validation:
            row["metric_scope"] = "real_backtest_validation_incomplete"
            row["metrics_source"] = "backtest_engine_validation_incomplete"
            row["empirical_evidence"] = False
            row["scoreability_status"] = "not_scoreable_validation_incomplete"
        else:
            row["scoreability_status"] = "not_scoreable_no_empirical_metrics"
        _clear_empirical_metric_fields(row)


def _missing_configured_validation_reasons(failure_reasons: list[str], validation: ValidationSpec) -> list[str]:
    configured_methods = {str(method) for method in validation.methods}
    return [
        reason
        for reason in failure_reasons
        if reason.startswith("validation_method_not_executed:")
        and reason.split(":", maxsplit=1)[1] in configured_methods
    ]


def _clear_empirical_metric_fields(row: dict[str, Any]) -> None:
    for field in EMPIRICAL_METRIC_FIELDS:
        row[field] = None


def _real_cost_stress_records(
    *,
    engine: BacktestEngine,
    generic_spec: ExperimentSpec,
    dataset_path: Path,
    dataset_sha256: str,
    candidate: GenericExecutionCandidate,
    backtest_dir: Path,
) -> list[dict[str, Any]]:
    records = []
    for stress in candidate.funding_stress_bps:
        try:
            result = engine.run(
                EngineBacktestSpec(
                    run_id=_safe_artifact_name(f"{candidate.candidate_index + 1}-{candidate.candidate_id}-funding-{stress:g}"),
                    symbol="BTCUSDT",
                    output_dir=backtest_dir / "cost_stress",
                    dataset_path=dataset_path,
                    dataset_sha256=dataset_sha256,
                    strategy_id=candidate.strategy.strategy_id,
                    holding_window=candidate.holding_window,
                    fee_bps=candidate.fee_bps,
                    slippage_bps=candidate.slippage_bps,
                    funding_rate=float(stress) / 10000.0,
                    feature_set_id=candidate.feature_set_id,
                    feature_manifest_sha256=candidate.feature_manifest_hash,
                    strategy_config=_engine_strategy_config(candidate),
                )
            )
            metrics = _read_json(result.metrics_path)
            metric_scope = "real_backtest"
            manifest_path = str(result.manifest_path)
            failure_reasons = ""
        except Exception as exc:
            metrics = {}
            metric_scope = "real_backtest_failed"
            manifest_path = ""
            failure_reasons = f"cost_stress_backtest_failed:{type(exc).__name__}"
        records.append(
            {
                "strategy_id": candidate.strategy.strategy_id,
                "candidate_id": candidate.candidate_id,
                "funding_stress_bps": float(stress),
                "fee_bps": candidate.fee_bps,
                "slippage_bps": candidate.slippage_bps,
                "metric_scope": metric_scope,
                "trade_count": int(metrics.get("trade_count", 0)),
                "stressed_expectancy": float(metrics.get("expectancy_per_trade", 0.0)),
                "stressed_net_return": float(metrics.get("net_return_after_fees_slippage_funding", 0.0)),
                "backtest_manifest_path": manifest_path,
                "failure_reasons": failure_reasons,
            }
        )
    return records


def _regime_records_from_metrics(row: Mapping[str, Any], metrics: Mapping[str, Any]) -> list[dict[str, Any]]:
    split_by_regime = metrics.get("split_by_regime") or {}
    if not split_by_regime:
        return [
            {
                "strategy_id": row["strategy_id"],
                "candidate_id": row.get("candidate_id", ""),
                "regime": "none",
                "trade_count": int(row["trade_count"]),
                "costed_expectancy": float(row["costed_expectancy"]),
                "metric_scope": row["metric_scope"],
            }
        ]
    return [
        {
            "strategy_id": row["strategy_id"],
            "candidate_id": row.get("candidate_id", ""),
            "regime": str(regime),
            "trade_count": int(payload.get("trade_count", 0)),
            "costed_expectancy": float(payload.get("expectancy", 0.0)),
            "metric_scope": row["metric_scope"],
        }
        for regime, payload in split_by_regime.items()
    ]


def _side_records_from_trades(row: Mapping[str, Any], trades_path: Path) -> list[dict[str, Any]]:
    if not trades_path.exists():
        return []
    trades = pd.read_parquet(trades_path)
    records = []
    for side in ("long", "short"):
        side_trades = trades.loc[trades["side"].astype(str).str.lower() == side] if not trades.empty and "side" in trades.columns else trades.iloc[0:0]
        returns = pd.to_numeric(side_trades["net_return"], errors="coerce").fillna(0.0) if "net_return" in side_trades.columns else pd.Series(dtype=float)
        records.append(
            {
                "strategy_id": row["strategy_id"],
                "candidate_id": row.get("candidate_id", ""),
                "side": side,
                "trade_count": int(len(side_trades)),
                "costed_expectancy": float(returns.mean()) if len(returns) else 0.0,
                "minimum_evidence_passed": int(len(side_trades)) >= 1,
                "metric_scope": row["metric_scope"],
            }
        )
    return records


def _empty_side_records(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "strategy_id": row["strategy_id"],
            "candidate_id": row.get("candidate_id", ""),
            "side": side,
            "trade_count": 0,
            "costed_expectancy": 0.0,
            "minimum_evidence_passed": False,
            "metric_scope": row["metric_scope"],
        }
        for side in ("long", "short")
    ]


def _candidate_rankings(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    if "final_score" not in frame.columns:
        frame["final_score"] = None
    if "scoreable_candidate" not in frame.columns:
        frame["scoreable_candidate"] = False
    scoreable = frame.loc[frame["scoreable_candidate"].astype(bool)].copy()
    non_scoreable = frame.loc[~frame["scoreable_candidate"].astype(bool)].copy()
    scoreable = scoreable.sort_values(["final_score", "trade_count"], ascending=[False, False], kind="mergesort")
    non_scoreable = non_scoreable.sort_values(["candidate_id"], kind="mergesort") if "candidate_id" in non_scoreable.columns else non_scoreable
    ranked = pd.concat([scoreable, non_scoreable], ignore_index=True)
    ranked["rank"] = None
    if not scoreable.empty:
        ranked.loc[: len(scoreable) - 1, "rank"] = range(1, len(scoreable) + 1)
    return ranked


def _generic_dataset_identity(
    *,
    resolved_dataset_path: Path | None,
    supplied_spec: ExperimentSpec | None,
    artifact_links: Mapping[str, Any],
) -> dict[str, Any]:
    dataset_artifact_sha256 = _hash_file(resolved_dataset_path) if resolved_dataset_path is not None else None
    dataset_manifest_path = str(artifact_links.get("dataset_manifest_path") or "") or None
    dataset_manifest_sha256 = _hash_optional_artifact(dataset_manifest_path)
    supplied_dataset_manifest_hash = None
    if supplied_spec is not None and supplied_spec.dataset.dataset_manifest_hash != "dataset_manifest_unavailable":
        supplied_dataset_manifest_hash = supplied_spec.dataset.dataset_manifest_hash
    identity_payload = {
        "resolved_dataset_path": str(resolved_dataset_path) if resolved_dataset_path is not None else None,
        "dataset_artifact_sha256": dataset_artifact_sha256,
        "dataset_manifest_path": dataset_manifest_path,
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "supplied_dataset_manifest_hash": supplied_dataset_manifest_hash,
    }
    return {
        **identity_payload,
        "dataset_identity_hash": _stable_hash(identity_payload),
        "dataset_identity_contract": (
            "hash(resolved_dataset_path, dataset_artifact_sha256, dataset_manifest_sha256, supplied_dataset_manifest_hash)"
        ),
    }


def _resolve_generic_dataset_path(
    *,
    run_spec: ResearchExperimentSpec,
    supplied_spec: ExperimentSpec | None,
    artifact_links: Mapping[str, Any],
    evidence_manifest: Mapping[str, Any],
) -> Path | None:
    if supplied_spec is not None and supplied_spec.dataset.dataset_path:
        supplied_candidate = _resolve_existing_path(
            supplied_spec.dataset.dataset_path,
            base_path=run_spec.experiment_spec.parent if run_spec.experiment_spec is not None else run_spec.pipeline_spec.parent,
        )
        if supplied_candidate.exists() and supplied_candidate.is_file() and supplied_candidate.suffix.lower() == ".parquet":
            return supplied_candidate
        return None

    candidates: list[Path] = []
    if evidence_manifest.get("dataset_path"):
        candidates.append(_resolve_existing_path(evidence_manifest["dataset_path"], base_path=run_spec.pipeline_spec.parent))
    for experiment in evidence_manifest.get("experiments") or []:
        if isinstance(experiment, Mapping) and experiment.get("dataset_path"):
            candidates.append(_resolve_existing_path(experiment["dataset_path"], base_path=run_spec.pipeline_spec.parent))

    dataset_manifest_path = artifact_links.get("dataset_manifest_path")
    if dataset_manifest_path:
        manifest_path = Path(str(dataset_manifest_path))
        if manifest_path.exists():
            manifest = _read_json(manifest_path)
            for key in ("dataset_path", "parquet_path", "data_path"):
                if manifest.get(key):
                    candidates.append(_resolve_existing_path(manifest.get(key), base_path=manifest_path.parent))

    for key in ("effective_pipeline_spec_path", "source_pipeline_spec_path"):
        spec_path = artifact_links.get(key)
        if not spec_path:
            continue
        path = Path(str(spec_path))
        if not path.exists():
            continue
        pipeline_spec = _read_json(path)
        evidence_stage = pipeline_spec.get("evidence_stage") or {}
        if isinstance(evidence_stage, Mapping) and evidence_stage.get("dataset_path"):
            candidates.append(_resolve_existing_path(evidence_stage["dataset_path"], base_path=path.parent))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() == ".parquet":
            return candidate
    return None


def _resolve_existing_path(value: Any, *, base_path: Path) -> Path:
    candidate = Path(str(value)).expanduser()
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate.resolve()
    return (base_path / candidate).resolve()


def _safe_artifact_name(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return "-".join(part for part in safe.split("-") if part) or "artifact"


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "candidate_id",
        "experiment_name",
        "strategy_id",
        "strategy_type",
        "feature_set_id",
        "search_method",
        "search_parameters_json",
        "cache_key",
        "metric_scope",
        "metrics_source",
        "empirical_evidence",
        "aggregate_backtest_evidence",
        "validation_evidence_complete",
        "scoreable_candidate",
        "scoreability_status",
        "backtest_manifest_path",
        "metrics_path",
        "result_sha256",
        "trade_count",
        "long_count",
        "short_count",
        "costed_expectancy",
        "net_return_after_fees_slippage_funding",
        "drawdown_adjusted_return",
        "max_drawdown",
        "hit_rate",
        "profit_factor",
        "final_score",
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
            payload = {field: row.get(field, "") for field in fields}
            payload["failure_reasons"] = "|".join(row["failure_reasons"])
            writer.writerow(payload)


def _empty_split_metrics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "strategy_id",
            "candidate_id",
            "split_index",
            "validation_method",
            "trade_count",
            "costed_expectancy",
            "drawdown_adjusted_return",
            "backtest_manifest_path",
            "failure_reasons",
        ]
    )


def _empty_regime_metrics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "strategy_id",
            "candidate_id",
            "regime",
            "trade_count",
            "costed_expectancy",
            "metric_scope",
        ]
    )


def _empty_side_metrics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "strategy_id",
            "candidate_id",
            "side",
            "trade_count",
            "costed_expectancy",
            "minimum_evidence_passed",
            "metric_scope",
        ]
    )


def _empty_cost_stress_metrics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "strategy_id",
            "candidate_id",
            "funding_stress_bps",
            "fee_bps",
            "slippage_bps",
            "metric_scope",
            "trade_count",
            "stressed_expectancy",
            "stressed_net_return",
            "backtest_manifest_path",
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
    pipeline_spec = _resolve_pipeline_spec_paths(_read_json(spec.pipeline_spec), source_dir=spec.pipeline_spec.parent)
    pipeline_spec["output_dir"] = str(output_dir / "pipeline")
    evidence_stage = dict(pipeline_spec.get("evidence_stage") or {})
    evidence_stage.pop("experiment_spec", None)
    pipeline_experiment_spec = _pipeline_evidence_experiment_spec(spec.experiment_spec)
    if pipeline_experiment_spec is not None:
        evidence_stage["enabled"] = True
        evidence_stage["experiment_spec"] = str(pipeline_experiment_spec)
    evidence_stage["workers"] = spec.workers
    evidence_stage["write_monitoring"] = spec.write_monitoring
    pipeline_spec["evidence_stage"] = evidence_stage
    effective_path = specs_dir / "provider_pipeline.effective.json"
    effective_path.write_text(_canonical_json(pipeline_spec, indent=2) + "\n", encoding="utf-8")
    return effective_path


def _resolve_pipeline_spec_paths(pipeline_spec: Mapping[str, Any], *, source_dir: Path) -> dict[str, Any]:
    resolved = dict(pipeline_spec)
    providers = []
    for provider in resolved.get("providers") or []:
        if not isinstance(provider, Mapping):
            providers.append(provider)
            continue
        provider_payload = dict(provider)
        inputs = []
        for item in provider_payload.get("inputs") or []:
            if not isinstance(item, Mapping):
                inputs.append(item)
                continue
            input_payload = dict(item)
            if input_payload.get("path"):
                input_payload["path"] = str(_resolve_path(input_payload["path"], base_path=source_dir))
            inputs.append(input_payload)
        provider_payload["inputs"] = inputs
        providers.append(provider_payload)
    if providers:
        resolved["providers"] = providers
    dataset_stage = dict(resolved.get("dataset_stage") or {})
    for key in ("research_config", "db_path"):
        if dataset_stage.get(key):
            dataset_stage[key] = str(_resolve_path(dataset_stage[key], base_path=source_dir))
    if dataset_stage:
        resolved["dataset_stage"] = dataset_stage
    evidence_stage = dict(resolved.get("evidence_stage") or {})
    for key in ("dataset_path", "hmm_knn_config", "experiment_spec"):
        if evidence_stage.get(key):
            evidence_stage[key] = str(_resolve_path(evidence_stage[key], base_path=source_dir))
    if evidence_stage:
        resolved["evidence_stage"] = evidence_stage
    return resolved


def _pipeline_evidence_experiment_spec(path: Path | None) -> Path | None:
    if path is None or not path.exists():
        return None
    try:
        payload = _read_json(path)
    except Exception:
        return None
    if _looks_like_generic_experiment_spec(payload):
        return None
    if _looks_like_hmm_knn_matrix_spec(payload):
        return path
    return None


def _looks_like_generic_experiment_spec(payload: Mapping[str, Any]) -> bool:
    return (
        isinstance(payload.get("dataset"), Mapping)
        or isinstance(payload.get("feature"), Mapping)
        or isinstance(payload.get("strategies"), list)
        or isinstance(payload.get("backtest"), Mapping)
        or isinstance(payload.get("validation"), Mapping)
        or isinstance(payload.get("search"), Mapping)
    )


def _looks_like_hmm_knn_matrix_spec(payload: Mapping[str, Any]) -> bool:
    return isinstance(payload.get("experiments"), list) and bool(payload.get("base_config_path"))


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
    if candidate.is_absolute():
        return candidate.resolve()
    base_candidate = (base_path / candidate).resolve()
    if base_candidate.exists():
        return base_candidate
    repo_candidate = (_repo_root_from_path(base_path) / candidate).resolve()
    if repo_candidate.exists():
        return repo_candidate
    return base_candidate


def _resolve_output_path(path: Any, *, base_path: Path) -> Path:
    candidate = Path(str(path)).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_path / candidate).resolve()


def _repo_root_from_path(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent.resolve()
    return Path.cwd().resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _ensure_inside_research_root(path: Path, *, research_root: Path, field_name: str) -> None:
    resolved_path = path.resolve()
    resolved_root = research_root.resolve()
    if not _is_relative_to(resolved_path, resolved_root):
        raise ValueError(f"{field_name} must be inside the configured research output directory")


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
