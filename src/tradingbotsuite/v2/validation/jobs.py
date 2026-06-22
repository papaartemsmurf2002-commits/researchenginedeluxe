# V2-AUDIT-ID: V2-AUD-VAL-003
# V2-CONTRACTS: docs/contracts/validation_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_validation_gate, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_validation
"""Durable validation gate worker for v2 run manifests."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.backtest_engine.artifacts import RunManifest, RunStatus
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobRecord, WorkerRunResult

VALIDATION_GATE_MANIFEST_SCHEMA_VERSION = "validation_gate_manifest_v1"
VALIDATION_GATE_MIN_COVERAGE = 0.98
VALIDATION_GATE_MIN_USABLE_MONTHS = 6
VALIDATION_GATE_EARLIEST_START = date(2024, 1, 1)
VALIDATION_GATE_REQUIRED_COST_SCENARIOS = ("base", "stress_2x", "stress_3x")
_SECRET_NAME_RE = re.compile(
    r"(^\.env$|secret|credential|private|token|password|wallet|api[_-]?key)",
    re.IGNORECASE,
)


class ValidationGateManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = VALIDATION_GATE_MANIFEST_SCHEMA_VERSION
    validation_manifest_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    run_manifest_path: str = Field(min_length=1)
    run_manifest_sha256: str = Field(min_length=64, max_length=64)
    validation_status: str = Field(pattern=r"^(pass|fail)$")
    evidence_mode: str = Field(min_length=1)
    blocker_reasons: tuple[str, ...] = ()
    fold_count: int = Field(ge=0)
    positive_fold_count: int = Field(ge=0)
    fold_stability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    cost_stress_scenarios: tuple[str, ...] = ()
    cost_fragile_warning: bool = False
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_manifest(self) -> "ValidationGateManifest":
        if self.validation_status == "pass" and self.blocker_reasons:
            raise ValueError("passing validation gate manifests cannot carry blockers")
        if self.validation_status == "fail" and not self.blocker_reasons:
            raise ValueError("failing validation gate manifests require blockers")
        require_research_boundary(self, context="validation gate manifest")
        return self


def run_validation_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    if job.kind != WorkerJobKind.VALIDATION_GATE:
        raise ValueError(f"unsupported validation job kind: {job.kind.value}")
    return _run_validation_gate_job(job=job, store=store, worker_id=worker_id)


def _run_validation_gate_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    run_manifest_path = _required_run_manifest_path(spec)
    run_dir = run_manifest_path.parent
    output_path = _validation_output_path(spec, run_dir=run_dir)
    evidence_mode = str(spec.get("evidence_mode", "sandbox_diagnostic")).strip().lower()
    if evidence_mode not in {"sandbox_diagnostic", "accepted_research"}:
        raise ValueError("validation gate evidence_mode must be sandbox_diagnostic or accepted_research")

    manifest = RunManifest.model_validate(_read_json(run_manifest_path))
    fold_rows = _read_parquet_artifact(manifest, "fold_metrics", run_dir=run_dir)
    cost_rows = _read_parquet_artifact(manifest, "cost_stress", run_dir=run_dir)
    blockers = _validation_blockers(
        manifest,
        evidence_mode=evidence_mode,
        fold_rows=fold_rows,
        cost_rows=cost_rows,
    )
    fold_count, positive_fold_count, fold_score = _fold_stability(fold_rows)
    scenarios = tuple(str(row.get("scenario_id", "")) for row in cost_rows if row.get("scenario_id"))
    report_payload = {
        "schema_version": VALIDATION_GATE_MANIFEST_SCHEMA_VERSION,
        "validation_manifest_id": "0" * 64,
        "run_id": manifest.run_id,
        "run_manifest_path": str(run_manifest_path),
        "run_manifest_sha256": file_sha256(run_manifest_path),
        "validation_status": "fail" if blockers else "pass",
        "evidence_mode": evidence_mode,
        "blocker_reasons": tuple(sorted(dict.fromkeys(blockers))),
        "fold_count": fold_count,
        "positive_fold_count": positive_fold_count,
        "fold_stability_score": fold_score,
        "cost_stress_scenarios": tuple(dict.fromkeys(scenarios)),
        "cost_fragile_warning": any(bool(row.get("cost_fragile_warning")) for row in cost_rows),
        **dict(RESEARCH_BOUNDARY),
    }
    report_payload["validation_manifest_id"] = canonical_json_hash(
        {key: value for key, value in report_payload.items() if key != "validation_manifest_id"}
    )
    report = ValidationGateManifest.model_validate(report_payload)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    output_refs = (
        "job_kind=validation_gate",
        f"run_id={report.run_id}",
        f"validation_status={report.validation_status}",
        f"validation_manifest_id={report.validation_manifest_id}",
        f"validation_manifest_path={output_path}",
        f"validation_manifest_sha256={file_sha256(output_path)}",
        f"run_manifest_sha256={report.run_manifest_sha256}",
        f"fold_count={report.fold_count}",
        f"fold_stability_score={'' if report.fold_stability_score is None else f'{report.fold_stability_score:.12f}'}",
        f"cost_stress_scenarios={','.join(report.cost_stress_scenarios)}",
        f"cost_fragile_warning={str(report.cost_fragile_warning).lower()}",
        f"blocker_reasons={','.join(report.blocker_reasons)}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=(
            f"archive_snapshot_id={manifest.archive_snapshot_id}",
            f"universe_snapshot_id={manifest.universe_snapshot_id}",
            f"validation_manifest_id={report.validation_manifest_id}",
        ),
        reason="validation_gate_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _validation_blockers(
    manifest: RunManifest,
    *,
    evidence_mode: str,
    fold_rows: list[dict[str, Any]],
    cost_rows: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if manifest.status != RunStatus.SUCCEEDED:
        blockers.append(f"run_status_{manifest.status.value}")
    if manifest.validation_status.value != "pass":
        blockers.append(f"run_manifest_validation_status_{manifest.validation_status.value}")
    if manifest.backtest_start.date() < VALIDATION_GATE_EARLIEST_START:
        blockers.append("backtest_start_before_2024")
    if manifest.usable_months < VALIDATION_GATE_MIN_USABLE_MONTHS:
        blockers.append("usable_months_below_6")
    if manifest.data_coverage_min < VALIDATION_GATE_MIN_COVERAGE:
        blockers.append("coverage_below_0_98")
    if evidence_mode == "accepted_research" and manifest.universe_mode != "as_of":
        blockers.append("accepted_research_requires_asof_universe")
    if (
        manifest.lockbox_start is not None
        and manifest.lockbox_end is not None
        and manifest.backtest_start < manifest.lockbox_end
        and manifest.backtest_end > manifest.lockbox_start
    ):
        blockers.append("lockbox_overlap")

    fold_count, _positive_fold_count, fold_score = _fold_stability(fold_rows)
    if fold_count == 0:
        blockers.append("fold_metrics_missing")
    elif fold_score is not None and fold_score < 0.5:
        blockers.append("fold_stability_below_min_share")

    scenarios = {str(row.get("scenario_id", "")) for row in cost_rows}
    for scenario in VALIDATION_GATE_REQUIRED_COST_SCENARIOS:
        if scenario not in scenarios:
            blockers.append(f"cost_stress_scenario_missing:{scenario}")
    if any(bool(row.get("cost_dependent_failure")) for row in cost_rows):
        blockers.append("cost_dependent_failure")
    return blockers


def _fold_stability(rows: list[dict[str, Any]]) -> tuple[int, int, float | None]:
    if not rows:
        return 0, 0, None
    returns = [float(row.get("net_return", 0.0)) for row in rows]
    positive = sum(1 for value in returns if value > 0.0)
    return len(returns), positive, positive / len(returns)


def _required_run_manifest_path(spec: dict[str, Any]) -> Path:
    value = spec.get("run_manifest_path")
    if not isinstance(value, str) or not value:
        raise ValueError("validation gate job spec requires run_manifest_path")
    path = _validate_path(Path(value), field_name="run_manifest_path", allowed_suffixes=(".json",))
    if path.name != "run_manifest.json":
        raise ValueError("validation gate run_manifest_path must point to run_manifest.json")
    if not path.exists() or not path.is_file():
        raise ValueError(f"run_manifest_path missing: {path}")
    return path


def _validation_output_path(spec: dict[str, Any], *, run_dir: Path) -> Path:
    raw = spec.get("validation_manifest_path")
    path = run_dir / "validation_gate_manifest.json" if raw is None else Path(str(raw))
    resolved = _validate_path(path, field_name="validation_manifest_path", allowed_suffixes=(".json",))
    try:
        resolved.relative_to(run_dir.resolve(strict=False))
    except ValueError as exc:
        raise ValueError("validation_manifest_path must stay inside the run manifest directory") from exc
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _read_parquet_artifact(
    manifest: RunManifest,
    name: str,
    *,
    run_dir: Path,
) -> list[dict[str, Any]]:
    ref = manifest.artifacts.get(name)
    if ref is None:
        raise ValueError(f"run manifest missing {name} artifact ref")
    path = _artifact_path(run_dir, ref.path)
    if file_sha256(path) != ref.sha256:
        raise ValueError(f"{name} artifact sha256 mismatch")
    return pq.read_table(path).to_pylist()


def _artifact_path(run_dir: Path, ref_path: str) -> Path:
    path = (run_dir / ref_path).resolve(strict=False)
    try:
        path.relative_to(run_dir.resolve(strict=False))
    except ValueError as exc:
        raise ValueError(f"artifact path escapes run directory: {ref_path}") from exc
    if not path.exists() or not path.is_file():
        raise ValueError(f"artifact path missing: {ref_path}")
    return path


def _validate_path(
    path: Path,
    *,
    field_name: str,
    allowed_suffixes: tuple[str, ...],
) -> Path:
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise ValueError(f"{field_name} name is reserved for secrets or local state")
    suffix = path.suffix.lower()
    if suffix not in allowed_suffixes:
        raise ValueError(
            f"{field_name} must use one of these suffixes: {','.join(allowed_suffixes)}"
        )
    return path.resolve(strict=False)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
