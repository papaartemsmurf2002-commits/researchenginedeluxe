# V2-AUDIT-ID: V2-AUD-DATASRC-034
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, strict_free_public_context, no_downloads
# V2-OWNER: v2_data_sources
"""Spot, oracle, and on-chain context availability matrix."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlencode

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

SPOT_ORACLE_CONTEXT_SOURCE_IDS = (
    "coinbase_spot_public",
    "kraken_spot_public",
    "pyth_hermes_public",
    "defillama_public",
    "dexscreener_public",
    "geckoterminal_public",
)


class SpotOracleContextAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    BLOCKED_MAPPING = "blocked_mapping"
    PROBE_ERROR = "probe_error"


class SpotOracleContextFetchStatus(str, Enum):
    COMPLETED = "completed"
    EMPTY = "empty"
    FETCH_ERROR = "fetch_error"
    PARSE_ERROR = "parse_error"


class SpotOracleContextEndpointSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_key: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    family: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    interval: str = Field(min_length=1)
    limit: int | None = Field(default=None, ge=1)
    timestamp_mode: str = Field(pattern=r"^(iso|s|none)$")
    rate_limit_hint: str = Field(min_length=1)


class SpotOracleContextGetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    payload: Any = None
    error: str | None = None


class SpotOracleContextAvailabilityRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    request_params: dict[str, str] = Field(default_factory=dict)
    request_url: str = Field(min_length=1)
    probe_start_ms: int = Field(ge=0)
    probe_end_ms: int = Field(ge=0)
    timestamp_mode: str = Field(pattern=r"^(iso|s|none)$")

    @model_validator(mode="after")
    def _validate_request(self) -> "SpotOracleContextAvailabilityRequest":
        if self.probe_end_ms <= self.probe_start_ms:
            raise ValueError("probe_end_ms must be greater than probe_start_ms")
        return self


class SpotOracleContextAvailabilityRow(BaseModel):
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
    interval: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    request_url: str | None = None
    request_params: dict[str, str] = Field(default_factory=dict)
    probe_start_ms: int | None = Field(default=None, ge=0)
    probe_end_ms: int | None = Field(default=None, ge=0)
    timestamp_mode: str = Field(pattern=r"^(iso|s|none)$")
    request_limit: int | None = Field(default=None, ge=1)
    rate_limit_hint: str = Field(min_length=1)
    availability_status: SpotOracleContextAvailabilityStatus
    http_status_code: int | None = None
    response_row_count: int | None = Field(default=None, ge=0)
    source_cost_class: CostClass
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_row(self) -> "SpotOracleContextAvailabilityRow":
        require_research_boundary(self, context="spot-oracle-context availability row")
        if self.native_to_hyperliquid:
            raise ValueError("spot-oracle-context rows cannot be Hyperliquid-native")
        if self.accepted_historical_coverage_proof:
            raise ValueError("availability rows are not historical coverage proof")
        if self.availability_status == SpotOracleContextAvailabilityStatus.AVAILABLE:
            if not self.request_url:
                raise ValueError("available rows require request_url")
            if not self.response_row_count:
                raise ValueError("available rows require positive response_row_count")
        if self.availability_status in {
            SpotOracleContextAvailabilityStatus.BLOCKED_MAPPING,
            SpotOracleContextAvailabilityStatus.PROBE_ERROR,
        } and not self.blocked_reasons:
            raise ValueError(f"{self.availability_status.value} rows require blocker reasons")
        return self


class SpotOracleContextAvailabilityManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "spot_oracle_context_availability_manifest"
    availability_manifest_id: str = Field(min_length=64, max_length=64)
    start_date: date
    end_date: date
    source_ids: tuple[str, ...] = Field(min_length=1)
    endpoint_ids: tuple[str, ...] = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    strict_zero_dollar_mode: bool = True
    rows: tuple[SpotOracleContextAvailabilityRow, ...]
    row_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    blocked_mapping_count: int = Field(ge=0)
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
    def _validate_manifest(self) -> "SpotOracleContextAvailabilityManifest":
        require_research_boundary(self, context="spot-oracle-context availability manifest")
        if self.manifest_type != "spot_oracle_context_availability_manifest":
            raise ValueError("manifest_type must be spot_oracle_context_availability_manifest")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.available_count != _count_status(
            self.rows,
            SpotOracleContextAvailabilityStatus.AVAILABLE,
        ):
            raise ValueError("available_count does not match rows")
        if self.missing_count != _count_status(
            self.rows,
            SpotOracleContextAvailabilityStatus.MISSING,
        ):
            raise ValueError("missing_count does not match rows")
        if self.blocked_mapping_count != _count_status(
            self.rows,
            SpotOracleContextAvailabilityStatus.BLOCKED_MAPPING,
        ):
            raise ValueError("blocked_mapping_count does not match rows")
        if self.probe_error_count != _count_status(
            self.rows,
            SpotOracleContextAvailabilityStatus.PROBE_ERROR,
        ):
            raise ValueError("probe_error_count does not match rows")
        expected_hash = spot_oracle_context_availability_rows_hash(self.rows)
        if self.row_manifest_hash != expected_hash:
            raise ValueError("row_manifest_hash does not match availability rows")
        expected_id = spot_oracle_context_availability_manifest_id_for(
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


class SpotOracleContextAvailabilityWriteResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    availability_manifest_id: str = Field(min_length=64, max_length=64)
    manifest_ref: str = Field(min_length=1)
    manifest_sha256: str = Field(min_length=64, max_length=64)
    row_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    blocked_mapping_count: int = Field(ge=0)
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
    def _validate_write_result(self) -> "SpotOracleContextAvailabilityWriteResult":
        require_research_boundary(self, context="spot-oracle-context availability write result")
        return self


class SpotOracleContextNormalizedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    endpoint_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    family: str = Field(min_length=1)
    row_index: int = Field(ge=0)
    source_timestamp_ms: int | None = Field(default=None, ge=0)
    source_timestamp: datetime | None = None
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
    def _validate_row(self) -> "SpotOracleContextNormalizedRow":
        require_research_boundary(self, context="spot-oracle-context normalized row")
        if self.native_to_hyperliquid:
            raise ValueError("spot-oracle-context normalized rows cannot be Hyperliquid-native")
        if self.accepted_historical_coverage_proof:
            raise ValueError("smoke rows are not accepted historical coverage proof")
        if (self.source_timestamp_ms is None) != (self.source_timestamp is None):
            raise ValueError("source_timestamp_ms and source_timestamp must both be present or absent")
        if self.row_hash != spot_oracle_context_normalized_row_hash(self):
            raise ValueError("row_hash does not match normalized row")
        return self


class SpotOracleContextFetchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    fetch_id: str = Field(min_length=64, max_length=64)
    source_id: str = Field(min_length=1)
    endpoint_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    family: str = Field(min_length=1)
    request_url: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    status: SpotOracleContextFetchStatus
    http_status_code: int | None = None
    response_payload_hash: str | None = Field(default=None, min_length=64, max_length=64)
    response_row_count: int | None = Field(default=None, ge=0)
    normalized_rows: tuple[SpotOracleContextNormalizedRow, ...] = ()
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
    def _validate_result(self) -> "SpotOracleContextFetchResult":
        require_research_boundary(self, context="spot-oracle-context fetch result")
        if self.row_count != len(self.normalized_rows):
            raise ValueError("row_count must match normalized_rows length")
        if self.status == SpotOracleContextFetchStatus.COMPLETED and not self.normalized_rows:
            raise ValueError("completed fetch results require normalized rows")
        if self.status != SpotOracleContextFetchStatus.COMPLETED and not self.blocked_reasons:
            raise ValueError(f"{self.status.value} fetch results require blocker reasons")
        expected_id = spot_oracle_context_fetch_id_for(
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


SpotOracleContextGetProbe = Callable[
    [str],
    SpotOracleContextGetResult | Mapping[str, Any] | int,
]


SPOT_ORACLE_CONTEXT_ENDPOINT_SPECS = (
    SpotOracleContextEndpointSpec(
        endpoint_id="coinbase_spot_candles",
        source_id="coinbase_spot_public",
        venue="coinbase",
        venue_key="coinbase_spot",
        market_type="spot",
        family="candles",
        endpoint_path="/products/{symbol}/candles",
        base_url="https://api.exchange.coinbase.com",
        interval="60",
        limit=300,
        timestamp_mode="iso",
        rate_limit_hint="public product candles endpoint; one-minute granularity capped at 300 candles",
    ),
    SpotOracleContextEndpointSpec(
        endpoint_id="kraken_spot_ohlc",
        source_id="kraken_spot_public",
        venue="kraken",
        venue_key="kraken_spot",
        market_type="spot",
        family="candles",
        endpoint_path="/0/public/OHLC",
        base_url="https://api.kraken.com",
        interval="1",
        limit=720,
        timestamp_mode="s",
        rate_limit_hint="public OHLC endpoint; one-minute interval with recent-window cap",
    ),
    SpotOracleContextEndpointSpec(
        endpoint_id="pyth_hermes_latest_price",
        source_id="pyth_hermes_public",
        venue="pyth",
        venue_key="pyth_feed",
        market_type="oracle",
        family="spot_oracle_context",
        endpoint_path="/v2/updates/price/latest",
        base_url="https://hermes.pyth.network",
        interval="latest",
        limit=None,
        timestamp_mode="none",
        rate_limit_hint="public Hermes latest price endpoint; feed IDs must be bounded",
    ),
    SpotOracleContextEndpointSpec(
        endpoint_id="defillama_current_price",
        source_id="defillama_public",
        venue="defillama",
        venue_key="defillama_context",
        market_type="context",
        family="spot_oracle_context",
        endpoint_path="/prices/current/{symbol}",
        base_url="https://coins.llama.fi",
        interval="latest",
        limit=None,
        timestamp_mode="none",
        rate_limit_hint="public current-price endpoint; context identifiers must be bounded",
    ),
    SpotOracleContextEndpointSpec(
        endpoint_id="dexscreener_pair_search",
        source_id="dexscreener_public",
        venue="dexscreener",
        venue_key="dexscreener",
        market_type="context",
        family="spot_oracle_context",
        endpoint_path="/latest/dex/search",
        base_url="https://api.dexscreener.com",
        interval="latest",
        limit=30,
        timestamp_mode="none",
        rate_limit_hint="public search endpoint; search probes must stay single-query and bounded",
    ),
    SpotOracleContextEndpointSpec(
        endpoint_id="geckoterminal_pool_search",
        source_id="geckoterminal_public",
        venue="geckoterminal",
        venue_key="geckoterminal",
        market_type="context",
        family="spot_oracle_context",
        endpoint_path="/api/v2/search/pools",
        base_url="https://api.geckoterminal.com",
        interval="latest",
        limit=100,
        timestamp_mode="none",
        rate_limit_hint="public pool search endpoint; query probes must stay single-query and bounded",
    ),
)

DEFAULT_SPOT_ORACLE_CONTEXT_ENDPOINT_IDS = tuple(
    spec.endpoint_id for spec in SPOT_ORACLE_CONTEXT_ENDPOINT_SPECS
)
_SPOT_ORACLE_CONTEXT_ENDPOINT_SPECS_BY_ID = {
    spec.endpoint_id: spec for spec in SPOT_ORACLE_CONTEXT_ENDPOINT_SPECS
}


def spot_oracle_context_endpoint_spec(endpoint_id: str) -> SpotOracleContextEndpointSpec:
    try:
        return _SPOT_ORACLE_CONTEXT_ENDPOINT_SPECS_BY_ID[endpoint_id]
    except KeyError as exc:
        raise ValueError(f"unsupported spot-oracle-context endpoint_id: {endpoint_id}") from exc


def spot_oracle_context_endpoint_ids_for_sources(source_ids: Iterable[str]) -> tuple[str, ...]:
    requested = set(source_ids)
    return tuple(
        spec.endpoint_id
        for spec in SPOT_ORACLE_CONTEXT_ENDPOINT_SPECS
        if spec.source_id in requested
    )


def build_spot_oracle_context_availability_request(
    *,
    endpoint_id: str,
    symbol: str,
    day: date,
    base_url: str | None = None,
) -> SpotOracleContextAvailabilityRequest:
    spec = spot_oracle_context_endpoint_spec(endpoint_id)
    start_ms, end_ms = _day_window_ms(day)
    normalized_symbol = _normalize_symbol(symbol, spec)
    params = _request_params_for_spec(
        spec=spec,
        symbol=normalized_symbol,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    quoted_symbol = quote(normalized_symbol, safe=":,")
    path = spec.endpoint_path.replace("{symbol}", quoted_symbol)
    root = (base_url or spec.base_url).rstrip("/")
    request_url = f"{root}{path}"
    if params:
        request_url = f"{request_url}?{urlencode(params)}"
    return SpotOracleContextAvailabilityRequest(
        endpoint_id=spec.endpoint_id,
        source_id=spec.source_id,
        venue=spec.venue,
        endpoint_path=path,
        request_params=params,
        request_url=request_url,
        probe_start_ms=start_ms,
        probe_end_ms=end_ms,
        timestamp_mode=spec.timestamp_mode,
    )


def spot_oracle_context_availability_rows_hash(
    rows: tuple[SpotOracleContextAvailabilityRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def spot_oracle_context_availability_manifest_id_for(
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
            "manifest_type": "spot_oracle_context_availability_manifest",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "source_ids": source_ids,
            "endpoint_ids": endpoint_ids,
            "source_registry_ref": source_registry_ref,
            "symbol_map_snapshot_id": symbol_map_snapshot_id,
            "row_manifest_hash": row_manifest_hash,
        }
    )


def spot_oracle_context_normalized_row_hash(
    row: SpotOracleContextNormalizedRow | Mapping[str, Any],
) -> str:
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
    if isinstance(row, SpotOracleContextNormalizedRow):
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


def spot_oracle_context_fetch_id_for(
    *,
    source_id: str,
    endpoint_id: str,
    request_url: str,
    status: SpotOracleContextFetchStatus,
    response_payload_hash: str | None,
    row_hashes: tuple[str, ...],
    blocked_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "spot_oracle_context_fetch_result",
            "source_id": source_id,
            "endpoint_id": endpoint_id,
            "request_url": request_url,
            "status": status.value,
            "response_payload_hash": response_payload_hash,
            "row_hashes": row_hashes,
            "blocked_reasons": blocked_reasons,
        }
    )


def write_spot_oracle_context_availability_manifest(
    *,
    archive_root: str | Path,
    symbol_map_snapshot: SymbolMapSnapshot | Mapping[str, Any],
    source_entries: Iterable[SourceRegistryEntry | Mapping[str, Any]],
    start_date: date,
    end_date: date,
    symbol_map_ref: str | None = None,
    source_ids: Iterable[str] = SPOT_ORACLE_CONTEXT_SOURCE_IDS,
    endpoint_ids: Iterable[str] | None = None,
    get_probe: SpotOracleContextGetProbe | None = None,
) -> SpotOracleContextAvailabilityWriteResult:
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
        else spot_oracle_context_endpoint_ids_for_sources(requested_source_ids)
    )
    if not requested_endpoint_ids:
        raise ValueError("endpoint_ids cannot be empty")
    entries_by_id = _validated_source_entries(source_entries, requested_source_ids)
    _validate_endpoint_ids(requested_endpoint_ids, requested_source_ids)
    probe = get_probe or default_spot_oracle_context_get_probe
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
    row_hash = spot_oracle_context_availability_rows_hash(rows)
    manifest_id = spot_oracle_context_availability_manifest_id_for(
        start_date=start_date,
        end_date=end_date,
        source_ids=requested_source_ids,
        endpoint_ids=requested_endpoint_ids,
        source_registry_ref=parsed_snapshot.source_registry_ref,
        symbol_map_snapshot_id=parsed_snapshot.symbol_map_snapshot_id,
        row_manifest_hash=row_hash,
    )
    manifest = SpotOracleContextAvailabilityManifest(
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
        available_count=_count_status(rows, SpotOracleContextAvailabilityStatus.AVAILABLE),
        missing_count=_count_status(rows, SpotOracleContextAvailabilityStatus.MISSING),
        blocked_mapping_count=_count_status(
            rows,
            SpotOracleContextAvailabilityStatus.BLOCKED_MAPPING,
        ),
        probe_error_count=_count_status(rows, SpotOracleContextAvailabilityStatus.PROBE_ERROR),
        row_manifest_hash=row_hash,
    )
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_path = layout.resolve(
        "manifests",
        "source_availability",
        f"spot_oracle_context_availability_{start_date.isoformat()}_{end_date.isoformat()}_{manifest_id[:16]}.json",
    )
    _write_json_model(manifest_path, manifest)
    return SpotOracleContextAvailabilityWriteResult(
        availability_manifest_id=manifest_id,
        manifest_ref=layout.relative_to_root(manifest_path),
        manifest_sha256=file_sha256(manifest_path),
        row_count=manifest.row_count,
        available_count=manifest.available_count,
        missing_count=manifest.missing_count,
        blocked_mapping_count=manifest.blocked_mapping_count,
        probe_error_count=manifest.probe_error_count,
    )


def fetch_spot_oracle_context_public_market_request(
    *,
    request: SpotOracleContextAvailabilityRequest | Mapping[str, Any],
    source_entry: SourceRegistryEntry | Mapping[str, Any],
    get_probe: SpotOracleContextGetProbe | None = None,
) -> SpotOracleContextFetchResult:
    parsed_request = (
        request
        if isinstance(request, SpotOracleContextAvailabilityRequest)
        else SpotOracleContextAvailabilityRequest.model_validate(dict(request))
    )
    spec = spot_oracle_context_endpoint_spec(parsed_request.endpoint_id)
    entry = (
        source_entry
        if isinstance(source_entry, SourceRegistryEntry)
        else SourceRegistryEntry.model_validate(dict(source_entry))
    )
    _validated_source_entries((entry,), (spec.source_id,))
    _validate_entry_supports_spec(entry, spec)
    venue_symbol = _venue_symbol_from_request(parsed_request, spec)
    probe = get_probe or default_spot_oracle_context_get_probe
    probe_result = _coerce_get_result(probe(parsed_request.request_url))
    response_payload_hash = _payload_hash(probe_result.payload)
    availability_status = _availability_status(spec=spec, result=probe_result)
    response_row_count = _response_row_count(probe_result.payload)
    if availability_status == SpotOracleContextAvailabilityStatus.MISSING:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=SpotOracleContextFetchStatus.EMPTY,
            http_status_code=probe_result.status_code,
            response_payload_hash=response_payload_hash,
            response_row_count=response_row_count,
            blocked_reasons=("empty_response",),
        )
    if availability_status == SpotOracleContextAvailabilityStatus.PROBE_ERROR:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=SpotOracleContextFetchStatus.FETCH_ERROR,
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
            status=SpotOracleContextFetchStatus.PARSE_ERROR,
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
            status=SpotOracleContextFetchStatus.EMPTY,
            http_status_code=probe_result.status_code,
            response_payload_hash=response_payload_hash,
            response_row_count=response_row_count,
            blocked_reasons=("empty_response",),
        )
    return _fetch_result(
        spec=spec,
        request=parsed_request,
        venue_symbol=venue_symbol,
        status=SpotOracleContextFetchStatus.COMPLETED,
        http_status_code=probe_result.status_code,
        response_payload_hash=response_payload_hash,
        response_row_count=response_row_count,
        rows=rows,
    )


def default_spot_oracle_context_get_probe(url: str) -> SpotOracleContextGetResult:
    try:
        response = httpx.get(url, timeout=10.0)
    except httpx.HTTPError as exc:
        return SpotOracleContextGetResult(error=str(exc))
    try:
        payload = response.json()
    except ValueError:
        payload = None
    return SpotOracleContextGetResult(
        status_code=response.status_code,
        headers={str(key): str(value) for key, value in response.headers.items()},
        payload=payload,
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
        raise ValueError("missing spot-oracle-context source entries: " + ",".join(missing))
    for source_id in source_ids:
        entry = entries[source_id]
        if source_id not in SPOT_ORACLE_CONTEXT_SOURCE_IDS:
            raise ValueError(f"unsupported spot-oracle-context source_id: {source_id}")
        require_strict_zero_dollar_source(entry)
        if not entry.accepted_under_strict_free:
            raise ValueError(f"{source_id} is not accepted under strict-free mode")
        if entry.native_to_hyperliquid:
            raise ValueError(f"{source_id} must not be Hyperliquid-native")
        if entry.accepted_historical_coverage_proof:
            raise ValueError(f"{source_id} cannot be accepted historical coverage proof")
        expected_role = (
            "external_comparison" if entry.market_type == "spot" else "spot_or_oracle_context"
        )
        if entry.research_role != expected_role:
            raise ValueError(f"{source_id} must remain {expected_role}")
    return entries


def _validate_endpoint_ids(endpoint_ids: tuple[str, ...], source_ids: tuple[str, ...]) -> None:
    for endpoint_id in endpoint_ids:
        spec = spot_oracle_context_endpoint_spec(endpoint_id)
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
    get_probe: SpotOracleContextGetProbe,
) -> tuple[SpotOracleContextAvailabilityRow, ...]:
    rows: list[SpotOracleContextAvailabilityRow] = []
    liquid_rows = [
        row
        for row in snapshot.symbol_map_rows
        if row.hyperliquid_liquid_as_of and row.above_day_notional_threshold
    ]
    for symbol_row in sorted(liquid_rows, key=lambda item: item.hyperliquid_coin):
        for endpoint_id in endpoint_ids:
            spec = spot_oracle_context_endpoint_spec(endpoint_id)
            entry = entries_by_id[spec.source_id]
            _validate_entry_supports_spec(entry, spec)
            try:
                mapping_ref = require_verified_external_mapping(symbol_row, spec.venue_key)
                venue_symbol = mapping_ref.symbol
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
                request = build_spot_oracle_context_availability_request(
                    endpoint_id=endpoint_id,
                    symbol=venue_symbol,
                    day=day,
                )
                probe_result = _coerce_get_result(get_probe(request.request_url))
                status = _availability_status(spec=spec, result=probe_result)
                rows.append(
                    SpotOracleContextAvailabilityRow(
                        source_id=spec.source_id,
                        endpoint_id=spec.endpoint_id,
                        source_registry_ref=snapshot.source_registry_ref,
                        symbol_map_ref=symbol_map_ref,
                        symbol_map_snapshot_id=snapshot.symbol_map_snapshot_id,
                        hyperliquid_coin=symbol_row.hyperliquid_coin,
                        venue=spec.venue,
                        venue_key=spec.venue_key,
                        venue_symbol=venue_symbol,
                        probe_date=day,
                        market_type=spec.market_type,
                        family=spec.family,
                        interval=spec.interval,
                        endpoint_path=request.endpoint_path,
                        request_url=request.request_url,
                        request_params=request.request_params,
                        probe_start_ms=request.probe_start_ms,
                        probe_end_ms=request.probe_end_ms,
                        timestamp_mode=spec.timestamp_mode,
                        request_limit=spec.limit,
                        rate_limit_hint=spec.rate_limit_hint,
                        availability_status=status,
                        http_status_code=probe_result.status_code,
                        response_row_count=_response_row_count(probe_result.payload),
                        source_cost_class=entry.cost_class,
                        blocked_reasons=_blocked_reasons_for_probe(
                            spec=spec,
                            result=probe_result,
                            status=status,
                        ),
                        probe_error=probe_result.error,
                    )
                )
    return tuple(rows)


def _validate_entry_supports_spec(
    entry: SourceRegistryEntry,
    spec: SpotOracleContextEndpointSpec,
) -> None:
    if spec.family not in entry.data_families:
        raise ValueError(f"{entry.source_id} is missing data family {spec.family}")
    if entry.venue != spec.venue:
        raise ValueError(f"{entry.source_id} venue does not match endpoint spec")
    if entry.market_type != spec.market_type:
        raise ValueError(f"{entry.source_id} market_type does not match endpoint spec")


def _fetch_result(
    *,
    spec: SpotOracleContextEndpointSpec,
    request: SpotOracleContextAvailabilityRequest,
    venue_symbol: str,
    status: SpotOracleContextFetchStatus,
    http_status_code: int | None = None,
    response_payload_hash: str | None = None,
    response_row_count: int | None = None,
    rows: tuple[SpotOracleContextNormalizedRow, ...] = (),
    blocked_reasons: tuple[str, ...] = (),
) -> SpotOracleContextFetchResult:
    fetch_id = spot_oracle_context_fetch_id_for(
        source_id=spec.source_id,
        endpoint_id=spec.endpoint_id,
        request_url=request.request_url,
        status=status,
        response_payload_hash=response_payload_hash,
        row_hashes=tuple(row.row_hash for row in rows),
        blocked_reasons=blocked_reasons,
    )
    return SpotOracleContextFetchResult(
        fetch_id=fetch_id,
        source_id=spec.source_id,
        endpoint_id=spec.endpoint_id,
        venue=spec.venue,
        venue_symbol=venue_symbol,
        market_type=spec.market_type,
        family=spec.family,
        request_url=request.request_url,
        endpoint_path=request.endpoint_path,
        status=status,
        http_status_code=http_status_code,
        response_payload_hash=response_payload_hash,
        response_row_count=response_row_count,
        normalized_rows=rows,
        row_count=len(rows),
        blocked_reasons=blocked_reasons,
    )


def _blocked_mapping_rows(
    *,
    snapshot: SymbolMapSnapshot,
    symbol_map_ref: str,
    source_entry: SourceRegistryEntry,
    spec: SpotOracleContextEndpointSpec,
    hyperliquid_coin: str,
    start_date: date,
    end_date: date,
    reason: str,
) -> list[SpotOracleContextAvailabilityRow]:
    return [
        SpotOracleContextAvailabilityRow(
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
            timestamp_mode=spec.timestamp_mode,
            request_limit=spec.limit,
            rate_limit_hint=spec.rate_limit_hint,
            availability_status=SpotOracleContextAvailabilityStatus.BLOCKED_MAPPING,
            source_cost_class=source_entry.cost_class,
            blocked_reasons=(reason,),
        )
        for day in _date_range(start_date, end_date)
    ]


def _request_params_for_spec(
    *,
    spec: SpotOracleContextEndpointSpec,
    symbol: str,
    start_ms: int,
    end_ms: int,
) -> dict[str, str]:
    if spec.endpoint_id == "coinbase_spot_candles":
        return {
            "start": _iso_from_ms(start_ms),
            "end": _iso_from_ms(end_ms),
            "granularity": spec.interval,
        }
    if spec.endpoint_id == "kraken_spot_ohlc":
        return {
            "pair": symbol,
            "interval": spec.interval,
            "since": str(start_ms // 1000),
        }
    if spec.endpoint_id == "pyth_hermes_latest_price":
        return {"ids[]": symbol}
    if spec.endpoint_id == "dexscreener_pair_search":
        return {"q": symbol}
    if spec.endpoint_id == "geckoterminal_pool_search":
        return {"query": symbol}
    return {}


def _normalize_payload(
    *,
    spec: SpotOracleContextEndpointSpec,
    request: SpotOracleContextAvailabilityRequest,
    result: SpotOracleContextGetResult,
) -> tuple[SpotOracleContextNormalizedRow, ...]:
    payload = result.payload
    if spec.endpoint_id == "coinbase_spot_candles":
        return _normalize_coinbase_candles(spec=spec, request=request, payload=payload)
    if spec.endpoint_id == "kraken_spot_ohlc":
        return _normalize_kraken_ohlc(spec=spec, request=request, payload=payload)
    if spec.endpoint_id == "pyth_hermes_latest_price":
        return _normalize_mapping_list(
            spec=spec,
            request=request,
            payload=payload,
            key="parsed",
            missing_message="pyth_hermes_latest_price payload is missing parsed rows",
        )
    if spec.endpoint_id == "defillama_current_price":
        return _normalize_defillama_prices(spec=spec, request=request, payload=payload)
    if spec.endpoint_id == "dexscreener_pair_search":
        return _normalize_mapping_list(
            spec=spec,
            request=request,
            payload=payload,
            key="pairs",
            missing_message="dexscreener_pair_search payload is missing pairs",
        )
    if spec.endpoint_id == "geckoterminal_pool_search":
        return _normalize_mapping_list(
            spec=spec,
            request=request,
            payload=payload,
            key="data",
            missing_message="geckoterminal_pool_search payload is missing data",
        )
    raise ValueError(f"unsupported spot-oracle-context endpoint_id: {spec.endpoint_id}")


def _normalize_coinbase_candles(
    *,
    spec: SpotOracleContextEndpointSpec,
    request: SpotOracleContextAvailabilityRequest,
    payload: Any,
) -> tuple[SpotOracleContextNormalizedRow, ...]:
    if not isinstance(payload, list):
        raise ValueError("coinbase_spot_candles payload must be a list")
    rows: list[SpotOracleContextNormalizedRow] = []
    for row_index, row in enumerate(payload):
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            raise ValueError("coinbase_spot_candles candle row must have at least 6 fields")
        timestamp_ms = _parse_timestamp_ms(row[0], field_name="time")
        raw_fields = {
            "time": str(row[0]),
            "low": str(row[1]),
            "high": str(row[2]),
            "open": str(row[3]),
            "close": str(row[4]),
            "volume": str(row[5]),
        }
        numeric_fields = {key: raw_fields[key] for key in ("low", "high", "open", "close", "volume")}
        rows.append(
            _normalized_row(
                spec=spec,
                request=request,
                row_index=row_index,
                source_timestamp_ms=timestamp_ms,
                raw_fields=raw_fields,
                numeric_fields=numeric_fields,
            )
        )
    return tuple(rows)


def _normalize_kraken_ohlc(
    *,
    spec: SpotOracleContextEndpointSpec,
    request: SpotOracleContextAvailabilityRequest,
    payload: Any,
) -> tuple[SpotOracleContextNormalizedRow, ...]:
    if not isinstance(payload, Mapping):
        raise ValueError("kraken_spot_ohlc payload must be an object")
    api_result = payload.get("result")
    if not isinstance(api_result, Mapping):
        raise ValueError("kraken_spot_ohlc payload is missing result")
    source_rows: list[Any] | None = None
    for key, value in api_result.items():
        if key == "last":
            continue
        if isinstance(value, list):
            source_rows = value
            break
    if source_rows is None:
        raise ValueError("kraken_spot_ohlc payload is missing OHLC rows")
    rows: list[SpotOracleContextNormalizedRow] = []
    for row_index, row in enumerate(source_rows):
        if not isinstance(row, (list, tuple)) or len(row) < 8:
            raise ValueError("kraken_spot_ohlc candle row must have at least 8 fields")
        timestamp_ms = _parse_timestamp_ms(row[0], field_name="time")
        raw_fields = {
            "time": str(row[0]),
            "open": str(row[1]),
            "high": str(row[2]),
            "low": str(row[3]),
            "close": str(row[4]),
            "vwap": str(row[5]),
            "volume": str(row[6]),
            "count": str(row[7]),
        }
        numeric_fields = {
            key: raw_fields[key]
            for key in ("open", "high", "low", "close", "vwap", "volume", "count")
        }
        rows.append(
            _normalized_row(
                spec=spec,
                request=request,
                row_index=row_index,
                source_timestamp_ms=timestamp_ms,
                raw_fields=raw_fields,
                numeric_fields=numeric_fields,
            )
        )
    return tuple(rows)


def _normalize_mapping_list(
    *,
    spec: SpotOracleContextEndpointSpec,
    request: SpotOracleContextAvailabilityRequest,
    payload: Any,
    key: str,
    missing_message: str,
) -> tuple[SpotOracleContextNormalizedRow, ...]:
    if not isinstance(payload, Mapping):
        raise ValueError(missing_message)
    source_rows = payload.get(key)
    if not isinstance(source_rows, list):
        raise ValueError(missing_message)
    rows: list[SpotOracleContextNormalizedRow] = []
    for row_index, row in enumerate(source_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"{spec.endpoint_id} row must be an object")
        raw_fields = _raw_fields_from_mapping(row)
        rows.append(
            _normalized_row(
                spec=spec,
                request=request,
                row_index=row_index,
                source_timestamp_ms=_first_timestamp_ms(raw_fields),
                raw_fields=raw_fields,
                numeric_fields=_numeric_fields_from_raw_fields(raw_fields),
            )
        )
    return tuple(rows)


def _normalize_defillama_prices(
    *,
    spec: SpotOracleContextEndpointSpec,
    request: SpotOracleContextAvailabilityRequest,
    payload: Any,
) -> tuple[SpotOracleContextNormalizedRow, ...]:
    if not isinstance(payload, Mapping):
        raise ValueError("defillama_current_price payload must be an object")
    coins = payload.get("coins")
    if not isinstance(coins, Mapping):
        raise ValueError("defillama_current_price payload is missing coins")
    rows: list[SpotOracleContextNormalizedRow] = []
    for row_index, (coin_id, row) in enumerate(sorted(coins.items())):
        if not isinstance(row, Mapping):
            raise ValueError("defillama_current_price coin row must be an object")
        raw_fields = {"coin_id": str(coin_id)}
        raw_fields.update(_raw_fields_from_mapping(row))
        rows.append(
            _normalized_row(
                spec=spec,
                request=request,
                row_index=row_index,
                source_timestamp_ms=_first_timestamp_ms(raw_fields),
                raw_fields=raw_fields,
                numeric_fields=_numeric_fields_from_raw_fields(raw_fields),
            )
        )
    return tuple(rows)


def _normalized_row(
    *,
    spec: SpotOracleContextEndpointSpec,
    request: SpotOracleContextAvailabilityRequest,
    row_index: int,
    source_timestamp_ms: int | None,
    raw_fields: Mapping[str, str],
    numeric_fields: Mapping[str, str],
) -> SpotOracleContextNormalizedRow:
    payload: dict[str, Any] = {
        "source_id": spec.source_id,
        "endpoint_id": spec.endpoint_id,
        "venue": spec.venue,
        "venue_symbol": _venue_symbol_from_request(request, spec),
        "market_type": spec.market_type,
        "family": spec.family,
        "row_index": row_index,
        "source_timestamp_ms": source_timestamp_ms,
        "source_timestamp": (
            datetime.fromtimestamp(source_timestamp_ms / 1000, tz=UTC)
            if source_timestamp_ms is not None
            else None
        ),
        "numeric_fields": dict(sorted(numeric_fields.items())),
        "raw_fields": dict(sorted(raw_fields.items())),
        "source_request_url": request.request_url,
    }
    return SpotOracleContextNormalizedRow(
        **payload,
        row_hash=spot_oracle_context_normalized_row_hash(payload),
    )


def _availability_status(
    *,
    spec: SpotOracleContextEndpointSpec,
    result: SpotOracleContextGetResult,
) -> SpotOracleContextAvailabilityStatus:
    if result.error:
        return SpotOracleContextAvailabilityStatus.PROBE_ERROR
    if result.status_code == 404:
        return SpotOracleContextAvailabilityStatus.MISSING
    if result.status_code != 200:
        return SpotOracleContextAvailabilityStatus.PROBE_ERROR
    api_error = _api_error(spec=spec, result=result)
    if api_error:
        return SpotOracleContextAvailabilityStatus.PROBE_ERROR
    row_count = _response_row_count(result.payload)
    if row_count and row_count > 0:
        return SpotOracleContextAvailabilityStatus.AVAILABLE
    return SpotOracleContextAvailabilityStatus.MISSING


def _blocked_reasons_for_probe(
    *,
    spec: SpotOracleContextEndpointSpec,
    result: SpotOracleContextGetResult,
    status: SpotOracleContextAvailabilityStatus,
) -> tuple[str, ...]:
    if status in {
        SpotOracleContextAvailabilityStatus.AVAILABLE,
        SpotOracleContextAvailabilityStatus.MISSING,
    }:
        return ()
    if result.error:
        return (f"probe_error:{result.error}",)
    api_error = _api_error(spec=spec, result=result)
    if api_error:
        return (api_error,)
    return (f"unexpected_http_status:{result.status_code}",)


def _api_error(
    *,
    spec: SpotOracleContextEndpointSpec,
    result: SpotOracleContextGetResult,
) -> str | None:
    payload = result.payload
    if not isinstance(payload, Mapping):
        return None
    error = payload.get("error")
    if error:
        if isinstance(error, list):
            if not error:
                return None
            return f"{spec.venue}_error:{error[0]}"
        if isinstance(error, Mapping):
            code = error.get("code")
            message = error.get("message")
            return f"{spec.venue}_error:{code or message}"
        return f"{spec.venue}_error:{error}"
    errors = payload.get("errors")
    if errors:
        return f"{spec.venue}_errors"
    message = payload.get("message")
    if message and not _has_expected_payload_data(payload):
        return f"{spec.venue}_message:{message}"
    return None


def _has_expected_payload_data(payload: Mapping[str, Any]) -> bool:
    row_count = _response_row_count(payload)
    return row_count is not None and row_count > 0


def _response_row_count(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    if not isinstance(payload, Mapping):
        return None
    data = payload.get("data")
    if isinstance(data, list):
        return len(data)
    pairs = payload.get("pairs")
    if isinstance(pairs, list):
        return len(pairs)
    parsed = payload.get("parsed")
    if isinstance(parsed, list):
        return len(parsed)
    coins = payload.get("coins")
    if isinstance(coins, Mapping):
        return len(coins)
    api_result = payload.get("result")
    if isinstance(api_result, Mapping):
        for key, value in api_result.items():
            if key == "last":
                continue
            if isinstance(value, list):
                return len(value)
    return None


def _coerce_get_result(
    value: SpotOracleContextGetResult | Mapping[str, Any] | int,
) -> SpotOracleContextGetResult:
    if isinstance(value, SpotOracleContextGetResult):
        return value
    if isinstance(value, int):
        return SpotOracleContextGetResult(status_code=value)
    return SpotOracleContextGetResult.model_validate(dict(value))


def _payload_hash(payload: Any) -> str | None:
    if payload is None:
        return None
    return canonical_json_hash(payload)


def _venue_symbol_from_request(
    request: SpotOracleContextAvailabilityRequest,
    spec: SpotOracleContextEndpointSpec,
) -> str:
    if spec.endpoint_id == "coinbase_spot_candles":
        prefix = "/products/"
        suffix = "/candles"
        if prefix in request.endpoint_path and request.endpoint_path.endswith(suffix):
            return unquote(request.endpoint_path.split(prefix, 1)[1][: -len(suffix)])
    if spec.endpoint_id == "kraken_spot_ohlc":
        pair = request.request_params.get("pair")
        if pair:
            return pair
    if spec.endpoint_id == "pyth_hermes_latest_price":
        feed_id = request.request_params.get("ids[]")
        if feed_id:
            return feed_id
    if spec.endpoint_id == "defillama_current_price":
        prefix = "/prices/current/"
        if request.endpoint_path.startswith(prefix):
            return unquote(request.endpoint_path[len(prefix) :])
    if spec.endpoint_id == "dexscreener_pair_search":
        query = request.request_params.get("q")
        if query:
            return query
    if spec.endpoint_id == "geckoterminal_pool_search":
        query = request.request_params.get("query")
        if query:
            return query
    raise ValueError(f"{spec.endpoint_id} request is missing venue symbol")


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


def _iso_from_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp_ms(value: Any, *, field_name: str) -> int:
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"invalid {field_name}: {value!r}")
        return value if value >= 10_000_000_000 else value * 1000
    raw = str(value).strip()
    if not raw:
        raise ValueError(f"invalid {field_name}: {value!r}")
    if "T" in raw:
        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"invalid {field_name}: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return int(parsed.timestamp() * 1000)
    try:
        parsed_float = float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {value!r}") from exc
    if parsed_float < 0:
        raise ValueError(f"invalid {field_name}: {value!r}")
    parsed_int = int(parsed_float)
    return parsed_int if parsed_int >= 10_000_000_000 else parsed_int * 1000


def _raw_fields_from_mapping(row: Mapping[str, Any], *, prefix: str = "") -> dict[str, str]:
    raw_fields: dict[str, str] = {}
    for key, value in sorted(row.items(), key=lambda item: str(item[0])):
        raw_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            raw_fields.update(_raw_fields_from_mapping(value, prefix=raw_key))
        elif isinstance(value, list):
            raw_fields[raw_key] = json.dumps(value, sort_keys=True, ensure_ascii=True)
        elif value is not None:
            raw_fields[raw_key] = str(value)
    return raw_fields


def _numeric_fields_from_raw_fields(raw_fields: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in raw_fields.items()
        if _is_decimal_like(value)
    }


def _is_decimal_like(value: str) -> bool:
    try:
        Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    return True


def _first_timestamp_ms(raw_fields: Mapping[str, str]) -> int | None:
    timestamp_keys = (
        "time",
        "timestamp",
        "updated_at",
        "publish_time",
        "publishTime",
        "price.publish_time",
        "ema_price.publish_time",
        "attributes.updated_at",
        "pairCreatedAt",
    )
    for key in timestamp_keys:
        value = raw_fields.get(key)
        if value is None:
            continue
        return _parse_timestamp_ms(value, field_name=key)
    return None


def _normalize_symbol(symbol: str, spec: SpotOracleContextEndpointSpec) -> str:
    normalized = symbol.strip()
    if spec.market_type == "spot":
        normalized = normalized.upper()
    if not normalized:
        raise ValueError(f"unsupported {spec.venue} symbol: {symbol!r}")
    if any(character.isspace() or ord(character) < 32 for character in normalized):
        raise ValueError(f"unsupported {spec.venue} symbol: {symbol!r}")
    return normalized


def _default_symbol_map_ref(snapshot: SymbolMapSnapshot) -> str:
    return f"manifests/symbol_maps/{snapshot.symbol_map_snapshot_id}.json"


def _count_status(
    rows: tuple[SpotOracleContextAvailabilityRow, ...],
    status: SpotOracleContextAvailabilityStatus,
) -> int:
    return sum(1 for row in rows if row.availability_status == status)


def _write_json_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
