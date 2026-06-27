# V2-AUDIT-ID: V2-AUD-DATASRC-060, V2-AUD-DATASRC-069
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md, docs/contracts/autonomous_readiness_contract.md
# V2-BOUNDARY: research_only, central_market_history_store, no_live_imports
# V2-OWNER: v2_data_sources
"""Central research-only market-history storage for strict-free provider data."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256, manifest_rows_hash
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY, V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_now
from tradingbotsuite.v2.security.boundary import require_research_boundary

CENTRAL_MARKET_HISTORY_SCHEMA_VERSION = "central_market_history_v1"
CENTRAL_MARKET_HISTORY_MANIFEST_TYPE = "central_market_history_batch_manifest"
CENTRAL_MARKET_HISTORY_DEFAULT_ROOT = Path("data/research/central_market_history")
OHLCV_EQUIVALENCE_TOLERANCE = 0.05
DEFAULT_COVERAGE_MIN = 0.98

_FORBIDDEN_SOURCE_ACCESS_TOKENS = (
    "paid",
    "requester_pays",
    "requester-pays",
    "synthetic",
    "fixture",
    "sandbox",
)


class CentralMarketHistoryFamily(str, Enum):
    OHLCV = "ohlcv"
    TRADE = "trade"
    ORDERFLOW = "orderflow"
    BOOK = "book"
    FUNDING = "funding"
    METADATA = "metadata"


class CentralMarketHistoryProviderStatus(str, Enum):
    EQUIVALENT_RESEARCH_DATA = "equivalent_research_data"
    PROVIDER_SPECIFIC_PASS = "provider_specific_pass"
    PROVIDER_SPECIFIC_DIVERGENT = "provider_specific_divergent"
    BLOCKED = "blocked"


class CentralMarketHistorySourceMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    provider: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_access_mode: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    official_public_source: bool = True
    authenticated_no_paid_source: bool = False
    local_existing_repo_ref: bool = False
    paid_required: bool = False
    requester_pays_required: bool = False
    synthetic: bool = False
    fixture_only: bool = False
    sandbox_only: bool = False
    supplied_ref: bool = False
    verifiable: bool = True
    raw_ref: str | None = None
    raw_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    notes: tuple[str, ...] = ()
    as_of: datetime = Field(default_factory=utc_now)
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

    @field_validator("provider", "source_id", "source_access_mode")
    @classmethod
    def _normalize_token(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("as_of")
    @classmethod
    def _utc_as_of(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_source(self) -> "CentralMarketHistorySourceMetadata":
        require_research_boundary(self, context="central market-history source metadata")
        blockers = central_market_history_source_blockers(self)
        if blockers:
            raise ValueError("central market-history source is not accepted evidence: " + ",".join(blockers))
        return self


class CentralMarketHistoryRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    provider: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_access_mode: str = Field(min_length=1)
    family: CentralMarketHistoryFamily
    normalized_symbol: str = Field(min_length=1)
    venue_symbol: str | None = None
    timeframe: str | None = None
    timestamp: datetime
    timestamp_ms: int = Field(ge=0)
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    quote_volume: float | None = None
    trade_count: float | None = None
    event_id: str | None = None
    numeric_fields: dict[str, float] = Field(default_factory=dict)
    raw_fields: dict[str, Any] = Field(default_factory=dict)
    provenance_refs: tuple[str, ...] = ()
    raw_ref: str | None = None
    raw_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    source_row_hash: str = Field(min_length=64, max_length=64)
    row_hash: str = Field(min_length=64, max_length=64)
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

    @field_validator("provider", "source_id", "source_access_mode")
    @classmethod
    def _normalize_provider_tokens(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("normalized_symbol")
    @classmethod
    def _normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("timeframe")
    @classmethod
    def _normalize_timeframe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("timestamp")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_row(self) -> "CentralMarketHistoryRow":
        require_research_boundary(self, context="central market-history row")
        if any(token in self.source_access_mode for token in _FORBIDDEN_SOURCE_ACCESS_TOKENS):
            raise ValueError("source_access_mode is not strict-free accepted evidence")
        if self.timestamp_ms != int(self.timestamp.timestamp() * 1000):
            raise ValueError("timestamp_ms must match timestamp")
        if self.family == CentralMarketHistoryFamily.OHLCV:
            missing = [
                name
                for name in ("timeframe", "open", "high", "low", "close", "volume")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError("OHLCV rows require " + ",".join(missing))
            assert self.open is not None
            assert self.high is not None
            assert self.low is not None
            assert self.close is not None
            assert self.volume is not None
            if self.high < max(self.open, self.close, self.low):
                raise ValueError("OHLCV high is below open/low/close")
            if self.low > min(self.open, self.close, self.high):
                raise ValueError("OHLCV low is above open/high/close")
            if self.volume < 0:
                raise ValueError("OHLCV volume must be non-negative")
        expected_source_hash = central_market_history_source_row_hash(
            _row_payload_for_hash(self.model_dump(mode="json"), include_source_hash=False)
        )
        if self.source_row_hash != expected_source_hash:
            raise ValueError("source_row_hash does not match row payload")
        expected_row_hash = central_market_history_row_hash(
            _row_payload_for_hash(self.model_dump(mode="json"), include_source_hash=True)
        )
        if self.row_hash != expected_row_hash:
            raise ValueError("row_hash does not match row payload")
        return self


class CentralMarketHistoryDuplicateGroup(BaseModel):
    model_config = ConfigDict(frozen=True)

    dedupe_key: str = Field(min_length=64, max_length=64)
    provider: str = Field(min_length=1)
    normalized_symbol: str = Field(min_length=1)
    timeframe: str | None = None
    family: str = Field(min_length=1)
    timestamp: datetime
    kept_row_hash: str = Field(min_length=64, max_length=64)
    duplicate_row_hashes: tuple[str, ...] = ()
    source_row_hashes: tuple[str, ...] = ()


class CentralMarketHistoryCoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    report_type: str = "central_market_history_coverage_report"
    coverage_report_id: str = Field(min_length=64, max_length=64)
    provider: str = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(min_length=1)
    normalized_symbol: str = Field(min_length=1)
    timeframe: str | None = None
    family: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    row_count: int = Field(ge=0)
    unique_timestamp_count: int = Field(ge=0)
    expected_timestamp_count: int = Field(ge=0)
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    coverage_min: float = Field(default=DEFAULT_COVERAGE_MIN, ge=0.0, le=1.0)
    nonempty: bool
    monotonic_timestamps: bool
    timestamp_sanity_pass: bool
    schema_valid: bool
    duplicate_count: int = Field(ge=0)
    quality_status: CentralMarketHistoryProviderStatus
    blocker_reasons: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
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

    @field_validator("start_ts", "end_ts", "created_at")
    @classmethod
    def _utc_dt(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_report(self) -> "CentralMarketHistoryCoverageReport":
        require_research_boundary(self, context="central market-history coverage report")
        if self.end_ts < self.start_ts:
            raise ValueError("coverage end_ts must not be before start_ts")
        if self.quality_status == CentralMarketHistoryProviderStatus.BLOCKED and not self.blocker_reasons:
            raise ValueError("blocked provider reports require blocker reasons")
        if self.quality_status != CentralMarketHistoryProviderStatus.BLOCKED and self.blocker_reasons:
            raise ValueError("passing provider reports cannot carry blocker reasons")
        expected_id = central_market_history_coverage_report_id_for(self)
        if self.coverage_report_id != expected_id:
            raise ValueError("coverage_report_id does not match report")
        return self


class CentralMarketHistoryComparisonReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    report_type: str = "central_market_history_ohlcv_comparison"
    comparison_report_id: str = Field(min_length=64, max_length=64)
    normalized_symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    provider_a: str = Field(min_length=1)
    provider_b: str = Field(min_length=1)
    overlap_rows: int = Field(ge=0)
    compared_price_field_count: int = Field(ge=0)
    max_abs_price_pct_diff: float | None = Field(default=None, ge=0.0)
    max_abs_volume_pct_diff: float | None = Field(default=None, ge=0.0)
    equivalence_tolerance: float = Field(default=OHLCV_EQUIVALENCE_TOLERANCE, ge=0.0)
    status: CentralMarketHistoryProviderStatus
    blocker_reasons: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
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
    def _validate_comparison(self) -> "CentralMarketHistoryComparisonReport":
        require_research_boundary(self, context="central market-history comparison report")
        if self.provider_a == self.provider_b:
            raise ValueError("comparison providers must differ")
        if self.status == CentralMarketHistoryProviderStatus.BLOCKED and not self.blocker_reasons:
            raise ValueError("blocked comparison reports require blocker reasons")
        expected_id = central_market_history_comparison_report_id_for(self)
        if self.comparison_report_id != expected_id:
            raise ValueError("comparison_report_id does not match report")
        return self


class CentralMarketHistoryQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    report_type: str = "central_market_history_quality_report"
    quality_report_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    row_count: int = Field(ge=0)
    provider_count: int = Field(ge=0)
    coverage_reports: tuple[CentralMarketHistoryCoverageReport, ...] = ()
    ohlcv_comparisons: tuple[CentralMarketHistoryComparisonReport, ...] = ()
    equivalent_ohlcv_pair_count: int = Field(ge=0)
    provider_specific_pair_count: int = Field(ge=0)
    blocked_provider_count: int = Field(ge=0)
    hyperliquid_rows_present: bool = False
    hyperliquid_missing_not_blocking: bool = True
    centralized_market_history_ready: bool = False
    readiness_role: str = "central_market_history_research_data_readiness"
    blocker_reasons: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
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
    def _validate_quality(self) -> "CentralMarketHistoryQualityReport":
        require_research_boundary(self, context="central market-history quality report")
        if self.centralized_market_history_ready and self.blocker_reasons:
            raise ValueError("ready market-history reports cannot carry blocker reasons")
        if not self.centralized_market_history_ready and not self.blocker_reasons:
            raise ValueError("blocked market-history reports require blocker reasons")
        expected_id = central_market_history_quality_report_id_for(self)
        if self.quality_report_id != expected_id:
            raise ValueError("quality_report_id does not match report")
        return self


class CentralMarketHistoryBatchManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = CENTRAL_MARKET_HISTORY_SCHEMA_VERSION
    manifest_type: str = CENTRAL_MARKET_HISTORY_MANIFEST_TYPE
    manifest_id: str = Field(min_length=64, max_length=64)
    run_id: str = Field(min_length=1)
    root_ref: str = Field(min_length=1)
    raw_ref: str = Field(min_length=1)
    raw_sha256: str = Field(min_length=64, max_length=64)
    normalized_ref: str = Field(min_length=1)
    normalized_sha256: str = Field(min_length=64, max_length=64)
    quality_report_ref: str = Field(min_length=1)
    quality_report_sha256: str = Field(min_length=64, max_length=64)
    source_metadata_refs: tuple[str, ...] = ()
    source_metadata_hash: str = Field(min_length=64, max_length=64)
    input_row_count: int = Field(ge=0)
    normalized_row_count: int = Field(ge=0)
    duplicate_row_count: int = Field(ge=0)
    dedupe_groups: tuple[CentralMarketHistoryDuplicateGroup, ...] = ()
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    append_only_manifest_ref: str = Field(min_length=1)
    as_of: datetime = Field(default_factory=utc_now)
    quality_report: CentralMarketHistoryQualityReport
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
    def _validate_manifest(self) -> "CentralMarketHistoryBatchManifest":
        require_research_boundary(self, context="central market-history batch manifest")
        if self.manifest_type != CENTRAL_MARKET_HISTORY_MANIFEST_TYPE:
            raise ValueError(f"manifest_type must be {CENTRAL_MARKET_HISTORY_MANIFEST_TYPE}")
        if self.normalized_row_count + self.duplicate_row_count != self.input_row_count:
            raise ValueError("normalized plus duplicate row counts must equal input rows")
        expected_id = central_market_history_manifest_id_for(self)
        if self.manifest_id != expected_id:
            raise ValueError("manifest_id does not match batch manifest")
        return self


class CentralMarketHistoryWriteResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_id: str = Field(min_length=64, max_length=64)
    manifest_ref: str = Field(min_length=1)
    manifest_sha256: str = Field(min_length=64, max_length=64)
    quality_report_id: str = Field(min_length=64, max_length=64)
    quality_report_ref: str = Field(min_length=1)
    normalized_ref: str = Field(min_length=1)
    row_count: int = Field(ge=0)
    duplicate_row_count: int = Field(ge=0)
    centralized_market_history_ready: bool
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
    def _validate_result(self) -> "CentralMarketHistoryWriteResult":
        require_research_boundary(self, context="central market-history write result")
        return self


def central_market_history_source_blockers(source: CentralMarketHistorySourceMetadata | Mapping[str, Any]) -> tuple[str, ...]:
    payload = source if isinstance(source, Mapping) else source.model_dump(mode="json")
    blockers: list[str] = []
    if payload.get("paid_required"):
        blockers.append("paid_source_excluded")
    if payload.get("requester_pays_required"):
        blockers.append("requester_pays_excluded")
    if payload.get("synthetic"):
        blockers.append("synthetic_source_excluded")
    if payload.get("fixture_only"):
        blockers.append("fixture_only_source_excluded")
    if payload.get("sandbox_only"):
        blockers.append("sandbox_only_source_excluded")
    if payload.get("supplied_ref"):
        blockers.append("supplied_ref_excluded")
    if not payload.get("verifiable", True):
        blockers.append("unverifiable_source_excluded")
    source_access_mode = str(payload.get("source_access_mode") or "").lower()
    for token in _FORBIDDEN_SOURCE_ACCESS_TOKENS:
        if token in source_access_mode:
            blockers.append(f"source_access_mode_{token}_excluded")
    if not (
        payload.get("official_public_source")
        or payload.get("authenticated_no_paid_source")
        or payload.get("local_existing_repo_ref")
    ):
        blockers.append("source_not_official_public_authenticated_free_or_existing_repo_ref")
    return tuple(dict.fromkeys(blockers))


def central_market_history_row_from_ohlcv(
    *,
    provider: str,
    source_id: str,
    source_access_mode: str,
    normalized_symbol: str,
    timestamp: datetime | int | float | str,
    timeframe: str,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    venue_symbol: str | None = None,
    quote_volume: float | None = None,
    trade_count: float | None = None,
    raw_fields: Mapping[str, Any] | None = None,
    provenance_refs: Sequence[str] = (),
    raw_ref: str | None = None,
    raw_sha256: str | None = None,
) -> CentralMarketHistoryRow:
    timestamp_dt = _coerce_timestamp(timestamp)
    provider = provider.strip().lower()
    source_id = source_id.strip().lower()
    source_access_mode = source_access_mode.strip().lower()
    normalized_symbol = normalized_symbol.strip().upper()
    timeframe = timeframe.strip()
    payload = {
        "provider": provider,
        "source_id": source_id,
        "source_access_mode": source_access_mode,
        "family": CentralMarketHistoryFamily.OHLCV,
        "normalized_symbol": normalized_symbol,
        "venue_symbol": venue_symbol,
        "timeframe": timeframe,
        "timestamp": timestamp_dt,
        "timestamp_ms": int(timestamp_dt.timestamp() * 1000),
        "open": float(open),
        "high": float(high),
        "low": float(low),
        "close": float(close),
        "volume": float(volume),
        "quote_volume": float(quote_volume) if quote_volume is not None else None,
        "trade_count": float(trade_count) if trade_count is not None else None,
        "raw_fields": dict(raw_fields or {}),
        "provenance_refs": tuple(provenance_refs),
        "raw_ref": raw_ref,
        "raw_sha256": raw_sha256,
    }
    source_hash = central_market_history_source_row_hash(
        _row_payload_for_hash(payload, include_source_hash=False)
    )
    row_hash = central_market_history_row_hash(
        {
            **_row_payload_for_hash(payload, include_source_hash=False),
            "source_row_hash": source_hash,
        }
    )
    return CentralMarketHistoryRow(**payload, source_row_hash=source_hash, row_hash=row_hash)


def central_market_history_row_from_event(
    *,
    provider: str,
    source_id: str,
    source_access_mode: str,
    family: CentralMarketHistoryFamily | str,
    normalized_symbol: str,
    timestamp: datetime | int | float | str,
    timeframe: str | None = None,
    venue_symbol: str | None = None,
    event_id: str | None = None,
    numeric_fields: Mapping[str, float] | None = None,
    raw_fields: Mapping[str, Any] | None = None,
    provenance_refs: Sequence[str] = (),
    raw_ref: str | None = None,
    raw_sha256: str | None = None,
) -> CentralMarketHistoryRow:
    family_value = CentralMarketHistoryFamily(family)
    if family_value == CentralMarketHistoryFamily.OHLCV:
        raise ValueError("use central_market_history_row_from_ohlcv for OHLCV rows")
    timestamp_dt = _coerce_timestamp(timestamp)
    provider = provider.strip().lower()
    source_id = source_id.strip().lower()
    source_access_mode = source_access_mode.strip().lower()
    normalized_symbol = normalized_symbol.strip().upper()
    timeframe = timeframe.strip() if timeframe is not None else None
    payload = {
        "provider": provider,
        "source_id": source_id,
        "source_access_mode": source_access_mode,
        "family": family_value,
        "normalized_symbol": normalized_symbol,
        "venue_symbol": venue_symbol,
        "timeframe": timeframe,
        "timestamp": timestamp_dt,
        "timestamp_ms": int(timestamp_dt.timestamp() * 1000),
        "event_id": event_id,
        "numeric_fields": dict(numeric_fields or {}),
        "raw_fields": dict(raw_fields or {}),
        "provenance_refs": tuple(provenance_refs),
        "raw_ref": raw_ref,
        "raw_sha256": raw_sha256,
    }
    source_hash = central_market_history_source_row_hash(
        _row_payload_for_hash(payload, include_source_hash=False)
    )
    row_hash = central_market_history_row_hash(
        {
            **_row_payload_for_hash(payload, include_source_hash=False),
            "source_row_hash": source_hash,
        }
    )
    return CentralMarketHistoryRow(**payload, source_row_hash=source_hash, row_hash=row_hash)


def central_market_history_rows_from_candle_records(
    rows: Iterable[Mapping[str, Any]],
    *,
    provider_field: str = "venue",
    source_id: str,
    source_access_mode: str = "zero_cost_public_api",
    symbol_field: str = "coin",
    venue_symbol_field: str = "venue_symbol",
    timeframe_field: str = "interval",
    timestamp_ms_field: str = "open_time_ms",
    provenance_ref: str,
    raw_sha256: str | None = None,
) -> tuple[CentralMarketHistoryRow, ...]:
    normalized: list[CentralMarketHistoryRow] = []
    for row in rows:
        normalized.append(
            central_market_history_row_from_ohlcv(
                provider=str(row[provider_field]),
                source_id=source_id,
                source_access_mode=source_access_mode,
                normalized_symbol=str(row[symbol_field]),
                venue_symbol=str(row.get(venue_symbol_field) or ""),
                timestamp=int(row[timestamp_ms_field]),
                timeframe=str(row[timeframe_field]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                quote_volume=_optional_float(row.get("quote_volume")),
                trade_count=_optional_float(row.get("trade_count")),
                raw_fields=dict(row),
                provenance_refs=(provenance_ref,),
                raw_ref=provenance_ref,
                raw_sha256=raw_sha256,
            )
        )
    return tuple(normalized)


def write_central_market_history_batch(
    *,
    root: str | Path,
    run_id: str,
    rows: Iterable[CentralMarketHistoryRow | Mapping[str, Any]],
    source_metadata: Iterable[CentralMarketHistorySourceMetadata | Mapping[str, Any]] = (),
    coverage_min: float = DEFAULT_COVERAGE_MIN,
    equivalence_tolerance: float = OHLCV_EQUIVALENCE_TOLERANCE,
) -> CentralMarketHistoryWriteResult:
    parsed_rows = tuple(_coerce_row(row) for row in rows)
    if not parsed_rows:
        raise ValueError("central market-history batch requires at least one row")
    parsed_sources = tuple(_coerce_source(source) for source in source_metadata)
    _validate_rows_have_source_metadata(parsed_rows, parsed_sources)

    root_path = Path(root).resolve(strict=False)
    raw_dir = root_path / "raw"
    normalized_dir = root_path / "normalized"
    manifest_dir = root_path / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    deduped_rows, duplicate_groups = dedupe_central_market_history_rows(parsed_rows)
    row_manifest_hash = central_market_history_rows_hash(deduped_rows)
    source_metadata_hash = central_market_history_source_metadata_hash(parsed_sources)
    batch_token = canonical_json_hash(
        {
            "run_id": run_id,
            "row_manifest_hash": row_manifest_hash,
            "source_metadata_hash": source_metadata_hash,
        }
    )[:16]

    raw_path = raw_dir / f"{run_id}-{batch_token}.jsonl"
    _write_jsonl(raw_path, [row.model_dump(mode="json") for row in parsed_rows])
    raw_sha = file_sha256(raw_path)

    normalized_path = normalized_dir / f"{run_id}-{batch_token}.parquet"
    _write_parquet(normalized_path, [row.model_dump(mode="json") for row in deduped_rows])
    normalized_sha = file_sha256(normalized_path)

    quality = build_central_market_history_quality_report(
        run_id=run_id,
        rows=deduped_rows,
        duplicate_groups=duplicate_groups,
        coverage_min=coverage_min,
        equivalence_tolerance=equivalence_tolerance,
    )
    quality_path = manifest_dir / f"{run_id}-{batch_token}-quality_report.json"
    _write_json(quality_path, quality.model_dump(mode="json"))
    quality_sha = file_sha256(quality_path)

    source_metadata_path = manifest_dir / f"{run_id}-{batch_token}-source_metadata.json"
    _write_json(
        source_metadata_path,
        {
            "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
            "manifest_type": "central_market_history_source_metadata",
            "source_metadata_hash": source_metadata_hash,
            "sources": [source.model_dump(mode="json") for source in parsed_sources],
            **RESEARCH_BOUNDARY,
        },
    )

    append_ref = "manifests/append_manifest.jsonl"
    partial = {
        "run_id": run_id,
        "root_ref": str(root_path),
        "raw_ref": _relative_ref(root_path, raw_path),
        "raw_sha256": raw_sha,
        "normalized_ref": _relative_ref(root_path, normalized_path),
        "normalized_sha256": normalized_sha,
        "quality_report_ref": _relative_ref(root_path, quality_path),
        "quality_report_sha256": quality_sha,
        "source_metadata_refs": (_relative_ref(root_path, source_metadata_path),),
        "source_metadata_hash": source_metadata_hash,
        "input_row_count": len(parsed_rows),
        "normalized_row_count": len(deduped_rows),
        "duplicate_row_count": len(parsed_rows) - len(deduped_rows),
        "dedupe_groups": duplicate_groups,
        "row_manifest_hash": row_manifest_hash,
        "append_only_manifest_ref": append_ref,
        "quality_report": quality,
    }
    manifest_id = central_market_history_manifest_id_from_payload(partial)
    manifest = CentralMarketHistoryBatchManifest(**partial, manifest_id=manifest_id)
    manifest_path = manifest_dir / f"{run_id}-{batch_token}-batch_manifest.json"
    _write_json(manifest_path, manifest.model_dump(mode="json"))
    manifest_sha = file_sha256(manifest_path)
    _append_jsonl(
        root_path / append_ref,
        {
            "manifest_id": manifest.manifest_id,
            "manifest_ref": _relative_ref(root_path, manifest_path),
            "manifest_sha256": manifest_sha,
            "run_id": run_id,
            "as_of": utc_now().isoformat(),
            **RESEARCH_BOUNDARY,
        },
    )
    return CentralMarketHistoryWriteResult(
        manifest_id=manifest.manifest_id,
        manifest_ref=_relative_ref(root_path, manifest_path),
        manifest_sha256=manifest_sha,
        quality_report_id=quality.quality_report_id,
        quality_report_ref=_relative_ref(root_path, quality_path),
        normalized_ref=_relative_ref(root_path, normalized_path),
        row_count=len(deduped_rows),
        duplicate_row_count=len(parsed_rows) - len(deduped_rows),
        centralized_market_history_ready=quality.centralized_market_history_ready,
    )


def write_central_market_history_ohlcv_payload_batch(
    *,
    root: str | Path,
    run_id: str,
    rows: Iterable[Mapping[str, Any]],
    source_metadata: Iterable[CentralMarketHistorySourceMetadata | Mapping[str, Any]],
    raw_source_index: Mapping[str, Any] | None = None,
    coverage_min: float = DEFAULT_COVERAGE_MIN,
    append_to_manifest: bool = True,
) -> CentralMarketHistoryWriteResult:
    """Write large provider-specific OHLCV batches without per-row Pydantic coercion."""

    parsed_rows = tuple(_coerce_fast_ohlcv_payload(row) for row in rows)
    if not parsed_rows:
        raise ValueError("central market-history OHLCV payload batch requires at least one row")
    providers = {row["provider"] for row in parsed_rows}
    if len(providers) != 1:
        raise ValueError("fast OHLCV payload batches are provider-specific")
    parsed_sources = tuple(_coerce_source(source) for source in source_metadata)
    if not parsed_sources:
        raise ValueError("fast OHLCV payload batches require source metadata")
    _validate_payloads_have_source_metadata(parsed_rows, parsed_sources)

    root_path = Path(root).resolve(strict=False)
    raw_dir = root_path / "raw"
    normalized_dir = root_path / "normalized"
    manifest_dir = root_path / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    deduped_rows, duplicate_groups = _dedupe_central_market_history_payloads(parsed_rows)
    row_manifest_hash = manifest_rows_hash(deduped_rows)
    source_metadata_hash = central_market_history_source_metadata_hash(parsed_sources)
    batch_token = canonical_json_hash(
        {
            "run_id": run_id,
            "row_manifest_hash": row_manifest_hash,
            "source_metadata_hash": source_metadata_hash,
            "writer": "fast_ohlcv_payload_batch_v1",
        }
    )[:16]

    raw_index_payload = {
        "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
        "manifest_type": "central_market_history_raw_source_index",
        "raw_index_role": "compact_source_archive_index_for_fast_ohlcv_writer",
        "run_id": run_id,
        "input_row_count": len(parsed_rows),
        "normalized_row_count": len(deduped_rows),
        "duplicate_row_count": len(parsed_rows) - len(deduped_rows),
        "row_manifest_hash": row_manifest_hash,
        "source_metadata_hash": source_metadata_hash,
        "raw_sources": _raw_sources_from_payloads(parsed_rows),
        "source_metadata": [source.model_dump(mode="json") for source in parsed_sources],
        "writer": "fast_ohlcv_payload_batch_v1",
        **dict(raw_source_index or {}),
        **RESEARCH_BOUNDARY,
    }
    raw_path = raw_dir / f"{run_id}-{batch_token}-raw_sources.json"
    _write_json_atomic(raw_path, raw_index_payload)
    raw_sha = file_sha256(raw_path)

    normalized_path = normalized_dir / f"{run_id}-{batch_token}.parquet"
    _write_parquet_atomic(normalized_path, deduped_rows)
    normalized_sha = file_sha256(normalized_path)

    quality = _build_ohlcv_payload_quality_report(
        run_id=run_id,
        rows=deduped_rows,
        duplicate_groups=duplicate_groups,
        coverage_min=coverage_min,
    )
    quality_path = manifest_dir / f"{run_id}-{batch_token}-quality_report.json"
    _write_json_atomic(quality_path, quality.model_dump(mode="json"))
    quality_sha = file_sha256(quality_path)

    source_metadata_path = manifest_dir / f"{run_id}-{batch_token}-source_metadata.json"
    _write_json_atomic(
        source_metadata_path,
        {
            "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
            "manifest_type": "central_market_history_source_metadata",
            "source_metadata_hash": source_metadata_hash,
            "sources": [source.model_dump(mode="json") for source in parsed_sources],
            **RESEARCH_BOUNDARY,
        },
    )

    append_ref = "manifests/append_manifest.jsonl"
    partial = {
        "run_id": run_id,
        "root_ref": str(root_path),
        "raw_ref": _relative_ref(root_path, raw_path),
        "raw_sha256": raw_sha,
        "normalized_ref": _relative_ref(root_path, normalized_path),
        "normalized_sha256": normalized_sha,
        "quality_report_ref": _relative_ref(root_path, quality_path),
        "quality_report_sha256": quality_sha,
        "source_metadata_refs": (_relative_ref(root_path, source_metadata_path),),
        "source_metadata_hash": source_metadata_hash,
        "input_row_count": len(parsed_rows),
        "normalized_row_count": len(deduped_rows),
        "duplicate_row_count": len(parsed_rows) - len(deduped_rows),
        "dedupe_groups": duplicate_groups,
        "row_manifest_hash": row_manifest_hash,
        "append_only_manifest_ref": append_ref,
        "quality_report": quality,
    }
    manifest_id = central_market_history_manifest_id_from_payload(partial)
    manifest = CentralMarketHistoryBatchManifest(**partial, manifest_id=manifest_id)
    manifest_path = manifest_dir / f"{run_id}-{batch_token}-batch_manifest.json"
    _write_json_atomic(manifest_path, manifest.model_dump(mode="json"))
    manifest_sha = file_sha256(manifest_path)
    manifest_ref = _relative_ref(root_path, manifest_path)
    if append_to_manifest:
        append_central_market_history_manifest_entry(
            root=root_path,
            run_id=run_id,
            manifest_ref=manifest_ref,
            manifest_sha256=manifest_sha,
            writer="fast_ohlcv_payload_batch_v1",
        )
    return CentralMarketHistoryWriteResult(
        manifest_id=manifest.manifest_id,
        manifest_ref=manifest_ref,
        manifest_sha256=manifest_sha,
        quality_report_id=quality.quality_report_id,
        quality_report_ref=_relative_ref(root_path, quality_path),
        normalized_ref=_relative_ref(root_path, normalized_path),
        row_count=len(deduped_rows),
        duplicate_row_count=len(parsed_rows) - len(deduped_rows),
        centralized_market_history_ready=quality.centralized_market_history_ready,
    )


def write_central_market_history_event_payload_batch(
    *,
    root: str | Path,
    run_id: str,
    rows: Iterable[Mapping[str, Any] | CentralMarketHistoryRow],
    source_metadata: Iterable[CentralMarketHistorySourceMetadata | Mapping[str, Any]],
    raw_source_index: Mapping[str, Any] | None = None,
    coverage_min: float = DEFAULT_COVERAGE_MIN,
    append_to_manifest: bool = True,
) -> CentralMarketHistoryWriteResult:
    """Write large provider event/book batches without per-row Pydantic coercion."""

    parsed_rows = tuple(_coerce_fast_event_payload(row) for row in rows)
    if not parsed_rows:
        raise ValueError("central market-history event payload batch requires at least one row")
    parsed_sources = tuple(_coerce_source(source) for source in source_metadata)
    if not parsed_sources:
        raise ValueError("fast event payload batches require source metadata")
    _validate_payloads_have_source_metadata(parsed_rows, parsed_sources)

    root_path = Path(root).resolve(strict=False)
    raw_dir = root_path / "raw"
    normalized_dir = root_path / "normalized"
    manifest_dir = root_path / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    deduped_rows, duplicate_groups = _dedupe_central_market_history_payloads(parsed_rows)
    row_manifest_hash = manifest_rows_hash(deduped_rows)
    source_metadata_hash = central_market_history_source_metadata_hash(parsed_sources)
    batch_token = canonical_json_hash(
        {
            "run_id": run_id,
            "row_manifest_hash": row_manifest_hash,
            "source_metadata_hash": source_metadata_hash,
            "writer": "fast_event_payload_batch_v1",
        }
    )[:16]

    raw_index_payload = {
        "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
        "manifest_type": "central_market_history_raw_source_index",
        "raw_index_role": "compact_source_archive_index_for_fast_event_writer",
        "run_id": run_id,
        "input_row_count": len(parsed_rows),
        "normalized_row_count": len(deduped_rows),
        "duplicate_row_count": len(parsed_rows) - len(deduped_rows),
        "row_manifest_hash": row_manifest_hash,
        "source_metadata_hash": source_metadata_hash,
        "raw_sources": _raw_sources_from_payloads(parsed_rows),
        "source_metadata": [source.model_dump(mode="json") for source in parsed_sources],
        "writer": "fast_event_payload_batch_v1",
        **dict(raw_source_index or {}),
        **RESEARCH_BOUNDARY,
    }
    raw_path = raw_dir / f"{run_id}-{batch_token}-raw_sources.json"
    _write_json_atomic(raw_path, raw_index_payload)
    raw_sha = file_sha256(raw_path)

    normalized_path = normalized_dir / f"{run_id}-{batch_token}.parquet"
    _write_parquet_atomic(normalized_path, deduped_rows)
    normalized_sha = file_sha256(normalized_path)

    quality = _build_payload_quality_report(
        run_id=run_id,
        rows=deduped_rows,
        duplicate_groups=duplicate_groups,
        coverage_min=coverage_min,
    )
    quality_path = manifest_dir / f"{run_id}-{batch_token}-quality_report.json"
    _write_json_atomic(quality_path, quality.model_dump(mode="json"))
    quality_sha = file_sha256(quality_path)

    source_metadata_path = manifest_dir / f"{run_id}-{batch_token}-source_metadata.json"
    _write_json_atomic(
        source_metadata_path,
        {
            "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
            "manifest_type": "central_market_history_source_metadata",
            "source_metadata_hash": source_metadata_hash,
            "sources": [source.model_dump(mode="json") for source in parsed_sources],
            **RESEARCH_BOUNDARY,
        },
    )

    append_ref = "manifests/append_manifest.jsonl"
    partial = {
        "run_id": run_id,
        "root_ref": str(root_path),
        "raw_ref": _relative_ref(root_path, raw_path),
        "raw_sha256": raw_sha,
        "normalized_ref": _relative_ref(root_path, normalized_path),
        "normalized_sha256": normalized_sha,
        "quality_report_ref": _relative_ref(root_path, quality_path),
        "quality_report_sha256": quality_sha,
        "source_metadata_refs": (_relative_ref(root_path, source_metadata_path),),
        "source_metadata_hash": source_metadata_hash,
        "input_row_count": len(parsed_rows),
        "normalized_row_count": len(deduped_rows),
        "duplicate_row_count": len(parsed_rows) - len(deduped_rows),
        "dedupe_groups": duplicate_groups,
        "row_manifest_hash": row_manifest_hash,
        "append_only_manifest_ref": append_ref,
        "quality_report": quality,
    }
    manifest_id = central_market_history_manifest_id_from_payload(partial)
    manifest = CentralMarketHistoryBatchManifest(**partial, manifest_id=manifest_id)
    manifest_path = manifest_dir / f"{run_id}-{batch_token}-batch_manifest.json"
    _write_json_atomic(manifest_path, manifest.model_dump(mode="json"))
    manifest_sha = file_sha256(manifest_path)
    manifest_ref = _relative_ref(root_path, manifest_path)
    if append_to_manifest:
        append_central_market_history_manifest_entry(
            root=root_path,
            run_id=run_id,
            manifest_ref=manifest_ref,
            manifest_sha256=manifest_sha,
            writer="fast_event_payload_batch_v1",
        )
    return CentralMarketHistoryWriteResult(
        manifest_id=manifest.manifest_id,
        manifest_ref=manifest_ref,
        manifest_sha256=manifest_sha,
        quality_report_id=quality.quality_report_id,
        quality_report_ref=_relative_ref(root_path, quality_path),
        normalized_ref=_relative_ref(root_path, normalized_path),
        row_count=len(deduped_rows),
        duplicate_row_count=len(parsed_rows) - len(deduped_rows),
        centralized_market_history_ready=quality.centralized_market_history_ready,
    )


def append_central_market_history_manifest_entry(
    *,
    root: str | Path,
    run_id: str,
    manifest_ref: str,
    manifest_sha256: str,
    writer: str = "fast_ohlcv_payload_batch_v1",
) -> None:
    """Verify and append a completed batch manifest to the central append log."""

    root_path = Path(root).resolve(strict=False)
    normalized_manifest_ref = manifest_ref.replace("\\", "/")
    if Path(normalized_manifest_ref).is_absolute():
        raise ValueError("central market-history manifest_ref must be relative to root")
    manifest_path = root_path.joinpath(*normalized_manifest_ref.split("/"))
    if not manifest_path.exists():
        raise FileNotFoundError(f"central market-history manifest not found: {manifest_path}")
    actual_sha = file_sha256(manifest_path)
    if actual_sha != manifest_sha256:
        raise ValueError("central market-history manifest SHA mismatch")
    manifest = CentralMarketHistoryBatchManifest.model_validate(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    if manifest.run_id != run_id:
        raise ValueError("central market-history manifest run_id mismatch")

    append_path = root_path / "manifests" / "append_manifest.jsonl"
    if append_path.exists():
        with append_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                existing = json.loads(line)
                if existing.get("run_id") != run_id:
                    continue
                if (
                    existing.get("manifest_id") == manifest.manifest_id
                    and existing.get("manifest_ref") == normalized_manifest_ref
                    and existing.get("manifest_sha256") == manifest_sha256
                ):
                    return
                raise FileExistsError(
                    "central market-history append manifest already has a different entry "
                    f"for run_id={run_id}"
                )

    _append_jsonl(
        append_path,
        {
            "manifest_id": manifest.manifest_id,
            "manifest_ref": normalized_manifest_ref,
            "manifest_sha256": manifest_sha256,
            "run_id": run_id,
            "as_of": utc_now().isoformat(),
            "writer": writer,
            **RESEARCH_BOUNDARY,
        },
    )


def dedupe_central_market_history_rows(
    rows: Iterable[CentralMarketHistoryRow],
) -> tuple[tuple[CentralMarketHistoryRow, ...], tuple[CentralMarketHistoryDuplicateGroup, ...]]:
    groups: dict[str, list[CentralMarketHistoryRow]] = defaultdict(list)
    for row in rows:
        groups[central_market_history_dedupe_key(row)].append(row)
    deduped: list[CentralMarketHistoryRow] = []
    duplicate_groups: list[CentralMarketHistoryDuplicateGroup] = []
    for key, group_rows in groups.items():
        ordered = sorted(group_rows, key=lambda item: (item.row_hash, item.source_row_hash))
        kept = ordered[0]
        deduped.append(kept)
        if len(ordered) > 1:
            duplicate_groups.append(
                CentralMarketHistoryDuplicateGroup(
                    dedupe_key=key,
                    provider=kept.provider,
                    normalized_symbol=kept.normalized_symbol,
                    timeframe=kept.timeframe,
                    family=kept.family.value,
                    timestamp=kept.timestamp,
                    kept_row_hash=kept.row_hash,
                    duplicate_row_hashes=tuple(row.row_hash for row in ordered[1:]),
                    source_row_hashes=tuple(row.source_row_hash for row in ordered),
                )
            )
    return (
        tuple(sorted(deduped, key=lambda item: (item.provider, item.normalized_symbol, item.timeframe or "", item.family.value, item.timestamp_ms, item.row_hash))),
        tuple(sorted(duplicate_groups, key=lambda item: item.dedupe_key)),
    )


def build_central_market_history_quality_report(
    *,
    run_id: str,
    rows: Sequence[CentralMarketHistoryRow],
    duplicate_groups: Sequence[CentralMarketHistoryDuplicateGroup] = (),
    coverage_min: float = DEFAULT_COVERAGE_MIN,
    equivalence_tolerance: float = OHLCV_EQUIVALENCE_TOLERANCE,
) -> CentralMarketHistoryQualityReport:
    coverage_reports = _coverage_reports_for_rows(
        rows=tuple(rows),
        duplicate_groups=tuple(duplicate_groups),
        coverage_min=coverage_min,
    )
    comparisons = _ohlcv_comparisons(
        tuple(rows),
        equivalence_tolerance=equivalence_tolerance,
    )
    blocked_provider_count = sum(
        1
        for report in coverage_reports
        if report.quality_status == CentralMarketHistoryProviderStatus.BLOCKED
    )
    ready = any(
        report.quality_status != CentralMarketHistoryProviderStatus.BLOCKED
        for report in coverage_reports
    )
    blockers: tuple[str, ...] = () if ready else ("no_usable_market_history_rows",)
    partial = {
        "run_id": run_id,
        "row_count": len(rows),
        "provider_count": len({row.provider for row in rows}),
        "coverage_reports": coverage_reports,
        "ohlcv_comparisons": comparisons,
        "equivalent_ohlcv_pair_count": sum(
            1
            for comparison in comparisons
            if comparison.status == CentralMarketHistoryProviderStatus.EQUIVALENT_RESEARCH_DATA
        ),
        "provider_specific_pair_count": sum(
            1
            for comparison in comparisons
            if comparison.status
            in {
                CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_PASS,
                CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_DIVERGENT,
            }
        ),
        "blocked_provider_count": blocked_provider_count,
        "hyperliquid_rows_present": any(row.provider == "hyperliquid" for row in rows),
        "hyperliquid_missing_not_blocking": True,
        "centralized_market_history_ready": ready,
        "blocker_reasons": blockers,
    }
    return CentralMarketHistoryQualityReport(
        **partial,
        quality_report_id=central_market_history_quality_report_id_from_payload(partial),
    )


def central_market_history_dedupe_key(row: CentralMarketHistoryRow) -> str:
    payload: dict[str, Any] = {
        "provider": row.provider,
        "normalized_symbol": row.normalized_symbol,
        "timeframe": row.timeframe,
        "timestamp_ms": row.timestamp_ms,
    }
    if row.family != CentralMarketHistoryFamily.OHLCV:
        payload.update(
            {
                "family": row.family.value,
                "event_id": row.event_id,
                "source_row_hash": row.source_row_hash,
            }
        )
    return canonical_json_hash(payload)


def central_market_history_source_row_hash(payload: Mapping[str, Any]) -> str:
    return canonical_json_hash({"row_type": "central_market_history_source_row", "payload": _json_ready(payload)})


def central_market_history_row_hash(payload: Mapping[str, Any]) -> str:
    return canonical_json_hash({"row_type": "central_market_history_row", "payload": _json_ready(payload)})


def central_market_history_rows_hash(rows: Sequence[CentralMarketHistoryRow]) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def central_market_history_source_metadata_hash(
    sources: Sequence[CentralMarketHistorySourceMetadata],
) -> str:
    return manifest_rows_hash(source.model_dump(mode="json") for source in sources)


def central_market_history_coverage_report_id_for(report: CentralMarketHistoryCoverageReport) -> str:
    return _central_market_history_coverage_report_id_from_payload(
        {
            "report_type": report.report_type,
            "provider": report.provider,
            "source_ids": report.source_ids,
            "normalized_symbol": report.normalized_symbol,
            "timeframe": report.timeframe,
            "family": report.family,
            "start_ts": report.start_ts.isoformat(),
            "end_ts": report.end_ts.isoformat(),
            "row_count": report.row_count,
            "unique_timestamp_count": report.unique_timestamp_count,
            "expected_timestamp_count": report.expected_timestamp_count,
            "coverage_ratio": report.coverage_ratio,
            "coverage_min": report.coverage_min,
            "nonempty": report.nonempty,
            "monotonic_timestamps": report.monotonic_timestamps,
            "timestamp_sanity_pass": report.timestamp_sanity_pass,
            "schema_valid": report.schema_valid,
            "duplicate_count": report.duplicate_count,
            "quality_status": report.quality_status.value,
            "blocker_reasons": report.blocker_reasons,
        }
    )


def _central_market_history_coverage_report_id_from_payload(payload: Mapping[str, Any]) -> str:
    status = payload["quality_status"]
    status_value = status.value if isinstance(status, CentralMarketHistoryProviderStatus) else str(status)
    return canonical_json_hash(
        {
            "report_type": payload.get("report_type", "central_market_history_coverage_report"),
            "provider": payload["provider"],
            "source_ids": tuple(payload["source_ids"]),
            "normalized_symbol": payload["normalized_symbol"],
            "timeframe": payload.get("timeframe"),
            "family": payload["family"],
            "start_ts": _coerce_timestamp(payload["start_ts"]).isoformat(),
            "end_ts": _coerce_timestamp(payload["end_ts"]).isoformat(),
            "row_count": payload["row_count"],
            "unique_timestamp_count": payload["unique_timestamp_count"],
            "expected_timestamp_count": payload["expected_timestamp_count"],
            "coverage_ratio": payload["coverage_ratio"],
            "coverage_min": payload["coverage_min"],
            "nonempty": payload["nonempty"],
            "monotonic_timestamps": payload["monotonic_timestamps"],
            "timestamp_sanity_pass": payload["timestamp_sanity_pass"],
            "schema_valid": payload["schema_valid"],
            "duplicate_count": payload["duplicate_count"],
            "quality_status": status_value,
            "blocker_reasons": tuple(payload.get("blocker_reasons", ())),
        }
    )


def central_market_history_comparison_report_id_for(report: CentralMarketHistoryComparisonReport) -> str:
    return canonical_json_hash(
        {
            "report_type": report.report_type,
            "normalized_symbol": report.normalized_symbol,
            "timeframe": report.timeframe,
            "provider_a": report.provider_a,
            "provider_b": report.provider_b,
            "overlap_rows": report.overlap_rows,
            "compared_price_field_count": report.compared_price_field_count,
            "max_abs_price_pct_diff": report.max_abs_price_pct_diff,
            "max_abs_volume_pct_diff": report.max_abs_volume_pct_diff,
            "equivalence_tolerance": report.equivalence_tolerance,
            "status": report.status.value,
            "blocker_reasons": report.blocker_reasons,
        }
    )


def central_market_history_quality_report_id_for(report: CentralMarketHistoryQualityReport) -> str:
    return central_market_history_quality_report_id_from_payload(
        {
            "run_id": report.run_id,
            "row_count": report.row_count,
            "provider_count": report.provider_count,
            "coverage_report_ids": tuple(item.coverage_report_id for item in report.coverage_reports),
            "comparison_report_ids": tuple(item.comparison_report_id for item in report.ohlcv_comparisons),
            "equivalent_ohlcv_pair_count": report.equivalent_ohlcv_pair_count,
            "provider_specific_pair_count": report.provider_specific_pair_count,
            "blocked_provider_count": report.blocked_provider_count,
            "hyperliquid_rows_present": report.hyperliquid_rows_present,
            "hyperliquid_missing_not_blocking": report.hyperliquid_missing_not_blocking,
            "centralized_market_history_ready": report.centralized_market_history_ready,
            "blocker_reasons": report.blocker_reasons,
        }
    )


def central_market_history_quality_report_id_from_payload(payload: Mapping[str, Any]) -> str:
    return canonical_json_hash(
        {
            "report_type": "central_market_history_quality_report",
            "run_id": payload["run_id"],
            "row_count": payload["row_count"],
            "provider_count": payload["provider_count"],
            "coverage_report_ids": tuple(
                item.coverage_report_id if isinstance(item, CentralMarketHistoryCoverageReport) else item
                for item in payload.get("coverage_reports", payload.get("coverage_report_ids", ()))
            ),
            "comparison_report_ids": tuple(
                item.comparison_report_id if isinstance(item, CentralMarketHistoryComparisonReport) else item
                for item in payload.get("ohlcv_comparisons", payload.get("comparison_report_ids", ()))
            ),
            "equivalent_ohlcv_pair_count": payload["equivalent_ohlcv_pair_count"],
            "provider_specific_pair_count": payload["provider_specific_pair_count"],
            "blocked_provider_count": payload["blocked_provider_count"],
            "hyperliquid_rows_present": payload["hyperliquid_rows_present"],
            "hyperliquid_missing_not_blocking": payload["hyperliquid_missing_not_blocking"],
            "centralized_market_history_ready": payload["centralized_market_history_ready"],
            "blocker_reasons": tuple(payload.get("blocker_reasons", ())),
        }
    )


def central_market_history_manifest_id_for(manifest: CentralMarketHistoryBatchManifest) -> str:
    return central_market_history_manifest_id_from_payload(
        manifest.model_dump(
            mode="json",
            exclude={"manifest_id", "as_of"},
        )
    )


def central_market_history_manifest_id_from_payload(payload: Mapping[str, Any]) -> str:
    return canonical_json_hash(
        {
            "manifest_type": CENTRAL_MARKET_HISTORY_MANIFEST_TYPE,
            "run_id": payload["run_id"],
            "raw_sha256": payload["raw_sha256"],
            "normalized_sha256": payload["normalized_sha256"],
            "quality_report_sha256": payload["quality_report_sha256"],
            "source_metadata_hash": payload["source_metadata_hash"],
            "input_row_count": payload["input_row_count"],
            "normalized_row_count": payload["normalized_row_count"],
            "duplicate_row_count": payload["duplicate_row_count"],
            "row_manifest_hash": payload["row_manifest_hash"],
            "quality_report_id": (
                payload["quality_report"].quality_report_id
                if isinstance(payload["quality_report"], CentralMarketHistoryQualityReport)
                else payload["quality_report"]["quality_report_id"]
            ),
        }
    )


def _coverage_reports_for_rows(
    *,
    rows: tuple[CentralMarketHistoryRow, ...],
    duplicate_groups: tuple[CentralMarketHistoryDuplicateGroup, ...],
    coverage_min: float,
) -> tuple[CentralMarketHistoryCoverageReport, ...]:
    by_group: dict[tuple[str, str, str | None, str], list[CentralMarketHistoryRow]] = defaultdict(list)
    for row in rows:
        by_group[(row.provider, row.normalized_symbol, row.timeframe, row.family.value)].append(row)
    duplicate_counts: dict[tuple[str, str, str | None, str], int] = defaultdict(int)
    for group in duplicate_groups:
        duplicate_counts[(group.provider, group.normalized_symbol, group.timeframe, group.family)] += len(
            group.duplicate_row_hashes
        )
    reports: list[CentralMarketHistoryCoverageReport] = []
    for (provider, symbol, timeframe, family), group_rows in by_group.items():
        timestamps = [row.timestamp for row in sorted(group_rows, key=lambda item: item.timestamp_ms)]
        unique_timestamp_count = len({row.timestamp_ms for row in group_rows})
        start_ts = timestamps[0]
        end_ts = timestamps[-1]
        expected_count = _expected_timestamp_count(start_ts, end_ts, timeframe, family)
        coverage_ratio = min(1.0, unique_timestamp_count / expected_count) if expected_count else 1.0
        nonempty = bool(group_rows)
        monotonic = [row.timestamp_ms for row in group_rows] == sorted(row.timestamp_ms for row in group_rows)
        timestamp_sanity = all(row.timestamp.tzinfo is not None and row.timestamp.tzinfo.utcoffset(row.timestamp) is not None for row in group_rows)
        schema_valid = all(_row_schema_quality_ok(row) for row in group_rows)
        blockers: list[str] = []
        if not nonempty:
            blockers.append("empty_rows")
        if not monotonic:
            blockers.append("non_monotonic_timestamps")
        if not timestamp_sanity:
            blockers.append("timestamp_sanity_failed")
        if not schema_valid:
            blockers.append("schema_invalid")
        if family == CentralMarketHistoryFamily.OHLCV.value and coverage_ratio < coverage_min:
            blockers.append("coverage_below_min")
        status = (
            CentralMarketHistoryProviderStatus.BLOCKED
            if blockers
            else CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_PASS
        )
        partial = {
            "provider": provider,
            "source_ids": tuple(sorted({row.source_id for row in group_rows})),
            "normalized_symbol": symbol,
            "timeframe": timeframe,
            "family": family,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "row_count": len(group_rows),
            "unique_timestamp_count": unique_timestamp_count,
            "expected_timestamp_count": expected_count,
            "coverage_ratio": coverage_ratio,
            "coverage_min": coverage_min,
            "nonempty": nonempty,
            "monotonic_timestamps": monotonic,
            "timestamp_sanity_pass": timestamp_sanity,
            "schema_valid": schema_valid,
            "duplicate_count": duplicate_counts[(provider, symbol, timeframe, family)],
            "quality_status": status,
            "blocker_reasons": tuple(blockers),
        }
        reports.append(
            CentralMarketHistoryCoverageReport(
                **partial,
                coverage_report_id=canonical_json_hash(
                    {
                        "report_type": "central_market_history_coverage_report",
                        "provider": provider,
                        "source_ids": partial["source_ids"],
                        "normalized_symbol": symbol,
                        "timeframe": timeframe,
                        "family": family,
                        "start_ts": start_ts.isoformat(),
                        "end_ts": end_ts.isoformat(),
                        "row_count": len(group_rows),
                        "unique_timestamp_count": unique_timestamp_count,
                        "expected_timestamp_count": expected_count,
                        "coverage_ratio": coverage_ratio,
                        "coverage_min": coverage_min,
                        "nonempty": nonempty,
                        "monotonic_timestamps": monotonic,
                        "timestamp_sanity_pass": timestamp_sanity,
                        "schema_valid": schema_valid,
                        "duplicate_count": duplicate_counts[(provider, symbol, timeframe, family)],
                        "quality_status": status.value,
                        "blocker_reasons": tuple(blockers),
                    }
                ),
            )
        )
    return tuple(sorted(reports, key=lambda item: (item.provider, item.normalized_symbol, item.timeframe or "", item.family)))


def _ohlcv_comparisons(
    rows: tuple[CentralMarketHistoryRow, ...],
    *,
    equivalence_tolerance: float,
) -> tuple[CentralMarketHistoryComparisonReport, ...]:
    grouped: dict[tuple[str, str], dict[str, dict[int, CentralMarketHistoryRow]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        if row.family != CentralMarketHistoryFamily.OHLCV or row.timeframe is None:
            continue
        grouped[(row.normalized_symbol, row.timeframe)][row.provider][row.timestamp_ms] = row
    reports: list[CentralMarketHistoryComparisonReport] = []
    for (symbol, timeframe), providers in grouped.items():
        provider_names = sorted(providers)
        for index, provider_a in enumerate(provider_names):
            for provider_b in provider_names[index + 1 :]:
                rows_a = providers[provider_a]
                rows_b = providers[provider_b]
                overlap = sorted(set(rows_a) & set(rows_b))
                price_diffs: list[float] = []
                volume_diffs: list[float] = []
                for timestamp_ms in overlap:
                    a = rows_a[timestamp_ms]
                    b = rows_b[timestamp_ms]
                    for field in ("open", "high", "low", "close"):
                        diff = _pct_diff(getattr(a, field), getattr(b, field))
                        if diff is not None:
                            price_diffs.append(diff)
                    volume_diff = _pct_diff(a.volume, b.volume)
                    if volume_diff is not None:
                        volume_diffs.append(volume_diff)
                blockers: tuple[str, ...] = ()
                if not overlap:
                    status = CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_PASS
                    blockers = ("no_timestamp_overlap_provider_specific",)
                elif not price_diffs:
                    status = CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_PASS
                    blockers = ("no_comparable_price_fields_provider_specific",)
                else:
                    max_price = max(price_diffs)
                    status = (
                        CentralMarketHistoryProviderStatus.EQUIVALENT_RESEARCH_DATA
                        if max_price <= equivalence_tolerance
                        else CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_DIVERGENT
                    )
                partial = {
                    "normalized_symbol": symbol,
                    "timeframe": timeframe,
                    "provider_a": provider_a,
                    "provider_b": provider_b,
                    "overlap_rows": len(overlap),
                    "compared_price_field_count": len(price_diffs),
                    "max_abs_price_pct_diff": max(price_diffs) if price_diffs else None,
                    "max_abs_volume_pct_diff": max(volume_diffs) if volume_diffs else None,
                    "equivalence_tolerance": equivalence_tolerance,
                    "status": status,
                    "blocker_reasons": blockers,
                }
                reports.append(
                    CentralMarketHistoryComparisonReport(
                        **partial,
                        comparison_report_id=canonical_json_hash(
                            {
                                "report_type": "central_market_history_ohlcv_comparison",
                                "normalized_symbol": symbol,
                                "timeframe": timeframe,
                                "provider_a": provider_a,
                                "provider_b": provider_b,
                                "overlap_rows": len(overlap),
                                "compared_price_field_count": len(price_diffs),
                                "max_abs_price_pct_diff": max(price_diffs) if price_diffs else None,
                                "max_abs_volume_pct_diff": max(volume_diffs) if volume_diffs else None,
                                "equivalence_tolerance": equivalence_tolerance,
                                "status": status.value,
                                "blocker_reasons": blockers,
                            }
                        ),
                    )
                )
    return tuple(sorted(reports, key=lambda item: (item.normalized_symbol, item.timeframe, item.provider_a, item.provider_b)))


def _row_schema_quality_ok(row: CentralMarketHistoryRow) -> bool:
    if row.family != CentralMarketHistoryFamily.OHLCV:
        return bool(row.provenance_refs and row.source_row_hash and row.row_hash)
    return all(
        value is not None
        for value in (row.open, row.high, row.low, row.close, row.volume, row.timeframe)
    )


def _expected_timestamp_count(
    start_ts: datetime,
    end_ts: datetime,
    timeframe: str | None,
    family: str,
) -> int:
    if family != CentralMarketHistoryFamily.OHLCV.value:
        return 0
    delta = _timeframe_delta(timeframe)
    if delta is None:
        return 0
    span = int((end_ts - start_ts).total_seconds())
    step = int(delta.total_seconds())
    if step <= 0:
        return 0
    return span // step + 1


def _timeframe_delta(timeframe: str | None) -> timedelta | None:
    if timeframe is None:
        return None
    value = timeframe.strip().lower()
    units = {"m": 60, "h": 3600, "d": 86400}
    unit = value[-1:]
    if unit not in units:
        return None
    try:
        count = int(value[:-1])
    except ValueError:
        return None
    if count <= 0:
        return None
    return timedelta(seconds=count * units[unit])


def _pct_diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    denominator = max(abs(a), abs(b))
    if denominator <= 0:
        return None
    return abs(a - b) / denominator


def _coerce_row(value: CentralMarketHistoryRow | Mapping[str, Any]) -> CentralMarketHistoryRow:
    if isinstance(value, CentralMarketHistoryRow):
        return value
    return CentralMarketHistoryRow.model_validate(dict(value))


def _coerce_source(
    value: CentralMarketHistorySourceMetadata | Mapping[str, Any],
) -> CentralMarketHistorySourceMetadata:
    if isinstance(value, CentralMarketHistorySourceMetadata):
        return value
    return CentralMarketHistorySourceMetadata.model_validate(dict(value))


def _validate_rows_have_source_metadata(
    rows: tuple[CentralMarketHistoryRow, ...],
    sources: tuple[CentralMarketHistorySourceMetadata, ...],
) -> None:
    if not sources:
        return
    known = {(source.provider, source.source_id) for source in sources}
    missing = sorted({(row.provider, row.source_id) for row in rows} - known)
    if missing:
        raise ValueError("missing source metadata for rows: " + ",".join(f"{provider}/{source_id}" for provider, source_id in missing))


def _validate_payloads_have_source_metadata(
    rows: tuple[Mapping[str, Any], ...],
    sources: tuple[CentralMarketHistorySourceMetadata, ...],
) -> None:
    known = {(source.provider, source.source_id) for source in sources}
    missing = sorted({(str(row["provider"]), str(row["source_id"])) for row in rows} - known)
    if missing:
        raise ValueError("missing source metadata for rows: " + ",".join(f"{provider}/{source_id}" for provider, source_id in missing))


def _coerce_fast_ohlcv_payload(value: Mapping[str, Any] | CentralMarketHistoryRow) -> dict[str, Any]:
    payload = value.model_dump(mode="json") if isinstance(value, CentralMarketHistoryRow) else dict(value)
    family = CentralMarketHistoryFamily(payload.get("family", CentralMarketHistoryFamily.OHLCV.value))
    if family != CentralMarketHistoryFamily.OHLCV:
        raise ValueError("fast OHLCV payload writer only accepts OHLCV rows")
    for key, expected in RESEARCH_BOUNDARY.items():
        if key in payload and payload[key] is not expected:
            raise ValueError(f"central market-history boundary override rejected: {key}")

    provider = str(payload["provider"]).strip().lower()
    source_id = str(payload["source_id"]).strip().lower()
    source_access_mode = str(payload["source_access_mode"]).strip().lower()
    for token in _FORBIDDEN_SOURCE_ACCESS_TOKENS:
        if token in source_access_mode:
            raise ValueError("source_access_mode is not strict-free accepted evidence")

    timestamp_dt = _coerce_timestamp(payload.get("timestamp", payload.get("timestamp_ms")))
    timestamp_ms = int(timestamp_dt.timestamp() * 1000)
    if payload.get("timestamp_ms") is not None and int(payload["timestamp_ms"]) != timestamp_ms:
        raise ValueError("timestamp_ms must match timestamp")

    open_value = float(payload["open"])
    high_value = float(payload["high"])
    low_value = float(payload["low"])
    close_value = float(payload["close"])
    volume_value = float(payload["volume"])
    if high_value < max(open_value, close_value, low_value):
        raise ValueError("OHLCV high is below open/low/close")
    if low_value > min(open_value, close_value, high_value):
        raise ValueError("OHLCV low is above open/high/close")
    if volume_value < 0:
        raise ValueError("OHLCV volume must be non-negative")

    row_payload: dict[str, Any] = {
        "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
        "provider": provider,
        "source_id": source_id,
        "source_access_mode": source_access_mode,
        "family": CentralMarketHistoryFamily.OHLCV.value,
        "normalized_symbol": str(payload["normalized_symbol"]).strip().upper(),
        "venue_symbol": payload.get("venue_symbol"),
        "timeframe": str(payload["timeframe"]).strip(),
        "timestamp": timestamp_dt.isoformat().replace("+00:00", "Z"),
        "timestamp_ms": timestamp_ms,
        "open": open_value,
        "high": high_value,
        "low": low_value,
        "close": close_value,
        "volume": volume_value,
        "quote_volume": _optional_float(payload.get("quote_volume")),
        "trade_count": _optional_float(payload.get("trade_count")),
        "event_id": None,
        "numeric_fields": dict(payload.get("numeric_fields") or {}),
        "raw_fields": dict(payload.get("raw_fields") or {}),
        "provenance_refs": list(payload.get("provenance_refs") or ()),
        "raw_ref": payload.get("raw_ref"),
        "raw_sha256": payload.get("raw_sha256"),
        **RESEARCH_BOUNDARY,
    }
    source_hash = central_market_history_source_row_hash(
        _row_payload_for_hash(row_payload, include_source_hash=False)
    )
    row_hash = central_market_history_row_hash(
        {
            **_row_payload_for_hash(row_payload, include_source_hash=False),
            "source_row_hash": source_hash,
        }
    )
    if payload.get("source_row_hash") is not None and payload["source_row_hash"] != source_hash:
        raise ValueError("source_row_hash does not match row payload")
    if payload.get("row_hash") is not None and payload["row_hash"] != row_hash:
        raise ValueError("row_hash does not match row payload")
    row_payload["source_row_hash"] = source_hash
    row_payload["row_hash"] = row_hash
    return row_payload


def _coerce_fast_event_payload(value: Mapping[str, Any] | CentralMarketHistoryRow) -> dict[str, Any]:
    payload = value.model_dump(mode="json") if isinstance(value, CentralMarketHistoryRow) else dict(value)
    family = CentralMarketHistoryFamily(payload["family"])
    if family == CentralMarketHistoryFamily.OHLCV:
        raise ValueError("fast event payload writer does not accept OHLCV rows")
    for key, expected in RESEARCH_BOUNDARY.items():
        if key in payload and payload[key] is not expected:
            raise ValueError(f"central market-history boundary override rejected: {key}")

    provider = str(payload["provider"]).strip().lower()
    source_id = str(payload["source_id"]).strip().lower()
    source_access_mode = str(payload["source_access_mode"]).strip().lower()
    for token in _FORBIDDEN_SOURCE_ACCESS_TOKENS:
        if token in source_access_mode:
            raise ValueError("source_access_mode is not strict-free accepted evidence")

    timestamp_dt = _coerce_timestamp(payload.get("timestamp", payload.get("timestamp_ms")))
    timestamp_ms = int(timestamp_dt.timestamp() * 1000)
    if payload.get("timestamp_ms") is not None and int(payload["timestamp_ms"]) != timestamp_ms:
        raise ValueError("timestamp_ms must match timestamp")

    timeframe = payload.get("timeframe")
    if timeframe is not None:
        timeframe = str(timeframe).strip() or None
    row_payload: dict[str, Any] = {
        "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
        "provider": provider,
        "source_id": source_id,
        "source_access_mode": source_access_mode,
        "family": family.value,
        "normalized_symbol": str(payload["normalized_symbol"]).strip().upper(),
        "venue_symbol": payload.get("venue_symbol"),
        "timeframe": timeframe,
        "timestamp": timestamp_dt.isoformat().replace("+00:00", "Z"),
        "timestamp_ms": timestamp_ms,
        "open": None,
        "high": None,
        "low": None,
        "close": None,
        "volume": None,
        "quote_volume": None,
        "trade_count": None,
        "event_id": None if payload.get("event_id") is None else str(payload.get("event_id")),
        "numeric_fields": {str(key): float(value) for key, value in dict(payload.get("numeric_fields") or {}).items()},
        "raw_fields": dict(payload.get("raw_fields") or {}),
        "provenance_refs": list(payload.get("provenance_refs") or ()),
        "raw_ref": payload.get("raw_ref"),
        "raw_sha256": payload.get("raw_sha256"),
        **RESEARCH_BOUNDARY,
    }
    source_hash = central_market_history_source_row_hash(
        _row_payload_for_hash(row_payload, include_source_hash=False)
    )
    row_hash = central_market_history_row_hash(
        {
            **_row_payload_for_hash(row_payload, include_source_hash=False),
            "source_row_hash": source_hash,
        }
    )
    if payload.get("source_row_hash") is not None and payload["source_row_hash"] != source_hash:
        raise ValueError("source_row_hash does not match row payload")
    if payload.get("row_hash") is not None and payload["row_hash"] != row_hash:
        raise ValueError("row_hash does not match row payload")
    row_payload["source_row_hash"] = source_hash
    row_payload["row_hash"] = row_hash
    return row_payload


def _dedupe_central_market_history_payloads(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[tuple[dict[str, Any], ...], tuple[CentralMarketHistoryDuplicateGroup, ...]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        normalized = dict(row)
        groups[_central_market_history_payload_dedupe_key(normalized)].append(normalized)
    deduped: list[dict[str, Any]] = []
    duplicate_groups: list[CentralMarketHistoryDuplicateGroup] = []
    for key, group_rows in groups.items():
        ordered = sorted(group_rows, key=lambda item: (str(item["row_hash"]), str(item["source_row_hash"])))
        kept = ordered[0]
        deduped.append(kept)
        if len(ordered) > 1:
            duplicate_groups.append(
                CentralMarketHistoryDuplicateGroup(
                    dedupe_key=key,
                    provider=str(kept["provider"]),
                    normalized_symbol=str(kept["normalized_symbol"]),
                    timeframe=kept.get("timeframe"),
                    family=str(kept["family"]),
                    timestamp=_coerce_timestamp(kept["timestamp"]),
                    kept_row_hash=str(kept["row_hash"]),
                    duplicate_row_hashes=tuple(str(row["row_hash"]) for row in ordered[1:]),
                    source_row_hashes=tuple(str(row["source_row_hash"]) for row in ordered),
                )
            )
    return (
        tuple(
            sorted(
                deduped,
                key=lambda item: (
                    str(item["provider"]),
                    str(item["normalized_symbol"]),
                    str(item.get("timeframe") or ""),
                    str(item["family"]),
                    int(item["timestamp_ms"]),
                    str(item["row_hash"]),
                ),
            )
        ),
        tuple(sorted(duplicate_groups, key=lambda item: item.dedupe_key)),
    )


def _central_market_history_payload_dedupe_key(row: Mapping[str, Any]) -> str:
    payload: dict[str, Any] = {
        "provider": row["provider"],
        "normalized_symbol": row["normalized_symbol"],
        "timeframe": row.get("timeframe"),
        "timestamp_ms": row["timestamp_ms"],
    }
    if row["family"] != CentralMarketHistoryFamily.OHLCV.value:
        payload.update(
            {
                "family": row["family"],
                "event_id": row.get("event_id"),
                "source_row_hash": row["source_row_hash"],
            }
        )
    return canonical_json_hash(payload)


def _raw_sources_from_payloads(rows: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for row in rows:
        key = (row.get("raw_ref"), row.get("raw_sha256"))
        entry = grouped.setdefault(
            key,
            {
                "raw_ref": row.get("raw_ref"),
                "raw_sha256": row.get("raw_sha256"),
                "providers": set(),
                "source_ids": set(),
                "symbols": set(),
                "families": set(),
                "timeframes": set(),
                "row_count": 0,
            },
        )
        entry["providers"].add(row["provider"])
        entry["source_ids"].add(row["source_id"])
        entry["symbols"].add(row["normalized_symbol"])
        entry["families"].add(row["family"])
        entry["timeframes"].add(row.get("timeframe"))
        entry["row_count"] += 1
    serializable = []
    for entry in grouped.values():
        serializable.append(
            {
                "raw_ref": entry["raw_ref"],
                "raw_sha256": entry["raw_sha256"],
                "providers": tuple(sorted(entry["providers"])),
                "source_ids": tuple(sorted(entry["source_ids"])),
                "symbols": tuple(sorted(entry["symbols"])),
                "families": tuple(sorted(entry["families"])),
                "timeframes": tuple(sorted(item for item in entry["timeframes"] if item is not None)),
                "row_count": entry["row_count"],
            }
        )
    return tuple(sorted(serializable, key=lambda item: (str(item["raw_ref"]), str(item["raw_sha256"]))))


def _build_ohlcv_payload_quality_report(
    *,
    run_id: str,
    rows: tuple[Mapping[str, Any], ...],
    duplicate_groups: tuple[CentralMarketHistoryDuplicateGroup, ...],
    coverage_min: float,
) -> CentralMarketHistoryQualityReport:
    return _build_payload_quality_report(
        run_id=run_id,
        rows=rows,
        duplicate_groups=duplicate_groups,
        coverage_min=coverage_min,
    )


def _build_payload_quality_report(
    *,
    run_id: str,
    rows: tuple[Mapping[str, Any], ...],
    duplicate_groups: tuple[CentralMarketHistoryDuplicateGroup, ...],
    coverage_min: float,
) -> CentralMarketHistoryQualityReport:
    coverage_reports = _coverage_reports_for_payloads(
        rows=rows,
        duplicate_groups=duplicate_groups,
        coverage_min=coverage_min,
    )
    blocked_provider_count = sum(
        1
        for report in coverage_reports
        if report.quality_status == CentralMarketHistoryProviderStatus.BLOCKED
    )
    ready = any(report.quality_status != CentralMarketHistoryProviderStatus.BLOCKED for report in coverage_reports)
    blockers: tuple[str, ...] = () if ready else ("no_usable_market_history_rows",)
    partial = {
        "run_id": run_id,
        "row_count": len(rows),
        "provider_count": len({row["provider"] for row in rows}),
        "coverage_reports": coverage_reports,
        "ohlcv_comparisons": (),
        "equivalent_ohlcv_pair_count": 0,
        "provider_specific_pair_count": len(coverage_reports) - blocked_provider_count,
        "blocked_provider_count": blocked_provider_count,
        "hyperliquid_rows_present": any(row["provider"] == "hyperliquid" for row in rows),
        "hyperliquid_missing_not_blocking": True,
        "centralized_market_history_ready": ready,
        "blocker_reasons": blockers,
    }
    return CentralMarketHistoryQualityReport(
        **partial,
        quality_report_id=central_market_history_quality_report_id_from_payload(partial),
    )


def _coverage_reports_for_payloads(
    *,
    rows: tuple[Mapping[str, Any], ...],
    duplicate_groups: tuple[CentralMarketHistoryDuplicateGroup, ...],
    coverage_min: float,
) -> tuple[CentralMarketHistoryCoverageReport, ...]:
    by_group: dict[tuple[str, str, str | None, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_group[(str(row["provider"]), str(row["normalized_symbol"]), row.get("timeframe"), str(row["family"]))].append(row)
    duplicate_counts: dict[tuple[str, str, str | None, str], int] = defaultdict(int)
    for group in duplicate_groups:
        duplicate_counts[(group.provider, group.normalized_symbol, group.timeframe, group.family)] += len(
            group.duplicate_row_hashes
        )
    reports: list[CentralMarketHistoryCoverageReport] = []
    for (provider, symbol, timeframe, family), group_rows in by_group.items():
        ordered_rows = sorted(group_rows, key=lambda item: int(item["timestamp_ms"]))
        timestamps = [_coerce_timestamp(row["timestamp"]) for row in ordered_rows]
        timestamp_ms_values = [int(row["timestamp_ms"]) for row in group_rows]
        unique_timestamp_count = len(set(timestamp_ms_values))
        start_ts = timestamps[0]
        end_ts = timestamps[-1]
        expected_count = _expected_timestamp_count(start_ts, end_ts, timeframe, family)
        coverage_ratio = min(1.0, unique_timestamp_count / expected_count) if expected_count else 1.0
        nonempty = bool(group_rows)
        monotonic = timestamp_ms_values == sorted(timestamp_ms_values)
        timestamp_sanity = all(timestamp.tzinfo is not None and timestamp.tzinfo.utcoffset(timestamp) is not None for timestamp in timestamps)
        schema_valid = all(_payload_schema_quality_ok(row) for row in group_rows)
        blockers: list[str] = []
        if not nonempty:
            blockers.append("empty_rows")
        if not monotonic:
            blockers.append("non_monotonic_timestamps")
        if not timestamp_sanity:
            blockers.append("timestamp_sanity_failed")
        if not schema_valid:
            blockers.append("schema_invalid")
        if family == CentralMarketHistoryFamily.OHLCV.value and coverage_ratio < coverage_min:
            blockers.append("coverage_below_min")
        status = CentralMarketHistoryProviderStatus.BLOCKED if blockers else CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_PASS
        partial = {
            "provider": provider,
            "source_ids": tuple(sorted({str(row["source_id"]) for row in group_rows})),
            "normalized_symbol": symbol,
            "timeframe": timeframe,
            "family": family,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "row_count": len(group_rows),
            "unique_timestamp_count": unique_timestamp_count,
            "expected_timestamp_count": expected_count,
            "coverage_ratio": coverage_ratio,
            "coverage_min": coverage_min,
            "nonempty": nonempty,
            "monotonic_timestamps": monotonic,
            "timestamp_sanity_pass": timestamp_sanity,
            "schema_valid": schema_valid,
            "duplicate_count": duplicate_counts[(provider, symbol, timeframe, family)],
            "quality_status": status,
            "blocker_reasons": tuple(blockers),
        }
        reports.append(
            CentralMarketHistoryCoverageReport(
                **partial,
                coverage_report_id=_central_market_history_coverage_report_id_from_payload(partial),
            )
        )
    return tuple(sorted(reports, key=lambda item: (item.normalized_symbol, item.timeframe or "", item.provider, item.family)))


def _ohlcv_payload_schema_quality_ok(row: Mapping[str, Any]) -> bool:
    return all(
        row.get(value_key) is not None
        for value_key in ("open", "high", "low", "close", "volume", "timeframe", "source_row_hash", "row_hash")
    )


def _payload_schema_quality_ok(row: Mapping[str, Any]) -> bool:
    if row.get("family") == CentralMarketHistoryFamily.OHLCV.value:
        return _ohlcv_payload_schema_quality_ok(row)
    return all(row.get(value_key) is not None for value_key in ("timestamp_ms", "source_row_hash", "row_hash")) and isinstance(
        row.get("numeric_fields"),
        Mapping,
    )


def _coerce_timestamp(value: datetime | int | float | str) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, int | float):
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric = numeric / 1000.0
        return datetime.fromtimestamp(numeric, tz=UTC)
    stripped = str(value).strip()
    if stripped.isdigit():
        return _coerce_timestamp(int(stripped))
    return ensure_utc(datetime.fromisoformat(stripped.replace("Z", "+00:00")))


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _json_ready(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return ensure_utc(value).isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, tuple | list):
        return [_json_ready(item) for item in value]
    return value


def _row_payload_for_hash(payload: Mapping[str, Any], *, include_source_hash: bool) -> dict[str, Any]:
    data = dict(_json_ready(payload))
    base = {
        "schema_version": CENTRAL_MARKET_HISTORY_SCHEMA_VERSION,
        "provider": None,
        "source_id": None,
        "source_access_mode": None,
        "family": None,
        "normalized_symbol": None,
        "venue_symbol": None,
        "timeframe": None,
        "timestamp": None,
        "timestamp_ms": None,
        "open": None,
        "high": None,
        "low": None,
        "close": None,
        "volume": None,
        "quote_volume": None,
        "trade_count": None,
        "event_id": None,
        "numeric_fields": {},
        "raw_fields": {},
        "provenance_refs": [],
        "raw_ref": None,
        "raw_sha256": None,
        **dict(RESEARCH_BOUNDARY),
    }
    for key, value in data.items():
        if key in {"row_hash", "source_row_hash"}:
            continue
        base[key] = value
    if base["timestamp"] is not None:
        base["timestamp"] = _coerce_timestamp(base["timestamp"]).isoformat().replace("+00:00", "Z")
    if include_source_hash:
        base["source_row_hash"] = data.get("source_row_hash")
    return _json_ready(base)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"central market-history file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"central market-history file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    part_path = path.with_name(path.name + ".part")
    if part_path.exists():
        raise FileExistsError(f"central market-history partial file already exists: {part_path}")
    part_path.write_text(json.dumps(_json_ready(payload), sort_keys=True, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    part_path.replace(path)


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"central market-history file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_json_ready(row), sort_keys=True, ensure_ascii=True) + "\n")


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_json_ready(row), sort_keys=True, ensure_ascii=True) + "\n")


def _write_parquet(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write empty central market-history parquet")
    if path.exists():
        raise FileExistsError(f"central market-history file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for row in rows for key in row})
    normalized = []
    for row in rows:
        ready = _json_ready(row)
        normalized.append({key: _parquet_scalar(ready.get(key)) for key in keys})
    pq.write_table(pa.Table.from_pylist(normalized), path, compression="zstd")


def _write_parquet_atomic(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError("cannot write empty central market-history parquet")
    if path.exists():
        raise FileExistsError(f"central market-history file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    part_path = path.with_name(path.name + ".part")
    if part_path.exists():
        raise FileExistsError(f"central market-history partial file already exists: {part_path}")
    keys = sorted({key for row in rows for key in row})
    normalized = []
    for row in rows:
        ready = _json_ready(row)
        normalized.append({key: _parquet_scalar(ready.get(key)) for key in keys})
    pq.write_table(pa.Table.from_pylist(normalized), part_path, compression="zstd")
    part_path.replace(path)


def _relative_ref(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _parquet_scalar(value: Any) -> Any:
    if isinstance(value, Mapping) or isinstance(value, list):
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    return value
