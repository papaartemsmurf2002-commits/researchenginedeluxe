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
from tradingbotsuite.v2.archive.raw_writer import read_jsonl_zstd
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, ArchiveSnapshotRecord, FileManifestRow
from tradingbotsuite.v2.data_quality.checks import build_quality_checks
from tradingbotsuite.v2.data_quality.coverage import (
    coverage_report_for_bars,
    coverage_report_for_timestamped_rows,
)
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import DEFAULT_COVERAGE_MIN, CoverageReport, EvidenceMode
from tradingbotsuite.v2.universe.hyperliquid import load_universe_rows
from tradingbotsuite.v2.universe.models import UniverseSnapshotRow
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import (
    WorkerJobKind,
    WorkerJobRecord,
    WorkerRunResult,
)

RAW_MICROSTRUCTURE_COVERAGE_FAMILIES = frozenset({"trades", "bbo", "l2"})
SILVER_TIMESTAMPED_COVERAGE_FAMILIES = frozenset({"asset_contexts"})
TIMESTAMPED_COVERAGE_FAMILIES = RAW_MICROSTRUCTURE_COVERAGE_FAMILIES | SILVER_TIMESTAMPED_COVERAGE_FAMILIES
RAW_MICROSTRUCTURE_NON_EVIDENCE_REASON = "raw_microstructure_not_accepted_coverage_evidence"


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
    if "archive_snapshot_id" in spec or "universe_snapshot_id" in spec:
        if spec.get("file_id") or spec.get("silver_file_id"):
            raise ValueError(
                "coverage audit job spec cannot combine file_id/silver_file_id "
                "with archive_snapshot_id/universe_snapshot_id"
            )
        return _run_universe_snapshot_coverage_audit_job(
            job=job,
            store=store,
            worker_id=worker_id,
        )
    archive_root = _required_str(spec, "archive_root")
    file_id = str(spec.get("file_id") or spec.get("silver_file_id") or "")
    if not file_id:
        raise ValueError("coverage audit job spec requires file_id or silver_file_id")
    layout = ArchiveLayout(archive_root)
    source_file = _find_manifest_file(ArchiveManifestStore(layout), file_id)
    if _is_timestamped_coverage_file(source_file):
        return _run_timestamped_file_coverage_audit_job(
            job=job,
            store=store,
            worker_id=worker_id,
            layout=layout,
            source_file=source_file,
        )
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


