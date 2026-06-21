# V2-AUDIT-ID: V2-AUD-XVENUE-001
# V2-CONTRACTS: docs/contracts/venue_adapter_contract.md
# V2-BOUNDARY: research_only, public_market_data_only, no_order_or_sizing
# V2-OWNER: v2_venues
"""Research-safe venue adapter schemas for v2."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now


class VenueAdapterCapability(BaseModel):
    model_config = ConfigDict(frozen=True)

    adapter_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    market_types: tuple[str, ...] = ("perp",)
    access_mode: Literal["fixture_only", "public_unsigned"] = "fixture_only"
    supports_bars: bool = False
    supports_funding: bool = False
    supports_trades: bool = False
    supports_bbo: bool = False
    supports_l2: bool = False
    supports_official_s3: bool = False
    rate_limit_policy: str = "not_applicable_fixture"
    provenance_required: bool = True
    default_primary_venue: bool = False
    secrets_access_allowed: bool = False
    signed_private_endpoints_allowed: bool = False
    account_state_allowed: bool = False
    order_placement_allowed: bool = False
    leverage_margin_mutation_allowed: bool = False
    sizing_allowed: bool = False
    runtime_mode_change_allowed: bool = False
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_capability(self) -> "VenueAdapterCapability":
        _require_boundary(self.research_only, self.observe_only, self.promotion_ready)
        forbidden = {
            "secrets_access_allowed": self.secrets_access_allowed,
            "signed_private_endpoints_allowed": self.signed_private_endpoints_allowed,
            "account_state_allowed": self.account_state_allowed,
            "order_placement_allowed": self.order_placement_allowed,
            "leverage_margin_mutation_allowed": self.leverage_margin_mutation_allowed,
            "sizing_allowed": self.sizing_allowed,
            "runtime_mode_change_allowed": self.runtime_mode_change_allowed,
        }
        enabled = [name for name, value in forbidden.items() if value]
        if enabled:
            raise ValueError("venue adapter capability violates v2 boundary: " + ",".join(enabled))
        if not self.provenance_required:
            raise ValueError("venue adapter capabilities must require provenance")
        return self


class VenueRawRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=64, max_length=64)
    adapter_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    source: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=utc_now)
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @classmethod
    def build(
        cls,
        *,
        adapter_id: str,
        venue: str,
        source: str,
        params: Mapping[str, Any] | None = None,
    ) -> "VenueRawRequest":
        materialized = dict(params or {})
        request_id = canonical_json_hash(
            {
                "adapter_id": adapter_id,
                "venue": venue,
                "source": source,
                "params": materialized,
                "schema_version": V2_SCHEMA_VERSION,
            }
        )
        return cls(
            request_id=request_id,
            adapter_id=adapter_id,
            venue=venue,
            source=source,
            params=materialized,
        )

    @model_validator(mode="after")
    def _validate_request(self) -> "VenueRawRequest":
        _require_boundary(self.research_only, self.observe_only, self.promotion_ready)
        return self


class VenueRawResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    response_id: str = Field(min_length=64, max_length=64)
    request_id: str = Field(min_length=64, max_length=64)
    adapter_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    source: str = Field(min_length=1)
    raw_payload_sha256: str = Field(min_length=64, max_length=64)
    row_count: int = Field(ge=0)
    rate_limit_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_scope: str = "fixture_research"
    captured_at: datetime = Field(default_factory=utc_now)
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @classmethod
    def build(
        cls,
        *,
        request: VenueRawRequest,
        payload: Any,
        row_count: int,
        rate_limit_metadata: Mapping[str, Any] | None = None,
        evidence_scope: str = "fixture_research",
    ) -> "VenueRawResponse":
        payload_hash = canonical_json_hash(payload)
        identity = {
            "request_id": request.request_id,
            "raw_payload_sha256": payload_hash,
            "row_count": row_count,
            "evidence_scope": evidence_scope,
            "schema_version": V2_SCHEMA_VERSION,
        }
        return cls(
            response_id=canonical_json_hash(identity),
            request_id=request.request_id,
            adapter_id=request.adapter_id,
            venue=request.venue,
            source=request.source,
            raw_payload_sha256=payload_hash,
            row_count=row_count,
            rate_limit_metadata=dict(rate_limit_metadata or {}),
            evidence_scope=evidence_scope,
        )

    @model_validator(mode="after")
    def _validate_response(self) -> "VenueRawResponse":
        _require_boundary(self.research_only, self.observe_only, self.promotion_ready)
        forbidden = {
            "live_signal": self.live_signal,
            "paper_signal": self.paper_signal,
            "sizing_instruction": self.sizing_instruction,
            "order_placement_instruction": self.order_placement_instruction,
            "runtime_mode_change": self.runtime_mode_change,
        }
        enabled = [name for name, value in forbidden.items() if value]
        if enabled:
            raise ValueError("venue raw response violates v2 boundary: " + ",".join(enabled))
        return self


def _require_boundary(research_only: bool, observe_only: bool, promotion_ready: bool) -> None:
    if not research_only or not observe_only or promotion_ready:
        raise ValueError("venue adapter records must preserve the v2 research boundary")
