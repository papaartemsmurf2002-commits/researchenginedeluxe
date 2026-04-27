from __future__ import annotations

import asyncio
import json
import random
import time
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit

import httpx
from websockets.asyncio.client import connect as ws_connect

from tradingbotsuite.core.models import Bar

BINANCE_15M_STREAM = "15m"
INTERVAL_TO_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "8h": 8 * 60 * 60_000,
}
BINANCE_REST_WEIGHT_PER_MINUTE = 2_400
BINANCE_REST_REFILL_MS = 60_000
DEPTH_HISTORY_WINDOW_MS = 60_000
BINANCE_WS_SESSION_LIMIT_MS = 24 * 60 * 60 * 1000
BINANCE_WS_PLANNED_RECONNECT_DEFAULT_MS = (23 * 60 * 60 * 1000) + (45 * 60 * 1000)
BINANCE_WS_PLANNED_RECONNECT_JITTER_DEFAULT_MS = 60_000
DEPTH_SYNC_COLD = "cold"
DEPTH_SYNC_BUFFERING = "buffering"
DEPTH_SYNC_BOOTSTRAPPING = "bootstrapping"
DEPTH_SYNC_SYNCED = "synced"
DEPTH_SYNC_RESYNC_PENDING = "resync_pending"
DEPTH_SYNC_BACKOFF = "backoff"
DEPTH_SYNC_STALE = "stale"
BINANCE_STREAM_ROUTE_PUBLIC = "public"
BINANCE_STREAM_ROUTE_MARKET = "market"
BINANCE_STREAM_BUNDLE_MARKET = "market_bundle"
BINANCE_STREAM_BUNDLE_PUBLIC = "public_bundle"
BINANCE_STREAM_ROUTE_BY_TYPE = {
    "depth": BINANCE_STREAM_ROUTE_PUBLIC,
    "bookTicker": BINANCE_STREAM_ROUTE_PUBLIC,
    "aggTrade": BINANCE_STREAM_ROUTE_MARKET,
    "kline": BINANCE_STREAM_ROUTE_MARKET,
}


class DepthAlignmentMismatchError(ValueError):
    pass


class DepthGapError(ValueError):
    pass


class DepthBookInvalidError(ValueError):
    pass


@dataclass(slots=True)
class LocalOrderBookState:
    bids: dict[Decimal, Decimal] = field(default_factory=dict)
    asks: dict[Decimal, Decimal] = field(default_factory=dict)
    last_update_id: int | None = None
    last_event_u: int | None = None
    synced: bool = False
    snapshot_time_ms: int | None = None
    last_bootstrap_attempt_ms: int | None = None
    last_depth_event_time_ms: int | None = None
    last_resync_request_ms: int | None = None
    next_bootstrap_after_ms: int = 0
    last_bootstrap_error: str | None = None
    sync_state: str = DEPTH_SYNC_COLD
    repair_in_flight: bool = False
    last_good_depth_time_ms: int | None = None
    last_gap_time_ms: int | None = None
    last_invalid_book_time_ms: int | None = None
    last_rate_limit_time_ms: int | None = None
    last_reconnect_time_ms: int | None = None
    last_planned_reconnect_time_ms: int | None = None
    next_planned_reconnect_time_ms: int | None = None
    last_resync_reason: str | None = None
    reconnect_backoff_ms: int = 0
    buffered_events: deque[dict[str, Any]] = field(default_factory=deque)
    depth_history: deque[dict[str, Any]] = field(default_factory=deque)


@dataclass(slots=True)
class DepthHealthCounters:
    gap_count: int = 0
    resync_count: int = 0
    reconnect_resync_count: int = 0
    rate_limit_count: int = 0
    gap_resync_count: int = 0
    planned_reconnect_count: int = 0
    error_reconnect_count: int = 0
    alignment_mismatch_count: int = 0
    invalid_book_count: int = 0
    dropped_buffered_event_count: int = 0
    buffer_high_watermark: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "depth_gap_count": self.gap_count,
            "depth_resync_count": self.resync_count,
            "depth_reconnect_resync_count": self.reconnect_resync_count,
            "depth_rate_limit_count": self.rate_limit_count,
            "depth_gap_resync_count": self.gap_resync_count,
            "depth_planned_reconnect_count": self.planned_reconnect_count,
            "depth_error_reconnect_count": self.error_reconnect_count,
            "depth_alignment_mismatch_count": self.alignment_mismatch_count,
            "depth_invalid_book_count": self.invalid_book_count,
            "depth_dropped_buffered_event_count": self.dropped_buffered_event_count,
            "depth_buffer_high_watermark": self.buffer_high_watermark,
        }


@dataclass(slots=True)
class StreamBundleLifecycle:
    route: str
    stream_types: tuple[str, ...]
    stream_names: tuple[str, ...]
    connected_at_ms: int | None = None
    next_planned_reconnect_ms: int | None = None
    last_planned_reconnect_ms: int | None = None
    last_error_reconnect_ms: int | None = None
    last_disconnect_reason: str | None = None
    planned_reconnect_count: int = 0
    error_reconnect_count: int = 0

    def as_dict(self, now_ms: int) -> dict[str, Any]:
        planned_reconnect_due_ms = (
            self.next_planned_reconnect_ms
            if self.next_planned_reconnect_ms is not None and self.next_planned_reconnect_ms > now_ms
            else None
        )
        return {
            "route": self.route,
            "stream_types": list(self.stream_types),
            "stream_names": list(self.stream_names),
            "connected_at_ms": self.connected_at_ms,
            "planned_reconnect_due_ms": planned_reconnect_due_ms,
            "last_planned_reconnect_ms": self.last_planned_reconnect_ms,
            "last_error_reconnect_ms": self.last_error_reconnect_ms,
            "last_disconnect_reason": self.last_disconnect_reason,
            "planned_reconnect_count": self.planned_reconnect_count,
            "error_reconnect_count": self.error_reconnect_count,
        }


@dataclass(slots=True)
class BinanceRestBudgetState:
    max_weight_per_minute: int
    budget_pct: float
    effective_limit: int
    reserved_weight: int = 0
    header_used_weight: int | None = None
    window_started_ms: int = 0
    throttled_until_ms: int = 0
    last_wait_ms: int | None = None
    last_reason: str | None = None

    def snapshot(self, now_ms: int) -> dict[str, Any]:
        used_weight = self.header_used_weight if self.header_used_weight is not None else self.reserved_weight
        return {
            "max_weight_per_minute": self.max_weight_per_minute,
            "budget_pct": self.budget_pct,
            "effective_limit": self.effective_limit,
            "used_weight": used_weight,
            "header_used_weight": self.header_used_weight,
            "reserved_weight": self.reserved_weight,
            "throttled_until_ms": self.throttled_until_ms if self.throttled_until_ms > now_ms else None,
            "last_wait_ms": self.last_wait_ms,
            "last_reason": self.last_reason,
            "window_started_ms": self.window_started_ms,
        }


class BinanceRestBudgetManager:
    def __init__(self, *, max_weight_per_minute: int, budget_pct: float) -> None:
        effective_limit = max(1, int(max_weight_per_minute * budget_pct))
        now_ms = int(time.time() * 1000)
        self._state = BinanceRestBudgetState(
            max_weight_per_minute=max_weight_per_minute,
            budget_pct=budget_pct,
            effective_limit=effective_limit,
            window_started_ms=now_ms,
        )
        self._lock = asyncio.Lock()

    def snapshot(self, now_ms: int | None = None) -> dict[str, Any]:
        return self._state.snapshot(now_ms if now_ms is not None else int(time.time() * 1000))

    def _reset_window_locked(self, now_ms: int) -> None:
        if now_ms - self._state.window_started_ms >= BINANCE_REST_REFILL_MS:
            self._state.window_started_ms = now_ms
            self._state.reserved_weight = 0
            self._state.header_used_weight = None

    async def wait_for_capacity(self, *, weight: int, reason: str) -> None:
        while True:
            wait_ms = 0
            async with self._lock:
                now_ms = int(time.time() * 1000)
                self._reset_window_locked(now_ms)
                used_weight = self._state.header_used_weight if self._state.header_used_weight is not None else self._state.reserved_weight
                if self._state.throttled_until_ms > now_ms:
                    wait_ms = self._state.throttled_until_ms - now_ms
                elif used_weight + weight <= self._state.effective_limit:
                    self._state.reserved_weight = used_weight + weight
                    self._state.last_reason = reason
                    self._state.last_wait_ms = 0
                    return
                else:
                    wait_ms = max((self._state.window_started_ms + BINANCE_REST_REFILL_MS) - now_ms, 250)
                    self._state.last_reason = reason
                self._state.last_wait_ms = wait_ms
            await asyncio.sleep(wait_ms / 1000.0)

    async def note_response(self, response: httpx.Response, *, weight: int, reason: str) -> None:
        async with self._lock:
            now_ms = int(time.time() * 1000)
            self._reset_window_locked(now_ms)
            used_weight_header = response.headers.get("x-mbx-used-weight-1m")
            if used_weight_header is not None:
                try:
                    self._state.header_used_weight = int(used_weight_header)
                except ValueError:
                    self._state.header_used_weight = None
            else:
                self._state.header_used_weight = None
                self._state.reserved_weight = max(self._state.reserved_weight, weight)
            self._state.last_reason = reason
            if response.status_code in {418, 429}:
                retry_after_ms = 0
                retry_after_header = response.headers.get("Retry-After")
                if retry_after_header is not None:
                    try:
                        retry_after_ms = max(int(float(retry_after_header) * 1000), 1_000)
                    except ValueError:
                        retry_after_ms = 0
                self._state.throttled_until_ms = max(self._state.throttled_until_ms, now_ms + retry_after_ms)

    async def note_rate_limit(self, *, retry_after_ms: int, reason: str) -> None:
        async with self._lock:
            now_ms = int(time.time() * 1000)
            self._reset_window_locked(now_ms)
            self._state.throttled_until_ms = max(self._state.throttled_until_ms, now_ms + retry_after_ms)
            self._state.last_reason = reason
            self._state.last_wait_ms = retry_after_ms


def _bar_from_row(row: list[Any]) -> Bar:
    return Bar(
        time_ms=int(row[0]),
        open=Decimal(str(row[1])),
        high=Decimal(str(row[2])),
        low=Decimal(str(row[3])),
        close=Decimal(str(row[4])),
        volume=Decimal(str(row[5])),
    )


def _bar_from_kline(kline: dict[str, Any]) -> Bar:
    return Bar(
        time_ms=int(kline["t"]),
        open=Decimal(str(kline["o"])),
        high=Decimal(str(kline["h"])),
        low=Decimal(str(kline["l"])),
        close=Decimal(str(kline["c"])),
        volume=Decimal(str(kline["v"])),
    )


def _normalize_ws_root_url(url: str) -> str:
    parts = urlsplit(url)
    path_segments = [segment for segment in parts.path.split("/") if segment]
    while path_segments and path_segments[-1] in {"public", "market", "private", "ws", "stream"}:
        path_segments.pop()
    normalized_path = f"/{'/'.join(path_segments)}" if path_segments else ""
    return urlunsplit(SplitResult(parts.scheme, parts.netloc, normalized_path, "", ""))


