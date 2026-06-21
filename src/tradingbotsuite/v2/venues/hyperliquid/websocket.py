# V2-AUDIT-ID: V2-AUD-XVENUE-006
# V2-CONTRACTS: docs/contracts/venue_adapter_contract.md
# V2-BOUNDARY: research_only, public_market_data_only, no_order_or_sizing
# V2-OWNER: v2_hyperliquid
"""Research-safe Hyperliquid public WebSocket helpers."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict
from websockets.sync.client import connect as ws_connect

from tradingbotsuite.v2.venues.contracts import (
    VenueAdapterCapability,
    VenueRawRequest,
    VenueRawResponse,
)

HYPERLIQUID_PUBLIC_WEBSOCKET_ADAPTER_ID = "hyperliquid_public_websocket_v1"
HYPERLIQUID_WS_TRADES_SOURCE = "websocket/trades"


class HyperliquidWebSocketFetchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability: VenueAdapterCapability
    raw_request: VenueRawRequest
    raw_response: VenueRawResponse
    payload: tuple[dict[str, Any], ...]
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False


def hyperliquid_public_websocket_capability() -> VenueAdapterCapability:
    return VenueAdapterCapability(
        adapter_id=HYPERLIQUID_PUBLIC_WEBSOCKET_ADAPTER_ID,
        venue="hyperliquid",
        market_types=("perp",),
        access_mode="public_unsigned",
        supports_trades=True,
        rate_limit_policy="hyperliquid_public_websocket_limits_apply",
        default_primary_venue=True,
    )


class HyperliquidWebSocketClient:
    """Small public WebSocket client for bounded market-data snapshots."""

    def __init__(
        self,
        ws_url: str = "wss://api.hyperliquid.xyz/ws",
        timeout: float = 20.0,
        connect: Callable[..., Any] | None = None,
    ) -> None:
        self.ws_url = ws_url
        self.timeout = timeout
        self.connect = connect or ws_connect

    def fetch_trade_snapshot(
        self,
        *,
        coin: str,
        max_messages: int = 20,
        max_rows: int = 200,
        max_seconds: float | None = None,
    ) -> HyperliquidWebSocketFetchResult:
        normalized_coin = coin.strip()
        if not normalized_coin:
            raise ValueError("trades coin is required")
        if max_messages <= 0:
            raise ValueError("max_messages must be positive")
        if max_rows <= 0:
            raise ValueError("max_rows must be positive")
        timeout_seconds = float(max_seconds if max_seconds is not None else self.timeout)
        if timeout_seconds <= 0:
            raise ValueError("max_seconds must be positive")
        capability = hyperliquid_public_websocket_capability()
        subscription = {"type": "trades", "coin": normalized_coin}
        request_body = {"method": "subscribe", "subscription": subscription}
        request = VenueRawRequest.build(
            adapter_id=capability.adapter_id,
            venue=capability.venue,
            source=HYPERLIQUID_WS_TRADES_SOURCE,
            params={
                "ws_url": self.ws_url,
                "method": "subscribe",
                "subscription": subscription,
                "max_messages": max_messages,
                "max_rows": max_rows,
                "max_seconds": timeout_seconds,
            },
        )
        messages = self._receive_messages(
            request_body=request_body,
            max_messages=max_messages,
            max_rows=max_rows,
            timeout_seconds=timeout_seconds,
        )
        raw_response = VenueRawResponse.build(
            request=request,
            payload=messages,
            row_count=sum(_trade_message_row_count(message) for message in messages),
            rate_limit_metadata={
                "max_messages": max_messages,
                "max_rows": max_rows,
                "max_seconds": timeout_seconds,
            },
            evidence_scope="public_unsigned_websocket_trade_snapshot",
        )
        return HyperliquidWebSocketFetchResult(
            capability=capability,
            raw_request=request,
            raw_response=raw_response,
            payload=tuple(messages),
        )

    def _receive_messages(
        self,
        *,
        request_body: dict[str, Any],
        max_messages: int,
        max_rows: int,
        timeout_seconds: float,
    ) -> list[dict[str, Any]]:
        deadline = time.monotonic() + timeout_seconds
        messages: list[dict[str, Any]] = []
        row_count = 0
        with self.connect(self.ws_url, open_timeout=timeout_seconds) as websocket:
            websocket.send(json.dumps(request_body, sort_keys=True))
            while len(messages) < max_messages and row_count < max_rows:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                raw_message = websocket.recv(timeout=remaining)
                message = _decode_message(raw_message)
                messages.append(message)
                row_count += _trade_message_row_count(message)
        if not messages:
            raise ValueError("public websocket trades returned no messages")
        return messages


def _decode_message(raw_message: str | bytes | bytearray) -> dict[str, Any]:
    if isinstance(raw_message, (bytes, bytearray)):
        raw_text = raw_message.decode("utf-8")
    else:
        raw_text = raw_message
    payload = json.loads(raw_text)
    if not isinstance(payload, dict):
        raise ValueError("public websocket message must be an object")
    return dict(payload)


def _trade_message_row_count(message: dict[str, Any]) -> int:
    if message.get("channel") != "trades":
        return 0
    data = message.get("data")
    if isinstance(data, list):
        return len([row for row in data if isinstance(row, dict)])
    return 0
