# V2-AUDIT-ID: V2-AUD-DATASRC-013
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, strict_free_public_derivatives_context, no_downloads
# V2-OWNER: v2_data_sources
"""Offline request builders for Binance USD-M public derivatives context."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.parquet_writer import write_parquet_rows
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.data_sources.schemas import (
    CostClass,
    CoverageLabel,
    CoverageWindow,
    DataFamilyCoverageReport,
    ExpectedBuckets,
)
from tradingbotsuite.v2.security.boundary import require_research_boundary

BINANCE_DERIVATIVES_CONTEXT_BASE_URL = "https://fapi.binance.com"
BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID = "binance_usdm_public_derivatives_context"

BINANCE_DERIVATIVES_INTERVAL_FAMILIES = frozenset(
    {
        "mark_price_klines",
        "index_price_klines",
        "premium_index_klines",
    }
)
BINANCE_DERIVATIVES_PERIOD_FAMILIES = frozenset(
    {
        "open_interest_statistics",
        "taker_buy_sell_volume",
        "long_short_ratios",
        "basis",
    }
)
BINANCE_DERIVATIVES_PAIR_PARAM_FAMILIES = frozenset(
    {
        "index_price_klines",
        "basis",
    }
)


class BinanceDerivativesContextFamily(str, Enum):
    FUNDING_RATE_HISTORY = "funding_rate_history"
    OPEN_INTEREST = "open_interest"
    OPEN_INTEREST_STATISTICS = "open_interest_statistics"
    MARK_PRICE_KLINES = "mark_price_klines"
    INDEX_PRICE_KLINES = "index_price_klines"
    PREMIUM_INDEX_KLINES = "premium_index_klines"
    TAKER_BUY_SELL_VOLUME = "taker_buy_sell_volume"
    LONG_SHORT_RATIOS = "long_short_ratios"
    BASIS = "basis"


class BinanceDerivativesContextFetchStatus(str, Enum):
    FETCHED = "fetched"
    BLOCKED = "blocked"
    FETCH_ERROR = "fetch_error"
    PARSE_ERROR = "parse_error"


class BinanceDerivativesContextPageStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"


class BinanceDerivativesContextArchiveIngestStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"


class BinanceDerivativesContextBackfillStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"


class BinanceDerivativesContextEndpointSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    family: BinanceDerivativesContextFamily
    endpoint: str = Field(min_length=1)
    symbol_parameter: str = Field(pattern=r"^(symbol|pair)$")
    limit_max: int | None = Field(default=None, ge=1)
    accepts_time_range: bool = True
    requires_interval: bool = False
    requires_period: bool = False
    requires_contract_type: bool = False
    request_weight: int | None = Field(default=None, ge=1)
    rate_limit_note: str
    history_window_days: int | None = Field(default=None, ge=1)
    docs_url: str


class BinanceDerivativesContextRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID
    base_url: str = Field(min_length=1)
    family: BinanceDerivativesContextFamily
    endpoint: str = Field(min_length=1)
    url: str = Field(min_length=1)
    params: dict[str, str | int] = Field(default_factory=dict)
    symbol: str = Field(min_length=1)
    symbol_parameter: str = Field(pattern=r"^(symbol|pair)$")
    interval: str | None = None
    period: str | None = None
    limit: int | None = Field(default=None, ge=1)
    start_time_ms: int | None = Field(default=None, ge=0)
    end_time_ms: int | None = Field(default=None, ge=0)
    contract_type: str | None = None
    limit_max: int | None = Field(default=None, ge=1)
    request_weight: int | None = Field(default=None, ge=1)
    history_window_days: int | None = Field(default=None, ge=1)
    docs_url: str
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
    def _validate_request(self) -> "BinanceDerivativesContextRequest":
        require_research_boundary(self, context="Binance derivatives context request")
        expected_param = "pair" if self.family.value in BINANCE_DERIVATIVES_PAIR_PARAM_FAMILIES else "symbol"
        if self.symbol_parameter != expected_param:
            raise ValueError(f"{self.family.value} must use {expected_param} parameter")
        if self.native_to_hyperliquid:
            raise ValueError("Binance context requests are never Hyperliquid-native")
        if self.end_time_ms is not None and self.start_time_ms is not None:
            if self.end_time_ms < self.start_time_ms:
                raise ValueError("end_time_ms must be greater than or equal to start_time_ms")
        return self


class BinanceDerivativesContextGetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    content: bytes = b""
    error: str | None = None


class BinanceDerivativesContextNormalizedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID
    family: BinanceDerivativesContextFamily
    symbol: str = Field(min_length=1)
    venue: str = "binance"
    market_type: str = "perpetual"
    timestamp_ms: int | None = Field(default=None, ge=0)
    open_time_ms: int | None = Field(default=None, ge=0)
    close_time_ms: int | None = Field(default=None, ge=0)
    publication_time_ms: int | None = Field(default=None, ge=0)
    interval: str | None = None
    period: str | None = None
    bucket_seconds: int | None = Field(default=None, ge=1)
    numeric_fields: dict[str, str] = Field(default_factory=dict)
    unit_fields: dict[str, str] = Field(default_factory=dict)
    raw_fields: dict[str, Any] = Field(default_factory=dict)
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
    def _validate_row(self) -> "BinanceDerivativesContextNormalizedRow":
        require_research_boundary(self, context="Binance derivatives context row")
        if self.native_to_hyperliquid:
            raise ValueError("Binance context rows are never Hyperliquid-native")
        return self


class BinanceDerivativesContextFetchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    fetch_result_id: str = Field(min_length=64, max_length=64)
    request: BinanceDerivativesContextRequest
    status: BinanceDerivativesContextFetchStatus
    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    byte_count: int = Field(default=0, ge=0)
    raw_row_count: int = Field(default=0, ge=0)
    normalized_row_count: int = Field(default=0, ge=0)
    normalized_rows_hash: str = Field(min_length=64, max_length=64)
    rows: tuple[BinanceDerivativesContextNormalizedRow, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
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
    def _validate_fetch_result(self) -> "BinanceDerivativesContextFetchResult":
        require_research_boundary(self, context="Binance derivatives context fetch")
        if self.native_to_hyperliquid:
            raise ValueError("Binance context fetches are never Hyperliquid-native")
        if self.normalized_row_count != len(self.rows):
            raise ValueError("normalized_row_count must match rows")
        if self.normalized_rows_hash != _binance_derivatives_rows_hash(self.rows):
            raise ValueError("normalized_rows_hash does not match rows")
        expected_id = _binance_derivatives_fetch_result_id(
            request=self.request,
            status=self.status,
            status_code=self.status_code,
            content_sha256=self.content_sha256,
            byte_count=self.byte_count,
            raw_row_count=self.raw_row_count,
            normalized_rows_hash=self.normalized_rows_hash,
            blocked_reasons=self.blocked_reasons,
        )
        if self.fetch_result_id != expected_id:
            raise ValueError("fetch_result_id does not match fetch result identity")
        if self.status == BinanceDerivativesContextFetchStatus.FETCHED:
            if self.blocked_reasons:
                raise ValueError("fetched results cannot carry blocker reasons")
            if self.content_sha256 is None:
                raise ValueError("fetched results require content_sha256")
        elif not self.blocked_reasons:
            raise ValueError("blocked/error results require blocker reasons")
        return self


class BinanceDerivativesContextPageResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    page_result_id: str = Field(min_length=64, max_length=64)
    family: BinanceDerivativesContextFamily
    symbol: str = Field(min_length=1)
    start_time_ms: int | None = Field(default=None, ge=0)
    end_time_ms: int | None = Field(default=None, ge=0)
    interval: str | None = None
    period: str | None = None
    limit: int | None = Field(default=None, ge=1)
    max_pages: int = Field(ge=0)
    status: BinanceDerivativesContextPageStatus
    page_count: int = Field(default=0, ge=0)
    page_request_urls: tuple[str, ...] = ()
    page_fetch_result_ids: tuple[str, ...] = ()
    normalized_row_count: int = Field(default=0, ge=0)
    normalized_rows_hash: str = Field(min_length=64, max_length=64)
    rows: tuple[BinanceDerivativesContextNormalizedRow, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
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
    def _validate_page_result(self) -> "BinanceDerivativesContextPageResult":
        require_research_boundary(self, context="Binance derivatives context pages")
        if self.native_to_hyperliquid:
            raise ValueError("Binance context pages are never Hyperliquid-native")
        if self.page_count != len(self.page_fetch_result_ids):
            raise ValueError("page_count must match page_fetch_result_ids")
        if len(self.page_request_urls) != len(self.page_fetch_result_ids):
            raise ValueError("page_request_urls must match page_fetch_result_ids")
        if self.normalized_row_count != len(self.rows):
            raise ValueError("normalized_row_count must match rows")
        if self.normalized_rows_hash != _binance_derivatives_rows_hash(self.rows):
            raise ValueError("normalized_rows_hash does not match rows")
        expected_id = _binance_derivatives_page_result_id(
            family=self.family,
            symbol=self.symbol,
            start_time_ms=self.start_time_ms,
            end_time_ms=self.end_time_ms,
            interval=self.interval,
            period=self.period,
            limit=self.limit,
            max_pages=self.max_pages,
            status=self.status,
            page_request_urls=self.page_request_urls,
            page_fetch_result_ids=self.page_fetch_result_ids,
            normalized_rows_hash=self.normalized_rows_hash,
            blocked_reasons=self.blocked_reasons,
        )
        if self.page_result_id != expected_id:
            raise ValueError("page_result_id does not match page result identity")
        if self.status == BinanceDerivativesContextPageStatus.COMPLETED and self.blocked_reasons:
            raise ValueError("completed page results cannot carry blockers")
        if self.status == BinanceDerivativesContextPageStatus.BLOCKED and not self.blocked_reasons:
            raise ValueError("blocked page results require blocker reasons")
        return self


class BinanceDerivativesContextArchiveIngestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    ingest_id: str = Field(min_length=64, max_length=64)
    page_result_id: str = Field(min_length=64, max_length=64)
    family: BinanceDerivativesContextFamily
    symbol: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    archive_date: date | None = None
    run_id: str | None = None
    job_id: str | None = None
    status: BinanceDerivativesContextArchiveIngestStatus
    raw_file_id: str | None = Field(default=None, min_length=64, max_length=64)
    raw_file_ref: str | None = None
    silver_file_id: str | None = Field(default=None, min_length=64, max_length=64)
    silver_file_ref: str | None = None
    raw_row_count: int = Field(default=0, ge=0)
    silver_row_count: int = Field(default=0, ge=0)
    normalized_rows_hash: str = Field(min_length=64, max_length=64)
    blocked_reasons: tuple[str, ...] = ()
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
    def _validate_archive_ingest(self) -> "BinanceDerivativesContextArchiveIngestResult":
        require_research_boundary(self, context="Binance derivatives context archive ingest")
        if self.native_to_hyperliquid:
            raise ValueError("Binance context archive rows are never Hyperliquid-native")
        if self.accepted_research_evidence:
            raise ValueError("archive ingest does not create accepted research evidence")
        expected_id = _binance_derivatives_archive_ingest_id(
            page_result_id=self.page_result_id,
            family=self.family,
            symbol=self.symbol,
            instrument_id=self.instrument_id,
            archive_date=self.archive_date.isoformat() if self.archive_date else None,
            run_id=self.run_id,
            job_id=self.job_id,
            status=self.status,
            raw_file_id=self.raw_file_id,
            silver_file_id=self.silver_file_id,
            raw_row_count=self.raw_row_count,
            silver_row_count=self.silver_row_count,
            normalized_rows_hash=self.normalized_rows_hash,
            blocked_reasons=self.blocked_reasons,
        )
        if self.ingest_id != expected_id:
            raise ValueError("ingest_id does not match archive ingest identity")
        if self.status == BinanceDerivativesContextArchiveIngestStatus.COMPLETED:
            if self.blocked_reasons:
                raise ValueError("completed archive ingest cannot carry blockers")
            if not self.raw_file_id or not self.silver_file_id:
                raise ValueError("completed archive ingest requires raw and silver file IDs")
            if self.raw_row_count <= 0 or self.silver_row_count <= 0:
                raise ValueError("completed archive ingest requires rows")
        elif not self.blocked_reasons:
            raise ValueError("blocked archive ingest requires blocker reasons")
        return self


class BinanceDerivativesContextBackfillResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "binance_derivatives_context_backfill_result"
    backfill_id: str = Field(min_length=64, max_length=64)
    status: BinanceDerivativesContextBackfillStatus
    family: BinanceDerivativesContextFamily
    symbol: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    page_result_id: str = Field(min_length=64, max_length=64)
    archive_ingest_id: str = Field(min_length=64, max_length=64)
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
    def _validate_backfill_result(self) -> "BinanceDerivativesContextBackfillResult":
        require_research_boundary(self, context="Binance derivatives context backfill")
        if self.manifest_type != "binance_derivatives_context_backfill_result":
            raise ValueError("manifest_type must be binance_derivatives_context_backfill_result")
        if self.status == BinanceDerivativesContextBackfillStatus.COMPLETED and self.blocker_reasons:
            raise ValueError("completed backfill cannot carry blocker reasons")
        if self.status == BinanceDerivativesContextBackfillStatus.BLOCKED and not self.blocker_reasons:
            raise ValueError("blocked backfill requires blocker reasons")
        expected_id = _binance_derivatives_backfill_id(
            family=self.family,
            symbol=self.symbol,
            instrument_id=self.instrument_id,
            page_result_id=self.page_result_id,
            archive_ingest_id=self.archive_ingest_id,
            coverage_report_id=self.coverage_report_id,
            accepted_for_research_reporting=self.accepted_for_research_reporting,
            blocker_reasons=self.blocker_reasons,
        )
        if self.backfill_id != expected_id:
            raise ValueError("backfill_id does not match backfill identity")
        return self


BINANCE_DERIVATIVES_CONTEXT_ENDPOINT_SPECS: dict[
    BinanceDerivativesContextFamily,
    BinanceDerivativesContextEndpointSpec,
] = {
    BinanceDerivativesContextFamily.FUNDING_RATE_HISTORY: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.FUNDING_RATE_HISTORY,
        endpoint="/fapi/v1/fundingRate",
        symbol_parameter="symbol",
        limit_max=1_000,
        request_weight=None,
        rate_limit_note="Shared 500 requests / 5 minutes / IP with fundingInfo.",
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History",
    ),
    BinanceDerivativesContextFamily.OPEN_INTEREST: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.OPEN_INTEREST,
        endpoint="/fapi/v1/openInterest",
        symbol_parameter="symbol",
        accepts_time_range=False,
        request_weight=1,
        rate_limit_note="Public current open-interest request weight 1.",
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest",
    ),
    BinanceDerivativesContextFamily.OPEN_INTEREST_STATISTICS: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.OPEN_INTEREST_STATISTICS,
        endpoint="/futures/data/openInterestHist",
        symbol_parameter="symbol",
        limit_max=500,
        requires_period=True,
        rate_limit_note="1000 requests / 5 minutes / IP.",
        history_window_days=31,
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics",
    ),
    BinanceDerivativesContextFamily.MARK_PRICE_KLINES: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.MARK_PRICE_KLINES,
        endpoint="/fapi/v1/markPriceKlines",
        symbol_parameter="symbol",
        limit_max=1_500,
        requires_interval=True,
        rate_limit_note="Weight varies by LIMIT.",
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price-Kline-Candlestick-Data",
    ),
    BinanceDerivativesContextFamily.INDEX_PRICE_KLINES: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.INDEX_PRICE_KLINES,
        endpoint="/fapi/v1/indexPriceKlines",
        symbol_parameter="pair",
        limit_max=1_500,
        requires_interval=True,
        rate_limit_note="Weight varies by LIMIT.",
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Index-Price-Kline-Candlestick-Data",
    ),
    BinanceDerivativesContextFamily.PREMIUM_INDEX_KLINES: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.PREMIUM_INDEX_KLINES,
        endpoint="/fapi/v1/premiumIndexKlines",
        symbol_parameter="symbol",
        limit_max=1_500,
        requires_interval=True,
        rate_limit_note="Weight varies by LIMIT.",
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Premium-Index-Kline-Data",
    ),
    BinanceDerivativesContextFamily.TAKER_BUY_SELL_VOLUME: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.TAKER_BUY_SELL_VOLUME,
        endpoint="/futures/data/takerlongshortRatio",
        symbol_parameter="symbol",
        limit_max=500,
        requires_period=True,
        rate_limit_note="1000 requests / 5 minutes / IP.",
        history_window_days=30,
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Taker-BuySell-Volume",
    ),
    BinanceDerivativesContextFamily.LONG_SHORT_RATIOS: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.LONG_SHORT_RATIOS,
        endpoint="/futures/data/globalLongShortAccountRatio",
        symbol_parameter="symbol",
        limit_max=500,
        requires_period=True,
        rate_limit_note="1000 requests / 5 minutes / IP.",
        history_window_days=30,
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Long-Short-Ratio",
    ),
    BinanceDerivativesContextFamily.BASIS: BinanceDerivativesContextEndpointSpec(
        family=BinanceDerivativesContextFamily.BASIS,
        endpoint="/futures/data/basis",
        symbol_parameter="pair",
        limit_max=500,
        requires_period=True,
        requires_contract_type=True,
        rate_limit_note="Public basis statistics endpoint.",
        history_window_days=30,
        docs_url="https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Basis",
    ),
}


def binance_derivatives_context_spec(
    family: str | BinanceDerivativesContextFamily,
) -> BinanceDerivativesContextEndpointSpec:
    family_enum = _coerce_family(family)
    return BINANCE_DERIVATIVES_CONTEXT_ENDPOINT_SPECS[family_enum]


def build_binance_derivatives_context_request(
    *,
    family: str | BinanceDerivativesContextFamily,
    symbol: str,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    interval: str | None = None,
    period: str | None = None,
    limit: int | None = None,
    base_url: str = BINANCE_DERIVATIVES_CONTEXT_BASE_URL,
    contract_type: str | None = "PERPETUAL",
) -> BinanceDerivativesContextRequest:
    spec = binance_derivatives_context_spec(family)
    normalized_symbol = _normalize_symbol(symbol)
    normalized_interval = _normalize_optional_token(interval)
    normalized_period = _normalize_optional_token(period)
    normalized_contract_type = _normalize_optional_token(contract_type)
    _validate_request_inputs(
        spec=spec,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        interval=normalized_interval,
        period=normalized_period,
        limit=limit,
        contract_type=normalized_contract_type,
    )

    params: dict[str, str | int] = {spec.symbol_parameter: normalized_symbol}
    if normalized_interval is not None:
        params["interval"] = normalized_interval
    if normalized_period is not None:
        params["period"] = normalized_period
    if spec.requires_contract_type:
        params["contractType"] = normalized_contract_type or "PERPETUAL"
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    if limit is not None:
        params["limit"] = limit

    query = urlencode(params)
    cleaned_base_url = base_url.rstrip("/")
    url = f"{cleaned_base_url}{spec.endpoint}?{query}"
    return BinanceDerivativesContextRequest(
        base_url=cleaned_base_url,
        family=spec.family,
        endpoint=spec.endpoint,
        url=url,
        params=params,
        symbol=normalized_symbol,
        symbol_parameter=spec.symbol_parameter,
        interval=normalized_interval,
        period=normalized_period,
        limit=limit,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        contract_type=normalized_contract_type if spec.requires_contract_type else None,
        limit_max=spec.limit_max,
        request_weight=spec.request_weight,
        history_window_days=spec.history_window_days,
        docs_url=spec.docs_url,
    )


def default_binance_derivatives_context_get(
    url: str,
) -> BinanceDerivativesContextGetResult:
    try:
        response = httpx.get(url, follow_redirects=True, timeout=60.0)
        return BinanceDerivativesContextGetResult(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
        )
    except httpx.HTTPError as exc:
        return BinanceDerivativesContextGetResult(error=type(exc).__name__)


def fetch_binance_derivatives_context_request(
    request: BinanceDerivativesContextRequest,
    *,
    get: Callable[[str], BinanceDerivativesContextGetResult | Mapping[str, Any]] | None = None,
    max_bytes: int = 10 * 1024 * 1024,
) -> BinanceDerivativesContextFetchResult:
    if max_bytes <= 0:
        return _build_fetch_result(
            request=request,
            status=BinanceDerivativesContextFetchStatus.BLOCKED,
            blocked_reasons=("max_bytes_must_be_positive",),
        )
    get_client = get or default_binance_derivatives_context_get
    response = _coerce_derivatives_get_result(get_client(request.url))
    if response.error:
        return _build_fetch_result(
            request=request,
            status=BinanceDerivativesContextFetchStatus.FETCH_ERROR,
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
            blocked_reasons=(f"fetch_error:{response.error}",),
        )
    if response.status_code != 200:
        return _build_fetch_result(
            request=request,
            status=BinanceDerivativesContextFetchStatus.FETCH_ERROR,
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
            blocked_reasons=(f"http_status:{response.status_code}",),
        )
    if len(response.content) > max_bytes:
        return _build_fetch_result(
            request=request,
            status=BinanceDerivativesContextFetchStatus.BLOCKED,
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
            blocked_reasons=("max_bytes_exceeded",),
        )
    try:
        payload = json.loads(response.content.decode("utf-8"))
        raw_rows = _payload_to_rows(payload)
        rows = tuple(
            _normalize_binance_derivatives_context_row(request, raw_row)
            for raw_row in raw_rows
        )
    except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _build_fetch_result(
            request=request,
            status=BinanceDerivativesContextFetchStatus.PARSE_ERROR,
            status_code=response.status_code,
            headers=response.headers,
            content=response.content,
            blocked_reasons=(f"parse_error:{type(exc).__name__}",),
        )
    return _build_fetch_result(
        request=request,
        status=BinanceDerivativesContextFetchStatus.FETCHED,
        status_code=response.status_code,
        headers=response.headers,
        content=response.content,
        raw_row_count=len(raw_rows),
        rows=rows,
    )


def fetch_binance_derivatives_context_pages(
    *,
    family: str | BinanceDerivativesContextFamily,
    symbol: str,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    interval: str | None = None,
    period: str | None = None,
    limit: int | None = None,
    max_pages: int = 10,
    base_url: str = BINANCE_DERIVATIVES_CONTEXT_BASE_URL,
    contract_type: str | None = "PERPETUAL",
    get: Callable[[str], BinanceDerivativesContextGetResult | Mapping[str, Any]] | None = None,
    max_bytes: int = 10 * 1024 * 1024,
) -> BinanceDerivativesContextPageResult:
    family_enum = _coerce_family(family)
    spec = binance_derivatives_context_spec(family_enum)
    normalized_symbol = _normalize_symbol(symbol)
    if max_pages <= 0:
        return _build_page_result(
            family=family_enum,
            symbol=normalized_symbol,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            interval=interval,
            period=period,
            limit=limit,
            max_pages=max_pages,
            status=BinanceDerivativesContextPageStatus.BLOCKED,
            blocked_reasons=("max_pages_must_be_positive",),
        )
    if spec.accepts_time_range and (start_time_ms is None or end_time_ms is None):
        return _build_page_result(
            family=family_enum,
            symbol=normalized_symbol,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            interval=interval,
            period=period,
            limit=limit,
            max_pages=max_pages,
            status=BinanceDerivativesContextPageStatus.BLOCKED,
            blocked_reasons=("bounded_start_end_required",),
        )
    effective_limit = limit if limit is not None else spec.limit_max
    page_urls: list[str] = []
    page_ids: list[str] = []
    rows: list[BinanceDerivativesContextNormalizedRow] = []
    blocked_reasons: list[str] = []
    cursor = start_time_ms
    completed = True

    for _ in range(max_pages):
        if spec.accepts_time_range and cursor is not None and end_time_ms is not None:
            if cursor > end_time_ms:
                break
        try:
            request = build_binance_derivatives_context_request(
                family=family_enum,
                symbol=normalized_symbol,
                start_time_ms=cursor if spec.accepts_time_range else None,
                end_time_ms=end_time_ms if spec.accepts_time_range else None,
                interval=interval,
                period=period,
                limit=effective_limit,
                base_url=base_url,
                contract_type=contract_type,
            )
        except ValueError as exc:
            completed = False
            blocked_reasons.append(f"request_error:{type(exc).__name__}:{exc}")
            break
        fetch = fetch_binance_derivatives_context_request(
            request,
            get=get,
            max_bytes=max_bytes,
        )
        page_urls.append(request.url)
        page_ids.append(fetch.fetch_result_id)
        if fetch.status != BinanceDerivativesContextFetchStatus.FETCHED:
            completed = False
            blocked_reasons.extend(f"page_blocked:{reason}" for reason in fetch.blocked_reasons)
            break
        rows.extend(fetch.rows)
        if not spec.accepts_time_range:
            break
        if not fetch.rows:
            break
        if effective_limit is None or fetch.raw_row_count < effective_limit:
            break
        try:
            next_cursor = _next_page_start_ms(fetch.rows, fallback_cursor=cursor)
        except ValueError as exc:
            completed = False
            blocked_reasons.append(f"cursor_error:{type(exc).__name__}:{exc}")
            break
        if cursor is not None and next_cursor <= cursor:
            completed = False
            blocked_reasons.append("non_advancing_cursor")
            break
        cursor = next_cursor
    else:
        if spec.accepts_time_range and cursor is not None and end_time_ms is not None:
            if cursor <= end_time_ms:
                completed = False
                blocked_reasons.append("max_pages_exceeded")

    status = (
        BinanceDerivativesContextPageStatus.COMPLETED
        if completed
        else BinanceDerivativesContextPageStatus.BLOCKED
    )
    return _build_page_result(
        family=family_enum,
        symbol=normalized_symbol,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        interval=interval,
        period=period,
        limit=effective_limit,
        max_pages=max_pages,
        status=status,
        page_request_urls=tuple(page_urls),
        page_fetch_result_ids=tuple(page_ids),
        rows=tuple(rows),
        blocked_reasons=tuple(blocked_reasons),
    )


def ingest_binance_derivatives_context_pages_to_archive(
    *,
    archive_root: str | Path,
    page_result: BinanceDerivativesContextPageResult,
    instrument_id: str,
    archive_date: date | None = None,
    run_id: str | None = None,
    job_id: str | None = None,
) -> BinanceDerivativesContextArchiveIngestResult:
    if page_result.status != BinanceDerivativesContextPageStatus.COMPLETED:
        return _build_archive_ingest_result(
            page_result=page_result,
            instrument_id=instrument_id,
            archive_date=archive_date,
            run_id=run_id,
            job_id=job_id,
            status=BinanceDerivativesContextArchiveIngestStatus.BLOCKED,
            blocked_reasons=("page_result_blocked",),
        )
    if not page_result.rows:
        return _build_archive_ingest_result(
            page_result=page_result,
            instrument_id=instrument_id,
            archive_date=archive_date,
            run_id=run_id,
            job_id=job_id,
            status=BinanceDerivativesContextArchiveIngestStatus.BLOCKED,
            blocked_reasons=("no_rows_to_ingest",),
        )
    if any(row.timestamp_ms is None for row in page_result.rows):
        return _build_archive_ingest_result(
            page_result=page_result,
            instrument_id=instrument_id,
            archive_date=archive_date,
            run_id=run_id,
            job_id=job_id,
            status=BinanceDerivativesContextArchiveIngestStatus.BLOCKED,
            blocked_reasons=("missing_row_timestamp",),
        )
    start_ts, end_ts = _page_result_time_bounds(page_result)
    effective_archive_date = archive_date or start_ts.date()
    effective_run_id = run_id or f"binance-derivatives-{page_result.page_result_id[:16]}"
    effective_job_id = job_id or effective_run_id
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    raw_records = [
        {
            **row.model_dump(mode="json"),
            "page_result_id": page_result.page_result_id,
            "page_request_urls": list(page_result.page_request_urls),
            "page_fetch_result_ids": list(page_result.page_fetch_result_ids),
            "normalized_rows_hash": page_result.normalized_rows_hash,
            "accepted_research_evidence": False,
            "native_to_hyperliquid": False,
        }
        for row in page_result.rows
    ]
    timeframe = page_result.interval or page_result.period
    raw_file = RawJsonlZstdWriter(layout, store).write_records(
        records=raw_records,
        venue="binance",
        datatype="derivatives_context",
        date=effective_archive_date.isoformat(),
        run_id=effective_run_id,
        job_id=effective_job_id,
        adapter_id="binance_usdm_derivatives_context_v1",
        source_endpoint_or_subscription=f"paginated_rest/{page_result.family.value}",
        symbols=(page_result.symbol,),
        start_ts=start_ts,
        end_ts=end_ts,
        instrument_id=instrument_id,
        timeframe=timeframe,
        filename=f"raw-{page_result.family.value}",
    )
    silver_rows = [
        _silver_context_row(
            row=row,
            page_result=page_result,
            instrument_id=instrument_id,
            raw_file_id=raw_file.file_id,
        )
        for row in page_result.rows
    ]
    silver_file = write_parquet_rows(
        layout=layout,
        store=store,
        rows=silver_rows,
        layer=ArchiveLayer.SILVER,
        dataset="derivatives_context",
        venue="binance",
        datatype="derivatives_context",
        date=effective_archive_date.isoformat(),
        job_id=effective_job_id,
        source_file_ids=(raw_file.file_id,),
        filename=f"silver-{page_result.family.value}-{page_result.page_result_id[:16]}",
        timeframe=timeframe,
        instrument_id=instrument_id,
    )
    return _build_archive_ingest_result(
        page_result=page_result,
        instrument_id=instrument_id,
        archive_date=effective_archive_date,
        run_id=effective_run_id,
        job_id=effective_job_id,
        status=BinanceDerivativesContextArchiveIngestStatus.COMPLETED,
        raw_file_id=raw_file.file_id,
        raw_file_ref=raw_file.path,
        silver_file_id=silver_file.file_id,
        silver_file_ref=silver_file.path,
        raw_row_count=raw_file.row_count or 0,
        silver_row_count=silver_file.row_count or 0,
    )


def build_binance_derivatives_context_coverage_report(
    *,
    page_result: BinanceDerivativesContextPageResult,
    archive_ingest: BinanceDerivativesContextArchiveIngestResult,
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None = None,
    coverage_min: float = 0.98,
) -> DataFamilyCoverageReport:
    rows = page_result.rows
    reasons: list[str] = []
    if page_result.status != BinanceDerivativesContextPageStatus.COMPLETED:
        reasons.append("page_result_blocked")
    if archive_ingest.status != BinanceDerivativesContextArchiveIngestStatus.COMPLETED:
        reasons.append("archive_ingest_blocked")
    if archive_ingest.raw_file_id is None or archive_ingest.silver_file_id is None:
        reasons.append("missing_archive_refs")
    if not archive_snapshot_ref:
        reasons.append("missing_archive_snapshot_ref")
    if page_result.family == BinanceDerivativesContextFamily.OPEN_INTEREST:
        reasons.append("current_context_snapshot_only")
    if not rows:
        reasons.append("no_rows")
    if any(row.timestamp_ms is None for row in rows):
        reasons.append("missing_row_timestamp")

    bucket_seconds = _coverage_bucket_seconds(page_result)
    if bucket_seconds is None:
        reasons.append("missing_bucket_seconds")
        bucket_seconds = 1
    coverage_window = _coverage_window_for_rows(rows, bucket_seconds)
    expected_bucket_count, observed_bucket_count, missing_buckets = _coverage_bucket_counts(
        rows=rows,
        bucket_seconds=bucket_seconds,
        coverage_window=coverage_window,
    )
    coverage_ratio = (
        observed_bucket_count / expected_bucket_count if expected_bucket_count else 0.0
    )
    if coverage_ratio < coverage_min:
        reasons.append("coverage_below_min")
    if missing_buckets:
        reasons.append("missing_buckets")

    unique_reasons = tuple(dict.fromkeys(reasons))
    accepted = not unique_reasons and coverage_ratio >= coverage_min
    identity = {
        "source_id": BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID,
        "family": page_result.family.value,
        "symbol": page_result.symbol,
        "page_result_id": page_result.page_result_id,
        "archive_ingest_id": archive_ingest.ingest_id,
        "archive_snapshot_ref": archive_snapshot_ref,
        "coverage_window": {
            "start": coverage_window.start.isoformat(),
            "end": coverage_window.end.isoformat(),
        },
        "bucket_seconds": bucket_seconds,
        "expected_bucket_count": expected_bucket_count,
        "observed_bucket_count": observed_bucket_count,
        "missing_buckets_hash": manifest_rows_hash({"bucket": bucket} for bucket in missing_buckets),
        "accepted": accepted,
        "reasons": list(unique_reasons),
    }
    return DataFamilyCoverageReport(
        coverage_report_id=canonical_json_hash(identity),
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol=page_result.symbol,
        family=page_result.family.value,
        venue="binance",
        source_ids=(BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID,),
        source_cost_classes=(CostClass.PUBLIC_RATE_LIMITED,),
        labels=(CoverageLabel.EXTERNAL_COMPARISON,),
        coverage_window=coverage_window,
        expected_buckets=ExpectedBuckets(
            bucket_seconds=bucket_seconds,
            count=expected_bucket_count,
        ),
        observed_buckets=observed_bucket_count,
        coverage_ratio=coverage_ratio,
        coverage_min=coverage_min,
        missing_buckets=missing_buckets,
        accepted_for_research_reporting=accepted,
        reason=unique_reasons,
    )


def run_binance_derivatives_context_backfill(
    *,
    archive_root: str | Path,
    family: str | BinanceDerivativesContextFamily,
    symbol: str,
    instrument_id: str,
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None = None,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    interval: str | None = None,
    period: str | None = None,
    limit: int | None = None,
    max_pages: int = 10,
    base_url: str = BINANCE_DERIVATIVES_CONTEXT_BASE_URL,
    contract_type: str | None = "PERPETUAL",
    get: Callable[[str], BinanceDerivativesContextGetResult | Mapping[str, Any]] | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    coverage_min: float = 0.98,
) -> BinanceDerivativesContextBackfillResult:
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    page_result = fetch_binance_derivatives_context_pages(
        family=family,
        symbol=symbol,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        interval=interval,
        period=period,
        limit=limit,
        max_pages=max_pages,
        base_url=base_url,
        contract_type=contract_type,
        get=get,
        max_bytes=max_bytes,
    )
    archive_ingest = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=archive_root,
        page_result=page_result,
        instrument_id=instrument_id,
    )
    coverage_report = build_binance_derivatives_context_coverage_report(
        page_result=page_result,
        archive_ingest=archive_ingest,
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        coverage_min=coverage_min,
    )
    coverage_ref = _write_derivatives_coverage_report(layout, coverage_report)
    blocker_reasons = tuple(
        dict.fromkeys(
            (
                *page_result.blocked_reasons,
                *archive_ingest.blocked_reasons,
                *coverage_report.reason,
            )
        )
    )
    status = (
        BinanceDerivativesContextBackfillStatus.COMPLETED
        if coverage_report.accepted_for_research_reporting and not blocker_reasons
        else BinanceDerivativesContextBackfillStatus.BLOCKED
    )
    result_blockers = () if status == BinanceDerivativesContextBackfillStatus.COMPLETED else blocker_reasons
    backfill_id = _binance_derivatives_backfill_id(
        family=page_result.family,
        symbol=page_result.symbol,
        instrument_id=instrument_id,
        page_result_id=page_result.page_result_id,
        archive_ingest_id=archive_ingest.ingest_id,
        coverage_report_id=coverage_report.coverage_report_id,
        accepted_for_research_reporting=coverage_report.accepted_for_research_reporting,
        blocker_reasons=result_blockers,
    )
    return BinanceDerivativesContextBackfillResult(
        backfill_id=backfill_id,
        status=status,
        family=page_result.family,
        symbol=page_result.symbol,
        instrument_id=instrument_id,
        page_result_id=page_result.page_result_id,
        archive_ingest_id=archive_ingest.ingest_id,
        coverage_report_id=coverage_report.coverage_report_id,
        coverage_report_ref=coverage_ref,
        accepted_for_research_reporting=coverage_report.accepted_for_research_reporting,
        blocker_reasons=result_blockers,
    )


def _coerce_family(family: str | BinanceDerivativesContextFamily) -> BinanceDerivativesContextFamily:
    try:
        return BinanceDerivativesContextFamily(family)
    except ValueError as exc:
        raise ValueError(f"unsupported Binance derivatives context family: {family}") from exc


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol is required")
    return normalized


def _normalize_optional_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_request_inputs(
    *,
    spec: BinanceDerivativesContextEndpointSpec,
    start_time_ms: int | None,
    end_time_ms: int | None,
    interval: str | None,
    period: str | None,
    limit: int | None,
    contract_type: str | None,
) -> None:
    if spec.requires_interval and interval is None:
        raise ValueError(f"{spec.family.value} requires interval")
    if not spec.requires_interval and interval is not None:
        raise ValueError(f"{spec.family.value} does not accept interval")
    if spec.requires_period and period is None:
        raise ValueError(f"{spec.family.value} requires period")
    if not spec.requires_period and period is not None:
        raise ValueError(f"{spec.family.value} does not accept period")
    if spec.requires_contract_type and contract_type is None:
        raise ValueError(f"{spec.family.value} requires contract_type")
    if not spec.requires_contract_type and contract_type not in {None, "PERPETUAL"}:
        raise ValueError(f"{spec.family.value} does not accept contract_type")
    if spec.limit_max is None and limit is not None:
        raise ValueError(f"{spec.family.value} does not accept limit")
    if limit is not None and spec.limit_max is not None and limit > spec.limit_max:
        raise ValueError(f"{spec.family.value} limit exceeds max {spec.limit_max}")
    if not spec.accepts_time_range and (
        start_time_ms is not None or end_time_ms is not None
    ):
        raise ValueError(f"{spec.family.value} does not accept start/end time")
    if start_time_ms is not None and start_time_ms < 0:
        raise ValueError("start_time_ms must be non-negative")
    if end_time_ms is not None and end_time_ms < 0:
        raise ValueError("end_time_ms must be non-negative")
    if end_time_ms is not None and start_time_ms is not None and end_time_ms < start_time_ms:
        raise ValueError("end_time_ms must be greater than or equal to start_time_ms")


def binance_derivatives_context_family_values() -> tuple[str, ...]:
    return tuple(family.value for family in BinanceDerivativesContextFamily)


def binance_derivatives_context_specs_payload() -> tuple[dict[str, Any], ...]:
    return tuple(
        spec.model_dump(mode="json")
        for spec in BINANCE_DERIVATIVES_CONTEXT_ENDPOINT_SPECS.values()
    )


def _coerce_derivatives_get_result(
    value: BinanceDerivativesContextGetResult | Mapping[str, Any],
) -> BinanceDerivativesContextGetResult:
    if isinstance(value, BinanceDerivativesContextGetResult):
        return value
    return BinanceDerivativesContextGetResult.model_validate(dict(value))


def _payload_to_rows(payload: Any) -> tuple[Any, ...]:
    if isinstance(payload, list):
        return tuple(payload)
    if isinstance(payload, dict):
        return (payload,)
    raise ValueError("Binance derivatives response must be an object or array")


def _normalize_binance_derivatives_context_row(
    request: BinanceDerivativesContextRequest,
    raw_row: Any,
) -> BinanceDerivativesContextNormalizedRow:
    if request.family in {
        BinanceDerivativesContextFamily.MARK_PRICE_KLINES,
        BinanceDerivativesContextFamily.INDEX_PRICE_KLINES,
        BinanceDerivativesContextFamily.PREMIUM_INDEX_KLINES,
    }:
        return _normalize_derivatives_kline_row(request, raw_row)
    if not isinstance(raw_row, Mapping):
        raise ValueError(f"{request.family.value} rows must be JSON objects")
    raw = dict(raw_row)
    if request.family == BinanceDerivativesContextFamily.FUNDING_RATE_HISTORY:
        return _normalize_funding_rate_history_row(request, raw)
    if request.family == BinanceDerivativesContextFamily.OPEN_INTEREST:
        return _normalize_open_interest_row(request, raw)
    if request.family == BinanceDerivativesContextFamily.OPEN_INTEREST_STATISTICS:
        return _normalize_open_interest_statistics_row(request, raw)
    if request.family == BinanceDerivativesContextFamily.TAKER_BUY_SELL_VOLUME:
        return _normalize_taker_buy_sell_row(request, raw)
    if request.family == BinanceDerivativesContextFamily.LONG_SHORT_RATIOS:
        return _normalize_long_short_ratio_row(request, raw)
    if request.family == BinanceDerivativesContextFamily.BASIS:
        return _normalize_basis_row(request, raw)
    raise ValueError(f"unsupported Binance derivatives context family: {request.family.value}")


def _normalize_funding_rate_history_row(
    request: BinanceDerivativesContextRequest,
    raw: dict[str, Any],
) -> BinanceDerivativesContextNormalizedRow:
    symbol = _row_symbol(raw, request)
    quote_asset = _base_quote_assets(symbol)[1]
    timestamp_ms = _int_field(raw, "fundingTime")
    numeric_fields = _numeric_fields(
        raw,
        {
            "fundingRate": "funding_rate",
            "markPrice": "mark_price",
        },
    )
    unit_fields = {
        "funding_rate": "rate",
        "mark_price": quote_asset,
    }
    return _context_row(
        request=request,
        raw=raw,
        symbol=symbol,
        timestamp_ms=timestamp_ms,
        publication_time_ms=timestamp_ms,
        numeric_fields=numeric_fields,
        unit_fields=unit_fields,
    )


def _normalize_open_interest_row(
    request: BinanceDerivativesContextRequest,
    raw: dict[str, Any],
) -> BinanceDerivativesContextNormalizedRow:
    symbol = _row_symbol(raw, request)
    timestamp_ms = _int_field(raw, "time")
    return _context_row(
        request=request,
        raw=raw,
        symbol=symbol,
        timestamp_ms=timestamp_ms,
        publication_time_ms=timestamp_ms,
        numeric_fields=_numeric_fields(raw, {"openInterest": "open_interest_contracts"}),
        unit_fields={"open_interest_contracts": "contracts"},
    )


def _normalize_open_interest_statistics_row(
    request: BinanceDerivativesContextRequest,
    raw: dict[str, Any],
) -> BinanceDerivativesContextNormalizedRow:
    symbol = _row_symbol(raw, request)
    quote_asset = _base_quote_assets(symbol)[1]
    timestamp_ms = _int_field(raw, "timestamp")
    return _context_row(
        request=request,
        raw=raw,
        symbol=symbol,
        timestamp_ms=timestamp_ms,
        publication_time_ms=timestamp_ms,
        numeric_fields=_numeric_fields(
            raw,
            {
                "sumOpenInterest": "open_interest_contracts",
                "sumOpenInterestValue": "open_interest_value",
            },
        ),
        unit_fields={
            "open_interest_contracts": "contracts",
            "open_interest_value": quote_asset,
        },
    )


def _normalize_derivatives_kline_row(
    request: BinanceDerivativesContextRequest,
    raw_row: Any,
) -> BinanceDerivativesContextNormalizedRow:
    if not isinstance(raw_row, Sequence) or isinstance(raw_row, (str, bytes, bytearray)):
        raise ValueError(f"{request.family.value} rows must be JSON arrays")
    if len(raw_row) < 7:
        raise ValueError(f"{request.family.value} rows require at least 7 columns")
    raw = {
        "open_time": raw_row[0],
        "open": raw_row[1],
        "high": raw_row[2],
        "low": raw_row[3],
        "close": raw_row[4],
        "ignore": raw_row[5] if len(raw_row) > 5 else None,
        "close_time": raw_row[6],
        "raw": list(raw_row),
    }
    quote_asset = _base_quote_assets(request.symbol)[1]
    open_time_ms = _int_field(raw, "open_time")
    close_time_ms = _int_field(raw, "close_time")
    if request.family == BinanceDerivativesContextFamily.PREMIUM_INDEX_KLINES:
        field_map = {
            "open": "open_premium_index",
            "high": "high_premium_index",
            "low": "low_premium_index",
            "close": "close_premium_index",
        }
        units = {
            "open_premium_index": "rate",
            "high_premium_index": "rate",
            "low_premium_index": "rate",
            "close_premium_index": "rate",
        }
    else:
        field_map = {
            "open": "open_price",
            "high": "high_price",
            "low": "low_price",
            "close": "close_price",
        }
        units = {
            "open_price": quote_asset,
            "high_price": quote_asset,
            "low_price": quote_asset,
            "close_price": quote_asset,
        }
    return _context_row(
        request=request,
        raw=raw,
        symbol=request.symbol,
        timestamp_ms=open_time_ms,
        open_time_ms=open_time_ms,
        close_time_ms=close_time_ms,
        publication_time_ms=close_time_ms,
        numeric_fields=_numeric_fields(raw, field_map),
        unit_fields=units,
    )


def _normalize_taker_buy_sell_row(
    request: BinanceDerivativesContextRequest,
    raw: dict[str, Any],
) -> BinanceDerivativesContextNormalizedRow:
    symbol = _row_symbol(raw, request)
    base_asset = _base_quote_assets(symbol)[0]
    timestamp_ms = _int_field(raw, "timestamp")
    return _context_row(
        request=request,
        raw=raw,
        symbol=symbol,
        timestamp_ms=timestamp_ms,
        publication_time_ms=timestamp_ms,
        numeric_fields=_numeric_fields(
            raw,
            {
                "buySellRatio": "buy_sell_ratio",
                "buyVol": "taker_buy_base_asset_volume",
                "sellVol": "taker_sell_base_asset_volume",
            },
        ),
        unit_fields={
            "buy_sell_ratio": "ratio",
            "taker_buy_base_asset_volume": base_asset,
            "taker_sell_base_asset_volume": base_asset,
        },
    )


def _normalize_long_short_ratio_row(
    request: BinanceDerivativesContextRequest,
    raw: dict[str, Any],
) -> BinanceDerivativesContextNormalizedRow:
    symbol = _row_symbol(raw, request)
    timestamp_ms = _int_field(raw, "timestamp")
    return _context_row(
        request=request,
        raw=raw,
        symbol=symbol,
        timestamp_ms=timestamp_ms,
        publication_time_ms=timestamp_ms,
        numeric_fields=_numeric_fields(
            raw,
            {
                "longShortRatio": "long_short_ratio",
                "longAccount": "long_account_share",
                "shortAccount": "short_account_share",
            },
        ),
        unit_fields={
            "long_short_ratio": "ratio",
            "long_account_share": "share",
            "short_account_share": "share",
        },
    )


def _normalize_basis_row(
    request: BinanceDerivativesContextRequest,
    raw: dict[str, Any],
) -> BinanceDerivativesContextNormalizedRow:
    symbol = str(raw.get("pair") or request.symbol).upper()
    quote_asset = _base_quote_assets(symbol)[1]
    timestamp_ms = _int_field(raw, "timestamp")
    return _context_row(
        request=request,
        raw=raw,
        symbol=symbol,
        timestamp_ms=timestamp_ms,
        publication_time_ms=timestamp_ms,
        numeric_fields=_numeric_fields(
            raw,
            {
                "basis": "basis_value",
                "basisRate": "basis_rate",
                "annualizedBasisRate": "annualized_basis_rate",
            },
        ),
        unit_fields={
            "basis_value": quote_asset,
            "basis_rate": "rate",
            "annualized_basis_rate": "rate",
        },
    )


def _context_row(
    *,
    request: BinanceDerivativesContextRequest,
    raw: dict[str, Any],
    symbol: str,
    timestamp_ms: int | None,
    publication_time_ms: int | None,
    numeric_fields: dict[str, str],
    unit_fields: dict[str, str],
    open_time_ms: int | None = None,
    close_time_ms: int | None = None,
) -> BinanceDerivativesContextNormalizedRow:
    return BinanceDerivativesContextNormalizedRow(
        family=request.family,
        symbol=symbol,
        timestamp_ms=timestamp_ms,
        open_time_ms=open_time_ms,
        close_time_ms=close_time_ms,
        publication_time_ms=publication_time_ms,
        interval=request.interval,
        period=request.period,
        bucket_seconds=_bucket_seconds(request.interval or request.period),
        numeric_fields=numeric_fields,
        unit_fields={
            key: value for key, value in unit_fields.items() if key in numeric_fields
        },
        raw_fields=raw,
    )


def _row_symbol(raw: Mapping[str, Any], request: BinanceDerivativesContextRequest) -> str:
    value = raw.get("symbol") or raw.get("pair") or request.symbol
    return str(value).strip().upper()


def _numeric_fields(raw: Mapping[str, Any], field_map: Mapping[str, str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_key, normalized_key in field_map.items():
        if raw_key not in raw:
            continue
        value = raw[raw_key]
        if value is None or value == "":
            continue
        fields[normalized_key] = str(value)
    return fields


def _int_field(raw: Mapping[str, Any], key: str) -> int | None:
    if key not in raw or raw[key] in {None, ""}:
        return None
    value = raw[key]
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be an integer timestamp") from exc


def _base_quote_assets(symbol: str) -> tuple[str, str]:
    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[: -len(quote)], quote
    return symbol, "quote"


def _bucket_seconds(value: str | None) -> int | None:
    if value is None:
        return None
    unit = value[-1]
    try:
        count = int(value[:-1])
    except ValueError as exc:
        raise ValueError(f"unsupported interval/period: {value}") from exc
    multiplier = {
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
        "w": 7 * 24 * 60 * 60,
    }.get(unit)
    if multiplier is None:
        raise ValueError(f"unsupported interval/period: {value}")
    return count * multiplier


def _build_fetch_result(
    *,
    request: BinanceDerivativesContextRequest,
    status: BinanceDerivativesContextFetchStatus,
    status_code: int | None = None,
    headers: Mapping[str, str] | None = None,
    content: bytes = b"",
    raw_row_count: int = 0,
    rows: tuple[BinanceDerivativesContextNormalizedRow, ...] = (),
    blocked_reasons: tuple[str, ...] = (),
) -> BinanceDerivativesContextFetchResult:
    content_sha256 = hashlib.sha256(content).hexdigest() if content else None
    rows_hash = _binance_derivatives_rows_hash(rows)
    identity = _binance_derivatives_fetch_result_id(
        request=request,
        status=status,
        status_code=status_code,
        content_sha256=content_sha256,
        byte_count=len(content),
        raw_row_count=raw_row_count,
        normalized_rows_hash=rows_hash,
        blocked_reasons=blocked_reasons,
    )
    return BinanceDerivativesContextFetchResult(
        fetch_result_id=identity,
        request=request,
        status=status,
        status_code=status_code,
        headers=dict(headers or {}),
        content_sha256=content_sha256,
        byte_count=len(content),
        raw_row_count=raw_row_count,
        normalized_row_count=len(rows),
        normalized_rows_hash=rows_hash,
        rows=rows,
        blocked_reasons=blocked_reasons,
    )


def _binance_derivatives_rows_hash(
    rows: tuple[BinanceDerivativesContextNormalizedRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def _binance_derivatives_fetch_result_id(
    *,
    request: BinanceDerivativesContextRequest,
    status: BinanceDerivativesContextFetchStatus,
    status_code: int | None,
    content_sha256: str | None,
    byte_count: int,
    raw_row_count: int,
    normalized_rows_hash: str,
    blocked_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "source_id": request.source_id,
            "family": request.family.value,
            "url": request.url,
            "status": status.value,
            "status_code": status_code,
            "content_sha256": content_sha256,
            "byte_count": byte_count,
            "raw_row_count": raw_row_count,
            "normalized_rows_hash": normalized_rows_hash,
            "blocked_reasons": list(blocked_reasons),
        }
    )


def _next_page_start_ms(
    rows: tuple[BinanceDerivativesContextNormalizedRow, ...],
    *,
    fallback_cursor: int | None,
) -> int:
    timestamps = [
        row.timestamp_ms
        for row in rows
        if row.timestamp_ms is not None
    ]
    if not timestamps:
        if fallback_cursor is None:
            raise ValueError("cannot advance cursor without row timestamps")
        return fallback_cursor
    last_timestamp = max(timestamps)
    bucket_seconds = next(
        (row.bucket_seconds for row in rows if row.bucket_seconds is not None),
        None,
    )
    if bucket_seconds is not None:
        return last_timestamp + bucket_seconds * 1000
    return last_timestamp + 1


def _build_page_result(
    *,
    family: BinanceDerivativesContextFamily,
    symbol: str,
    start_time_ms: int | None,
    end_time_ms: int | None,
    interval: str | None,
    period: str | None,
    limit: int | None,
    max_pages: int,
    status: BinanceDerivativesContextPageStatus,
    page_request_urls: tuple[str, ...] = (),
    page_fetch_result_ids: tuple[str, ...] = (),
    rows: tuple[BinanceDerivativesContextNormalizedRow, ...] = (),
    blocked_reasons: tuple[str, ...] = (),
) -> BinanceDerivativesContextPageResult:
    rows_hash = _binance_derivatives_rows_hash(rows)
    result_id = _binance_derivatives_page_result_id(
        family=family,
        symbol=symbol,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        interval=interval,
        period=period,
        limit=limit,
        max_pages=max_pages,
        status=status,
        page_request_urls=page_request_urls,
        page_fetch_result_ids=page_fetch_result_ids,
        normalized_rows_hash=rows_hash,
        blocked_reasons=blocked_reasons,
    )
    return BinanceDerivativesContextPageResult(
        page_result_id=result_id,
        family=family,
        symbol=symbol,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        interval=interval,
        period=period,
        limit=limit,
        max_pages=max_pages,
        status=status,
        page_count=len(page_fetch_result_ids),
        page_request_urls=page_request_urls,
        page_fetch_result_ids=page_fetch_result_ids,
        normalized_row_count=len(rows),
        normalized_rows_hash=rows_hash,
        rows=rows,
        blocked_reasons=blocked_reasons,
    )


def _binance_derivatives_page_result_id(
    *,
    family: BinanceDerivativesContextFamily,
    symbol: str,
    start_time_ms: int | None,
    end_time_ms: int | None,
    interval: str | None,
    period: str | None,
    limit: int | None,
    max_pages: int,
    status: BinanceDerivativesContextPageStatus,
    page_request_urls: tuple[str, ...],
    page_fetch_result_ids: tuple[str, ...],
    normalized_rows_hash: str,
    blocked_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "source_id": BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID,
            "family": family.value,
            "symbol": symbol,
            "start_time_ms": start_time_ms,
            "end_time_ms": end_time_ms,
            "interval": interval,
            "period": period,
            "limit": limit,
            "max_pages": max_pages,
            "status": status.value,
            "page_request_urls": list(page_request_urls),
            "page_fetch_result_ids": list(page_fetch_result_ids),
            "normalized_rows_hash": normalized_rows_hash,
            "blocked_reasons": list(blocked_reasons),
        }
    )


def _page_result_time_bounds(
    page_result: BinanceDerivativesContextPageResult,
) -> tuple[datetime, datetime]:
    start_ms = min(row.timestamp_ms for row in page_result.rows if row.timestamp_ms is not None)
    end_candidates = [
        value
        for row in page_result.rows
        for value in (row.close_time_ms, row.publication_time_ms, row.timestamp_ms)
        if value is not None
    ]
    end_ms = max(end_candidates) + 1
    return _datetime_from_ms(start_ms), _datetime_from_ms(end_ms)


def _silver_context_row(
    *,
    row: BinanceDerivativesContextNormalizedRow,
    page_result: BinanceDerivativesContextPageResult,
    instrument_id: str,
    raw_file_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": V2_SCHEMA_VERSION,
        "venue": "binance",
        "instrument_id": instrument_id,
        "symbol": row.symbol,
        "family": row.family.value,
        "ts": _datetime_from_ms(row.timestamp_ms).isoformat() if row.timestamp_ms is not None else None,
        "open_ts": _datetime_from_ms(row.open_time_ms).isoformat() if row.open_time_ms is not None else None,
        "close_ts": _datetime_from_ms(row.close_time_ms).isoformat() if row.close_time_ms is not None else None,
        "publication_ts": (
            _datetime_from_ms(row.publication_time_ms).isoformat()
            if row.publication_time_ms is not None
            else None
        ),
        "timestamp_ms": row.timestamp_ms,
        "open_time_ms": row.open_time_ms,
        "close_time_ms": row.close_time_ms,
        "publication_time_ms": row.publication_time_ms,
        "interval": row.interval,
        "period": row.period,
        "bucket_seconds": row.bucket_seconds,
        "numeric_fields_json": _canonical_json_text(row.numeric_fields),
        "unit_fields_json": _canonical_json_text(row.unit_fields),
        "raw_fields_json": _canonical_json_text(row.raw_fields),
        "page_result_id": page_result.page_result_id,
        "page_fetch_result_ids_json": _canonical_json_text(list(page_result.page_fetch_result_ids)),
        "source_file_id": raw_file_id,
        "source_layer": ArchiveLayer.RAW.value,
        "accepted_research_evidence": False,
        "native_to_hyperliquid": False,
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


def _build_archive_ingest_result(
    *,
    page_result: BinanceDerivativesContextPageResult,
    instrument_id: str,
    archive_date: date | None,
    run_id: str | None,
    job_id: str | None,
    status: BinanceDerivativesContextArchiveIngestStatus,
    raw_file_id: str | None = None,
    raw_file_ref: str | None = None,
    silver_file_id: str | None = None,
    silver_file_ref: str | None = None,
    raw_row_count: int = 0,
    silver_row_count: int = 0,
    blocked_reasons: tuple[str, ...] = (),
) -> BinanceDerivativesContextArchiveIngestResult:
    ingest_id = _binance_derivatives_archive_ingest_id(
        page_result_id=page_result.page_result_id,
        family=page_result.family,
        symbol=page_result.symbol,
        instrument_id=instrument_id,
        archive_date=archive_date.isoformat() if archive_date else None,
        run_id=run_id,
        job_id=job_id,
        status=status,
        raw_file_id=raw_file_id,
        silver_file_id=silver_file_id,
        raw_row_count=raw_row_count,
        silver_row_count=silver_row_count,
        normalized_rows_hash=page_result.normalized_rows_hash,
        blocked_reasons=blocked_reasons,
    )
    return BinanceDerivativesContextArchiveIngestResult(
        ingest_id=ingest_id,
        page_result_id=page_result.page_result_id,
        family=page_result.family,
        symbol=page_result.symbol,
        instrument_id=instrument_id,
        archive_date=archive_date,
        run_id=run_id,
        job_id=job_id,
        status=status,
        raw_file_id=raw_file_id,
        raw_file_ref=raw_file_ref,
        silver_file_id=silver_file_id,
        silver_file_ref=silver_file_ref,
        raw_row_count=raw_row_count,
        silver_row_count=silver_row_count,
        normalized_rows_hash=page_result.normalized_rows_hash,
        blocked_reasons=blocked_reasons,
    )


def _binance_derivatives_archive_ingest_id(
    *,
    page_result_id: str,
    family: BinanceDerivativesContextFamily,
    symbol: str,
    instrument_id: str,
    archive_date: str | None,
    run_id: str | None,
    job_id: str | None,
    status: BinanceDerivativesContextArchiveIngestStatus,
    raw_file_id: str | None,
    silver_file_id: str | None,
    raw_row_count: int,
    silver_row_count: int,
    normalized_rows_hash: str,
    blocked_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "page_result_id": page_result_id,
            "family": family.value,
            "symbol": symbol,
            "instrument_id": instrument_id,
            "archive_date": archive_date,
            "run_id": run_id,
            "job_id": job_id,
            "status": status.value,
            "raw_file_id": raw_file_id,
            "silver_file_id": silver_file_id,
            "raw_row_count": raw_row_count,
            "silver_row_count": silver_row_count,
            "normalized_rows_hash": normalized_rows_hash,
            "blocked_reasons": list(blocked_reasons),
        }
    )


def _datetime_from_ms(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)


def _canonical_json_text(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _coverage_bucket_seconds(
    page_result: BinanceDerivativesContextPageResult,
) -> int | None:
    for row in page_result.rows:
        if row.bucket_seconds is not None:
            return row.bucket_seconds
    if page_result.family == BinanceDerivativesContextFamily.FUNDING_RATE_HISTORY:
        return 8 * 60 * 60
    if page_result.family == BinanceDerivativesContextFamily.OPEN_INTEREST:
        return 1
    return None


def _coverage_window_for_rows(
    rows: tuple[BinanceDerivativesContextNormalizedRow, ...],
    bucket_seconds: int,
) -> CoverageWindow:
    timestamps = [row.timestamp_ms for row in rows if row.timestamp_ms is not None]
    if not timestamps:
        start = datetime.fromtimestamp(0, tz=UTC)
        end = datetime.fromtimestamp(bucket_seconds, tz=UTC)
        return CoverageWindow(start=start, end=end)
    start_ms = min(timestamps)
    end_ms = max(timestamps) + bucket_seconds * 1000
    return CoverageWindow(start=_datetime_from_ms(start_ms), end=_datetime_from_ms(end_ms))


def _coverage_bucket_counts(
    *,
    rows: tuple[BinanceDerivativesContextNormalizedRow, ...],
    bucket_seconds: int,
    coverage_window: CoverageWindow,
) -> tuple[int, int, tuple[str, ...]]:
    bucket_ms = bucket_seconds * 1000
    start_ms = int(coverage_window.start.timestamp() * 1000)
    end_ms = int(coverage_window.end.timestamp() * 1000)
    expected_starts = tuple(range(start_ms, end_ms, bucket_ms))
    observed_starts = {
        ((row.timestamp_ms - start_ms) // bucket_ms) * bucket_ms + start_ms
        for row in rows
        if row.timestamp_ms is not None and row.timestamp_ms >= start_ms
    }
    missing = tuple(
        _datetime_from_ms(bucket_start).isoformat()
        for bucket_start in expected_starts
        if bucket_start not in observed_starts
    )
    observed = sum(1 for bucket_start in expected_starts if bucket_start in observed_starts)
    return len(expected_starts), observed, missing


def _write_derivatives_coverage_report(
    layout: ArchiveLayout,
    report: DataFamilyCoverageReport,
) -> str:
    path = layout.resolve(
        "manifests",
        "coverage_reports",
        f"data_family_coverage_{report.coverage_report_id[:16]}.json",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            report.model_dump(mode="json"),
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return layout.relative_to_root(path)


def _binance_derivatives_backfill_id(
    *,
    family: BinanceDerivativesContextFamily,
    symbol: str,
    instrument_id: str,
    page_result_id: str,
    archive_ingest_id: str,
    coverage_report_id: str,
    accepted_for_research_reporting: bool,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "binance_derivatives_context_backfill_result",
            "family": family.value,
            "symbol": symbol,
            "instrument_id": instrument_id,
            "page_result_id": page_result_id,
            "archive_ingest_id": archive_ingest_id,
            "coverage_report_id": coverage_report_id,
            "accepted_for_research_reporting": accepted_for_research_reporting,
            "blocker_reasons": list(blocker_reasons),
        }
    )
