# V2-AUDIT-ID: V2-AUD-AUDIT-001
# V2-CONTRACTS: docs/contracts/audit_report_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_audit_check, blocker_report, no_live_imports
# V2-OWNER: v2_audit
"""Durable worker job handlers for v2 audit/blocker reports."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.audit.schemas import (
    AuditBlockerReport,
    AuditJobSummary,
    AuditReportStatus,
)
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobRecord, WorkerJobStatus, WorkerRunResult

_SECRET_NAME_RE = re.compile(
    r"(^\.env$|secret|credential|private|token|password|wallet|api[_-]?key)",
    re.IGNORECASE,
)
_BLOCKER_REF_PREFIXES = {
    "blocker_reasons": "",
    "known_blockers": "",
    "missing_evidence": "missing_evidence:",
}


def run_audit_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    if job.kind != WorkerJobKind.AUDIT_CHECK:
        raise ValueError(f"unsupported audit job kind: {job.kind.value}")
    return _run_audit_check_job(job=job, store=store, worker_id=worker_id)


def build_audit_blocker_report(
    *,
    run_id: str,
    job_store_path: str | Path,
    jobs: tuple[WorkerJobRecord, ...],
    extra_blocker_reasons: tuple[str, ...] = (),
    required_next_actions: tuple[str, ...] = (),
    artifact_refs: tuple[str, ...] = (),
    required_successful_job_kinds: tuple[WorkerJobKind, ...] = (),
    required_artifact_ref_prefixes: tuple[str, ...] = (),
) -> AuditBlockerReport:
    summaries = tuple(_summarize_job(record) for record in jobs)
    required_evidence_blockers = _required_evidence_blockers(
        jobs=jobs,
        required_successful_job_kinds=required_successful_job_kinds,
        required_artifact_ref_prefixes=required_artifact_ref_prefixes,
    )
    blocker_reasons = _unique(
        (
            *extra_blocker_reasons,
            *required_evidence_blockers,
            *(reason for summary in summaries for reason in summary.blocker_reasons),
        )
    )
    status = (
        AuditReportStatus.COMPLETED_WITH_BLOCKERS
        if blocker_reasons
        else AuditReportStatus.PASS
    )
    next_actions = _unique(required_next_actions or _default_next_actions(blocker_reasons))
    refs = _unique(
        (
            *artifact_refs,
            *(ref for summary in summaries for ref in summary.output_refs),
            *(ref for summary in summaries for ref in summary.archive_manifest_refs),
        )
    )
    job_status_counts = dict(Counter(summary.status for summary in summaries))
    identity = {
        "schema_version": "audit_blocker_report_v1",
        "run_id": run_id,
        "job_store_path": str(Path(job_store_path).resolve(strict=False)),
        "audited_job_ids": [summary.job_id for summary in summaries],
        "job_status_counts": job_status_counts,
        "blocker_reasons": blocker_reasons,
        "required_next_actions": next_actions,
        "required_successful_job_kinds": [kind.value for kind in required_successful_job_kinds],
        "required_artifact_ref_prefixes": list(required_artifact_ref_prefixes),
        "artifact_refs": refs,
        "job_summaries": [summary.model_dump(mode="json") for summary in summaries],
    }
    return AuditBlockerReport(
        report_id=canonical_json_hash(identity),
        run_id=run_id,
        created_at=utc_now(),
        status=status,
        accepted_research_ready=False,
        job_store_path=identity["job_store_path"],
        audited_job_ids=tuple(identity["audited_job_ids"]),
        job_status_counts=job_status_counts,
        blocker_reasons=blocker_reasons,
        required_next_actions=next_actions,
        required_successful_job_kinds=tuple(identity["required_successful_job_kinds"]),
        required_artifact_ref_prefixes=tuple(identity["required_artifact_ref_prefixes"]),
        artifact_refs=refs,
        job_summaries=summaries,
    )


def _run_audit_check_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = dict(job.input_spec)
    report_path = _required_path(spec, "report_path", allowed_suffixes=(".json",))
    target_job_ids = _optional_string_tuple(spec.get("target_job_ids"))
    jobs, missing_targets = _select_jobs(store=store, current_job_id=job.job_id, target_job_ids=target_job_ids)
    extra_blockers = _unique(
        (
            *_optional_string_tuple(spec.get("extra_blocker_reasons"), default=()),
            *(f"target_job_missing:{target}" for target in missing_targets),
        )
    )
    required_successful_job_kinds = _optional_worker_job_kind_tuple(
        spec.get("required_successful_job_kinds"),
        default=(),
    )
    required_artifact_ref_prefixes = _optional_string_tuple(
        spec.get("required_artifact_ref_prefixes"),
        default=(),
    )
    report = build_audit_blocker_report(
        run_id=str(spec.get("run_id") or job.job_id),
        job_store_path=store.path,
        jobs=tuple(jobs),
        extra_blocker_reasons=extra_blockers,
        required_next_actions=_optional_string_tuple(spec.get("required_next_actions"), default=()),
        artifact_refs=_optional_string_tuple(spec.get("artifact_refs"), default=()),
        required_successful_job_kinds=required_successful_job_kinds,
        required_artifact_ref_prefixes=required_artifact_ref_prefixes,
    )
    _write_report(report_path, report)
    output_refs = [
        "job_kind=audit_check",
        f"report_id={report.report_id}",
        f"report_status={report.status.value}",
        f"accepted_research_ready={str(report.accepted_research_ready).lower()}",
        f"blocker_count={len(report.blocker_reasons)}",
        f"report_path={report_path}",
        f"report_sha256={file_sha256(report_path)}",
    ]
    if required_successful_job_kinds:
        output_refs.append(
            f"required_successful_job_kinds={_csv(kind.value for kind in required_successful_job_kinds)}"
        )
    if required_artifact_ref_prefixes:
        output_refs.append(
            f"required_artifact_ref_prefixes={_csv(required_artifact_ref_prefixes)}"
        )
    domain_refs = (
        f"report_path={report_path}",
        f"report_sha256={file_sha256(report_path)}",
        f"audited_job_count={len(report.audited_job_ids)}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=tuple(output_refs),
        archive_manifest_refs=domain_refs,
        reason="audit_check_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _summarize_job(record: WorkerJobRecord) -> AuditJobSummary:
    blockers = list(_job_status_blockers(record))
    blockers.extend(_blocker_refs(record.output_refs))
    if record.gap_record_ids:
        blockers.append(f"gap_records_present:{record.job_id}")
    return AuditJobSummary(
        job_id=record.job_id,
        kind=record.kind.value,
        status=record.status.value,
        terminal_state=record.terminal_state,
        attempts=record.attempts,
        failure_reason=record.failure_reason,
        blocker_reasons=_unique(blockers),
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _job_status_blockers(record: WorkerJobRecord) -> tuple[str, ...]:
    if record.status == WorkerJobStatus.FAILED:
        reason = record.failure_reason or "unknown_failure"
        return (f"job_failed:{record.job_id}:{reason}",)
    if record.status == WorkerJobStatus.STALE:
        return (f"job_stale:{record.job_id}",)
    if record.status == WorkerJobStatus.CANCELLED:
        return (f"job_cancelled:{record.job_id}",)
    if record.status in {WorkerJobStatus.QUEUED, WorkerJobStatus.CLAIMED, WorkerJobStatus.RUNNING, WorkerJobStatus.RETRYING}:
        return (f"job_incomplete:{record.job_id}:{record.status.value}",)
    return ()


def _blocker_refs(refs: tuple[str, ...]) -> tuple[str, ...]:
    blockers: list[str] = []
    for ref in refs:
        key, separator, value = ref.partition("=")
        if separator != "=" or key not in _BLOCKER_REF_PREFIXES or not value:
            continue
        prefix = _BLOCKER_REF_PREFIXES[key]
        blockers.extend(f"{prefix}{item}" for item in value.split(",") if item)
    return _unique(blockers)


def _required_evidence_blockers(
    *,
    jobs: tuple[WorkerJobRecord, ...],
    required_successful_job_kinds: tuple[WorkerJobKind, ...],
    required_artifact_ref_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    successful_kinds = {
        record.kind.value
        for record in jobs
        if record.status == WorkerJobStatus.SUCCEEDED
    }
    refs = tuple(
        ref
        for record in jobs
        for ref in (*record.output_refs, *record.archive_manifest_refs)
    )
    blockers: list[str] = []
    for kind in required_successful_job_kinds:
        if kind.value not in successful_kinds:
            blockers.append(f"missing_evidence:successful_job_kind:{kind.value}")
    for prefix in required_artifact_ref_prefixes:
        if not any(ref.startswith(prefix) for ref in refs):
            blockers.append(f"missing_evidence:artifact_ref_prefix:{prefix}")
    return _unique(blockers)


def _select_jobs(
    *,
    store: WorkerJobStore,
    current_job_id: str,
    target_job_ids: tuple[str, ...] | None,
) -> tuple[list[WorkerJobRecord], tuple[str, ...]]:
    if target_job_ids is None:
        return [record for record in store.list_jobs() if record.job_id != current_job_id], ()
    selected: list[WorkerJobRecord] = []
    missing: list[str] = []
    for target in target_job_ids:
        if target == current_job_id:
            continue
        record = store.load_job(target)
        if record is None:
            missing.append(target)
        else:
            selected.append(record)
    return selected, tuple(missing)


def _required_path(
    spec: dict[str, Any],
    key: str,
    *,
    allowed_suffixes: tuple[str, ...],
) -> Path:
    value = spec.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"audit worker job spec requires {key}")
    path = Path(value)
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise ValueError(f"{key} name is reserved for secrets or local state")
    suffix = path.suffix.lower()
    if suffix not in allowed_suffixes:
        raise ValueError(f"{key} must use one of these suffixes: {','.join(allowed_suffixes)}")
    return path.resolve(strict=False)


def _optional_string_tuple(value: Any, *, default: tuple[str, ...] | None = None) -> tuple[str, ...] | None:
    if value is None:
        return default
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, (list, tuple)):
        values = tuple(value)
    else:
        raise ValueError("audit worker list fields must be strings or lists of strings")
    if not all(isinstance(item, str) for item in values):
        raise ValueError("audit worker list fields must be strings or lists of strings")
    return tuple(item for item in values if item)


def _optional_worker_job_kind_tuple(
    value: Any,
    *,
    default: tuple[WorkerJobKind, ...] | None = None,
) -> tuple[WorkerJobKind, ...] | None:
    values = _optional_string_tuple(value, default=None)
    if values is None:
        return default
    kinds: list[WorkerJobKind] = []
    for item in values:
        try:
            kinds.append(WorkerJobKind(item))
        except ValueError as exc:
            raise ValueError(f"unsupported required_successful_job_kinds value: {item}") from exc
    return tuple(kinds)


def _default_next_actions(blocker_reasons: tuple[str, ...]) -> tuple[str, ...]:
    if blocker_reasons:
        return (
            "review_audit_blocker_report",
            "fix_or_requeue_failed_stale_incomplete_jobs",
            "rerun_audit_check_after_blockers_are_resolved",
        )
    return ("independent_completion_audit_required_before_autonomous_ready",)


def _unique(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _csv(values) -> str:
    return ",".join(str(value) for value in values)


def _write_report(path: Path, report: AuditBlockerReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
