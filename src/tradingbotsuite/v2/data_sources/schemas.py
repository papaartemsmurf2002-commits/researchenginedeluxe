# V2-AUDIT-ID: V2-AUD-DATASRC-001, V2-AUD-DATASRC-004
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md, docs/contracts/data_family_coverage_contract.md
# V2-BOUNDARY: research_only, no_live_imports, strict_free_data_sources
# V2-OWNER: v2_data_sources
"""Schemas for v2 source registries, symbol maps, and family coverage."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.security.boundary import require_research_boundary


class CostClass(str, Enum):
    ZERO_COST_PUBLIC = "zero_cost_public"
    PUBLIC_RATE_LIMITED = "public_rate_limited"
    FREE_SAMPLE_ONLY = "free_sample_only"
    PUBLIC_REQUESTER_PAYS_TRANSFER = "public_requester_pays_transfer"
    PAID_OR_KEYED = "paid_or_keyed"


class SourcePriority(str, Enum):
    P0 = "P0"
    P0_QUARANTINED = "P0_quarantined"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class MappingStatus(str, Enum):
    VERIFIED = "verified"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    DELISTED = "delisted"
    NOT_CHECKED = "not_checked"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class MarketType(str, Enum):
    PERPETUAL = "perpetual"
    SPOT = "spot"
    ORACLE = "oracle"
    CONTEXT = "context"
    UNKNOWN = "unknown"


class CoverageLabel(str, Enum):
    NATIVE_HYPERLIQUID = "native_hyperliquid"
    EXTERNAL_COMPARISON = "external_comparison"
    EXTERNAL_PROXY = "external_proxy"
    DIAGNOSTIC_SAMPLE = "diagnostic_sample"


ALLOWED_DATA_FAMILIES = frozenset(
    {
        "universe_metadata",
        "universe_snapshot",
        "asset_contexts",
        "funding",
        "funding_rate_history",
        "candles",
        "candles_1m",
        "bars_1m",
        "trades",
        "fills",
        "derived_trades",
        "bbo",
        "l2_order_book",
        "l2_snapshots",
        "open_interest",
        "open_interest_statistics",
        "mark_price_klines",
        "index_price_klines",
        "premium_index_klines",
        "taker_buy_sell_volume",
        "long_short_ratios",
        "basis",
        "liquidations",
        "spot_oracle_context",
    }
)

STRICT_ZERO_ALLOWED_COST_CLASSES = frozenset(
    {
        CostClass.ZERO_COST_PUBLIC,
        CostClass.PUBLIC_RATE_LIMITED,
        CostClass.FREE_SAMPLE_ONLY,
    }
)

DISALLOWED_ACCEPTANCE_REASONS = frozenset(
    {
        "forward_capture_segment_only",
        "not_full_2024_plus_window",
        "recent_window_only",
        "recent_window_api_cap",
        "bounded_session_not_continuous",
        "free_sample_only",
        "diagnostic_sample_non_evidence",
        "requester_pays_disabled",
        "external_proxy_non_native",
        "paid_or_keyed_out_of_scope",
    }
)


class RateLimitPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_parallel_downloads: int = Field(default=1, ge=1)
    retry_backoff_seconds: tuple[int, ...] = Field(default=(1, 2, 5, 10), min_length=1)
    page_cap: int | None = Field(default=None, ge=1)


class SourceRegistryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_]*$")
    venue: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    native_to_hyperliquid: bool
    cost_class: CostClass
    auth_required: bool
    secret_required: bool = False
    paid_required: bool = False
    strict_zero_dollar_allowed: bool = True
    accepted_under_strict_free: bool = True
    accepted_historical_coverage_proof: bool = False
    data_families: tuple[str, ...] = Field(min_length=1)
    history_mode: str = Field(min_length=1)
    priority: SourcePriority
    research_role: str = Field(min_length=1)
    rate_limit_policy: RateLimitPolicy | None = None
    provenance_required: tuple[str, ...] = ()
    required_operator_gate: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    source_url_template: str | None = None

    @model_validator(mode="after")
    def _validate_source_registry_entry(self) -> "SourceRegistryEntry":
        unknown_families = sorted(set(self.data_families) - ALLOWED_DATA_FAMILIES)
        if unknown_families:
            raise ValueError(
                "unknown data_families: " + ",".join(unknown_families)
            )
        if self.strict_zero_dollar_allowed and (
            self.auth_required or self.secret_required or self.paid_required
        ):
            raise ValueError(
                "strict-zero-dollar sources cannot require auth, secrets, or payment"
            )
        if self.cost_class in {
            CostClass.PUBLIC_REQUESTER_PAYS_TRANSFER,
            CostClass.PAID_OR_KEYED,
        }:
            if self.strict_zero_dollar_allowed:
                raise ValueError(
                    f"{self.cost_class.value} sources cannot be strict-zero-dollar allowed"
                )
            if self.accepted_under_strict_free:
                raise ValueError(
                    f"{self.cost_class.value} sources cannot be accepted under strict-free"
                )
            if self.cost_class == CostClass.PUBLIC_REQUESTER_PAYS_TRANSFER:
                if not self.required_operator_gate:
                    raise ValueError(
                        "requester-pays sources require an explicit operator gate"
                    )
        if self.cost_class == CostClass.FREE_SAMPLE_ONLY:
            if self.accepted_under_strict_free:
                raise ValueError("free-sample sources are diagnostic only")
            if self.accepted_historical_coverage_proof:
                raise ValueError("free samples cannot prove historical coverage")
        if self.accepted_under_strict_free and not self.strict_zero_dollar_allowed:
            raise ValueError(
                "accepted_under_strict_free requires strict_zero_dollar_allowed"
            )
        if self.accepted_historical_coverage_proof and self.cost_class not in {
            CostClass.ZERO_COST_PUBLIC,
            CostClass.PUBLIC_RATE_LIMITED,
        }:
            raise ValueError(
                "historical coverage proof requires a non-diagnostic free/public source"
            )
        return self


class VenueSymbolRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    venue: str = Field(min_length=1)
    symbol: str | None = None
    market_type: MarketType = MarketType.UNKNOWN
    status: MappingStatus = MappingStatus.NOT_CHECKED
    quote_asset: str | None = None
    contract_type: str | None = None
    native_symbol: str | None = None
    notes: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_symbol_ref(self) -> "VenueSymbolRef":
        if self.status == MappingStatus.VERIFIED and not self.symbol:
            raise ValueError("verified mappings require a symbol")
        return self


class VenueSymbolMapRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    hyperliquid_coin: str = Field(min_length=1)
    as_of_date: date
    canonical_base_asset: str = Field(min_length=1)
    symbols: dict[str, VenueSymbolRef] = Field(default_factory=dict)
    hyperliquid_liquid_as_of: bool
    above_day_notional_threshold: bool
    external_mapping_verified: MappingStatus = MappingStatus.NOT_CHECKED
    provenance: dict[str, Any] = Field(default_factory=dict)
    blocker_reasons: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _validate_symbol_map_row(self) -> "VenueSymbolMapRow":
        hyperliquid_ref = self.symbols.get("hyperliquid_perp")
        if self.hyperliquid_liquid_as_of and self.above_day_notional_threshold:
            if hyperliquid_ref is None:
                raise ValueError("liquid Hyperliquid rows require hyperliquid_perp")
            if hyperliquid_ref.status != MappingStatus.VERIFIED:
                raise ValueError("liquid Hyperliquid rows require verified native symbol")
            if hyperliquid_ref.market_type != MarketType.PERPETUAL:
                raise ValueError("hyperliquid_perp must be a perpetual mapping")
        for key, ref in self.symbols.items():
            if key.endswith("_spot") and ref.market_type not in {
                MarketType.SPOT,
                MarketType.CONTEXT,
            }:
                raise ValueError(f"{key} cannot be marked as {ref.market_type.value}")
        if self.external_mapping_verified in {
            MappingStatus.AMBIGUOUS,
            MappingStatus.MANUAL_REVIEW_REQUIRED,
        } and not self.blocker_reasons:
            raise ValueError("ambiguous/manual-review rows require blocker reasons")
        return self


def source_registry_entries_hash(entries: tuple[SourceRegistryEntry, ...]) -> str:
    return manifest_rows_hash(entry.model_dump(mode="json") for entry in entries)


def source_registry_snapshot_id_for(
    *,
    as_of_date: date,
    universe_snapshot_id: str,
    strict_zero_dollar_mode: bool,
    entry_manifest_hash: str,
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "source_registry_snapshot",
            "as_of_date": as_of_date.isoformat(),
            "universe_snapshot_id": universe_snapshot_id,
            "strict_zero_dollar_mode": strict_zero_dollar_mode,
            "entry_manifest_hash": entry_manifest_hash,
        }
    )


def symbol_map_rows_hash(rows: tuple[VenueSymbolMapRow, ...]) -> str:
    return manifest_rows_hash(_symbol_map_hash_row(row) for row in rows)


def symbol_map_snapshot_id_for(
    *,
    as_of_date: date,
    universe_snapshot_id: str,
    source_registry_snapshot_id: str,
    row_manifest_hash: str,
) -> str:
    return canonical_json_hash(
        {
            "manifest_type": "symbol_map_snapshot",
            "as_of_date": as_of_date.isoformat(),
            "universe_snapshot_id": universe_snapshot_id,
            "source_registry_snapshot_id": source_registry_snapshot_id,
            "row_manifest_hash": row_manifest_hash,
        }
    )


class SourceRegistrySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "source_registry_snapshot"
    registry_snapshot_id: str = Field(min_length=64, max_length=64)
    as_of_date: date
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_ref: str = Field(min_length=1)
    strict_zero_dollar_mode: bool = True
    source_entries: tuple[SourceRegistryEntry, ...] = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(min_length=1)
    source_count: int = Field(ge=1)
    entry_manifest_hash: str = Field(min_length=64, max_length=64)
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
    def _validate_source_registry_snapshot(self) -> "SourceRegistrySnapshot":
        require_research_boundary(self, context="source registry snapshot")
        if self.manifest_type != "source_registry_snapshot":
            raise ValueError("manifest_type must be source_registry_snapshot")
        expected_source_ids = tuple(sorted(entry.source_id for entry in self.source_entries))
        if self.source_ids != expected_source_ids:
            raise ValueError("source_ids must match sorted source entry IDs")
        if self.source_count != len(self.source_entries):
            raise ValueError("source_count must match source_entries length")
        expected_hash = source_registry_entries_hash(self.source_entries)
        if self.entry_manifest_hash != expected_hash:
            raise ValueError("entry_manifest_hash does not match source entries")
        expected_id = source_registry_snapshot_id_for(
            as_of_date=self.as_of_date,
            universe_snapshot_id=self.universe_snapshot_id,
            strict_zero_dollar_mode=self.strict_zero_dollar_mode,
            entry_manifest_hash=self.entry_manifest_hash,
        )
        if self.registry_snapshot_id != expected_id:
            raise ValueError("registry_snapshot_id does not match snapshot identity")
        if self.strict_zero_dollar_mode:
            for entry in self.source_entries:
                require_strict_zero_dollar_source(entry)
                if not entry.accepted_under_strict_free:
                    raise ValueError(f"{entry.source_id} is not accepted under strict-free mode")
        return self


class SymbolMapSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "symbol_map_snapshot"
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    as_of_date: date
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_ref: str = Field(min_length=1)
    source_registry_snapshot_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_rows: tuple[VenueSymbolMapRow, ...]
    symbol_map_count: int = Field(ge=0)
    liquid_symbol_count: int = Field(ge=0)
    above_day_notional_threshold_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
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
    def _validate_symbol_map_snapshot(self) -> "SymbolMapSnapshot":
        require_research_boundary(self, context="symbol map snapshot")
        if self.manifest_type != "symbol_map_snapshot":
            raise ValueError("manifest_type must be symbol_map_snapshot")
        if self.symbol_map_count != len(self.symbol_map_rows):
            raise ValueError("symbol_map_count must match symbol_map_rows length")
        if self.liquid_symbol_count != sum(1 for row in self.symbol_map_rows if row.hyperliquid_liquid_as_of):
            raise ValueError("liquid_symbol_count does not match symbol-map rows")
        if self.above_day_notional_threshold_count != sum(
            1 for row in self.symbol_map_rows if row.above_day_notional_threshold
        ):
            raise ValueError("above_day_notional_threshold_count does not match rows")
        if self.blocker_count != sum(1 for row in self.symbol_map_rows if row.blocker_reasons):
            raise ValueError("blocker_count does not match symbol-map rows")
        if any(row.as_of_date != self.as_of_date for row in self.symbol_map_rows):
            raise ValueError("all symbol-map rows must share snapshot as_of_date")
        expected_hash = symbol_map_rows_hash(self.symbol_map_rows)
        if self.row_manifest_hash != expected_hash:
            raise ValueError("row_manifest_hash does not match symbol-map rows")
        expected_id = symbol_map_snapshot_id_for(
            as_of_date=self.as_of_date,
            universe_snapshot_id=self.universe_snapshot_id,
            source_registry_snapshot_id=self.source_registry_snapshot_id,
            row_manifest_hash=self.row_manifest_hash,
        )
        if self.symbol_map_snapshot_id != expected_id:
            raise ValueError("symbol_map_snapshot_id does not match snapshot identity")
        return self


class CoverageWindow(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _validate_window(self) -> "CoverageWindow":
        if self.end <= self.start:
            raise ValueError("coverage window end must be greater than start")
        return self


class ExpectedBuckets(BaseModel):
    model_config = ConfigDict(frozen=True)

    bucket_seconds: int = Field(ge=1)
    count: int = Field(ge=0)


class DataFamilyCoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "data_family_coverage_report"
    coverage_report_id: str = Field(min_length=1)
    universe_snapshot_ref: str = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    archive_snapshot_ref: str | None = None
    symbol: str = Field(min_length=1)
    family: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(min_length=1)
    source_cost_classes: tuple[CostClass, ...] = Field(min_length=1)
    labels: tuple[CoverageLabel, ...] = Field(min_length=1)
    coverage_window: CoverageWindow
    expected_buckets: ExpectedBuckets
    observed_buckets: int = Field(ge=0)
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
    missing_buckets: tuple[str, ...] = ()
    accepted_for_research_reporting: bool = False
    reason: tuple[str, ...] = ()
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
    def _validate_coverage_report(self) -> "DataFamilyCoverageReport":
        require_research_boundary(self, context="data family coverage report")
        if self.manifest_type != "data_family_coverage_report":
            raise ValueError("manifest_type must be data_family_coverage_report")
        if self.expected_buckets.count and self.observed_buckets > self.expected_buckets.count:
            raise ValueError("observed_buckets cannot exceed expected bucket count")
        if self.family not in ALLOWED_DATA_FAMILIES:
            raise ValueError(f"unknown coverage family: {self.family}")
        if self.accepted_for_research_reporting:
            if self.coverage_ratio < self.coverage_min:
                raise ValueError("accepted coverage must meet coverage_min")
            if self.reason:
                raise ValueError("accepted coverage cannot carry blocker reasons")
            if CoverageLabel.DIAGNOSTIC_SAMPLE in self.labels:
                raise ValueError("diagnostic sample coverage cannot be accepted")
            if CoverageLabel.EXTERNAL_PROXY in self.labels:
                raise ValueError("external proxy coverage cannot be accepted")
            if any(
                cost_class
                in {
                    CostClass.FREE_SAMPLE_ONLY,
                    CostClass.PUBLIC_REQUESTER_PAYS_TRANSFER,
                    CostClass.PAID_OR_KEYED,
                }
                for cost_class in self.source_cost_classes
            ):
                raise ValueError("accepted coverage cannot depend on diagnostic or paid sources")
        blocked_reasons = set(self.reason) & DISALLOWED_ACCEPTANCE_REASONS
        if self.accepted_for_research_reporting and blocked_reasons:
            raise ValueError(
                "accepted coverage has blocked reasons: "
                + ",".join(sorted(blocked_reasons))
            )
        return self


def require_strict_zero_dollar_source(entry: SourceRegistryEntry) -> None:
    if entry.cost_class not in STRICT_ZERO_ALLOWED_COST_CLASSES:
        raise ValueError(f"{entry.source_id} is not allowed in strict-zero-dollar mode")
    if entry.auth_required or entry.secret_required or entry.paid_required:
        raise ValueError(f"{entry.source_id} requires auth, secrets, or payment")
    if not entry.strict_zero_dollar_allowed:
        raise ValueError(f"{entry.source_id} is not strict-zero-dollar allowed")


def require_verified_external_mapping(
    row: VenueSymbolMapRow,
    venue_key: str,
) -> VenueSymbolRef:
    ref = row.symbols.get(venue_key)
    if ref is None:
        raise ValueError(f"{venue_key} mapping is missing")
    if ref.status != MappingStatus.VERIFIED:
        raise ValueError(f"{venue_key} mapping is {ref.status.value}")
    if not ref.symbol:
        raise ValueError(f"{venue_key} mapping has no symbol")
    return ref


def _symbol_map_hash_row(row: VenueSymbolMapRow) -> dict[str, Any]:
    return row.model_dump(mode="json", exclude={"created_at"})
