# V2-AUDIT-ID: V2-AUD-COLLECT-016
# V2-CONTRACTS: docs/contracts/collector_job_contract.md, docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, public_historical_dataset_collection, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_collectors
"""Bounded public historical perp dataset collection and validation."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import median
from typing import Any

import httpx
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter
from tradingbotsuite.v2.archive.rebuild import (
    bronze_candles_to_silver_bars,
    bronze_funding_to_silver,
    create_silver_market_data_snapshot,
    raw_candles_to_bronze,
    raw_funding_to_bronze,
)
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat
from tradingbotsuite.v2.data_quality.coverage import coverage_report_for_bars, timeframe_to_timedelta
from tradingbotsuite.v2.data_quality.reports import CoverageManifestStore
from tradingbotsuite.v2.data_quality.schemas import DEFAULT_COVERAGE_MIN, EvidenceMode
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.universe.hyperliquid import load_universe_rows, refresh_hyperliquid_universe
from tradingbotsuite.v2.universe.models import UniverseMode, UniverseRefreshResult, UniverseSnapshotRow
from tradingbotsuite.v2.venues.hyperliquid import (
    HYPERLIQUID_CANDLE_SNAPSHOT_SOURCE,
    HYPERLIQUID_FUNDING_HISTORY_SOURCE,
    HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID,
    HyperliquidInfoClient,
)

HISTORICAL_DATASET_REPORT_SCHEMA_VERSION = "historical_perp_dataset_report_v1"
DEFAULT_BINANCE_BASE_URL = "https://fapi.binance.com"
DEFAULT_MAX_INSTRUMENTS = 25
DEFAULT_BINANCE_CLOSE_DIFF_WARN_BPS = 250.0

BinanceKlineFetcher = Callable[[str, str, datetime, datetime], list[Mapping[str, Any]]]


class HistoricalPerpDatasetConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_root: str = Field(min_length=1)
    archive_root: str = Field(min_length=1)
    run_id: str = Field(default="v2-historical-perp-dataset", pattern=r"^[A-Za-z0-9_.-]+$")
    start_ts: datetime
    end_ts: datetime
    timeframe: str = "1d"
    asof_date: date
    min_day_notional_usd: int = Field(default=5_000_000, ge=1)
    max_instruments: int = Field(default=DEFAULT_MAX_INSTRUMENTS, ge=0)
    coins: tuple[str, ...] = ()
    coverage_min: float = Field(default=DEFAULT_COVERAGE_MIN, ge=0.0, le=1.0)
    public_info_url: str = Field(default="https://api.hyperliquid.xyz/info", min_length=1)
    public_info_timeout: float = Field(default=20.0, gt=0.0)
    max_public_info_pages: int = Field(default=50, ge=1, le=5_000)
    max_candles_per_public_page: int = Field(default=5_000, ge=1, le=5_000)
    include_funding: bool = False
    max_funding_pages: int = Field(default=100, ge=1, le=10_000)
    include_hip3_dexs: bool = False
    validate_binance: bool = True
    binance_base_url: str = Field(default=DEFAULT_BINANCE_BASE_URL, min_length=1)
    binance_timeout: float = Field(default=20.0, gt=0.0)
    binance_close_diff_warn_bps: float = Field(default=DEFAULT_BINANCE_CLOSE_DIFF_WARN_BPS, ge=0.0)
    created_by_id: str = "codex-manager-agent"
    evidence_mode: str = "sandbox_diagnostic"
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator("coins", mode="before")
    @classmethod
    def _normalize_coins(cls, value: Any) -> tuple[str, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            parts = [value]
        else:
            parts = list(value)
        return tuple(dict.fromkeys(str(part).strip().upper() for part in parts if str(part).strip()))

    @field_validator("evidence_mode")
    @classmethod
    def _sandbox_only(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized != EvidenceMode.SANDBOX_DIAGNOSTIC.value:
            raise ValueError("historical public collection must remain sandbox_diagnostic")
        return normalized

    @model_validator(mode="after")
    def _validate_config(self) -> "HistoricalPerpDatasetConfig":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        timeframe_to_timedelta(self.timeframe)
        require_research_boundary(self, context="historical perp dataset config")
        return self


class InstrumentCollectionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: str
    coin: str
    day_ntl_vlm_usd: float
    status: str = "collected"
    reason: str | None = None
    raw_file_id: str | None = None
    bronze_file_id: str | None = None
    silver_file_id: str | None = None
    coverage_report_id: str | None = None
    fetched_page_count: int = Field(default=0, ge=0)
    source_row_count: int = Field(default=0, ge=0)
    expected_rows: int = Field(default=0, ge=0)
    observed_rows: int = Field(default=0, ge=0)
    coverage_ratio: float = 0.0
    missing_timestamp_count: int = Field(default=0, ge=0)
    technical_coverage_pass: bool = False
    blocker_reasons: tuple[str, ...] = ()
    funding_status: str = "not_requested"
    funding_reason: str | None = None
    funding_raw_file_id: str | None = None
    funding_bronze_file_id: str | None = None
    funding_silver_file_id: str | None = None
    funding_row_count: int = Field(default=0, ge=0)


class BinanceValidationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: str
    coin: str
    binance_symbol: str | None = None
    status: str
    reason: str | None = None
    hyperliquid_rows: int = Field(default=0, ge=0)
    binance_rows: int = Field(default=0, ge=0)
    overlap_rows: int = Field(default=0, ge=0)
    median_abs_close_diff_bps: float | None = None
    p95_abs_close_diff_bps: float | None = None
    max_abs_close_diff_bps: float | None = None


class HistoricalPerpDatasetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = HISTORICAL_DATASET_REPORT_SCHEMA_VERSION
    run_id: str
    report_path: str
    archive_root: str
    output_root: str
    universe_snapshot_id: str
    archive_snapshot_id: str
    requested_start_ts: datetime
    requested_end_ts: datetime
    timeframe: str
    universe_mode: str = UniverseMode.CURRENT_LABELED_SANDBOX.value
    evidence_mode: str = EvidenceMode.SANDBOX_DIAGNOSTIC.value
    universe_eligible_count: int = Field(ge=0)
    selected_instrument_count: int = Field(ge=0)
    collected_instrument_count: int = Field(ge=0)
    technical_coverage_pass_count: int = Field(ge=0)
    min_coverage_ratio: float | None = None
    binance_checked_count: int = Field(ge=0)
    binance_pass_count: int = Field(ge=0)
    binance_warning_count: int = Field(ge=0)
    binance_skipped_count: int = Field(ge=0)
    funding_collected_count: int = Field(default=0, ge=0)
    funding_skipped_count: int = Field(default=0, ge=0)
    accepted_research_ready: bool = False
    current_universe_caveat: str = "current_public_universe_not_historical_asof"
    boundary_flags: dict[str, bool] = Field(default_factory=lambda: dict(RESEARCH_BOUNDARY))
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_result(self) -> "HistoricalPerpDatasetResult":
        if self.accepted_research_ready:
            raise ValueError("public current-universe collection cannot be accepted research ready")
        require_research_boundary(self, context="historical perp dataset result")
        return self


def collect_historical_perp_dataset(
    config: HistoricalPerpDatasetConfig | Mapping[str, Any],
    *,
    hyperliquid_client: Any | None = None,
    binance_fetcher: BinanceKlineFetcher | None = None,
) -> HistoricalPerpDatasetResult:
    parsed = (
        config
        if isinstance(config, HistoricalPerpDatasetConfig)
        else HistoricalPerpDatasetConfig.model_validate(dict(config))
    )
    output_root = Path(parsed.output_root).resolve(strict=False)
    archive_root = Path(parsed.archive_root).resolve(strict=False)
    output_root.mkdir(parents=True, exist_ok=True)
    layout = ArchiveLayout(archive_root)
    layout.initialize()

    client = hyperliquid_client or HyperliquidInfoClient(
        base_url=parsed.public_info_url,
        timeout=parsed.public_info_timeout,
    )
    universe = _refresh_current_public_universe(parsed, client=client)
    selected_rows = _selected_universe_rows(parsed, universe)
    if not selected_rows:
        raise ValueError("current public universe produced no selected eligible instruments")
    venue_symbols = _venue_symbols_by_instrument(archive_root)

    instrument_summaries: list[InstrumentCollectionSummary] = []
    binance_summaries: list[BinanceValidationSummary] = []
    for row in selected_rows:
        coin = venue_symbols.get(row.instrument_id, _coin_from_instrument(row.instrument_id))
        try:
            summary, hyperliquid_rows = _collect_one_instrument(parsed, row, client=client, coin=coin)
        except Exception as exc:
            summary = InstrumentCollectionSummary(
                instrument_id=row.instrument_id,
                coin=coin,
                day_ntl_vlm_usd=row.day_ntl_vlm_usd,
                status="skipped",
                reason=f"collection_failed:{exc}",
                blocker_reasons=("collection_failed",),
            )
            hyperliquid_rows = []
        instrument_summaries.append(summary)
        if parsed.validate_binance and hyperliquid_rows:
            binance_summaries.append(
                _validate_against_binance(
                    parsed,
                    row,
                    coin=coin,
                    hyperliquid_rows=hyperliquid_rows,
                    fetcher=binance_fetcher,
                )
            )
        elif parsed.validate_binance:
            binance_summaries.append(
                BinanceValidationSummary(
                    instrument_id=row.instrument_id,
                    coin=coin,
                    status="skipped",
                    reason=summary.reason or "hyperliquid_rows_unavailable",
                )
            )

    snapshot = create_silver_market_data_snapshot(
        archive_root=archive_root,
        venue_scope="hyperliquid",
        start_ts=parsed.start_ts,
        end_ts=parsed.end_ts,
        notes=f"{parsed.run_id}_current_public_historical_dataset_sandbox",
    )
    collected = [summary for summary in instrument_summaries if summary.status == "collected"]
    min_coverage = min((summary.coverage_ratio for summary in collected), default=None)
    report_path = output_root / f"{parsed.run_id}_historical_dataset_report.json"
    result = HistoricalPerpDatasetResult(
        run_id=parsed.run_id,
        report_path=str(report_path),
        archive_root=str(archive_root),
        output_root=str(output_root),
        universe_snapshot_id=universe.snapshot_id,
        archive_snapshot_id=snapshot.archive_snapshot_id,
        requested_start_ts=parsed.start_ts,
        requested_end_ts=parsed.end_ts,
        timeframe=parsed.timeframe,
        universe_eligible_count=_eligible_count(archive_root, universe.snapshot_id),
        selected_instrument_count=len(selected_rows),
        collected_instrument_count=len(collected),
        technical_coverage_pass_count=sum(1 for summary in collected if summary.technical_coverage_pass),
        min_coverage_ratio=min_coverage,
        binance_checked_count=sum(1 for summary in binance_summaries if summary.status in {"passed", "warning"}),
        binance_pass_count=sum(1 for summary in binance_summaries if summary.status == "passed"),
        binance_warning_count=sum(1 for summary in binance_summaries if summary.status == "warning"),
        binance_skipped_count=sum(1 for summary in binance_summaries if summary.status == "skipped"),
        funding_collected_count=sum(1 for summary in instrument_summaries if summary.funding_status == "collected"),
        funding_skipped_count=sum(1 for summary in instrument_summaries if summary.funding_status == "skipped"),
    )
    _write_report(
        path=report_path,
        config=parsed,
        result=result,
        instruments=instrument_summaries,
        binance=binance_summaries,
    )
    return result


def _refresh_current_public_universe(
    config: HistoricalPerpDatasetConfig,
    *,
    client: Any,
) -> UniverseRefreshResult:
    return refresh_hyperliquid_universe(
        archive_root=config.archive_root,
        asof_date=config.asof_date,
        min_day_notional_usd=config.min_day_notional_usd,
        mode=UniverseMode.CURRENT_LABELED_SANDBOX,
        include_hip3_dexs=config.include_hip3_dexs,
        client=client,
    )


def _selected_universe_rows(
    config: HistoricalPerpDatasetConfig,
    universe: UniverseRefreshResult,
) -> list[UniverseSnapshotRow]:
    rows = [
        row
        for row in load_universe_rows(config.archive_root)
        if row.snapshot_id == universe.snapshot_id and row.eligible
    ]
    if config.coins:
        wanted = set(config.coins)
        rows = [row for row in rows if _coin_from_instrument(row.instrument_id) in wanted]
    rows = sorted(rows, key=lambda row: (-row.day_ntl_vlm_usd, row.instrument_id))
    if config.max_instruments:
        rows = rows[: config.max_instruments]
    return rows


def _eligible_count(archive_root: Path, snapshot_id: str) -> int:
    return sum(1 for row in load_universe_rows(archive_root) if row.snapshot_id == snapshot_id and row.eligible)


def _collect_one_instrument(
    config: HistoricalPerpDatasetConfig,
    universe_row: UniverseSnapshotRow,
    *,
    client: Any,
    coin: str,
) -> tuple[InstrumentCollectionSummary, list[dict[str, Any]]]:
    instrument_id = universe_row.instrument_id
    fetches = _fetch_hyperliquid_candle_pages(
        client=client,
        coin=coin,
        timeframe=config.timeframe,
        start_ts=config.start_ts,
        end_ts=config.end_ts,
        max_pages=config.max_public_info_pages,
        page_limit=config.max_candles_per_public_page,
    )
    rows = [
        row
        for fetch in fetches
        for row in _public_candle_records(fetch.payload if hasattr(fetch, "payload") else fetch)
    ]
    if not rows:
        return (
            InstrumentCollectionSummary(
                instrument_id=instrument_id,
                coin=coin,
                day_ntl_vlm_usd=universe_row.day_ntl_vlm_usd,
                status="skipped",
                reason="hyperliquid_candle_window_empty",
                fetched_page_count=len(fetches),
                blocker_reasons=("hyperliquid_candle_window_empty",),
            ),
            [],
        )
    rows = _dedupe_candle_rows(rows)
    layout = ArchiveLayout(config.archive_root)
    store = ArchiveManifestStore(layout)
    raw_file = RawJsonlZstdWriter(layout, store).write_records(
        records=rows,
        venue="hyperliquid",
        datatype="candles",
        date=config.start_ts.date().isoformat(),
        run_id=config.run_id,
        job_id=f"{config.run_id}-{coin}-raw-candles",
        adapter_id=HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID,
        source_endpoint_or_subscription=HYPERLIQUID_CANDLE_SNAPSHOT_SOURCE,
        symbols=(instrument_id,),
        start_ts=config.start_ts,
        end_ts=config.end_ts,
        instrument_id=instrument_id,
        timeframe=config.timeframe,
    )
    bronze = raw_candles_to_bronze(
        archive_root=config.archive_root,
        raw_file_id=raw_file.file_id,
        job_id=f"{config.run_id}-{coin}-bronze-candles",
        instrument_id=instrument_id,
        timeframe=config.timeframe,
    )
    silver = bronze_candles_to_silver_bars(
        archive_root=config.archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id=f"{config.run_id}-{coin}-silver-bars",
        derive_timeframes=(),
        write_coverage=False,
        create_snapshot=False,
    )
    silver_file = silver.output_files[0]
    silver_rows = pq.ParquetFile(layout.resolve(silver_file.path)).read().to_pylist()
    report = coverage_report_for_bars(
        silver_rows,
        venue="hyperliquid",
        instrument_id=instrument_id,
        family="bars",
        timeframe=config.timeframe,
        start_ts=config.start_ts,
        end_ts=config.end_ts,
        coverage_min=config.coverage_min,
        evidence_mode=EvidenceMode.SANDBOX_DIAGNOSTIC,
    )
    CoverageManifestStore(layout).append_coverage_report(report)
    technical_pass = (
        report.coverage_ratio >= config.coverage_min
        and report.duplicate_timestamp_count == 0
        and report.parse_failure_count == 0
    )
    funding_refs: dict[str, Any] = {"funding_status": "not_requested"}
    if config.include_funding:
        try:
            funding_refs = _collect_funding_for_instrument(config, instrument_id=instrument_id, coin=coin, client=client)
        except Exception as exc:
            funding_refs = {
                "funding_status": "skipped",
                "funding_reason": f"funding_collection_failed:{exc}",
            }
    return (
        InstrumentCollectionSummary(
            instrument_id=instrument_id,
            coin=coin,
            day_ntl_vlm_usd=universe_row.day_ntl_vlm_usd,
            raw_file_id=raw_file.file_id,
            bronze_file_id=bronze.output_files[0].file_id,
            silver_file_id=silver_file.file_id,
            coverage_report_id=report.coverage_report_id,
            fetched_page_count=len(fetches),
            source_row_count=len(rows),
            expected_rows=report.expected_rows,
            observed_rows=report.observed_rows,
            coverage_ratio=report.coverage_ratio,
            missing_timestamp_count=report.missing_timestamp_count,
            technical_coverage_pass=technical_pass,
            blocker_reasons=report.blocker_reasons,
            **funding_refs,
        ),
        rows,
    )


def _collect_funding_for_instrument(
    config: HistoricalPerpDatasetConfig,
    *,
    instrument_id: str,
    coin: str,
    client: Any,
) -> dict[str, Any]:
    fetches = _fetch_hyperliquid_funding_pages(
        client=client,
        coin=coin,
        start_ts=config.start_ts,
        end_ts=config.end_ts,
        max_pages=config.max_funding_pages,
    )
    rows = [
        row
        for fetch in fetches
        for row in _public_funding_records(fetch.payload if hasattr(fetch, "payload") else fetch)
    ]
    if not rows:
        return {
            "funding_status": "skipped",
            "funding_reason": "hyperliquid_funding_window_empty",
        }
    layout = ArchiveLayout(config.archive_root)
    store = ArchiveManifestStore(layout)
    raw_file = RawJsonlZstdWriter(layout, store).write_records(
        records=rows,
        venue="hyperliquid",
        datatype="funding",
        date=config.start_ts.date().isoformat(),
        run_id=config.run_id,
        job_id=f"{config.run_id}-{coin}-raw-funding",
        adapter_id=HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID,
        source_endpoint_or_subscription=HYPERLIQUID_FUNDING_HISTORY_SOURCE,
        symbols=(instrument_id,),
        start_ts=config.start_ts,
        end_ts=config.end_ts,
        instrument_id=instrument_id,
    )
    bronze = raw_funding_to_bronze(
        archive_root=config.archive_root,
        raw_file_id=raw_file.file_id,
        job_id=f"{config.run_id}-{coin}-bronze-funding",
        instrument_id=instrument_id,
    )
    silver = bronze_funding_to_silver(
        archive_root=config.archive_root,
        bronze_file_id=bronze.output_files[0].file_id,
        job_id=f"{config.run_id}-{coin}-silver-funding",
    )
    return {
        "funding_status": "collected",
        "funding_raw_file_id": raw_file.file_id,
        "funding_bronze_file_id": bronze.output_files[0].file_id,
        "funding_silver_file_id": silver.output_files[0].file_id,
        "funding_row_count": len(rows),
    }


def _fetch_hyperliquid_candle_pages(
    *,
    client: Any,
    coin: str,
    timeframe: str,
    start_ts: datetime,
    end_ts: datetime,
    max_pages: int,
    page_limit: int,
) -> list[Any]:
    fetches: list[Any] = []
    for page_index, (page_start, page_end) in enumerate(
        _iter_page_windows(start_ts=start_ts, end_ts=end_ts, timeframe=timeframe, page_limit=page_limit),
        start=1,
    ):
        if page_index > max_pages:
            raise ValueError("Hyperliquid candle pagination exceeded max_public_info_pages")
        fetches.append(
            client.fetch_candle_snapshot(
                coin=coin,
                interval=timeframe,
                start_time=page_start,
                end_time=page_end,
            )
        )
    return fetches


def _fetch_hyperliquid_funding_pages(
    *,
    client: Any,
    coin: str,
    start_ts: datetime,
    end_ts: datetime,
    max_pages: int,
) -> list[Any]:
    fetches: list[Any] = []
    current = ensure_utc(start_ts)
    end = ensure_utc(end_ts)
    while current < end:
        if len(fetches) >= max_pages:
            raise ValueError("Hyperliquid funding pagination exceeded max_funding_pages")
        fetch = client.fetch_funding_history(
            coin=coin,
            start_time=current,
            end_time=end,
        )
        rows = _public_funding_records(fetch.payload if hasattr(fetch, "payload") else fetch)
        if not rows:
            break
        fetches.append(fetch)
        last_ms = max(int(row["time"]) for row in rows)
        next_current = datetime.fromtimestamp((last_ms + 1) / 1000, tz=UTC)
        if next_current <= current:
            raise ValueError("Hyperliquid funding pagination did not advance")
        current = next_current
    return fetches


def _iter_page_windows(
    *,
    start_ts: datetime,
    end_ts: datetime,
    timeframe: str,
    page_limit: int,
) -> Iterable[tuple[datetime, datetime]]:
    step = timeframe_to_timedelta(timeframe)
    page_delta = step * page_limit
    current = ensure_utc(start_ts)
    end = ensure_utc(end_ts)
    while current < end:
        page_end = min(current + page_delta, end)
        yield current, page_end
        current = page_end


def _public_candle_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Hyperliquid candleSnapshot payload must be a list")
    records: list[dict[str, Any]] = []
    for index, row in enumerate(payload):
        if not isinstance(row, Mapping):
            raise ValueError(f"Hyperliquid candleSnapshot row {index} must be an object")
        records.append(dict(row))
    return records


def _public_funding_records(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Hyperliquid fundingHistory payload must be a list")
    records: list[dict[str, Any]] = []
    for index, row in enumerate(payload):
        if not isinstance(row, Mapping):
            raise ValueError(f"Hyperliquid fundingHistory row {index} must be an object")
        records.append(dict(row))
    return records


def _dedupe_candle_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_ts: dict[int, dict[str, Any]] = {}
    for row in rows:
        ts = int(row.get("t") or row.get("ts") or row.get("time"))
        by_ts[ts] = dict(row)
    return [by_ts[key] for key in sorted(by_ts)]


def _validate_against_binance(
    config: HistoricalPerpDatasetConfig,
    universe_row: UniverseSnapshotRow,
    *,
    coin: str,
    hyperliquid_rows: Sequence[Mapping[str, Any]],
    fetcher: BinanceKlineFetcher | None,
) -> BinanceValidationSummary:
    symbol = _binance_symbol_for_hyperliquid_coin(coin)
    if symbol is None:
        return BinanceValidationSummary(
            instrument_id=universe_row.instrument_id,
            coin=coin,
            status="skipped",
            reason="no_plain_binance_symbol_mapping",
            hyperliquid_rows=len(hyperliquid_rows),
        )
    active_fetcher = fetcher or _default_binance_fetcher(config)
    try:
        binance_rows = active_fetcher(symbol, config.timeframe, config.start_ts, config.end_ts)
    except Exception as exc:
        return BinanceValidationSummary(
            instrument_id=universe_row.instrument_id,
            coin=coin,
            binance_symbol=symbol,
            status="skipped",
            reason=f"binance_fetch_failed:{exc}",
            hyperliquid_rows=len(hyperliquid_rows),
        )
    if not binance_rows:
        return BinanceValidationSummary(
            instrument_id=universe_row.instrument_id,
            coin=coin,
            binance_symbol=symbol,
            status="skipped",
            reason="binance_symbol_or_window_unavailable",
            hyperliquid_rows=len(hyperliquid_rows),
        )
    diffs = _close_diff_bps(hyperliquid_rows, binance_rows)
    if not diffs:
        return BinanceValidationSummary(
            instrument_id=universe_row.instrument_id,
            coin=coin,
            binance_symbol=symbol,
            status="skipped",
            reason="no_timestamp_overlap",
            hyperliquid_rows=len(hyperliquid_rows),
            binance_rows=len(binance_rows),
        )
    p95 = _percentile(diffs, 0.95)
    status = "passed" if p95 <= config.binance_close_diff_warn_bps else "warning"
    reason = None if status == "passed" else "cross_venue_close_diff_above_warning_threshold"
    return BinanceValidationSummary(
        instrument_id=universe_row.instrument_id,
        coin=coin,
        binance_symbol=symbol,
        status=status,
        reason=reason,
        hyperliquid_rows=len(hyperliquid_rows),
        binance_rows=len(binance_rows),
        overlap_rows=len(diffs),
        median_abs_close_diff_bps=median(diffs),
        p95_abs_close_diff_bps=p95,
        max_abs_close_diff_bps=max(diffs),
    )


def _default_binance_fetcher(config: HistoricalPerpDatasetConfig) -> BinanceKlineFetcher:
    def fetch(symbol: str, timeframe: str, start_ts: datetime, end_ts: datetime) -> list[Mapping[str, Any]]:
        return fetch_binance_usdm_klines(
            symbol=symbol,
            timeframe=timeframe,
            start_ts=start_ts,
            end_ts=end_ts,
            base_url=config.binance_base_url,
            timeout=config.binance_timeout,
        )

    return fetch


def fetch_binance_usdm_klines(
    *,
    symbol: str,
    timeframe: str,
    start_ts: datetime,
    end_ts: datetime,
    base_url: str = DEFAULT_BINANCE_BASE_URL,
    timeout: float = 20.0,
) -> list[dict[str, Any]]:
    step = timeframe_to_timedelta(timeframe)
    start_ms = _epoch_millis(start_ts)
    end_ms_exclusive = _epoch_millis(end_ts)
    current_ms = start_ms
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        while current_ms < end_ms_exclusive:
            response = client.get(
                "/fapi/v1/klines",
                params={
                    "symbol": symbol,
                    "interval": timeframe,
                    "startTime": current_ms,
                    "endTime": end_ms_exclusive - 1,
                    "limit": 1500,
                },
            )
            if response.status_code in {400, 404}:
                return []
            response.raise_for_status()
            payload = response.json()
            if not payload:
                break
            for item in payload:
                if not isinstance(item, list) or len(item) < 6:
                    continue
                open_time = int(item[0])
                if open_time < start_ms or open_time >= end_ms_exclusive or open_time in seen:
                    continue
                seen.add(open_time)
                rows.append(
                    {
                        "ts": open_time,
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    }
                )
            last_open = int(payload[-1][0])
            next_ms = last_open + int(step.total_seconds() * 1000)
            if next_ms <= current_ms:
                break
            current_ms = next_ms
    return sorted(rows, key=lambda row: int(row["ts"]))


def _close_diff_bps(
    hyperliquid_rows: Sequence[Mapping[str, Any]],
    binance_rows: Sequence[Mapping[str, Any]],
) -> list[float]:
    binance_by_ts = {_timestamp_ms(row): float(row["close"]) for row in binance_rows}
    diffs: list[float] = []
    for row in hyperliquid_rows:
        ts = _timestamp_ms(row)
        binance_close = binance_by_ts.get(ts)
        if binance_close is None or binance_close <= 0:
            continue
        hl_close = float(row.get("c") or row.get("close"))
        diffs.append(abs(hl_close - binance_close) / binance_close * 10_000.0)
    return diffs


def _timestamp_ms(row: Mapping[str, Any]) -> int:
    return int(row.get("t") or row.get("ts") or row.get("time"))


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ValueError("percentile requires non-empty values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _coin_from_instrument(instrument_id: str) -> str:
    return instrument_id.rsplit(":", 1)[-1].upper()


def _venue_symbols_by_instrument(archive_root: Path) -> dict[str, str]:
    path = ArchiveLayout(archive_root).resolve("manifests", "instrument_catalog.parquet")
    if not path.exists():
        return {}
    rows = pq.ParquetFile(path).read().to_pylist()
    symbols: dict[str, str] = {}
    for row in rows:
        instrument_id = str(row.get("instrument_id") or "")
        venue_symbol = str(row.get("venue_symbol") or "")
        if instrument_id and venue_symbol:
            symbols[instrument_id] = venue_symbol
    return symbols


def _binance_symbol_for_hyperliquid_coin(coin: str) -> str | None:
    normalized = coin.strip()
    if not normalized or not normalized.replace("_", "").isalnum():
        return None
    if normalized.startswith("k") and len(normalized) > 1 and normalized[1:].upper() == normalized[1:]:
        return f"1000{normalized[1:]}USDT"
    return f"{normalized.upper()}USDT"


def _epoch_millis(value: datetime) -> int:
    return int(ensure_utc(value).timestamp() * 1000)


def _write_report(
    *,
    path: Path,
    config: HistoricalPerpDatasetConfig,
    result: HistoricalPerpDatasetResult,
    instruments: Sequence[InstrumentCollectionSummary],
    binance: Sequence[BinanceValidationSummary],
) -> None:
    payload = {
        "schema_version": HISTORICAL_DATASET_REPORT_SCHEMA_VERSION,
        "config": config.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "instrument_summaries": [item.model_dump(mode="json") for item in instruments],
        "binance_validation": [item.model_dump(mode="json") for item in binance],
        "boundary": dict(RESEARCH_BOUNDARY),
        "accepted_research_ready": False,
        "caveats": [
            "current_public_universe_not_historical_asof",
            "binance_cross_venue_validation_is_sanity_check_not_hyperliquid_ground_truth",
            "no_strategy_candidate_paper_live_order_sizing_runtime_or_promotion_claim",
        ],
        "written_at": utc_isoformat(datetime.now(tz=UTC)),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
