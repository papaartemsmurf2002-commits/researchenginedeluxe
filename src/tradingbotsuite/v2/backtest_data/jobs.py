# V2-AUDIT-ID: V2-AUD-BTDATA-005
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_backtest_data_load, archive_snapshot_reads, no_live_imports
# V2-OWNER: v2_backtest_data
"""Durable worker job handler for explicit backtest-data loads."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.backtest_data.schemas import BacktestDataRequest
from tradingbotsuite.v2.backtest_data.service import BacktestDataService
from tradingbotsuite.v2.config.time import utc_isoformat
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import WorkerJobKind, WorkerJobRecord, WorkerRunResult


def run_backtest_data_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    if job.kind != WorkerJobKind.BACKTEST_DATA_LOAD:
        raise ValueError(f"unsupported backtest-data job kind: {job.kind.value}")
    spec = dict(job.input_spec)
    if spec.get("write_manifest", True) is False:
        raise ValueError("backtest_data_load worker requires write_manifest=true")
    request = _data_request(spec)
    asof_date = _optional_date(spec.get("asof_date"))
    data_slice = BacktestDataService(request.archive_root).load_panel(
        request,
        asof_date=asof_date,
        write_manifest=True,
    )
    manifest_path = Path(request.archive_root) / "manifests" / "backtest_data_requests.parquet"
    data_manifest = data_slice.data_manifest
    data_manifest_hash = canonical_json_hash(data_manifest.model_dump(mode="json"))
    output_refs = [
        "job_kind=backtest_data_load",
        f"job_id={job.job_id}",
        f"archive_root={Path(request.archive_root).resolve(strict=False)}",
        f"backtest_data_manifest_path={manifest_path}",
        f"backtest_data_manifest_sha256={file_sha256(manifest_path)}",
        f"data_manifest_id={data_manifest.data_manifest_id}",
        f"data_manifest_hash={data_manifest_hash}",
        f"archive_snapshot_id={data_slice.archive_snapshot_id}",
        f"universe_snapshot_id={data_slice.universe_snapshot_id}",
        f"coverage_report_id={data_slice.coverage_report_id}",
        f"evidence_mode={request.evidence_mode.value}",
        f"venue={request.venue}",
        f"instrument_id={request.instrument_id}",
        f"family={request.family}",
        f"timeframe={request.timeframe}",
        f"loaded_fields={','.join(data_slice.loaded_fields)}",
        f"row_count={data_manifest.row_count}",
        f"warmup_row_count={data_manifest.warmup_row_count}",
        f"reported_row_count={data_manifest.reported_row_count}",
        f"start_ts={utc_isoformat(request.start_ts)}",
        f"end_ts={utc_isoformat(request.end_ts)}",
    ]
    archive_refs = (
        f"archive_snapshot_id={data_slice.archive_snapshot_id}",
        f"universe_snapshot_id={data_slice.universe_snapshot_id}",
        f"coverage_report_id={data_slice.coverage_report_id}",
        f"data_manifest_id={data_manifest.data_manifest_id}",
        f"backtest_data_manifest_path={manifest_path}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=tuple(output_refs),
        archive_manifest_refs=archive_refs,
        reason="backtest_data_load_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _data_request(spec: Mapping[str, Any]) -> BacktestDataRequest:
    payload = spec.get("backtest_data_request")
    if payload is None:
        payload = dict(spec)
    if not isinstance(payload, Mapping):
        raise ValueError("backtest_data_request must be an object when provided")
    data = dict(payload)
    if "include_lockbox" in spec and "exclude_lockbox" not in data:
        data["exclude_lockbox"] = not bool(spec["include_lockbox"])
    return BacktestDataRequest.model_validate(data)


def _optional_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))
