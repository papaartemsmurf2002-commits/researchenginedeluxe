# V2-AUDIT-ID: V2-AUD-DATASRC-030, V2-AUD-DATASRC-031
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, strict_free_public_rate_limited, no_downloads
# V2-OWNER: v2_data_sources
"""dYdX and Deribit public reference-derivatives availability matrix."""

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

REFERENCE_DERIVATIVES_SOURCE_IDS = (
    "dydx_indexer_public",
    "deribit_public",
)


class ReferenceDerivativesAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    BLOCKED_MAPPING = "blocked_mapping"
    PROBE_ERROR = "probe_error"


class ReferenceDerivativesFetchStatus(str, Enum):
    COMPLETED = "completed"
    EMPTY = "empty"
    FETCH_ERROR = "fetch_error"
    PARSE_ERROR = "parse_error"


class ReferenceDerivativesEndpointSpec(BaseModel):
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
    timestamp_mode: str = Field(pattern=r"^(iso|ms)$")
    rate_limit_hint: str = Field(min_length=1)


class ReferenceDerivativesGetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int | None = Field(default=None, ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    payload: Any = None
    error: str | None = None


class ReferenceDerivativesAvailabilityRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    request_params: dict[str, str] = Field(default_factory=dict)
    request_url: str = Field(min_length=1)
    probe_start_ms: int = Field(ge=0)
    probe_end_ms: int = Field(ge=0)
    timestamp_mode: str = Field(pattern=r"^(iso|ms)$")

    @model_validator(mode="after")
    def _validate_request(self) -> "ReferenceDerivativesAvailabilityRequest":
        if self.probe_end_ms <= self.probe_start_ms:
            raise ValueError("probe_end_ms must be greater than probe_start_ms")
        return self


class ReferenceDerivativesAvailabilityRow(BaseModel):
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
    timestamp_mode: str = Field(pattern=r"^(iso|ms)$")
    request_limit: int | None = Field(default=None, ge=1)
    rate_limit_hint: str = Field(min_length=1)
    availability_status: ReferenceDerivativesAvailabilityStatus
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
    def _validate_row(self) -> "ReferenceDerivativesAvailabilityRow":
        require_research_boundary(self, context="reference-derivatives availability row")
        if self.native_to_hyperliquid:
            raise ValueError("reference-derivatives rows cannot be Hyperliquid-native")
        if self.accepted_historical_coverage_proof:
            raise ValueError("availability rows are not historical coverage proof")
        if self.availability_status == ReferenceDerivativesAvailabilityStatus.AVAILABLE:
            if not self.request_url:
                raise ValueError("available rows require request_url")
            if not self.response_row_count:
                raise ValueError("available rows require positive response_row_count")
        if self.availability_status in {
            ReferenceDerivativesAvailabilityStatus.BLOCKED_MAPPING,
            ReferenceDerivativesAvailabilityStatus.PROBE_ERROR,
        } and not self.blocked_reasons:
            raise ValueError(f"{self.availability_status.value} rows require blocker reasons")
        return self


class ReferenceDerivativesAvailabilityManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "reference_derivatives_availability_manifest"
    availability_manifest_id: str = Field(min_length=64, max_length=64)
    start_date: date
    end_date: date
    source_ids: tuple[str, ...] = Field(min_length=1)
    endpoint_ids: tuple[str, ...] = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    strict_zero_dollar_mode: bool = True
    rows: tuple[ReferenceDerivativesAvailabilityRow, ...]
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
    def _validate_manifest(self) -> "ReferenceDerivativesAvailabilityManifest":
        require_research_boundary(self, context="reference-derivatives availability manifest")
        if self.manifest_type != "reference_derivatives_availability_manifest":
            raise ValueError("manifest_type must be reference_derivatives_availability_manifest")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.available_count != _count_status(
            self.rows,
            ReferenceDerivativesAvailabilityStatus.AVAILABLE,
        ):
            raise ValueError("available_count does not match rows")
        if self.missing_count != _count_status(
            self.rows,
            ReferenceDerivativesAvailabilityStatus.MISSING,
        ):
            raise ValueError("missing_count does not match rows")
        if self.blocked_mapping_count != _count_status(
            self.rows,
            ReferenceDerivativesAvailabilityStatus.BLOCKED_MAPPING,
        ):
            raise ValueError("blocked_mapping_count does not match rows")
        if self.probe_error_count != _count_status(
            self.rows,
            ReferenceDerivativesAvailabilityStatus.PROBE_ERROR,
        ):
            raise ValueError("probe_error_count does not match rows")
        expected_hash = reference_derivatives_availability_rows_hash(self.rows)
        if self.row_manifest_hash != expected_hash:
            raise ValueError("row_manifest_hash does not match availability rows")
        expected_id = reference_derivatives_availability_manifest_id_for(
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


class ReferenceDerivativesAvailabilityWriteResult(BaseModel):
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
    def _validate_result(self) -> "ReferenceDerivativesAvailabilityWriteResult":
        require_research_boundary(self, context="reference-derivatives availability write result")
        return self


class ReferenceDerivativesNormalizedRow(BaseModel):
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
    def _validate_row(self) -> "ReferenceDerivativesNormalizedRow":
        require_research_boundary(self, context="reference-derivatives normalized row")
        if self.native_to_hyperliquid:
            raise ValueError("reference-derivatives normalized rows cannot be Hyperliquid-native")
        if self.accepted_historical_coverage_proof:
            raise ValueError("smoke rows are not accepted historical coverage proof")
        if self.row_hash != reference_derivatives_normalized_row_hash(self):
            raise ValueError("row_hash does not match normalized row")
        return self


class ReferenceDerivativesFetchResult(BaseModel):
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
    status: ReferenceDerivativesFetchStatus
    http_status_code: int | None = None
    response_payload_hash: str | None = Field(default=None, min_length=64, max_length=64)
    response_row_count: int | None = Field(default=None, ge=0)
    normalized_rows: tuple[ReferenceDerivativesNormalizedRow, ...] = ()
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
    def _validate_result(self) -> "ReferenceDerivativesFetchResult":
        require_research_boundary(self, context="reference-derivatives fetch result")
        if self.row_count != len(self.normalized_rows):
            raise ValueError("row_count must match normalized_rows length")
        if self.status == ReferenceDerivativesFetchStatus.COMPLETED and not self.normalized_rows:
            raise ValueError("completed fetch results require normalized rows")
        if self.status != ReferenceDerivativesFetchStatus.COMPLETED and not self.blocked_reasons:
            raise ValueError(f"{self.status.value} fetch results require blocker reasons")
        expected_id = reference_derivatives_fetch_id_for(
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


REFERENCE_DERIVATIVES_ENDPOINT_SPECS: dict[str, ReferenceDerivativesEndpointSpec] = {
    "dydx_indexer_candles": ReferenceDerivativesEndpointSpec(
        endpoint_id="dydx_indexer_candles",
        source_id="dydx_indexer_public",
        venue="dydx",
        venue_key="dydx",
        market_type="perpetual",
        family="candles",
        endpoint_path="/v4/candles/perpetualMarkets/{symbol}",
        base_url="https://indexer.dydx.trade",
        interval="1MIN",
        limit=100,
        timestamp_mode="iso",
        rate_limit_hint="dYdX public indexer endpoint limits apply",
    ),
    "deribit_tradingview_chart": ReferenceDerivativesEndpointSpec(
        endpoint_id="deribit_tradingview_chart",
        source_id="deribit_public",
        venue="deribit",
        venue_key="deribit_perpetual",
        market_type="perpetual",
        family="candles",
        endpoint_path="/api/v2/public/get_tradingview_chart_data",
        base_url="https://www.deribit.com",
        interval="1",
        limit=None,
        timestamp_mode="ms",
        rate_limit_hint="Deribit public REST endpoint limits apply",
    ),
}
DEFAULT_REFERENCE_DERIVATIVES_ENDPOINT_IDS = tuple(REFERENCE_DERIVATIVES_ENDPOINT_SPECS)

ReferenceDerivativesGetProbe = Callable[
    [str],
    ReferenceDerivativesGetResult | Mapping[str, Any] | int,
]


def reference_derivatives_endpoint_spec(endpoint_id: str) -> ReferenceDerivativesEndpointSpec:
    try:
        return REFERENCE_DERIVATIVES_ENDPOINT_SPECS[endpoint_id]
    except KeyError as exc:
        raise ValueError(f"unsupported reference-derivatives endpoint_id: {endpoint_id}") from exc


def reference_derivatives_endpoint_ids_for_sources(source_ids: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(source_ids)
    return tuple(
        endpoint_id
        for endpoint_id, spec in REFERENCE_DERIVATIVES_ENDPOINT_SPECS.items()
        if spec.source_id in requested
    )


def build_reference_derivatives_availability_request(
    *,
    endpoint_id: str,
    symbol: str,
    day: date,
    base_url: str | None = None,
) -> ReferenceDerivativesAvailabilityRequest:
    spec = reference_derivatives_endpoint_spec(endpoint_id)
    start_ms, end_ms = _day_window_ms(day)
    normalized_symbol = _normalize_symbol(symbol, spec.venue)
    params = _request_params_for_spec(
        spec=spec,
        symbol=normalized_symbol,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    path = spec.endpoint_path.replace("{symbol}", normalized_symbol)
    root = (base_url or spec.base_url).rstrip("/")
    return ReferenceDerivativesAvailabilityRequest(
        endpoint_id=spec.endpoint_id,
        source_id=spec.source_id,
        venue=spec.venue,
        endpoint_path=path,
        request_params=params,
        request_url=f"{root}{path}?{urlencode(params)}",
        probe_start_ms=start_ms,
        probe_end_ms=end_ms,
        timestamp_mode=spec.timestamp_mode,
    )


def reference_derivatives_availability_rows_hash(
    rows: tuple[ReferenceDerivativesAvailabilityRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def reference_derivatives_availability_manifest_id_for(
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
            "manifest_type": "reference_derivatives_availability_manifest",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "source_ids": source_ids,
            "endpoint_ids": endpoint_ids,
            "source_registry_ref": source_registry_ref,
            "symbol_map_snapshot_id": symbol_map_snapshot_id,
            "row_manifest_hash": row_manifest_hash,
        }
    )


def reference_derivatives_normalized_row_hash(
    row: ReferenceDerivativesNormalizedRow | Mapping[str, Any],
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
    if isinstance(row, ReferenceDerivativesNormalizedRow):
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


def reference_derivatives_fetch_id_for(
    *,
    source_id: str,
    endpoint_id: str,
    request_url: str,
    status: ReferenceDerivativesFetchStatus,
    response_payload_hash: str | None,
    row_hashes: tuple[str, ...],
    blocked_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "reference_derivatives_fetch_result",
            "source_id": source_id,
            "endpoint_id": endpoint_id,
            "request_url": request_url,
            "status": status.value,
            "response_payload_hash": response_payload_hash,
            "row_hashes": row_hashes,
            "blocked_reasons": blocked_reasons,
        }
    )


def write_reference_derivatives_availability_manifest(
    *,
    archive_root: str | Path,
    symbol_map_snapshot: SymbolMapSnapshot | Mapping[str, Any],
    source_entries: Iterable[SourceRegistryEntry | Mapping[str, Any]],
    start_date: date,
    end_date: date,
    symbol_map_ref: str | None = None,
    source_ids: Iterable[str] = REFERENCE_DERIVATIVES_SOURCE_IDS,
    endpoint_ids: Iterable[str] | None = None,
    get_probe: ReferenceDerivativesGetProbe | None = None,
) -> ReferenceDerivativesAvailabilityWriteResult:
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
        else reference_derivatives_endpoint_ids_for_sources(requested_source_ids)
    )
    if not requested_endpoint_ids:
        raise ValueError("endpoint_ids cannot be empty")
    entries_by_id = _validated_source_entries(source_entries, requested_source_ids)
    _validate_endpoint_ids(requested_endpoint_ids, requested_source_ids)
    probe = get_probe or default_reference_derivatives_get_probe
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
    row_hash = reference_derivatives_availability_rows_hash(rows)
    manifest_id = reference_derivatives_availability_manifest_id_for(
        start_date=start_date,
        end_date=end_date,
        source_ids=requested_source_ids,
        endpoint_ids=requested_endpoint_ids,
        source_registry_ref=parsed_snapshot.source_registry_ref,
        symbol_map_snapshot_id=parsed_snapshot.symbol_map_snapshot_id,
        row_manifest_hash=row_hash,
    )
    manifest = ReferenceDerivativesAvailabilityManifest(
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
        available_count=_count_status(rows, ReferenceDerivativesAvailabilityStatus.AVAILABLE),
        missing_count=_count_status(rows, ReferenceDerivativesAvailabilityStatus.MISSING),
        blocked_mapping_count=_count_status(
            rows,
            ReferenceDerivativesAvailabilityStatus.BLOCKED_MAPPING,
        ),
        probe_error_count=_count_status(rows, ReferenceDerivativesAvailabilityStatus.PROBE_ERROR),
        row_manifest_hash=row_hash,
    )
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    manifest_path = layout.resolve(
        "manifests",
        "source_availability",
        f"reference_derivatives_availability_{start_date.isoformat()}_{end_date.isoformat()}_{manifest_id[:16]}.json",
    )
    _write_json_model(manifest_path, manifest)
    return ReferenceDerivativesAvailabilityWriteResult(
        availability_manifest_id=manifest_id,
        manifest_ref=layout.relative_to_root(manifest_path),
        manifest_sha256=file_sha256(manifest_path),
        row_count=manifest.row_count,
        available_count=manifest.available_count,
        missing_count=manifest.missing_count,
        blocked_mapping_count=manifest.blocked_mapping_count,
        probe_error_count=manifest.probe_error_count,
    )


def fetch_reference_derivatives_public_market_request(
    *,
    request: ReferenceDerivativesAvailabilityRequest | Mapping[str, Any],
    source_entry: SourceRegistryEntry | Mapping[str, Any],
    get_probe: ReferenceDerivativesGetProbe | None = None,
) -> ReferenceDerivativesFetchResult:
    parsed_request = (
        request
        if isinstance(request, ReferenceDerivativesAvailabilityRequest)
        else ReferenceDerivativesAvailabilityRequest.model_validate(dict(request))
    )
    spec = reference_derivatives_endpoint_spec(parsed_request.endpoint_id)
    entry = (
        source_entry
        if isinstance(source_entry, SourceRegistryEntry)
        else SourceRegistryEntry.model_validate(dict(source_entry))
    )
    _validated_source_entries((entry,), (spec.source_id,))
    _validate_entry_supports_spec(entry, spec)
    venue_symbol = _venue_symbol_from_request(parsed_request, spec)
    probe = get_probe or default_reference_derivatives_get_probe
    probe_result = _coerce_get_result(probe(parsed_request.request_url))
    response_payload_hash = _payload_hash(probe_result.payload)
    availability_status = _availability_status(spec=spec, result=probe_result)
    response_row_count = _response_row_count(probe_result.payload)
    if availability_status == ReferenceDerivativesAvailabilityStatus.MISSING:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=ReferenceDerivativesFetchStatus.EMPTY,
            http_status_code=probe_result.status_code,
            response_payload_hash=response_payload_hash,
            response_row_count=response_row_count,
            blocked_reasons=("empty_response",),
        )
    if availability_status == ReferenceDerivativesAvailabilityStatus.PROBE_ERROR:
        return _fetch_result(
            spec=spec,
            request=parsed_request,
            venue_symbol=venue_symbol,
            status=ReferenceDerivativesFetchStatus.FETCH_ERROR,
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
            status=ReferenceDerivativesFetchStatus.PARSE_ERROR,
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
            status=ReferenceDerivativesFetchStatus.EMPTY,
            http_status_code=probe_result.status_code,
            response_payload_hash=response_payload_hash,
            response_row_count=response_row_count,
            blocked_reasons=("empty_response",),
        )
    return _fetch_result(
        spec=spec,
        request=parsed_request,
        venue_symbol=venue_symbol,
        status=ReferenceDerivativesFetchStatus.COMPLETED,
        http_status_code=probe_result.status_code,
        response_payload_hash=response_payload_hash,
        response_row_count=response_row_count,
        rows=rows,
    )


def default_reference_derivatives_get_probe(url: str) -> ReferenceDerivativesGetResult:
    try:
        response = httpx.get(url, timeout=10.0)
    except httpx.HTTPError as exc:
        return ReferenceDerivativesGetResult(error=str(exc))
    try:
        payload = response.json()
    except ValueError:
        payload = None
    return ReferenceDerivativesGetResult(
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
        raise ValueError("missing reference-derivatives source entries: " + ",".join(missing))
    for source_id in source_ids:
        entry = entries[source_id]
        if source_id not in REFERENCE_DERIVATIVES_SOURCE_IDS:
            raise ValueError(f"unsupported reference-derivatives source_id: {source_id}")
        require_strict_zero_dollar_source(entry)
        if not entry.accepted_under_strict_free:
            raise ValueError(f"{source_id} is not accepted under strict-free mode")
        if entry.native_to_hyperliquid:
            raise ValueError(f"{source_id} must not be Hyperliquid-native")
        if entry.accepted_historical_coverage_proof:
            raise ValueError(f"{source_id} cannot be accepted historical coverage proof")
        if entry.research_role != "external_comparison":
            raise ValueError(f"{source_id} must remain external_comparison")
    return entries


def _validate_endpoint_ids(endpoint_ids: tuple[str, ...], source_ids: tuple[str, ...]) -> None:
    for endpoint_id in endpoint_ids:
        spec = reference_derivatives_endpoint_spec(endpoint_id)
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
    get_probe: ReferenceDerivativesGetProbe,
) -> tuple[ReferenceDerivativesAvailabilityRow, ...]:
    rows: list[ReferenceDerivativesAvailabilityRow] = []
    liquid_rows = [
        row
        for row in snapshot.symbol_map_rows
        if row.hyperliquid_liquid_as_of and row.above_day_notional_threshold
    ]
    for symbol_row in sorted(liquid_rows, key=lambda item: item.hyperliquid_coin):
        for endpoint_id in endpoint_ids:
            spec = reference_derivatives_endpoint_spec(endpoint_id)
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
                request = build_reference_derivatives_availability_request(
                    endpoint_id=endpoint_id,
                    symbol=venue_symbol,
                    day=day,
                )
                probe_result = _coerce_get_result(get_probe(request.request_url))
                status = _availability_status(spec=spec, result=probe_result)
                rows.append(
                    ReferenceDerivativesAvailabilityRow(
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
    spec: ReferenceDerivativesEndpointSpec,
) -> None:
    if spec.family not in entry.data_families:
        raise ValueError(f"{entry.source_id} is missing data family {spec.family}")
    if entry.venue != spec.venue:
        raise ValueError(f"{entry.source_id} venue does not match endpoint spec")
    if entry.market_type != spec.market_type:
        raise ValueError(f"{entry.source_id} market_type does not match endpoint spec")


def _fetch_result(
    *,
    spec: ReferenceDerivativesEndpointSpec,
    request: ReferenceDerivativesAvailabilityRequest,
    venue_symbol: str,
    status: ReferenceDerivativesFetchStatus,
    http_status_code: int | None = None,
    response_payload_hash: str | None = None,
    response_row_count: int | None = None,
    rows: tuple[ReferenceDerivativesNormalizedRow, ...] = (),
    blocked_reasons: tuple[str, ...] = (),
) -> ReferenceDerivativesFetchResult:
    fetch_id = reference_derivatives_fetch_id_for(
        source_id=spec.source_id,
        endpoint_id=spec.endpoint_id,
        request_url=request.request_url,
        status=status,
        response_payload_hash=response_payload_hash,
        row_hashes=tuple(row.row_hash for row in rows),
        blocked_reasons=blocked_reasons,
    )
    return ReferenceDerivativesFetchResult(
        fetch_id=fetch_id,
        source_id=spec.source_id,
        endpoint_id=spec.endpoint_id,
        venue=spec.venue,
        venue_symbol=venue_symbol,
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


def _normalize_payload(
    *,
    spec: ReferenceDerivativesEndpointSpec,
    request: ReferenceDerivativesAvailabilityRequest,
    result: ReferenceDerivativesGetResult,
) -> tuple[ReferenceDerivativesNormalizedRow, ...]:
    rows: list[ReferenceDerivativesNormalizedRow] = []
    for index, raw_row in enumerate(_raw_rows(spec=spec, result=result)):
        rows.append(
            _normalize_candle_row(
                spec=spec,
                request=request,
                raw_row=raw_row,
                row_index=index,
            )
        )
    return tuple(rows)


def _raw_rows(*, spec: ReferenceDerivativesEndpointSpec, result: ReferenceDerivativesGetResult) -> list[Any]:
    payload = result.payload
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, Mapping):
        raise ValueError(f"{spec.endpoint_id} payload must be an object or list")
    candles = payload.get("candles")
    if isinstance(candles, list):
        return candles
    data = payload.get("data")
    if isinstance(data, list):
        return data
    api_result = payload.get("result")
    if isinstance(api_result, Mapping):
        return _rows_from_columnar_data(api_result)
    raise ValueError(f"{spec.endpoint_id} payload is missing rows")


def _rows_from_columnar_data(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    columns = {str(key): value for key, value in data.items() if isinstance(value, list)}
    if not columns:
        return []
    row_count = max(len(value) for value in columns.values())
    rows: list[dict[str, Any]] = []
    for index in range(row_count):
        row: dict[str, Any] = {}
        for key, values in columns.items():
            if index < len(values):
                row[key] = values[index]
        rows.append(row)
    return rows


def _normalize_candle_row(
    *,
    spec: ReferenceDerivativesEndpointSpec,
    request: ReferenceDerivativesAvailabilityRequest,
    raw_row: Any,
    row_index: int,
) -> ReferenceDerivativesNormalizedRow:
    if not isinstance(raw_row, Mapping):
        raise ValueError(f"{spec.endpoint_id} candle row is malformed")
    raw_fields = _raw_fields_from_mapping(raw_row)
    timestamp_ms = _timestamp_ms_from_fields(spec, raw_fields)
    numeric_fields = {
        key: value
        for key, value in raw_fields.items()
        if key
        in {
            "open",
            "high",
            "low",
            "close",
            "volume",
            "cost",
            "baseTokenVolume",
            "base_token_volume",
            "quoteVolume",
            "quote_volume",
            "usdVolume",
            "usd_volume",
            "trades",
        }
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
    spec: ReferenceDerivativesEndpointSpec,
    request: ReferenceDerivativesAvailabilityRequest,
    row_index: int,
    timestamp_ms: int,
    numeric_fields: dict[str, str],
    raw_fields: dict[str, str],
) -> ReferenceDerivativesNormalizedRow:
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
    return ReferenceDerivativesNormalizedRow(
        **payload,
        row_hash=reference_derivatives_normalized_row_hash(payload),
    )


def _blocked_mapping_rows(
    *,
    snapshot: SymbolMapSnapshot,
    symbol_map_ref: str,
    source_entry: SourceRegistryEntry,
    spec: ReferenceDerivativesEndpointSpec,
    hyperliquid_coin: str,
    start_date: date,
    end_date: date,
    reason: str,
) -> list[ReferenceDerivativesAvailabilityRow]:
    return [
        ReferenceDerivativesAvailabilityRow(
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
            availability_status=ReferenceDerivativesAvailabilityStatus.BLOCKED_MAPPING,
            source_cost_class=source_entry.cost_class,
            blocked_reasons=(reason,),
        )
        for day in _date_range(start_date, end_date)
    ]


def _request_params_for_spec(
    *,
    spec: ReferenceDerivativesEndpointSpec,
    symbol: str,
    start_ms: int,
    end_ms: int,
) -> dict[str, str]:
    if spec.venue == "dydx":
        return {
            "resolution": spec.interval,
            "fromISO": _iso_from_ms(start_ms),
            "toISO": _iso_from_ms(end_ms),
            "limit": str(spec.limit),
        }
    return {
        "instrument_name": symbol,
        "start_timestamp": str(start_ms),
        "end_timestamp": str(end_ms),
        "resolution": spec.interval,
    }


def _availability_status(
    *,
    spec: ReferenceDerivativesEndpointSpec,
    result: ReferenceDerivativesGetResult,
) -> ReferenceDerivativesAvailabilityStatus:
    if result.error:
        return ReferenceDerivativesAvailabilityStatus.PROBE_ERROR
    if result.status_code == 404:
        return ReferenceDerivativesAvailabilityStatus.MISSING
    if result.status_code != 200:
        return ReferenceDerivativesAvailabilityStatus.PROBE_ERROR
    api_error = _api_error(spec=spec, result=result)
    if api_error:
        return ReferenceDerivativesAvailabilityStatus.PROBE_ERROR
    row_count = _response_row_count(result.payload)
    if row_count and row_count > 0:
        return ReferenceDerivativesAvailabilityStatus.AVAILABLE
    return ReferenceDerivativesAvailabilityStatus.MISSING


def _blocked_reasons_for_probe(
    *,
    spec: ReferenceDerivativesEndpointSpec,
    result: ReferenceDerivativesGetResult,
    status: ReferenceDerivativesAvailabilityStatus,
) -> tuple[str, ...]:
    if status in {
        ReferenceDerivativesAvailabilityStatus.AVAILABLE,
        ReferenceDerivativesAvailabilityStatus.MISSING,
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
    spec: ReferenceDerivativesEndpointSpec,
    result: ReferenceDerivativesGetResult,
) -> str | None:
    payload = result.payload
    if not isinstance(payload, Mapping):
        return None
    error = payload.get("error")
    if error:
        if isinstance(error, Mapping):
            code = error.get("code")
            message = error.get("message")
            return f"{spec.venue}_error:{code or message}"
        return f"{spec.venue}_error:{error}"
    errors = payload.get("errors")
    if errors:
        return f"{spec.venue}_errors"
    if spec.venue == "deribit":
        api_result = payload.get("result")
        if isinstance(api_result, Mapping):
            status = api_result.get("status")
            if status not in {None, "ok", "no_data"}:
                return f"deribit_status:{status}"
    return None


def _response_row_count(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    if not isinstance(payload, Mapping):
        return None
    candles = payload.get("candles")
    if isinstance(candles, list):
        return len(candles)
    data = payload.get("data")
    if isinstance(data, list):
        return len(data)
    if isinstance(data, Mapping):
        for value in data.values():
            if isinstance(value, list):
                return len(value)
    api_result = payload.get("result")
    if isinstance(api_result, Mapping):
        ticks = api_result.get("ticks")
        if isinstance(ticks, list):
            return len(ticks)
        if api_result.get("status") == "no_data":
            return 0
    return None


def _coerce_get_result(
    value: ReferenceDerivativesGetResult | Mapping[str, Any] | int,
) -> ReferenceDerivativesGetResult:
    if isinstance(value, ReferenceDerivativesGetResult):
        return value
    if isinstance(value, int):
        return ReferenceDerivativesGetResult(status_code=value)
    return ReferenceDerivativesGetResult.model_validate(dict(value))


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


def _normalize_symbol(symbol: str, venue: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError(f"unsupported {venue} symbol: {symbol!r}")
    allowed = normalized.replace("_", "").replace("-", "")
    if not allowed.isalnum():
        raise ValueError(f"unsupported {venue} symbol: {symbol!r}")
    return normalized


def _payload_hash(payload: Any) -> str | None:
    if payload is None:
        return None
    return canonical_json_hash(payload)


def _venue_symbol_from_request(
    request: ReferenceDerivativesAvailabilityRequest,
    spec: ReferenceDerivativesEndpointSpec,
) -> str:
    instrument = request.request_params.get("instrument_name")
    if instrument:
        return instrument
    if spec.venue == "dydx":
        return request.endpoint_path.rstrip("/").rsplit("/", 1)[-1]
    raise ValueError(f"{spec.endpoint_id} request is missing venue symbol")


def _timestamp_ms_from_fields(
    spec: ReferenceDerivativesEndpointSpec,
    raw_fields: Mapping[str, str],
) -> int:
    for key in ("startedAt", "started_at", "startsAt", "timestamp", "time", "ticks", "t"):
        value = raw_fields.get(key)
        if value is not None:
            return _parse_timestamp_ms(value, field_name=key)
    raise ValueError(f"{spec.endpoint_id} candle row is missing timestamp")


def _parse_timestamp_ms(value: str, *, field_name: str) -> int:
    raw = str(value).strip()
    if "T" in raw:
        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"invalid {field_name}: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return int(parsed.timestamp() * 1000)
    timestamp = _parse_int(raw, field_name=field_name)
    return timestamp if timestamp >= 10_000_000_000 else timestamp * 1000


def _raw_fields_from_mapping(row: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in sorted(row.items())
        if value is not None
    }


def _parse_int(value: str, *, field_name: str) -> int:
    try:
        parsed = int(str(value))
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"invalid {field_name}: {value!r}")
    return parsed


def _default_symbol_map_ref(snapshot: SymbolMapSnapshot) -> str:
    return f"manifests/symbol_maps/{snapshot.symbol_map_snapshot_id}.json"


def _count_status(
    rows: tuple[ReferenceDerivativesAvailabilityRow, ...],
    status: ReferenceDerivativesAvailabilityStatus,
) -> int:
    return sum(1 for row in rows if row.availability_status == status)


def _write_json_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