def _run_timestamped_file_coverage_audit_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
    layout: ArchiveLayout,
    source_file: FileManifestRow,
) -> WorkerRunResult:
    spec = job.input_spec
    rows = _read_timestamped_coverage_rows(layout, source_file)
    venue = str(spec.get("venue") or source_file.venue)
    instrument_id = str(spec.get("instrument_id") or source_file.instrument_id or "")
    timeframe = str(spec.get("timeframe") or spec.get("bucket_timeframe") or "")
    if not instrument_id:
        raise ValueError("timestamped coverage audit source file must declare instrument_id or job spec must provide it")
    if not timeframe:
        raise ValueError("timestamped coverage audit requires timeframe or bucket_timeframe")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    family = str(spec.get("family") or source_file.datatype)
    mode = EvidenceMode(str(spec.get("evidence_mode", EvidenceMode.SANDBOX_DIAGNOSTIC.value)))
    coverage_min = float(spec.get("coverage_min", DEFAULT_COVERAGE_MIN))
    report = coverage_report_for_timestamped_rows(
        rows,
        venue=venue,
        instrument_id=instrument_id,
        family=family,
        timeframe=timeframe,
        start_ts=start_ts,
        end_ts=end_ts,
        ts_field=str(spec.get("timestamp_field", "ts")),
        sequence_field=_optional_sequence_field(spec),
        coverage_min=coverage_min,
        evidence_mode=mode,
        force_non_evidence_reason=_force_non_evidence_reason(source_file),
        source_caveats=_timestamped_source_caveats(source_file),
    )
    manifest_store = CoverageManifestStore(layout)
    manifest_store.append_coverage_report(report)
    archive_refs = (
        f"coverage_report_id={report.coverage_report_id}",
        f"source_file_id={source_file.file_id}",
    )
    output_refs = (
        "job_kind=coverage_audit",
        "coverage_scope=timestamped_file",
        "coverage_method=nonempty_time_buckets",
        f"source_file_id={source_file.file_id}",
        f"source_layer={source_file.layer.value}",
        f"source_datatype={source_file.datatype}",
        f"source_row_count={len(rows)}",
        f"coverage_report_id={report.coverage_report_id}",
        "quality_check_ids=",
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
        reason="coverage_audit_timestamped_file_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_universe_snapshot_coverage_audit_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    archive_root = _required_str(spec, "archive_root")
    archive_snapshot_id = _required_str(spec, "archive_snapshot_id")
    universe_snapshot_id = _required_str(spec, "universe_snapshot_id")
    timeframe = _required_str(spec, "timeframe")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    family = str(spec.get("family", "bars"))
    mode = EvidenceMode(str(spec.get("evidence_mode", EvidenceMode.SANDBOX_DIAGNOSTIC.value)))
    coverage_min = float(spec.get("coverage_min", DEFAULT_COVERAGE_MIN))
    eligible_only = bool(spec.get("eligible_only", True))
    field_names = _field_names(spec)

    layout = ArchiveLayout(archive_root)
    manifest_store = ArchiveManifestStore(layout)
    archive_snapshot = _find_archive_snapshot(manifest_store, archive_snapshot_id)
    if family == "bars":
        if archive_snapshot.layer != ArchiveLayer.SILVER:
            raise ValueError("coverage audit archive_snapshot_id must reference a silver snapshot")
        coverage_method = "fixed_timeframe_bars"
        missing_file_reason = "missing_silver_bars_file"
        source_datatype = "bars"
        files_by_instrument = _silver_bar_files_by_instrument(
            manifest_store=manifest_store,
            archive_snapshot=archive_snapshot,
            venue=str(spec.get("venue", "")),
            timeframe=timeframe,
        )
    elif family in TIMESTAMPED_COVERAGE_FAMILIES:
        _require_timestamped_snapshot_layer(archive_snapshot, family=family)
        coverage_method = "nonempty_time_buckets"
        missing_file_reason = _missing_timestamped_file_reason(archive_snapshot.layer, family)
        source_datatype = family
        files_by_instrument = _timestamped_files_by_instrument(
            manifest_store=manifest_store,
            archive_snapshot=archive_snapshot,
            venue=str(spec.get("venue", "")),
            datatype=family,
        )
    else:
        raise ValueError("coverage audit archive_snapshot_id supports family=bars,trades,bbo,l2,asset_contexts")
    universe_rows = _find_universe_snapshot_rows(
        archive_root=archive_root,
        universe_snapshot_id=universe_snapshot_id,
        eligible_only=eligible_only,
    )
    if not universe_rows:
        raise ValueError("coverage audit universe snapshot contains no instruments in scope")
    venue = str(spec.get("venue") or universe_rows[0].venue)
    if not files_by_instrument:
        files_by_instrument = _coverage_files_by_instrument(
            manifest_store=manifest_store,
            archive_snapshot=archive_snapshot,
            venue=venue,
            datatype=source_datatype,
            timeframe=timeframe if family == "bars" else None,
        )
    coverage_store = CoverageManifestStore(layout)
    reports: list[CoverageReport] = []
    quality_check_ids: list[str] = []
    missing_file_instruments: list[str] = []
    total_source_rows = 0

    for universe_row in universe_rows:
        source_files = files_by_instrument.get(universe_row.instrument_id, [])
        if not source_files:
            missing_file_instruments.append(universe_row.instrument_id)
        rows = (
            _read_silver_bar_rows(layout, source_files)
            if family == "bars"
            else _read_timestamped_files(layout, source_files)
        )
        total_source_rows += len(rows)
        if family == "bars":
            report = coverage_report_for_bars(
                rows,
                venue=venue,
                instrument_id=universe_row.instrument_id,
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
                instrument_id=universe_row.instrument_id,
                family=family,
                timeframe=timeframe,
                start_ts=start_ts,
                end_ts=end_ts,
                evidence_mode=mode,
                **field_names,
            )
        else:
            report = coverage_report_for_timestamped_rows(
                rows,
                venue=venue,
                instrument_id=universe_row.instrument_id,
                family=family,
                timeframe=timeframe,
                start_ts=start_ts,
                end_ts=end_ts,
                ts_field=str(spec.get("timestamp_field", "ts")),
                sequence_field=_optional_sequence_field(spec),
                coverage_min=coverage_min,
                evidence_mode=mode,
                force_non_evidence_reason=(
                    RAW_MICROSTRUCTURE_NON_EVIDENCE_REASON
                    if family in RAW_MICROSTRUCTURE_COVERAGE_FAMILIES
                    else None
                ),
                source_caveats=_timestamped_family_caveats(family),
            )
            checks = []
        coverage_store.append_coverage_report(report)
        if bool(spec.get("write_quality_checks", True)):
            coverage_store.append_quality_checks(checks)
            quality_check_ids.extend(check.check_id for check in checks)
        reports.append(report)

    report_ids = tuple(report.coverage_report_id for report in reports)
    blocked_reports = [report for report in reports if not report.evidence_eligible]
    blocker_reasons = sorted(
        {
            reason
            for report in blocked_reports
            for reason in report.blocker_reasons
        }
        | ({missing_file_reason} if missing_file_instruments else set())
    )
    min_coverage = min(report.coverage_ratio for report in reports)
    archive_refs = (
        f"archive_snapshot_id={archive_snapshot.archive_snapshot_id}",
        f"universe_snapshot_id={universe_snapshot_id}",
        f"coverage_report_ids={','.join(report_ids)}",
        f"quality_check_ids={','.join(quality_check_ids)}",
    )
    output_refs = (
        "job_kind=coverage_audit",
        "coverage_scope=universe_snapshot",
        f"archive_snapshot_id={archive_snapshot.archive_snapshot_id}",
        f"universe_snapshot_id={universe_snapshot_id}",
        f"universe_eligible_only={str(eligible_only).lower()}",
        f"venue={venue}",
        f"timeframe={timeframe}",
        f"coverage_method={coverage_method}",
        f"source_layer={archive_snapshot.layer.value}",
        f"source_datatype={source_datatype}",
        f"instrument_count={len(universe_rows)}",
        f"audited_instrument_count={len(reports)}",
        f"total_source_row_count={total_source_rows}",
        f"missing_file_instrument_count={len(missing_file_instruments)}",
        f"missing_file_instruments={','.join(missing_file_instruments)}",
        f"min_coverage_ratio={min_coverage:.12f}",
        f"evidence_eligible_count={len(reports) - len(blocked_reports)}",
        f"blocked_instrument_count={len(blocked_reports)}",
        f"blocker_reasons={','.join(blocker_reasons)}",
        f"coverage_report_ids={','.join(report_ids)}",
        f"quality_check_ids={','.join(quality_check_ids)}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="coverage_audit_universe_snapshot_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _find_archive_snapshot(
    store: ArchiveManifestStore,
    archive_snapshot_id: str,
) -> ArchiveSnapshotRecord:
    matches = [
        row
        for row in store.load_archive_snapshots()
        if row.archive_snapshot_id == archive_snapshot_id
    ]
    if len(matches) != 1:
        raise KeyError(f"archive snapshot not found: {archive_snapshot_id}")
    return matches[0]


def _find_universe_snapshot_rows(
    *,
    archive_root: str,
    universe_snapshot_id: str,
    eligible_only: bool,
) -> list[UniverseSnapshotRow]:
    rows = [
        row
        for row in load_universe_rows(archive_root)
        if row.snapshot_id == universe_snapshot_id
    ]
    if eligible_only:
        rows = [row for row in rows if row.eligible]
    return sorted(rows, key=lambda row: row.instrument_id)


def _silver_bar_files_by_instrument(
    *,
    manifest_store: ArchiveManifestStore,
    archive_snapshot: ArchiveSnapshotRecord,
    venue: str,
    timeframe: str,
) -> dict[str, list[FileManifestRow]]:
    included_ids = set(archive_snapshot.included_file_ids)
    files_by_instrument: dict[str, list[FileManifestRow]] = {}
    for row in manifest_store.load_file_manifest():
        if row.file_id not in included_ids:
            continue
        if row.layer != ArchiveLayer.SILVER or row.datatype != "bars":
            continue
        if row.venue != venue or row.timeframe != timeframe or not row.instrument_id:
            continue
        files_by_instrument.setdefault(row.instrument_id, []).append(row)
    for rows in files_by_instrument.values():
        rows.sort(key=lambda row: (row.date or "", row.path, row.file_id))
    return files_by_instrument


def _timestamped_files_by_instrument(
    *,
    manifest_store: ArchiveManifestStore,
    archive_snapshot: ArchiveSnapshotRecord,
    venue: str,
    datatype: str,
) -> dict[str, list[FileManifestRow]]:
    return _coverage_files_by_instrument(
        manifest_store=manifest_store,
        archive_snapshot=archive_snapshot,
        venue=venue,
        datatype=datatype,
        timeframe=None,
    )


def _coverage_files_by_instrument(
    *,
    manifest_store: ArchiveManifestStore,
    archive_snapshot: ArchiveSnapshotRecord,
    venue: str,
    datatype: str,
    timeframe: str | None,
) -> dict[str, list[FileManifestRow]]:
    included_ids = set(archive_snapshot.included_file_ids)
    files_by_instrument: dict[str, list[FileManifestRow]] = {}
    for row in manifest_store.load_file_manifest():
        if row.file_id not in included_ids:
            continue
        if row.layer != archive_snapshot.layer or row.datatype != datatype:
            continue
        if row.venue != venue or not row.instrument_id:
            continue
        if timeframe is not None and row.timeframe != timeframe:
            continue
        files_by_instrument.setdefault(row.instrument_id, []).append(row)
    for rows in files_by_instrument.values():
        rows.sort(key=lambda row: (row.date or "", row.hour or -1, row.path, row.file_id))
    return files_by_instrument


def _read_silver_bar_rows(layout: ArchiveLayout, files: list[FileManifestRow]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for file_row in files:
        rows.extend(pq.ParquetFile(layout.resolve(file_row.path)).read().to_pylist())
    return rows


def _read_timestamped_files(layout: ArchiveLayout, files: list[FileManifestRow]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for file_row in files:
        rows.extend(_read_timestamped_coverage_rows(layout, file_row))
    return rows


def _read_timestamped_coverage_rows(layout: ArchiveLayout, file_row: FileManifestRow) -> list[dict[str, Any]]:
    if file_row.layer == ArchiveLayer.RAW:
        if file_row.uncompressed_size_bytes is None:
            raise ValueError("raw timestamped coverage file must include uncompressed_size_bytes")
        return read_jsonl_zstd(
            layout.resolve(file_row.path),
            uncompressed_size=file_row.uncompressed_size_bytes,
        )
    return pq.ParquetFile(layout.resolve(file_row.path)).read().to_pylist()


def _find_manifest_file(store: ArchiveManifestStore, file_id: str) -> FileManifestRow:
    matches = [row for row in store.load_file_manifest() if row.file_id == file_id]
    if len(matches) != 1:
        raise KeyError(f"archive file_manifest row not found: {file_id}")
    return matches[0]


def _require_silver_bars_file(row: FileManifestRow) -> None:
    if row.layer != ArchiveLayer.SILVER or row.datatype != "bars":
        raise ValueError(
            "coverage audit requires a silver bars archive file, raw trades/bbo/l2 file, "
            "or silver asset_contexts file"
        )


def _is_timestamped_coverage_file(row: FileManifestRow) -> bool:
    return (
        row.layer == ArchiveLayer.RAW and row.datatype in RAW_MICROSTRUCTURE_COVERAGE_FAMILIES
    ) or (
        row.layer == ArchiveLayer.SILVER and row.datatype in SILVER_TIMESTAMPED_COVERAGE_FAMILIES
    )


def _require_timestamped_snapshot_layer(snapshot: ArchiveSnapshotRecord, *, family: str) -> None:
    if family in RAW_MICROSTRUCTURE_COVERAGE_FAMILIES:
        if snapshot.layer != ArchiveLayer.RAW:
            raise ValueError("raw microstructure coverage audit requires a raw archive snapshot")
        return
    if family in SILVER_TIMESTAMPED_COVERAGE_FAMILIES:
        if snapshot.layer != ArchiveLayer.SILVER:
            raise ValueError("asset_contexts coverage audit requires a silver archive snapshot")
        return
    raise ValueError("timestamped coverage audit supports trades,bbo,l2,asset_contexts")


def _missing_timestamped_file_reason(layer: ArchiveLayer, family: str) -> str:
    return f"missing_{layer.value}_{family}_file"


def _force_non_evidence_reason(file_row: FileManifestRow) -> str | None:
    if file_row.layer == ArchiveLayer.RAW and file_row.datatype in RAW_MICROSTRUCTURE_COVERAGE_FAMILIES:
        return RAW_MICROSTRUCTURE_NON_EVIDENCE_REASON
    return None


def _timestamped_source_caveats(file_row: FileManifestRow) -> tuple[str, ...]:
    if file_row.layer == ArchiveLayer.RAW and file_row.datatype in RAW_MICROSTRUCTURE_COVERAGE_FAMILIES:
        return _timestamped_family_caveats(file_row.datatype)
    return _timestamped_family_caveats(file_row.datatype)


def _timestamped_family_caveats(family: str) -> tuple[str, ...]:
    if family in RAW_MICROSTRUCTURE_COVERAGE_FAMILIES:
        return (
            "raw_microstructure_bucket_coverage_not_event_completeness",
            "raw_microstructure_not_queue_or_fill_realism",
        )
    return ("timestamped_context_bucket_coverage",)


def _optional_sequence_field(spec: dict[str, Any]) -> str | None:
    if "sequence_field" not in spec:
        return "sequence"
    value = spec.get("sequence_field")
    if value is None:
        return None
    text = str(value)
    return text or None


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
