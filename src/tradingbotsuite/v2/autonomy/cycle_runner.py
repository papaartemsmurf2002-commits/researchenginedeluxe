# V2-AUDIT-ID: V2-AUD-AUTONOMY-006
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md, docs/contracts/worker_job_contract.md, docs/contracts/audit_report_contract.md
# V2-BOUNDARY: research_only, bounded_cycle_execution, durable_workers_only, no_live_imports
# V2-OWNER: v2_autonomy
"""Bounded executor for enqueued v2 autopilot research-cycle plans."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.autonomy.schemas import (
    AutopilotCycleBindingSpec,
    AutopilotCycleExecutionManifest,
    AutopilotCycleExecutionResult,
    AutopilotCycleExecutionStatus,
    AutopilotCycleJobExecution,
    AutopilotCycleJobExecutionAction,
    AutopilotCyclePlanManifest,
    AutopilotCyclePlanStatus,
    AutopilotPlannedJob,
)
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobRecord, WorkerJobStatus
from tradingbotsuite.v2.workers.runner import run_one_job

_BOUNDARY_INPUT_KEYS = frozenset(
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


class AutopilotCycleRunnerError(ValueError):
    """Raised when a bounded research-cycle plan cannot be executed safely."""


def load_autopilot_cycle_plan(path: str | Path) -> AutopilotCyclePlanManifest:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise AutopilotCycleRunnerError(f"cycle plan cannot be read: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AutopilotCycleRunnerError(f"cycle plan is not valid JSON: {path}") from exc
    try:
        return AutopilotCyclePlanManifest.model_validate(payload)
    except ValidationError as exc:
        raise AutopilotCycleRunnerError(f"cycle plan validation failed: {exc}") from exc


def run_autopilot_cycle_plan(
    plan_manifest_path: str | Path,
    *,
    job_store_path: str | Path | None = None,
    worker_id: str = "autopilot-cycle-runner",
    max_jobs: int | None = None,
    run_audit_on_blocker: bool = True,
) -> AutopilotCycleExecutionResult:
    plan_path = Path(plan_manifest_path).resolve(strict=False)
    plan = load_autopilot_cycle_plan(plan_path)
    if plan.status != AutopilotCyclePlanStatus.ENQUEUED:
        raise AutopilotCycleRunnerError("bounded cycle execution requires an enqueued plan manifest")
    if not plan.planned_jobs:
        raise AutopilotCycleRunnerError("bounded cycle plan has no planned jobs")
    if any(not planned.enqueued for planned in plan.planned_jobs):
        raise AutopilotCycleRunnerError("bounded cycle plan contains unenqueued jobs")
    _validate_plan_bindings(plan)

    store_path = _resolve_job_store_path(plan, job_store_path=job_store_path)
    job_limit = max_jobs if max_jobs is not None else len(plan.planned_jobs)
    if job_limit < 1:
        raise AutopilotCycleRunnerError("max_jobs must be positive")

    store = WorkerJobStore(store_path)
    store.initialize()
    executions: list[AutopilotCycleJobExecution] = []
    execution_blockers: list[str] = []
    executed_job_count = 0
    skipped_job_count = 0
    audit_attempted = False
    non_audit_blocked = False

    for planned in sorted(plan.planned_jobs, key=lambda job: (job.dependency_order, job.job_id)):
        is_audit = planned.job_id == plan.audit_job_id
        if non_audit_blocked and not is_audit:
            execution = _not_run_after_blocker(planned)
            executions.append(execution)
            execution_blockers.extend(execution.blocker_reasons)
            continue
        if is_audit and non_audit_blocked and not run_audit_on_blocker:
            execution = _not_run_after_blocker(planned)
            executions.append(execution)
            execution_blockers.extend(execution.blocker_reasons)
            continue
        if executed_job_count >= job_limit:
            execution = _not_run_max_jobs(planned)
            executions.append(execution)
            execution_blockers.extend(execution.blocker_reasons)
            if not is_audit:
                non_audit_blocked = True
            continue

        execution = _run_or_skip_planned_job(
            store=store,
            planned=planned,
            worker_id=worker_id,
            bindings=tuple(
                binding for binding in plan.bindings if binding.target_job_id == planned.job_id
            ),
        )
        executions.append(execution)
        execution_blockers.extend(execution.blocker_reasons)
        if execution.action == AutopilotCycleJobExecutionAction.RAN:
            executed_job_count += 1
            if is_audit:
                audit_attempted = True
        if execution.action == AutopilotCycleJobExecutionAction.SKIPPED_ALREADY_SUCCEEDED:
            skipped_job_count += 1
        if execution.blocker_reasons and not is_audit:
            non_audit_blocked = True

    audit_blockers = _audit_report_blockers(plan.audit_report_path)
    blockers = _unique((*execution_blockers, *audit_blockers))
    status = (
        AutopilotCycleExecutionStatus.COMPLETED_WITH_BLOCKERS
        if blockers
        else AutopilotCycleExecutionStatus.COMPLETED
    )
    execution_manifest_path = plan_path.parent / "autopilot_cycle_execution.json"
    identity = {
        "schema_version": "autopilot_bounded_cycle_execution_v1",
        "plan_id": plan.plan_id,
        "run_id": plan.run_id,
        "status": status.value,
        "plan_manifest_path": str(plan_path),
        "job_store_path": str(store_path),
        "worker_id": worker_id,
        "max_jobs": job_limit,
        "executed_job_count": executed_job_count,
        "skipped_job_count": skipped_job_count,
        "audit_job_id": plan.audit_job_id,
        "audit_report_path": plan.audit_report_path,
        "blocker_reasons": blockers,
        "job_executions": [execution.model_dump(mode="json") for execution in executions],
    }
    execution_id = canonical_json_hash(identity)
    manifest = AutopilotCycleExecutionManifest(
        execution_id=execution_id,
        plan_id=plan.plan_id,
        run_id=plan.run_id,
        status=status,
        plan_manifest_path=str(plan_path),
        execution_manifest_path=str(execution_manifest_path),
        job_store_path=str(store_path),
        worker_id=worker_id,
        max_jobs=job_limit,
        planned_job_count=len(plan.planned_jobs),
        executed_job_count=executed_job_count,
        skipped_job_count=skipped_job_count,
        audit_job_id=plan.audit_job_id,
        audit_report_path=plan.audit_report_path,
        audit_attempted=audit_attempted,
        blocker_count=len(blockers),
        blocker_reasons=blockers,
        job_executions=tuple(executions),
    )
    execution_manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return AutopilotCycleExecutionResult(
        status=status,
        execution_manifest_path=str(execution_manifest_path),
        execution_id=execution_id,
        audit_report_path=plan.audit_report_path,
        executed_job_count=executed_job_count,
        skipped_job_count=skipped_job_count,
        audit_attempted=audit_attempted,
        blocker_reasons=blockers,
    )


def _resolve_job_store_path(
    plan: AutopilotCyclePlanManifest,
    *,
    job_store_path: str | Path | None,
) -> Path:
    if plan.job_store_path is None and job_store_path is None:
        raise AutopilotCycleRunnerError("enqueued cycle plan does not record a job_store_path")
    plan_store = Path(plan.job_store_path).resolve(strict=False) if plan.job_store_path else None
    requested_store = Path(job_store_path).resolve(strict=False) if job_store_path else None
    if plan_store is not None and requested_store is not None and plan_store != requested_store:
        raise AutopilotCycleRunnerError(
            f"requested job_store does not match plan manifest: {requested_store} != {plan_store}"
        )
    return plan_store or requested_store  # type: ignore[return-value]


def _validate_plan_bindings(plan: AutopilotCyclePlanManifest) -> None:
    if not plan.bindings:
        return
    order_by_job_id = {job.job_id: job.dependency_order for job in plan.planned_jobs}
    generated_job_ids = {job.job_id for job in plan.planned_jobs if job.generated_by_planner}
    for binding in plan.bindings:
        if binding.source_job_id not in order_by_job_id:
            raise AutopilotCycleRunnerError(
                f"binding source_job_id is not in the plan manifest: {binding.source_job_id}"
            )
        if binding.target_job_id not in order_by_job_id:
            raise AutopilotCycleRunnerError(
                f"binding target_job_id is not in the plan manifest: {binding.target_job_id}"
            )
        if binding.source_job_id in generated_job_ids or binding.target_job_id in generated_job_ids:
            raise AutopilotCycleRunnerError(
                "bounded cycle bindings cannot use generated audit jobs"
            )
        if order_by_job_id[binding.source_job_id] >= order_by_job_id[binding.target_job_id]:
            raise AutopilotCycleRunnerError(
                "binding source job must precede target job: "
                f"{binding.source_job_id}->{binding.target_job_id}"
            )
        unsafe_segment = _unsafe_input_path_segment(binding.target_input_path)
        if unsafe_segment is not None:
            raise AutopilotCycleRunnerError(
                f"binding target_input_path attempts boundary override: {unsafe_segment}"
            )


def _run_or_skip_planned_job(
    *,
    store: WorkerJobStore,
    planned: AutopilotPlannedJob,
    worker_id: str,
    bindings: tuple[AutopilotCycleBindingSpec, ...],
) -> AutopilotCycleJobExecution:
    before = store.load_job(planned.job_id)
    if before is None:
        reason = f"planned_job_missing:{planned.job_id}"
        return _job_execution(
            planned,
            action=AutopilotCycleJobExecutionAction.BLOCKED_MISSING,
            blocker_reasons=(reason,),
        )
    if before.status == WorkerJobStatus.SUCCEEDED:
        return _job_execution(
            planned,
            action=AutopilotCycleJobExecutionAction.SKIPPED_ALREADY_SUCCEEDED,
            status_before=before.status.value,
            status_after=before.status.value,
            record=before,
        )
    if before.status != WorkerJobStatus.QUEUED:
        reason = f"planned_job_not_queued_or_succeeded:{planned.job_id}:{before.status.value}"
        return _job_execution(
            planned,
            action=AutopilotCycleJobExecutionAction.BLOCKED_STATUS,
            status_before=before.status.value,
            status_after=before.status.value,
            record=before,
            blocker_reasons=(reason,),
        )

    next_queued = store.list_jobs(kind=planned.kind, status=WorkerJobStatus.QUEUED)
    if not next_queued or next_queued[0].job_id != planned.job_id:
        next_job_id = next_queued[0].job_id if next_queued else "none"
        reason = f"planned_job_not_next_for_kind:{planned.job_id}:{planned.kind.value}:next={next_job_id}"
        return _job_execution(
            planned,
            action=AutopilotCycleJobExecutionAction.BLOCKED_NOT_NEXT_FOR_KIND,
            status_before=before.status.value,
            status_after=before.status.value,
            record=before,
            blocker_reasons=(reason,),
        )

    bind_record, applied_bindings, binding_blockers = _apply_bindings(
        store=store,
        target=before,
        bindings=bindings,
        worker_id=worker_id,
    )
    if binding_blockers:
        return _job_execution(
            planned,
            action=AutopilotCycleJobExecutionAction.BLOCKED_BINDING,
            status_before=before.status.value,
            status_after=bind_record.status.value,
            input_spec_hash_before=before.input_spec_hash,
            input_spec_hash_after=bind_record.input_spec_hash,
            record=bind_record,
            applied_bindings=applied_bindings,
            blocker_reasons=binding_blockers,
        )

    result = run_one_job(store=store, kind=planned.kind, worker_id=worker_id)
    after = store.load_job(planned.job_id)
    blockers: list[str] = []
    if result is None:
        blockers.append(f"planned_job_not_claimed:{planned.job_id}")
    elif result.job_id != planned.job_id:
        blockers.append(f"planned_job_claim_mismatch:{planned.job_id}:ran={result.job_id}")
    elif result.status != WorkerJobStatus.SUCCEEDED:
        blockers.append(f"planned_job_not_succeeded:{planned.job_id}:{result.status.value}")
    record = after or before
    return _job_execution(
        planned,
        action=AutopilotCycleJobExecutionAction.RAN,
        status_before=before.status.value,
        status_after=record.status.value,
        input_spec_hash_before=before.input_spec_hash,
        input_spec_hash_after=bind_record.input_spec_hash,
        record=record,
        applied_bindings=applied_bindings,
        blocker_reasons=tuple(blockers),
    )


def _apply_bindings(
    *,
    store: WorkerJobStore,
    target: WorkerJobRecord,
    bindings: tuple[AutopilotCycleBindingSpec, ...],
    worker_id: str,
) -> tuple[WorkerJobRecord, tuple[str, ...], tuple[str, ...]]:
    if not bindings:
        return target, (), ()
    blockers: list[str] = []
    applied: list[str] = []
    bound_spec = deepcopy(target.input_spec)
    for binding in bindings:
        unsafe_segment = _unsafe_input_path_segment(binding.target_input_path)
        if unsafe_segment is not None:
            blockers.append(
                f"binding_target_input_path_forbidden:{binding.target_job_id}:{unsafe_segment}"
            )
            continue
        source = store.load_job(binding.source_job_id)
        if source is None:
            blockers.append(
                f"binding_source_job_missing:{binding.target_job_id}:{binding.source_job_id}"
            )
            continue
        if source.status != WorkerJobStatus.SUCCEEDED:
            blockers.append(
                "binding_source_job_not_succeeded:"
                f"{binding.target_job_id}:{binding.source_job_id}:{source.status.value}"
            )
            continue
        values = _matching_ref_values(source, binding.source_ref_prefix)
        if not values:
            blockers.append(
                f"binding_ref_missing:{binding.target_job_id}:{binding.source_job_id}:{binding.source_ref_prefix}"
            )
            continue
        if len(values) > 1:
            blockers.append(
                "binding_ref_ambiguous:"
                f"{binding.target_job_id}:{binding.source_job_id}:{binding.source_ref_prefix}"
            )
            continue
        try:
            _set_input_path(bound_spec, binding.target_input_path, values[0])
        except ValueError as exc:
            blockers.append(
                f"binding_target_input_path_invalid:{binding.target_job_id}:{binding.target_input_path}:{exc}"
            )
            continue
        applied.append(
            "input_spec."
            f"{binding.target_input_path}<={binding.source_job_id}:{binding.source_ref_prefix}{values[0]}"
        )
    if blockers:
        return target, (), tuple(blockers)
    try:
        updated = store.update_queued_input_spec(
            target.job_id,
            input_spec=bound_spec,
            worker_id=worker_id,
            reason="autopilot_cycle_binding_applied",
        )
    except (KeyError, ValueError) as exc:
        return target, (), (f"binding_input_spec_update_failed:{target.job_id}:{exc}",)
    return updated, tuple(applied), ()


def _matching_ref_values(record: WorkerJobRecord, prefix: str) -> tuple[str, ...]:
    values = []
    for ref in (*record.output_refs, *record.archive_manifest_refs):
        if not ref.startswith(prefix):
            continue
        value = ref[len(prefix) :]
        if value:
            values.append(value)
    return tuple(dict.fromkeys(values))


def _set_input_path(spec: dict[str, Any], path: str, value: str) -> None:
    current = spec
    segments = path.split(".")
    for segment in segments[:-1]:
        next_value = current.get(segment)
        if next_value is None:
            next_value = {}
            current[segment] = next_value
        if not isinstance(next_value, dict):
            raise ValueError(f"non_object_segment:{segment}")
        current = next_value
    current[segments[-1]] = value


def _unsafe_input_path_segment(path: str) -> str | None:
    for segment in path.split("."):
        if segment in _BOUNDARY_INPUT_KEYS:
            return segment
    return None


def _job_execution(
    planned: AutopilotPlannedJob,
    *,
    action: AutopilotCycleJobExecutionAction,
    status_before: str | None = None,
    status_after: str | None = None,
    input_spec_hash_before: str | None = None,
    input_spec_hash_after: str | None = None,
    record: WorkerJobRecord | None = None,
    applied_bindings: tuple[str, ...] = (),
    blocker_reasons: tuple[str, ...] = (),
) -> AutopilotCycleJobExecution:
    return AutopilotCycleJobExecution(
        job_id=planned.job_id,
        kind=planned.kind,
        dependency_order=planned.dependency_order,
        generated_by_planner=planned.generated_by_planner,
        action=action,
        status_before=status_before,
        status_after=status_after,
        input_spec_hash_before=input_spec_hash_before,
        input_spec_hash_after=input_spec_hash_after,
        applied_bindings=applied_bindings,
        output_refs=record.output_refs if record else (),
        archive_manifest_refs=record.archive_manifest_refs if record else (),
        gap_record_ids=record.gap_record_ids if record else (),
        failure_reason=record.failure_reason if record else None,
        blocker_reasons=blocker_reasons,
    )


def _not_run_after_blocker(planned: AutopilotPlannedJob) -> AutopilotCycleJobExecution:
    return _job_execution(
        planned,
        action=AutopilotCycleJobExecutionAction.NOT_RUN_AFTER_BLOCKER,
        blocker_reasons=(f"planned_job_not_run_after_blocker:{planned.job_id}",),
    )


def _not_run_max_jobs(planned: AutopilotPlannedJob) -> AutopilotCycleJobExecution:
    return _job_execution(
        planned,
        action=AutopilotCycleJobExecutionAction.NOT_RUN_MAX_JOBS,
        blocker_reasons=(f"max_jobs_exhausted_before:{planned.job_id}",),
    )


def _audit_report_blockers(audit_report_path: str) -> tuple[str, ...]:
    path = Path(audit_report_path)
    if not path.exists():
        return ()
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return (f"audit_report_unreadable:{path}",)
    blockers = payload.get("blocker_reasons", ())
    if not isinstance(blockers, list):
        return (f"audit_report_invalid_blocker_reasons:{path}",)
    return _unique(tuple(str(reason) for reason in blockers if reason))


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))
