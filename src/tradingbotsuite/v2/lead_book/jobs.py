# V2-AUDIT-ID: V2-AUD-LEAD-004, V2-AUD-LEAD-006
# V2-CONTRACTS: docs/contracts/lead_book_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_lead_book_worker, non_promotable_leads, no_live_imports
# V2-OWNER: v2_lead_book
"""Durable worker job handlers for v2 Lead Book operations."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.lead_book.schemas import LeadBookScanConfig
from tradingbotsuite.v2.lead_book.service import (
    LeadBookStore,
    create_lead_from_source,
    scan_lead_book_queue,
)
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobRecord, WorkerRunResult

_SECRET_NAME_RE = re.compile(
    r"(^\.env$|secret|credential|private|token|password|wallet|api[_-]?key)",
    re.IGNORECASE,
)
_BOUNDARY_OVERRIDE_KEYS = {
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


def run_lead_book_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    if job.kind == WorkerJobKind.LEAD_BOOK_SCAN:
        return _run_lead_book_scan_job(job=job, store=store, worker_id=worker_id)
    if job.kind != WorkerJobKind.LEAD_BOOK_UPSERT:
        raise ValueError(f"unsupported Lead Book job kind: {job.kind.value}")
    return _run_lead_book_upsert_job(job=job, store=store, worker_id=worker_id)


def _run_lead_book_scan_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = dict(job.input_spec)
    _reject_boundary_overrides(spec)
    lead_book_path = _required_path(
        spec,
        "lead_book_path",
        allowed_suffixes=(".parquet",),
        require_file=False,
    )
    output_path = _required_path(
        spec,
        "output_path",
        allowed_suffixes=(".json",),
        require_file=False,
    )
    scan_result = scan_lead_book_queue(
        LeadBookScanConfig.model_validate(
            {
                "lead_book_path": str(lead_book_path),
                "output_path": str(output_path),
                "states": _required_states(spec),
                "max_rows": spec.get("max_rows", 500),
            }
        )
    )
    scan_manifest_path = Path(scan_result.scan_manifest_path).resolve(strict=False)
    blocker_refs = tuple(
        f"blocker_reason={reason}" for reason in scan_result.blocker_reasons
    )
    blocker_count = len(scan_result.blocker_reasons)
    output_refs = (
        "job_kind=lead_book_scan",
        f"lead_book_scan_manifest_path={scan_manifest_path}",
        f"lead_book_scan_manifest_sha256={file_sha256(scan_manifest_path)}",
        f"lead_book_scan_id={scan_result.scan_id}",
        f"lead_book_scan_evidence_mode={scan_result.evidence_mode}",
        f"states={','.join(state.value for state in scan_result.states)}",
        f"total_lead_count={scan_result.total_lead_count}",
        f"matched_count={scan_result.matched_count}",
        f"returned_count={scan_result.returned_count}",
        f"blocker_count={blocker_count}",
        "accepted_research_ready=false",
        "promotion_ready=false",
        f"lead_book_path={lead_book_path}",
        *blocker_refs,
    )
    domain_refs = (
        f"lead_book_scan_manifest_path={scan_manifest_path}",
        f"lead_book_scan_manifest_sha256={file_sha256(scan_manifest_path)}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=domain_refs,
        reason="lead_book_scan_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_lead_book_upsert_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = dict(job.input_spec)
    _reject_boundary_overrides(spec)
    lead_book_path = _required_path(
        spec,
        "lead_book_path",
        allowed_suffixes=(".parquet",),
        require_file=False,
    )
    source_artifact_path = _required_path(
        spec,
        "source_artifact_path",
        allowed_suffixes=(".json", ".parquet"),
        require_file=True,
    )
    export_csv_path = _optional_path(
        spec.get("export_csv_path"),
        field_name="export_csv_path",
        allowed_suffixes=(".csv",),
    )
    lead = create_lead_from_source(
        source_artifact_path=source_artifact_path,
        source_type=_required_string(spec, "source_type"),
        strategy_family=_required_string(spec, "strategy_family"),
        economic_thesis=_required_string(spec, "economic_thesis"),
        created_by_id=_required_string(spec, "created_by_id"),
        venue_scope=str(spec.get("venue_scope", "hyperliquid")),
        universe_scope=str(spec.get("universe_scope", "as_of")),
        instrument_scope=_string_tuple(spec.get("instrument_scope", ("unknown",))),
        data_window_start=_optional_datetime(spec.get("data_window_start"), "data_window_start"),
        data_window_end=_optional_datetime(spec.get("data_window_end"), "data_window_end"),
        data_source=str(spec.get("data_source", "source_artifact")),
        roi_observed=_required_float(spec, "roi_observed"),
        roi_projected=_required_float(spec, "roi_projected"),
        roi_projection_assumptions=_required_string(spec, "roi_projection_assumptions"),
        why_interesting=_required_string(spec, "why_interesting"),
        trade_count_summary=_required_mapping(spec, "trade_count_summary"),
        monthly_stability_summary=_required_mapping(spec, "monthly_stability_summary"),
        pnl_concentration_summary=_required_mapping(spec, "pnl_concentration_summary"),
        lead_id=_optional_string(spec.get("lead_id"), "lead_id"),
        created_by_type=str(spec.get("created_by_type", "agent")),
        cost_assumptions=str(spec.get("cost_assumptions", "manifested_cost_model")),
        funding_assumptions=str(spec.get("funding_assumptions", "manifested_funding_model")),
        slippage_assumptions=str(spec.get("slippage_assumptions", "manifested_slippage_model")),
        fill_assumptions=str(spec.get("fill_assumptions", "research_fill_assumptions_only")),
        roi_projection_confidence=str(spec.get("roi_projection_confidence", "unknown")),
        known_blockers=_string_tuple(spec.get("known_blockers", ()), allow_empty=True),
        missing_evidence=_string_tuple(spec.get("missing_evidence", ()), allow_empty=True),
        required_next_validation=_string_tuple(spec.get("required_next_validation", ("deep_validation",))),
        notes=str(spec.get("notes", "")),
    )
    lead_book = LeadBookStore(lead_book_path)
    lead_book.upsert(lead)
    export_refs: list[str] = []
    if export_csv_path is not None:
        lead_book.export_csv(export_csv_path)
        export_refs.extend(
            [
                f"export_csv_path={export_csv_path}",
                f"export_csv_sha256={file_sha256(export_csv_path)}",
            ]
        )
    output_refs = (
        "job_kind=lead_book_upsert",
        f"lead_id={lead.lead_id}",
        f"lead_state={lead.state.value}",
        f"human_inspection_status={lead.human_inspection_status.value}",
        f"agent_approval_status={lead.agent_approval_status.value}",
        "promotion_ready=false",
        "candidate_evidence=false",
        f"source_type={lead.source_type}",
        f"source_artifact_sha256={lead.source_artifact_sha256}",
        f"lead_book_path={lead_book_path}",
        f"lead_book_sha256={file_sha256(lead_book_path)}",
        f"known_blockers={','.join(lead.known_blockers)}",
        f"missing_evidence={','.join(lead.missing_evidence)}",
        *export_refs,
    )
    domain_refs = (
        f"source_artifact_path={source_artifact_path}",
        f"source_artifact_sha256={lead.source_artifact_sha256}",
        f"lead_book_sha256={file_sha256(lead_book_path)}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=domain_refs,
        reason="lead_book_upsert_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _reject_boundary_overrides(spec: dict[str, Any]) -> None:
    forbidden = sorted(_BOUNDARY_OVERRIDE_KEYS.intersection(spec))
    if forbidden:
        raise ValueError(
            f"Lead Book worker job spec must not override boundary fields: {','.join(forbidden)}"
        )


def _required_states(spec: dict[str, Any]) -> tuple[str, ...]:
    if "states" not in spec:
        raise ValueError("Lead Book scan worker job spec requires states")
    return _string_tuple(spec["states"])


def _required_path(
    spec: dict[str, Any],
    key: str,
    *,
    allowed_suffixes: tuple[str, ...],
    require_file: bool,
) -> Path:
    value = spec.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Lead Book worker job spec requires {key}")
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
        if not resolved.exists() and not _part_backed_parquet_exists(resolved):
            raise ValueError(f"{field_name} missing: {path}")
        if resolved.exists() and not resolved.is_file():
            raise ValueError(f"{field_name} must be a file: {path}")
    return resolved


def _part_backed_parquet_exists(path: Path) -> bool:
    return path.suffix.lower() == ".parquet" and path.with_suffix(".index.json").exists()


def _required_string(spec: dict[str, Any], key: str) -> str:
    value = spec.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Lead Book worker job spec requires {key}")
    return value


def _optional_string(value: Any, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string when provided")
    return value


def _required_float(spec: dict[str, Any], key: str) -> float:
    value = spec.get(key)
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Lead Book worker job spec requires numeric {key}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Lead Book worker job spec requires numeric {key}") from exc


def _required_mapping(spec: dict[str, Any], key: str) -> dict[str, Any]:
    value = spec.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Lead Book worker job spec requires object {key}")
    return dict(value)


def _string_tuple(value: Any, *, allow_empty: bool = False) -> tuple[str, ...]:
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, (list, tuple)):
        values = tuple(value)
    else:
        raise ValueError("Lead Book worker list fields must be strings or lists of strings")
    if not all(isinstance(item, str) for item in values):
        raise ValueError("Lead Book worker list fields must be strings or lists of strings")
    parsed = tuple(item for item in values if item)
    if not parsed and not allow_empty:
        raise ValueError("Lead Book worker list fields must not be empty")
    return parsed


def _optional_datetime(value: Any, key: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be an ISO-8601 string when provided")
    normalized = value.replace("Z", "+00:00")
    try:
        return ensure_utc(datetime.fromisoformat(normalized))
    except ValueError as exc:
        raise ValueError(f"{key} must be an ISO-8601 UTC timestamp") from exc
