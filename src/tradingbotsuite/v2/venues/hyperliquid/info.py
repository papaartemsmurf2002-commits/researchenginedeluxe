# V2-AUDIT-ID: V2-AUD-UNIV-001
# V2-CONTRACTS: docs/contracts/venue_adapter_contract.md, docs/contracts/universe_contract.md
# V2-BOUNDARY: research_only, unsigned_public_info, no_order_or_sizing
# V2-OWNER: v2_hyperliquid
"""Research-safe Hyperliquid public info client."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from tradingbotsuite.v2.venues.contracts import (
    VenueAdapterCapability,
    VenueRawRequest,
    VenueRawResponse,
)

HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID = "hyperliquid_public_info_v1"
HYPERLIQUID_META_AND_ASSET_CTXS_SOURCE = "info/metaAndAssetCtxs"


class HyperliquidInfoFetchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability: VenueAdapterCapability
    raw_request: VenueRawRequest
    raw_response: VenueRawResponse
    payload: Any
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False


def hyperliquid_public_info_capability() -> VenueAdapterCapability:
    return VenueAdapterCapability(
        adapter_id=HYPERLIQUID_PUBLIC_INFO_ADAPTER_ID,
        venue="hyperliquid",
        market_types=("perp",),
        access_mode="public_unsigned",
        supports_universe_metadata=True,
        rate_limit_policy="hyperliquid_public_info_limits_apply",
        default_primary_venue=True,
    )


class HyperliquidInfoClient:
    """Small unsigned public-info client.

    This client uses only the public info endpoint and has no access to signing,
    account, order, leverage, margin, or live runtime behavior.
    """

    def __init__(
        self,
        base_url: str = "https://api.hyperliquid.xyz/info",
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.transport = transport

    def meta_and_asset_contexts(self) -> Any:
        return self.fetch_meta_and_asset_contexts().payload

    def fetch_meta_and_asset_contexts(self) -> HyperliquidInfoFetchResult:
        capability = hyperliquid_public_info_capability()
        request = VenueRawRequest.build(
            adapter_id=capability.adapter_id,
            venue=capability.venue,
            source=HYPERLIQUID_META_AND_ASSET_CTXS_SOURCE,
            params={
                "http_method": "POST",
                "base_url": self.base_url,
                "type": "metaAndAssetCtxs",
            },
        )
        client_kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.transport is not None:
            client_kwargs["transport"] = self.transport
        with httpx.Client(**client_kwargs) as client:
            response = client.post(
                self.base_url,
                json={"type": "metaAndAssetCtxs"},
            )
        response.raise_for_status()
        payload = response.json()
        raw_response = VenueRawResponse.build(
            request=request,
            payload=payload,
            row_count=_payload_instrument_count(payload),
            rate_limit_metadata=_rate_limit_metadata(response),
            evidence_scope="public_unsigned_universe_metadata",
        )
        return HyperliquidInfoFetchResult(
            capability=capability,
            raw_request=request,
            raw_response=raw_response,
            payload=payload,
        )


def _payload_instrument_count(payload: Any) -> int:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        universe = payload[0].get("universe", [])
        return len(universe) if isinstance(universe, list) else 0
    if isinstance(payload, dict):
        if isinstance(payload.get("meta"), dict):
            universe = payload["meta"].get("universe", [])
            return len(universe) if isinstance(universe, list) else 0
        universe = payload.get("universe", [])
        return len(universe) if isinstance(universe, list) else 0
    return 0


def _rate_limit_metadata(response: httpx.Response) -> dict[str, Any]:
    metadata: dict[str, Any] = {"status_code": response.status_code}
    for header in ("x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"):
        value = response.headers.get(header)
        if value is not None:
            metadata[header] = value
    return metadata
