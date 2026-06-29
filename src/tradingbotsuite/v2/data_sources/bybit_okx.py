# V2-AUDIT-ID: V2-AUD-DATASRC-024
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, strict_free_public_rate_limited, no_downloads
# V2-OWNER: v2_data_sources
"""Bybit/OKX public market availability matrix scaffolding."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import (
    canonical_json_hash,
    file_sha256,
    manifest_rows_hash,
)
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.data_sources.schemas import (
    CostClass,
    SourceRegistryEntry,
    SymbolMapSnapshot,
    require_strict_zero_dollar_source,
    require_verified_external_mapping,
)
from tradingbotsuite.v2.security.boundary import require_research_boundary

BYBIT_PUBLIC_MARKET_BASE_URL = "https://api.bybit.com"
OKX_PUBLIC_MARKET_BASE_URL = "https://www.okx.com"

BYBIT_PUBLIC_MARKET_SOURCE_ID = "bybit_public_market"
OKX_PUBLIC_MARKET_SOURCE_ID = "okx_public_market"
DEFAULT_BYBIT_OKX_SOURCE_IDS = (
    BYBIT_PUBLIC_MARKET_SOURCE_ID,
    OKX_PUBLIC_MARKET_SOURCE_ID,
)


class BybitOkxAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    BLOCKED_MAPPING = "blocked_mapping"
    BLOCKED_ENDPOINT_LIMIT = "blocked_endpoint_limit"
    PROBE_ERROR = "probe_error"


class BybitOkxFetchStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    EMPTY = "empty"
    FETCH_ERROR = "fetch_error"
    PARSE_ERROR = "parse_error"


class BybitOkxEndpointSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_key: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    family: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    interval: str | None = None
    limit: int | None = Field(default=None, ge=1)
    rate_limit_hint: str = Field(min_length=1)
    supports_date_window: bool = True
    endpoint_caveats: tuple[str, ...] = ()


class BybitOkxGetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    payload: Any = None
    error: str | None = None


class BybitOkxAvailabilityRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    request_params: dict[str, str] = Field(default_factory=dict)
    request_url: str = Field(min_length=1)
    probe_start_ms: int | None = Field(default=None, ge=0)
    probe_end_ms: int | None = Field(default=None, ge=0)
    supports_date_window: bool = True

    @model_validator(mode="after")
    def _validate_request(self) -> "BybitOkxAvailabilityRequest":
        if self.probe_start_ms is not None and self.probe_end_ms is not None:
            if self.probe_end_ms <= self.probe_start_ms:
                raise ValueError("probe_end_ms must be greater than probe_start_ms")
        return self


class BybitOkxPaginatedRequestPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    plan_type: str = "bybit_okx_paginated_request_plan"
    endpoint_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    day: date
    page_span_ms: int | None = Field(default=None, ge=1)
    max_pages: int = Field(ge=1)
    requests: tuple[BybitOkxAvailabilityRequest, ...] = ()
    request_count: int = Field(ge=0)
    truncated: bool = False
    truncation_reasons: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
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
    def _validate_plan(self) -> "BybitOkxPaginatedRequestPlan":
        require_research_boundary(self, context="Bybit/OKX paginated request plan")
        if self.plan_type != "bybit_okx_paginated_request_plan":
            raise ValueError("plan_type must be bybit_okx_paginated_request_plan")
        if self.request_count != len(self.requests):
            raise ValueError("request_count must match requests")
        if self.truncated and not self.truncation_reasons:
            raise ValueError("truncated plans require truncation_reasons")
        if self.blocked_reasons and self.requests:
            raise ValueError("blocked plans cannot include requests")
        if not self.blocked_reasons and not self.requests:
            raise ValueError("unblocked paginated plans require requests")
        return self


class BybitOkxAvailabilityRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    endpoint_id: str = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    hyperliquid_coin: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_key: str = Field(min_length=1)
    venue_symbol: str | None = None
    probe_date: date
    market_type: str = Field(min_length=1)
    family: str = Field(min_length=1)
    interval: str | None = None
    endpoint_path: str = Field(min_length=1)
    request_url: str | None = None
    request_params: dict[str, str] = Field(default_factory=dict)
    probe_start_ms: int | None = Field(default=None, ge=0)
    probe_end_ms: int | None = Field(default=None, ge=0)
    request_limit: int | None = Field(default=None, ge=1)
    rate_limit_hint: str = Field(min_length=1)
    supports_date_window: bool
    availability_status: BybitOkxAvailabilityStatus
    http_status_code: int | None = None
    response_row_count: int | None = Field(default=None, ge=0)
    source_cost_class: CostClass
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
    blocked_reasons: tuple[str, ...] = ()
    probe_error: str | None = None
    endpoint_caveats: tuple[str, ...] = ()
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
    def _validate_row(self) -> "BybitOkxAvailabilityRow":
        require_research_boundary(self, context="Bybit/OKX availability row")
        if self.native_to_hyperliquid:
            raise ValueError("Bybit/OKX rows cannot be Hyperliquid-native")
        if self.accepted_historical_coverage_proof:
            raise ValueError("availability rows are not historical coverage proof")
        if self.availability_status == BybitOkxAvailabilityStatus.AVAILABLE:
            if not self.request_url:
                raise ValueError("available rows require request_url")
            if not self.response_row_count:
                raise ValueError("available rows require positive response_row_count")
        if self.availability_status in {
            BybitOkxAvailabilityStatus.BLOCKED_MAPPING,
            BybitOkxAvailabilityStatus.BLOCKED_ENDPOINT_LIMIT,
            BybitOkxAvailabilityStatus.PROBE_ERROR,
        } and not self.blocked_reasons:
            raise ValueError(f"{self.availability_status.value} rows require blocker reasons")
        return self


class BybitOkxAvailabilityManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "bybit_okx_availability_manifest"
    availability_manifest_id: str = Field(min_length=64, max_length=64)
    start_date: date
    end_date: date
    source_ids: tuple[str, ...] = Field(min_length=1)
    endpoint_ids: tuple[str, ...] = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    strict_zero_dollar_mode: bool = True
    rows: tuple[BybitOkxAvailabilityRow, ...]
    row_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    blocked_mapping_count: int = Field(ge=0)
    blocked_endpoint_limit_count: int = Field(ge=0)
    probe_error_count: int = Field(ge=0)
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
    def _validate_manifest(self) -> "BybitOkxAvailabilityManifest":
        require_research_boundary(self, context="Bybit/OKX availability manifest")
        if self.manifest_type != "bybit_okx_availability_manifest":
            raise ValueError("manifest_type must be bybit_okx_availability_manifest")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.available_count != _count_status(self.rows, BybitOkxAvailabilityStatus.AVAILABLE):
            raise ValueError("available_count does not match rows")
        if self.missing_count != _count_status(self.rows, BybitOkxAvailabilityStatus.MISSING):
            raise ValueError("missing_count does not match rows")
        if self.blocked_mapping_count != _count_status(
            self.rows,
            BybitOkxAvailabilityStatus.BLOCKED_MAPPING,
        ):
            raise ValueError("blocked_mapping_count does not match rows")
        if self.blocked_endpoint_limit_count != _count_status(
            self.rows,
            BybitOkxAvailabilityStatus.BLOCKED_ENDPOINT_LIMIT,
        ):
            raise ValueError("blocked_endpoint_limit_count does not match rows")
        if self.probe_error_count != _count_status(self.rows, BybitOkxAvailabilityStatus.PROBE_ERROR):
            raise ValueError("probe_error_count does not match rows")
        expected_hash = bybit_okx_availability_rows_hash(self.rows)
        if self.row_manifest_hash != expected_hash:
            raise ValueError("row_manifest_hash does not match availability rows")
        expected_id = bybit_okx_availability_manifest_id_for(
            start_date=self.start_date,
            end_date=self.end_date,
            source_ids=self.source_ids,
            endpoint_ids=self.endpoint_ids,
            source_registry_ref=self.source_registry_ref,
            symbol_map_snapshot_id=self.symbol_map_snapshot_id,
            row_manifest_hash=self.row_manifest_hash,
        )
        if self.availability_manifest_id != expected_id:
            raise ValueError("availability_manifest_id does not match manifest identity")
        return self


class BybitOkxAvailabilityWriteResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    availability_manifest_id: str = Field(min_length=64, max_length=64)
    manifest_ref: str = Field(min_length=1)
    manifest_sha256: str = Field(min_length=64, max_length=64)
    row_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    blocked_mapping_count: int = Field(ge=0)
    blocked_endpoint_limit_count: int = Field(ge=0)
    probe_error_count: int = Field(ge=0)
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
    def _validate_result(self) -> "BybitOkxAvailabilityWriteResult":
        require_research_boundary(self, context="Bybit/OKX availability write result")
        return self


class BybitOkxNormalizedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    endpoint_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    family: str = Field(min_length=1)
    row_index: int = Field(ge=0)
    source_timestamp_ms: int = Field(ge=0)
    source_timestamp: datetime
    numeric_fields: dict[str, str] = Field(default_factory=dict)
    raw_fields: dict[str, str] = Field(default_factory=dict)
    source_request_url: str = Field(min_length=1)
    row_hash: str = Field(min_length=64, max_length=64)
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_row(self) -> "BybitOkxNormalizedRow":
        require_research_boundary(self, context="Bybit/OKX normalized row")
        if self.native_to_hyperliquid:
            raise ValueError("Bybit/OKX normalized rows cannot be Hyperliquid-native")
        if self.accepted_historical_coverage_proof:
            raise ValueError("smoke rows are not accepted historical coverage proof")
        expected_hash = bybit_okx_normalized_row_hash(self)
        if self.row_hash != expected_hash:
            raise ValueError("row_hash does not match normalized row")
        return self


class BybitOkxFetchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    fetch_id: str = Field(min_length=64, max_length=64)
    source_id: str = Field(min_length=1)
    endpoint_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    family: str = Field(min_length=1)
    request_url: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    status: BybitOkxFetchStatus
    http_status_code: int | None = None
    response_payload_hash: str | None = Field(default=None, min_length=64, max_length=64)
    response_row_count: int | None = Field(default=None, ge=0)
    normalized_rows: tuple[BybitOkxNormalizedRow, ...] = ()
    row_count: int = Field(ge=0)
    blocked_reasons: tuple[str, ...] = ()
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
    def _validate_result(self) -> "BybitOkxFetchResult":
        require_research_boundary(self, context="Bybit/OKX fetch result")
        if self.row_count != len(self.normalized_rows):
            raise ValueError("row_count must match normalized_rows length")
        if self.status == BybitOkxFetchStatus.COMPLETED and not self.normalized_rows:
            raise ValueError("completed fetch results require normalized rows")
        if self.status != BybitOkxFetchStatus.COMPLETED and not self.blocked_reasons:
            raise ValueError(f"{self.status.value} fetch results require blocker reasons")
        expected_id = bybit_okx_fetch_id_for(
            source_id=self.source_id,
            endpoint_id=self.endpoint_id,
            request_url=self.request_url,
            status=self.status,
            response_payload_hash=self.response_payload_hash,
            row_hashes=tuple(row.row_hash for row in self.normalized_rows),
            blocked_reasons=self.blocked_reasons,
        )
        if self.fetch_id != expected_id:
            raise ValueError("fetch_id does not match fetch result identity")
        return self


BYBIT_OKX_ENDPOINT_SPECS: dict[str, BybitOkxEndpointSpec] = {
    "bybit_kline": BybitOkxEndpointSpec(
        endpoint_id="bybit_kline",
        source_id=BYBIT_PUBLIC_MARKET_SOURCE_ID,
        venue="bybit",
        venue_key="bybit_linear",
        market_type="perpetual",
        family="candles",
        endpoint_path="/v5/market/kline",
        base_url=BYBIT_PUBLIC_MARKET_BASE_URL,
        interval="1",
        limit=1000,
        rate_limit_hint="Bybit public REST IP and per-endpoint limits apply",
    ),
    "bybit_recent_trades": BybitOkxEndpointSpec(
        endpoint_id="bybit_recent_trades",
        source_id=BYBIT_PUBLIC_MARKET_SOURCE_ID,
        venue="bybit",
        venue_key="bybit_linear",
        market_type="perpetual",
        family="trades",
        endpoint_path="/v5/market/recent-trade",
        base_url=BYBIT_PUBLIC_MARKET_BASE_URL,
        limit=1000,
        rate_limit_hint="Bybit recent trades endpoint is recent-window only",
        supports_date_window=False,
        endpoint_caveats=("recent_window_only",),
    ),
    "bybit_orderbook": BybitOkxEndpointSpec(
        endpoint_id="bybit_orderbook",
        source_id=BYBIT_PUBLIC_MARKET_SOURCE_ID,
        venue="bybit",
        venue_key="bybit_linear",
        market_type="perpetual",
        family="l2_order_book",
        endpoint_path="/v5/market/orderbook",
        base_url=BYBIT_PUBLIC_MARKET_BASE_URL,
        limit=50,
        rate_limit_hint="Bybit orderbook endpoint is snapshot/recent only",
        supports_date_window=False,
        endpoint_caveats=("snapshot_not_historical",),
    ),
    "bybit_funding_history": BybitOkxEndpointSpec(
        endpoint_id="bybit_funding_history",
        source_id=BYBIT_PUBLIC_MARKET_SOURCE_ID,
        venue="bybit",
        venue_key="bybit_linear",
        market_type="perpetual",
        family="funding",
        endpoint_path="/v5/market/funding/history",
        base_url=BYBIT_PUBLIC_MARKET_BASE_URL,
        limit=200,
        rate_limit_hint="Bybit public REST IP and per-endpoint limits apply",
    ),
    "bybit_open_interest": BybitOkxEndpointSpec(
        endpoint_id="bybit_open_interest",
        source_id=BYBIT_PUBLIC_MARKET_SOURCE_ID,
        venue="bybit",
        venue_key="bybit_linear",
        market_type="perpetual",
        family="open_interest",
        endpoint_path="/v5/market/open-interest",
        base_url=BYBIT_PUBLIC_MARKET_BASE_URL,
        interval="5min",
        limit=200,
        rate_limit_hint="Bybit public REST IP and per-endpoint limits apply",
    ),
    "okx_history_candles": BybitOkxEndpointSpec(
        endpoint_id="okx_history_candles",
        source_id=OKX_PUBLIC_MARKET_SOURCE_ID,
        venue="okx",
        venue_key="okx_swap",
        market_type="perpetual",
        family="candles",
        endpoint_path="/api/v5/market/history-candles",
        base_url=OKX_PUBLIC_MARKET_BASE_URL,
        interval="1m",
        limit=100,
        rate_limit_hint="OKX endpoint-specific IP limits apply",
    ),
    "okx_history_trades": BybitOkxEndpointSpec(
        endpoint_id="okx_history_trades",
        source_id=OKX_PUBLIC_MARKET_SOURCE_ID,
        venue="okx",
        venue_key="okx_swap",
        market_type="perpetual",
        family="trades",
        endpoint_path="/api/v5/market/history-trades",
        base_url=OKX_PUBLIC_MARKET_BASE_URL,
        limit=100,
        rate_limit_hint="OKX history trades pagination is endpoint-specific",
        supports_date_window=False,
        endpoint_caveats=("endpoint_specific_cursor_required",),
    ),
    "okx_books": BybitOkxEndpointSpec(
        endpoint_id="okx_books",
        source_id=OKX_PUBLIC_MARKET_SOURCE_ID,
        venue="okx",
        venue_key="okx_swap",
        market_type="perpetual",
        family="l2_order_book",
        endpoint_path="/api/v5/market/books",
        base_url=OKX_PUBLIC_MARKET_BASE_URL,
        limit=50,
        rate_limit_hint="OKX order book endpoint is snapshot/recent only",
        supports_date_window=False,
        endpoint_caveats=("snapshot_not_historical",),
    ),
    "okx_funding_rate_history": BybitOkxEndpointSpec(
        endpoint_id="okx_funding_rate_history",
        source_id=OKX_PUBLIC_MARKET_SOURCE_ID,
        venue="okx",
        venue_key="okx_swap",
        market_type="perpetual",
        family="funding",
        endpoint_path="/api/v5/public/funding-rate-history",
        base_url=OKX_PUBLIC_MARKET_BASE_URL,
        limit=100,
        rate_limit_hint="OKX endpoint-specific IP limits apply",
    ),
    "okx_open_interest": BybitOkxEndpointSpec(
        endpoint_id="okx_open_interest",
        source_id=OKX_PUBLIC_MARKET_SOURCE_ID,
        venue="okx",
        venue_key="okx_swap",
        market_type="perpetual",
        family="open_interest",
        endpoint_path="/api/v5/public/open-interest",
        base_url=OKX_PUBLIC_MARKET_BASE_URL,
        rate_limit_hint="OKX open-interest endpoint is latest snapshot only",
        supports_date_window=False,
        endpoint_caveats=("snapshot_not_historical",),
    ),
}
DEFAULT_BYBIT_OKX_ENDPOINT_IDS = tuple(BYBIT_OKX_ENDPOINT_SPECS)

BybitOkxGetProbe = Callable[[str], BybitOkxGetResult | Mapping[str, Any] | int]


def bybit_okx_endpoint_spec(endpoint_id: str) -> BybitOkxEndpointSpec:
    try:
        return BYBIT_OKX_ENDPOINT_SPECS[endpoint_id]
    except KeyError as exc:
        raise ValueError(f"unsupported Bybit/OKX endpoint_id: {endpoint_id}") from exc


def bybit_okx_endpoint_ids_for_sources(source_ids: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(source_ids)
    return tuple(
        endpoint_id
        for endpoint_id, spec in BYBIT_OKX_ENDPOINT_SPECS.items()
        if spec.source_id in requested
    )


def build_bybit_okx_availability_request(
    *,
    endpoint_id: str,
    symbol: str,
    day: date,
    base_url: str | None = None,
) -> BybitOkxAvailabilityRequest:
    spec = bybit_okx_endpoint_spec(endpoint_id)
    start_ms, end_ms = _day_window_ms(day)
    return _build_bybit_okx_window_request(
        spec=spec,
        symbol=symbol,
        start_ms=start_ms,
        end_ms=end_ms,
        base_url=base_url,
    )


def build_bybit_okx_paginated_request_plan(
    *,
    endpoint_id: str,
    symbol: str,
    day: date,
    max_pages: int,
    base_url: str | None = None,
) -> BybitOkxPaginatedRequestPlan:
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    spec = bybit_okx_endpoint_spec(endpoint_id)
    venue_symbol = _normalize_symbol(symbol, spec.venue)
    if not spec.supports_date_window:
        return BybitOkxPaginatedRequestPlan(
            endpoint_id=spec.endpoint_id,
            source_id=spec.source_id,
            venue=spec.venue,
            venue_symbol=venue_symbol,
            day=day,
            max_pages=max_pages,
            requests=(),
            request_count=0,
            blocked_reasons=("endpoint_does_not_support_date_window",),
        )
    start_ms, end_ms = _day_window_ms(day)
    page_span_ms = _page_span_ms_for_spec(spec)
    requests: list[BybitOkxAvailabilityRequest] = []
    cursor = start_ms
    while cursor < end_ms and len(requests) < max_pages:
        page_end_ms = min(end_ms, cursor + page_span_ms)
        requests.append(
            _build_bybit_okx_window_request(
                spec=spec,
                symbol=venue_symbol,
                start_ms=cursor,
                end_ms=page_end_ms,
                base_url=base_url,
            )
        )
        cursor = page_end_ms
    truncated = cursor < end_ms
    return BybitOkxPaginatedRequestPlan(
        endpoint_id=spec.endpoint_id,
        source_id=spec.source_id,
        venue=spec.venue,
        venue_symbol=venue_symbol,
        day=day,
        page_span_ms=page_span_ms,
        max_pages=max_pages,
        requests=tuple(requests),
        request_count=len(requests),
        truncated=truncated,
        truncation_reasons=("page_cap_exceeded",) if truncated else (),
    )


def fetch_bybit_okx_public_market_pages(
    *,
    plan: BybitOkxPaginatedRequestPlan | Mapping[str, Any],
    source_entry: SourceRegistryEntry | Mapping[str, Any],
    get_probe: BybitOkxGetProbe | None = None,
) -> tuple[BybitOkxFetchResult, ...]:
    parsed_plan = (
        plan
        if isinstance(plan, BybitOkxPaginatedRequestPlan)
        else BybitOkxPaginatedRequestPlan.model_validate(dict(plan))
    )
    if parsed_plan.blocked_reasons:
        return ()
    return tuple(
        fetch_bybit_okx_public_market_request(
            request=request,
            source_entry=source_entry,
            get_probe=get_probe,
        )
        for request in parsed_plan.requests
    )


def _build_bybit_okx_window_request(
    *,
    spec: BybitOkxEndpointSpec,
    symbol: str,
    start_ms: int,
    end_ms: int,
    base_url: str | None = None,
) -> BybitOkxAvailabilityRequest:
    params = _request_params_for_spec(spec=spec, symbol=symbol, start_ms=start_ms, end_ms=end_ms)
    root = (base_url or spec.base_url).rstrip("/")
    query = urlencode(params)
    return BybitOkxAvailabilityRequest(
        endpoint_id=spec.endpoint_id,
        source_id=spec.source_id,
        venue=spec.venue,
        endpoint_path=spec.endpoint_path,
        request_params=params,
        request_url=f"{root}{spec.endpoint_path}?{query}",
        probe_start_ms=start_ms if spec.supports_date_window else None,
        probe_end_ms=end_ms if spec.supports_date_window else None,
        supports_date_window=spec.supports_date_window,
    )


def bybit_okx_availability_rows_hash(
    rows: tuple[BybitOkxAvailabilityRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def bybit_okx_availability_manifest_id_for(
    *,
    start_date: date,
    end_date: date,
    source_ids: tuple[str, ...],
    endpoint_ids: tuple[str, ...],
    source_registry_ref: str,
    symbol_map_snapshot_id: str,
    row_manifest_hash: str,
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "bybit_okx_availability_manifest",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "source_ids": source_ids,
            "endpoint_ids": endpoint_ids,
            "source_registry_ref": source_registry_ref,
            "symbol_map_snapshot_id": symbol_map_snapshot_id,
            "row_manifest_hash": row_manifest_hash,
        }
    )


def bybit_okx_normalized_row_hash(row: BybitOkxNormalizedRow | Mapping[str, Any]) -> str:
    excluded = {
        "row_hash",
        "schema_version",
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
    if isinstance(row, BybitOkxNormalizedRow):
        payload = row.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: value for key, value in dict(row).items() if key not in excluded}
        payload.setdefault("native_to_hyperliquid", False)
        payload.setdefault("accepted_historical_coverage_proof", False)
        if isinstance(payload.get("source_timestamp"), datetime):
            payload["source_timestamp"] = (
                payload["source_timestamp"].isoformat().replace("+00:00", "Z")
            )
    return canonical_json_hash(payload)


def bybit_okx_fetch_id_for(
    *,
    source_id: str,
    endpoint_id: str,
    request_url: str,
    status: BybitOkxFetchStatus,
    response_payload_hash: str | None,
    row_hashes: tuple[str, ...],
    blocked_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "bybit_okx_fetch_result",
            "source_id": source_id,
            "endpoint_id": endpoint_id,
            "request_url": request_url,
            "status": status.value,
            "response_payload_hash": response_payload_hash,
            "row_hashes": row_hashes,
            "blocked_reasons": blocked_reasons,
        }
    )


def write_bybit_okx_availability_manifest(
    *,
    archive_root: str | Path,
    symbol_map_snapshot: SymbolMapSnapshot | Mapping[str, Any],
    source_entries: Iterable[SourceRegistryEntry | Mapping[str, Any]],
    start_date: date,
    end_date: date,
    symbol_map_ref: str | None = None,
    source_ids: Iterable[str] = DEFAULT_BYBIT_OKX_SOURCE_IDS,
    endpoint_ids: Iterable[str] | None = None,
    get_probe: BybitOkxGetProbe | None = None,
) -> BybitOkxAvailabilityWriteResult:
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
    requested_endpoint_ids = (
        tuple(endpoint_ids)
        if endpoint_ids is not None
        else bybit_okx_endpoint_ids_for_sources(requested_source_ids)
    )
    if not requested_endpoint_ids:
        raise ValueError("endpoint_ids cannot be empty")
    entries_by_id = _validated_source_entries(source_entries, requested_source_ids)
    _validate_endpoint_ids(requested_endpoint_ids, requested_source_ids)
    probe = get_probe or default_bybit_okx_get_probe
    resolved_symbol_map_ref = symbol_map_ref or _default_symbol_map_ref(parsed_snapshot)
    rows = _build_availability_rows(
        snapshot=parsed_snapshot,
        symbol_map_ref=resolved_symbol_map_ref,
        entries_by_id=entries_by_id,
        start_date=start_date,
        end_date=end_date,
        endpoint_ids=requested_endpoint_ids,
        get_probe=probe,
    )
    row_hash = bybit_okx_availability_rows_hash(rows)
    manifest_id = bybit_okx_availability_manifest_id_for(
        start_date=start_date,
        end_date=end_date,
        source_ids=requested_source_ids,
        endpoint_ids=requested_endpoint_ids,
        source_registry_ref=parsed_snapshot.source_registry_ref,
        symbol_map_snapshot_id=parsed_snapshot.symbol_map_snapshot_id,
        row_manifest_hash=row_hash,
    )
    manifest = BybitOkxAvailabilityManifest(
        availability_manifest_id=manifest_id,
        start_date=start_date,
        end_date=end_date,
        source_ids=requested_source_ids,
        endpoint_ids=requested_endpoint_ids,
        source_registry_ref=parsed_snapshot.source_registry_ref,
        symbol_map_ref=resolved_symbol_map_ref,
        symbol_map_snapshot_id=parsed_snapshot.symbol_map_snapshot_id,
        rows=rows,
        row_count=len(rows),
        available_count=_count_status(rows, BybitOkxAvailabilityStatus.AVAILABLE),
        missing_count=_count_status(rows, BybitOkxAvailabilityStatus.MISSING),
        blocked_mapping_count=_count_status(rows, BybitOkxAvailabilityStatus.BLOCKED_MAPPING),
        blocked_endpoint_limit_count=_count_status(
            rows,
            BybitOkxAvailabilityStatus.BLOCKED_ENDPOINT_LIMIT,
        ),
        probe_error_count=_count_status(rows, BybitOkxAvailabilityStatus.PROBE_ERROR),
        row_manifest_hash=row_hash,
    )
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_path = layout.resolve(
        "manifests",
        "source_availability",
        f"bybit_okx_availability_{start_date.isoformat()}_{end_date.isoformat()}_{manifest_id[:16]}.json",
    )
    _write_json_model(manifest_path, manifest)
    return BybitOkxAvailabilityWriteResult(
        availability_manifest_id=manifest_id,
        manifest_ref=layout.relative_to_root(manifest_path),
        manifest_sha256=file_sha256(manifest_path),
        row_count=manifest.row_count,
        available_count=manifest.available_count,
        missing_count=manifest.missing_count,
        blocked_mapping_count=manifest.blocked_mapping_count,
        blocked_endpoint_limit_count=manifest.blocked_endpoint_limit_count,
        probe_error_count=manifest.probe_error_count,
    )


def fetch_bybit_okx_public_market_request(
    *,
    request: BybitOkxAvailabilityRequest | Mapping[str, Any],
    source_entry: SourceRegistryEntry | Mapping[str, Any],
    get_probe: BybitOkxGetProbe | None = None,
) -> BybitOkxFetchResult:
    parsed_request = (
        request
        if isinstance(request, BybitOkxAvailabilityRequest)
        else BybitOkxAvailabilityRequest.model_validate(dict(request))
    )
    spec = bybit_okx_endpoint_spec(parsed_request.endpoint_id)
    entry = (
        source_entry
        if isinstance(source_entry, SourceRegistryEntry)
        else SourceRegistryEntry.model_validate(dict(source_entry))
    )
    _validated_source_entries((entry,), (spec.source_id,))
    _validate_entry_supports_spec(entry, spec)
    venue_symbol = _venue_symbol_from_request(parsed_request, spec)
    if not spec.supports_date_window:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=BybitOkxFetchStatus.BLOCKED,
            blocked_reasons=("endpoint_does_not_support_date_window",),
        )
    probe = get_probe or default_bybit_okx_get_probe
    probe_result = _coerce_get_result(probe(parsed_request.request_url))
    response_payload_hash = _payload_hash(probe_result.payload)
    availability_status = _availability_status(spec=spec, result=probe_result)
    response_row_count = _response_row_count(spec=spec, result=probe_result)
    if availability_status == BybitOkxAvailabilityStatus.MISSING:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=BybitOkxFetchStatus.EMPTY,
            http_status_code=probe_result.status_code,
            response_payload_hash=response_payload_hash,
            response_row_count=response_row_count,
            blocked_reasons=("empty_response",),
        )
    if availability_status == BybitOkxAvailabilityStatus.PROBE_ERROR:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=BybitOkxFetchStatus.FETCH_ERROR,
            http_status_code=probe_result.status_code,
            response_payload_hash=response_payload_hash,
            response_row_count=response_row_count,
            blocked_reasons=_blocked_reasons_for_probe(
                spec=spec,
                result=probe_result,
                status=availability_status,
            ),
        )
    try:
        rows = _normalize_payload(spec=spec, request=parsed_request, result=probe_result)
    except ValueError as exc:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=BybitOkxFetchStatus.PARSE_ERROR,
            http_status_code=probe_result.status_code,
            response_payload_hash=response_payload_hash,
            response_row_count=response_row_count,
            blocked_reasons=(str(exc),),
        )
    if not rows:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=BybitOkxFetchStatus.EMPTY,
            http_status_code=probe_result.status_code,
            response_payload_hash=response_payload_hash,
            response_row_count=response_row_count,
            blocked_reasons=("empty_normalized_rows",),
        )
    return _fetch_result(
        spec=spec,
        request=parsed_request,
        venue_symbol=venue_symbol,
        status=BybitOkxFetchStatus.COMPLETED,
        http_status_code=probe_result.status_code,
        response_payload_hash=response_payload_hash,
        response_row_count=response_row_count,
        rows=rows,
    )


def default_bybit_okx_get_probe(url: str) -> BybitOkxGetResult:
    try:
        response = httpx.get(url, follow_redirects=True, timeout=20.0)
    except httpx.HTTPError as exc:
        return BybitOkxGetResult(error=str(exc))
    payload: Any
    try:
        payload = response.json()
    except ValueError:
        payload = None
    return BybitOkxGetResult(
        status_code=response.status_code,
        headers={str(key): str(value) for key, value in response.headers.items()},
        payload=payload,
    )


def _fetch_result(
    *,
    spec: BybitOkxEndpointSpec,
    request: BybitOkxAvailabilityRequest,
    venue_symbol: str,
    status: BybitOkxFetchStatus,
    http_status_code: int | None = None,
    response_payload_hash: str | None = None,
    response_row_count: int | None = None,
    rows: tuple[BybitOkxNormalizedRow, ...] = (),
    blocked_reasons: tuple[str, ...] = (),
) -> BybitOkxFetchResult:
    fetch_id = bybit_okx_fetch_id_for(
        source_id=spec.source_id,
        endpoint_id=spec.endpoint_id,
        request_url=request.request_url,
        status=status,
        response_payload_hash=response_payload_hash,
        row_hashes=tuple(row.row_hash for row in rows),
        blocked_reasons=blocked_reasons,
    )
    return BybitOkxFetchResult(
        fetch_id=fetch_id,
        source_id=spec.source_id,
        endpoint_id=spec.endpoint_id,
        venue=spec.venue,
        venue_symbol=venue_symbol,
        family=spec.family,
        request_url=request.request_url,
        endpoint_path=spec.endpoint_path,
        status=status,
        http_status_code=http_status_code,
        response_payload_hash=response_payload_hash,
        response_row_count=response_row_count,
        normalized_rows=rows,
        row_count=len(rows),
        blocked_reasons=blocked_reasons,
    )


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
        raise ValueError("missing Bybit/OKX source entries: " + ",".join(missing))
    for source_id in source_ids:
        entry = entries[source_id]
        if source_id not in DEFAULT_BYBIT_OKX_SOURCE_IDS:
            raise ValueError(f"unsupported Bybit/OKX source_id: {source_id}")
        require_strict_zero_dollar_source(entry)
        if not entry.accepted_under_strict_free:
            raise ValueError(f"{source_id} is not accepted under strict-free mode")
        if entry.native_to_hyperliquid:
            raise ValueError(f"{source_id} must not be Hyperliquid-native")
        if entry.accepted_historical_coverage_proof:
            raise ValueError(f"{source_id} cannot be accepted historical coverage proof")
        expected_venue = "bybit" if source_id == BYBIT_PUBLIC_MARKET_SOURCE_ID else "okx"
        if entry.venue != expected_venue:
            raise ValueError(f"{source_id} venue must be {expected_venue}")
        if entry.research_role != "external_comparison":
            raise ValueError(f"{source_id} must remain external_comparison")
    return entries


def _validate_endpoint_ids(endpoint_ids: tuple[str, ...], source_ids: tuple[str, ...]) -> None:
    for endpoint_id in endpoint_ids:
        spec = bybit_okx_endpoint_spec(endpoint_id)
        if spec.source_id not in source_ids:
            raise ValueError(f"{endpoint_id} belongs to unrequested source {spec.source_id}")


def _build_availability_rows(
    *,
    snapshot: SymbolMapSnapshot,
    symbol_map_ref: str,
    entries_by_id: Mapping[str, SourceRegistryEntry],
    start_date: date,
    end_date: date,
    endpoint_ids: tuple[str, ...],
    get_probe: BybitOkxGetProbe,
) -> tuple[BybitOkxAvailabilityRow, ...]:
    rows: list[BybitOkxAvailabilityRow] = []
    liquid_rows = [
        row
        for row in snapshot.symbol_map_rows
        if row.hyperliquid_liquid_as_of and row.above_day_notional_threshold
    ]
    for symbol_row in sorted(liquid_rows, key=lambda item: item.hyperliquid_coin):
        for endpoint_id in endpoint_ids:
            spec = bybit_okx_endpoint_spec(endpoint_id)
            entry = entries_by_id[spec.source_id]
            _validate_entry_supports_spec(entry, spec)
            try:
                mapping_ref = require_verified_external_mapping(symbol_row, spec.venue_key)
                venue_symbol = mapping_ref.symbol
            except ValueError as exc:
                rows.extend(
                    _blocked_rows(
                        snapshot=snapshot,
                        symbol_map_ref=symbol_map_ref,
                        source_entry=entry,
                        spec=spec,
                        hyperliquid_coin=symbol_row.hyperliquid_coin,
                        start_date=start_date,
                        end_date=end_date,
                        status=BybitOkxAvailabilityStatus.BLOCKED_MAPPING,
                        reason=str(exc),
                    )
                )
                continue
            for day in _date_range(start_date, end_date):
                request = build_bybit_okx_availability_request(
                    endpoint_id=endpoint_id,
                    symbol=venue_symbol,
                    day=day,
                )
                if not spec.supports_date_window:
                    rows.append(
                        _row_from_request(
                            snapshot=snapshot,
                            symbol_map_ref=symbol_map_ref,
                            source_entry=entry,
                            spec=spec,
                            hyperliquid_coin=symbol_row.hyperliquid_coin,
                            venue_symbol=venue_symbol,
                            day=day,
                            request=request,
                            status=BybitOkxAvailabilityStatus.BLOCKED_ENDPOINT_LIMIT,
                            blocked_reasons=("endpoint_does_not_support_date_window",),
                        )
                    )
                    continue
                probe_result = _coerce_get_result(get_probe(request.request_url))
                status = _availability_status(spec=spec, result=probe_result)
                rows.append(
                    _row_from_request(
                        snapshot=snapshot,
                        symbol_map_ref=symbol_map_ref,
                        source_entry=entry,
                        spec=spec,
                        hyperliquid_coin=symbol_row.hyperliquid_coin,
                        venue_symbol=venue_symbol,
                        day=day,
                        request=request,
                        status=status,
                        http_status_code=probe_result.status_code,
                        response_row_count=_response_row_count(spec=spec, result=probe_result),
                        blocked_reasons=_blocked_reasons_for_probe(
                            spec=spec,
                            result=probe_result,
                            status=status,
                        ),
                        probe_error=probe_result.error,
                    )
                )
    return tuple(rows)


def _validate_entry_supports_spec(entry: SourceRegistryEntry, spec: BybitOkxEndpointSpec) -> None:
    if spec.family not in entry.data_families:
        raise ValueError(f"{entry.source_id} is missing data family {spec.family}")
    if entry.venue != spec.venue:
        raise ValueError(f"{entry.source_id} venue does not match endpoint spec")
    if entry.market_type != spec.market_type:
        raise ValueError(f"{entry.source_id} market_type does not match endpoint spec")


def _normalize_payload(
    *,
    spec: BybitOkxEndpointSpec,
    request: BybitOkxAvailabilityRequest,
    result: BybitOkxGetResult,
) -> tuple[BybitOkxNormalizedRow, ...]:
    raw_rows = _raw_rows(spec=spec, result=result)
    rows: list[BybitOkxNormalizedRow] = []
    for index, raw_row in enumerate(raw_rows):
        rows.append(
            _normalize_raw_row(
                spec=spec,
                request=request,
                raw_row=raw_row,
                row_index=index,
            )
        )
    return tuple(rows)


def _raw_rows(*, spec: BybitOkxEndpointSpec, result: BybitOkxGetResult) -> list[Any]:
    payload = result.payload
    if spec.venue == "bybit":
        if not isinstance(payload, Mapping):
            raise ValueError("Bybit payload must be an object")
        result_payload = payload.get("result")
        if not isinstance(result_payload, Mapping):
            raise ValueError("Bybit payload is missing result object")
        rows = result_payload.get("list")
        if not isinstance(rows, list):
            raise ValueError("Bybit payload is missing result.list")
        return rows
    if not isinstance(payload, Mapping):
        raise ValueError("OKX payload must be an object")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("OKX payload is missing data list")
    return rows


def _normalize_raw_row(
    *,
    spec: BybitOkxEndpointSpec,
    request: BybitOkxAvailabilityRequest,
    raw_row: Any,
    row_index: int,
) -> BybitOkxNormalizedRow:
    if spec.endpoint_id in {"bybit_kline", "okx_history_candles"}:
        return _normalize_candle_row(spec=spec, request=request, raw_row=raw_row, row_index=row_index)
    if spec.endpoint_id in {"bybit_funding_history", "okx_funding_rate_history"}:
        return _normalize_funding_row(spec=spec, request=request, raw_row=raw_row, row_index=row_index)
    if spec.endpoint_id == "bybit_open_interest":
        return _normalize_open_interest_row(spec=spec, request=request, raw_row=raw_row, row_index=row_index)
    raise ValueError(f"{spec.endpoint_id} is not supported for date-window smoke normalization")


def _normalize_candle_row(
    *,
    spec: BybitOkxEndpointSpec,
    request: BybitOkxAvailabilityRequest,
    raw_row: Any,
    row_index: int,
) -> BybitOkxNormalizedRow:
    if not isinstance(raw_row, list) or len(raw_row) < 6:
        raise ValueError(f"{spec.endpoint_id} candle row is malformed")
    field_names = (
        ("start_time_ms", "open", "high", "low", "close", "volume", "turnover")
        if spec.venue == "bybit"
        else (
            "start_time_ms",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "volume_currency",
            "volume_quote",
            "confirm",
        )
    )
    raw_fields = _raw_fields_from_sequence(field_names, raw_row)
    timestamp_ms = _parse_timestamp_ms(raw_fields["start_time_ms"])
    numeric_keys = (
        ("open", "high", "low", "close", "volume", "turnover")
        if spec.venue == "bybit"
        else ("open", "high", "low", "close", "volume", "volume_currency", "volume_quote")
    )
    return _normalized_row(
        spec=spec,
        request=request,
        row_index=row_index,
        timestamp_ms=timestamp_ms,
        numeric_fields={key: raw_fields[key] for key in numeric_keys if key in raw_fields},
        raw_fields=raw_fields,
    )


def _normalize_funding_row(
    *,
    spec: BybitOkxEndpointSpec,
    request: BybitOkxAvailabilityRequest,
    raw_row: Any,
    row_index: int,
) -> BybitOkxNormalizedRow:
    if not isinstance(raw_row, Mapping):
        raise ValueError(f"{spec.endpoint_id} funding row is malformed")
    raw_fields = _raw_fields_from_mapping(raw_row)
    timestamp_key = "fundingRateTimestamp" if spec.venue == "bybit" else "fundingTime"
    if timestamp_key not in raw_fields:
        raise ValueError(f"{spec.endpoint_id} funding row is missing {timestamp_key}")
    timestamp_ms = _parse_timestamp_ms(raw_fields[timestamp_key])
    numeric_fields = {
        key: value
        for key, value in raw_fields.items()
        if key in {"fundingRate", "realizedRate", "nextFundingRate"}
    }
    return _normalized_row(
        spec=spec,
        request=request,
        row_index=row_index,
        timestamp_ms=timestamp_ms,
        numeric_fields=numeric_fields,
        raw_fields=raw_fields,
    )


def _normalize_open_interest_row(
    *,
    spec: BybitOkxEndpointSpec,
    request: BybitOkxAvailabilityRequest,
    raw_row: Any,
    row_index: int,
) -> BybitOkxNormalizedRow:
    if not isinstance(raw_row, Mapping):
        raise ValueError(f"{spec.endpoint_id} open-interest row is malformed")
    raw_fields = _raw_fields_from_mapping(raw_row)
    if "timestamp" not in raw_fields:
        raise ValueError(f"{spec.endpoint_id} open-interest row is missing timestamp")
    timestamp_ms = _parse_timestamp_ms(raw_fields["timestamp"])
    numeric_fields = {
        key: value
        for key, value in raw_fields.items()
        if key in {"openInterest", "openInterestValue"}
    }
    return _normalized_row(
        spec=spec,
        request=request,
        row_index=row_index,
        timestamp_ms=timestamp_ms,
        numeric_fields=numeric_fields,
        raw_fields=raw_fields,
    )


def _normalized_row(
    *,
    spec: BybitOkxEndpointSpec,
    request: BybitOkxAvailabilityRequest,
    row_index: int,
    timestamp_ms: int,
    numeric_fields: dict[str, str],
    raw_fields: dict[str, str],
) -> BybitOkxNormalizedRow:
    payload = {
        "source_id": spec.source_id,
        "endpoint_id": spec.endpoint_id,
        "venue": spec.venue,
        "venue_symbol": _venue_symbol_from_request(request, spec),
        "family": spec.family,
        "row_index": row_index,
        "source_timestamp_ms": timestamp_ms,
        "source_timestamp": datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
        "numeric_fields": numeric_fields,
        "raw_fields": raw_fields,
        "source_request_url": request.request_url,
    }
    return BybitOkxNormalizedRow(
        **payload,
        row_hash=bybit_okx_normalized_row_hash(payload),
    )


def _blocked_rows(
    *,
    snapshot: SymbolMapSnapshot,
    symbol_map_ref: str,
    source_entry: SourceRegistryEntry,
    spec: BybitOkxEndpointSpec,
    hyperliquid_coin: str,
    start_date: date,
    end_date: date,
    status: BybitOkxAvailabilityStatus,
    reason: str,
) -> list[BybitOkxAvailabilityRow]:
    return [
        BybitOkxAvailabilityRow(
            source_id=spec.source_id,
            endpoint_id=spec.endpoint_id,
            source_registry_ref=snapshot.source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            symbol_map_snapshot_id=snapshot.symbol_map_snapshot_id,
            hyperliquid_coin=hyperliquid_coin,
            venue=spec.venue,
            venue_key=spec.venue_key,
            probe_date=day,
            market_type=spec.market_type,
            family=spec.family,
            interval=spec.interval,
            endpoint_path=spec.endpoint_path,
            request_limit=spec.limit,
            rate_limit_hint=spec.rate_limit_hint,
            supports_date_window=spec.supports_date_window,
            availability_status=status,
            source_cost_class=source_entry.cost_class,
            blocked_reasons=(reason,),
            endpoint_caveats=spec.endpoint_caveats,
        )
        for day in _date_range(start_date, end_date)
    ]


def _row_from_request(
    *,
    snapshot: SymbolMapSnapshot,
    symbol_map_ref: str,
    source_entry: SourceRegistryEntry,
    spec: BybitOkxEndpointSpec,
    hyperliquid_coin: str,
    venue_symbol: str,
    day: date,
    request: BybitOkxAvailabilityRequest,
    status: BybitOkxAvailabilityStatus,
    http_status_code: int | None = None,
    response_row_count: int | None = None,
    blocked_reasons: tuple[str, ...] = (),
    probe_error: str | None = None,
) -> BybitOkxAvailabilityRow:
    return BybitOkxAvailabilityRow(
        source_id=spec.source_id,
        endpoint_id=spec.endpoint_id,
        source_registry_ref=snapshot.source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        symbol_map_snapshot_id=snapshot.symbol_map_snapshot_id,
        hyperliquid_coin=hyperliquid_coin,
        venue=spec.venue,
        venue_key=spec.venue_key,
        venue_symbol=venue_symbol,
        probe_date=day,
        market_type=spec.market_type,
        family=spec.family,
        interval=spec.interval,
        endpoint_path=spec.endpoint_path,
        request_url=request.request_url,
        request_params=request.request_params,
        probe_start_ms=request.probe_start_ms,
        probe_end_ms=request.probe_end_ms,
        request_limit=spec.limit,
        rate_limit_hint=spec.rate_limit_hint,
        supports_date_window=spec.supports_date_window,
        availability_status=status,
        http_status_code=http_status_code,
        response_row_count=response_row_count,
        source_cost_class=source_entry.cost_class,
        blocked_reasons=blocked_reasons,
        probe_error=probe_error,
        endpoint_caveats=spec.endpoint_caveats,
    )


def _page_span_ms_for_spec(spec: BybitOkxEndpointSpec) -> int:
    day_ms = 24 * 60 * 60 * 1000
    limit = spec.limit or 1
    if spec.endpoint_id in {"bybit_kline", "okx_history_candles"}:
        return min(day_ms, limit * _interval_ms(str(spec.interval)))
    if spec.endpoint_id == "bybit_open_interest":
        return min(day_ms, limit * _interval_ms(str(spec.interval)))
    if spec.endpoint_id in {"bybit_funding_history", "okx_funding_rate_history"}:
        return day_ms
    return day_ms


def _interval_ms(interval: str) -> int:
    normalized = interval.strip().lower()
    if not normalized:
        raise ValueError("interval cannot be empty")
    if normalized.isdigit():
        return int(normalized) * 60 * 1000
    for suffix, multiplier in (
        ("min", 60 * 1000),
        ("m", 60 * 1000),
        ("h", 60 * 60 * 1000),
        ("d", 24 * 60 * 60 * 1000),
    ):
        if normalized.endswith(suffix):
            amount = normalized[: -len(suffix)]
            if amount.isdigit():
                return int(amount) * multiplier
    raise ValueError(f"unsupported interval for pagination: {interval!r}")


def _request_params_for_spec(
    *,
    spec: BybitOkxEndpointSpec,
    symbol: str,
    start_ms: int,
    end_ms: int,
) -> dict[str, str]:
    normalized_symbol = _normalize_symbol(symbol, spec.venue)
    if spec.venue == "bybit":
        params: dict[str, str] = {
            "category": "linear",
            "symbol": normalized_symbol,
        }
        if spec.endpoint_id == "bybit_kline":
            params.update(
                {
                    "interval": str(spec.interval),
                    "start": str(start_ms),
                    "end": str(end_ms),
                    "limit": str(spec.limit),
                }
            )
        elif spec.endpoint_id == "bybit_recent_trades":
            params["limit"] = str(spec.limit)
        elif spec.endpoint_id == "bybit_orderbook":
            params["limit"] = str(spec.limit)
        elif spec.endpoint_id == "bybit_funding_history":
            params.update(
                {
                    "startTime": str(start_ms),
                    "endTime": str(end_ms),
                    "limit": str(spec.limit),
                }
            )
        elif spec.endpoint_id == "bybit_open_interest":
            params.update(
                {
                    "intervalTime": str(spec.interval),
                    "startTime": str(start_ms),
                    "endTime": str(end_ms),
                    "limit": str(spec.limit),
                }
            )
        return params
    params = {"instId": normalized_symbol}
    if spec.endpoint_id == "okx_history_candles":
        params.update(
            {
                "bar": str(spec.interval),
                "after": str(start_ms),
                "before": str(end_ms),
                "limit": str(spec.limit),
            }
        )
    elif spec.endpoint_id == "okx_history_trades":
        params["limit"] = str(spec.limit)
    elif spec.endpoint_id == "okx_books":
        params["sz"] = str(spec.limit)
    elif spec.endpoint_id == "okx_funding_rate_history":
        params.update(
            {
                "after": str(start_ms),
                "before": str(end_ms),
                "limit": str(spec.limit),
            }
        )
    elif spec.endpoint_id == "okx_open_interest":
        params["instType"] = "SWAP"
    return params


def _availability_status(
    *,
    spec: BybitOkxEndpointSpec,
    result: BybitOkxGetResult,
) -> BybitOkxAvailabilityStatus:
    if result.error:
        return BybitOkxAvailabilityStatus.PROBE_ERROR
    if result.status_code == 404:
        return BybitOkxAvailabilityStatus.MISSING
    if result.status_code != 200:
        return BybitOkxAvailabilityStatus.PROBE_ERROR
    api_error = _api_error(spec=spec, result=result)
    if api_error:
        return BybitOkxAvailabilityStatus.PROBE_ERROR
    row_count = _response_row_count(spec=spec, result=result)
    if row_count and row_count > 0:
        return BybitOkxAvailabilityStatus.AVAILABLE
    return BybitOkxAvailabilityStatus.MISSING


def _blocked_reasons_for_probe(
    *,
    spec: BybitOkxEndpointSpec,
    result: BybitOkxGetResult,
    status: BybitOkxAvailabilityStatus,
) -> tuple[str, ...]:
    if status == BybitOkxAvailabilityStatus.AVAILABLE:
        return ()
    if result.error:
        return (f"probe_error:{result.error}",)
    api_error = _api_error(spec=spec, result=result)
    if api_error:
        return (api_error,)
    if result.status_code not in {200, 404}:
        return (f"unexpected_http_status:{result.status_code}",)
    return ()


def _api_error(*, spec: BybitOkxEndpointSpec, result: BybitOkxGetResult) -> str | None:
    payload = result.payload
    if not isinstance(payload, Mapping):
        return None
    if spec.venue == "bybit":
        ret_code = payload.get("retCode")
        if ret_code not in {None, 0, "0"}:
            return f"bybit_ret_code:{ret_code}"
    if spec.venue == "okx":
        code = payload.get("code")
        if code not in {None, "0", 0}:
            return f"okx_code:{code}"
    return None


def _response_row_count(*, spec: BybitOkxEndpointSpec, result: BybitOkxGetResult) -> int | None:
    payload = result.payload
    if spec.venue == "bybit":
        if isinstance(payload, Mapping):
            result_payload = payload.get("result")
            if isinstance(result_payload, Mapping):
                rows = result_payload.get("list")
                if isinstance(rows, list):
                    return len(rows)
        return None
    if isinstance(payload, Mapping):
        rows = payload.get("data")
        if isinstance(rows, list):
            return len(rows)
    return None


def _coerce_get_result(value: BybitOkxGetResult | Mapping[str, Any] | int) -> BybitOkxGetResult:
    if isinstance(value, BybitOkxGetResult):
        return value
    if isinstance(value, int):
        return BybitOkxGetResult(status_code=value)
    return BybitOkxGetResult.model_validate(dict(value))


def _date_range(start_date: date, end_date: date) -> tuple[date, ...]:
    days: list[date] = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return tuple(days)


def _day_window_ms(day: date) -> tuple[int, int]:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _normalize_symbol(symbol: str, venue: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError(f"unsupported {venue} symbol: {symbol!r}")
    if venue == "okx":
        if any(part == "" for part in normalized.split("-")):
            raise ValueError(f"unsupported OKX symbol: {symbol!r}")
        return normalized
    if not normalized.replace("_", "").isalnum():
        raise ValueError(f"unsupported Bybit symbol: {symbol!r}")
    return normalized


def _venue_symbol_from_request(
    request: BybitOkxAvailabilityRequest,
    spec: BybitOkxEndpointSpec,
) -> str:
    key = "symbol" if spec.venue == "bybit" else "instId"
    value = request.request_params.get(key)
    if value is None:
        raise ValueError(f"{spec.endpoint_id} request is missing {key}")
    return value


def _payload_hash(payload: Any) -> str | None:
    if payload is None:
        return None
    return canonical_json_hash(payload)


def _raw_fields_from_sequence(field_names: tuple[str, ...], values: list[Any]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for index, field_name in enumerate(field_names):
        if index >= len(values):
            break
        fields[field_name] = str(values[index])
    return fields


def _raw_fields_from_mapping(row: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in sorted(row.items())
        if value is not None
    }


def _parse_timestamp_ms(value: str) -> int:
    try:
        timestamp_ms = int(str(value))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp_ms: {value!r}") from exc
    if timestamp_ms < 0:
        raise ValueError(f"invalid timestamp_ms: {value!r}")
    return timestamp_ms


def _default_symbol_map_ref(snapshot: SymbolMapSnapshot) -> str:
    return f"manifests/symbol_maps/{snapshot.symbol_map_snapshot_id}.json"


def _count_status(
    rows: tuple[BybitOkxAvailabilityRow, ...],
    status: BybitOkxAvailabilityStatus,
) -> int:
    return sum(1 for row in rows if row.availability_status == status)


def _write_json_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
