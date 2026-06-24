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
    bronze_asset_contexts_to_silver,
    bronze_candles_to_silver_bars,
    bronze_funding_to_silver,
    raw_asset_contexts_to_bronze,
    raw_candles_to_bronze,
    raw_funding_to_bronze,
)
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.config.time import utc_isoformat, utc_now
from tradingbotsuite.v2.data_sources.binance_derivatives import (
    BinanceDerivativesContextGetResult,
    run_binance_derivatives_context_backfill,
)
from tradingbotsuite.v2.security.path_policy import resolve_within_root
from tradingbotsuite.v2.universe.hyperliquid import load_universe_rows, refresh_hyperliquid_universe
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
_PUBLIC_WEBSOCKET_CAPTURE_MODES = frozenset({"snapshot", "unattended_session"})
_HYPERLIQUID_OFFICIAL_DATASET_SCOPES = {
    "market_data_l2_book": "official_hyperliquid_l2_book_snapshots",
    "asset_ctxs": "official_hyperliquid_asset_contexts",
    "node_fills_by_block": "official_hyperliquid_node_fills_by_block",
    "node_fills": "official_hyperliquid_node_fills_legacy",
    "node_trades": "official_hyperliquid_node_trades_legacy",
}
_HYPERLIQUID_OFFICIAL_DATASET_ALIASES = {
    "market_data": "market_data_l2_book",
    "l2book": "market_data_l2_book",
    "l2_book": "market_data_l2_book",
    "l2_books": "market_data_l2_book",
    "asset_ctx": "asset_ctxs",
    "asset_contexts": "asset_ctxs",
    "node_fill_by_block": "node_fills_by_block",
    "node_fills_by_block": "node_fills_by_block",
    "node_fills": "node_fills",
    "node_trades": "node_trades",
}
_HYPERLIQUID_UNSUPPORTED_OFFICIAL_DATASET_HINTS = (
    "candle",
    "candles",
    "ohlcv",
    "kline",
    "klines",
    "spot_asset",
    "spot_assets",
)


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
    if job.kind == WorkerJobKind.BINANCE_DERIVATIVES_CONTEXT_BACKFILL:
        return _run_binance_derivatives_context_backfill_job(
            job=job,
            store=store,
            worker_id=worker_id,
        )
    raise ValueError(f"unsupported collector job kind: {job.kind.value}")


def _run_universe_refresh_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    source_mode = _universe_source_mode(spec)
    if source_mode == "existing_ref":
        return _run_existing_universe_ref_job(job=job, store=store, worker_id=worker_id)
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
    if source_mode == "existing_ref":
        return _run_existing_archive_ref_job(job=job, store=store, worker_id=worker_id)
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


