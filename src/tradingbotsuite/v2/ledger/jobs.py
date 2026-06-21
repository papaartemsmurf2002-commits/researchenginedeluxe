# V2-AUDIT-ID: V2-AUD-LEDGER-004
# V2-CONTRACTS: docs/contracts/ledger_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_ledger_append, generated_exports_only, no_live_imports
# V2-OWNER: v2_ledger
"""Durable worker job handlers for v2 ledger append/export operations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.ledger.service import append_run_to_ledger, export_ledger
from tradingbotsuite.v2.ledger.schemas import LedgerAppendRequest
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobRecord, WorkerRunResult

_SECRET_NAME_RE = re.compile(
    r"(^\.env$|secret|credential|private|token|password|wallet|api[_-]?key)",
    re.IGNORECASE,
)


def run_ledger_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    if job.kind != WorkerJobKind.LEDGER_APPEND_EXPORT:
        raise ValueError(f"unsupported ledger job kind: {job.kind.value}")
    return _run_ledger_append_export_job(job=job, store=store, worker_id=worker_id)


def _run_ledger_append_export_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    run_manifest_path = _required_path(
        spec,
        "run_manifest_path",
        allowed_suffixes=(".json",),
        require_file=True,
    )
    if run_manifest_path.name != "run_manifest.json":
        raise ValueError("ledger worker run_manifest_path must point to run_manifest.json")
    ledger_path = _required_path(
        spec,
        "ledger_path",
        allowed_suffixes=(".parquet",),
        require_file=False,
    )
    export_csv_path = _optional_path(
        spec.get("export_csv_path"),
        field_name="export_csv_path",
        allowed_suffixes=(".csv",),
    )
    export_xlsx_path = _optional_path(
        spec.get("export_xlsx_path"),
        field_name="export_xlsx_path",
        allowed_suffixes=(".xlsx",),
    )
    row = append_run_to_ledger(
        LedgerAppendRequest(
            run_manifest_path=str(run_manifest_path),
            ledger_path=str(ledger_path),
            evidence_mode=str(spec.get("evidence_mode", "sandbox_diagnostic")),
            notes=str(spec.get("notes", "")),
        )
    )
    export_refs: list[str] = []
    if export_csv_path is not None:
        export_ledger(
            ledger_path=ledger_path,
            output_path=export_csv_path,
            export_format="csv",
        )
        export_refs.extend(
            [
                f"export_csv_path={export_csv_path}",
                f"export_csv_sha256={file_sha256(export_csv_path)}",
            ]
        )
    if export_xlsx_path is not None:
        export_ledger(
            ledger_path=ledger_path,
            output_path=export_xlsx_path,
            export_format="xlsx",
        )
        export_refs.extend(
            [
                f"export_xlsx_path={export_xlsx_path}",
                f"export_xlsx_sha256={file_sha256(export_xlsx_path)}",
            ]
        )
    output_refs = (
        "job_kind=ledger_append_export",
        f"run_id={row.run_id}",
        f"row_status={row.row_status}",
        f"validation_status={row.validation_status}",
        f"evidence_mode={row.evidence_mode}",
        f"ledger_path={ledger_path}",
        f"ledger_sha256={file_sha256(ledger_path)}",
        f"ledger_index={row.ledger_index}",
        f"row_hash={row.row_hash}",
        f"blocker_reasons={','.join(row.blocker_reasons)}",
        *export_refs,
    )
    archive_refs = (
        f"archive_snapshot_id={row.archive_snapshot_id}",
        f"universe_snapshot_id={row.universe_snapshot_id}",
        f"artifact_sha256={row.artifact_sha256}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="ledger_append_export_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _required_path(
    spec: dict[str, Any],
    key: str,
    *,
    allowed_suffixes: tuple[str, ...],
    require_file: bool,
) -> Path:
    value = spec.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"ledger worker job spec requires {key}")
    return _validate_path(
        Path(value),
        field_name=key,
        allowed_suffixes=allowed_suffixes,
        require_file=require_file,
    )


def _optional_path(
    value: Any,
    *,
    field_name: str,
    allowed_suffixes: tuple[str, ...],
) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string when provided")
    return _validate_path(
        Path(value),
        field_name=field_name,
        allowed_suffixes=allowed_suffixes,
        require_file=False,
    )


def _validate_path(
    path: Path,
    *,
    field_name: str,
    allowed_suffixes: tuple[str, ...],
    require_file: bool,
) -> Path:
    if any(_SECRET_NAME_RE.search(part) for part in path.parts):
        raise ValueError(f"{field_name} name is reserved for secrets or local state")
    suffix = path.suffix.lower()
    if suffix not in allowed_suffixes:
        raise ValueError(
            f"{field_name} must use one of these suffixes: {','.join(allowed_suffixes)}"
        )
    resolved = path.resolve(strict=False)
    if require_file:
        if not resolved.exists():
            raise ValueError(f"{field_name} missing: {path}")
        if not resolved.is_file():
            raise ValueError(f"{field_name} must be a file: {path}")
    return resolved
