# V2-AUDIT-ID: V2-AUD-AUTONOMY-004
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md, docs/contracts/worker_job_contract.md, docs/contracts/audit_report_contract.md
# V2-BOUNDARY: research_only, bounded_cycle_plan, durable_enqueue_only, no_live_imports
# V2-OWNER: v2_autonomy
"""Bounded durable research-cycle planner for v2."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.autonomy.schemas import (
    AutopilotCycleJobSpec,
    AutopilotCyclePlanConfig,
    AutopilotCyclePlanManifest,
    AutopilotCyclePlanResult,
    AutopilotCyclePlanStatus,
    AutopilotPlannedJob,
)
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_SECRET_NAME_RE = re.compile(
    r"(^\.env$|secret|credential|private|token|password|wallet|api[_-]?key)",
    re.IGNORECASE,
)
_BOUNDARY_OVERRIDE_KEYS = frozenset(
    {
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    }
)
_ALLOWED_PLANNED_JOB_KINDS = frozenset(
    {
        WorkerJobKind.UNIVERSE_REFRESH,
        WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        WorkerJobKind.FUNDING_BACKFILL,
        WorkerJobKind.WEBSOCKET_CAPTURE,
        WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        WorkerJobKind.OFFICIAL_S3_BACKFILL,
        WorkerJobKind.COVERAGE_AUDIT,
        WorkerJobKind.VECTORIZED_BACKTEST,
        WorkerJobKind.LEDGER_APPEND_EXPORT,
        WorkerJobKind.LEAD_BOOK_UPSERT,
    }
)
_COLLECTOR_STAGE_KINDS = frozenset(
    {
        WorkerJobKind.RECENT_CANDLE_BOOTSTRAP,
        WorkerJobKind.FUNDING_BACKFILL,
        WorkerJobKind.WEBSOCKET_CAPTURE,
        WorkerJobKind.WEBSOCKET_TRADE_CAPTURE,
        WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE,
        WorkerJobKind.OFFICIAL_S3_BACKFILL,
    }
)
_REQUIRED_STAGE_KINDS = (
    ("universe_refresh", frozenset({WorkerJobKind.UNIVERSE_REFRESH})),
    ("collector", _COLLECTOR_STAGE_KINDS),
    ("coverage_audit", frozenset({WorkerJobKind.COVERAGE_AUDIT})),
    ("vectorized_backtest", frozenset({WorkerJobKind.VECTORIZED_BACKTEST})),
    ("ledger_append_export", frozenset({WorkerJobKind.LEDGER_APPEND_EXPORT})),
    ("lead_book_upsert", frozenset({WorkerJobKind.LEAD_BOOK_UPSERT})),
)
_DEFAULT_ARTIFACT_REF_PREFIXES = (
    "universe_snapshot_id=",
    "archive_snapshot_id=",
    "coverage_report_id",
    "run_manifest_path=",
    "ledger_path=",
    "lead_book_path=",
)
_DEFAULT_NEXT_ACTIONS = (
    "run_planned_worker_jobs_in_declared_order",
    "run_generated_audit_check_after_worker_jobs_finish",
    "resolve_reported_blockers_before_claiming_research_ready",
)


class AutopilotCyclePlanError(ValueError):
    """Raised when a bounded research-cycle plan cannot be accepted."""


def load_autopilot_cycle_spec(path: str | Path) -> AutopilotCyclePlanConfig:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise AutopilotCyclePlanError(f"cycle spec cannot be read: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AutopilotCyclePlanError(f"cycle spec is not valid JSON: {path}") from exc
    try:
        return AutopilotCyclePlanConfig.model_validate(payload)
    except ValidationError as exc:
        raise AutopilotCyclePlanError(f"cycle spec validation failed: {exc}") from exc


def plan_autopilot_research_cycle(
    config: AutopilotCyclePlanConfig | dict[str, Any],
    *,
    output_root: str | Path,
    job_store_path: str | Path | None = None,
    enqueue: bool = False,
) -> AutopilotCyclePlanResult:
    parsed = config if isinstance(config, AutopilotCyclePlanConfig) else AutopilotCyclePlanConfig.model_validate(config)
    if not _SAFE_RUN_ID.fullmatch(parsed.run_id):
        raise AutopilotCyclePlanError(f"unsafe_run_id: {parsed.run_id}")
    if len(parsed.jobs) > parsed.max_jobs:
        raise AutopilotCyclePlanError(
            f"bounded cycle has {len(parsed.jobs)} jobs, above max_jobs={parsed.max_jobs}"
        )
    _validate_job_specs(parsed.jobs)
    _validate_required_stage_coverage(parsed.jobs)

    root = Path(output_root).resolve()
    run_root = (root / parsed.run_id).resolve()
    try:
        run_root.relative_to(root)
    except ValueError as exc:
        raise AutopilotCyclePlanError("cycle output root escapes requested output_root") from exc
    run_root.mkdir(parents=True, exist_ok=True)

    audit_job_id = parsed.audit_job_id or f"JOB-{parsed.run_id}-audit"
    audit_report_path = _audit_report_path(parsed, run_root=run_root)
    required_successful = _required_successful_job_kinds(parsed)
    required_order = _required_job_kind_order(parsed)
    required_prefixes = parsed.required_artifact_ref_prefixes or _DEFAULT_ARTIFACT_REF_PREFIXES
    required_next_actions = parsed.required_next_actions or _DEFAULT_NEXT_ACTIONS
    planned_jobs = _planned_jobs(parsed, audit_job_id=audit_job_id)
    audit_input_spec = {
        "run_id": parsed.run_id,
        "report_path": str(audit_report_path),
        "target_job_ids": [job.job_id for job in parsed.jobs],
        "required_successful_job_kinds": [kind.value for kind in required_successful],
        "required_artifact_ref_prefixes": list(required_prefixes),
        "required_job_kind_order": [kind.value for kind in required_order],
        "required_next_actions": list(required_next_actions),
    }
    audit_planned_job = AutopilotPlannedJob(
        job_id=audit_job_id,
        kind=WorkerJobKind.AUDIT_CHECK,
        input_spec_hash=canonical_json_hash(audit_input_spec),
        max_attempts=1,
        dependency_order=len(planned_jobs),
        generated_by_planner=True,
        enqueued=enqueue,
    )
    if enqueue:
        _enqueue_plan(
            parsed,
            job_store_path=job_store_path,
            audit_job_id=audit_job_id,
            audit_input_spec=audit_input_spec,
        )
        planned_jobs = tuple(job.model_copy(update={"enqueued": True}) for job in planned_jobs)
    all_planned_jobs = (*planned_jobs, audit_planned_job)
    plan_manifest_path = run_root / "autopilot_cycle_plan.json"
    status = AutopilotCyclePlanStatus.ENQUEUED if enqueue else AutopilotCyclePlanStatus.PLANNED
    identity = {
        "schema_version": "autopilot_bounded_cycle_plan_v1",
        "run_id": parsed.run_id,
        "status": status.value,
        "job_store_path": None if job_store_path is None else str(Path(job_store_path).resolve(strict=False)),
        "planned_jobs": [job.model_dump(mode="json") for job in all_planned_jobs],
        "audit_report_path": str(audit_report_path),
        "required_successful_job_kinds": [kind.value for kind in required_successful],
        "required_artifact_ref_prefixes": list(required_prefixes),
        "required_job_kind_order": [kind.value for kind in required_order],
        "required_next_actions": list(required_next_actions),
    }
    plan_id = canonical_json_hash(identity)
    manifest = AutopilotCyclePlanManifest(
        plan_id=plan_id,
        run_id=parsed.run_id,
        status=status,
        output_root=str(root),
        job_store_path=identity["job_store_path"],
        plan_manifest_path=str(plan_manifest_path),
        planned_jobs=all_planned_jobs,
        audit_job_id=audit_job_id,
        audit_report_path=str(audit_report_path),
        required_successful_job_kinds=tuple(identity["required_successful_job_kinds"]),
        required_artifact_ref_prefixes=tuple(identity["required_artifact_ref_prefixes"]),
        required_job_kind_order=tuple(identity["required_job_kind_order"]),
        required_next_actions=tuple(identity["required_next_actions"]),
    )
    plan_manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return AutopilotCyclePlanResult(
        status=status,
        plan_manifest_path=str(plan_manifest_path),
        plan_id=plan_id,
        planned_job_count=len(all_planned_jobs),
        enqueued_job_count=len(all_planned_jobs) if enqueue else 0,
        audit_job_id=audit_job_id,
        audit_report_path=str(audit_report_path),
    )


def _validate_job_specs(jobs: tuple[AutopilotCycleJobSpec, ...]) -> None:
    for job in jobs:
        if job.kind not in _ALLOWED_PLANNED_JOB_KINDS:
            raise AutopilotCyclePlanError(
                f"bounded cycle does not support worker kind: {job.kind.value}"
            )
        boundary_path = _find_boundary_override_path(job.input_spec)
        if boundary_path is not None:
            raise AutopilotCyclePlanError(
                f"job {job.job_id} input_spec attempts boundary override: {boundary_path}"
            )


def _validate_required_stage_coverage(jobs: tuple[AutopilotCycleJobSpec, ...]) -> None:
    kinds = {job.kind for job in jobs}
    missing = [
        stage_name
        for stage_name, stage_kinds in _REQUIRED_STAGE_KINDS
        if not kinds.intersection(stage_kinds)
    ]
    if missing:
        raise AutopilotCyclePlanError(
            "bounded cycle is missing required stage(s): " + ",".join(missing)
        )


def _planned_jobs(
    parsed: AutopilotCyclePlanConfig,
    *,
    audit_job_id: str,
) -> tuple[AutopilotPlannedJob, ...]:
    if audit_job_id in {job.job_id for job in parsed.jobs}:
        raise AutopilotCyclePlanError("generated audit_job_id duplicates a planned job")
    return tuple(
        AutopilotPlannedJob(
            job_id=job.job_id,
            kind=job.kind,
            input_spec_hash=canonical_json_hash(job.input_spec),
            max_attempts=job.max_attempts,
            dependency_order=index,
            generated_by_planner=False,
            enqueued=False,
        )
        for index, job in enumerate(parsed.jobs)
    )


def _enqueue_plan(
    parsed: AutopilotCyclePlanConfig,
    *,
    job_store_path: str | Path | None,
    audit_job_id: str,
    audit_input_spec: dict[str, Any],
) -> None:
    if job_store_path is None:
        raise AutopilotCyclePlanError("enqueue requires job_store_path")
    store = WorkerJobStore(job_store_path)
    store.initialize()
    all_job_ids = [job.job_id for job in parsed.jobs] + [audit_job_id]
    existing = [job_id for job_id in all_job_ids if store.load_job(job_id) is not None]
    if existing:
        raise AutopilotCyclePlanError("bounded cycle job already exists: " + ",".join(existing))
    for job in parsed.jobs:
        store.enqueue(
            kind=job.kind,
            job_id=job.job_id,
            input_spec=job.input_spec,
            max_attempts=job.max_attempts,
            reason="autopilot_cycle_plan_enqueued",
        )
    store.enqueue(
        kind=WorkerJobKind.AUDIT_CHECK,
        job_id=audit_job_id,
        input_spec=audit_input_spec,
        max_attempts=1,
        reason="autopilot_cycle_audit_job_enqueued",
    )


def _audit_report_path(parsed: AutopilotCyclePlanConfig, *, run_root: Path) -> Path:
    if parsed.audit_report_path is None:
        return run_root / "audit_blocker_report.json"
    path = Path(parsed.audit_report_path)
    if path.is_absolute():
        raise AutopilotCyclePlanError("audit_report_path must be relative to the cycle run root")
    if path.suffix.lower() != ".json":
        raise AutopilotCyclePlanError("audit_report_path must end with .json")
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise AutopilotCyclePlanError("audit_report_path name is reserved for secrets or local state")
    resolved = (run_root / path).resolve(strict=False)
    try:
        resolved.relative_to(run_root)
    except ValueError as exc:
        raise AutopilotCyclePlanError("audit_report_path escapes cycle run root") from exc
    return resolved


def _required_successful_job_kinds(parsed: AutopilotCyclePlanConfig) -> tuple[WorkerJobKind, ...]:
    if parsed.required_successful_job_kinds:
        return parsed.required_successful_job_kinds
    return _unique_kinds(tuple(job.kind for job in parsed.jobs))


def _required_job_kind_order(parsed: AutopilotCyclePlanConfig) -> tuple[WorkerJobKind, ...]:
    if parsed.required_job_kind_order:
        return parsed.required_job_kind_order
    return _unique_kinds(tuple(job.kind for job in parsed.jobs))


def _unique_kinds(kinds: tuple[WorkerJobKind, ...]) -> tuple[WorkerJobKind, ...]:
    return tuple(dict.fromkeys(kinds))


def _find_boundary_override_path(value: Any, *, prefix: str = "input_spec") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            next_prefix = f"{prefix}.{key}"
            if str(key) in _BOUNDARY_OVERRIDE_KEYS:
                return next_prefix
            found = _find_boundary_override_path(item, prefix=next_prefix)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _find_boundary_override_path(item, prefix=f"{prefix}[{index}]")
            if found is not None:
                return found
    return None