def _run_existing_universe_ref_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    archive_root = Path(_required_str(spec, "archive_root")).resolve(strict=False)
    if not archive_root.is_dir():
        raise ValueError("universe_refresh source=existing_ref requires an existing archive_root")
    snapshot_id = _required_str(spec, "universe_snapshot_id")
    if len(snapshot_id) != 64:
        raise ValueError("universe_snapshot_id must be 64 hex characters")
    expected_instrument = str(spec.get("instrument_id", "")).strip()
    expected_mode = UniverseMode(str(spec.get("mode", UniverseMode.AS_OF.value)))
    expected_asof_date = (
        _parse_date(str(spec["asof_date"]))
        if isinstance(spec.get("asof_date"), str) and spec.get("asof_date")
        else None
    )
    evidence_mode = str(spec.get("evidence_mode", "accepted_research")).strip().lower()
    rows = [
        row
        for row in load_universe_rows(archive_root)
        if row.snapshot_id == snapshot_id
    ]
    if not rows:
        raise ValueError(f"universe_snapshot_not_found: {snapshot_id}")
    if any(row.universe_mode != expected_mode for row in rows):
        raise ValueError(f"universe_snapshot_mode_mismatch: {expected_mode.value}")
    if expected_asof_date is not None and any(row.asof_date != expected_asof_date for row in rows):
        raise ValueError(f"universe_snapshot_asof_date_mismatch: {expected_asof_date.isoformat()}")
    checked_rows = rows
    if expected_instrument:
        checked_rows = [row for row in rows if row.instrument_id == expected_instrument]
        if len(checked_rows) != 1:
            raise ValueError(f"instrument_not_in_universe_snapshot: {expected_instrument}")
    if evidence_mode in {"accepted_research", "reported_evidence"}:
        for row in checked_rows:
            if row.universe_mode != UniverseMode.AS_OF:
                raise ValueError("existing_ref accepted evidence requires as_of universe")
            if row.evidence_scope != "accepted_research":
                raise ValueError(f"universe_evidence_scope_not_accepted: {row.evidence_scope}")
            if not row.accepted_research_evidence_allowed:
                raise ValueError(f"instrument_not_evidence_allowed: {row.instrument_id}")
    raw_file_ids = tuple(dict.fromkeys(row.raw_file_id for row in rows))
    raw_payload_hashes = tuple(dict.fromkeys(row.raw_payload_sha256 for row in rows))
    output_refs = [
        "source_mode=existing_ref",
        "universe_ref_checked=true",
        f"universe_snapshot_id={snapshot_id}",
        f"universe_mode={expected_mode.value}",
        f"instrument_count={len(rows)}",
        f"eligible_count={sum(1 for row in rows if row.eligible)}",
        f"accepted_evidence_allowed_count={sum(1 for row in rows if row.accepted_research_evidence_allowed)}",
        f"raw_file_ids={_csv(raw_file_ids)}",
        f"raw_payload_sha256s={_csv(raw_payload_hashes)}",
    ]
    if expected_instrument:
        output_refs.append(f"instrument_id={expected_instrument}")
    archive_refs = (
        f"universe_snapshot_id={snapshot_id}",
        f"raw_file_ids={_csv(raw_file_ids)}",
        "universe_ref_checked=true",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=tuple(output_refs),
        archive_manifest_refs=archive_refs,
        reason="universe_refresh_existing_ref_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_existing_archive_ref_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    archive_root = Path(_required_str(spec, "archive_root")).resolve(strict=False)
    if not archive_root.is_dir():
        raise ValueError("recent_candle_bootstrap source=existing_ref requires an existing archive_root")
    snapshot_id = _required_str(spec, "archive_snapshot_id")
    if len(snapshot_id) != 64:
        raise ValueError("archive_snapshot_id must be 64 hex characters")
    layout = ArchiveLayout(archive_root)
    manifest_store = ArchiveManifestStore(layout)
    snapshots = [
        snapshot
        for snapshot in manifest_store.load_archive_snapshots()
        if snapshot.archive_snapshot_id == snapshot_id
    ]
    if len(snapshots) != 1:
        raise ValueError(f"archive_snapshot_not_found: {snapshot_id}")
    snapshot = snapshots[0]
    if snapshot.layer != ArchiveLayer.SILVER:
        raise ValueError("archive_snapshot_layer_not_silver")
    venue = str(spec.get("venue", "")).strip()
    if venue and snapshot.venue_scope not in {venue, "all", "*"}:
        raise ValueError(f"archive_snapshot_venue_scope_mismatch: {snapshot.venue_scope}")
    start_ts = _optional_datetime(spec.get("start_ts"))
    end_ts = _optional_datetime(spec.get("end_ts"))
    if start_ts is not None and snapshot.start_ts > start_ts:
        raise ValueError("archive_snapshot_window_starts_after_requested_start")
    if end_ts is not None and snapshot.end_ts < end_ts:
        raise ValueError("archive_snapshot_window_ends_before_requested_end")
    included_file_ids = set(snapshot.included_file_ids)
    if not included_file_ids:
        raise ValueError("archive_snapshot_has_no_included_files")
    family = str(spec.get("family", spec.get("datatype", "bars"))).strip()
    instrument_id = str(spec.get("instrument_id", "")).strip()
    timeframe = str(spec.get("timeframe", "")).strip()
    included_rows = [
        row
        for row in manifest_store.load_file_manifest()
        if row.file_id in included_file_ids and row.layer == ArchiveLayer.SILVER
    ]
    matching_rows = [
        row
        for row in included_rows
        if (not venue or row.venue == venue)
        and (not family or row.datatype == family)
        and (not instrument_id or row.instrument_id == instrument_id)
        and (not timeframe or row.timeframe == timeframe)
    ]
    if not matching_rows:
        raise ValueError("archive_snapshot_no_matching_silver_files")
    missing_paths = [
        row.path
        for row in matching_rows
        if not layout.resolve(row.path).is_file()
    ]
    if missing_paths:
        raise ValueError("archive_snapshot_file_missing: " + ",".join(missing_paths))
    silver_file_ids = tuple(row.file_id for row in matching_rows)
    output_refs = (
        "collector_mode=existing_archive_ref_check",
        "source_mode=existing_ref",
        "archive_ref_checked=true",
        f"archive_snapshot_id={snapshot.archive_snapshot_id}",
        f"source_layer={snapshot.layer.value}",
        f"venue_scope={snapshot.venue_scope}",
        f"snapshot_start_ts={utc_isoformat(snapshot.start_ts)}",
        f"snapshot_end_ts={utc_isoformat(snapshot.end_ts)}",
        f"matching_file_count={len(matching_rows)}",
        f"silver_file_ids={_csv(silver_file_ids)}",
    )
    archive_refs = (
        f"archive_snapshot_id={snapshot.archive_snapshot_id}",
        f"silver_file_ids={_csv(silver_file_ids)}",
        "archive_ref_checked=true",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="recent_candle_bootstrap_existing_ref_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
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


def _run_binance_derivatives_context_backfill_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    source = str(spec.get("source", "public_api")).strip()
    if source not in {"public_api", "fixture_payloads"}:
        raise ValueError("binance derivatives context source must be public_api or fixture_payloads")
    get_client = (
        _binance_derivatives_fixture_get(spec)
        if source == "fixture_payloads"
        else None
    )
    result = run_binance_derivatives_context_backfill(
        archive_root=_required_str(spec, "archive_root"),
        family=_required_str(spec, "family"),
        symbol=_required_str(spec, "symbol"),
        instrument_id=_required_str(spec, "instrument_id"),
        start_time_ms=_optional_int(spec.get("start_time_ms")),
        end_time_ms=_optional_int(spec.get("end_time_ms")),
        interval=spec.get("interval"),
        period=spec.get("period"),
        limit=_optional_int(spec.get("limit")),
        max_pages=int(spec.get("max_pages", 10)),
        universe_snapshot_ref=_required_str(spec, "universe_snapshot_ref"),
        source_registry_ref=_required_str(spec, "source_registry_ref"),
        symbol_map_ref=_required_str(spec, "symbol_map_ref"),
        archive_snapshot_ref=spec.get("archive_snapshot_ref"),
        base_url=str(spec.get("base_url", "https://fapi.binance.com")),
        contract_type=spec.get("contract_type", "PERPETUAL"),
        get=get_client,
        max_bytes=int(spec.get("max_bytes", 10 * 1024 * 1024)),
        coverage_min=float(spec.get("coverage_min", 0.98)),
    )
    blocker_text = ",".join(result.blocker_reasons)
    output_refs = (
        "job_kind=binance_derivatives_context_backfill",
        "collector_mode=binance_derivatives_context_backfill",
        f"source_mode={source}",
        f"family={result.family.value}",
        f"symbol={result.symbol}",
        f"instrument_id={result.instrument_id}",
        f"backfill_status={result.status.value}",
        f"accepted_for_research_reporting={str(result.accepted_for_research_reporting).lower()}",
        f"page_result_id={result.page_result_id}",
        f"archive_ingest_id={result.archive_ingest_id}",
        f"coverage_report_id={result.coverage_report_id}",
        f"coverage_report_ref={result.coverage_report_ref}",
        f"blocker_reasons={blocker_text}",
    )
    archive_refs = (
        f"page_result_id={result.page_result_id}",
        f"archive_ingest_id={result.archive_ingest_id}",
        f"coverage_report_id={result.coverage_report_id}",
        f"coverage_report_ref={result.coverage_report_ref}",
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="binance_derivatives_context_backfill_succeeded",
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
    source = str(spec.get("source", "")).strip()
    if _is_candle_datatype(spec.get("datatype")) and source == "public_websocket":
        return _run_public_websocket_candle_capture_job(
            job=job,
            store=store,
            worker_id=worker_id,
        )
    if _is_candle_datatype(spec.get("datatype")) and _has_record_source(spec):
        return _run_websocket_candle_batch_archive_job(
            job=job,
            store=store,
            worker_id=worker_id,
        )
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


def _run_public_websocket_candle_capture_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    if _has_record_source(spec):
        raise ValueError("public websocket candle capture cannot mix source=public_websocket with local records")
    source_registry_source_id = _require_public_websocket_source_registry(
        spec,
        expected_source_id="hyperliquid_ws_candle",
    )
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    timeframe = str(spec.get("timeframe", "1m"))
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    coin = _hyperliquid_coin_from_spec(spec, instrument_id=instrument_id)
    max_messages = int(spec.get("max_public_ws_messages", 20))
    max_rows = int(spec.get("max_public_ws_rows", 200))
    max_seconds = float(spec.get("max_public_ws_seconds", spec.get("public_ws_timeout", 20.0)))
    capture_mode = _public_websocket_capture_mode(spec)
    session_started_at = utc_now()
    if capture_mode == "unattended_session":
        store.heartbeat(
            job.job_id,
            worker_id=worker_id,
            details={"phase": "public_websocket_capture_session", "stream": "candle"},
        )
    fetch = HyperliquidWebSocketClient(
        ws_url=str(spec.get("public_ws_url", "wss://api.hyperliquid.xyz/ws")),
        timeout=float(spec.get("public_ws_timeout", max_seconds)),
    ).fetch_candle_snapshot(
        coin=coin,
        interval=timeframe,
        max_messages=max_messages,
        max_rows=max_rows,
        max_seconds=max_seconds,
    )
    records = _public_websocket_candle_records(
        fetch.payload,
        instrument_id=instrument_id,
        timeframe=timeframe,
        max_rows=max_rows,
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
        adapter_id=fetch.capability.adapter_id,
        source_endpoint_or_subscription=fetch.raw_request.source,
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
    session_refs = _record_public_websocket_capture_session(
        archive_root=archive_root,
        job_id=job.job_id,
        worker_id=worker_id,
        capture_mode=capture_mode,
        stream="candle",
        datatype="candles",
        instrument_id=instrument_id,
        coin=coin,
        started_at=session_started_at,
        fetch=fetch,
        normalized_row_count=raw_file.row_count or 0,
        archive_refs=archive_refs,
        max_messages=max_messages,
        max_rows=max_rows,
        max_seconds=max_seconds,
        timeframe=timeframe,
    )
    if session_refs:
        store.heartbeat(
            job.job_id,
            worker_id=worker_id,
            details={"phase": "public_websocket_capture_session_archived", "stream": "candle"},
        )
    output_refs = (
        _public_websocket_candle_collector_mode(capture_mode),
        "source_mode=public_websocket",
        f"source_registry_source_id={source_registry_source_id}",
        f"capture_mode={capture_mode}",
        f"continuous_capture={str(capture_mode == 'unattended_session').lower()}",
        "accepted_historical_coverage_proof=false",
        _public_websocket_caveat_ref(capture_mode, snapshot_key="websocket_candle_snapshot_caveat"),
        f"datatype={_candle_datatype_value(spec.get('datatype'))}",
        f"row_count={raw_file.row_count or 0}",
        f"ws_message_count={len(fetch.payload)}",
        f"ws_candle_row_count={fetch.raw_response.row_count}",
        f"venue_adapter_id={fetch.capability.adapter_id}",
        f"source_endpoint_or_subscription={fetch.raw_request.source}",
        f"raw_request_id={fetch.raw_request.request_id}",
        f"raw_response_id={fetch.raw_response.response_id}",
        f"raw_payload_sha256={fetch.raw_response.raw_payload_sha256}",
        f"coin={coin}",
        f"interval={timeframe}",
        f"max_public_ws_messages={max_messages}",
        f"max_public_ws_rows={max_rows}",
        f"max_public_ws_seconds={max_seconds}",
        "gap_evidence_recorded=false",
        *session_refs,
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="websocket_candle_public_snapshot_archive_write_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_websocket_candle_batch_archive_job(
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
    records, source_refs, source_endpoint = _collector_records(
        spec,
        default_source_endpoint="local_records/websocket/candles",
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
        adapter_id=str(spec.get("adapter_id", "local_websocket_candle_batch_v1")),
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
    gap_record_ids: tuple[str, ...] = ()
    gap_refs: tuple[str, ...] = ()
    reconnect_attempts = int(spec.get("reconnect_attempts", 0))
    backoff_seconds = int(spec.get("backoff_seconds", 0))
    gap_reason = str(spec.get("gap_reason", "")).strip()
    if gap_reason or reconnect_attempts > 0:
        gap = store.record_gap(
            job_id=job.job_id,
            kind=job.kind,
            reason=gap_reason or "websocket_candle_batch_reconnect_recorded",
            worker_id=worker_id,
            start_ts=start_ts,
            end_ts=end_ts,
            backoff_seconds=backoff_seconds,
            reconnect_attempts=reconnect_attempts,
        )
        gap_record_ids = (gap.gap_record_id,)
        gap_refs = (f"gap_record_id={gap.gap_record_id}",)
    output_refs = (
        "collector_mode=websocket_candle_batch_archive_write",
        "source_mode=local_records",
        "continuous_capture=false",
        "accepted_historical_coverage_proof=false",
        "websocket_candle_batch_caveat=bounded_batch_not_unattended_continuous_capture",
        f"source_endpoint_or_subscription={source_endpoint}",
        f"row_count={raw_file.row_count or 0}",
        f"timeframe={timeframe}",
        *source_refs,
        *gap_refs,
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        gap_record_ids=gap_record_ids,
        reason="websocket_candle_batch_archive_write_succeeded",
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
        if datatype == MicrostructureDataType.TRADES:
            return _run_public_websocket_trade_capture_job(
                job=job,
                store=store,
                worker_id=worker_id,
                datatype=datatype,
            )
        return _run_public_websocket_l2_bbo_capture_job(
            job=job,
            store=store,
            worker_id=worker_id,
            datatype=datatype,
        )
    if source_mode == "official_s3_node_trade_replay":
        return _run_official_s3_node_trade_replay_job(
            job=job,
            store=store,
            worker_id=worker_id,
            datatype=datatype,
        )
    if source_mode == "official_s3_l2_replay":
        return _run_official_s3_l2_replay_job(
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


def _run_official_s3_l2_replay_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
    datatype: MicrostructureDataType,
) -> WorkerRunResult:
    if datatype not in {MicrostructureDataType.BBO, MicrostructureDataType.L2}:
        raise ValueError("official_s3_l2_replay only supports datatype bbo or l2")
    spec = job.input_spec
    official_dataset = _canonical_hyperliquid_official_dataset(
        str(spec.get("official_dataset", "market_data_l2_book"))
    )
    if official_dataset != "market_data_l2_book":
        raise ValueError("official_s3_l2_replay requires official_dataset=market_data_l2_book")
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    records_path = _resolve_records_file(spec)
    payloads = _read_records_file(
        records_path,
        records_format=str(spec.get("records_format", "auto")),
    )
    records = [
        row
        for payload in payloads
        for row in _public_l2_book_microstructure_records(
            payload,
            datatype=datatype,
            instrument_id=instrument_id,
            source="official_s3/market_data_l2_book",
        )
    ]
    if not records:
        raise ValueError("official_s3_l2_replay payloads produced no rows")
    source_endpoint = str(
        spec.get("source_endpoint_or_subscription", "official_s3/market_data_l2_book")
    )
    capture = write_microstructure_raw_capture(
        archive_root=archive_root,
        records=records,
        venue=str(spec.get("venue", "hyperliquid")),
        datatype=datatype,
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=str(spec.get("adapter_id", "hyperliquid_official_s3_l2_replay_v1")),
        source_endpoint_or_subscription=source_endpoint,
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
        "collector_mode=official_s3_l2_replay_capture",
        "source_mode=official_s3_l2_replay",
        f"datatype={datatype.value}",
        f"row_count={capture.raw_file.row_count or 0}",
        f"payload_count={len(payloads)}",
        f"official_dataset={official_dataset}",
        f"official_dataset_scope={_HYPERLIQUID_OFFICIAL_DATASET_SCOPES[official_dataset]}",
        f"records_file_sha256={file_sha256(records_path)}",
        f"records_file_row_count={len(payloads)}",
        f"source_endpoint_or_subscription={source_endpoint}",
        "official_s3_network_download=false",
        "official_s3_l2_replay_caveat=trusted_decompressed_payloads_not_continuous_coverage",
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
        reason=f"{datatype.value}_official_s3_l2_replay_capture_succeeded",
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
    source_registry_source_id = _require_public_websocket_source_registry(
        spec,
        expected_source_id="hyperliquid_ws_trades",
    )
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    coin = _hyperliquid_coin_from_spec(spec, instrument_id=instrument_id)
    max_messages = int(spec.get("max_public_ws_messages", 20))
    max_rows = int(spec.get("max_public_ws_rows", 200))
    max_seconds = float(spec.get("max_public_ws_seconds", spec.get("public_ws_timeout", 20.0)))
    capture_mode = _public_websocket_capture_mode(spec)
    session_started_at = utc_now()
    if capture_mode == "unattended_session":
        store.heartbeat(
            job.job_id,
            worker_id=worker_id,
            details={"phase": "public_websocket_capture_session", "stream": "trades"},
        )
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
    session_refs = _record_public_websocket_capture_session(
        archive_root=archive_root,
        job_id=job.job_id,
        worker_id=worker_id,
        capture_mode=capture_mode,
        stream="trades",
        datatype=datatype.value,
        instrument_id=instrument_id,
        coin=coin,
        started_at=session_started_at,
        fetch=fetch,
        normalized_row_count=capture.raw_file.row_count or 0,
        archive_refs=archive_refs,
        max_messages=max_messages,
        max_rows=max_rows,
        max_seconds=max_seconds,
    )
    if session_refs:
        store.heartbeat(
            job.job_id,
            worker_id=worker_id,
            details={"phase": "public_websocket_capture_session_archived", "stream": "trades"},
        )
    output_refs = (
        _public_websocket_trade_collector_mode(capture_mode),
        "source_mode=public_websocket",
        f"source_registry_source_id={source_registry_source_id}",
        f"capture_mode={capture_mode}",
        f"continuous_capture={str(capture_mode == 'unattended_session').lower()}",
        "accepted_historical_coverage_proof=false",
        _public_websocket_caveat_ref(capture_mode, snapshot_key="websocket_trade_snapshot_caveat"),
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
        *session_refs,
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


def _run_public_websocket_l2_bbo_capture_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
    datatype: MicrostructureDataType,
) -> WorkerRunResult:
    if datatype not in {MicrostructureDataType.BBO, MicrostructureDataType.L2}:
        raise ValueError("public websocket BBO/L2 capture only supports datatype bbo or l2")
    spec = job.input_spec
    source_registry_source_id = _require_public_websocket_source_registry(
        spec,
        expected_source_id=(
            "hyperliquid_ws_bbo"
            if datatype == MicrostructureDataType.BBO
            else "hyperliquid_ws_l2_book"
        ),
    )
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    coin = _hyperliquid_coin_from_spec(spec, instrument_id=instrument_id)
    max_messages = int(spec.get("max_public_ws_messages", 20))
    max_rows = int(spec.get("max_public_ws_rows", 200))
    max_seconds = float(spec.get("max_public_ws_seconds", spec.get("public_ws_timeout", 20.0)))
    capture_mode = _public_websocket_capture_mode(spec)
    session_started_at = utc_now()
    if capture_mode == "unattended_session":
        store.heartbeat(
            job.job_id,
            worker_id=worker_id,
            details={"phase": "public_websocket_capture_session", "stream": datatype.value},
        )
    client = HyperliquidWebSocketClient(
        ws_url=str(spec.get("public_ws_url", "wss://api.hyperliquid.xyz/ws")),
        timeout=float(spec.get("public_ws_timeout", max_seconds)),
    )
    if datatype == MicrostructureDataType.BBO:
        fetch = client.fetch_bbo_snapshot(
            coin=coin,
            max_messages=max_messages,
            max_rows=max_rows,
            max_seconds=max_seconds,
        )
        records = _public_websocket_bbo_records(
            fetch.payload,
            instrument_id=instrument_id,
            max_rows=max_rows,
        )
        stream_row_ref = f"ws_bbo_row_count={fetch.raw_response.row_count}"
        aggregation_refs: tuple[str, ...] = ()
    else:
        n_sig_figs = _optional_l2_book_n_sig_figs(spec)
        mantissa = _optional_int(spec.get("mantissa"))
        fetch = client.fetch_l2_book_snapshot(
            coin=coin,
            n_sig_figs=n_sig_figs,
            mantissa=mantissa,
            max_messages=max_messages,
            max_rows=max_rows,
            max_seconds=max_seconds,
        )
        records = _public_websocket_l2_book_records(
            fetch.payload,
            instrument_id=instrument_id,
            max_rows=max_rows,
        )
        stream_row_ref = f"ws_l2_book_row_count={fetch.raw_response.row_count}"
        aggregation_refs = _l2_book_aggregation_refs(n_sig_figs=n_sig_figs, mantissa=mantissa)
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
    session_refs = _record_public_websocket_capture_session(
        archive_root=archive_root,
        job_id=job.job_id,
        worker_id=worker_id,
        capture_mode=capture_mode,
        stream="bbo" if datatype == MicrostructureDataType.BBO else "l2Book",
        datatype=datatype.value,
        instrument_id=instrument_id,
        coin=coin,
        started_at=session_started_at,
        fetch=fetch,
        normalized_row_count=capture.raw_file.row_count or 0,
        archive_refs=archive_refs,
        max_messages=max_messages,
        max_rows=max_rows,
        max_seconds=max_seconds,
    )
    if session_refs:
        store.heartbeat(
            job.job_id,
            worker_id=worker_id,
            details={"phase": "public_websocket_capture_session_archived", "stream": datatype.value},
        )
    output_refs = (
        _public_websocket_l2_bbo_collector_mode(capture_mode),
        "source_mode=public_websocket",
        f"source_registry_source_id={source_registry_source_id}",
        f"capture_mode={capture_mode}",
        f"continuous_capture={str(capture_mode == 'unattended_session').lower()}",
        "accepted_historical_coverage_proof=false",
        _public_websocket_caveat_ref(
            capture_mode,
            snapshot_key="public_websocket_l2_bbo_snapshot_caveat",
        ),
        f"datatype={datatype.value}",
        f"row_count={capture.raw_file.row_count or 0}",
        f"ws_message_count={len(fetch.payload)}",
        stream_row_ref,
        f"venue_adapter_id={fetch.capability.adapter_id}",
        f"source_endpoint_or_subscription={fetch.raw_request.source}",
        f"raw_request_id={fetch.raw_request.request_id}",
        f"raw_response_id={fetch.raw_response.response_id}",
        f"raw_payload_sha256={fetch.raw_response.raw_payload_sha256}",
        f"coin={coin}",
        *aggregation_refs,
        f"max_public_ws_messages={max_messages}",
        f"max_public_ws_rows={max_rows}",
        f"max_public_ws_seconds={max_seconds}",
        f"storage_total_bytes={capture.storage_report.total_bytes}",
        f"storage_within_budget={str(capture.storage_report.within_budget).lower()}",
        "gap_evidence_recorded=false",
        *session_refs,
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason=f"{datatype.value}_public_websocket_l2_bbo_snapshot_capture_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _run_official_s3_node_trade_replay_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
    datatype: MicrostructureDataType,
) -> WorkerRunResult:
    if datatype != MicrostructureDataType.TRADES:
        raise ValueError("official_s3_node_trade_replay only supports datatype trades")
    spec = job.input_spec
    official_dataset = _canonical_hyperliquid_official_dataset(
        str(spec.get("official_dataset", ""))
    )
    allowed_datasets = {"node_fills_by_block", "node_fills", "node_trades"}
    if official_dataset not in allowed_datasets:
        raise ValueError(
            "official_s3_node_trade_replay requires official_dataset=node_fills_by_block, "
            "node_fills, or node_trades"
        )
    archive_root = _required_str(spec, "archive_root")
    instrument_id = _required_str(spec, "instrument_id")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    coin = _hyperliquid_coin_from_spec(spec, instrument_id=instrument_id)
    records_path = _resolve_records_file(spec)
    payloads = _read_node_trade_payload_file(
        records_path,
        records_format=str(spec.get("records_format", "auto")),
    )
    rows, skipped_rows = _official_node_trade_rows(
        payloads,
        instrument_id=instrument_id,
        coin=coin,
        source=f"official_s3/{official_dataset}",
    )
    if not rows:
        raise ValueError("official_s3_node_trade_replay payloads produced no matching trade rows")
    source_endpoint = str(
        spec.get("source_endpoint_or_subscription", f"official_s3/{official_dataset}")
    )
    capture = write_microstructure_raw_capture(
        archive_root=archive_root,
        records=rows,
        venue=str(spec.get("venue", "hyperliquid")),
        datatype=datatype,
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=str(spec.get("adapter_id", "hyperliquid_official_s3_node_trade_replay_v1")),
        source_endpoint_or_subscription=source_endpoint,
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
        "collector_mode=official_s3_node_trade_replay_capture",
        "source_mode=official_s3_node_trade_replay",
        f"datatype={datatype.value}",
        f"row_count={capture.raw_file.row_count or 0}",
        f"trade_row_count={capture.raw_file.row_count or 0}",
        f"payload_count={len(payloads)}",
        f"skipped_row_count={skipped_rows}",
        f"official_dataset={official_dataset}",
        f"official_dataset_scope={_HYPERLIQUID_OFFICIAL_DATASET_SCOPES[official_dataset]}",
        f"records_file_sha256={file_sha256(records_path)}",
        f"records_file_row_count={len(payloads)}",
        f"source_endpoint_or_subscription={source_endpoint}",
        f"coin={coin}",
        "official_s3_network_download=false",
        "official_s3_node_trade_replay_caveat=trusted_decompressed_payloads_not_coverage_certification",
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
        reason="trades_official_s3_node_trade_replay_capture_succeeded",
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
    if str(spec.get("source", "")).strip() == "official_s3_asset_ctxs_replay":
        return _run_official_s3_asset_ctxs_replay_job(
            job=job,
            store=store,
            worker_id=worker_id,
        )
    venue = str(spec.get("venue", "hyperliquid"))
    adapter_id = str(spec.get("adapter_id", "official_s3_backfill_fixture_v1"))
    source_endpoint = str(
        spec.get("source_endpoint_or_subscription", "official_s3_backfill_fixture")
    )
    official_refs = _official_s3_scope_refs(
        spec,
        venue=venue,
        source_endpoint_or_subscription=source_endpoint,
        source_file=_required_str(spec, "source_file"),
    )
    raw_file, storage_report = preserve_official_s3_backfill_file(
        archive_root=_required_str(spec, "archive_root"),
        source_file=_required_str(spec, "source_file"),
        trusted_source_root=_required_str(spec, "trusted_source_root"),
        venue=venue,
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=adapter_id,
        source_endpoint_or_subscription=source_endpoint,
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
        f"venue_adapter_id={adapter_id}",
        f"source_endpoint_or_subscription={source_endpoint}",
        f"raw_file_sha256={raw_file.sha256}",
        *official_refs,
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


def _run_official_s3_asset_ctxs_replay_job(
    *,
    job: WorkerJobRecord,
    store: WorkerJobStore,
    worker_id: str,
) -> WorkerRunResult:
    spec = job.input_spec
    venue = str(spec.get("venue", "hyperliquid"))
    if venue.lower() != "hyperliquid":
        raise ValueError("official_s3_asset_ctxs_replay only supports venue=hyperliquid")
    if "records" in spec and spec.get("records") is not None:
        raise ValueError("official_s3_backfill source=official_s3_asset_ctxs_replay cannot include records")
    if not spec.get("records_file"):
        raise ValueError("official_s3_backfill source=official_s3_asset_ctxs_replay requires records_file")
    explicit_dataset = str(spec.get("official_dataset", "")).strip()
    if not explicit_dataset:
        raise ValueError("official_s3_asset_ctxs_replay requires official_dataset=asset_ctxs")
    official_dataset = _canonical_hyperliquid_official_dataset(explicit_dataset)
    if official_dataset != "asset_ctxs":
        raise ValueError("official_s3_asset_ctxs_replay requires official_dataset=asset_ctxs")
    archive_root = _required_str(spec, "archive_root")
    start_ts = _parse_datetime(_required_str(spec, "start_ts"))
    end_ts = _parse_datetime(_required_str(spec, "end_ts"))
    records_path = _resolve_records_file(spec)
    records = _read_asset_context_records_file(
        records_path,
        records_format=str(spec.get("records_format", "auto")),
    )
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_store = ArchiveManifestStore(layout)
    adapter_id = str(spec.get("adapter_id", "hyperliquid_official_s3_asset_ctxs_replay_v1"))
    source_endpoint = str(
        spec.get("source_endpoint_or_subscription", "official_s3/asset_ctxs")
    )
    instrument_id = spec.get("instrument_id")
    if instrument_id is not None:
        instrument_id = str(instrument_id)
    raw_file = RawJsonlZstdWriter(layout, manifest_store).write_records(
        records=records,
        venue=venue,
        datatype="asset_contexts",
        date=_required_str(spec, "date"),
        run_id=str(spec.get("run_id", job.job_id)),
        job_id=job.job_id,
        adapter_id=adapter_id,
        source_endpoint_or_subscription=source_endpoint,
        symbols=_asset_context_symbols(spec, records),
        start_ts=start_ts,
        end_ts=end_ts,
        instrument_id=instrument_id,
        filename=str(spec.get("filename", "asset-contexts")),
    )
    bronze = raw_asset_contexts_to_bronze(
        archive_root=archive_root,
        raw_file_id=raw_file.file_id,
        job_id=f"{job.job_id}-bronze-asset-contexts",
        instrument_id=instrument_id,
    )
    silver = bronze_asset_contexts_to_silver(
        archive_root=archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id=f"{job.job_id}-silver-asset-contexts",
    )
    context_row_count = sum(row.row_count or 0 for row in silver.output_files)
    archive_refs = _market_data_archive_refs(
        raw_file_id=raw_file.file_id,
        bronze=bronze,
        silver=silver,
    )
    output_refs = (
        "collector_mode=official_s3_asset_ctxs_replay_archive_write",
        "source_mode=official_s3_asset_ctxs_replay",
        f"row_count={context_row_count}",
        f"raw_record_count={raw_file.row_count or 0}",
        f"context_row_count={context_row_count}",
        f"venue_adapter_id={adapter_id}",
        f"source_endpoint_or_subscription={source_endpoint}",
        f"official_dataset={official_dataset}",
        f"official_dataset_scope={_HYPERLIQUID_OFFICIAL_DATASET_SCOPES[official_dataset]}",
        f"records_file_sha256={file_sha256(records_path)}",
        f"records_file_row_count={len(records)}",
        "official_s3_network_download=false",
        "official_s3_asset_ctxs_replay_caveat=trusted_decompressed_payloads_not_continuous_coverage",
        *archive_refs,
    )
    record = store.succeed_job(
        job.job_id,
        worker_id=worker_id,
        output_refs=output_refs,
        archive_manifest_refs=archive_refs,
        reason="official_s3_asset_ctxs_replay_archive_write_succeeded",
    )
    return WorkerRunResult(
        job_id=job.job_id,
        status=record.status,
        output_refs=record.output_refs,
        archive_manifest_refs=record.archive_manifest_refs,
        gap_record_ids=record.gap_record_ids,
    )


def _official_s3_scope_refs(
    spec: dict[str, Any],
    *,
    venue: str,
    source_endpoint_or_subscription: str,
    source_file: str,
) -> tuple[str, ...]:
    explicit_dataset = str(spec.get("official_dataset", "")).strip()
    if venue.lower() != "hyperliquid":
        if explicit_dataset:
            return (f"official_dataset={explicit_dataset}",)
        return ()
    dataset = _hyperliquid_official_dataset(
        explicit_dataset=explicit_dataset,
        source_endpoint_or_subscription=source_endpoint_or_subscription,
        source_file=source_file,
    )
    return (
        "source_mode=trusted_local_official_file",
        f"official_dataset={dataset}",
        f"official_dataset_scope={_HYPERLIQUID_OFFICIAL_DATASET_SCOPES[dataset]}",
        "official_s3_network_download=false",
        "official_s3_research_caveat=raw_native_file_preserved_not_normalized_coverage_evidence",
    )


def _hyperliquid_official_dataset(
    *,
    explicit_dataset: str,
    source_endpoint_or_subscription: str,
    source_file: str,
) -> str:
    if explicit_dataset:
        return _canonical_hyperliquid_official_dataset(explicit_dataset)
    haystack = f"{source_endpoint_or_subscription} {source_file}".replace("\\", "/").lower()
    if "hyperliquid-archive/market_data" in haystack and "l2book" in haystack:
        return "market_data_l2_book"
    if "hyperliquid-archive/asset_ctxs" in haystack or "/asset_ctxs/" in haystack:
        return "asset_ctxs"
    if "hl-mainnet-node-data/node_fills_by_block" in haystack:
        return "node_fills_by_block"
    if "hl-mainnet-node-data/node_fills" in haystack:
        return "node_fills"
    if "hl-mainnet-node-data/node_trades" in haystack:
        return "node_trades"
    if any(hint in haystack for hint in _HYPERLIQUID_UNSUPPORTED_OFFICIAL_DATASET_HINTS):
        raise ValueError(
            "Hyperliquid official S3 dataset is not supported for v2 official_s3_backfill"
        )
    raise ValueError(
        "Hyperliquid official_s3_backfill requires official_dataset or an inferable official source path"
    )


def _canonical_hyperliquid_official_dataset(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace("/", "_")
    canonical = _HYPERLIQUID_OFFICIAL_DATASET_ALIASES.get(normalized, normalized)
    if canonical in _HYPERLIQUID_OFFICIAL_DATASET_SCOPES:
        return canonical
    if any(hint in canonical for hint in _HYPERLIQUID_UNSUPPORTED_OFFICIAL_DATASET_HINTS):
        raise ValueError(
            "Hyperliquid official S3 dataset is not supported for v2 official_s3_backfill"
        )
    allowed = ", ".join(sorted(_HYPERLIQUID_OFFICIAL_DATASET_SCOPES))
    raise ValueError(f"unsupported Hyperliquid official_dataset: {value}; expected one of {allowed}")


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
        if source not in {"payload_file", "public_api", "existing_ref"}:
            raise ValueError("universe_refresh source must be payload_file, public_api, or existing_ref")
        if source == "payload_file" and not has_payload_file:
            raise ValueError("universe_refresh source=payload_file requires payload_file")
        if source == "public_api" and has_payload_file:
            raise ValueError("universe_refresh source=public_api cannot include payload_file")
        if source == "existing_ref":
            if has_payload_file:
                raise ValueError("universe_refresh source=existing_ref cannot include payload_file")
            if not spec.get("universe_snapshot_id"):
                raise ValueError("universe_refresh source=existing_ref requires universe_snapshot_id")
        return source
    if has_payload_file:
        return "payload_file"
    raise ValueError("universe_refresh job requires payload_file or source=public_api")


def _recent_candle_source_mode(spec: dict[str, Any]) -> str:
    source = str(spec.get("source", "")).strip()
    has_records = _has_record_source(spec)
    if not source:
        return "records" if has_records else "diagnostic"
    if source == "existing_ref":
        if has_records:
            raise ValueError("recent_candle_bootstrap source=existing_ref cannot include records")
        if not spec.get("archive_snapshot_id"):
            raise ValueError("recent_candle_bootstrap source=existing_ref requires archive_snapshot_id")
        return "existing_ref"
    if source == "public_api":
        if has_records:
            raise ValueError("recent_candle_bootstrap source=public_api cannot include records")
        return "public_api"
    if source not in {"records", "records_file", "inline"}:
        raise ValueError("recent_candle_bootstrap source must be public_api, existing_ref, records, or records_file")
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
        if datatype not in {MicrostructureDataType.TRADES, MicrostructureDataType.BBO, MicrostructureDataType.L2}:
            raise ValueError("microstructure source=public_websocket only supports datatype trades, bbo, or l2")
        if has_records:
            if datatype == MicrostructureDataType.TRADES:
                raise ValueError("websocket_trade_capture source=public_websocket cannot include records")
            raise ValueError("websocket_l2_bbo_capture source=public_websocket cannot include records")
        return "public_websocket"
    if source == "public_api":
        if datatype not in {MicrostructureDataType.BBO, MicrostructureDataType.L2}:
            raise ValueError("microstructure source=public_api only supports datatype bbo or l2")
        if has_records:
            raise ValueError("websocket_l2_bbo_capture source=public_api cannot include records")
        return "public_api"
    if source == "official_s3_l2_replay":
        if datatype not in {MicrostructureDataType.BBO, MicrostructureDataType.L2}:
            raise ValueError("microstructure source=official_s3_l2_replay only supports datatype bbo or l2")
        if "records" in spec and spec.get("records") is not None:
            raise ValueError("websocket_l2_bbo_capture source=official_s3_l2_replay cannot include records")
        if not spec.get("records_file"):
            raise ValueError("websocket_l2_bbo_capture source=official_s3_l2_replay requires records_file")
        return "official_s3_l2_replay"
    if source == "official_s3_node_trade_replay":
        if datatype != MicrostructureDataType.TRADES:
            raise ValueError("microstructure source=official_s3_node_trade_replay only supports datatype trades")
        if "records" in spec and spec.get("records") is not None:
            raise ValueError("websocket_trade_capture source=official_s3_node_trade_replay cannot include records")
        if not spec.get("records_file"):
            raise ValueError("websocket_trade_capture source=official_s3_node_trade_replay requires records_file")
        return "official_s3_node_trade_replay"
    if source not in {"records", "inline"}:
        raise ValueError(
            "microstructure capture source must be official_s3_l2_replay, "
            "official_s3_node_trade_replay, public_api, public_websocket, or records"
        )
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


def _binance_derivatives_fixture_get(
    spec: dict[str, Any],
) -> Any:
    payloads = spec.get("response_payloads")
    if not isinstance(payloads, list) or not payloads:
        raise ValueError("source=fixture_payloads requires non-empty response_payloads")
    index = {"value": 0}

    def get(_url: str) -> BinanceDerivativesContextGetResult:
        if index["value"] >= len(payloads):
            return BinanceDerivativesContextGetResult(error="fixture_payloads_exhausted")
        payload = payloads[index["value"]]
        index["value"] += 1
        return BinanceDerivativesContextGetResult(
            status_code=200,
            content=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        )

    return get


def _optional_l2_book_n_sig_figs(spec: dict[str, Any]) -> int | None:
    value = spec.get("n_sig_figs")
    if value is None and "nSigFigs" in spec:
        value = spec.get("nSigFigs")
    return _optional_int(value)


def _public_websocket_capture_mode(spec: dict[str, Any]) -> str:
    mode = str(spec.get("capture_mode", "snapshot")).strip() or "snapshot"
    if mode not in _PUBLIC_WEBSOCKET_CAPTURE_MODES:
        allowed = ", ".join(sorted(_PUBLIC_WEBSOCKET_CAPTURE_MODES))
        raise ValueError(f"public websocket capture_mode must be one of: {allowed}")
    return mode


def _require_public_websocket_source_registry(
    spec: dict[str, Any],
    *,
    expected_source_id: str,
) -> str:
    source_id = str(spec.get("source_registry_source_id", "")).strip()
    if not source_id:
        raise ValueError(
            "public_websocket source_registry_source_id is required "
            f"and must be {expected_source_id}"
        )
    if source_id != expected_source_id:
        raise ValueError(
            "public_websocket source_registry_source_id must be "
            f"{expected_source_id}, got {source_id}"
        )
    return source_id


def _public_websocket_candle_collector_mode(capture_mode: str) -> str:
    if capture_mode == "unattended_session":
        return "collector_mode=public_websocket_candle_capture_session_archive_write"
    return "collector_mode=public_websocket_candle_archive_write"


def _public_websocket_trade_collector_mode(capture_mode: str) -> str:
    if capture_mode == "unattended_session":
        return "collector_mode=public_websocket_trade_capture_session"
    return "collector_mode=public_websocket_trade_snapshot_capture"


def _public_websocket_l2_bbo_collector_mode(capture_mode: str) -> str:
    if capture_mode == "unattended_session":
        return "collector_mode=public_websocket_l2_bbo_capture_session"
    return "collector_mode=public_websocket_l2_bbo_snapshot_capture"


def _public_websocket_caveat_ref(capture_mode: str, *, snapshot_key: str) -> str:
    if capture_mode == "unattended_session":
        return (
            "public_websocket_capture_session_caveat="
            "bounded_unattended_public_stream_segment_not_historical_coverage_proof"
        )
    return f"{snapshot_key}=bounded_public_stream_snapshot_not_unattended_continuous_capture"


def _record_public_websocket_capture_session(
    *,
    archive_root: str,
    job_id: str,
    worker_id: str,
    capture_mode: str,
    stream: str,
    datatype: str,
    instrument_id: str,
    coin: str,
    started_at: datetime,
    fetch: Any,
    normalized_row_count: int,
    archive_refs: tuple[str, ...],
    max_messages: int,
    max_rows: int,
    max_seconds: float,
    timeframe: str | None = None,
) -> tuple[str, ...]:
    if capture_mode != "unattended_session":
        return ()
    finished_at = utc_now()
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    report = {
        "job_id": job_id,
        "worker_id": worker_id,
        "capture_mode": capture_mode,
        "source_mode": "public_websocket",
        "stream": stream,
        "datatype": datatype,
        "instrument_id": instrument_id,
        "coin": coin,
        "timeframe": timeframe,
        "started_at": utc_isoformat(started_at),
        "finished_at": utc_isoformat(finished_at),
        "venue_adapter_id": fetch.capability.adapter_id,
        "source_endpoint_or_subscription": fetch.raw_request.source,
        "raw_request_id": fetch.raw_request.request_id,
        "raw_response_id": fetch.raw_response.response_id,
        "raw_payload_sha256": fetch.raw_response.raw_payload_sha256,
        "ws_message_count": len(fetch.payload),
        "ws_source_row_count": fetch.raw_response.row_count,
        "normalized_row_count": normalized_row_count,
        "max_public_ws_messages": max_messages,
        "max_public_ws_rows": max_rows,
        "max_public_ws_seconds": max_seconds,
        "archive_refs": list(archive_refs),
        "continuous_capture": True,
        "continuous_capture_segment": True,
        "accepted_historical_coverage_proof": False,
        "capture_session_caveat": "bounded_unattended_public_stream_segment_not_historical_coverage_proof",
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
    }
    session_id = canonical_json_hash(report)
    report["capture_session_id"] = session_id
    report_path = layout.resolve(
        "manifests",
        "websocket_capture_sessions",
        f"{session_id}.json",
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    return (
        "unattended_capture_session=true",
        "continuous_capture_segment=true",
        f"capture_session_id={session_id}",
        f"capture_session_path={layout.relative_to_root(report_path)}",
    )


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


def _is_candle_datatype(value: Any) -> bool:
    return str(value or "").strip().lower() in {"candle", "candles"}


def _candle_datatype_value(value: Any) -> str:
    return "candles" if _is_candle_datatype(value) else str(value or "")


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


def _read_asset_context_records_file(path: Path, *, records_format: str) -> list[dict[str, Any]]:
    normalized = records_format.lower()
    if normalized == "auto":
        normalized = "json" if path.suffix.lower() == ".json" else "jsonl"
    if normalized == "json":
        return _asset_context_records_from_payload(json.loads(path.read_text(encoding="utf-8")))
    if normalized in {"jsonl", "ndjson"}:
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"collector JSONL asset_ctxs line {line_number} is invalid JSON") from exc
            records.extend(_asset_context_records_from_payload(payload))
        if not records:
            raise ValueError("collector JSONL asset_ctxs records_file must contain at least one payload")
        return records
    raise ValueError("records_format must be auto, json, jsonl, or ndjson")


def _read_node_trade_payload_file(path: Path, *, records_format: str) -> list[dict[str, Any]]:
    normalized = records_format.lower()
    if normalized == "auto":
        normalized = "json" if path.suffix.lower() == ".json" else "jsonl"
    if normalized == "json":
        return _node_trade_payloads_from_json(json.loads(path.read_text(encoding="utf-8")))
    if normalized in {"jsonl", "ndjson"}:
        payloads: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"collector JSONL node trade line {line_number} is invalid JSON") from exc
            payloads.extend(_node_trade_payloads_from_json(payload))
        if not payloads:
            raise ValueError("collector JSONL node trade records_file must contain at least one payload")
        return payloads
    raise ValueError("records_format must be auto, json, jsonl, or ndjson")


def _node_trade_payloads_from_json(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [dict(payload)]
    if isinstance(payload, list):
        return _coerce_record_rows(payload)
    raise ValueError("node trade payload must be an object or list of objects")


def _asset_context_records_from_payload(payload: Any) -> list[dict[str, Any]]:
    meta_context_record = _asset_context_meta_record(payload)
    if meta_context_record is not None:
        return [meta_context_record]
    if isinstance(payload, dict):
        return [dict(payload)]
    if isinstance(payload, list):
        if not payload:
            raise ValueError("asset_ctxs payload list must not be empty")
        return _coerce_record_rows(payload)
    raise ValueError("asset_ctxs payload must be an object, list of objects, or meta/context pair")


def _asset_context_meta_record(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[0], dict) and isinstance(payload[1], list):
        return _asset_context_record_from_meta(payload[0], payload[1])
    if isinstance(payload, dict) and "meta" in payload and "assetCtxs" in payload:
        return _asset_context_record_from_meta(payload["meta"], payload["assetCtxs"])
    if isinstance(payload, dict) and "universe" in payload and "asset_contexts" in payload:
        return _asset_context_record_from_meta(payload, payload["asset_contexts"])
    return None


def _asset_context_record_from_meta(meta: Any, contexts: Any) -> dict[str, Any]:
    if not isinstance(meta, dict):
        raise ValueError("asset_ctxs meta payload must be an object")
    if not isinstance(contexts, list):
        raise ValueError("asset_ctxs contexts payload must be a list")
    universe = meta.get("universe")
    universe_rows = universe if isinstance(universe, list) else []
    rows: list[dict[str, Any]] = []
    for index, context in enumerate(contexts):
        if not isinstance(context, dict):
            raise ValueError(f"asset_ctxs context[{index}] must be an object")
        row = dict(context)
        if index < len(universe_rows) and isinstance(universe_rows[index], dict):
            name = (
                universe_rows[index].get("name")
                or universe_rows[index].get("coin")
                or universe_rows[index].get("symbol")
                or universe_rows[index].get("s")
            )
            if name is not None and "name" not in row:
                row["name"] = str(name)
        rows.append(row)
    if not rows:
        raise ValueError("asset_ctxs contexts payload must contain at least one object")
    return {"contexts": rows}


def _asset_context_symbols(spec: dict[str, Any], records: list[dict[str, Any]]) -> tuple[str, ...]:
    explicit = spec.get("symbols")
    if explicit is not None:
        return _symbol_tuple(explicit)
    inferred = sorted(
        {
            str(symbol)
            for row in _iter_asset_context_rows(records)
            for symbol in (_asset_context_symbol(row),)
            if symbol is not None and str(symbol).strip()
        }
    )
    if inferred:
        return tuple(inferred)
    instrument_id = spec.get("instrument_id")
    if instrument_id is not None and str(instrument_id).strip():
        return (str(instrument_id),)
    return ("asset_ctxs",)


def _iter_asset_context_rows(records: list[dict[str, Any]]):
    for record in records:
        contexts = record.get("contexts")
        if isinstance(contexts, list):
            for item in contexts:
                if isinstance(item, dict):
                    yield item
            continue
        asset_contexts = record.get("asset_contexts")
        if isinstance(asset_contexts, list):
            for item in asset_contexts:
                if isinstance(item, dict):
                    yield item
            continue
        yield record


def _asset_context_symbol(row: dict[str, Any]) -> Any:
    for key in ("instrument_id", "symbol", "coin", "name", "s"):
        value = row.get(key)
        if value is not None:
            return value
    return None


def _symbol_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        symbols = tuple(part.strip() for part in value.split(",") if part.strip())
        if symbols:
            return symbols
    if isinstance(value, (list, tuple)):
        symbols = tuple(str(part).strip() for part in value if str(part).strip())
        if symbols:
            return symbols
    raise ValueError("symbols must be a non-empty string or list when provided")


def _coerce_record_rows(value: list[Any]) -> list[dict[str, Any]]:
    if not value:
        raise ValueError("collector records_file requires non-empty records")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"collector records_file[{index}] must be an object")
        rows.append(dict(item))
    return rows


def _official_node_trade_rows(
    payloads: list[dict[str, Any]],
    *,
    instrument_id: str,
    coin: str,
    source: str,
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    skipped = 0
    sequence = 0
    for payload in payloads:
        for item in _iter_node_trade_items(payload):
            item_coin = str(item.get("coin") or "").strip()
            if item_coin and item_coin != coin:
                skipped += 1
                continue
            rows.append(
                _official_node_trade_row(
                    item,
                    instrument_id=instrument_id,
                    sequence=sequence,
                    source=source,
                )
            )
            sequence += 1
    return rows, skipped


def _iter_node_trade_items(payload: dict[str, Any]):
    if _is_trade_like_payload(payload):
        yield payload
        return
    for key in ("fills", "trades", "data"):
        value = payload.get(key)
        if value is None:
            continue
        if not isinstance(value, list):
            raise ValueError(f"official node trade payload {key} must be a list")
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise ValueError(f"official node trade payload {key}[{index}] must be an object")
            row = dict(item)
            if row.get("time") is None and payload.get("time") is not None:
                row["time"] = payload["time"]
            yield row
        return
    raise ValueError("official node trade payload must contain trade fields or fills/trades/data list")


def _is_trade_like_payload(payload: dict[str, Any]) -> bool:
    return payload.get("px") is not None and payload.get("sz") is not None and (
        payload.get("time") is not None or payload.get("ts") is not None
    )


def _official_node_trade_row(
    item: dict[str, Any],
    *,
    instrument_id: str,
    sequence: int,
    source: str,
) -> dict[str, Any]:
    time_value = item.get("time")
    if time_value is None:
        time_value = item.get("ts")
    if time_value is None:
        raise ValueError("official node trade row is missing time")
    price = _positive_float(_required_trade_value(item, "px"), field="px")
    size = _positive_float(_required_trade_value(item, "sz"), field="sz")
    trade_id = _official_node_trade_id(item, instrument_id=instrument_id, time_value=time_value, sequence=sequence)
    return {
        "ts": _official_node_trade_datetime(time_value).isoformat(timespec="milliseconds"),
        "instrument_id": instrument_id,
        "event_type": "trade",
        "sequence": sequence,
        "price": price,
        "size": size,
        "side": str(item.get("side")) if item.get("side") is not None else None,
        "trade_id": trade_id,
        "source": source,
    }


def _official_node_trade_id(
    item: dict[str, Any],
    *,
    instrument_id: str,
    time_value: Any,
    sequence: int,
) -> str:
    tid = item.get("tid")
    if tid is not None:
        return f"{item.get('coin') or instrument_id}:{_official_node_trade_millis(time_value)}:{tid}"
    tx_hash = item.get("hash")
    if tx_hash is not None:
        return f"{tx_hash}:{sequence}"
    oid = item.get("oid")
    if oid is not None:
        return f"{item.get('coin') or instrument_id}:{_official_node_trade_millis(time_value)}:{oid}:{sequence}"
    return f"{instrument_id}:{_official_node_trade_millis(time_value)}:{sequence}"


def _official_node_trade_datetime(value: Any) -> datetime:
    if isinstance(value, str) and not value.isdigit():
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return _timestamp_datetime(value)


def _official_node_trade_millis(value: Any) -> int:
    return int(_official_node_trade_datetime(value).timestamp() * 1000)


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
    source: str = "public_api/info/l2Book",
) -> list[dict[str, Any]]:
    snapshot_ts = _public_l2_book_time(payload)
    bid_levels, ask_levels = _public_l2_book_levels(payload)
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


def _public_websocket_candle_records(
    payload: Any,
    *,
    instrument_id: str,
    timeframe: str,
    max_rows: int,
) -> list[dict[str, Any]]:
    if max_rows <= 0:
        raise ValueError("max_rows must be positive")
    messages = _coerce_public_websocket_messages(payload)
    rows: list[dict[str, Any]] = []
    for message in messages:
        if message.get("channel") != "candle":
            continue
        data = message.get("data")
        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            raise ValueError("public websocket candle message data must be an object or list")
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"public websocket candle data[{index}] must be an object")
            row = dict(item)
            row.setdefault("instrument_id", instrument_id)
            row.setdefault("i", timeframe)
            rows.append(row)
            if len(rows) >= max_rows:
                break
        if len(rows) >= max_rows:
            break
    if not rows:
        raise ValueError("public websocket candle returned no candle rows")
    return rows


def _public_websocket_bbo_records(
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
        if message.get("channel") != "bbo":
            continue
        data = message.get("data")
        if not isinstance(data, dict):
            raise ValueError("public websocket bbo message data must be an object")
        rows.append(
            _public_websocket_bbo_row(
                dict(data),
                instrument_id=instrument_id,
                sequence=sequence,
            )
        )
        sequence += 1
        if len(rows) >= max_rows:
            break
    if not rows:
        raise ValueError("public websocket bbo returned no rows")
    return rows


def _public_websocket_l2_book_records(
    payload: Any,
    *,
    instrument_id: str,
    max_rows: int,
) -> list[dict[str, Any]]:
    if max_rows <= 0:
        raise ValueError("max_rows must be positive")
    messages = _coerce_public_websocket_messages(payload)
    rows: list[dict[str, Any]] = []
    for message in messages:
        if message.get("channel") != "l2Book":
            continue
        data = message.get("data")
        if not isinstance(data, dict):
            raise ValueError("public websocket l2Book message data must be an object")
        rows.extend(
            _public_l2_book_microstructure_records(
                dict(data),
                datatype=MicrostructureDataType.L2,
                instrument_id=instrument_id,
                source="public_websocket/l2Book",
            )
        )
        if len(rows) >= max_rows:
            break
    if not rows:
        raise ValueError("public websocket l2Book returned no rows")
    return rows[:max_rows]


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


def _public_websocket_bbo_row(
    item: dict[str, Any],
    *,
    instrument_id: str,
    sequence: int,
) -> dict[str, Any]:
    ts = _public_websocket_book_time(item, label="bbo")
    bbo = item.get("bbo")
    if not isinstance(bbo, list) or len(bbo) < 2:
        raise ValueError("public websocket bbo message must contain bid and ask levels")
    best_bid = _public_websocket_bbo_level(bbo[0], side="bid")
    best_ask = _public_websocket_bbo_level(bbo[1], side="ask")
    return {
        "ts": ts.isoformat(),
        "instrument_id": instrument_id,
        "event_type": "bbo",
        "sequence": sequence,
        "bid": _l2_level_price(best_bid, side="bid", index=0),
        "ask": _l2_level_price(best_ask, side="ask", index=0),
        "bid_size": _l2_level_size(best_bid, side="bid", index=0),
        "ask_size": _l2_level_size(best_ask, side="ask", index=0),
        "source": "public_websocket/bbo",
    }


def _public_websocket_book_time(payload: dict[str, Any], *, label: str) -> datetime:
    value = payload.get("time")
    if value is None:
        value = payload.get("ts")
    if value is None:
        raise ValueError(f"public websocket {label} message is missing time")
    return _timestamp_datetime(value)


def _public_websocket_bbo_level(value: Any, *, side: str) -> dict[str, Any]:
    if value is None:
        raise ValueError(f"public websocket bbo {side} level is missing")
    if not isinstance(value, dict):
        raise ValueError(f"public websocket bbo {side} level must be an object")
    return dict(value)


def _l2_book_aggregation_refs(
    *,
    n_sig_figs: int | None,
    mantissa: int | None,
) -> tuple[str, ...]:
    refs: list[str] = []
    if n_sig_figs is not None:
        refs.append(f"nSigFigs={n_sig_figs}")
    if mantissa is not None:
        refs.append(f"mantissa={mantissa}")
    return tuple(refs)


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
