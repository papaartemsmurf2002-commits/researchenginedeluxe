# V2-AUDIT-ID: V2-AUD-COLLECT-001
# V2-CONTRACTS: docs/contracts/collector_job_contract.md, docs/contracts/worker_job_contract.md
# V2-BOUNDARY: research_only, durable_collectors, no_live_imports
# V2-OWNER: v2_collectors
"""Initial durable collector job handlers for v2 workers."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.microstructure import (
    MicrostructureDataType,
    parse_microstructure_datatype,
    preserve_official_s3_backfill_file,
    write_microstructure_raw_capture,
)
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter
from tradingbotsuite.v2.archive.rebuild import (
    RebuildResult,
    bronze_candles_to_silver_bars,
    bronze_funding_to_silver,
    raw_candles_to_bronze,
    raw_funding_to_bronze,
)
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.security.path_policy import resolve_within_root
from tradingbotsuite.v2.universe.hyperliquid import refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode
from tradingbotsuite.v2.venues.hyperliquid import HyperliquidInfoClient, HyperliquidWebSocketClient
from tradingbotsuite.v2.workers.job_store import WorkerJobStore
from tradingbotsuite.v2.workers.models import (
    WorkerJobKind,
    WorkerJobRecord,
    WorkerJobStatus,
    WorkerRunResult,
)


_DEFAULT_MAX_RECORDS_FILE_BYTES = 100 * 1024 * 1024
_RECORDS_FILE_SUFFIXES = frozenset({".json", ".jsonl", ".ndjson"})
_UNSAFE_RECORDS_FILE_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        "credentials.json",
        "credentials.jsonl",
        "secrets.json",
        "secrets.jsonl",
    }
)
_UNSAFE_RECORDS_FILE_SUFFIXES = frozenset(
    {
        ".db",
        ".dll",
        ".dylib",
        ".env",
        ".exe",
        ".gz",
        ".joblib",
        ".key",
        ".pem",
        ".pickle",
        ".pkl",
        ".sqlite",
        ".zip",
    }
)
_PUBLIC_INFO_TIME_RANGE_PAGE_LIMIT = 500
_PUBLIC_CANDLE_SNAPSHOT_ROW_LIMIT = 5000


class CollectorJobStatus(str, Enum):
    QUEUED = WorkerJobStatus.QUEUED.value
    RUNNING = WorkerJobStatus.RUNNING.value
    SUCCEEDED = WorkerJobStatus.SUCCEEDED.value
    FAILED = WorkerJobStatus.FAILED.value
    CANCELLED = WorkerJobStatus.CANCELLED.value
    STALE = WorkerJobStatus.STALE.value


class CollectorJobRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    job_id: str = Field(min_length=1)
    kind: WorkerJobKind
    status: CollectorJobStatus
    input_spec_hash: str = Field(min_length=64, max_length=64)
    archive_manifest_refs: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @classmethod
    def from_worker_job(cls, record: WorkerJobRecord) -> "CollectorJobRecord":
        return cls(
            job_id=record.job_id,
            kind=record.kind,
            status=CollectorJobStatus(record.status.value),
            input_spec_hash=record.input_spec_hash,
            archive_manifest_refs=record.archive_manifest_refs,
            output_refs=record.output_refs,
            failure_reason=record.failure_reason,
        )


def run_collector_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    if job.kind == WorkerJobKind.UNIVERSE_REFRESH:
        return _run_universe_refresh_job(job=job, store=store, worker_id=worker_id)
    if job.kind == WorkerJobKind.RECENT_CANDLE_BOOTSTRAP:
        return _run_recent_candle_bootstrap_job(job=job, store=store, worker_id=worker_id)
    if job.kind == WorkerJobKind.FUNDING_BACKFILL:
        return _run_funding_backfill_job(job=job, store=store, worker_id=worker_id)
    if job.kind == WorkerJobKind.WEBSOCKET_CAPTURE:
        return _run_websocket_capture_skeleton(job=job, store=store, worker_id=worker_id)
    if job.kind == WorkerJobKind.WEBSOCKET_TRADE_CAPTURE:
        return _run_microstructure_capture_job(
            job=job,
            store=store,
            worker_id=worker_id,
            datatype=MicrostructureDataType.TRADES,
        )
    if job.kind == WorkerJobKind.WEBSOCKET_L2_BBO_CAPTURE:
        return _run_microstructure_capture_job(
            job=job,
            store=store,
            worker_id=worker_id,
            datatype=parse_microstructure_datatype(str(job.input_spec.get("datatype", ""))),
        )
    if job.kind == WorkerJobKind.OFFICIAL_S3_BACKFILL:
        return _run_official_s3_backfill_job(job=job, store=store, worker_id=worker_id)
    raise ValueError(f"unsupported collector job kind: {job.kind.value}")


def _run_universe_refresh_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    source_mode = _universe_source_mode(spec)
    client = (
        HyperliquidInfoClient(
            base_url=str(spec.get("public_info_url", "https://api.hyperliquid.xyz/info")),
            timeout=float(spec.get("public_info_timeout", 20.0)),
        )
        if source_mode == "public_api"
        else None
    )
    result = refresh_hyperliquid_universe(
        archive_root=_required_str(spec, "archive_root"),
        payload_file=spec.get("payload_file") if source_mode == "payload_file" else None,
        asof_date=_parse_date(_required_str(spec, "asof_date")),
        min_day_notional_usd=int(spec.get("min_day_notional_usd", 5_000_000)),
        mode=UniverseMode(str(spec.get("mode", UniverseMode.AS_OF.value))),
        include_hip3_dexs=bool(spec.get("include_hip3_dexs", False)),
        client=client,
    )
    output_refs = [
        f"source_mode={result.payload_source}",
        f"universe_snapshot_id={result.snapshot_id}",
        f"eligible_count={result.eligible_count}",
        f"instrument_count={result.instrument_count}",
        f"raw_payload_sha256={result.raw_payload_sha256}",
        f"venue_adapter_id={result.venue_adapter_id}",
        f"source_endpoint_or_subscription={result.source_endpoint_or_subscription}",
    ]
    if result.raw_request_id:
        output_refs.append(f"raw_request_id={result.raw_request_id}")
    if result.raw_response_id:
        output_refs.append(f"raw_response_id={result.raw_response_id}")
    archive_refs = (
        f"raw_file_id={result.raw_file_id}",
        f"universe_snapshot_id={result.snapshot_id}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=tuple(output_refs),
        archive_manifest_refs=archive_refs,
        reason="universe_refresh_job_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_recent_candle_bootstrap_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    source_mode = _recent_candle_source_mode(spec)
    if source_mode == "public_api":
        return _run_public_recent_candle_bootstrap_job(
            job=job,
            store=store,
            worker_id=worker_id,
        )
    if _has_record_source(spec):
        archive_root = _required_str(spec, "archive_root")
        instrument_id = _required_str(spec, "instrument_id")
        timeframe = str(spec.get("timeframe", "1m"))
        start_ts = _parse_datetime(_required_str(spec, "start_ts"))
        end_ts = _parse_datetime(_required_str(spec, "end_ts"))
        records, source_refs, source_endpoint = _collector_records(
            spec,
            default_source_endpoint="fixture/rest/candles",
        )
        layout = ArchiveLayout(archive_root)
        layout.initialize()
        manifest_store = ArchiveManifestStore(layout)
        raw_file = RawJsonlZstdWriter(layout, manifest_store).write_records(
            records=records,
            venue=str(spec.get("venue", "hyperliquid")),
            datatype="candles",
            date=_required_str(spec, "date"),
            run_id=str(spec.get("run_id", job.job_id)),
            job_id=job.job_id,
            adapter_id=str(spec.get("adapter_id", "fixture_recent_candle_bootstrap_v1")),
            source_endpoint_or_subscription=source_endpoint,
            symbols=(instrument_id,),
            start_ts=start_ts,
            end_ts=end_ts,
            instrument_id=instrument_id,
            timeframe=timeframe,
        )
        bronze = raw_candles_to_bronze(
            archive_root=archive_root,
            raw_file_id=raw_file.file_id,
            job_id=f"{job.job_id}-bronze-candles",
            instrument_id=instrument_id,
            timeframe=timeframe,
        )
        silver = bronze_candles_to_silver_bars(
            archive_root=archive_root,
            bronze_file_id=bronze.output_files[0].file_id,
            job_id=f"{job.job_id}-silver-bars",
            derive_timeframes=_derive_timeframes(spec),
            write_coverage=not bool(spec.get("skip_coverage", False)),
            create_snapshot=bool(spec.get("create_snapshot", False)),
        )
        archive_refs = _market_data_archive_refs(
            raw_file_id=raw_file.file_id,
            bronze=bronze,
            silver=silver,
        )
        output_refs = (
            "collector_mode=fixture_candle_archive_write",
            f"row_count={raw_file.row_count or 0}",
            f"timeframe={timeframe}",
            *source_refs,
            *archive_refs,
        )
        record = store.succeed_job(
            job.job_id,
            worker_id=worker_id,
            output_refs=output_refs,
            archive_manifest_refs=archive_refs,
            reason="recent_candle_bootstrap_archive_write_succeeded",
        )
        return WorkerRunResult(
            job_id=job.job_id,
            status=record.status,
            output_refs=record.output_refs,
            archive_manifest_refs=record.archive_manifest_refs,
        )
    warning = _api_cap_warning(
        job=job,
        scope="recent_candle_bootstrap",
        instrument_id=str(spec.get("instrument_id", "unknown")),
        timeframe=str(spec.get("timeframe", "1m")),
    )
    output_refs = (
        warning,
        "collector_mode=diagnostic_skeleton",
        "archive_manifest_ref=pending_until_phase8_normalization",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=("archive_manifest_ref=pending_until_phase8_normalization",),
        reason="recent_candle_bootstrap_diagnostic_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
    )


def _run_public_recent_candle_bootstrap_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    timeframe = str(spec.get("timeframe", "1m"))
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    coin = _hyperliquid_coin_from_spec(spec, instrument_id=instrument_id)
    page_limit = _public_candle_page_limit(
        spec.get("max_candles_per_public_page", _PUBLIC_CANDLE_SNAPSHOT_ROW_LIMIT)
    )
    client = HyperliquidInfoClient(
        base_url=str(spec.get("public_info_url", "https://api.hyperliquid.xyz/info")),
        timeout=float(spec.get("public_info_timeout", 20.0)),
    )
    fetches = _fetch_public_candle_snapshot_pages(
        client=client,
        coin=coin,
        timeframe=timeframe,
        start_ts=start_ts,
        end_ts=end_ts,
        max_pages=int(spec.get("max_public_info_pages", 50)),
        page_limit=page_limit,
    )
    records = [
        row
        for fetch in fetches
        for row in _public_candle_records(fetch.payload)
    ]
    if not records:
        raise ValueError("public candleSnapshot response returned no rows")
    first_fetch = fetches[0]
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_store = ArchiveManifestStore(layout)
    raw_file = RawJsonlZstdWriter(layout, manifest_store).write_records(
        records=records,
        venue=str(spec.get("venue", "hyperliquid")),
        datatype="candles",
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=first_fetch.capability.adapter_id,
        source_endpoint_or_subscription=first_fetch.raw_request.source,
        symbols=(instrument_id,),
        start_ts=start_ts,
        end_ts=end_ts,
        instrument_id=instrument_id,
        timeframe=timeframe,
    )
    bronze = raw_candles_to_bronze(
        archive_root=archive_root,
        raw_file_id=raw_file.file_id,
        job_id=f"{job.job_id}-bronze-candles",
        instrument_id=instrument_id,
        timeframe=timeframe,
    )
    silver = bronze_candles_to_silver_bars(
        archive_root=archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id=f"{job.job_id}-silver-bars",
        derive_timeframes=_derive_timeframes(spec),
        write_coverage=not bool(spec.get("skip_coverage", False)),
        create_snapshot=bool(spec.get("create_snapshot", False)),
    )
    archive_refs = _market_data_archive_refs(
        raw_file_id=raw_file.file_id,
        bronze=bronze,
        silver=silver,
    )
    output_refs = (
        "collector_mode=public_api_candle_archive_write",
        "source_mode=public_api",
        f"row_count={raw_file.row_count or 0}",
        f"api_row_count={sum(fetch.raw_response.row_count for fetch in fetches)}",
        f"api_page_count={len(fetches)}",
        f"venue_adapter_id={first_fetch.capability.adapter_id}",
        f"source_endpoint_or_subscription={first_fetch.raw_request.source}",
        f"raw_request_id={first_fetch.raw_request.request_id}",
        f"raw_response_id={first_fetch.raw_response.response_id}",
        f"raw_payload_sha256={first_fetch.raw_response.raw_payload_sha256}",
        f"raw_request_ids={_csv(fetch.raw_request.request_id for fetch in fetches)}",
        f"raw_response_ids={_csv(fetch.raw_response.response_id for fetch in fetches)}",
        f"raw_payload_sha256s={_csv(fetch.raw_response.raw_payload_sha256 for fetch in fetches)}",
        f"coin={coin}",
        f"timeframe={timeframe}",
        "api_documented_limit=most_recent_5000_candles",
        f"api_page_span_limit_candles={page_limit}",
        "api_recent_window_caveat=not_full_historical_evidence",
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="recent_candle_bootstrap_public_api_archive_write_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
    )


def _run_funding_backfill_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    source_mode = _funding_source_mode(spec)
    if source_mode == "public_api":
        return _run_public_funding_backfill_job(job=job, store=store, worker_id=worker_id)
    if _has_record_source(spec):
        archive_root = _required_str(spec, "archive_root")
        instrument_id = _required_str(spec, "instrument_id")
        start_ts = _parse_datetime(_required_str(spec, "start_ts"))
        end_ts = _parse_datetime(_required_str(spec, "end_ts"))
        records, source_refs, source_endpoint = _collector_records(
            spec,
            default_source_endpoint="fixture/rest/funding",
        )
        layout = ArchiveLayout(archive_root)
        layout.initialize()
        manifest_store = ArchiveManifestStore(layout)
        raw_file = RawJsonlZstdWriter(layout, manifest_store).write_records(
            records=records,
            venue=str(spec.get("venue", "hyperliquid")),
            datatype="funding",
            date=_required_str(spec, "date"),
            run_id=str(spec.get("run_id", job.job_id)),
            job_id=job.job_id,
            adapter_id=str(spec.get("adapter_id", "fixture_funding_backfill_v1")),
            source_endpoint_or_subscription=source_endpoint,
            symbols=(instrument_id,),
            start_ts=start_ts,
            end_ts=end_ts,
            instrument_id=instrument_id,
        )
        bronze = raw_funding_to_bronze(
            archive_root=archive_root,
            raw_file_id=raw_file.file_id,
            job_id=f"{job.job_id}-bronze-funding",
            instrument_id=instrument_id,
        )
        silver = bronze_funding_to_silver(
            archive_root=archive_root,
            bronze_file_id=bronze.output_files[0].file_id,
            job_id=f"{job.job_id}-silver-funding",
        )
        archive_refs = _market_data_archive_refs(
            raw_file_id=raw_file.file_id,
            bronze=bronze,
            silver=silver,
        )
        output_refs = (
            "collector_mode=fixture_funding_archive_write",
            f"row_count={raw_file.row_count or 0}",
            *source_refs,
            *archive_refs,
        )
        record = store.succeed_job(
            job.job_id,
            worker_id=worker_id,
            output_refs=output_refs,
            archive_manifest_refs=archive_refs,
            reason="funding_backfill_archive_write_succeeded",
        )
        return WorkerRunResult(
            job_id=job.job_id,
            status=record.status,
            output_refs=record.output_refs,
            archive_manifest_refs=record.archive_manifest_refs,
        )
    warning = _api_cap_warning(
        job=job,
        scope="funding_backfill",
        instrument_id=str(spec.get("instrument_id", "unknown")),
        timeframe="funding",
    )
    output_refs = (
        warning,
        "collector_mode=diagnostic_skeleton",
        "archive_manifest_ref=pending_until_phase8_normalization",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=("archive_manifest_ref=pending_until_phase8_normalization",),
        reason="funding_backfill_diagnostic_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
    )


def _run_public_funding_backfill_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    coin = _hyperliquid_coin_from_spec(spec, instrument_id=instrument_id)
    client = HyperliquidInfoClient(
        base_url=str(spec.get("public_info_url", "https://api.hyperliquid.xyz/info")),
        timeout=float(spec.get("public_info_timeout", 20.0)),
    )
    fetches = _fetch_public_funding_history_pages(
        client=client,
        coin=coin,
        start_ts=start_ts,
        end_ts=end_ts,
        max_pages=int(spec.get("max_public_info_pages", 50)),
    )
    records = [
        row
        for fetch in fetches
        for row in _public_funding_records(fetch.payload)
    ]
    if not records:
        raise ValueError("public fundingHistory response returned no rows")
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_store = ArchiveManifestStore(layout)
    raw_file = RawJsonlZstdWriter(layout, manifest_store).write_records(
        records=records,
        venue=str(spec.get("venue", "hyperliquid")),
        datatype="funding",
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=fetches[0].capability.adapter_id,
        source_endpoint_or_subscription=fetches[0].raw_request.source,
        symbols=(instrument_id,),
        start_ts=start_ts,
        end_ts=end_ts,
        instrument_id=instrument_id,
    )
    bronze = raw_funding_to_bronze(
        archive_root=archive_root,
        raw_file_id=raw_file.file_id,
        job_id=f"{job.job_id}-bronze-funding",
        instrument_id=instrument_id,
    )
    silver = bronze_funding_to_silver(
        archive_root=archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id=f"{job.job_id}-silver-funding",
    )
    archive_refs = _market_data_archive_refs(
        raw_file_id=raw_file.file_id,
        bronze=bronze,
        silver=silver,
    )
    output_refs = (
        "collector_mode=public_api_funding_archive_write",
        "source_mode=public_api",
        f"row_count={raw_file.row_count or 0}",
        f"api_row_count={sum(fetch.raw_response.row_count for fetch in fetches)}",
        f"api_page_count={len(fetches)}",
        f"venue_adapter_id={fetches[0].capability.adapter_id}",
        f"source_endpoint_or_subscription={fetches[0].raw_request.source}",
        f"raw_request_ids={_csv(fetch.raw_request.request_id for fetch in fetches)}",
        f"raw_response_ids={_csv(fetch.raw_response.response_id for fetch in fetches)}",
        f"raw_payload_sha256s={_csv(fetch.raw_response.raw_payload_sha256 for fetch in fetches)}",
        f"coin={coin}",
        "api_documented_limit=time_range_responses_return_500_elements_or_blocks",
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="funding_backfill_public_api_archive_write_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
    )


def _run_websocket_capture_skeleton(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    reconnect_attempts = int(spec.get("reconnect_attempts", 1))
    backoff_seconds = int(spec.get("backoff_seconds", 1))
    reason = str(spec.get("gap_reason", "websocket_capture_not_started_in_phase7_skeleton"))
    start_ts = _optional_datetime(spec.get("start_ts"))
    end_ts = _optional_datetime(spec.get("end_ts"))
    gap = store.record_gap(
        job_id=job.job_id,
        kind=job.kind,
        reason=reason,
        worker_id=worker_id,
        start_ts=start_ts,
        end_ts=end_ts,
        backoff_seconds=backoff_seconds,
        reconnect_attempts=reconnect_attempts,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=(
            "collector_mode=websocket_capture_skeleton",
            f"gap_record_id={gap.gap_record_id}",
            "archive_manifest_ref=gap_record_only",
        ),
        archive_manifest_refs=("archive_manifest_ref=gap_record_only",),
        gap_record_ids=(gap.gap_record_id,),
        reason="websocket_capture_gap_recorded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_microstructure_capture_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
    datatype: MicrostructureDataType,
) -> WorkerRunResult:
    if datatype not in {MicrostructureDataType.TRADES, MicrostructureDataType.BBO, MicrostructureDataType.L2}:
        raise ValueError("microstructure capture job requires datatype trades, bbo, or l2")
    spec = job.input_spec
    source_mode = _microstructure_source_mode(spec, datatype=datatype)
    if source_mode == "public_api":
        return _run_public_l2_bbo_capture_job(
            job=job,
            store=store,
            worker_id=worker_id,
            datatype=datatype,
        )
    if source_mode == "public_websocket":
        return _run_public_websocket_trade_capture_job(
            job=job,
            store=store,
            worker_id=worker_id,
            datatype=datatype,
        )
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    reconnect_attempts = int(spec.get("reconnect_attempts", 0))
    backoff_seconds = int(spec.get("backoff_seconds", 0))
    gap_reason = str(spec.get("gap_reason", "")).strip()
    has_gap_evidence = bool(gap_reason) or reconnect_attempts > 0
    capture = write_microstructure_raw_capture(
        archive_root=_required_str(spec, "archive_root"),
        records=_required_records(spec),
        venue=str(spec.get("venue", "hyperliquid")),
        datatype=datatype,
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=str(spec.get("adapter_id", "fixture_microstructure_v1")),
        source_endpoint_or_subscription=str(
            spec.get("source_endpoint_or_subscription", f"fixture/websocket/{datatype.value}")
        ),
        instrument_id=_required_str(spec, "instrument_id"),
        start_ts=start_ts,
        end_ts=end_ts,
        storage_budget_bytes=int(spec.get("storage_budget_bytes", 1_000_000_000)),
        reconnect_attempts=reconnect_attempts,
        gap_count=1 if has_gap_evidence else 0,
    )
    gap_record_ids: tuple[str, ...] = ()
    if has_gap_evidence:
        gap = store.record_gap(
            job_id=job.job_id,
            kind=job.kind,
            reason=gap_reason or "microstructure_reconnect_recorded",
            worker_id=worker_id,
            start_ts=start_ts,
            end_ts=end_ts,
            backoff_seconds=backoff_seconds,
            reconnect_attempts=reconnect_attempts,
        )
        gap_record_ids = (gap.gap_record_id,)
    archive_refs = (
        f"raw_file_id={capture.raw_file.file_id}",
        f"quality_report_id={capture.quality_report.quality_report_id}",
        f"storage_report_id={capture.storage_report.storage_report_id}",
    )
    output_refs = (
        "collector_mode=fixture_microstructure_capture",
        f"datatype={datatype.value}",
        f"row_count={capture.raw_file.row_count or 0}",
        f"storage_total_bytes={capture.storage_report.total_bytes}",
        f"storage_within_budget={str(capture.storage_report.within_budget).lower()}",
        f"gap_evidence_recorded={str(has_gap_evidence).lower()}",
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        gap_record_ids=gap_record_ids,
        reason=f"{datatype.value}_microstructure_capture_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_public_websocket_trade_capture_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
    datatype: MicrostructureDataType,
) -> WorkerRunResult:
    if datatype != MicrostructureDataType.TRADES:
        raise ValueError("public websocket capture only supports datatype trades")
    spec = job.input_spec
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    coin = _hyperliquid_coin_from_spec(spec, instrument_id=instrument_id)
    max_messages = int(spec.get("max_public_ws_messages", 20))
    max_rows = int(spec.get("max_public_ws_rows", 200))
    max_seconds = float(spec.get("max_public_ws_seconds", spec.get("public_ws_timeout", 20.0)))
    fetch = HyperliquidWebSocketClient(
        ws_url=str(spec.get("public_ws_url", "wss://api.hyperliquid.xyz/ws")),
        timeout=float(spec.get("public_ws_timeout", max_seconds)),
    ).fetch_trade_snapshot(
        coin=coin,
        max_messages=max_messages,
        max_rows=max_rows,
        max_seconds=max_seconds,
    )
    records = _public_websocket_trade_records(
        fetch.payload,
        instrument_id=instrument_id,
        max_rows=max_rows,
    )
    capture = write_microstructure_raw_capture(
        archive_root=archive_root,
        records=records,
        venue=str(spec.get("venue", "hyperliquid")),
        datatype=datatype,
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=fetch.capability.adapter_id,
        source_endpoint_or_subscription=fetch.raw_request.source,
        instrument_id=instrument_id,
        start_ts=start_ts,
        end_ts=end_ts,
        storage_budget_bytes=int(spec.get("storage_budget_bytes", 1_000_000_000)),
    )
    archive_refs = (
        f"raw_file_id={capture.raw_file.file_id}",
        f"quality_report_id={capture.quality_report.quality_report_id}",
        f"storage_report_id={capture.storage_report.storage_report_id}",
    )
    output_refs = (
        "collector_mode=public_websocket_trade_snapshot_capture",
        "source_mode=public_websocket",
        f"datatype={datatype.value}",
        f"row_count={capture.raw_file.row_count or 0}",
        f"ws_message_count={len(fetch.payload)}",
        f"ws_trade_row_count={fetch.raw_response.row_count}",
        f"venue_adapter_id={fetch.capability.adapter_id}",
        f"source_endpoint_or_subscription={fetch.raw_request.source}",
        f"raw_request_id={fetch.raw_request.request_id}",
        f"raw_response_id={fetch.raw_response.response_id}",
        f"raw_payload_sha256={fetch.raw_response.raw_payload_sha256}",
        f"coin={coin}",
        f"max_public_ws_messages={max_messages}",
        f"max_public_ws_rows={max_rows}",
        f"max_public_ws_seconds={max_seconds}",
        f"storage_total_bytes={capture.storage_report.total_bytes}",
        f"storage_within_budget={str(capture.storage_report.within_budget).lower()}",
        "gap_evidence_recorded=false",
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="trades_public_websocket_snapshot_capture_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_public_l2_bbo_capture_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
    datatype: MicrostructureDataType,
) -> WorkerRunResult:
    spec = job.input_spec
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    coin = _hyperliquid_coin_from_spec(spec, instrument_id=instrument_id)
    fetch = HyperliquidInfoClient(
        base_url=str(spec.get("public_info_url", "https://api.hyperliquid.xyz/info")),
        timeout=float(spec.get("public_info_timeout", 20.0)),
    ).fetch_l2_book(
        coin=coin,
        n_sig_figs=_optional_int(spec.get("n_sig_figs")),
        mantissa=_optional_int(spec.get("mantissa")),
    )
    records = _public_l2_book_microstructure_records(
        fetch.payload,
        datatype=datatype,
        instrument_id=instrument_id,
    )
    capture = write_microstructure_raw_capture(
        archive_root=archive_root,
        records=records,
        venue=str(spec.get("venue", "hyperliquid")),
        datatype=datatype,
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=fetch.capability.adapter_id,
        source_endpoint_or_subscription=fetch.raw_request.source,
        instrument_id=instrument_id,
        start_ts=start_ts,
        end_ts=end_ts,
        storage_budget_bytes=int(spec.get("storage_budget_bytes", 1_000_000_000)),
    )
    archive_refs = (
        f"raw_file_id={capture.raw_file.file_id}",
        f"quality_report_id={capture.quality_report.quality_report_id}",
        f"storage_report_id={capture.storage_report.storage_report_id}",
    )
    output_refs = (
        "collector_mode=public_api_l2_bbo_snapshot_capture",
        "source_mode=public_api",
        f"datatype={datatype.value}",
        f"row_count={capture.raw_file.row_count or 0}",
        f"api_row_count={fetch.raw_response.row_count}",
        f"venue_adapter_id={fetch.capability.adapter_id}",
        f"source_endpoint_or_subscription={fetch.raw_request.source}",
        f"raw_request_id={fetch.raw_request.request_id}",
        f"raw_response_id={fetch.raw_response.response_id}",
        f"raw_payload_sha256={fetch.raw_response.raw_payload_sha256}",
        f"coin={coin}",
        "api_documented_limit=max_20_levels_per_side",
        f"storage_total_bytes={capture.storage_report.total_bytes}",
        f"storage_within_budget={str(capture.storage_report.within_budget).lower()}",
        "gap_evidence_recorded=false",
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason=f"{datatype.value}_public_l2_book_snapshot_capture_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_official_s3_backfill_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    raw_file, storage_report = preserve_official_s3_backfill_file(
        archive_root=_required_str(spec, "archive_root"),
        source_file=_required_str(spec, "source_file"),
        trusted_source_root=_required_str(spec, "trusted_source_root"),
        venue=str(spec.get("venue", "hyperliquid")),
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=str(spec.get("adapter_id", "official_s3_backfill_fixture_v1")),
        source_endpoint_or_subscription=str(
            spec.get("source_endpoint_or_subscription", "official_s3_backfill_fixture")
        ),
        instrument_id=spec.get("instrument_id"),
        start_ts=_parse_datetime(_required_str(spec, "start_ts")),
        end_ts=_parse_datetime(_required_str(spec, "end_ts")),
        storage_budget_bytes=int(spec.get("storage_budget_bytes", 1_000_000_000)),
        row_count=int(spec.get("row_count", 0)),
        filename=spec.get("filename"),
    )
    archive_refs = (
        f"raw_file_id={raw_file.file_id}",
        f"storage_report_id={storage_report.storage_report_id}",
    )
    output_refs = (
        "collector_mode=official_s3_backfill_preserve_local_file",
        f"row_count={raw_file.row_count or 0}",
        f"storage_total_bytes={storage_report.total_bytes}",
        f"storage_within_budget={str(storage_report.within_budget).lower()}",
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="official_s3_backfill_preserved",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _api_cap_warning(
    *,
    job: WorkerJobRecord,
    scope: str,
    instrument_id: str,
    timeframe: str,
) -> str:
    warning_id = canonical_json_hash(
        {
            "job_id": job.job_id,
            "scope": scope,
            "instrument_id": instrument_id,
            "timeframe": timeframe,
            "input_spec_hash": job.input_spec_hash,
        }
    )[:16]
    return f"api_cap_warning_id={warning_id}:latest_window_or_api_cap_must_not_support_accepted_evidence"


def _required_str(spec: dict[str, Any], key: str) -> str:
    value = spec.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"collector job spec requires {key}")
    return value


def _universe_source_mode(spec: dict[str, Any]) -> str:
    source = str(spec.get("source", "")).strip()
    has_payload_file = bool(spec.get("payload_file"))
    if source:
        if source not in {"payload_file", "public_api"}:
            raise ValueError("universe_refresh source must be payload_file or public_api")
        if source == "payload_file" and not has_payload_file:
            raise ValueError("universe_refresh source=payload_file requires payload_file")
        if source == "public_api" and has_payload_file:
            raise ValueError("universe_refresh source=public_api cannot include payload_file")
        return source
    if has_payload_file:
        return "payload_file"
    raise ValueError("universe_refresh job requires payload_file or source=public_api")


def _recent_candle_source_mode(spec: dict[str, Any]) -> str:
    source = str(spec.get("source", "")).strip()
    has_records = _has_record_source(spec)
    if not source:
        return "records" if has_records else "diagnostic"
    if source == "public_api":
        if has_records:
            raise ValueError("recent_candle_bootstrap source=public_api cannot include records")
        return "public_api"
    if source not in {"records", "records_file", "inline"}:
        raise ValueError("recent_candle_bootstrap source must be public_api, records, or records_file")
    if not has_records:
        raise ValueError(f"recent_candle_bootstrap source={source} requires records or records_file")
    return "records"


def _funding_source_mode(spec: dict[str, Any]) -> str:
    source = str(spec.get("source", "")).strip()
    has_records = _has_record_source(spec)
    if not source:
        return "records" if has_records else "diagnostic"
    if source == "public_api":
        if has_records:
            raise ValueError("funding_backfill source=public_api cannot include records")
        return "public_api"
    if source not in {"records", "records_file", "inline"}:
        raise ValueError("funding_backfill source must be public_api, records, or records_file")
    if not has_records:
        raise ValueError(f"funding_backfill source={source} requires records or records_file")
    return "records"


def _microstructure_source_mode(
    spec: dict[str, Any],
    *,
    datatype: MicrostructureDataType,
) -> str:
    source = str(spec.get("source", "")).strip()
    has_records = _has_record_source(spec)
    if not source:
        return "records"
    if source == "public_websocket":
        if datatype != MicrostructureDataType.TRADES:
            raise ValueError("microstructure source=public_websocket only supports datatype trades")
        if has_records:
            raise ValueError("websocket_trade_capture source=public_websocket cannot include records")
        return "public_websocket"
    if source == "public_api":
        if datatype not in {MicrostructureDataType.BBO, MicrostructureDataType.L2}:
            raise ValueError("microstructure source=public_api only supports datatype bbo or l2")
        if has_records:
            raise ValueError("websocket_l2_bbo_capture source=public_api cannot include records")
        return "public_api"
    if source not in {"records", "inline"}:
        raise ValueError("microstructure capture source must be public_api, public_websocket, or records")
    if not has_records:
        raise ValueError(f"microstructure capture source={source} requires records")
    return "records"


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("collector timestamps must include timezone")
    return parsed


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"unsupported datetime value: {value!r}")


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _required_records(spec: dict[str, Any]) -> list[dict[str, Any]]:
    value = spec.get("records")
    if not isinstance(value, list) or not value:
        raise ValueError("collector job spec requires non-empty records")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"collector records[{index}] must be an object")
        rows.append(dict(item))
    return rows


def _has_record_source(spec: dict[str, Any]) -> bool:
    return ("records" in spec and spec.get("records") is not None) or bool(
        spec.get("records_file")
    )


def _collector_records(
    spec: dict[str, Any],
    *,
    default_source_endpoint: str,
) -> tuple[list[dict[str, Any]], tuple[str, ...], str]:
    has_inline = "records" in spec and spec.get("records") is not None
    has_file = bool(spec.get("records_file"))
    if has_inline and has_file:
        raise ValueError("collector job spec cannot include both records and records_file")
    if has_inline:
        records = _required_records(spec)
        return (
            records,
            ("records_source=inline", f"records_inline_row_count={len(records)}"),
            str(spec.get("source_endpoint_or_subscription", default_source_endpoint)),
        )
    if has_file:
        path = _resolve_records_file(spec)
        records = _read_records_file(
            path,
            records_format=str(spec.get("records_format", "auto")),
        )
        source_refs = (
            "records_source=records_file",
            f"records_file_sha256={file_sha256(path)}",
            f"records_file_row_count={len(records)}",
        )
        return records, source_refs, str(
            spec.get("source_endpoint_or_subscription", f"local_records_file:{path.name}")
        )
    raise ValueError("collector job spec requires records or records_file")


def _resolve_records_file(spec: dict[str, Any]) -> Path:
    records_file = _required_str(spec, "records_file")
    trusted_root = _required_str(spec, "trusted_source_root")
    resolved = resolve_within_root(trusted_root, records_file)
    _validate_records_file_path(resolved)
    if not resolved.exists():
        raise ValueError(f"collector records_file does not exist: {records_file}")
    if not resolved.is_file():
        raise ValueError(f"collector records_file is not a file: {records_file}")
    max_bytes = int(spec.get("max_records_file_bytes", _DEFAULT_MAX_RECORDS_FILE_BYTES))
    if max_bytes <= 0:
        raise ValueError("max_records_file_bytes must be positive")
    size_bytes = resolved.stat().st_size
    if size_bytes > max_bytes:
        raise ValueError(
            f"collector records_file exceeds max_records_file_bytes: {size_bytes}>{max_bytes}"
        )
    return resolved


def _validate_records_file_path(path: Path) -> None:
    suffix = path.suffix.lower()
    suffixes = {part.lower() for part in path.suffixes}
    if path.name.lower() in _UNSAFE_RECORDS_FILE_NAMES:
        raise ValueError("collector records_file name is reserved for secrets or local state")
    if suffixes & _UNSAFE_RECORDS_FILE_SUFFIXES:
        raise ValueError("collector records_file has an unsafe extension")
    if suffix not in _RECORDS_FILE_SUFFIXES:
        raise ValueError("collector records_file must use .json, .jsonl, or .ndjson")


def _read_records_file(path: Path, *, records_format: str) -> list[dict[str, Any]]:
    normalized = records_format.lower()
    if normalized == "auto":
        normalized = "json" if path.suffix.lower() == ".json" else "jsonl"
    if normalized == "json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("collector JSON records_file must contain a list")
        return _coerce_record_rows(payload)
    if normalized in {"jsonl", "ndjson"}:
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"collector JSONL records_file line {line_number} is invalid JSON") from exc
            if not isinstance(value, dict):
                raise ValueError(f"collector JSONL records_file line {line_number} must be an object")
            rows.append(dict(value))
        if not rows:
            raise ValueError("collector JSONL records_file must contain at least one object")
        return rows
    raise ValueError("records_format must be auto, json, jsonl, or ndjson")


def _coerce_record_rows(value: list[Any]) -> list[dict[str, Any]]:
    if not value:
        raise ValueError("collector records_file requires non-empty records")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"collector records_file[{index}] must be an object")
        rows.append(dict(item))
    return rows


def _public_candle_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("public candleSnapshot response must be a list")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"public candleSnapshot response[{index}] must be an object")
        rows.append(dict(item))
    if not rows:
        raise ValueError("public candleSnapshot response returned no rows")
    return rows


def _fetch_public_candle_snapshot_pages(
    *,
    client: HyperliquidInfoClient,
    coin: str,
    timeframe: str,
    start_ts: datetime,
    end_ts: datetime,
    max_pages: int,
    page_limit: int,
):
    if max_pages <= 0:
        raise ValueError("max_public_info_pages must be positive")
    if page_limit <= 0:
        raise ValueError("max_candles_per_public_page must be positive")
    pages = []
    for page_index, (page_start, page_end) in enumerate(
        _public_candle_snapshot_windows(
            start_ts=start_ts,
            end_ts=end_ts,
            timeframe=timeframe,
            page_limit=page_limit,
        )
    ):
        if page_index >= max_pages:
            raise ValueError("public candleSnapshot pagination exceeded max_public_info_pages")
        fetch = client.fetch_candle_snapshot(
            coin=coin,
            interval=timeframe,
            start_time=page_start,
            end_time=page_end,
        )
        _public_candle_records(fetch.payload)
        pages.append(fetch)
    if not pages:
        raise ValueError("public candleSnapshot response returned no rows")
    return tuple(pages)


def _public_candle_page_limit(value: Any) -> int:
    page_limit = int(value)
    if page_limit <= 0:
        raise ValueError("max_candles_per_public_page must be positive")
    if page_limit > _PUBLIC_CANDLE_SNAPSHOT_ROW_LIMIT:
        raise ValueError("max_candles_per_public_page cannot exceed documented 5000-candle limit")
    return page_limit


def _public_candle_snapshot_windows(
    *,
    start_ts: datetime,
    end_ts: datetime,
    timeframe: str,
    page_limit: int,
):
    if end_ts <= start_ts:
        raise ValueError("public candleSnapshot end_ts must be after start_ts")
    interval = _public_candle_interval_delta(timeframe)
    page_span = interval * page_limit
    cursor = start_ts
    while cursor < end_ts:
        page_end = min(cursor + page_span, end_ts)
        if page_end <= cursor:
            raise ValueError("public candleSnapshot pagination did not advance")
        yield cursor, page_end
        cursor = page_end


def _public_candle_interval_delta(timeframe: str) -> timedelta:
    text = timeframe.strip()
    if len(text) < 2:
        raise ValueError("public candleSnapshot timeframe must include amount and unit")
    amount_text = text[:-1]
    unit = text[-1]
    if not amount_text.isdigit():
        raise ValueError("public candleSnapshot timeframe amount must be a positive integer")
    amount = int(amount_text)
    if amount <= 0:
        raise ValueError("public candleSnapshot timeframe amount must be positive")
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    if unit == "w":
        return timedelta(weeks=amount)
    raise ValueError("public candleSnapshot pagination supports fixed-width m, h, d, or w intervals")


def _fetch_public_funding_history_pages(
    *,
    client: HyperliquidInfoClient,
    coin: str,
    start_ts: datetime,
    end_ts: datetime,
    max_pages: int,
):
    if max_pages <= 0:
        raise ValueError("max_public_info_pages must be positive")
    pages = []
    cursor = start_ts
    end_ms = _timestamp_millis(end_ts)
    last_seen_ms: int | None = None
    for _page_index in range(max_pages):
        fetch = client.fetch_funding_history(
            coin=coin,
            start_time=cursor,
            end_time=end_ts,
        )
        rows = _public_funding_records(fetch.payload)
        if not rows:
            break
        page_max_ms = max(_funding_row_time_millis(row) for row in rows)
        if last_seen_ms is not None and page_max_ms <= last_seen_ms:
            raise ValueError("public fundingHistory pagination did not advance")
        pages.append(fetch)
        last_seen_ms = page_max_ms
        if page_max_ms >= end_ms or len(rows) < _PUBLIC_INFO_TIME_RANGE_PAGE_LIMIT:
            break
        cursor = datetime.fromtimestamp((page_max_ms + 1) / 1000, tz=UTC)
    else:
        raise ValueError("public fundingHistory pagination exceeded max_public_info_pages")
    if not pages:
        raise ValueError("public fundingHistory response returned no rows")
    return tuple(pages)


def _public_funding_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("public fundingHistory response must be a list")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"public fundingHistory response[{index}] must be an object")
        rows.append(dict(item))
    return rows


def _public_l2_book_microstructure_records(
    payload: Any,
    *,
    datatype: MicrostructureDataType,
    instrument_id: str,
) -> list[dict[str, Any]]:
    snapshot_ts = _public_l2_book_time(payload)
    bid_levels, ask_levels = _public_l2_book_levels(payload)
    source = "public_api/info/l2Book"
    if datatype == MicrostructureDataType.BBO:
        best_bid = bid_levels[0]
        best_ask = ask_levels[0]
        return [
            {
                "ts": snapshot_ts.isoformat(),
                "instrument_id": instrument_id,
                "event_type": "bbo",
                "sequence": 0,
                "bid": _l2_level_price(best_bid, side="bid", index=0),
                "ask": _l2_level_price(best_ask, side="ask", index=0),
                "bid_size": _l2_level_size(best_bid, side="bid", index=0),
                "ask_size": _l2_level_size(best_ask, side="ask", index=0),
                "source": source,
            }
        ]
    if datatype == MicrostructureDataType.L2:
        return [
            {
                "ts": snapshot_ts.isoformat(),
                "instrument_id": instrument_id,
                "event_type": "l2",
                "sequence": 0,
                "bid_depth": sum(
                    _l2_level_size(level, side="bid", index=index)
                    for index, level in enumerate(bid_levels)
                ),
                "ask_depth": sum(
                    _l2_level_size(level, side="ask", index=index)
                    for index, level in enumerate(ask_levels)
                ),
                "book_levels": len(bid_levels) + len(ask_levels),
                "source": source,
            }
        ]
    raise ValueError("public l2Book capture only supports datatype bbo or l2")


def _public_websocket_trade_records(
    payload: Any,
    *,
    instrument_id: str,
    max_rows: int,
) -> list[dict[str, Any]]:
    if max_rows <= 0:
        raise ValueError("max_rows must be positive")
    messages = _coerce_public_websocket_messages(payload)
    rows: list[dict[str, Any]] = []
    sequence = 0
    for message in messages:
        if message.get("channel") != "trades":
            continue
        data = message.get("data")
        if not isinstance(data, list):
            raise ValueError("public websocket trades message data must be a list")
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"public websocket trades data[{index}] must be an object")
            rows.append(
                _public_websocket_trade_row(
                    dict(item),
                    instrument_id=instrument_id,
                    sequence=sequence,
                )
            )
            sequence += 1
            if len(rows) >= max_rows:
                break
        if len(rows) >= max_rows:
            break
    if not rows:
        raise ValueError("public websocket trades returned no trade rows")
    return rows


def _coerce_public_websocket_messages(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, tuple):
        payload = list(payload)
    if not isinstance(payload, list):
        raise ValueError("public websocket payload must be a message list")
    messages: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"public websocket message[{index}] must be an object")
        messages.append(dict(item))
    return messages


def _public_websocket_trade_row(
    item: dict[str, Any],
    *,
    instrument_id: str,
    sequence: int,
) -> dict[str, Any]:
    ts = _timestamp_datetime(_required_trade_value(item, "time"))
    price = _positive_float(_required_trade_value(item, "px"), field="px")
    size = _positive_float(_required_trade_value(item, "sz"), field="sz")
    coin = str(item.get("coin", "")).strip()
    tid = item.get("tid")
    trade_id = f"{coin or instrument_id}:{_timestamp_millis(item['time'])}:{tid}" if tid is not None else item.get("hash")
    return {
        "ts": ts.isoformat(timespec="milliseconds"),
        "instrument_id": instrument_id,
        "event_type": "trade",
        "sequence": sequence,
        "price": price,
        "size": size,
        "side": str(item.get("side")) if item.get("side") is not None else None,
        "trade_id": str(trade_id) if trade_id is not None else None,
        "source": "public_websocket/trades",
    }


def _required_trade_value(item: dict[str, Any], field: str) -> Any:
    value = item.get(field)
    if value is None:
        raise ValueError(f"public websocket trade is missing {field}")
    return value


def _positive_float(value: Any, *, field: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"public websocket trade {field} must be positive")
    return parsed


def _public_l2_book_time(payload: Any) -> datetime:
    if not isinstance(payload, dict):
        raise ValueError("public l2Book response must be an object")
    value = payload.get("time")
    if value is None:
        value = payload.get("ts")
    if value is None:
        raise ValueError("public l2Book response is missing time")
    return _timestamp_datetime(value)


def _public_l2_book_levels(payload: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        raise ValueError("public l2Book response must be an object")
    levels = payload.get("levels")
    if not isinstance(levels, list) or len(levels) < 2:
        raise ValueError("public l2Book response must contain bid and ask levels")
    bids = _coerce_l2_levels(levels[0], side="bid")
    asks = _coerce_l2_levels(levels[1], side="ask")
    if not bids or not asks:
        raise ValueError("public l2Book response returned no top-of-book levels")
    return bids, asks


def _coerce_l2_levels(value: Any, *, side: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"public l2Book {side} levels must be a list")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"public l2Book {side} levels[{index}] must be an object")
        rows.append(dict(item))
    return rows


def _l2_level_price(level: dict[str, Any], *, side: str, index: int) -> float:
    value = level.get("px")
    if value is None:
        value = level.get("price")
    if value is None:
        raise ValueError(f"public l2Book {side} levels[{index}] missing px")
    price = float(value)
    if price <= 0:
        raise ValueError(f"public l2Book {side} levels[{index}] price must be positive")
    return price


def _l2_level_size(level: dict[str, Any], *, side: str, index: int) -> float:
    value = level.get("sz")
    if value is None:
        value = level.get("size")
    if value is None:
        raise ValueError(f"public l2Book {side} levels[{index}] missing sz")
    size = float(value)
    if size < 0:
        raise ValueError(f"public l2Book {side} levels[{index}] size must be non-negative")
    return size


def _funding_row_time_millis(row: dict[str, Any]) -> int:
    value = row.get("time")
    if value is None:
        value = row.get("ts")
    if value is None:
        value = row.get("funding_time")
    if value is None:
        raise ValueError("public fundingHistory row is missing time")
    return _timestamp_millis(value)


def _timestamp_millis(value: Any) -> int:
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, int | float):
        numeric = float(value)
        if numeric > 10_000_000_000:
            return int(numeric)
        return int(numeric * 1000)
    if isinstance(value, str):
        if value.isdigit():
            return _timestamp_millis(int(value))
        return int(_parse_datetime(value).timestamp() * 1000)
    raise ValueError(f"unsupported timestamp value: {value!r}")


def _timestamp_datetime(value: Any) -> datetime:
    return datetime.fromtimestamp(_timestamp_millis(value) / 1000, tz=UTC)


def _hyperliquid_coin_from_spec(spec: dict[str, Any], *, instrument_id: str) -> str:
    explicit = str(spec.get("coin", "")).strip()
    if explicit:
        return explicit
    perp_prefix = "hyperliquid:perp:"
    hip3_prefix = "hyperliquid:hip3:"
    if instrument_id.startswith(perp_prefix):
        return instrument_id[len(perp_prefix) :]
    if instrument_id.startswith(hip3_prefix):
        return instrument_id[len(hip3_prefix) :]
    return instrument_id


def _derive_timeframes(spec: dict[str, Any]) -> tuple[str, ...]:
    value = spec.get("derive_timeframes", ("5m", "15m", "1h"))
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(part).strip() for part in value if str(part).strip())
    raise ValueError("derive_timeframes must be a comma-delimited string or list")


def _market_data_archive_refs(
    *,
    raw_file_id: str,
    bronze: RebuildResult,
    silver: RebuildResult,
) -> tuple[str, ...]:
    refs = [
        f"raw_file_id={raw_file_id}",
        f"bronze_file_ids={_csv(row.file_id for row in bronze.output_files)}",
        f"silver_file_ids={_csv(row.file_id for row in silver.output_files)}",
        f"normalization_manifest_ids={_csv(_normalization_ids(bronze, silver))}",
    ]
    if silver.coverage_report_ids:
        refs.append(f"coverage_report_ids={','.join(silver.coverage_report_ids)}")
    if silver.archive_snapshot_id:
        refs.append(f"archive_snapshot_id={silver.archive_snapshot_id}")
    return tuple(refs)


def _normalization_ids(*results: RebuildResult) -> tuple[str, ...]:
    return tuple(
        manifest.normalization_manifest_id
        for result in results
        for manifest in result.normalization_manifests
    )


def _csv(values) -> str:
    return ",".join(str(value) for value in values)


def normalize_payload_file(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return str(Path(path))
