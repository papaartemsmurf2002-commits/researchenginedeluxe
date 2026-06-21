# V2-AUDIT-ID: V2-AUD-UNIV-001
# V2-CONTRACTS: docs/contracts/venue_adapter_contract.md, docs/contracts/universe_contract.md
# V2-BOUNDARY: research_only, unsigned_public_info, no_order_or_sizing
# V2-OWNER: v2_hyperliquid
"""Research-safe Hyperliquid public info client."""

from __future__ import annotations

from typing import Any

import httpx


class HyperliquidInfoClient:
    """Small unsigned public-info client.

    This client uses only the public info endpoint and has no access to signing,
    account, order, leverage, margin, or live runtime behavior.
    """

    def __init__(self, base_url: str = "https://api.hyperliquid.xyz/info", timeout: float = 20.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def meta_and_asset_contexts(self) -> Any:
        response = httpx.post(
            self.base_url,
            json={"type": "metaAndAssetCtxs"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