def _signed_sqrt_notional_metrics(window_trades: list[dict[str, Any]]) -> tuple[Decimal, Decimal, Decimal]:
    """Return concave signed-flow metrics inspired by square-root impact.

    This is diagnostic/research plumbing, not a live gate. Large trades should
    not receive linear directional influence when the feature is meant to proxy
    impact pressure, so each trade contributes sign * sqrt(notional).
    """
    signed = Decimal("0")
    total = Decimal("0")
    for trade in window_trades:
        notional = Decimal(trade["notional"])
        if notional <= 0:
            continue
        contribution = notional.sqrt()
        total += contribution
        signed += contribution if trade["aggressor_side"] == "buy" else -contribution
    ratio = signed / total if total > 0 else Decimal("0")
    return signed, total, ratio


def _trade_sign_autocorrelation(window_trades: list[dict[str, Any]]) -> Decimal | None:
    signs = [Decimal("1") if trade["aggressor_side"] == "buy" else Decimal("-1") for trade in window_trades]
    if len(signs) < 3:
        return None
    current = signs[1:]
    previous = signs[:-1]
    current_mean = sum(current, start=Decimal("0")) / Decimal(len(current))
    previous_mean = sum(previous, start=Decimal("0")) / Decimal(len(previous))
    numerator = sum((now - current_mean) * (lagged - previous_mean) for now, lagged in zip(current, previous))
    current_variance = sum((now - current_mean) ** 2 for now in current)
    previous_variance = sum((lagged - previous_mean) ** 2 for lagged in previous)
    if current_variance <= 0 or previous_variance <= 0:
        return None
    return numerator / (current_variance * previous_variance).sqrt()


def _trade_price_response_metrics(window_trades: list[dict[str, Any]], signed_sqrt_total: Decimal) -> dict[str, str | None]:
    if len(window_trades) < 2:
        return {
            "trade_price_response_bps": None,
            "impact_efficiency_bps_per_sqrt_notional": None,
            "flow_price_alignment_bps": None,
        }
    ordered = sorted(window_trades, key=lambda trade: int(trade["time_ms"]))
    first_price = Decimal(ordered[0]["price"])
    last_price = Decimal(ordered[-1]["price"])
    if first_price <= 0:
        return {
            "trade_price_response_bps": None,
            "impact_efficiency_bps_per_sqrt_notional": None,
            "flow_price_alignment_bps": None,
        }
    response_bps = ((last_price - first_price) / first_price) * Decimal("10000")
    signed_notional = sum(
        (Decimal(trade["notional"]) if trade["aggressor_side"] == "buy" else -Decimal(trade["notional"]))
        for trade in window_trades
    )
    flow_sign = Decimal("1") if signed_notional > 0 else (Decimal("-1") if signed_notional < 0 else Decimal("0"))
    alignment_bps = response_bps * flow_sign
    efficiency = response_bps / signed_sqrt_total if signed_sqrt_total > 0 else None
    return {
        "trade_price_response_bps": str(response_bps),
        "impact_efficiency_bps_per_sqrt_notional": str(efficiency) if efficiency is not None else None,
        "flow_price_alignment_bps": str(alignment_bps),
    }


