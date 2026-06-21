# V2-AUDIT-ID: V2-AUD-CONTRACTS-001
# V2-CONTRACTS: docs/contracts/universe_contract.md
# V2-BOUNDARY: research_only, no_live_imports, as_of_universe
# V2-OWNER: v2_universe
"""Universe schema skeletons for v2."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.config import defaults
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now


class UniverseMode(str, Enum):
    AS_OF = "as_of"
    CURRENT_LABELED_SANDBOX = "current_labeled_sandbox"
    STATIC_FIXTURE = "static_fixture"


class UniverseConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    venue: str = defaults.DEFAULT_PRIMARY_VENUE
    market_type: str = defaults.DEFAULT_MARKET_TYPE
    min_day_notional_usd: int = Field(
        default=defaults.DEFAULT_MIN_DAY_NOTIONAL_USD,
        ge=5_000_000,
    )
    mode: UniverseMode = UniverseMode.AS_OF
    coverage_min: float = Field(default=defaults.DEFAULT_COVERAGE_MIN, ge=0.98, le=1.0)


class UniverseSnapshotRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(min_length=1)
    mode: UniverseMode = UniverseMode.AS_OF
    manifest_hash: str = Field(min_length=64, max_length=64)


class InstrumentCatalogRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: str = Field(min_length=1)
    venue: str = "hyperliquid"
    venue_symbol: str = Field(min_length=1)
    canonical_symbol: str = Field(min_length=1)
    market_type: str = "perp"
    base_asset: str = Field(min_length=1)
    quote_asset: str = "USD"
    settle_asset: str | None = "USDC"
    first_seen_ts: datetime
    last_seen_ts: datetime
    status: str = "active"
    sz_decimals: int | None = None
    max_leverage: float | None = None
    only_isolated: bool | None = None
    is_hip3_or_rwa: bool = False
    dex_namespace: str | None = None
    reference_market: str | None = None
    oracle_source: str | None = None
    reference_session_calendar: str | None = None
    weekend_behavior_documented: bool | None = None
    listing_age_days: int | None = None
    proxy_data_available: bool | None = None
    source_snapshot_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _hip3_metadata_shape(self) -> "InstrumentCatalogRow":
        if self.is_hip3_or_rwa and not self.dex_namespace:
            raise ValueError("HIP-3/RWA instruments require dex_namespace")
        return self


class AssetContextSnapshotRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    day_ntl_vlm_usd: float = Field(ge=0.0)
    open_interest: float | None = None
    mark_px: float | None = None
    oracle_px: float | None = None
    funding: float | None = None
    raw_context: dict[str, Any] = Field(default_factory=dict)


class UniverseSnapshotRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(min_length=64, max_length=64)
    asof_date: date
    venue: str = "hyperliquid"
    universe_rule_id: str = "hl_perps_day_ntl_vlm_gte_5m_v1"
    universe_mode: UniverseMode = UniverseMode.AS_OF
    instrument_id: str = Field(min_length=1)
    day_ntl_vlm_usd: float = Field(ge=0.0)
    open_interest: float | None = None
    mark_px: float | None = None
    oracle_px: float | None = None
    funding: float | None = None
    eligible_volume: bool
    eligible_coverage: bool = True
    eligible_history: bool = True
    eligible_status: bool = True
    eligible_hip3_metadata: bool = True
    eligible: bool
    exclusion_reason: str | None = None
    evidence_scope: str = "accepted_research"
    accepted_research_evidence_allowed: bool = True
    raw_payload_sha256: str = Field(min_length=64, max_length=64)
    raw_file_id: str = Field(min_length=64, max_length=64)
    created_at: datetime = Field(default_factory=utc_now)


class UniverseRefreshResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(min_length=64, max_length=64)
    raw_file_id: str = Field(min_length=64, max_length=64)
    raw_payload_sha256: str = Field(min_length=64, max_length=64)
    instrument_count: int = Field(ge=0)
    eligible_count: int = Field(ge=0)
    asof_date: date
    universe_mode: UniverseMode
    payload_source: str = Field(default="inline_payload", min_length=1)
    venue_adapter_id: str = "hyperliquid_public_info_v1"
    source_endpoint_or_subscription: str = "info/metaAndAssetCtxs"
    raw_request_id: str | None = None
    raw_response_id: str | None = None
