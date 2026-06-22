# V2-AUDIT-ID: V2-AUD-AUTONOMY-014
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, bounded_scheduler_tick, durable_workers_only, no_live_imports
# V2-OWNER: v2_autonomy
"""Run-once bounded scheduler tick for enqueued autopilot cycle plans."""

from __future__ import annotations

import json
import re
from pathlib import Path

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.autonomy.cycle_runner import (
    AutopilotCycleRunnerError,
    run_autopilot_cycle_plan,
)
from tradingbotsuite.v2.autonomy.schemas import (
    AutopilotSchedulerPlanAction,
    AutopilotSchedulerPlanResult,
    AutopilotSchedulerTickManifest,
    AutopilotSchedulerTickResult,
    AutopilotSchedulerTickStatus,
)

_SECRET_NAME_RE = re.compile(
    r"(^\.env$|secret|credential|private|token|password|wallet|api[_-]?key)",
    re.IGNORECASE,
)


class AutopilotSchedulerError(ValueError):
    """Raised when a scheduler tick request is unsafe or invalid."""


def run_autopilot_scheduler_tick(
    *,
    plan_manifest_paths: tuple[str | Path, ...],
    output_root: str | Path,
    job_store_path: str | Path | None = None,
    worker_id: str = "autopilot-scheduler",
    scheduler_id: str = "autopilot-scheduler",
    max_plans: int = 1,
    max_jobs_per_plan: int | None = None,
    run_audit_on_blocker: bool = True,
) -> AutopilotSchedulerTickResult:
    if not plan_manifest_paths:
        raise AutopilotSchedulerError("scheduler tick requires at least one plan manifest")
    if max_plans < 1:
        raise AutopilotSchedulerError("max_plans must be positive")
    if max_jobs_per_plan is not None and max_jobs_per_plan < 1:
        raise AutopilotSchedulerError("max_jobs_per_plan must be positive")

    output_dir = _validate_output_root(output_root)
    selected = tuple(Path(path).resolve(strict=False) for path in plan_manifest_paths[:max_plans])
    deferred = tuple(Path(path).resolve(strict=False) for path in plan_manifest_paths[max_plans:])
    plan_results: list[AutopilotSchedulerPlanResult] = []
    blockers: list[str] = []

    for plan_path in selected:
        result = _run_one_plan(
            plan_path=plan_path,
            job_store_path=job_store_path,
            worker_id=worker_id,
            max_jobs_per_plan=max_jobs_per_plan,
            run_audit_on_blocker=run_audit_on_blocker,
        )
        plan_results.append(result)
        blockers.extend(
            f"scheduler_plan_blocker:{plan_path}:{reason}"
            for reason in result.blocker_reasons
        )

    for plan_path in deferred:
        reason = f"scheduler_plan_deferred_max_plans:{plan_path}"
        plan_results.append(
            AutopilotSchedulerPlanResult(
                plan_manifest_path=str(plan_path),
                action=AutopilotSchedulerPlanAction.DEFERRED_MAX_PLANS,
                status="deferred",
                blocker_reasons=(reason,),
            )
        )
        blockers.append(reason)

    status = (
        AutopilotSchedulerTickStatus.COMPLETED_WITH_BLOCKERS
        if blockers
        else AutopilotSchedulerTickStatus.COMPLETED
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "autopilot_scheduler_tick.json"
    identity = {
        "schema_version": "autopilot_scheduler_tick_v1",
        "scheduler_id": scheduler_id,
        "status": status.value,
        "output_root": str(output_dir),
        "job_store_path": str(Path(job_store_path).resolve(strict=False)) if job_store_path else None,
        "worker_id": worker_id,
        "max_plans": max_plans,
        "max_jobs_per_plan": max_jobs_per_plan,
        "requested_plan_paths": [str(Path(path).resolve(strict=False)) for path in plan_manifest_paths],
        "plan_results": [result.model_dump(mode="json") for result in plan_results],
        "blocker_reasons": blockers,
    }
    session_id = canonical_json_hash(identity)
    manifest = AutopilotSchedulerTickManifest(
        session_id=session_id,
        scheduler_id=scheduler_id,
        status=status,
        output_root=str(output_dir),
        scheduler_manifest_path=str(manifest_path),
        job_store_path=identity["job_store_path"],
        worker_id=worker_id,
        max_plans=max_plans,
        max_jobs_per_plan=max_jobs_per_plan,
        requested_plan_count=len(plan_manifest_paths),
        selected_plan_count=len(selected),
        executed_plan_count=sum(
            1 for result in plan_results if result.action == AutopilotSchedulerPlanAction.RAN
        ),
        blocker_count=len(_unique(tuple(blockers))),
        blocker_reasons=_unique(tuple(blockers)),
        plan_results=tuple(plan_results),
    )
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return AutopilotSchedulerTickResult(
        status=status,
        scheduler_manifest_path=str(manifest_path),
        session_id=session_id,
        executed_plan_count=manifest.executed_plan_count,
        blocker_reasons=manifest.blocker_reasons,
    )


def _run_one_plan(
    *,
    plan_path: Path,
    job_store_path: str | Path | None,
    worker_id: str,
    max_jobs_per_plan: int | None,
    run_audit_on_blocker: bool,
) -> AutopilotSchedulerPlanResult:
    try:
        result = run_autopilot_cycle_plan(
            plan_path,
            job_store_path=job_store_path,
            worker_id=worker_id,
            max_jobs=max_jobs_per_plan,
            run_audit_on_blocker=run_audit_on_blocker,
        )
    except (AutopilotCycleRunnerError, ValueError) as exc:
        return AutopilotSchedulerPlanResult(
            plan_manifest_path=str(plan_path),
            action=AutopilotSchedulerPlanAction.BLOCKED,
            status="blocked",
            blocker_reasons=(f"scheduler_plan_rejected:{plan_path}:{exc}",),
        )
    return AutopilotSchedulerPlanResult(
        plan_manifest_path=str(plan_path),
        action=AutopilotSchedulerPlanAction.RAN,
        status=result.status.value,
        execution_manifest_path=result.execution_manifest_path,
        execution_id=result.execution_id,
        audit_report_path=result.audit_report_path,
        executed_job_count=result.executed_job_count,
        skipped_job_count=result.skipped_job_count,
        audit_attempted=result.audit_attempted,
        blocker_reasons=result.blocker_reasons,
    )


def _validate_output_root(path_value: str | Path) -> Path:
    path = Path(path_value).resolve(strict=False)
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise AutopilotSchedulerError("scheduler output root cannot be secret-like")
    return path


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))
