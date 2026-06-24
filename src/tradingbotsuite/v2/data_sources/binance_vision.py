# V2-AUDIT-ID: V2-AUD-DATASRC-005
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, strict_free_binance_vision_availability, no_downloads
# V2-OWNER: v2_data_sources
"""Binance Vision availability scanner for verified cross-venue mappings."""

from __future__ import annotations

import json
import csv
import hashlib
import io
import zipfile
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import (
    canonical_json_hash,
    file_sha256,
    manifest_rows_hash,
)
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.layout import partition, safe_partition_value
from tradingbotsuite.v2.archive.market_data import BronzeCandleRow, SilverBarRow
from tradingbotsuite.v2.archive.microstructure import write_microstructure_raw_capture
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.data_sources.schemas import (
    CostClass,
    CoverageLabel,
    CoverageWindow,
    DataFamilyCoverageReport,
    ExpectedBuckets,
    SourceRegistryEntry,
    SymbolMapSnapshot,
    require_strict_zero_dollar_source,
    require_verified_external_mapping,
)
from tradingbotsuite.v2.security.boundary import require_research_boundary

BINANCE_VISION_BASE_URL = "https://data.binance.vision"


class BinanceVisionAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    BLOCKED_MAPPING = "blocked_mapping"
    PROBE_ERROR = "probe_error"


class BinanceVisionChecksumStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    NOT_CHECKED = "not_checked"
    PROBE_ERROR = "probe_error"


class BinanceVisionDownloadStatus(str, Enum):
    DOWNLOADED = "downloaded"
    CACHE_HIT = "cache_hit"
    BLOCKED = "blocked"
    DOWNLOAD_ERROR = "download_error"
    CHECKSUM_MISMATCH = "checksum_mismatch"


class BinanceVisionBackfillStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"


class BinanceVisionRowType(str, Enum):
    TRADE = "trade"
    AGG_TRADE = "agg_trade"
    KLINE = "kline"


class BinanceVisionSourceSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    market_scope: str
    venue_key: str
    market_type: str
    family: str
    data_family: str
    folder: str
    filename_family: str
    interval: str | None = None


BINANCE_VISION_SOURCE_SPECS: dict[str, BinanceVisionSourceSpec] = {
    "binance_vision_usdm_trades": BinanceVisionSourceSpec(
        source_id="binance_vision_usdm_trades",
        market_scope="futures_um",
        venue_key="binance_usdm",
        market_type="perpetual",
        family="trades",
        data_family="trades",
        folder="data/futures/um/daily/trades",
        filename_family="trades",
    ),
    "binance_vision_usdm_agg_trades": BinanceVisionSourceSpec(
        source_id="binance_vision_usdm_agg_trades",
        market_scope="futures_um",
        venue_key="binance_usdm",
        market_type="perpetual",
        family="aggTrades",
        data_family="derived_trades",
        folder="data/futures/um/daily/aggTrades",
        filename_family="aggTrades",
    ),
    "binance_vision_usdm_klines": BinanceVisionSourceSpec(
        source_id="binance_vision_usdm_klines",
        market_scope="futures_um",
        venue_key="binance_usdm",
        market_type="perpetual",
        family="klines",
        data_family="candles_1m",
        folder="data/futures/um/daily/klines",
        filename_family="klines",
        interval="1m",
    ),
    "binance_vision_spot_trades": BinanceVisionSourceSpec(
        source_id="binance_vision_spot_trades",
        market_scope="spot",
        venue_key="binance_spot",
        market_type="spot",
        family="trades",
        data_family="trades",
        folder="data/spot/daily/trades",
        filename_family="trades",
    ),
    "binance_vision_spot_agg_trades": BinanceVisionSourceSpec(
        source_id="binance_vision_spot_agg_trades",
        market_scope="spot",
        venue_key="binance_spot",
        market_type="spot",
        family="aggTrades",
        data_family="derived_trades",
        folder="data/spot/daily/aggTrades",
        filename_family="aggTrades",
    ),
    "binance_vision_spot_klines": BinanceVisionSourceSpec(
        source_id="binance_vision_spot_klines",
        market_scope="spot",
        venue_key="binance_spot",
        market_type="spot",
        family="klines",
        data_family="candles_1m",
        folder="data/spot/daily/klines",
        filename_family="klines",
        interval="1m",
    ),
}

DEFAULT_BINANCE_VISION_SOURCE_IDS = tuple(BINANCE_VISION_SOURCE_SPECS)


class BinanceVisionHeadResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class BinanceVisionGetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    content: bytes = b""
    error: str | None = None


class BinanceVisionAvailabilityRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    hyperliquid_coin: str = Field(min_length=1)
    venue_key: str = Field(min_length=1)
    binance_symbol: str | None = None
    probe_date: date
    market_scope: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    family: str = Field(min_length=1)
    data_family: str = Field(min_length=1)
    interval: str | None = None
    zip_url: str | None = None
    checksum_url: str | None = None
    zip_status: BinanceVisionAvailabilityStatus
    checksum_status: BinanceVisionChecksumStatus = BinanceVisionChecksumStatus.NOT_CHECKED
    http_status_code: int | None = None
    checksum_http_status_code: int | None = None
    content_length_bytes: int | None = Field(default=None, ge=0)
    checksum_content_length_bytes: int | None = Field(default=None, ge=0)
    source_cost_class: CostClass
    native_to_hyperliquid: bool = False
    blocked_reasons: tuple[str, ...] = ()
    probe_error: str | None = None
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
    def _validate_row(self) -> "BinanceVisionAvailabilityRow":
        require_research_boundary(self, context="Binance Vision availability row")
        if self.native_to_hyperliquid:
            raise ValueError("Binance Vision availability rows cannot be Hyperliquid-native")
        if self.zip_status == BinanceVisionAvailabilityStatus.AVAILABLE and not self.zip_url:
            raise ValueError("available rows require zip_url")
        if self.zip_status == BinanceVisionAvailabilityStatus.BLOCKED_MAPPING and not self.blocked_reasons:
            raise ValueError("blocked mapping rows require blocker reasons")
        return self


class BinanceVisionAvailabilityManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "binance_vision_availability_manifest"
    availability_manifest_id: str = Field(min_length=64, max_length=64)
    start_date: date
    end_date: date
    source_ids: tuple[str, ...] = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    strict_zero_dollar_mode: bool = True
    rows: tuple[BinanceVisionAvailabilityRow, ...]
    row_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    blocked_mapping_count: int = Field(ge=0)
    probe_error_count: int = Field(ge=0)
    checksum_available_count: int = Field(ge=0)
    checksum_missing_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
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
    def _validate_manifest(self) -> "BinanceVisionAvailabilityManifest":
        require_research_boundary(self, context="Binance Vision availability manifest")
        if self.manifest_type != "binance_vision_availability_manifest":
            raise ValueError("manifest_type must be binance_vision_availability_manifest")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.available_count != _count_zip_status(self.rows, BinanceVisionAvailabilityStatus.AVAILABLE):
            raise ValueError("available_count does not match rows")
        if self.missing_count != _count_zip_status(self.rows, BinanceVisionAvailabilityStatus.MISSING):
            raise ValueError("missing_count does not match rows")
        if self.blocked_mapping_count != _count_zip_status(
            self.rows,
            BinanceVisionAvailabilityStatus.BLOCKED_MAPPING,
        ):
            raise ValueError("blocked_mapping_count does not match rows")
        if self.probe_error_count != _count_zip_status(self.rows, BinanceVisionAvailabilityStatus.PROBE_ERROR):
            raise ValueError("probe_error_count does not match rows")
        if self.checksum_available_count != _count_checksum_status(
            self.rows,
            BinanceVisionChecksumStatus.AVAILABLE,
        ):
            raise ValueError("checksum_available_count does not match rows")
        if self.checksum_missing_count != _count_checksum_status(
            self.rows,
            BinanceVisionChecksumStatus.MISSING,
        ):
            raise ValueError("checksum_missing_count does not match rows")
        expected_hash = binance_vision_availability_rows_hash(self.rows)
        if self.row_manifest_hash != expected_hash:
            raise ValueError("row_manifest_hash does not match availability rows")
        expected_id = binance_vision_availability_manifest_id_for(
            start_date=self.start_date,
            end_date=self.end_date,
            source_ids=self.source_ids,
            source_registry_ref=self.source_registry_ref,
            symbol_map_snapshot_id=self.symbol_map_snapshot_id,
            row_manifest_hash=self.row_manifest_hash,
        )
        if self.availability_manifest_id != expected_id:
            raise ValueError("availability_manifest_id does not match manifest identity")
        return self


class BinanceVisionAvailabilityWriteResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    availability_manifest_id: str = Field(min_length=64, max_length=64)
    manifest_ref: str = Field(min_length=1)
    manifest_sha256: str = Field(min_length=64, max_length=64)
    row_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    blocked_mapping_count: int = Field(ge=0)
    probe_error_count: int = Field(ge=0)
    checksum_available_count: int = Field(ge=0)
    checksum_missing_count: int = Field(ge=0)
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
    def _validate_result(self) -> "BinanceVisionAvailabilityWriteResult":
        require_research_boundary(self, context="Binance Vision availability result")
        return self


class BinanceVisionDownloadResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "binance_vision_download_manifest"
    download_id: str = Field(min_length=64, max_length=64)
    download_manifest_ref: str = Field(min_length=1)
    status: BinanceVisionDownloadStatus
    source_id: str
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    hyperliquid_coin: str = Field(min_length=1)
    binance_symbol: str | None = None
    probe_date: date
    market_scope: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    family: str = Field(min_length=1)
    data_family: str = Field(min_length=1)
    interval: str | None = None
    zip_url: str | None = None
    checksum_url: str | None = None
    zip_cache_ref: str | None = None
    checksum_cache_ref: str | None = None
    zip_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    checksum_payload_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    checksum_expected_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    byte_count: int = Field(default=0, ge=0)
    checksum_byte_count: int = Field(default=0, ge=0)
    checksum_verified: bool = False
    cache_hit: bool = False
    max_bytes: int = Field(ge=1)
    source_cost_class: CostClass
    native_to_hyperliquid: bool = False
    blocked_reasons: tuple[str, ...] = ()
    downloaded_at: str = Field(default_factory=lambda: utc_now().isoformat())
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
    def _validate_download_result(self) -> "BinanceVisionDownloadResult":
        require_research_boundary(self, context="Binance Vision download result")
        if self.manifest_type != "binance_vision_download_manifest":
            raise ValueError("manifest_type must be binance_vision_download_manifest")
        if self.native_to_hyperliquid:
            raise ValueError("Binance Vision download result cannot be Hyperliquid-native")
        if self.status in {
            BinanceVisionDownloadStatus.DOWNLOADED,
            BinanceVisionDownloadStatus.CACHE_HIT,
        }:
            if not self.zip_cache_ref or not self.zip_sha256 or not self.byte_count:
                raise ValueError("successful downloads require zip cache ref, sha256, and bytes")
            if self.blocked_reasons:
                raise ValueError("successful downloads cannot carry blocker reasons")
        if self.status == BinanceVisionDownloadStatus.CHECKSUM_MISMATCH and not self.blocked_reasons:
            raise ValueError("checksum mismatch requires blocker reasons")
        return self


class BinanceVisionDailyBackfillResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "binance_vision_daily_backfill_result"
    backfill_id: str = Field(min_length=64, max_length=64)
    status: BinanceVisionBackfillStatus
    source_id: str
    binance_symbol: str | None = None
    hyperliquid_coin: str = Field(min_length=1)
    probe_date: date
    target_download_id: str = Field(min_length=64, max_length=64)
    target_download_manifest_ref: str = Field(min_length=1)
    target_parse_hash: str | None = Field(default=None, min_length=64, max_length=64)
    target_ingest_id: str | None = Field(default=None, min_length=64, max_length=64)
    comparison_download_id: str | None = Field(default=None, min_length=64, max_length=64)
    comparison_parse_hash: str | None = Field(default=None, min_length=64, max_length=64)
    comparison_report_id: str | None = Field(default=None, min_length=64, max_length=64)
    coverage_report_id: str = Field(min_length=1)
    coverage_report_ref: str = Field(min_length=1)
    accepted_for_research_reporting: bool = False
    blocker_reasons: tuple[str, ...] = ()
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
    def _validate_backfill_result(self) -> "BinanceVisionDailyBackfillResult":
        require_research_boundary(self, context="Binance Vision daily backfill result")
        if self.manifest_type != "binance_vision_daily_backfill_result":
            raise ValueError("manifest_type must be binance_vision_daily_backfill_result")
        if self.status == BinanceVisionBackfillStatus.COMPLETED and self.blocker_reasons:
            raise ValueError("completed backfill cannot carry blocker reasons")
        if self.status == BinanceVisionBackfillStatus.BLOCKED and not self.blocker_reasons:
            raise ValueError("blocked backfill requires blocker reasons")
        expected_id = canonical_json_hash(
            {
                "manifest_type": self.manifest_type,
                "source_id": self.source_id,
                "binance_symbol": self.binance_symbol,
                "hyperliquid_coin": self.hyperliquid_coin,
                "probe_date": self.probe_date.isoformat(),
                "target_download_id": self.target_download_id,
                "target_parse_hash": self.target_parse_hash,
                "target_ingest_id": self.target_ingest_id,
                "comparison_download_id": self.comparison_download_id,
                "comparison_parse_hash": self.comparison_parse_hash,
                "comparison_report_id": self.comparison_report_id,
                "coverage_report_id": self.coverage_report_id,
                "accepted_for_research_reporting": self.accepted_for_research_reporting,
                "blocker_reasons": self.blocker_reasons,
            }
        )
        if self.backfill_id != expected_id:
            raise ValueError("backfill_id does not match result identity")
        return self


class BinanceVisionBackfillBatchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "binance_vision_backfill_batch"
    batch_id: str = Field(min_length=64, max_length=64)
    batch_manifest_ref: str = Field(min_length=1)
    availability_manifest_id: str = Field(min_length=64, max_length=64)
    target_source_id: str = Field(min_length=1)
    comparison_source_id: str | None = None
    selected_count: int = Field(ge=0)
    completed_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    max_rows: int = Field(ge=1)
    daily_results: tuple[BinanceVisionDailyBackfillResult, ...]
    daily_result_ids: tuple[str, ...]
    blocker_reasons: tuple[str, ...] = ()
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
    def _validate_batch_result(self) -> "BinanceVisionBackfillBatchResult":
        require_research_boundary(self, context="Binance Vision backfill batch result")
        if self.manifest_type != "binance_vision_backfill_batch":
            raise ValueError("manifest_type must be binance_vision_backfill_batch")
        if self.selected_count != len(self.daily_results):
            raise ValueError("selected_count must match daily results")
        if self.daily_result_ids != tuple(result.backfill_id for result in self.daily_results):
            raise ValueError("daily_result_ids must match daily results")
        if self.completed_count != sum(
            1 for result in self.daily_results if result.status == BinanceVisionBackfillStatus.COMPLETED
        ):
            raise ValueError("completed_count does not match daily results")
        if self.blocked_count != sum(
            1 for result in self.daily_results if result.status == BinanceVisionBackfillStatus.BLOCKED
        ):
            raise ValueError("blocked_count does not match daily results")
        if self.accepted_count != sum(
            1 for result in self.daily_results if result.accepted_for_research_reporting
        ):
            raise ValueError("accepted_count does not match daily results")
        expected_id = canonical_json_hash(
            {
                "manifest_type": self.manifest_type,
                "availability_manifest_id": self.availability_manifest_id,
                "target_source_id": self.target_source_id,
                "comparison_source_id": self.comparison_source_id,
                "max_rows": self.max_rows,
                "daily_result_ids": self.daily_result_ids,
                "blocker_reasons": self.blocker_reasons,
            }
        )
        if self.batch_id != expected_id:
            raise ValueError("batch_id does not match result identity")
        return self


class BinanceVisionParsedDataRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str
    binance_symbol: str = Field(min_length=1)
    row_type: BinanceVisionRowType
    source_row_index: int = Field(ge=0)
    event_time_ms: int = Field(ge=0)
    trade_id: int | None = None
    aggregate_trade_id: int | None = None
    first_trade_id: int | None = None
    last_trade_id: int | None = None
    price: float | None = Field(default=None, gt=0)
    quantity: float | None = Field(default=None, ge=0)
    open: float | None = Field(default=None, gt=0)
    high: float | None = Field(default=None, gt=0)
    low: float | None = Field(default=None, gt=0)
    close: float | None = Field(default=None, gt=0)
    volume: float | None = Field(default=None, ge=0)
    close_time_ms: int | None = Field(default=None, ge=0)
    trade_count: int | None = Field(default=None, ge=0)
    buyer_maker: bool | None = None
    raw_fields: dict[str, str] = Field(default_factory=dict)
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
    def _validate_parsed_row(self) -> "BinanceVisionParsedDataRow":
        require_research_boundary(self, context="Binance Vision parsed row")
        if self.row_type == BinanceVisionRowType.KLINE:
            required = (self.open, self.high, self.low, self.close, self.volume, self.close_time_ms)
            if any(value is None for value in required):
                raise ValueError("kline rows require OHLCV and close_time_ms")
            assert self.open is not None
            assert self.high is not None
            assert self.low is not None
            assert self.close is not None
            if self.low > min(self.open, self.high, self.close):
                raise ValueError("kline low cannot exceed open/high/close")
            if self.high < max(self.open, self.low, self.close):
                raise ValueError("kline high cannot be below open/low/close")
        if self.row_type == BinanceVisionRowType.TRADE and self.trade_id is None:
            raise ValueError("trade rows require trade_id")
        if self.row_type == BinanceVisionRowType.AGG_TRADE and self.aggregate_trade_id is None:
            raise ValueError("agg_trade rows require aggregate_trade_id")
        return self


class BinanceVisionParseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str
    binance_symbol: str = Field(min_length=1)
    family: str
    row_type: BinanceVisionRowType
    archive_member: str = Field(min_length=1)
    zip_sha256: str = Field(min_length=64, max_length=64)
    checksum_verified: bool = False
    checksum_expected_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    row_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    duplicate_ids: tuple[int, ...] = ()
    gap_count: int = Field(ge=0)
    input_monotonic: bool
    interval_alignment_status: str = "not_applicable"
    normalized_rows_hash: str = Field(min_length=64, max_length=64)
    rows: tuple[BinanceVisionParsedDataRow, ...]
    warnings: tuple[str, ...] = ()
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
    def _validate_parse_result(self) -> "BinanceVisionParseResult":
        require_research_boundary(self, context="Binance Vision parse result")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.normalized_rows_hash != manifest_rows_hash(
            row.model_dump(mode="json") for row in self.rows
        ):
            raise ValueError("normalized_rows_hash does not match rows")
        if self.checksum_verified and not self.checksum_expected_sha256:
            raise ValueError("checksum_verified requires checksum_expected_sha256")
        return self


class BinanceVisionArchiveIngestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    ingest_id: str = Field(min_length=64, max_length=64)
    source_id: str
    binance_symbol: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    archive_date: date
    row_type: BinanceVisionRowType
    row_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    input_monotonic: bool
    interval_alignment_status: str
    zip_sha256: str = Field(min_length=64, max_length=64)
    checksum_verified: bool = False
    parser_manifest_ref: str = Field(min_length=1)
    raw_file_id: str = Field(min_length=64, max_length=64)
    bronze_file_id: str | None = Field(default=None, min_length=64, max_length=64)
    silver_file_id: str | None = Field(default=None, min_length=64, max_length=64)
    microstructure_quality_report_id: str | None = Field(default=None, min_length=64, max_length=64)
    storage_report_id: str | None = Field(default=None, min_length=64, max_length=64)
    accepted_research_evidence: bool = False
    native_to_hyperliquid: bool = False
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
    def _validate_ingest_result(self) -> "BinanceVisionArchiveIngestResult":
        require_research_boundary(self, context="Binance Vision archive ingest result")
        if self.accepted_research_evidence:
            raise ValueError("local Binance Vision ingest cannot mark accepted research evidence")
        if self.native_to_hyperliquid:
            raise ValueError("Binance Vision ingest result cannot be Hyperliquid-native")
        return self


class BinanceVisionReconstructedBarRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    bucket_start_ms: int = Field(ge=0)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    observed_event_count: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_bar(self) -> "BinanceVisionReconstructedBarRow":
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("reconstructed low cannot exceed open/high/close")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("reconstructed high cannot be below open/low/close")
        return self


class BinanceVisionBarComparisonRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    bucket_start_ms: int = Field(ge=0)
    status: str = Field(min_length=1)
    kline_open: float = Field(gt=0)
    kline_high: float = Field(gt=0)
    kline_low: float = Field(gt=0)
    kline_close: float = Field(gt=0)
    kline_volume: float = Field(ge=0)
    reconstructed_open: float | None = Field(default=None, gt=0)
    reconstructed_high: float | None = Field(default=None, gt=0)
    reconstructed_low: float | None = Field(default=None, gt=0)
    reconstructed_close: float | None = Field(default=None, gt=0)
    reconstructed_volume: float | None = Field(default=None, ge=0)
    open_abs_diff: float | None = Field(default=None, ge=0)
    high_abs_diff: float | None = Field(default=None, ge=0)
    low_abs_diff: float | None = Field(default=None, ge=0)
    close_abs_diff: float | None = Field(default=None, ge=0)
    volume_abs_diff: float | None = Field(default=None, ge=0)
    kline_trade_count: int | None = Field(default=None, ge=0)
    reconstructed_event_count: int | None = Field(default=None, ge=0)
    reasons: tuple[str, ...] = ()


class BinanceVisionBarComparisonReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "binance_vision_reconstructed_bar_comparison"
    comparison_report_id: str = Field(min_length=64, max_length=64)
    binance_symbol: str = Field(min_length=1)
    source_row_type: BinanceVisionRowType
    kline_rows_hash: str = Field(min_length=64, max_length=64)
    source_rows_hash: str = Field(min_length=64, max_length=64)
    price_abs_tolerance: float = Field(ge=0)
    volume_abs_tolerance: float = Field(ge=0)
    compared_bucket_count: int = Field(ge=0)
    passed_bucket_count: int = Field(ge=0)
    failed_bucket_count: int = Field(ge=0)
    missing_reconstructed_count: int = Field(ge=0)
    max_close_abs_diff: float = Field(ge=0)
    passed: bool
    blocker_reasons: tuple[str, ...] = ()
    rows: tuple[BinanceVisionBarComparisonRow, ...]
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
    def _validate_report(self) -> "BinanceVisionBarComparisonReport":
        require_research_boundary(self, context="Binance Vision reconstructed-bar comparison")
        if self.report_type != "binance_vision_reconstructed_bar_comparison":
            raise ValueError("report_type must be binance_vision_reconstructed_bar_comparison")
        if self.compared_bucket_count != len(self.rows):
            raise ValueError("compared_bucket_count must match rows length")
        if self.passed_bucket_count != sum(1 for row in self.rows if row.status == "passed"):
            raise ValueError("passed_bucket_count does not match rows")
        if self.failed_bucket_count != sum(1 for row in self.rows if row.status == "failed"):
            raise ValueError("failed_bucket_count does not match rows")
        if self.missing_reconstructed_count != sum(
            1 for row in self.rows if row.status == "missing_reconstructed"
        ):
            raise ValueError("missing_reconstructed_count does not match rows")
        if self.passed and self.blocker_reasons:
            raise ValueError("passing comparison cannot carry blocker reasons")
        if not self.passed and not self.blocker_reasons:
            raise ValueError("failing comparison requires blocker reasons")
        expected_id = canonical_json_hash(
            {
                "report_type": self.report_type,
                "binance_symbol": self.binance_symbol,
                "source_row_type": self.source_row_type.value,
                "kline_rows_hash": self.kline_rows_hash,
                "source_rows_hash": self.source_rows_hash,
                "price_abs_tolerance": self.price_abs_tolerance,
                "volume_abs_tolerance": self.volume_abs_tolerance,
                "rows_hash": manifest_rows_hash(row.model_dump(mode="json") for row in self.rows),
            }
        )
        if self.comparison_report_id != expected_id:
            raise ValueError("comparison_report_id does not match report identity")
        return self


HeadProbe = Callable[[str], BinanceVisionHeadResult | Mapping[str, Any] | int]


def binance_vision_daily_zip_url(
    *,
    source_id: str,
    symbol: str,
    day: date,
    base_url: str = BINANCE_VISION_BASE_URL,
) -> str:
    spec = binance_vision_source_spec(source_id)
    normalized_symbol = _normalize_binance_symbol(symbol)
    day_text = day.isoformat()
    root = base_url.rstrip("/")
    if spec.family == "klines":
        return (
            f"{root}/{spec.folder}/{normalized_symbol}/{spec.interval}/"
            f"{normalized_symbol}-{spec.interval}-{day_text}.zip"
        )
    return (
        f"{root}/{spec.folder}/{normalized_symbol}/"
        f"{normalized_symbol}-{spec.filename_family}-{day_text}.zip"
    )


def binance_vision_checksum_url(zip_url: str) -> str:
    return f"{zip_url}.CHECKSUM"


