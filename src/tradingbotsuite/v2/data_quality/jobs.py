# V2-AUDIT-ID: V2-AUD-QUAL-004
# V2-CONTRACTS: docs/contracts/data_quality_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_coverage_audit, no_live_imports
# V2-OWNER: v2_data_quality
"""Durable data-quality worker job handlers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, FileManifestRow
from tradingbotsuite.v2.data_quality.checks import build_quality_checks
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import DEFAULT_COVERAGE_MIN, EvidenceMode
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import (
    WorkerJobKind,
    WorkerJobRecord,
    WorkerRunResult,
)


def run_data_quality_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    if job.kind == WorkerJobKind.COVERAGE_AUDIT:
        return _run_coverage_audit_job(job=job, store=store, worker_id=worker_id)
    raise ValueError(f"unsupported data-quality job kind: {job.kind.value}")


def _run_coverage_audit_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    archive_root = _required_str(spec, "archive_root")
    file_id = str(spec.get("file_id") or spec.get("silver_file_id") or "")
    if not file_id:
        raise ValueError("coverage audit job spec requires file_id or silver_file_id")
    layout = ArchiveLayout(archive_root)
    source_file = _find_manifest_file(ArchiveManifestStore(layout), file_id)
    _require_silver_bars_file(source_file)
    rows = pq.ParquetFile(layout.resolve(source_file.path)).read().to_pylist()
    venue = str(spec.get("venue") or source_file.venue)
    instrument_id = str(spec.get("instrument_id") or source_file.instrument_id or "")
    timeframe = str(spec.get("timeframe") or source_file.timeframe or "")
    if not instrument_id:
        raise ValueError("coverage audit source file must declare instrument_id or job spec must provide it")
    if not timeframe:
        raise ValueError("coverage audit source file must declare timeframe or job spec must provide it")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    family = str(spec.get("family", "bars"))
    mode = EvidenceMode(str(spec.get("evidence_mode", EvidenceMode.SANDBOX_DIAGNOSTIC.value)))
    coverage_min = float(spec.get("coverage_min", DEFAULT_COVERAGE_MIN))
    field_names = _field_names(spec)
    report = coverage_report_for_bars(
        rows,
        venue=venue,
        instrument_id=instrument_id,
        family=family,
        timeframe=timeframe,
        start_ts=start_ts,
        end_ts=end_ts,
        coverage_min=coverage_min,
        evidence_mode=mode,
        **field_names,
    )
    checks = build_quality_checks(
        rows,
        venue=venue,
        instrument_id=instrument_id,
        family=family,
        timeframe=timeframe,
        start_ts=start_ts,
        end_ts=end_ts,
        evidence_mode=mode,
        **field_names,
    )
    manifest_store = CoverageManifestStore(layout)
    manifest_store.append_coverage_report(report)
    if bool(spec.get("write_quality_checks", True)):
        manifest_store.append_quality_checks(checks)
    quality_check_ids = tuple(check.check_id for check in checks)
    archive_refs = (
        f"coverage_report_id={report.coverage_report_id}",
        f"quality_check_ids={','.join(quality_check_ids)}",
        f"source_file_id={source_file.file_id}",
    )
    output_refs = (
        "job_kind=coverage_audit",
        f"source_file_id={source_file.file_id}",
        f"source_row_count={len(rows)}",
        f"coverage_report_id={report.coverage_report_id}",
        f"quality_check_ids={','.join(quality_check_ids)}",
        f"coverage_ratio={report.coverage_ratio:.12f}",
        f"quality_status={report.quality_status.value}",
        f"evidence_eligible={str(report.evidence_eligible).lower()}",
        f"blocker_reasons={','.join(report.blocker_reasons)}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="coverage_audit_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _find_manifest_file(store: ArchiveManifestStore, file_id: str) -> FileManifestRow:
    matches = [row for row in store.load_file_manifest() if row.file_id == file_id]
    if len(matches) != 1:
        raise KeyError(f"archive file_manifest row not found: {file_id}")
    return matches[0]


def _require_silver_bars_file(row: FileManifestRow) -> None:
    if row.layer != ArchiveLayer.SILVER or row.datatype != "bars":
        raise ValueError("coverage audit requires a silver bars archive file")


def _field_names(spec: dict[str, Any]) -> dict[str, str]:
    return {
        "ts_field": str(spec.get("timestamp_field", "ts")),
        "volume_field": str(spec.get("volume_field", "volume")),
        "price_field": str(spec.get("price_field", "close")),
        "spread_field": str(spec.get("spread_field", "spread")),
        "funding_field": str(spec.get("funding_field", "funding")),
    }


def _required_str(spec: dict[str, Any], key: str) -> str:
    value = spec.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"coverage audit job spec requires {key}")
    return value


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("coverage audit timestamps must include timezone")
    return parsed


def normalize_payload_file(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return str(Path(path))
