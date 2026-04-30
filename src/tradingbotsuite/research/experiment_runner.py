from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Mapping

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


@dataclass(frozen=True, slots=True)
class ResearchExperimentRunResult:
    output_dir: Path
    manifest_path: Path
    conclusion_path: Path
    pipeline_summary_path: Path


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
    manifest_path = output_dir / "experiment_run_manifest.json"
    manifest_path.write_text(_canonical_json(manifest, indent=2) + "\n", encoding="utf-8")
    return ResearchExperimentRunResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        conclusion_path=conclusion_path,
        pipeline_summary_path=pipeline_result.pipeline_summary_path,
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


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _canonical_json(payload: Any, *, indent: int | None = None) -> str:
    return json.dumps(payload, indent=indent, sort_keys=True, default=str)