class BinanceCandleClient:
    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        *,
        ws_base_url: str = "wss://fstream.binance.com",
        ws_stale_after_ms: int = 120_000,
        cache_limit: int = 512,
        depth_update_speed_ms: int = 250,
        depth_snapshot_limit: int = 1000,
        depth_required_levels: int = 10,
        depth_resync_min_interval_ms: int = 2_000,
        depth_snapshot_default_backoff_ms: int = 15_000,
        depth_max_buffer_events: int = 8_192,
        depth_reconnect_backoff_ms: int = 1_000,
        depth_reconnect_max_backoff_ms: int = 30_000,
        websocket_planned_reconnect_ms: int = BINANCE_WS_PLANNED_RECONNECT_DEFAULT_MS,
        websocket_planned_reconnect_jitter_ms: int = BINANCE_WS_PLANNED_RECONNECT_JITTER_DEFAULT_MS,
        rest_weight_budget_pct: float = 0.85,
        websocket_connect: Callable[..., Any] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.ws_base_url = ws_base_url.rstrip("/")
        self.ws_root_url = _normalize_ws_root_url(self.ws_base_url)
        self.ws_stale_after_ms = ws_stale_after_ms
        self._client = client or httpx.AsyncClient(base_url=self.base_url, timeout=10.0)
        self._owns_client = client is None
        self._websocket_connect = websocket_connect or ws_connect
        self._cache_limit = cache_limit
        self.depth_update_speed_ms = depth_update_speed_ms
        self.depth_snapshot_limit = depth_snapshot_limit
        self.depth_required_levels = depth_required_levels
        self.depth_resync_min_interval_ms = depth_resync_min_interval_ms
        self.depth_snapshot_default_backoff_ms = depth_snapshot_default_backoff_ms
        self.depth_max_buffer_events = depth_max_buffer_events
        self.depth_reconnect_backoff_ms = depth_reconnect_backoff_ms
        self.depth_reconnect_max_backoff_ms = depth_reconnect_max_backoff_ms
        self.websocket_planned_reconnect_ms = websocket_planned_reconnect_ms
        self.websocket_planned_reconnect_jitter_ms = websocket_planned_reconnect_jitter_ms
        self.rest_weight_budget_pct = rest_weight_budget_pct
        self._rest_budget = BinanceRestBudgetManager(
            max_weight_per_minute=BINANCE_REST_WEIGHT_PER_MINUTE,
            budget_pct=rest_weight_budget_pct,
        )

        self._closed_bars_by_symbol: dict[str, deque[Bar]] = {}
        self._latest_bar_by_symbol: dict[str, Bar] = {}
        self._agg_trades_by_symbol: dict[str, deque[dict[str, Any]]] = {}
        self._book_ticker_by_symbol: dict[str, dict[str, Any]] = {}
        self._local_order_book_by_symbol: dict[str, LocalOrderBookState] = {}
        self._depth_counters_by_symbol: dict[str, DepthHealthCounters] = {}
        self._stream_tasks: dict[str, asyncio.Task[None]] = {}
        self._stream_bundle_lifecycle_by_key: dict[str, StreamBundleLifecycle] = {}
        self._depth_bootstrap_locks: dict[str, asyncio.Lock] = {}
        self._depth_bootstrap_tasks: dict[str, asyncio.Task[None]] = {}
        self._stream_started_ms_by_symbol: dict[str, int] = {}
        self._next_bar_bootstrap_after_ms_by_symbol: dict[str, int] = {}
        self._last_bar_bootstrap_error_by_symbol: dict[str, str] = {}
        self._feature_backoff_until_by_key: dict[str, int] = {}
        self._feature_last_error_by_key: dict[str, str] = {}
        self._feature_cache: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._historical_bar_range_cache: dict[tuple[str, str, int, int], list[Bar]] = {}
        self._last_kline_ws_message_ms_by_symbol: dict[str, int] = {}
        self._last_trade_ws_message_ms_by_symbol: dict[str, int] = {}
        self._last_book_ws_message_ms_by_symbol: dict[str, int] = {}
        self._last_depth_ws_message_ms_by_symbol: dict[str, int] = {}
        self._last_stream_error_by_stream: dict[str, str] = {}

    async def start_market_streams(self, symbols: list[str]) -> None:
        for symbol in symbols:
            self._ensure_stream_tasks(symbol)
        for symbol in symbols:
            if symbol not in self._latest_bar_by_symbol or len(self._closed_bars(symbol)) < 2:
                try:
                    await self._bootstrap_recent_bars(symbol, 2)
                except Exception:
                    pass
            self._schedule_depth_resync_with_reason(symbol, reason="startup", immediate=True)

    def get_stream_status(self) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        tracked_symbols = sorted(
            {
                *self._stream_started_ms_by_symbol.keys(),
                *self._last_kline_ws_message_ms_by_symbol.keys(),
                *self._last_trade_ws_message_ms_by_symbol.keys(),
                *self._last_book_ws_message_ms_by_symbol.keys(),
                *self._last_depth_ws_message_ms_by_symbol.keys(),
            }
        )
        return {
            "enabled": True,
            "started": any(not task.done() for task in self._stream_tasks.values()),
            "ws_base_url": self.ws_base_url,
            "ws_root_url": self.ws_root_url,
            "ws_routes": {
                BINANCE_STREAM_ROUTE_PUBLIC: f"{self.ws_root_url}/{BINANCE_STREAM_ROUTE_PUBLIC}",
                BINANCE_STREAM_ROUTE_MARKET: f"{self.ws_root_url}/{BINANCE_STREAM_ROUTE_MARKET}",
            },
            "tracked_symbols": tracked_symbols,
            "stream_bundles": {
                bundle_key: lifecycle.as_dict(now_ms)
                for bundle_key, lifecycle in self._stream_bundle_lifecycle_by_key.items()
            },
            "last_ws_message_ms": max(
                [
                    *self._last_kline_ws_message_ms_by_symbol.values(),
                    *self._last_trade_ws_message_ms_by_symbol.values(),
                    *self._last_book_ws_message_ms_by_symbol.values(),
                    *self._last_depth_ws_message_ms_by_symbol.values(),
                ],
                default=None,
            ),
            "symbol_status": {
                symbol: {
                    "started_ms": self._stream_started_ms_by_symbol.get(symbol),
                    "last_kline_ws_message_ms": self._last_kline_ws_message_ms_by_symbol.get(symbol),
                    "last_trade_ws_message_ms": self._last_trade_ws_message_ms_by_symbol.get(symbol),
                    "last_book_ws_message_ms": self._last_book_ws_message_ms_by_symbol.get(symbol),
                    "last_depth_ws_message_ms": self._last_depth_ws_message_ms_by_symbol.get(symbol),
                    "last_ws_message_ms": max(
                        [
                            value
                            for value in (
                                self._last_kline_ws_message_ms_by_symbol.get(symbol),
                                self._last_trade_ws_message_ms_by_symbol.get(symbol),
                                self._last_book_ws_message_ms_by_symbol.get(symbol),
                                self._last_depth_ws_message_ms_by_symbol.get(symbol),
                            )
                            if value is not None
                        ],
                        default=None,
                    ),
                    "order_book_synced": self._order_book(symbol).synced,
                    "order_book_health_state": self._order_book_health_state(symbol, now_ms),
                    "depth_sync_state": self._depth_sync_state(symbol, now_ms),
                    "order_book_last_update_id": self._order_book(symbol).last_update_id,
                    "order_book_snapshot_time_ms": self._order_book(symbol).snapshot_time_ms,
                    "order_book_last_bootstrap_attempt_ms": self._order_book(symbol).last_bootstrap_attempt_ms,
                    "order_book_next_bootstrap_after_ms": self._order_book(symbol).next_bootstrap_after_ms,
                    "repair_in_flight": self._order_book(symbol).repair_in_flight,
                    "last_good_depth_time_ms": self._order_book(symbol).last_good_depth_time_ms,
                    "last_gap_time_ms": self._order_book(symbol).last_gap_time_ms,
                    "last_rate_limit_time_ms": self._order_book(symbol).last_rate_limit_time_ms,
                    "last_invalid_book_time_ms": self._order_book(symbol).last_invalid_book_time_ms,
                    "last_planned_reconnect_time_ms": self._order_book(symbol).last_planned_reconnect_time_ms,
                    "next_planned_reconnect_time_ms": self._order_book(symbol).next_planned_reconnect_time_ms,
                    "buffered_event_count": len(self._order_book(symbol).buffered_events),
                    "rest_budget_state": self._rest_budget.snapshot(now_ms),
                    "depth_update_speed_ms": self.depth_update_speed_ms,
                    "depth_snapshot_limit": self.depth_snapshot_limit,
                    "depth_required_levels": self.depth_required_levels,
                    **self._depth_counters(symbol).as_dict(),
                    "last_error": self._last_stream_error_by_stream.get(f"{symbol}:kline")
                    or self._last_stream_error_by_stream.get(f"{symbol}:aggTrade")
                    or self._last_stream_error_by_stream.get(f"{symbol}:bookTicker")
                    or self._last_stream_error_by_stream.get(f"{symbol}:depth"),
                }
                for symbol in tracked_symbols
            },
        }

    async def close(self) -> None:
        for task in self._stream_tasks.values():
            task.cancel()
        for task in self._depth_bootstrap_tasks.values():
            task.cancel()
        for task in self._stream_tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        for task in self._depth_bootstrap_tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._stream_tasks.clear()
        self._depth_bootstrap_tasks.clear()
        if self._owns_client:
            await self._client.aclose()

    async def fetch_recent_closed_bars(self, symbol: str, limit: int) -> list[Bar]:
        cached = list(self._closed_bars(symbol))
        if len(cached) >= limit:
            return cached[-limit:]
        await self._ensure_stream(symbol)
        cached = list(self._closed_bars(symbol))
        if len(cached) >= limit:
            return cached[-limit:]
        bars = await self._bootstrap_recent_bars(symbol, max(limit, 2))
        return bars[-limit:]

    async def fetch_historical_closed_bars(
        self,
        symbol: str,
        *,
        limit: int,
        end_time_ms: int | None = None,
        interval: str = BINANCE_15M_STREAM,
    ) -> list[Bar]:
        if end_time_ms is not None:
            interval_ms = INTERVAL_TO_MS.get(interval, INTERVAL_TO_MS[BINANCE_15M_STREAM])
            start_time_ms = end_time_ms - ((limit - 1) * interval_ms)
            bars = await self.fetch_historical_closed_bar_range(
                symbol,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                interval=interval,
            )
            return bars[-limit:]
        params: dict[str, Any] = {"symbol": symbol, "interval": interval, "limit": limit}
        rows = await self._request_klines_with_retry(params, include_incomplete=False)
        if end_time_ms is None and rows:
            rows = rows[:-1]
        return [_bar_from_row(row) for row in rows[-limit:]]

    async def fetch_future_closed_bars(
        self,
        symbol: str,
        *,
        start_time_ms: int,
        limit: int,
        interval: str = BINANCE_15M_STREAM,
    ) -> list[Bar]:
        interval_ms = INTERVAL_TO_MS.get(interval, INTERVAL_TO_MS[BINANCE_15M_STREAM])
        end_time_ms = start_time_ms + ((limit - 1) * interval_ms) + interval_ms - 1
        bars = await self.fetch_historical_closed_bar_range(
            symbol,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            interval=interval,
        )
        return bars[:limit]

    async def fetch_historical_closed_bar_range(
        self,
        symbol: str,
        *,
        start_time_ms: int,
        end_time_ms: int,
        interval: str = BINANCE_15M_STREAM,
    ) -> list[Bar]:
        if end_time_ms < start_time_ms:
            return []
        cache_key = (symbol, interval, start_time_ms, end_time_ms)
        cached = self._historical_bar_range_cache.get(cache_key)
        if cached is not None:
            return list(cached)
        interval_ms = INTERVAL_TO_MS.get(interval, INTERVAL_TO_MS[BINANCE_15M_STREAM])
        limit = min(1500, max(2, ((end_time_ms - start_time_ms) // interval_ms) + 2))
        current_start_ms = start_time_ms
        rows: list[list[Any]] = []
        seen_open_times: set[int] = set()
        while current_start_ms <= end_time_ms:
            batch = await self._request_klines_with_retry(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start_ms,
                    "endTime": end_time_ms,
                    "limit": limit,
                },
                include_incomplete=False,
            )
            if not batch:
                break
            for row in batch:
                open_time_ms = int(row[0])
                if open_time_ms < start_time_ms or open_time_ms > end_time_ms or open_time_ms in seen_open_times:
                    continue
                seen_open_times.add(open_time_ms)
                rows.append(row)
            next_start_ms = int(batch[-1][0]) + interval_ms
            if next_start_ms <= current_start_ms or len(batch) < limit:
                break
            current_start_ms = next_start_ms
        rows.sort(key=lambda row: int(row[0]))
        bars = [_bar_from_row(row) for row in rows]
        self._historical_bar_range_cache[cache_key] = list(bars)
        return bars

    async def fetch_latest_bar(self, symbol: str, *, include_incomplete: bool = True) -> Bar:
        if include_incomplete and symbol in self._latest_bar_by_symbol:
            return self._latest_bar_by_symbol[symbol]
        cached = list(self._closed_bars(symbol))
        if cached:
            return cached[-1]
        await self._ensure_stream(symbol)
        if include_incomplete and symbol in self._latest_bar_by_symbol:
            return self._latest_bar_by_symbol[symbol]
        cached = list(self._closed_bars(symbol))
        if cached:
            return cached[-1]
        bars = await self._bootstrap_recent_bars(symbol, 2)
        if include_incomplete and symbol in self._latest_bar_by_symbol:
            return self._latest_bar_by_symbol[symbol]
        return bars[-1]

    async def fetch_funding_context(self, symbol: str, *, as_of_ms: int, history_limit: int = 8) -> dict[str, Any]:
        cache_key = ("funding", symbol, history_limit, as_of_ms // INTERVAL_TO_MS["8h"])
        if cache_key in self._feature_cache:
            return dict(self._feature_cache[cache_key])
        rows, issue = await self._fetch_feature_json(
            endpoint_key=f"{symbol}:fundingRate",
            url=f"{self.base_url}/fapi/v1/fundingRate",
            params={"symbol": symbol, "endTime": as_of_ms, "limit": history_limit},
            default_backoff_ms=15_000,
            source="fundingRate",
        )
        rows = sorted((rows or []), key=lambda item: int(item["fundingTime"]))
        funding_rate = None
        previous_rate = None
        if rows:
            funding_rate = Decimal(str(rows[-1]["fundingRate"]))
            if len(rows) >= 2:
                previous_rate = Decimal(str(rows[-2]["fundingRate"]))
        next_funding_ms = None
        if rows:
            next_funding_ms = int(rows[-1]["fundingTime"]) + INTERVAL_TO_MS["8h"]
        elif as_of_ms > 0:
            next_funding_ms = ((as_of_ms // INTERVAL_TO_MS["8h"]) + 1) * INTERVAL_TO_MS["8h"]
        result = {
            "funding_rate": str(funding_rate) if funding_rate is not None else None,
            "funding_rate_prev": str(previous_rate) if previous_rate is not None else None,
            "funding_rate_change": (str(funding_rate - previous_rate) if funding_rate is not None and previous_rate is not None else None),
            "time_to_next_funding_ms": (max(next_funding_ms - as_of_ms, 0) if next_funding_ms is not None else None),
            "source": "fundingRate",
            "history_count": len(rows),
        }
        if issue is not None:
            result.update(issue)
        self._feature_cache[cache_key] = dict(result)
        return result

    async def fetch_open_interest_context(
        self,
        symbol: str,
        *,
        as_of_ms: int,
        period: str = "5m",
        lookback_points: int = 13,
    ) -> dict[str, Any]:
        period_ms = INTERVAL_TO_MS.get(period, 5 * 60_000)
        cache_key = ("open_interest", symbol, period, lookback_points, as_of_ms // period_ms)
        if cache_key in self._feature_cache:
            return dict(self._feature_cache[cache_key])

        now_ms = int(time.time() * 1000)
        current_payload = None
        current_issue = None
        if abs(now_ms - as_of_ms) <= period_ms * 2:
            current_payload, current_issue = await self._fetch_feature_json(
                endpoint_key=f"{symbol}:openInterest:current",
                url=f"{self.base_url}/fapi/v1/openInterest",
                params={"symbol": symbol},
                default_backoff_ms=15_000,
                source="openInterest",
            )
        history_rows, history_issue = await self._fetch_feature_json(
            endpoint_key=f"{symbol}:openInterestHist:{period}",
            url=f"{self.base_url}/futures/data/openInterestHist",
            params={"symbol": symbol, "period": period, "limit": lookback_points, "endTime": as_of_ms},
            default_backoff_ms=15_000,
            source="openInterestHist",
        )
        history_rows = sorted((history_rows or []), key=lambda item: int(item["timestamp"]))
        current_oi = (
            Decimal(str(current_payload["openInterest"]))
            if current_payload is not None and current_payload.get("openInterest") is not None
            else None
        )
        previous_oi = Decimal(str(history_rows[-2]["sumOpenInterest"])) if len(history_rows) >= 2 else None
        reference_oi = Decimal(str(history_rows[-1]["sumOpenInterest"])) if history_rows else current_oi
        open_interest_change = (
            reference_oi - previous_oi if reference_oi is not None and previous_oi is not None else None
        )
        open_interest_change_pct = (
            (open_interest_change / previous_oi) if open_interest_change is not None and previous_oi not in {None, Decimal("0")} else None
        )
        open_interest_value = Decimal(str(history_rows[-1]["sumOpenInterestValue"])) if history_rows else None
        result = {
            "open_interest": str(reference_oi) if reference_oi is not None else None,
            "open_interest_change": str(open_interest_change) if open_interest_change is not None else None,
            "open_interest_change_pct": str(open_interest_change_pct) if open_interest_change_pct is not None else None,
            "open_interest_value": str(open_interest_value) if open_interest_value is not None else None,
            "current_open_interest": str(current_oi) if current_oi is not None else None,
            "source": "openInterestHist",
            "history_count": len(history_rows),
        }
        if current_issue is not None:
            result["current_source_error"] = current_issue["source_error"]
        if history_issue is not None:
            result.update(history_issue)
        self._feature_cache[cache_key] = dict(result)
        return result

    async def fetch_premium_context(self, symbol: str, *, as_of_ms: int, interval: str = "5m") -> dict[str, Any]:
        period_ms = INTERVAL_TO_MS.get(interval, 5 * 60_000)
        cache_key = ("premium", symbol, interval, as_of_ms // period_ms)
        if cache_key in self._feature_cache:
            return dict(self._feature_cache[cache_key])
        now_ms = int(time.time() * 1000)
        mark_payload = None
        premium_rows = None
        mark_issue = None
        premium_issue = None
        if abs(now_ms - as_of_ms) <= period_ms * 2:
            mark_payload, mark_issue = await self._fetch_feature_json(
                endpoint_key=f"{symbol}:premiumIndex:current",
                url=f"{self.base_url}/fapi/v1/premiumIndex",
                params={"symbol": symbol},
                default_backoff_ms=15_000,
                source="premiumIndex",
            )
            premium_rows, premium_issue = await self._fetch_feature_json(
                endpoint_key=f"{symbol}:premiumIndexKlines:{interval}",
                url=f"{self.base_url}/fapi/v1/premiumIndexKlines",
                params={"symbol": symbol, "interval": interval, "endTime": as_of_ms, "limit": 2},
                default_backoff_ms=15_000,
                source="premiumIndexKlines",
            )
            rows = premium_rows or []
            mark_price = Decimal(str(mark_payload["markPrice"])) if mark_payload and mark_payload.get("markPrice") is not None else None
            index_price = Decimal(str(mark_payload["indexPrice"])) if mark_payload and mark_payload.get("indexPrice") is not None else None
        else:
            mark_rows, mark_issue = await self._fetch_feature_json(
                endpoint_key=f"{symbol}:markPriceKlines:{interval}",
                url=f"{self.base_url}/fapi/v1/markPriceKlines",
                params={"symbol": symbol, "interval": interval, "endTime": as_of_ms, "limit": 2},
                default_backoff_ms=15_000,
                source="markPriceKlines",
            )
            index_rows, index_issue = await self._fetch_feature_json(
                endpoint_key=f"{symbol}:indexPriceKlines:{interval}",
                url=f"{self.base_url}/fapi/v1/indexPriceKlines",
                params={"symbol": symbol, "interval": interval, "endTime": as_of_ms, "limit": 2},
                default_backoff_ms=15_000,
                source="indexPriceKlines",
            )
            premium_rows, premium_issue = await self._fetch_feature_json(
                endpoint_key=f"{symbol}:premiumIndexKlines:{interval}",
                url=f"{self.base_url}/fapi/v1/premiumIndexKlines",
                params={"symbol": symbol, "interval": interval, "endTime": as_of_ms, "limit": 2},
                default_backoff_ms=15_000,
                source="premiumIndexKlines",
            )
            rows = premium_rows or []
            latest_mark_row = mark_rows[-1] if mark_rows else None
            latest_index_row = index_rows[-1] if index_rows else None
            mark_price = Decimal(str(latest_mark_row[4])) if latest_mark_row is not None else None
            index_price = Decimal(str(latest_index_row[4])) if latest_index_row is not None else None
            if mark_issue is not None and premium_issue is None:
                premium_issue = mark_issue
            if index_issue is not None and premium_issue is None:
                premium_issue = index_issue
        current_row = rows[-1] if rows else None
        previous_row = rows[-2] if len(rows) >= 2 else None
        premium_close = Decimal(str(current_row[4])) if current_row is not None else None
        premium_prev = Decimal(str(previous_row[4])) if previous_row is not None else None
        basis = (mark_price - index_price) if mark_price is not None and index_price is not None else None
        basis_rate = (basis / index_price) if basis is not None and index_price not in {None, Decimal("0")} else None
        result = {
            "mark_price": str(mark_price) if mark_price is not None else None,
            "index_price": str(index_price) if index_price is not None else None,
            "basis": str(basis) if basis is not None else None,
            "basis_rate": str(basis_rate) if basis_rate is not None else None,
            "premium_close": str(premium_close) if premium_close is not None else None,
            "premium_change": (str(premium_close - premium_prev) if premium_close is not None and premium_prev is not None else None),
            "next_funding_time_ms": (
                int(mark_payload["nextFundingTime"])
                if mark_payload is not None and mark_payload.get("nextFundingTime") is not None
                else None
            ),
            "source": "premiumIndexKlines",
        }
        if mark_issue is not None and premium_issue is None:
            result.update(mark_issue)
        elif premium_issue is not None:
            result.update(premium_issue)
        self._feature_cache[cache_key] = dict(result)
        return result

    async def get_microstructure_snapshot(
        self,
        symbol: str,
        *,
        windows_seconds: tuple[int, ...] = (10, 20, 30, 60),
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        trades = list(self._agg_trades(symbol))
        last_trade_ms = self._last_trade_ws_message_ms_by_symbol.get(symbol)
        last_book_ms = self._last_book_ws_message_ms_by_symbol.get(symbol)
        trade_flow_available = last_trade_ms is not None and (now_ms - last_trade_ms) <= self.ws_stale_after_ms
        top_of_book_available = last_book_ms is not None and (now_ms - last_book_ms) <= self.ws_stale_after_ms
        entry_ready = trade_flow_available and top_of_book_available
        blocking_reasons: list[str] = []
        warning_reasons: list[str] = []
        if not trade_flow_available:
            blocking_reasons.append("missing_trade_stream")
            if last_trade_ms is not None:
                blocking_reasons[-1] = "stale_trade_stream"
        if not top_of_book_available:
            blocking_reasons.append("missing_book_ticker_stream")
            if last_book_ms is not None:
                blocking_reasons[-1] = "stale_book_ticker_stream"
        last_depth_ms = self._last_depth_ws_message_ms_by_symbol.get(symbol)
        order_book = self._order_book(symbol)
        counters = self._depth_counters(symbol)
        order_book_health_state = self._order_book_health_state(symbol, now_ms)
        depth_sync_state = self._depth_sync_state(symbol, now_ms)
        validity_issue = self._order_book_validity_issue(symbol, order_book)
        depth_healthy = depth_sync_state == DEPTH_SYNC_SYNCED and validity_issue is None
        if last_depth_ms is None:
            warning_reasons.append("missing_depth_stream")
        elif depth_sync_state == DEPTH_SYNC_STALE:
            warning_reasons.append("stale_depth_stream")
        elif depth_sync_state in {DEPTH_SYNC_BUFFERING, DEPTH_SYNC_RESYNC_PENDING, DEPTH_SYNC_BACKOFF}:
            warning_reasons.append("order_book_unsynced")
        elif validity_issue is not None:
            warning_reasons.append("order_book_invalid")
        if order_book.last_bootstrap_error:
            warning_reasons.append("bootstrap_error")
        book = self._book_ticker_by_symbol.get(symbol)
        trade_flow_windows: dict[str, Any] = {}

        for window_seconds in sorted(set(windows_seconds)):
            threshold_ms = now_ms - (window_seconds * 1000)
            window_trades = [trade for trade in trades if trade["time_ms"] >= threshold_ms]
            buy_qty = sum((trade["qty"] for trade in window_trades if trade["aggressor_side"] == "buy"), start=Decimal("0"))
            sell_qty = sum((trade["qty"] for trade in window_trades if trade["aggressor_side"] == "sell"), start=Decimal("0"))
            buy_qty_raw = sum((trade["raw_qty"] for trade in window_trades if trade["aggressor_side"] == "buy"), start=Decimal("0"))
            sell_qty_raw = sum((trade["raw_qty"] for trade in window_trades if trade["aggressor_side"] == "sell"), start=Decimal("0"))
            buy_notional = sum(
                (trade["notional"] for trade in window_trades if trade["aggressor_side"] == "buy"),
                start=Decimal("0"),
            )
            sell_notional = sum(
                (trade["notional"] for trade in window_trades if trade["aggressor_side"] == "sell"),
                start=Decimal("0"),
            )
            buy_notional_raw = sum(
                (trade["raw_notional"] for trade in window_trades if trade["aggressor_side"] == "buy"),
                start=Decimal("0"),
            )
            sell_notional_raw = sum(
                (trade["raw_notional"] for trade in window_trades if trade["aggressor_side"] == "sell"),
                start=Decimal("0"),
            )
            total_qty = buy_qty + sell_qty
            total_notional = buy_notional + sell_notional
            signed_qty = buy_qty - sell_qty
            signed_notional = buy_notional - sell_notional
            buy_trade_count = sum(1 for trade in window_trades if trade["aggressor_side"] == "buy")
            sell_trade_count = sum(1 for trade in window_trades if trade["aggressor_side"] == "sell")
            rpi_adjusted_trade_count = sum(1 for trade in window_trades if trade["normal_qty"] is not None)
            ratio = (signed_qty / total_qty) if total_qty > 0 else Decimal("0")
            signed_sqrt_notional, sqrt_total_notional, sqrt_ratio = _signed_sqrt_notional_metrics(window_trades)
            trade_sign_acf_lag1 = _trade_sign_autocorrelation(window_trades)
            price_response = _trade_price_response_metrics(window_trades, sqrt_total_notional)
            trade_flow_windows[str(window_seconds)] = {
                "trade_count": len(window_trades),
                "buy_trade_count": buy_trade_count,
                "sell_trade_count": sell_trade_count,
                "buy_qty": str(buy_qty),
                "sell_qty": str(sell_qty),
                "buy_notional": str(buy_notional),
                "sell_notional": str(sell_notional),
                "signed_qty": str(signed_qty),
                "signed_notional": str(signed_notional),
                "signed_ratio": str(ratio),
                "total_notional": str(total_notional),
                "sqrt_signed_notional": str(signed_sqrt_notional),
                "sqrt_total_notional": str(sqrt_total_notional),
                "sqrt_signed_ratio": str(sqrt_ratio),
                "trade_sign_acf_lag1": str(trade_sign_acf_lag1) if trade_sign_acf_lag1 is not None else None,
                **price_response,
                "raw_buy_qty": str(buy_qty_raw),
                "raw_sell_qty": str(sell_qty_raw),
                "raw_total_notional": str(buy_notional_raw + sell_notional_raw),
                "rpi_adjusted_trade_count": rpi_adjusted_trade_count,
                "qty_source": "nq_or_q",
                "impact_transform": "sqrt_notional",
            }

        queue_feature_status = "available" if depth_healthy else ("degraded" if entry_ready else "unavailable")
        availability = {
            "trade_flow_available": trade_flow_available,
            "top_of_book_available": top_of_book_available,
            "queue_depth_available": depth_healthy,
            "depth_depletion_available": depth_healthy,
        }
        snapshot: dict[str, Any] = {
            "symbol": symbol,
            "healthy": entry_ready,
            "entry_ready": entry_ready,
            "depth_healthy": depth_healthy,
            "queue_imbalance_available": depth_healthy,
            "availability": availability,
            "trade_flow_available": trade_flow_available,
            "top_of_book_available": top_of_book_available,
            "depth_depletion_available": depth_healthy,
            "queue_feature_status": queue_feature_status,
            "degraded": entry_ready and not depth_healthy,
            "reasons": blocking_reasons,
            "warnings": warning_reasons,
            "bootstrap_error": order_book.last_bootstrap_error,
            "book_validity_issue": validity_issue,
            "depth_bootstrap_retry_after_ms": order_book.next_bootstrap_after_ms if order_book.next_bootstrap_after_ms > now_ms else None,
            **counters.as_dict(),
            "depth_update_speed_ms": self.depth_update_speed_ms,
            "depth_snapshot_limit": self.depth_snapshot_limit,
            "depth_required_levels": self.depth_required_levels,
            "order_book_mode": "diff_depth_local_book",
            "order_book_health_state": order_book_health_state,
            "depth_sync_state": depth_sync_state,
            "order_book_synced": order_book.synced,
            "last_snapshot_time_ms": order_book.snapshot_time_ms,
            "last_bootstrap_attempt_ms": order_book.last_bootstrap_attempt_ms,
            "last_resync_request_ms": order_book.last_resync_request_ms,
            "last_resync_reason": order_book.last_resync_reason,
            "last_good_depth_time_ms": order_book.last_good_depth_time_ms,
            "last_gap_time_ms": order_book.last_gap_time_ms,
            "last_invalid_book_time_ms": order_book.last_invalid_book_time_ms,
            "last_rate_limit_time_ms": order_book.last_rate_limit_time_ms,
            "last_planned_reconnect_time_ms": order_book.last_planned_reconnect_time_ms,
            "next_planned_reconnect_time_ms": (
                order_book.next_planned_reconnect_time_ms
                if order_book.next_planned_reconnect_time_ms and order_book.next_planned_reconnect_time_ms > now_ms
                else None
            ),
            "buffered_event_count": len(order_book.buffered_events),
            "repair_in_flight": order_book.repair_in_flight,
            "backoff_until_ms": order_book.next_bootstrap_after_ms if order_book.next_bootstrap_after_ms > now_ms else None,
            "rest_budget_state": self._rest_budget.snapshot(now_ms),
            "last_trade_time_ms": last_trade_ms,
            "last_book_ticker_time_ms": last_book_ms,
            "last_depth_time_ms": last_depth_ms,
            "windows": trade_flow_windows,
            "top_of_book_imbalance": None,
            "queue_imbalance_l1": None,
            "queue_imbalance_l5": None,
            "queue_imbalance_l10": None,
        }
        if book is not None:
            denominator = book["bid_qty"] + book["ask_qty"]
            top_of_book_imbalance = (book["bid_qty"] - book["ask_qty"]) / denominator if denominator > 0 else Decimal("0")
            mid_price = (book["bid_price"] + book["ask_price"]) / Decimal("2")
            spread = book["ask_price"] - book["bid_price"]
            spread_bps = (spread / mid_price) * Decimal("10000") if mid_price > 0 else Decimal("0")
            snapshot.update(
                {
                    "best_bid_price": str(book["bid_price"]),
                    "best_bid_qty": str(book["bid_qty"]),
                    "best_ask_price": str(book["ask_price"]),
                    "best_ask_qty": str(book["ask_qty"]),
                    "mid_price": str(mid_price),
                    "spread_bps": str(spread_bps),
                    "top_of_book_imbalance": str(top_of_book_imbalance),
                }
            )
        local_depth_snapshot = self._local_book_snapshot(symbol) if depth_healthy else None
        if local_depth_snapshot is not None:
            snapshot["local_order_book"] = local_depth_snapshot
            snapshot["queue_imbalance_l1"] = local_depth_snapshot["queue_imbalance_l1"]
            snapshot["queue_imbalance_l5"] = local_depth_snapshot["queue_imbalance_l5"]
            snapshot["queue_imbalance_l10"] = local_depth_snapshot["queue_imbalance_l10"]
            snapshot["best_level_depth"] = {
                "bid_qty": local_depth_snapshot["best_bid_qty"],
                "ask_qty": local_depth_snapshot["best_ask_qty"],
            }
            snapshot["depth_depletion"] = {
                "bid_l5": local_depth_snapshot["bid_depth_l5_depletion"],
                "ask_l5": local_depth_snapshot["ask_depth_l5_depletion"],
                "bid_l10": local_depth_snapshot["bid_depth_l10_depletion"],
                "ask_l10": local_depth_snapshot["ask_depth_l10_depletion"],
            }
        return snapshot

    async def _ensure_stream(self, symbol: str) -> None:
        self._ensure_stream_tasks(symbol)
        now_ms = int(time.time() * 1000)
        if symbol not in self._latest_bar_by_symbol or len(self._closed_bars(symbol)) < 2:
            retry_after_ms = self._next_bar_bootstrap_after_ms_by_symbol.get(symbol, 0)
            if retry_after_ms > now_ms:
                raise RuntimeError(
                    f"Binance klines temporarily backed off until {retry_after_ms} after rate limiting; "
                    f"last error: {self._last_bar_bootstrap_error_by_symbol.get(symbol, 'unknown')}"
                )
            await self._bootstrap_recent_bars(symbol, 2)

    def _ensure_stream_tasks(self, symbol: str) -> None:
        self._stream_started_ms_by_symbol.setdefault(symbol, int(time.time() * 1000))
        for bundle_key, route, stream_specs in self._stream_bundle_specs(symbol):
            self._ensure_stream_bundle_task(symbol, bundle_key, route, stream_specs)
        state = self._order_book(symbol)
        if state.sync_state == DEPTH_SYNC_COLD:
            state.sync_state = DEPTH_SYNC_BUFFERING

    async def _send_request(
        self,
        *,
        url: str,
        params: dict[str, Any],
        weight: int,
        endpoint_name: str,
    ) -> httpx.Response:
        await self._rest_budget.wait_for_capacity(weight=weight, reason=endpoint_name)
        response = await self._client.get(url, params=params)
        await self._rest_budget.note_response(response, weight=weight, reason=endpoint_name)
        return response

    def _kline_request_weight(self, limit: int) -> int:
        if limit < 100:
            return 1
        if limit < 500:
            return 2
        if limit <= 1000:
            return 5
        return 10

    def _depth_snapshot_request_weight(self, limit: int) -> int:
        if limit <= 50:
            return 2
        if limit == 100:
            return 5
        if limit <= 500:
            return 10
        return 20

    def _retry_after_ms(self, exc: httpx.HTTPStatusError, *, default_ms: int) -> int:
        retry_after_header = exc.response.headers.get("Retry-After")
        if retry_after_header:
            try:
                return max(int(float(retry_after_header) * 1000), 1_000)
            except ValueError:
                return default_ms
        return default_ms

    def _feature_issue_payload(
        self,
        *,
        source: str,
        error: str,
        status_code: int | None,
        backoff_until_ms: int | None,
        rate_limited: bool,
    ) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        payload: dict[str, Any] = {
            "source": source,
            "source_error": error,
            "source_status_code": status_code,
            "rate_limited": rate_limited,
        }
        if backoff_until_ms is not None and backoff_until_ms > now_ms:
            payload["backoff_until_ms"] = backoff_until_ms
            payload["retry_after_ms"] = backoff_until_ms - now_ms
        return payload

    async def _fetch_feature_json(
        self,
        *,
        endpoint_key: str,
        url: str,
        params: dict[str, Any],
        default_backoff_ms: int,
        source: str,
    ) -> tuple[Any | None, dict[str, Any] | None]:
        now_ms = int(time.time() * 1000)
        backoff_until_ms = self._feature_backoff_until_by_key.get(endpoint_key)
        if backoff_until_ms is not None and backoff_until_ms > now_ms:
            return None, self._feature_issue_payload(
                source=source,
                error=self._feature_last_error_by_key.get(endpoint_key, f"{source} temporarily backed off"),
                status_code=None,
                backoff_until_ms=backoff_until_ms,
                rate_limited=True,
            )
        try:
            response = await self._send_request(
                url=url,
                params=params,
                weight=1,
                endpoint_name=source,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_text = str(exc)
            self._feature_last_error_by_key[endpoint_key] = error_text
            backoff_until_ms = None
            rate_limited = exc.response.status_code in {418, 429}
            if rate_limited:
                computed_backoff_ms = self._retry_after_ms(
                    exc,
                    default_ms=(120_000 if exc.response.status_code == 418 else default_backoff_ms),
                )
                backoff_until_ms = int(time.time() * 1000) + computed_backoff_ms
                self._feature_backoff_until_by_key[endpoint_key] = backoff_until_ms
            return None, self._feature_issue_payload(
                source=source,
                error=error_text,
                status_code=exc.response.status_code,
                backoff_until_ms=backoff_until_ms,
                rate_limited=rate_limited,
            )
        except httpx.HTTPError as exc:
            error_text = str(exc)
            self._feature_last_error_by_key[endpoint_key] = error_text
            return None, self._feature_issue_payload(
                source=source,
                error=error_text,
                status_code=None,
                backoff_until_ms=None,
                rate_limited=False,
            )
        self._feature_backoff_until_by_key.pop(endpoint_key, None)
        self._feature_last_error_by_key.pop(endpoint_key, None)
        return response.json(), None

    def _ensure_stream_task(self, symbol: str, stream_type: str, stream_name: str) -> None:
        task_key = f"{symbol}:{stream_type}"
        task = self._stream_tasks.get(task_key)
        if task is None or task.done():
            self._stream_tasks[task_key] = asyncio.create_task(self._run_stream(symbol, stream_type, stream_name))

    def _depth_stream_name(self, symbol: str) -> str:
        return f"{symbol.lower()}@depth" if self.depth_update_speed_ms == 250 else f"{symbol.lower()}@depth@{self.depth_update_speed_ms}ms"

    def _stream_bundle_specs(self, symbol: str) -> list[tuple[str, str, list[tuple[str, str]]]]:
        return [
            (
                BINANCE_STREAM_BUNDLE_MARKET,
                BINANCE_STREAM_ROUTE_MARKET,
                [
                    ("kline", f"{symbol.lower()}@kline_{BINANCE_15M_STREAM}"),
                    ("aggTrade", f"{symbol.lower()}@aggTrade"),
                ],
            ),
            (
                BINANCE_STREAM_BUNDLE_PUBLIC,
                BINANCE_STREAM_ROUTE_PUBLIC,
                [
                    ("bookTicker", f"{symbol.lower()}@bookTicker"),
                    ("depth", self._depth_stream_name(symbol)),
                ],
            ),
        ]

    def _ensure_stream_bundle_task(
        self,
        symbol: str,
        bundle_key: str,
        route: str,
        stream_specs: list[tuple[str, str]],
    ) -> None:
        task_key = f"{symbol}:{bundle_key}"
        lifecycle = self._stream_bundle_lifecycle_by_key.get(task_key)
        if lifecycle is None:
            self._stream_bundle_lifecycle_by_key[task_key] = StreamBundleLifecycle(
                route=route,
                stream_types=tuple(stream_type for stream_type, _ in stream_specs),
                stream_names=tuple(stream_name for _, stream_name in stream_specs),
            )
        else:
            lifecycle.route = route
            lifecycle.stream_types = tuple(stream_type for stream_type, _ in stream_specs)
            lifecycle.stream_names = tuple(stream_name for _, stream_name in stream_specs)
        task = self._stream_tasks.get(task_key)
        if task is None or task.done():
            self._stream_tasks[task_key] = asyncio.create_task(
                self._run_stream_bundle(symbol, bundle_key, route, stream_specs)
            )

    def _stream_route(self, stream_type: str) -> str:
        return BINANCE_STREAM_ROUTE_BY_TYPE.get(stream_type, BINANCE_STREAM_ROUTE_MARKET)

    def _stream_url(self, stream_type: str, stream_name: str) -> str:
        route = self._stream_route(stream_type)
        return f"{self.ws_root_url}/{route}/ws/{stream_name}"

    def _stream_bundle_url(self, route: str, stream_names: list[str]) -> str:
        return f"{self.ws_root_url}/{route}/stream?streams={'/'.join(stream_names)}"

    def _next_planned_reconnect_ms(self, connected_at_ms: int) -> int:
        max_jitter_ms = max(BINANCE_WS_SESSION_LIMIT_MS - self.websocket_planned_reconnect_ms - 1, 0)
        jitter_ms = min(self.websocket_planned_reconnect_jitter_ms, max_jitter_ms)
        return connected_at_ms + self.websocket_planned_reconnect_ms + random.randint(0, jitter_ms)

    def _set_stream_error(self, symbol: str, stream_types: list[str], detail: str | None) -> None:
        if detail is None:
            return
        for stream_type in stream_types:
            self._last_stream_error_by_stream[f"{symbol}:{stream_type}"] = detail

    def _clear_stream_error(self, symbol: str, stream_type: str) -> None:
        self._last_stream_error_by_stream.pop(f"{symbol}:{stream_type}", None)

    def _closed_bars(self, symbol: str) -> deque[Bar]:
        return self._closed_bars_by_symbol.setdefault(symbol, deque(maxlen=self._cache_limit))

    def _agg_trades(self, symbol: str) -> deque[dict[str, Any]]:
        return self._agg_trades_by_symbol.setdefault(symbol, deque(maxlen=self._cache_limit * 32))

    def _order_book(self, symbol: str) -> LocalOrderBookState:
        state = self._local_order_book_by_symbol.get(symbol)
        if state is None:
            state = LocalOrderBookState(
                buffered_events=deque(maxlen=self.depth_max_buffer_events),
                depth_history=deque(maxlen=512),
            )
            self._local_order_book_by_symbol[symbol] = state
        return state

    def _depth_counters(self, symbol: str) -> DepthHealthCounters:
        return self._depth_counters_by_symbol.setdefault(symbol, DepthHealthCounters())

    def _depth_bootstrap_lock(self, symbol: str) -> asyncio.Lock:
        return self._depth_bootstrap_locks.setdefault(symbol, asyncio.Lock())

    async def _bootstrap_recent_bars(self, symbol: str, limit: int) -> list[Bar]:
        try:
            rows = await self._request_klines_with_retry(
                {"symbol": symbol, "interval": BINANCE_15M_STREAM, "limit": limit + 1},
                include_incomplete=True,
                max_attempts=1,
            )
        except httpx.HTTPStatusError as exc:
            self._last_bar_bootstrap_error_by_symbol[symbol] = str(exc)
            default_backoff_ms = 120_000 if exc.response.status_code == 418 else 15_000
            self._next_bar_bootstrap_after_ms_by_symbol[symbol] = int(time.time() * 1000) + self._retry_after_ms(
                exc,
                default_ms=default_backoff_ms,
            )
            raise RuntimeError(
                "Binance kline bootstrap rate limited. "
                f"HTTP {exc.response.status_code}; backing off until {self._next_bar_bootstrap_after_ms_by_symbol[symbol]}"
            ) from exc
        if len(rows) < limit:
            raise ValueError(f"insufficient Binance bars for {symbol}")
        closed_rows = rows[:-1] if len(rows) > limit else rows
        bars = [_bar_from_row(row) for row in closed_rows[-limit:]]
        self._replace_closed_bars(symbol, bars)
        if rows:
            self._latest_bar_by_symbol[symbol] = _bar_from_row(rows[-1])
        self._last_bar_bootstrap_error_by_symbol.pop(symbol, None)
        self._next_bar_bootstrap_after_ms_by_symbol.pop(symbol, None)
        return bars

    async def _request_klines_with_retry(
        self,
        params: dict[str, Any],
        *,
        include_incomplete: bool,
        max_attempts: int = 4,
    ) -> list[list[Any]]:
        attempt = 0
        last_exc: Exception | None = None
        while attempt < max_attempts:
            try:
                response = await self._send_request(
                    url=f"{self.base_url}/fapi/v1/klines",
                    params=params,
                    weight=self._kline_request_weight(int(params.get("limit", 500))),
                    endpoint_name="klines",
                )
                response.raise_for_status()
                rows = response.json()
                if not include_incomplete and rows:
                    now_ms = int(time.time() * 1000)
                    rows = [row for row in rows if int(row[6]) <= now_ms]
                return rows
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in {418, 429} or attempt >= max_attempts - 1:
                    raise
                sleep_ms = self._retry_after_ms(
                    exc,
                    default_ms=(120_000 if exc.response.status_code == 418 else 15_000 * (attempt + 1)),
                )
                await asyncio.sleep(sleep_ms / 1000.0)
            attempt += 1
        if last_exc is not None:
            raise last_exc
        return []

    async def _bootstrap_order_book(self, symbol: str) -> None:
        async with self._depth_bootstrap_lock(symbol):
            state = self._order_book(symbol)
            now_ms = int(time.time() * 1000)
            state.last_bootstrap_attempt_ms = now_ms
            state.sync_state = DEPTH_SYNC_BOOTSTRAPPING
            try:
                response = await self._send_request(
                    url=f"{self.base_url}/fapi/v1/depth",
                    params={"symbol": symbol, "limit": self.depth_snapshot_limit},
                    weight=self._depth_snapshot_request_weight(self.depth_snapshot_limit),
                    endpoint_name="depth_snapshot",
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                state.synced = False
                state.last_bootstrap_error = str(exc)
                retry_after_ms = self._retry_after_ms(exc, default_ms=self.depth_snapshot_default_backoff_ms)
                retry_after_ms += random.randint(0, min(1_000, max(retry_after_ms // 5, 250)))
                state.next_bootstrap_after_ms = now_ms + retry_after_ms
                if exc.response.status_code in {418, 429}:
                    counters = self._depth_counters(symbol)
                    counters.rate_limit_count += 1
                    state.last_rate_limit_time_ms = now_ms
                    state.sync_state = DEPTH_SYNC_BACKOFF
                    await self._rest_budget.note_rate_limit(retry_after_ms=retry_after_ms, reason="depth_snapshot")
                else:
                    state.sync_state = DEPTH_SYNC_RESYNC_PENDING
                self._last_stream_error_by_stream[f"{symbol}:depth"] = str(exc)
                raise
            payload = response.json()
            snapshot_update_id = int(payload["lastUpdateId"])
            state.bids = {
                Decimal(str(price)): Decimal(str(qty))
                for price, qty in payload.get("bids", [])
                if Decimal(str(qty)) > Decimal("0")
            }
            state.asks = {
                Decimal(str(price)): Decimal(str(qty))
                for price, qty in payload.get("asks", [])
                if Decimal(str(qty)) > Decimal("0")
            }
            state.last_update_id = snapshot_update_id
            state.last_event_u = snapshot_update_id
            state.synced = True
            state.snapshot_time_ms = now_ms
            state.last_good_depth_time_ms = now_ms
            state.last_bootstrap_error = None
            state.next_bootstrap_after_ms = 0
            state.sync_state = DEPTH_SYNC_SYNCED
            self._raise_if_order_book_invalid(symbol, state, event_time_ms=now_ms)
            self._record_depth_history(state, event_time_ms=now_ms)

            buffered_events = list(state.buffered_events)
            replay_events = [event for event in buffered_events if int(event["u"]) >= snapshot_update_id]
            dropped_events = max(len(buffered_events) - len(replay_events), 0)
            if dropped_events:
                self._depth_counters(symbol).dropped_buffered_event_count += dropped_events
            if replay_events:
                first_index = next(
                    (
                        index
                        for index, event in enumerate(replay_events)
                        if self._depth_event_aligns_snapshot(event, snapshot_update_id)
                    ),
                    None,
                )
                if first_index is None:
                    state.synced = False
                    state.sync_state = DEPTH_SYNC_RESYNC_PENDING
                    state.last_bootstrap_error = f"unable to align Binance depth snapshot for {symbol}"
                    state.buffered_events = deque(replay_events, maxlen=self.depth_max_buffer_events)
                    state.next_bootstrap_after_ms = int(time.time() * 1000) + self.depth_resync_min_interval_ms
                    self._depth_counters(symbol).alignment_mismatch_count += 1
                    raise ValueError(f"unable to align Binance depth snapshot for {symbol}")
                state.buffered_events.clear()
                if first_index:
                    self._depth_counters(symbol).dropped_buffered_event_count += first_index
                for event in replay_events[first_index:]:
                    self._apply_depth_event(symbol, event)
            else:
                state.buffered_events.clear()
            self._depth_counters(symbol).resync_count += 1

    async def _run_stream(self, symbol: str, stream_type: str, stream_name: str) -> None:
        url = self._stream_url(stream_type, stream_name)
        task_key = f"{symbol}:{stream_type}"
        reconnect_sleep_ms = self.depth_reconnect_backoff_ms if stream_type == "depth" else 1_000
        while True:
            disconnect_detail: str | None = None
            try:
                async with self._websocket_connect(url) as websocket:
                    if stream_type == "depth":
                        state = self._order_book(symbol)
                        if state.sync_state == DEPTH_SYNC_COLD:
                            state.sync_state = DEPTH_SYNC_BUFFERING
                        reconnect_sleep_ms = self.depth_reconnect_backoff_ms
                    async for raw_message in websocket:
                        payload = json.loads(raw_message)
                        if stream_type == "kline":
                            self._handle_kline_message(payload)
                        elif stream_type == "aggTrade":
                            self._handle_agg_trade_message(payload)
                        elif stream_type == "bookTicker":
                            self._handle_book_ticker_message(payload)
                        elif stream_type == "depth":
                            self._handle_depth_message(payload)
                disconnect_detail = "websocket_stream_closed"
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                disconnect_detail = str(exc)
            self._last_stream_error_by_stream[task_key] = disconnect_detail
            if stream_type == "depth":
                self._handle_depth_disconnect(symbol, disconnect_detail)
            await asyncio.sleep(max(reconnect_sleep_ms, 250) / 1000.0)
            if stream_type == "depth":
                reconnect_sleep_ms = min(max(reconnect_sleep_ms * 2, self.depth_reconnect_backoff_ms), self.depth_reconnect_max_backoff_ms)

    async def _run_stream_bundle(
        self,
        symbol: str,
        bundle_key: str,
        route: str,
        stream_specs: list[tuple[str, str]],
    ) -> None:
        stream_types = [stream_type for stream_type, _ in stream_specs]
        url = self._stream_bundle_url(route, [stream_name for _, stream_name in stream_specs])
        task_key = f"{symbol}:{bundle_key}"
        lifecycle = self._stream_bundle_lifecycle_by_key.setdefault(
            task_key,
            StreamBundleLifecycle(
                route=route,
                stream_types=tuple(stream_types),
                stream_names=tuple(stream_name for _, stream_name in stream_specs),
            ),
        )
        has_depth = "depth" in stream_types
        reconnect_sleep_ms = self.depth_reconnect_backoff_ms if has_depth else 1_000
        while True:
            disconnect_detail: str | None = None
            planned_disconnect = False
            try:
                async with self._websocket_connect(url) as websocket:
                    connected_at_ms = int(time.time() * 1000)
                    planned_reconnect_at_ms = self._next_planned_reconnect_ms(connected_at_ms)
                    lifecycle.connected_at_ms = connected_at_ms
                    lifecycle.next_planned_reconnect_ms = planned_reconnect_at_ms
                    lifecycle.last_disconnect_reason = None
                    if has_depth:
                        state = self._order_book(symbol)
                        if state.sync_state == DEPTH_SYNC_COLD:
                            state.sync_state = DEPTH_SYNC_BUFFERING
                        state.next_planned_reconnect_time_ms = planned_reconnect_at_ms
                        reconnect_sleep_ms = self.depth_reconnect_backoff_ms
                    while True:
                        timeout_seconds = max((planned_reconnect_at_ms - int(time.time() * 1000)) / 1000.0, 0.0)
                        if timeout_seconds <= 0:
                            planned_disconnect = True
                            disconnect_detail = "planned_reconnect"
                            break
                        try:
                            raw_message = await asyncio.wait_for(websocket.recv(), timeout=timeout_seconds)
                        except asyncio.TimeoutError:
                            planned_disconnect = True
                            disconnect_detail = "planned_reconnect"
                            break
                        payload = json.loads(raw_message)
                        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
                            payload = payload["data"]
                        self._dispatch_stream_payload(payload)
                if not planned_disconnect:
                    disconnect_detail = "websocket_stream_closed"
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                disconnect_detail = str(exc)
            disconnected_at_ms = int(time.time() * 1000)
            lifecycle.connected_at_ms = None
            lifecycle.next_planned_reconnect_ms = None
            lifecycle.last_disconnect_reason = disconnect_detail
            if planned_disconnect:
                lifecycle.last_planned_reconnect_ms = disconnected_at_ms
                lifecycle.planned_reconnect_count += 1
                self._last_stream_error_by_stream.pop(task_key, None)
                for stream_type in stream_types:
                    self._clear_stream_error(symbol, stream_type)
            else:
                lifecycle.last_error_reconnect_ms = disconnected_at_ms
                lifecycle.error_reconnect_count += 1
                self._last_stream_error_by_stream[task_key] = disconnect_detail
                self._set_stream_error(symbol, stream_types, disconnect_detail)
            if has_depth:
                self._handle_depth_disconnect(
                    symbol,
                    disconnect_detail or "websocket_stream_closed",
                    planned=planned_disconnect,
                )
            await asyncio.sleep(max(reconnect_sleep_ms, 250) / 1000.0)
            if has_depth:
                reconnect_sleep_ms = min(max(reconnect_sleep_ms * 2, self.depth_reconnect_backoff_ms), self.depth_reconnect_max_backoff_ms)

    def _dispatch_stream_payload(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        event_type = payload.get("e")
        if event_type == "kline":
            self._handle_kline_message(payload)
        elif event_type == "aggTrade":
            self._handle_agg_trade_message(payload)
        elif event_type == "bookTicker":
            self._handle_book_ticker_message(payload)
        elif event_type == "depthUpdate":
            self._handle_depth_message(payload)

    def _handle_kline_message(self, payload: dict[str, Any]) -> None:
        if payload.get("e") != "kline":
            return
        symbol = str(payload.get("s") or "")
        kline = payload.get("k")
        if not symbol or not isinstance(kline, dict):
            return
        self._clear_stream_error(symbol, "kline")
        bar = _bar_from_kline(kline)
        now_ms = int(payload.get("E") or time.time() * 1000)
        self._last_kline_ws_message_ms_by_symbol[symbol] = now_ms
        self._latest_bar_by_symbol[symbol] = bar
        if bool(kline.get("x")):
            self._append_closed_bar(symbol, bar)

    def _handle_agg_trade_message(self, payload: dict[str, Any]) -> None:
        if payload.get("e") != "aggTrade":
            return
        symbol = str(payload.get("s") or "")
        if not symbol:
            return
        self._clear_stream_error(symbol, "aggTrade")
        price = Decimal(str(payload["p"]))
        raw_qty = Decimal(str(payload["q"]))
        normal_qty = Decimal(str(payload["nq"])) if payload.get("nq") is not None else None
        # Binance now exposes `nq` as the non-RPI quantity for aggTrade events.
        # When present, use it so signed flow stays aligned with the public order-book
        # streams, which explicitly exclude RPI liquidity.
        qty = normal_qty if normal_qty is not None else raw_qty
        is_buyer_maker = bool(payload.get("m"))
        aggressor_side = "sell" if is_buyer_maker else "buy"
        time_ms = int(payload.get("T") or payload.get("E") or time.time() * 1000)
        trade = {
            "time_ms": time_ms,
            "price": price,
            "qty": qty,
            "raw_qty": raw_qty,
            "normal_qty": normal_qty,
            "notional": price * qty,
            "raw_notional": price * raw_qty,
            "aggressor_side": aggressor_side,
        }
        trades = self._agg_trades(symbol)
        trades.append(trade)
        cutoff_ms = time_ms - max(self.ws_stale_after_ms, 120_000)
        while trades and trades[0]["time_ms"] < cutoff_ms:
            trades.popleft()
        self._last_trade_ws_message_ms_by_symbol[symbol] = int(payload.get("E") or time_ms)

    def _handle_book_ticker_message(self, payload: dict[str, Any]) -> None:
        if payload.get("e") != "bookTicker":
            return
        symbol = str(payload.get("s") or "")
        if not symbol:
            return
        self._clear_stream_error(symbol, "bookTicker")
        self._book_ticker_by_symbol[symbol] = {
            "bid_price": Decimal(str(payload["b"])),
            "bid_qty": Decimal(str(payload["B"])),
            "ask_price": Decimal(str(payload["a"])),
            "ask_qty": Decimal(str(payload["A"])),
            "time_ms": int(payload.get("E") or payload.get("T") or time.time() * 1000),
        }
        self._last_book_ws_message_ms_by_symbol[symbol] = int(payload.get("E") or time.time() * 1000)

    def _handle_depth_message(self, payload: dict[str, Any]) -> None:
        if payload.get("e") != "depthUpdate":
            return
        symbol = str(payload.get("s") or "")
        if not symbol:
            return
        self._clear_stream_error(symbol, "depth")
        event = {
            "symbol": symbol,
            "U": int(payload["U"]),
            "u": int(payload["u"]),
            "pu": int(payload.get("pu") or 0),
            "b": payload.get("b", []),
            "a": payload.get("a", []),
            "time_ms": int(payload.get("E") or payload.get("T") or time.time() * 1000),
        }
        state = self._order_book(symbol)
        self._last_depth_ws_message_ms_by_symbol[symbol] = event["time_ms"]
        state.last_depth_event_time_ms = event["time_ms"]
        if not state.synced or state.last_update_id is None:
            self._buffer_depth_event(symbol, state, event)
            return
        try:
            self._apply_depth_event(symbol, event)
        except ValueError as exc:
            state.synced = False
            state.sync_state = DEPTH_SYNC_RESYNC_PENDING
            state.last_gap_time_ms = event["time_ms"]
            state.last_bootstrap_error = str(exc)
            state.buffered_events.clear()
            self._buffer_depth_event(symbol, state, event)
            counters = self._depth_counters(symbol)
            if isinstance(exc, DepthBookInvalidError):
                state.last_invalid_book_time_ms = event["time_ms"]
            else:
                counters.gap_count += 1
            self._last_stream_error_by_stream[f"{symbol}:depth"] = str(exc)
            self._schedule_depth_resync_with_reason(
                symbol,
                reason="invalid_book" if isinstance(exc, DepthBookInvalidError) else "gap",
            )

    def _replace_closed_bars(self, symbol: str, bars: list[Bar]) -> None:
        cache = self._closed_bars(symbol)
        cache.clear()
        for bar in bars:
            cache.append(bar)

    def _append_closed_bar(self, symbol: str, bar: Bar) -> None:
        cache = self._closed_bars(symbol)
        if cache and cache[-1].time_ms == bar.time_ms:
            cache[-1] = bar
            return
        cache.append(bar)

    def _buffer_depth_event(self, symbol: str, state: LocalOrderBookState, event: dict[str, Any]) -> None:
        if state.sync_state == DEPTH_SYNC_COLD:
            state.sync_state = DEPTH_SYNC_BUFFERING
        counters = self._depth_counters(symbol)
        if len(state.buffered_events) == state.buffered_events.maxlen:
            counters.dropped_buffered_event_count += 1
        state.buffered_events.append(event)
        counters.buffer_high_watermark = max(counters.buffer_high_watermark, len(state.buffered_events))

    def _apply_depth_event(self, symbol: str, event: dict[str, Any]) -> None:
        state = self._order_book(symbol)
        if state.last_update_id is None:
            raise ValueError(f"depth snapshot missing for {symbol}")
        if int(event["u"]) < state.last_update_id:
            self._depth_counters(symbol).dropped_buffered_event_count += 1
            return
        first_event_after_snapshot = state.last_event_u == state.last_update_id
        if first_event_after_snapshot and not self._depth_event_aligns_snapshot(event, state.last_update_id):
            self._depth_counters(symbol).alignment_mismatch_count += 1
            raise DepthAlignmentMismatchError(f"depth snapshot alignment mismatch for {symbol}")
        if state.last_event_u is not None and not first_event_after_snapshot:
            expected_previous = state.last_event_u
            if int(event["pu"]) not in {0, expected_previous}:
                raise DepthGapError(f"depth stream gap for {symbol}: expected pu={expected_previous}, got {event['pu']}")
        self._apply_depth_side(state.bids, event.get("b", []))
        self._apply_depth_side(state.asks, event.get("a", []))
        self._raise_if_order_book_invalid(symbol, state, event_time_ms=int(event["time_ms"]))
        state.last_update_id = int(event["u"])
        state.last_event_u = int(event["u"])
        state.synced = True
        state.sync_state = DEPTH_SYNC_SYNCED
        state.last_bootstrap_error = None
        state.last_good_depth_time_ms = int(event["time_ms"])
        self._record_depth_history(state, event_time_ms=int(event["time_ms"]))

    def _depth_event_aligns_snapshot(self, event: dict[str, Any], snapshot_update_id: int) -> bool:
        if int(event["U"]) <= snapshot_update_id <= int(event["u"]):
            return True
        return int(event.get("pu") or 0) == snapshot_update_id

    def _apply_depth_side(self, side: dict[Decimal, Decimal], updates: list[list[Any]]) -> None:
        for price_raw, qty_raw in updates:
            price = Decimal(str(price_raw))
            qty = Decimal(str(qty_raw))
            if qty == Decimal("0"):
                side.pop(price, None)
            else:
                side[price] = qty

    def _record_depth_history(self, state: LocalOrderBookState, *, event_time_ms: int) -> None:
        if not state.bids or not state.asks:
            return
        bid_levels = sorted(state.bids.items(), key=lambda item: item[0], reverse=True)
        ask_levels = sorted(state.asks.items(), key=lambda item: item[0])
        history_entry = {
            "time_ms": event_time_ms,
            "bid_depth_l5": sum((qty for _, qty in bid_levels[:5]), start=Decimal("0")),
            "ask_depth_l5": sum((qty for _, qty in ask_levels[:5]), start=Decimal("0")),
            "bid_depth_l10": sum((qty for _, qty in bid_levels[:10]), start=Decimal("0")),
            "ask_depth_l10": sum((qty for _, qty in ask_levels[:10]), start=Decimal("0")),
        }
        if state.depth_history and state.depth_history[-1]["time_ms"] == event_time_ms:
            state.depth_history[-1] = history_entry
        else:
            state.depth_history.append(history_entry)
        cutoff_ms = event_time_ms - DEPTH_HISTORY_WINDOW_MS
        while state.depth_history and state.depth_history[0]["time_ms"] < cutoff_ms:
            state.depth_history.popleft()

    def _handle_depth_disconnect(self, symbol: str, detail: str, *, planned: bool = False) -> None:
        state = self._order_book(symbol)
        now_ms = int(time.time() * 1000)
        state.last_reconnect_time_ms = now_ms
        counters = self._depth_counters(symbol)
        if planned:
            state.last_planned_reconnect_time_ms = now_ms
            state.next_planned_reconnect_time_ms = None
            counters.planned_reconnect_count += 1
        else:
            counters.error_reconnect_count += 1
        if state.last_update_id is None and not state.buffered_events:
            return
        state.synced = False
        state.last_bootstrap_error = None if planned else detail
        state.sync_state = DEPTH_SYNC_RESYNC_PENDING
        counters.reconnect_resync_count += 1
        self._schedule_depth_resync_with_reason(symbol, reason="planned_reconnect" if planned else "ws_reconnect")

    def _schedule_depth_resync(self, symbol: str) -> None:
        self._schedule_depth_resync_with_reason(symbol, reason="manual")

    def _schedule_depth_resync_with_reason(self, symbol: str, *, reason: str, immediate: bool = False) -> None:
        state = self._order_book(symbol)
        now_ms = int(time.time() * 1000)
        state.last_resync_request_ms = now_ms
        state.last_resync_reason = reason
        counters = self._depth_counters(symbol)
        if reason == "gap":
            counters.gap_resync_count += 1
        state.sync_state = DEPTH_SYNC_BACKOFF if state.next_bootstrap_after_ms > now_ms else DEPTH_SYNC_RESYNC_PENDING
        jitter_ms = 0 if immediate else random.randint(0, min(500, max(self.depth_resync_min_interval_ms // 4, 1)))
        min_ready_ms = now_ms if immediate else now_ms + self.depth_resync_min_interval_ms + jitter_ms
        if state.next_bootstrap_after_ms < min_ready_ms:
            state.next_bootstrap_after_ms = min_ready_ms
        task = self._depth_bootstrap_tasks.get(symbol)
        if task is not None and not task.done():
            return
        self._depth_bootstrap_tasks[symbol] = asyncio.create_task(self._run_depth_resync(symbol))

    async def _run_depth_resync(self, symbol: str) -> None:
        state = self._order_book(symbol)
        state.repair_in_flight = True
        try:
            while True:
                delay_ms = max(state.next_bootstrap_after_ms - int(time.time() * 1000), 0)
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)
                try:
                    await self._bootstrap_order_book(symbol)
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._last_stream_error_by_stream[f"{symbol}:depth"] = str(exc)
                    state = self._order_book(symbol)
                    if state.next_bootstrap_after_ms > int(time.time() * 1000):
                        continue
                    return
        except asyncio.CancelledError:
            raise
        finally:
            self._order_book(symbol).repair_in_flight = False

    def _order_book_validity_issue(self, symbol: str, state: LocalOrderBookState) -> str | None:
        if not state.bids or not state.asks:
            return f"invalid local order book for {symbol}: empty side"
        bid_levels = sorted(state.bids.items(), key=lambda item: item[0], reverse=True)
        ask_levels = sorted(state.asks.items(), key=lambda item: item[0])
        if bid_levels[0][0] >= ask_levels[0][0]:
            return f"invalid local order book for {symbol}: crossed best bid/ask"
        if len(bid_levels) < self.depth_required_levels or len(ask_levels) < self.depth_required_levels:
            return (
                f"invalid local order book for {symbol}: insufficient levels "
                f"bids={len(bid_levels)} asks={len(ask_levels)} required={self.depth_required_levels}"
            )
        return None

    def _raise_if_order_book_invalid(self, symbol: str, state: LocalOrderBookState, *, event_time_ms: int) -> None:
        issue = self._order_book_validity_issue(symbol, state)
        if issue is None:
            return
        self._mark_order_book_invalid(symbol, state, issue=issue, event_time_ms=event_time_ms)
        raise DepthBookInvalidError(issue)

    def _mark_order_book_invalid(
        self,
        symbol: str,
        state: LocalOrderBookState,
        *,
        issue: str,
        event_time_ms: int,
    ) -> None:
        state.synced = False
        state.sync_state = DEPTH_SYNC_RESYNC_PENDING
        state.last_invalid_book_time_ms = event_time_ms
        state.last_bootstrap_error = issue
        self._last_stream_error_by_stream[f"{symbol}:depth"] = issue
        self._depth_counters(symbol).invalid_book_count += 1
        self._schedule_depth_resync_with_reason(symbol, reason="invalid_book")

    def _local_book_snapshot(self, symbol: str) -> dict[str, Any] | None:
        state = self._order_book(symbol)
        if not state.synced or self._order_book_validity_issue(symbol, state) is not None:
            return None
        bid_levels = sorted(state.bids.items(), key=lambda item: item[0], reverse=True)
        ask_levels = sorted(state.asks.items(), key=lambda item: item[0])
        best_bid_price, best_bid_qty = bid_levels[0]
        best_ask_price, best_ask_qty = ask_levels[0]
        local_mid = (best_bid_price + best_ask_price) / Decimal("2")

        def queue_imbalance(level_count: int) -> Decimal:
            bid_sum = sum((qty for _, qty in bid_levels[:level_count]), start=Decimal("0"))
            ask_sum = sum((qty for _, qty in ask_levels[:level_count]), start=Decimal("0"))
            denominator = bid_sum + ask_sum
            return (bid_sum - ask_sum) / denominator if denominator > 0 else Decimal("0")

        bid_depth_l5 = sum((qty for _, qty in bid_levels[:5]), start=Decimal("0"))
        ask_depth_l5 = sum((qty for _, qty in ask_levels[:5]), start=Decimal("0"))
        bid_depth_l10 = sum((qty for _, qty in bid_levels[:10]), start=Decimal("0"))
        ask_depth_l10 = sum((qty for _, qty in ask_levels[:10]), start=Decimal("0"))
        recent_history = list(state.depth_history)
        max_bid_depth_l5 = max((entry["bid_depth_l5"] for entry in recent_history), default=bid_depth_l5)
        max_ask_depth_l5 = max((entry["ask_depth_l5"] for entry in recent_history), default=ask_depth_l5)
        max_bid_depth_l10 = max((entry["bid_depth_l10"] for entry in recent_history), default=bid_depth_l10)
        max_ask_depth_l10 = max((entry["ask_depth_l10"] for entry in recent_history), default=ask_depth_l10)

        def depletion(current: Decimal, recent_max: Decimal) -> Decimal:
            if recent_max <= Decimal("0"):
                return Decimal("1")
            return current / recent_max

        return {
            "best_bid_price": str(best_bid_price),
            "best_bid_qty": str(best_bid_qty),
            "best_ask_price": str(best_ask_price),
            "best_ask_qty": str(best_ask_qty),
            "mid_price": str(local_mid),
            "last_update_id": state.last_update_id,
            "snapshot_time_ms": state.snapshot_time_ms,
            "bid_depth_l5": str(bid_depth_l5),
            "ask_depth_l5": str(ask_depth_l5),
            "bid_depth_l10": str(bid_depth_l10),
            "ask_depth_l10": str(ask_depth_l10),
            "queue_imbalance_l1": str(queue_imbalance(1)),
            "queue_imbalance_l5": str(queue_imbalance(5)),
            "queue_imbalance_l10": str(queue_imbalance(10)),
            "bid_depth_l5_depletion": str(depletion(bid_depth_l5, max_bid_depth_l5)),
            "ask_depth_l5_depletion": str(depletion(ask_depth_l5, max_ask_depth_l5)),
            "bid_depth_l10_depletion": str(depletion(bid_depth_l10, max_bid_depth_l10)),
            "ask_depth_l10_depletion": str(depletion(ask_depth_l10, max_ask_depth_l10)),
        }

    def _depth_sync_state(self, symbol: str, now_ms: int) -> str:
        state = self._order_book(symbol)
        if state.sync_state == DEPTH_SYNC_BOOTSTRAPPING:
            return DEPTH_SYNC_BOOTSTRAPPING
        if state.next_bootstrap_after_ms > now_ms:
            return DEPTH_SYNC_BACKOFF
        if state.sync_state in {DEPTH_SYNC_COLD, DEPTH_SYNC_BUFFERING, DEPTH_SYNC_RESYNC_PENDING}:
            return state.sync_state
        if not state.synced:
            return DEPTH_SYNC_RESYNC_PENDING if state.last_update_id is not None else DEPTH_SYNC_BUFFERING
        last_depth_ms = self._last_depth_ws_message_ms_by_symbol.get(symbol)
        if last_depth_ms is None or now_ms - last_depth_ms > self.ws_stale_after_ms:
            return DEPTH_SYNC_STALE
        return DEPTH_SYNC_SYNCED

    def _order_book_health_state(self, symbol: str, now_ms: int) -> str:
        state = self._order_book(symbol)
        depth_sync_state = self._depth_sync_state(symbol, now_ms)
        if depth_sync_state == DEPTH_SYNC_BACKOFF:
            return "backoff"
        if depth_sync_state == DEPTH_SYNC_COLD:
            return "cold"
        if depth_sync_state == DEPTH_SYNC_BUFFERING:
            return "buffering"
        if depth_sync_state == DEPTH_SYNC_BOOTSTRAPPING:
            return "bootstrapping"
        if depth_sync_state == DEPTH_SYNC_RESYNC_PENDING:
            return "resync_pending"
        if depth_sync_state == DEPTH_SYNC_STALE:
            return "stale"
        validity_issue = self._order_book_validity_issue(symbol, state)
        if validity_issue is not None:
            return "invalid"
        return "healthy"