def binance_vision_source_spec(source_id: str) -> BinanceVisionSourceSpec:
    try:
        return BINANCE_VISION_SOURCE_SPECS[source_id]
    except KeyError as exc:
        raise ValueError(f"unsupported Binance Vision source_id: {source_id}") from exc


def binance_vision_availability_rows_hash(
    rows: tuple[BinanceVisionAvailabilityRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def binance_vision_availability_manifest_id_for(
    *,
    start_date: date,
    end_date: date,
    source_ids: tuple[str, ...],
    source_registry_ref: str,
    symbol_map_snapshot_id: str,
    row_manifest_hash: str,
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "binance_vision_availability_manifest",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "source_ids": source_ids,
            "source_registry_ref": source_registry_ref,
            "symbol_map_snapshot_id": symbol_map_snapshot_id,
            "row_manifest_hash": row_manifest_hash,
        }
    )


def write_binance_vision_availability_manifest(
    *,
    archive_root: str | Path,
    symbol_map_snapshot: SymbolMapSnapshot | Mapping[str, Any],
    symbol_map_ref: str | None = None,
    source_entries: Iterable[SourceRegistryEntry | Mapping[str, Any]],
    start_date: date,
    end_date: date,
    source_ids: Iterable[str] = DEFAULT_BINANCE_VISION_SOURCE_IDS,
    head_probe: HeadProbe | None = None,
    base_url: str = BINANCE_VISION_BASE_URL,
) -> BinanceVisionAvailabilityWriteResult:
    parsed_snapshot = (
        symbol_map_snapshot
        if isinstance(symbol_map_snapshot, SymbolMapSnapshot)
        else SymbolMapSnapshot.model_validate(dict(symbol_map_snapshot))
    )
    requested_source_ids = tuple(source_ids)
    if not requested_source_ids:
        raise ValueError("source_ids cannot be empty")
    if end_date < start_date:
        raise ValueError("end_date must be greater than or equal to start_date")
    entries_by_id = _validated_source_entries(source_entries, requested_source_ids)
    probe = head_probe or default_binance_vision_head_probe
    resolved_symbol_map_ref = symbol_map_ref or _default_symbol_map_ref(parsed_snapshot)
    rows = _build_availability_rows(
        snapshot=parsed_snapshot,
        symbol_map_ref=resolved_symbol_map_ref,
        entries_by_id=entries_by_id,
        start_date=start_date,
        end_date=end_date,
        source_ids=requested_source_ids,
        head_probe=probe,
        base_url=base_url,
    )
    row_hash = binance_vision_availability_rows_hash(rows)
    manifest_id = binance_vision_availability_manifest_id_for(
        start_date=start_date,
        end_date=end_date,
        source_ids=requested_source_ids,
        source_registry_ref=parsed_snapshot.source_registry_ref,
        symbol_map_snapshot_id=parsed_snapshot.symbol_map_snapshot_id,
        row_manifest_hash=row_hash,
    )
    manifest = BinanceVisionAvailabilityManifest(
        availability_manifest_id=manifest_id,
        start_date=start_date,
        end_date=end_date,
        source_ids=requested_source_ids,
        source_registry_ref=parsed_snapshot.source_registry_ref,
        symbol_map_ref=resolved_symbol_map_ref,
        symbol_map_snapshot_id=parsed_snapshot.symbol_map_snapshot_id,
        rows=rows,
        row_count=len(rows),
        available_count=_count_zip_status(rows, BinanceVisionAvailabilityStatus.AVAILABLE),
        missing_count=_count_zip_status(rows, BinanceVisionAvailabilityStatus.MISSING),
        blocked_mapping_count=_count_zip_status(rows, BinanceVisionAvailabilityStatus.BLOCKED_MAPPING),
        probe_error_count=_count_zip_status(rows, BinanceVisionAvailabilityStatus.PROBE_ERROR),
        checksum_available_count=_count_checksum_status(rows, BinanceVisionChecksumStatus.AVAILABLE),
        checksum_missing_count=_count_checksum_status(rows, BinanceVisionChecksumStatus.MISSING),
        row_manifest_hash=row_hash,
    )
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_path = layout.resolve(
        "manifests",
        "source_availability",
        f"binance_vision_availability_{start_date.isoformat()}_{end_date.isoformat()}_{manifest_id[:16]}.json",
    )
    _write_json_model(manifest_path, manifest)
    return BinanceVisionAvailabilityWriteResult(
        availability_manifest_id=manifest_id,
        manifest_ref=layout.relative_to_root(manifest_path),
        manifest_sha256=file_sha256(manifest_path),
        row_count=manifest.row_count,
        available_count=manifest.available_count,
        missing_count=manifest.missing_count,
        blocked_mapping_count=manifest.blocked_mapping_count,
        probe_error_count=manifest.probe_error_count,
        checksum_available_count=manifest.checksum_available_count,
        checksum_missing_count=manifest.checksum_missing_count,
    )


def default_binance_vision_head_probe(url: str) -> BinanceVisionHeadResult:
    try:
        response = httpx.head(url, follow_redirects=True, timeout=20.0)
        return BinanceVisionHeadResult(
            status_code=response.status_code,
            headers={str(key).lower(): str(value) for key, value in response.headers.items()},
        )
    except Exception as exc:
        return BinanceVisionHeadResult(error=type(exc).__name__)


def default_binance_vision_get(url: str) -> BinanceVisionGetResult:
    try:
        response = httpx.get(url, follow_redirects=True, timeout=60.0)
        return BinanceVisionGetResult(
            status_code=response.status_code,
            headers={str(key).lower(): str(value) for key, value in response.headers.items()},
            content=response.content,
        )
    except Exception as exc:
        return BinanceVisionGetResult(error=type(exc).__name__)


def download_binance_vision_availability_row_to_cache(
    *,
    archive_root: str | Path,
    availability_row: BinanceVisionAvailabilityRow,
    get: Callable[[str], BinanceVisionGetResult | Mapping[str, Any]] | None = None,
    force: bool = False,
    max_bytes: int = 250_000_000,
) -> BinanceVisionDownloadResult:
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    get_client = get or default_binance_vision_get
    preflight_blockers = _download_preflight_blockers(availability_row)
    if preflight_blockers:
        result = _build_download_result(
            layout=layout,
            availability_row=availability_row,
            status=BinanceVisionDownloadStatus.BLOCKED,
            max_bytes=max_bytes,
            blocked_reasons=preflight_blockers,
        )
        _write_json_model(layout.resolve(result.download_manifest_ref), result)
        return result

    assert availability_row.zip_url is not None
    zip_path = _download_cache_path(layout, availability_row, suffix="zip")
    zip_cache_hit = zip_path.exists() and not force
    if zip_cache_hit:
        zip_bytes = zip_path.read_bytes()
        if len(zip_bytes) > max_bytes:
            result = _build_download_result(
                layout=layout,
                availability_row=availability_row,
                status=BinanceVisionDownloadStatus.DOWNLOAD_ERROR,
                max_bytes=max_bytes,
                blocked_reasons=("cached_zip_exceeds_max_bytes",),
            )
            _write_json_model(layout.resolve(result.download_manifest_ref), result)
            return result
    else:
        zip_response = _coerce_get_result(get_client(availability_row.zip_url))
        if zip_response.status_code != 200:
            result = _build_download_result(
                layout=layout,
                availability_row=availability_row,
                status=BinanceVisionDownloadStatus.DOWNLOAD_ERROR,
                max_bytes=max_bytes,
                blocked_reasons=_download_error_reasons("zip", zip_response),
            )
            _write_json_model(layout.resolve(result.download_manifest_ref), result)
            return result
        zip_bytes = zip_response.content
        if len(zip_bytes) > max_bytes:
            result = _build_download_result(
                layout=layout,
                availability_row=availability_row,
                status=BinanceVisionDownloadStatus.DOWNLOAD_ERROR,
                max_bytes=max_bytes,
                blocked_reasons=("zip_exceeds_max_bytes",),
            )
            _write_json_model(layout.resolve(result.download_manifest_ref), result)
            return result
        _write_bytes_atomic(zip_path, zip_bytes)

    zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()
    checksum_cache_ref: str | None = None
    checksum_payload_sha256: str | None = None
    checksum_expected_sha256: str | None = None
    checksum_verified = False
    checksum_byte_count = 0
    checksum_cache_hit = False
    if availability_row.checksum_status == BinanceVisionChecksumStatus.AVAILABLE:
        if not availability_row.checksum_url:
            result = _build_download_result(
                layout=layout,
                availability_row=availability_row,
                status=BinanceVisionDownloadStatus.DOWNLOAD_ERROR,
                max_bytes=max_bytes,
                zip_cache_ref=layout.relative_to_root(zip_path),
                zip_sha256=zip_sha256,
                byte_count=len(zip_bytes),
                cache_hit=zip_cache_hit,
                blocked_reasons=("checksum_url_missing",),
            )
            _write_json_model(layout.resolve(result.download_manifest_ref), result)
            return result
        checksum_path = _download_cache_path(layout, availability_row, suffix="CHECKSUM")
        checksum_cache_hit = checksum_path.exists() and not force
        if checksum_cache_hit:
            checksum_bytes = checksum_path.read_bytes()
        else:
            checksum_response = _coerce_get_result(get_client(availability_row.checksum_url))
            if checksum_response.status_code != 200:
                result = _build_download_result(
                    layout=layout,
                    availability_row=availability_row,
                    status=BinanceVisionDownloadStatus.DOWNLOAD_ERROR,
                    max_bytes=max_bytes,
                    zip_cache_ref=layout.relative_to_root(zip_path),
                    zip_sha256=zip_sha256,
                    byte_count=len(zip_bytes),
                    cache_hit=zip_cache_hit,
                    blocked_reasons=_download_error_reasons("checksum", checksum_response),
                )
                _write_json_model(layout.resolve(result.download_manifest_ref), result)
                return result
            checksum_bytes = checksum_response.content
            _write_bytes_atomic(checksum_path, checksum_bytes)
        checksum_cache_ref = layout.relative_to_root(checksum_path)
        checksum_byte_count = len(checksum_bytes)
        checksum_payload_sha256 = hashlib.sha256(checksum_bytes).hexdigest()
        checksum_expected_sha256 = _parse_checksum_payload(checksum_bytes)
        if checksum_expected_sha256 != zip_sha256:
            result = _build_download_result(
                layout=layout,
                availability_row=availability_row,
                status=BinanceVisionDownloadStatus.CHECKSUM_MISMATCH,
                max_bytes=max_bytes,
                zip_cache_ref=layout.relative_to_root(zip_path),
                checksum_cache_ref=checksum_cache_ref,
                zip_sha256=zip_sha256,
                checksum_payload_sha256=checksum_payload_sha256,
                checksum_expected_sha256=checksum_expected_sha256,
                byte_count=len(zip_bytes),
                checksum_byte_count=checksum_byte_count,
                cache_hit=zip_cache_hit and checksum_cache_hit,
                blocked_reasons=("checksum_mismatch",),
            )
            _write_json_model(layout.resolve(result.download_manifest_ref), result)
            return result
        checksum_verified = True

    result = _build_download_result(
        layout=layout,
        availability_row=availability_row,
        status=(
            BinanceVisionDownloadStatus.CACHE_HIT
            if zip_cache_hit
            and (
                availability_row.checksum_status != BinanceVisionChecksumStatus.AVAILABLE
                or checksum_cache_hit
            )
            else BinanceVisionDownloadStatus.DOWNLOADED
        ),
        max_bytes=max_bytes,
        zip_cache_ref=layout.relative_to_root(zip_path),
        checksum_cache_ref=checksum_cache_ref,
        zip_sha256=zip_sha256,
        checksum_payload_sha256=checksum_payload_sha256,
        checksum_expected_sha256=checksum_expected_sha256,
        byte_count=len(zip_bytes),
        checksum_byte_count=checksum_byte_count,
        checksum_verified=checksum_verified,
        cache_hit=zip_cache_hit,
    )
    _write_json_model(layout.resolve(result.download_manifest_ref), result)
    return result


def run_binance_vision_daily_backfill(
    *,
    archive_root: str | Path,
    availability_row: BinanceVisionAvailabilityRow,
    universe_snapshot_ref: str,
    comparison_availability_row: BinanceVisionAvailabilityRow | None = None,
    archive_snapshot_ref: str | None = None,
    get: Callable[[str], BinanceVisionGetResult | Mapping[str, Any]] | None = None,
    force_download: bool = False,
    max_bytes: int = 250_000_000,
    coverage_min: float = 0.98,
) -> BinanceVisionDailyBackfillResult:
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    blocker_reasons: list[str] = []
    target_download = download_binance_vision_availability_row_to_cache(
        archive_root=archive_root,
        availability_row=availability_row,
        get=get,
        force=force_download,
        max_bytes=max_bytes,
    )
    target_parse: BinanceVisionParseResult | None = None
    target_ingest: BinanceVisionArchiveIngestResult | None = None
    comparison_download: BinanceVisionDownloadResult | None = None
    comparison_parse: BinanceVisionParseResult | None = None
    comparison_report: BinanceVisionBarComparisonReport | None = None

    if target_download.status in {
        BinanceVisionDownloadStatus.DOWNLOADED,
        BinanceVisionDownloadStatus.CACHE_HIT,
    }:
        try:
            target_parse = _parse_download_result_from_cache(layout, target_download)
        except Exception as exc:
            blocker_reasons.append(f"target_parse_failed:{type(exc).__name__}")
        if target_parse is not None:
            try:
                target_ingest = ingest_binance_vision_zip_bytes_to_archive(
                    archive_root=archive_root,
                    source_id=availability_row.source_id,
                    symbol=target_parse.binance_symbol,
                    archive_date=availability_row.probe_date,
                    zip_bytes=_read_cached_bytes(layout, target_download.zip_cache_ref),
                    checksum_payload=_read_optional_cached_bytes(layout, target_download.checksum_cache_ref),
                )
            except Exception as exc:
                blocker_reasons.append(f"target_ingest_failed:{type(exc).__name__}")
    else:
        blocker_reasons.extend(target_download.blocked_reasons)

    if (
        target_parse is not None
        and target_parse.row_type == BinanceVisionRowType.KLINE
        and comparison_availability_row is not None
    ):
        comparison_download = download_binance_vision_availability_row_to_cache(
            archive_root=archive_root,
            availability_row=comparison_availability_row,
            get=get,
            force=force_download,
            max_bytes=max_bytes,
        )
        if comparison_download.status in {
            BinanceVisionDownloadStatus.DOWNLOADED,
            BinanceVisionDownloadStatus.CACHE_HIT,
        }:
            try:
                comparison_parse = _parse_download_result_from_cache(layout, comparison_download)
                comparison_report = compare_binance_vision_reconstructed_bars(
                    source_result=comparison_parse,
                    kline_result=target_parse,
                )
            except Exception as exc:
                blocker_reasons.append(f"comparison_failed:{type(exc).__name__}")
        else:
            blocker_reasons.extend(f"comparison_{reason}" for reason in comparison_download.blocked_reasons)

    coverage_report = build_binance_vision_data_family_coverage_report(
        availability_row=availability_row,
        universe_snapshot_ref=universe_snapshot_ref,
        download_result=target_download,
        parse_result=target_parse,
        ingest_result=target_ingest,
        comparison_report=comparison_report,
        archive_snapshot_ref=archive_snapshot_ref,
        coverage_min=coverage_min,
    )
    coverage_ref = _write_data_family_coverage_report(layout, coverage_report)
    blocker_reasons.extend(coverage_report.reason)
    blocker_tuple = tuple(dict.fromkeys(blocker_reasons))
    status = (
        BinanceVisionBackfillStatus.COMPLETED
        if coverage_report.accepted_for_research_reporting and not blocker_tuple
        else BinanceVisionBackfillStatus.BLOCKED
    )
    backfill_id = canonical_json_hash(
        {
            "manifest_type": "binance_vision_daily_backfill_result",
            "source_id": availability_row.source_id,
            "binance_symbol": availability_row.binance_symbol,
            "hyperliquid_coin": availability_row.hyperliquid_coin,
            "probe_date": availability_row.probe_date.isoformat(),
            "target_download_id": target_download.download_id,
            "target_parse_hash": target_parse.normalized_rows_hash if target_parse else None,
            "target_ingest_id": target_ingest.ingest_id if target_ingest else None,
            "comparison_download_id": comparison_download.download_id if comparison_download else None,
            "comparison_parse_hash": comparison_parse.normalized_rows_hash if comparison_parse else None,
            "comparison_report_id": comparison_report.comparison_report_id if comparison_report else None,
            "coverage_report_id": coverage_report.coverage_report_id,
            "accepted_for_research_reporting": coverage_report.accepted_for_research_reporting,
            "blocker_reasons": () if status == BinanceVisionBackfillStatus.COMPLETED else blocker_tuple,
        }
    )
    return BinanceVisionDailyBackfillResult(
        backfill_id=backfill_id,
        status=status,
        source_id=availability_row.source_id,
        binance_symbol=availability_row.binance_symbol,
        hyperliquid_coin=availability_row.hyperliquid_coin,
        probe_date=availability_row.probe_date,
        target_download_id=target_download.download_id,
        target_download_manifest_ref=target_download.download_manifest_ref,
        target_parse_hash=target_parse.normalized_rows_hash if target_parse else None,
        target_ingest_id=target_ingest.ingest_id if target_ingest else None,
        comparison_download_id=comparison_download.download_id if comparison_download else None,
        comparison_parse_hash=comparison_parse.normalized_rows_hash if comparison_parse else None,
        comparison_report_id=comparison_report.comparison_report_id if comparison_report else None,
        coverage_report_id=coverage_report.coverage_report_id,
        coverage_report_ref=coverage_ref,
        accepted_for_research_reporting=coverage_report.accepted_for_research_reporting,
        blocker_reasons=() if status == BinanceVisionBackfillStatus.COMPLETED else blocker_tuple,
    )


def run_binance_vision_backfill_batch(
    *,
    archive_root: str | Path,
    availability_manifest: BinanceVisionAvailabilityManifest | Mapping[str, Any],
    target_source_id: str,
    universe_snapshot_ref: str,
    comparison_source_id: str | None = None,
    archive_snapshot_ref: str | None = None,
    get: Callable[[str], BinanceVisionGetResult | Mapping[str, Any]] | None = None,
    force_download: bool = False,
    max_bytes: int = 250_000_000,
    coverage_min: float = 0.98,
    max_rows: int = 100,
) -> BinanceVisionBackfillBatchResult:
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest = (
        availability_manifest
        if isinstance(availability_manifest, BinanceVisionAvailabilityManifest)
        else BinanceVisionAvailabilityManifest.model_validate(dict(availability_manifest))
    )
    target_rows = tuple(
        row for row in manifest.rows if row.source_id == target_source_id
    )[:max_rows]
    comparison_rows: dict[tuple[str | None, date], BinanceVisionAvailabilityRow] = {}
    if comparison_source_id is not None:
        comparison_rows = {
            (row.binance_symbol, row.probe_date): row
            for row in manifest.rows
            if row.source_id == comparison_source_id
        }
    daily_results = tuple(
        run_binance_vision_daily_backfill(
            archive_root=archive_root,
            availability_row=row,
            comparison_availability_row=comparison_rows.get((row.binance_symbol, row.probe_date)),
            universe_snapshot_ref=universe_snapshot_ref,
            archive_snapshot_ref=archive_snapshot_ref,
            get=get,
            force_download=force_download,
            max_bytes=max_bytes,
            coverage_min=coverage_min,
        )
        for row in target_rows
    )
    blocker_reasons = tuple(
        dict.fromkeys(
            reason
            for result in daily_results
            for reason in result.blocker_reasons
        )
    )
    daily_result_ids = tuple(result.backfill_id for result in daily_results)
    batch_id = canonical_json_hash(
        {
            "manifest_type": "binance_vision_backfill_batch",
            "availability_manifest_id": manifest.availability_manifest_id,
            "target_source_id": target_source_id,
            "comparison_source_id": comparison_source_id,
            "max_rows": max_rows,
            "daily_result_ids": daily_result_ids,
            "blocker_reasons": blocker_reasons,
        }
    )
    batch_ref = _backfill_batch_manifest_ref(batch_id)
    result = BinanceVisionBackfillBatchResult(
        batch_id=batch_id,
        batch_manifest_ref=batch_ref,
        availability_manifest_id=manifest.availability_manifest_id,
        target_source_id=target_source_id,
        comparison_source_id=comparison_source_id,
        selected_count=len(daily_results),
        completed_count=sum(
            1 for daily in daily_results if daily.status == BinanceVisionBackfillStatus.COMPLETED
        ),
        blocked_count=sum(
            1 for daily in daily_results if daily.status == BinanceVisionBackfillStatus.BLOCKED
        ),
        accepted_count=sum(1 for daily in daily_results if daily.accepted_for_research_reporting),
        max_rows=max_rows,
        daily_results=daily_results,
        daily_result_ids=daily_result_ids,
        blocker_reasons=blocker_reasons,
    )
    _write_json_model(layout.resolve(batch_ref), result)
    return result


def parse_binance_vision_zip_bytes(
    *,
    source_id: str,
    symbol: str,
    zip_bytes: bytes,
    checksum_payload: bytes | str | None = None,
) -> BinanceVisionParseResult:
    spec = binance_vision_source_spec(source_id)
    normalized_symbol = _normalize_binance_symbol(symbol)
    zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()
    expected_checksum = _parse_checksum_payload(checksum_payload)
    checksum_verified = False
    if expected_checksum is not None:
        if expected_checksum != zip_sha256:
            raise ValueError(
                f"Binance Vision checksum mismatch: expected {expected_checksum}, observed {zip_sha256}"
            )
        checksum_verified = True
    csv_member, csv_text = _read_single_csv_from_zip(zip_bytes)
    raw_rows = _parse_csv_text(csv_text, spec)
    parsed_rows = tuple(
        sorted(
            (
                _parse_binance_vision_row(
                    row,
                    source_id=source_id,
                    symbol=normalized_symbol,
                    spec=spec,
                    source_row_index=index,
                )
                for index, row in enumerate(raw_rows)
            ),
            key=lambda item: (item.event_time_ms, item.source_row_index),
        )
    )
    event_times_in_input = [
        _event_time_from_raw(row, spec)
        for row in raw_rows
    ]
    duplicate_ids = _duplicate_ids(parsed_rows)
    gap_count, interval_status = _gap_and_interval_status(parsed_rows, spec)
    warnings: list[str] = []
    input_monotonic = event_times_in_input == sorted(event_times_in_input)
    if not input_monotonic:
        warnings.append("input_timestamps_not_monotonic")
    if duplicate_ids:
        warnings.append("duplicate_event_ids")
    if gap_count:
        warnings.append("kline_interval_gaps")
    if interval_status == "misaligned":
        warnings.append("kline_interval_misaligned")
    row_hash = manifest_rows_hash(row.model_dump(mode="json") for row in parsed_rows)
    return BinanceVisionParseResult(
        source_id=source_id,
        binance_symbol=normalized_symbol,
        family=spec.family,
        row_type=_row_type_for_spec(spec),
        archive_member=csv_member,
        zip_sha256=zip_sha256,
        checksum_verified=checksum_verified,
        checksum_expected_sha256=expected_checksum,
        row_count=len(parsed_rows),
        duplicate_count=len(duplicate_ids),
        duplicate_ids=duplicate_ids,
        gap_count=gap_count,
        input_monotonic=input_monotonic,
        interval_alignment_status=interval_status,
        normalized_rows_hash=row_hash,
        rows=parsed_rows,
        warnings=tuple(warnings),
    )


def ingest_binance_vision_zip_bytes_to_archive(
    *,
    archive_root: str | Path,
    source_id: str,
    symbol: str,
    archive_date: date,
    zip_bytes: bytes,
    checksum_payload: bytes | str | None = None,
    instrument_id: str | None = None,
    run_id: str | None = None,
    job_id: str | None = None,
    storage_budget_bytes: int = 50_000_000,
) -> BinanceVisionArchiveIngestResult:
    parse_result = parse_binance_vision_zip_bytes(
        source_id=source_id,
        symbol=symbol,
        zip_bytes=zip_bytes,
        checksum_payload=checksum_payload,
    )
    spec = binance_vision_source_spec(source_id)
    resolved_instrument_id = instrument_id or _default_binance_instrument_id(
        parse_result.binance_symbol,
        market_type=spec.market_type,
    )
    ingest_id = canonical_json_hash(
        {
            "source_id": source_id,
            "symbol": parse_result.binance_symbol,
            "archive_date": archive_date.isoformat(),
            "zip_sha256": parse_result.zip_sha256,
            "instrument_id": resolved_instrument_id,
            "schema_version": V2_SCHEMA_VERSION,
        }
    )
    resolved_job_id = job_id or f"binance-vision-ingest-{ingest_id[:16]}"
    resolved_run_id = run_id or resolved_job_id
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    parser_manifest_path = layout.resolve(
        "manifests",
        "binance_vision_parse_results",
        f"{ingest_id}.json",
    )
    _write_json_model(parser_manifest_path, parse_result)
    if parse_result.row_type == BinanceVisionRowType.KLINE:
        raw_file_id, bronze_file_id, silver_file_id = _ingest_kline_rows(
            layout=layout,
            parse_result=parse_result,
            archive_date=archive_date,
            instrument_id=resolved_instrument_id,
            run_id=resolved_run_id,
            job_id=resolved_job_id,
        )
        quality_report_id = None
        storage_report_id = None
    else:
        raw_file_id, quality_report_id, storage_report_id = _ingest_trade_rows(
            archive_root=archive_root,
            parse_result=parse_result,
            archive_date=archive_date,
            instrument_id=resolved_instrument_id,
            run_id=resolved_run_id,
            job_id=resolved_job_id,
            storage_budget_bytes=storage_budget_bytes,
        )
        bronze_file_id = None
        silver_file_id = None
    return BinanceVisionArchiveIngestResult(
        ingest_id=ingest_id,
        source_id=source_id,
        binance_symbol=parse_result.binance_symbol,
        instrument_id=resolved_instrument_id,
        archive_date=archive_date,
        row_type=parse_result.row_type,
        row_count=parse_result.row_count,
        duplicate_count=parse_result.duplicate_count,
        gap_count=parse_result.gap_count,
        input_monotonic=parse_result.input_monotonic,
        interval_alignment_status=parse_result.interval_alignment_status,
        zip_sha256=parse_result.zip_sha256,
        checksum_verified=parse_result.checksum_verified,
        parser_manifest_ref=layout.relative_to_root(parser_manifest_path),
        raw_file_id=raw_file_id,
        bronze_file_id=bronze_file_id,
        silver_file_id=silver_file_id,
        microstructure_quality_report_id=quality_report_id,
        storage_report_id=storage_report_id,
    )


def compare_binance_vision_reconstructed_bars(
    *,
    source_result: BinanceVisionParseResult,
    kline_result: BinanceVisionParseResult,
    price_abs_tolerance: float = 1e-9,
    volume_abs_tolerance: float = 1e-9,
) -> BinanceVisionBarComparisonReport:
    if price_abs_tolerance < 0 or volume_abs_tolerance < 0:
        raise ValueError("comparison tolerances must be non-negative")
    if source_result.row_type not in {BinanceVisionRowType.TRADE, BinanceVisionRowType.AGG_TRADE}:
        raise ValueError("source_result must contain trade or agg_trade rows")
    if kline_result.row_type != BinanceVisionRowType.KLINE:
        raise ValueError("kline_result must contain kline rows")
    if source_result.binance_symbol != kline_result.binance_symbol:
        raise ValueError("source_result and kline_result symbols must match")
    reconstructed = _reconstruct_minute_bars(source_result)
    comparison_rows = tuple(
        _compare_one_kline_bucket(
            kline_row=kline_row,
            reconstructed=reconstructed.get(kline_row.event_time_ms),
            price_abs_tolerance=price_abs_tolerance,
            volume_abs_tolerance=volume_abs_tolerance,
        )
        for kline_row in kline_result.rows
    )
    blocker_reasons: list[str] = []
    if any(row.status == "missing_reconstructed" for row in comparison_rows):
        blocker_reasons.append("missing_reconstructed_buckets")
    if any(row.status == "failed" for row in comparison_rows):
        blocker_reasons.append("ohlcv_tolerance_failed")
    max_close_abs_diff = max(
        (row.close_abs_diff or 0.0 for row in comparison_rows),
        default=0.0,
    )
    rows_hash = manifest_rows_hash(row.model_dump(mode="json") for row in comparison_rows)
    report_id = canonical_json_hash(
        {
            "report_type": "binance_vision_reconstructed_bar_comparison",
            "binance_symbol": kline_result.binance_symbol,
            "source_row_type": source_result.row_type.value,
            "kline_rows_hash": kline_result.normalized_rows_hash,
            "source_rows_hash": source_result.normalized_rows_hash,
            "price_abs_tolerance": price_abs_tolerance,
            "volume_abs_tolerance": volume_abs_tolerance,
            "rows_hash": rows_hash,
        }
    )
    return BinanceVisionBarComparisonReport(
        comparison_report_id=report_id,
        binance_symbol=kline_result.binance_symbol,
        source_row_type=source_result.row_type,
        kline_rows_hash=kline_result.normalized_rows_hash,
        source_rows_hash=source_result.normalized_rows_hash,
        price_abs_tolerance=price_abs_tolerance,
        volume_abs_tolerance=volume_abs_tolerance,
        compared_bucket_count=len(comparison_rows),
        passed_bucket_count=sum(1 for row in comparison_rows if row.status == "passed"),
        failed_bucket_count=sum(1 for row in comparison_rows if row.status == "failed"),
        missing_reconstructed_count=sum(
            1 for row in comparison_rows if row.status == "missing_reconstructed"
        ),
        max_close_abs_diff=max_close_abs_diff,
        passed=not blocker_reasons,
        blocker_reasons=tuple(blocker_reasons),
        rows=comparison_rows,
    )


def build_binance_vision_data_family_coverage_report(
    *,
    availability_row: BinanceVisionAvailabilityRow,
    universe_snapshot_ref: str,
    download_result: BinanceVisionDownloadResult | None = None,
    parse_result: BinanceVisionParseResult | None = None,
    ingest_result: BinanceVisionArchiveIngestResult | None = None,
    comparison_report: BinanceVisionBarComparisonReport | None = None,
    archive_snapshot_ref: str | None = None,
    coverage_min: float = 0.98,
) -> DataFamilyCoverageReport:
    """Build a fail-closed data-family coverage report for one Binance Vision day."""

    if coverage_min < 0 or coverage_min > 1:
        raise ValueError("coverage_min must be between 0 and 1")
    if availability_row.native_to_hyperliquid:
        raise ValueError("Binance Vision coverage cannot be Hyperliquid-native")
    _validate_coverage_download_result(availability_row, download_result)
    _validate_coverage_parse_result(availability_row, parse_result)
    _validate_coverage_ingest_result(availability_row, ingest_result)
    _validate_coverage_comparison_result(parse_result, comparison_report)

    expected_bucket_seconds, expected_count = _coverage_expected_bucket_spec(availability_row)
    observed_bucket_keys = _coverage_observed_bucket_keys(
        availability_row=availability_row,
        parse_result=parse_result,
        ingest_result=ingest_result,
    )
    observed_count = min(len(observed_bucket_keys), expected_count)
    missing_buckets = _coverage_missing_buckets(
        availability_row=availability_row,
        expected_count=expected_count,
        expected_bucket_seconds=expected_bucket_seconds,
        observed_bucket_keys=observed_bucket_keys,
    )
    coverage_ratio = observed_count / expected_count if expected_count else 0.0
    reasons = _coverage_blocker_reasons(
        availability_row=availability_row,
        download_result=download_result,
        parse_result=parse_result,
        ingest_result=ingest_result,
        comparison_report=comparison_report,
        archive_snapshot_ref=archive_snapshot_ref,
        coverage_ratio=coverage_ratio,
        coverage_min=coverage_min,
        expected_count=expected_count,
    )
    accepted = not reasons and coverage_ratio >= coverage_min
    identity = {
        "manifest_type": "data_family_coverage_report",
        "source_id": availability_row.source_id,
        "symbol_map_snapshot_id": availability_row.symbol_map_snapshot_id,
        "hyperliquid_coin": availability_row.hyperliquid_coin,
        "binance_symbol": availability_row.binance_symbol,
        "probe_date": availability_row.probe_date.isoformat(),
        "data_family": availability_row.data_family,
        "expected_bucket_seconds": expected_bucket_seconds,
        "expected_count": expected_count,
        "observed_count": observed_count,
        "coverage_ratio": round(coverage_ratio, 12),
        "missing_buckets_hash": manifest_rows_hash({"bucket": bucket} for bucket in missing_buckets),
        "availability_zip_status": availability_row.zip_status.value,
        "checksum_status": availability_row.checksum_status.value,
        "download_id": download_result.download_id if download_result else None,
        "download_status": (
            _download_identity_status(download_result.status)
            if download_result is not None
            else None
        ),
        "parse_hash": parse_result.normalized_rows_hash if parse_result else None,
        "ingest_id": ingest_result.ingest_id if ingest_result else None,
        "comparison_report_id": comparison_report.comparison_report_id if comparison_report else None,
        "archive_snapshot_ref": archive_snapshot_ref,
        "coverage_min": coverage_min,
        "reasons": reasons,
    }
    return DataFamilyCoverageReport(
        coverage_report_id=canonical_json_hash(identity),
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=availability_row.source_registry_ref,
        symbol_map_ref=availability_row.symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol=availability_row.hyperliquid_coin,
        family=availability_row.data_family,
        venue="binance",
        source_ids=(availability_row.source_id,),
        source_cost_classes=(availability_row.source_cost_class,),
        labels=(CoverageLabel.EXTERNAL_COMPARISON,),
        coverage_window=CoverageWindow(
            start=_coverage_day_start(availability_row.probe_date),
            end=_coverage_day_start(availability_row.probe_date + timedelta(days=1)),
        ),
        expected_buckets=ExpectedBuckets(
            bucket_seconds=expected_bucket_seconds,
            count=expected_count,
        ),
        observed_buckets=observed_count,
        coverage_ratio=coverage_ratio,
        coverage_min=coverage_min,
        missing_buckets=missing_buckets,
        accepted_for_research_reporting=accepted,
        reason=reasons,
    )


def _validate_coverage_parse_result(
    availability_row: BinanceVisionAvailabilityRow,
    parse_result: BinanceVisionParseResult | None,
) -> None:
    if parse_result is None:
        return
    expected_row_type = _row_type_for_source_id(availability_row.source_id)
    if parse_result.source_id != availability_row.source_id:
        raise ValueError("parse_result source_id does not match availability row")
    if availability_row.binance_symbol and parse_result.binance_symbol != availability_row.binance_symbol:
        raise ValueError("parse_result symbol does not match availability row")
    if parse_result.row_type != expected_row_type:
        raise ValueError("parse_result row_type does not match availability source")


def _validate_coverage_download_result(
    availability_row: BinanceVisionAvailabilityRow,
    download_result: BinanceVisionDownloadResult | None,
) -> None:
    if download_result is None:
        return
    if download_result.source_id != availability_row.source_id:
        raise ValueError("download_result source_id does not match availability row")
    if download_result.symbol_map_snapshot_id != availability_row.symbol_map_snapshot_id:
        raise ValueError("download_result symbol-map snapshot does not match availability row")
    if download_result.probe_date != availability_row.probe_date:
        raise ValueError("download_result date does not match availability row")
    if availability_row.binance_symbol and download_result.binance_symbol != availability_row.binance_symbol:
        raise ValueError("download_result symbol does not match availability row")


def _validate_coverage_ingest_result(
    availability_row: BinanceVisionAvailabilityRow,
    ingest_result: BinanceVisionArchiveIngestResult | None,
) -> None:
    if ingest_result is None:
        return
    expected_row_type = _row_type_for_source_id(availability_row.source_id)
    if ingest_result.source_id != availability_row.source_id:
        raise ValueError("ingest_result source_id does not match availability row")
    if availability_row.binance_symbol and ingest_result.binance_symbol != availability_row.binance_symbol:
        raise ValueError("ingest_result symbol does not match availability row")
    if ingest_result.archive_date != availability_row.probe_date:
        raise ValueError("ingest_result archive_date does not match availability row")
    if ingest_result.row_type != expected_row_type:
        raise ValueError("ingest_result row_type does not match availability source")


def _validate_coverage_comparison_result(
    parse_result: BinanceVisionParseResult | None,
    comparison_report: BinanceVisionBarComparisonReport | None,
) -> None:
    if comparison_report is None:
        return
    if parse_result is None:
        raise ValueError("comparison_report requires parse_result evidence")
    if parse_result.row_type != BinanceVisionRowType.KLINE:
        raise ValueError("comparison_report can only be attached to kline coverage")
    if comparison_report.binance_symbol != parse_result.binance_symbol:
        raise ValueError("comparison_report symbol does not match parse_result")
    if comparison_report.kline_rows_hash != parse_result.normalized_rows_hash:
        raise ValueError("comparison_report kline hash does not match parse_result")


def _coverage_expected_bucket_spec(availability_row: BinanceVisionAvailabilityRow) -> tuple[int, int]:
    if _row_type_for_source_id(availability_row.source_id) == BinanceVisionRowType.KLINE:
        return 60, 24 * 60
    return 24 * 60 * 60, 1


def _coverage_observed_bucket_keys(
    *,
    availability_row: BinanceVisionAvailabilityRow,
    parse_result: BinanceVisionParseResult | None,
    ingest_result: BinanceVisionArchiveIngestResult | None,
) -> set[int]:
    if availability_row.zip_status != BinanceVisionAvailabilityStatus.AVAILABLE:
        return set()
    _ = ingest_result
    if parse_result is None or parse_result.row_count == 0:
        return set()
    if parse_result.row_type != BinanceVisionRowType.KLINE:
        return {0}
    day_start_ms = _coverage_day_start_ms(availability_row.probe_date)
    day_end_ms = day_start_ms + 24 * 60 * 60 * 1000
    return {
        int((row.event_time_ms - day_start_ms) // 60_000)
        for row in parse_result.rows
        if day_start_ms <= row.event_time_ms < day_end_ms
    }


def _coverage_missing_buckets(
    *,
    availability_row: BinanceVisionAvailabilityRow,
    expected_count: int,
    expected_bucket_seconds: int,
    observed_bucket_keys: set[int],
) -> tuple[str, ...]:
    if expected_count == 1:
        if observed_bucket_keys:
            return ()
        return (_coverage_day_start(availability_row.probe_date).isoformat(),)
    start = _coverage_day_start(availability_row.probe_date)
    return tuple(
        (start + timedelta(seconds=expected_bucket_seconds * index)).isoformat()
        for index in range(expected_count)
        if index not in observed_bucket_keys
    )


def _coverage_blocker_reasons(
    *,
    availability_row: BinanceVisionAvailabilityRow,
    download_result: BinanceVisionDownloadResult | None,
    parse_result: BinanceVisionParseResult | None,
    ingest_result: BinanceVisionArchiveIngestResult | None,
    comparison_report: BinanceVisionBarComparisonReport | None,
    archive_snapshot_ref: str | None,
    coverage_ratio: float,
    coverage_min: float,
    expected_count: int,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if availability_row.zip_status == BinanceVisionAvailabilityStatus.BLOCKED_MAPPING:
        reasons.extend(availability_row.blocked_reasons or ("mapping_blocked",))
    elif availability_row.zip_status == BinanceVisionAvailabilityStatus.MISSING:
        reasons.append("source_zip_missing")
    elif availability_row.zip_status == BinanceVisionAvailabilityStatus.PROBE_ERROR:
        reasons.append("availability_probe_error")

    if download_result is not None and download_result.status not in {
        BinanceVisionDownloadStatus.DOWNLOADED,
        BinanceVisionDownloadStatus.CACHE_HIT,
    }:
        reasons.extend(download_result.blocked_reasons)
        reasons.append(f"download_status_{download_result.status.value}")

    if availability_row.zip_status == BinanceVisionAvailabilityStatus.AVAILABLE:
        if parse_result is None:
            reasons.append("parse_result_missing")
        if ingest_result is None:
            reasons.append("ingest_result_missing")
        if archive_snapshot_ref is None:
            reasons.append("archive_snapshot_ref_missing")

    if parse_result is not None:
        if parse_result.row_count == 0:
            reasons.append("parsed_rows_empty")
        if parse_result.duplicate_count:
            reasons.append("duplicate_native_ids_detected")
        if not parse_result.input_monotonic:
            reasons.append("input_timestamps_not_monotonic")
        if availability_row.checksum_status == BinanceVisionChecksumStatus.AVAILABLE and not parse_result.checksum_verified:
            reasons.append("checksum_available_but_not_verified")
        if parse_result.row_type == BinanceVisionRowType.KLINE:
            if parse_result.gap_count:
                reasons.append("kline_gap_detected")
            if parse_result.interval_alignment_status != "aligned":
                reasons.append("kline_interval_not_aligned")
            if comparison_report is None:
                reasons.append("reconstructed_bar_comparison_missing")
            elif not comparison_report.passed:
                reasons.extend(comparison_report.blocker_reasons)

    if coverage_ratio < coverage_min:
        reasons.append("coverage_below_minimum")
    if expected_count > 1 and coverage_ratio < 1.0:
        reasons.append("parsed_rows_partial")
    return tuple(dict.fromkeys(reasons))


def _coverage_day_start(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def _coverage_day_start_ms(day: date) -> int:
    return int(_coverage_day_start(day).timestamp() * 1000)


def _row_type_for_source_id(source_id: str) -> BinanceVisionRowType:
    return _row_type_for_spec(binance_vision_source_spec(source_id))


def _download_preflight_blockers(
    availability_row: BinanceVisionAvailabilityRow,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if availability_row.source_cost_class not in {
        CostClass.ZERO_COST_PUBLIC,
        CostClass.PUBLIC_RATE_LIMITED,
    }:
        reasons.append("source_cost_class_not_strict_free_backfill")
    if availability_row.native_to_hyperliquid:
        reasons.append("binance_vision_row_marked_native_to_hyperliquid")
    if availability_row.zip_status != BinanceVisionAvailabilityStatus.AVAILABLE:
        reasons.append(f"zip_status_{availability_row.zip_status.value}")
        reasons.extend(availability_row.blocked_reasons)
    if not availability_row.zip_url:
        reasons.append("zip_url_missing")
    return tuple(dict.fromkeys(reasons))


def _download_cache_path(
    layout: ArchiveLayout,
    availability_row: BinanceVisionAvailabilityRow,
    *,
    suffix: str,
) -> Path:
    symbol = availability_row.binance_symbol or "unknown"
    interval = availability_row.interval or "na"
    filename = (
        f"{availability_row.source_id}-{symbol}-"
        f"{interval}-{availability_row.probe_date.isoformat()}.{suffix}"
    )
    parts = [
        "raw",
        partition("venue", "binance"),
        partition("source", availability_row.source_id),
        partition("family", availability_row.data_family),
        partition("symbol", symbol),
        partition("date", availability_row.probe_date.isoformat()),
    ]
    return layout.resolve(
        *(part for part in parts if part is not None),
        safe_partition_value(filename),
    )


def _build_download_result(
    *,
    layout: ArchiveLayout,
    availability_row: BinanceVisionAvailabilityRow,
    status: BinanceVisionDownloadStatus,
    max_bytes: int,
    zip_cache_ref: str | None = None,
    checksum_cache_ref: str | None = None,
    zip_sha256: str | None = None,
    checksum_payload_sha256: str | None = None,
    checksum_expected_sha256: str | None = None,
    byte_count: int = 0,
    checksum_byte_count: int = 0,
    checksum_verified: bool = False,
    cache_hit: bool = False,
    blocked_reasons: tuple[str, ...] = (),
) -> BinanceVisionDownloadResult:
    download_id = _binance_vision_download_id(
        availability_row=availability_row,
        status=status,
        zip_sha256=zip_sha256,
        checksum_expected_sha256=checksum_expected_sha256,
        blocked_reasons=blocked_reasons,
        max_bytes=max_bytes,
    )
    manifest_ref = _download_manifest_ref(download_id)
    return BinanceVisionDownloadResult(
        download_id=download_id,
        download_manifest_ref=manifest_ref,
        status=status,
        source_id=availability_row.source_id,
        source_registry_ref=availability_row.source_registry_ref,
        symbol_map_ref=availability_row.symbol_map_ref,
        symbol_map_snapshot_id=availability_row.symbol_map_snapshot_id,
        hyperliquid_coin=availability_row.hyperliquid_coin,
        binance_symbol=availability_row.binance_symbol,
        probe_date=availability_row.probe_date,
        market_scope=availability_row.market_scope,
        market_type=availability_row.market_type,
        family=availability_row.family,
        data_family=availability_row.data_family,
        interval=availability_row.interval,
        zip_url=availability_row.zip_url,
        checksum_url=availability_row.checksum_url,
        zip_cache_ref=zip_cache_ref,
        checksum_cache_ref=checksum_cache_ref,
        zip_sha256=zip_sha256,
        checksum_payload_sha256=checksum_payload_sha256,
        checksum_expected_sha256=checksum_expected_sha256,
        byte_count=byte_count,
        checksum_byte_count=checksum_byte_count,
        checksum_verified=checksum_verified,
        cache_hit=cache_hit,
        max_bytes=max_bytes,
        source_cost_class=availability_row.source_cost_class,
        blocked_reasons=blocked_reasons,
    )


def _binance_vision_download_id(
    *,
    availability_row: BinanceVisionAvailabilityRow,
    status: BinanceVisionDownloadStatus,
    zip_sha256: str | None,
    checksum_expected_sha256: str | None,
    blocked_reasons: tuple[str, ...],
    max_bytes: int,
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "binance_vision_download_manifest",
            "source_id": availability_row.source_id,
            "symbol_map_snapshot_id": availability_row.symbol_map_snapshot_id,
            "hyperliquid_coin": availability_row.hyperliquid_coin,
            "binance_symbol": availability_row.binance_symbol,
            "probe_date": availability_row.probe_date.isoformat(),
            "zip_url": availability_row.zip_url,
            "checksum_url": availability_row.checksum_url,
            "status": _download_identity_status(status),
            "zip_sha256": zip_sha256,
            "checksum_expected_sha256": checksum_expected_sha256,
            "blocked_reasons": blocked_reasons,
            "max_bytes": max_bytes,
        }
    )


def _download_identity_status(status: BinanceVisionDownloadStatus) -> str:
    if status in {
        BinanceVisionDownloadStatus.DOWNLOADED,
        BinanceVisionDownloadStatus.CACHE_HIT,
    }:
        return "cached_payload_available"
    return status.value


def _download_manifest_ref(download_id: str) -> str:
    return (
        "manifests/source_downloads/"
        f"binance_vision_download_{download_id[:16]}.json"
    )


def _backfill_batch_manifest_ref(batch_id: str) -> str:
    return (
        "manifests/binance_vision_backfills/"
        f"binance_vision_backfill_batch_{batch_id[:16]}.json"
    )


def _coerce_get_result(value: BinanceVisionGetResult | Mapping[str, Any]) -> BinanceVisionGetResult:
    if isinstance(value, BinanceVisionGetResult):
        return value
    return BinanceVisionGetResult.model_validate(dict(value))


def _download_error_reasons(prefix: str, result: BinanceVisionGetResult) -> tuple[str, ...]:
    if result.error:
        return (f"{prefix}_download_error:{result.error}",)
    if result.status_code is None:
        return (f"{prefix}_download_error:no_status",)
    return (f"{prefix}_download_http_status:{result.status_code}",)


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_bytes(payload)
    tmp_path.replace(path)


def _parse_download_result_from_cache(
    layout: ArchiveLayout,
    download_result: BinanceVisionDownloadResult,
) -> BinanceVisionParseResult:
    return parse_binance_vision_zip_bytes(
        source_id=download_result.source_id,
        symbol=download_result.binance_symbol or "",
        zip_bytes=_read_cached_bytes(layout, download_result.zip_cache_ref),
        checksum_payload=_read_optional_cached_bytes(layout, download_result.checksum_cache_ref),
    )


def _read_cached_bytes(layout: ArchiveLayout, ref: str | None) -> bytes:
    if not ref:
        raise ValueError("cache ref missing")
    return layout.resolve(ref).read_bytes()


def _read_optional_cached_bytes(layout: ArchiveLayout, ref: str | None) -> bytes | None:
    if not ref:
        return None
    return layout.resolve(ref).read_bytes()


def _write_data_family_coverage_report(
    layout: ArchiveLayout,
    report: DataFamilyCoverageReport,
) -> str:
    path = layout.resolve(
        "manifests",
        "coverage_reports",
        f"data_family_coverage_{report.coverage_report_id[:16]}.json",
    )
    _write_json_model(path, report)
    return layout.relative_to_root(path)


def _validated_source_entries(
    source_entries: Iterable[SourceRegistryEntry | Mapping[str, Any]],
    source_ids: tuple[str, ...],
) -> dict[str, SourceRegistryEntry]:
    materialized = [
        entry if isinstance(entry, SourceRegistryEntry) else SourceRegistryEntry.model_validate(dict(entry))
        for entry in source_entries
    ]
    entries = {entry.source_id: entry for entry in materialized}
    missing = [source_id for source_id in source_ids if source_id not in entries]
    if missing:
        raise ValueError("missing Binance Vision source entries: " + ",".join(missing))
    for source_id in source_ids:
        spec = binance_vision_source_spec(source_id)
        entry = entries[source_id]
        require_strict_zero_dollar_source(entry)
        if not entry.accepted_under_strict_free:
            raise ValueError(f"{source_id} is not accepted under strict-free mode")
        if entry.venue != "binance" or entry.native_to_hyperliquid:
            raise ValueError(f"{source_id} must be a non-Hyperliquid-native Binance source")
        if entry.market_type != spec.market_type:
            raise ValueError(f"{source_id} market_type does not match Binance Vision spec")
        if spec.data_family not in entry.data_families:
            raise ValueError(f"{source_id} is missing data family {spec.data_family}")
    return entries


def _build_availability_rows(
    *,
    snapshot: SymbolMapSnapshot,
    symbol_map_ref: str,
    entries_by_id: Mapping[str, SourceRegistryEntry],
    start_date: date,
    end_date: date,
    source_ids: tuple[str, ...],
    head_probe: HeadProbe,
    base_url: str,
) -> tuple[BinanceVisionAvailabilityRow, ...]:
    rows: list[BinanceVisionAvailabilityRow] = []
    liquid_rows = [
        row
        for row in snapshot.symbol_map_rows
        if row.hyperliquid_liquid_as_of and row.above_day_notional_threshold
    ]
    for symbol_row in sorted(liquid_rows, key=lambda item: item.hyperliquid_coin):
        for source_id in source_ids:
            spec = binance_vision_source_spec(source_id)
            entry = entries_by_id[source_id]
            try:
                mapping_ref = require_verified_external_mapping(symbol_row, spec.venue_key)
                binance_symbol = mapping_ref.symbol
            except ValueError as exc:
                rows.extend(
                    _blocked_mapping_rows(
                        snapshot=snapshot,
                        symbol_map_ref=symbol_map_ref,
                        source_entry=entry,
                        spec=spec,
                        hyperliquid_coin=symbol_row.hyperliquid_coin,
                        start_date=start_date,
                        end_date=end_date,
                        reason=str(exc),
                    )
                )
                continue
            for day in _date_range(start_date, end_date):
                zip_url = binance_vision_daily_zip_url(
                    source_id=source_id,
                    symbol=binance_symbol,
                    day=day,
                    base_url=base_url,
                )
                zip_probe = _coerce_head_result(head_probe(zip_url))
                zip_status = _zip_status(zip_probe)
                checksum_url = binance_vision_checksum_url(zip_url)
                checksum_probe = None
                if zip_status == BinanceVisionAvailabilityStatus.AVAILABLE:
                    checksum_probe = _coerce_head_result(head_probe(checksum_url))
                checksum_status = _checksum_status(checksum_probe)
                rows.append(
                    BinanceVisionAvailabilityRow(
                        source_id=source_id,
                        source_registry_ref=snapshot.source_registry_ref,
                        symbol_map_ref=symbol_map_ref,
                        symbol_map_snapshot_id=snapshot.symbol_map_snapshot_id,
                        hyperliquid_coin=symbol_row.hyperliquid_coin,
                        venue_key=spec.venue_key,
                        binance_symbol=binance_symbol,
                        probe_date=day,
                        market_scope=spec.market_scope,
                        market_type=spec.market_type,
                        family=spec.family,
                        data_family=spec.data_family,
                        interval=spec.interval,
                        zip_url=zip_url,
                        checksum_url=checksum_url,
                        zip_status=zip_status,
                        checksum_status=checksum_status,
                        http_status_code=zip_probe.status_code,
                        checksum_http_status_code=(
                            checksum_probe.status_code if checksum_probe is not None else None
                        ),
                        content_length_bytes=_content_length(zip_probe),
                        checksum_content_length_bytes=(
                            _content_length(checksum_probe) if checksum_probe is not None else None
                        ),
                        source_cost_class=entry.cost_class,
                        blocked_reasons=_blocked_reasons_for_probe(zip_probe),
                        probe_error=zip_probe.error,
                    )
                )
    return tuple(rows)


def _blocked_mapping_rows(
    *,
    snapshot: SymbolMapSnapshot,
    symbol_map_ref: str,
    source_entry: SourceRegistryEntry,
    spec: BinanceVisionSourceSpec,
    hyperliquid_coin: str,
    start_date: date,
    end_date: date,
    reason: str,
) -> list[BinanceVisionAvailabilityRow]:
    return [
        BinanceVisionAvailabilityRow(
            source_id=spec.source_id,
            source_registry_ref=snapshot.source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            symbol_map_snapshot_id=snapshot.symbol_map_snapshot_id,
            hyperliquid_coin=hyperliquid_coin,
            venue_key=spec.venue_key,
            probe_date=day,
            market_scope=spec.market_scope,
            market_type=spec.market_type,
            family=spec.family,
            data_family=spec.data_family,
            interval=spec.interval,
            zip_status=BinanceVisionAvailabilityStatus.BLOCKED_MAPPING,
            checksum_status=BinanceVisionChecksumStatus.NOT_CHECKED,
            source_cost_class=source_entry.cost_class,
            blocked_reasons=(reason,),
        )
        for day in _date_range(start_date, end_date)
    ]


def _date_range(start_date: date, end_date: date) -> tuple[date, ...]:
    days: list[date] = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return tuple(days)


def _coerce_head_result(value: BinanceVisionHeadResult | Mapping[str, Any] | int) -> BinanceVisionHeadResult:
    if isinstance(value, BinanceVisionHeadResult):
        return value
    if isinstance(value, int):
        return BinanceVisionHeadResult(status_code=value)
    return BinanceVisionHeadResult.model_validate(dict(value))


def _zip_status(result: BinanceVisionHeadResult) -> BinanceVisionAvailabilityStatus:
    if result.error:
        return BinanceVisionAvailabilityStatus.PROBE_ERROR
    if result.status_code == 200:
        return BinanceVisionAvailabilityStatus.AVAILABLE
    if result.status_code == 404:
        return BinanceVisionAvailabilityStatus.MISSING
    return BinanceVisionAvailabilityStatus.PROBE_ERROR


def _checksum_status(result: BinanceVisionHeadResult | None) -> BinanceVisionChecksumStatus:
    if result is None:
        return BinanceVisionChecksumStatus.NOT_CHECKED
    if result.error:
        return BinanceVisionChecksumStatus.PROBE_ERROR
    if result.status_code == 200:
        return BinanceVisionChecksumStatus.AVAILABLE
    if result.status_code == 404:
        return BinanceVisionChecksumStatus.MISSING
    return BinanceVisionChecksumStatus.PROBE_ERROR


def _blocked_reasons_for_probe(result: BinanceVisionHeadResult) -> tuple[str, ...]:
    if result.error:
        return (f"probe_error:{result.error}",)
    if result.status_code not in {200, 404}:
        return (f"unexpected_http_status:{result.status_code}",)
    return ()


def _content_length(result: BinanceVisionHeadResult | None) -> int | None:
    if result is None:
        return None
    raw = result.headers.get("content-length") or result.headers.get("Content-Length")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _normalize_binance_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or not normalized.replace("_", "").isalnum():
        raise ValueError(f"unsupported Binance Vision symbol: {symbol!r}")
    return normalized


def _default_symbol_map_ref(snapshot: SymbolMapSnapshot) -> str:
    return f"manifests/symbol_maps/{snapshot.symbol_map_snapshot_id}.json"


def _count_zip_status(
    rows: tuple[BinanceVisionAvailabilityRow, ...],
    status: BinanceVisionAvailabilityStatus,
) -> int:
    return sum(1 for row in rows if row.zip_status == status)


def _count_checksum_status(
    rows: tuple[BinanceVisionAvailabilityRow, ...],
    status: BinanceVisionChecksumStatus,
) -> int:
    return sum(1 for row in rows if row.checksum_status == status)


def _ingest_kline_rows(
    *,
    layout: ArchiveLayout,
    parse_result: BinanceVisionParseResult,
    archive_date: date,
    instrument_id: str,
    run_id: str,
    job_id: str,
) -> tuple[str, str, str]:
    store = ArchiveManifestStore(layout)
    start_ts, end_ts = _parse_result_time_bounds(parse_result)
    raw_records = [
        {
            **row.model_dump(mode="json"),
            "parser_zip_sha256": parse_result.zip_sha256,
            "checksum_verified": parse_result.checksum_verified,
            "duplicate_ids": parse_result.duplicate_ids,
            "gap_count": parse_result.gap_count,
            "interval_alignment_status": parse_result.interval_alignment_status,
            "native_to_hyperliquid": False,
        }
        for row in parse_result.rows
    ]
    raw_file = RawJsonlZstdWriter(layout, store).write_records(
        records=raw_records,
        venue="binance",
        datatype="binance_vision_klines",
        date=archive_date.isoformat(),
        run_id=run_id,
        job_id=job_id,
        adapter_id="binance_vision_local_zip_parser_v1",
        source_endpoint_or_subscription=f"local_zip/{parse_result.source_id}",
        symbols=(parse_result.binance_symbol,),
        start_ts=start_ts,
        end_ts=end_ts,
        instrument_id=instrument_id,
        timeframe="1m",
        filename="parsed_klines",
    )
    bronze_rows = [
        BronzeCandleRow(
            venue="binance",
            instrument_id=instrument_id,
            timeframe="1m",
            ts=_datetime_from_ms(row.event_time_ms),
            end_ts=_datetime_from_ms((row.close_time_ms or row.event_time_ms + 59_999) + 1),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
            trade_count=row.trade_count,
            raw_file_id=raw_file.file_id,
            source_sequence=row.source_row_index,
            parse_warnings=parse_result.warnings,
        ).model_dump(mode="json")
        for row in parse_result.rows
    ]
    bronze_file = write_parquet_rows(
        layout=layout,
        store=store,
        rows=bronze_rows,
        layer=ArchiveLayer.BRONZE,
        dataset="candles",
        venue="binance",
        datatype="candles",
        date=archive_date.isoformat(),
        job_id=job_id,
        source_file_ids=(raw_file.file_id,),
        filename=f"bronze-klines-{parse_result.zip_sha256[:16]}",
        timeframe="1m",
        instrument_id=instrument_id,
    )
    silver_rows = [
        SilverBarRow(
            venue="binance",
            instrument_id=instrument_id,
            timeframe="1m",
            ts=_datetime_from_ms(row.event_time_ms),
            end_ts=_datetime_from_ms((row.close_time_ms or row.event_time_ms + 59_999) + 1),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
            trade_count=row.trade_count,
            source_timeframe="1m",
            source_file_id=bronze_file.file_id,
            source_layer=ArchiveLayer.BRONZE,
            normalization_warnings=parse_result.warnings,
        ).model_dump(mode="json")
        for row in parse_result.rows
    ]
    silver_file = write_parquet_rows(
        layout=layout,
        store=store,
        rows=silver_rows,
        layer=ArchiveLayer.SILVER,
        dataset="bars",
        venue="binance",
        datatype="bars",
        date=archive_date.isoformat(),
        job_id=job_id,
        source_file_ids=(bronze_file.file_id,),
        filename=f"silver-bars-{parse_result.zip_sha256[:16]}",
        timeframe="1m",
        instrument_id=instrument_id,
    )
    return raw_file.file_id, bronze_file.file_id, silver_file.file_id


def _ingest_trade_rows(
    *,
    archive_root: str | Path,
    parse_result: BinanceVisionParseResult,
    archive_date: date,
    instrument_id: str,
    run_id: str,
    job_id: str,
    storage_budget_bytes: int,
) -> tuple[str, str, str]:
    start_ts, end_ts = _parse_result_time_bounds(parse_result)
    records = [
        {
            "ts": _datetime_from_ms(row.event_time_ms).isoformat(),
            "instrument_id": instrument_id,
            "event_type": "trade",
            "sequence": row.source_row_index,
            "price": float(row.price),
            "size": float(row.quantity),
            "side": _trade_side(row.buyer_maker),
            "trade_id": str(row.trade_id or row.aggregate_trade_id),
            "source": parse_result.source_id,
            "schema_version": V2_SCHEMA_VERSION,
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }
        for row in parse_result.rows
    ]
    capture = write_microstructure_raw_capture(
        archive_root=archive_root,
        records=records,
        venue="binance",
        datatype="trades",
        date=archive_date.isoformat(),
        run_id=run_id,
        job_id=job_id,
        adapter_id="binance_vision_local_zip_parser_v1",
        source_endpoint_or_subscription=f"local_zip/{parse_result.source_id}",
        instrument_id=instrument_id,
        start_ts=start_ts,
        end_ts=end_ts,
        storage_budget_bytes=storage_budget_bytes,
        gap_count=parse_result.gap_count,
    )
    return (
        capture.raw_file.file_id,
        capture.quality_report.quality_report_id,
        capture.storage_report.storage_report_id,
    )


def _parse_result_time_bounds(parse_result: BinanceVisionParseResult) -> tuple[datetime, datetime]:
    first = min(row.event_time_ms for row in parse_result.rows)
    last = max((row.close_time_ms or row.event_time_ms) for row in parse_result.rows)
    return _datetime_from_ms(first), _datetime_from_ms(last + 1)


def _datetime_from_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _default_binance_instrument_id(symbol: str, *, market_type: str) -> str:
    namespace = "perp" if market_type == "perpetual" else market_type
    return f"binance:{namespace}:{symbol}"


def _trade_side(buyer_maker: bool | None) -> str | None:
    if buyer_maker is None:
        return None
    return "sell" if buyer_maker else "buy"


def _reconstruct_minute_bars(
    source_result: BinanceVisionParseResult,
) -> dict[int, BinanceVisionReconstructedBarRow]:
    buckets: dict[int, list[BinanceVisionParsedDataRow]] = {}
    for row in source_result.rows:
        bucket = (row.event_time_ms // 60_000) * 60_000
        buckets.setdefault(bucket, []).append(row)
    reconstructed: dict[int, BinanceVisionReconstructedBarRow] = {}
    for bucket, rows in buckets.items():
        ordered = sorted(rows, key=lambda item: (item.event_time_ms, item.source_row_index))
        prices = [float(row.price) for row in ordered]
        volume = sum(float(row.quantity) for row in ordered)
        reconstructed[bucket] = BinanceVisionReconstructedBarRow(
            bucket_start_ms=bucket,
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            volume=volume,
            observed_event_count=len(ordered),
        )
    return reconstructed


def _compare_one_kline_bucket(
    *,
    kline_row: BinanceVisionParsedDataRow,
    reconstructed: BinanceVisionReconstructedBarRow | None,
    price_abs_tolerance: float,
    volume_abs_tolerance: float,
) -> BinanceVisionBarComparisonRow:
    assert kline_row.open is not None
    assert kline_row.high is not None
    assert kline_row.low is not None
    assert kline_row.close is not None
    assert kline_row.volume is not None
    if reconstructed is None:
        return BinanceVisionBarComparisonRow(
            bucket_start_ms=kline_row.event_time_ms,
            status="missing_reconstructed",
            kline_open=float(kline_row.open),
            kline_high=float(kline_row.high),
            kline_low=float(kline_row.low),
            kline_close=float(kline_row.close),
            kline_volume=float(kline_row.volume),
            kline_trade_count=kline_row.trade_count,
            reasons=("missing_reconstructed_bucket",),
        )
    diffs = {
        "open_abs_diff": abs(float(kline_row.open) - reconstructed.open),
        "high_abs_diff": abs(float(kline_row.high) - reconstructed.high),
        "low_abs_diff": abs(float(kline_row.low) - reconstructed.low),
        "close_abs_diff": abs(float(kline_row.close) - reconstructed.close),
        "volume_abs_diff": abs(float(kline_row.volume) - reconstructed.volume),
    }
    reasons: list[str] = []
    for field_name in ("open_abs_diff", "high_abs_diff", "low_abs_diff", "close_abs_diff"):
        if diffs[field_name] > price_abs_tolerance:
            reasons.append(field_name.replace("_abs_diff", "_tolerance_exceeded"))
    if diffs["volume_abs_diff"] > volume_abs_tolerance:
        reasons.append("volume_tolerance_exceeded")
    return BinanceVisionBarComparisonRow(
        bucket_start_ms=kline_row.event_time_ms,
        status="failed" if reasons else "passed",
        kline_open=float(kline_row.open),
        kline_high=float(kline_row.high),
        kline_low=float(kline_row.low),
        kline_close=float(kline_row.close),
        kline_volume=float(kline_row.volume),
        reconstructed_open=reconstructed.open,
        reconstructed_high=reconstructed.high,
        reconstructed_low=reconstructed.low,
        reconstructed_close=reconstructed.close,
        reconstructed_volume=reconstructed.volume,
        open_abs_diff=diffs["open_abs_diff"],
        high_abs_diff=diffs["high_abs_diff"],
        low_abs_diff=diffs["low_abs_diff"],
        close_abs_diff=diffs["close_abs_diff"],
        volume_abs_diff=diffs["volume_abs_diff"],
        kline_trade_count=kline_row.trade_count,
        reconstructed_event_count=reconstructed.observed_event_count,
        reasons=tuple(reasons),
    )


HEADERLESS_FIELDS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "trades": (
        "trade_id",
        "price",
        "quantity",
        "quote_quantity",
        "time",
        "is_buyer_maker",
        "is_best_match",
    ),
    "aggTrades": (
        "aggregate_trade_id",
        "price",
        "quantity",
        "first_trade_id",
        "last_trade_id",
        "transact_time",
        "is_buyer_maker",
        "is_best_match",
    ),
    "klines": (
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
        "ignore",
    ),
}

FIELD_ALIASES = {
    "id": "trade_id",
    "trade id": "trade_id",
    "trade_id": "trade_id",
    "agg_trade_id": "aggregate_trade_id",
    "agg trade id": "aggregate_trade_id",
    "aggregate_trade_id": "aggregate_trade_id",
    "a": "aggregate_trade_id",
    "p": "price",
    "price": "price",
    "q": "quantity",
    "qty": "quantity",
    "quantity": "quantity",
    "first_trade_id": "first_trade_id",
    "first trade id": "first_trade_id",
    "f": "first_trade_id",
    "last_trade_id": "last_trade_id",
    "last trade id": "last_trade_id",
    "l": "last_trade_id",
    "time": "time",
    "transact_time": "transact_time",
    "transaction_time": "transact_time",
    "timestamp": "time",
    "is_buyer_maker": "is_buyer_maker",
    "is buyer maker": "is_buyer_maker",
    "m": "is_buyer_maker",
    "is_best_match": "is_best_match",
    "open_time": "open_time",
    "open time": "open_time",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "close_time": "close_time",
    "close time": "close_time",
    "number_of_trades": "number_of_trades",
    "number of trades": "number_of_trades",
    "trade_count": "number_of_trades",
}


def _parse_checksum_payload(payload: bytes | str | None) -> str | None:
    if payload is None:
        return None
    text = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
    token = text.strip().split()[0] if text.strip() else ""
    if len(token) == 64 and all(character in "0123456789abcdefABCDEF" for character in token):
        return token.lower()
    raise ValueError("invalid Binance Vision checksum payload")


def _read_single_csv_from_zip(zip_bytes: bytes) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            csv_members = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".csv") and not name.endswith("/")
            ]
            if len(csv_members) != 1:
                raise ValueError("Binance Vision ZIP must contain exactly one CSV member")
            member = csv_members[0]
            return member, archive.read(member).decode("utf-8-sig")
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid Binance Vision ZIP bytes") from exc


def _parse_csv_text(text: str, spec: BinanceVisionSourceSpec) -> list[dict[str, str]]:
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError("Binance Vision CSV has no data rows")
    if _has_csv_header(rows[0]):
        fieldnames = [_field_name(cell) for cell in rows[0]]
        data_rows = rows[1:]
    else:
        fieldnames = list(HEADERLESS_FIELDS_BY_FAMILY[spec.family])
        data_rows = rows
    parsed: list[dict[str, str]] = []
    for row in data_rows:
        item: dict[str, str] = {}
        for index, value in enumerate(row):
            field_name = fieldnames[index] if index < len(fieldnames) else f"extra_{index}"
            item[field_name] = value.strip()
        parsed.append(item)
    if not parsed:
        raise ValueError("Binance Vision CSV has a header but no data rows")
    return parsed


def _field_name(value: str) -> str:
    normalized = value.strip().replace("-", "_").replace(" ", "_").lower()
    return FIELD_ALIASES.get(normalized, normalized)


def _has_csv_header(first_row: list[str]) -> bool:
    normalized = {_field_name(cell) for cell in first_row}
    known = set(FIELD_ALIASES.values()) | {
        "open_time",
        "close_time",
        "number_of_trades",
        "trade_id",
        "aggregate_trade_id",
    }
    return bool(normalized & known)


def _parse_binance_vision_row(
    row: Mapping[str, str],
    *,
    source_id: str,
    symbol: str,
    spec: BinanceVisionSourceSpec,
    source_row_index: int,
) -> BinanceVisionParsedDataRow:
    row_type = _row_type_for_spec(spec)
    if row_type == BinanceVisionRowType.KLINE:
        return BinanceVisionParsedDataRow(
            source_id=source_id,
            binance_symbol=symbol,
            row_type=row_type,
            source_row_index=source_row_index,
            event_time_ms=_int_value(row, "open_time"),
            open=_float_value(row, "open"),
            high=_float_value(row, "high"),
            low=_float_value(row, "low"),
            close=_float_value(row, "close"),
            volume=_float_value(row, "volume"),
            close_time_ms=_int_value(row, "close_time"),
            trade_count=_optional_int_value(row, "number_of_trades"),
            raw_fields=_clean_raw_fields(row),
        )
    if row_type == BinanceVisionRowType.AGG_TRADE:
        return BinanceVisionParsedDataRow(
            source_id=source_id,
            binance_symbol=symbol,
            row_type=row_type,
            source_row_index=source_row_index,
            event_time_ms=_int_value(row, "transact_time", "time"),
            aggregate_trade_id=_int_value(row, "aggregate_trade_id"),
            first_trade_id=_optional_int_value(row, "first_trade_id"),
            last_trade_id=_optional_int_value(row, "last_trade_id"),
            price=_float_value(row, "price"),
            quantity=_float_value(row, "quantity"),
            buyer_maker=_optional_bool_value(row, "is_buyer_maker"),
            raw_fields=_clean_raw_fields(row),
        )
    return BinanceVisionParsedDataRow(
        source_id=source_id,
        binance_symbol=symbol,
        row_type=row_type,
        source_row_index=source_row_index,
        event_time_ms=_int_value(row, "time", "transact_time"),
        trade_id=_int_value(row, "trade_id"),
        price=_float_value(row, "price"),
        quantity=_float_value(row, "quantity"),
        buyer_maker=_optional_bool_value(row, "is_buyer_maker"),
        raw_fields=_clean_raw_fields(row),
    )


def _row_type_for_spec(spec: BinanceVisionSourceSpec) -> BinanceVisionRowType:
    if spec.family == "klines":
        return BinanceVisionRowType.KLINE
    if spec.family == "aggTrades":
        return BinanceVisionRowType.AGG_TRADE
    return BinanceVisionRowType.TRADE


def _event_time_from_raw(row: Mapping[str, str], spec: BinanceVisionSourceSpec) -> int:
    row_type = _row_type_for_spec(spec)
    if row_type == BinanceVisionRowType.KLINE:
        return _int_value(row, "open_time")
    if row_type == BinanceVisionRowType.AGG_TRADE:
        return _int_value(row, "transact_time", "time")
    return _int_value(row, "time", "transact_time")


def _duplicate_ids(rows: tuple[BinanceVisionParsedDataRow, ...]) -> tuple[int, ...]:
    observed: set[int] = set()
    duplicates: set[int] = set()
    for row in rows:
        event_id = row.trade_id or row.aggregate_trade_id
        if event_id is None and row.row_type == BinanceVisionRowType.KLINE:
            event_id = row.event_time_ms
        if event_id is None:
            continue
        if event_id in observed:
            duplicates.add(event_id)
        observed.add(event_id)
    return tuple(sorted(duplicates))


def _gap_and_interval_status(rows: tuple[BinanceVisionParsedDataRow, ...], spec: BinanceVisionSourceSpec) -> tuple[int, str]:
    if spec.family != "klines":
        return 0, "not_applicable"
    if not rows:
        return 0, "no_rows"
    aligned = all(
        row.event_time_ms % 60_000 == 0
        and row.close_time_ms is not None
        and row.close_time_ms == row.event_time_ms + 59_999
        for row in rows
    )
    unique_times = sorted(set(row.event_time_ms for row in rows))
    gap_count = 0
    for previous, current in zip(unique_times, unique_times[1:], strict=False):
        delta = current - previous
        if delta > 60_000:
            gap_count += max(0, delta // 60_000 - 1)
    return gap_count, "aligned" if aligned else "misaligned"


def _int_value(row: Mapping[str, str], *field_names: str) -> int:
    value = _required_value(row, *field_names)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"field must be integer: {field_names[0]}={value}") from exc


def _optional_int_value(row: Mapping[str, str], *field_names: str) -> int | None:
    value = _optional_value(row, *field_names)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"field must be integer: {field_names[0]}={value}") from exc


def _float_value(row: Mapping[str, str], *field_names: str) -> float:
    value = _required_value(row, *field_names)
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"field must be numeric: {field_names[0]}={value}") from exc


def _optional_bool_value(row: Mapping[str, str], *field_names: str) -> bool | None:
    value = _optional_value(row, *field_names)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "t", "yes", "y"}:
        return True
    if normalized in {"false", "0", "f", "no", "n"}:
        return False
    raise ValueError(f"field must be boolean: {field_names[0]}={value}")


def _required_value(row: Mapping[str, str], *field_names: str) -> str:
    value = _optional_value(row, *field_names)
    if value is None:
        raise ValueError("missing required field: " + ",".join(field_names))
    return value


def _optional_value(row: Mapping[str, str], *field_names: str) -> str | None:
    for field_name in field_names:
        value = row.get(field_name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def _clean_raw_fields(row: Mapping[str, str]) -> dict[str, str]:
    return {str(key): str(value) for key, value in sorted(row.items()) if str(value) != ""}


def _write_json_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
