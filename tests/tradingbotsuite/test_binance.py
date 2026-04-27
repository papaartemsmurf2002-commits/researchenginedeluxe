from __future__ import annotations

import asyncio
from decimal import Decimal

import httpx
import pytest

from tradingbotsuite.adapters.binance import BinanceCandleClient, DEPTH_SYNC_SYNCED


def _kline_row(bar, *, close_override: str | None = None) -> list[str | int]:
    return [
        bar.time_ms,
        str(bar.open),
        str(bar.high),
        str(bar.low),
        close_override or str(bar.close),
        str(bar.volume),
        bar.time_ms + 899_999,
        "0",
        0,
        "0",
        "0",
        "0",
    ]


@pytest.mark.asyncio
async def test_binance_client_bootstraps_rest_cache_without_stream_task(sample_bars) -> None:
    rows = [
        _kline_row(sample_bars[-3]),
        _kline_row(sample_bars[-2]),
        _kline_row(sample_bars[-1], close_override="70123.4"),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/fapi/v1/klines")
        return httpx.Response(200, json=rows)

    class RestOnlyBinanceClient(BinanceCandleClient):
        async def _ensure_stream(self, symbol: str) -> None:
            await self._bootstrap_recent_bars(symbol, 2)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = RestOnlyBinanceClient(
            "https://example.invalid",
            client=http_client,
            ws_base_url="wss://example.invalid",
        )
        closed = await client.fetch_recent_closed_bars("BTCUSDT", 1)
        latest = await client.fetch_latest_bar("BTCUSDT", include_incomplete=True)

    assert closed[-1].time_ms == sample_bars[-2].time_ms
    assert latest.close == Decimal("70123.4")


@pytest.mark.asyncio
async def test_binance_client_applies_live_and_closed_kline_updates(sample_bars) -> None:
    client = BinanceCandleClient("https://example.invalid", ws_base_url="wss://example.invalid")
    client._replace_closed_bars("BTCUSDT", [sample_bars[-2]])

    open_payload = {
        "e": "kline",
        "E": sample_bars[-1].time_ms + 1000,
        "s": "BTCUSDT",
        "k": {
            "t": sample_bars[-1].time_ms,
            "T": sample_bars[-1].time_ms + 899_999,
            "s": "BTCUSDT",
            "i": "15m",
            "o": str(sample_bars[-1].open),
            "c": "70200.0",
            "h": str(sample_bars[-1].high),
            "l": str(sample_bars[-1].low),
            "v": str(sample_bars[-1].volume),
            "x": False,
        },
    }
    closed_payload = {
        "e": "kline",
        "E": sample_bars[-1].time_ms + 2000,
        "s": "BTCUSDT",
        "k": {
            **open_payload["k"],
            "c": "70210.0",
            "x": True,
        },
    }

    client._handle_kline_message(open_payload)
    client._handle_kline_message(closed_payload)

    assert client._latest_bar_by_symbol["BTCUSDT"].close == Decimal("70210.0")
    assert list(client._closed_bars("BTCUSDT"))[-1].close == Decimal("70210.0")
    assert client.get_stream_status()["symbol_status"]["BTCUSDT"]["last_ws_message_ms"] == sample_bars[-1].time_ms + 2000
    await client.close()


def test_binance_stream_urls_follow_public_market_split() -> None:
    client = BinanceCandleClient("https://example.invalid", ws_base_url="wss://fstream.binance.com")

    assert client._stream_url("kline", "btcusdt@kline_15m") == "wss://fstream.binance.com/market/ws/btcusdt@kline_15m"
    assert client._stream_url("aggTrade", "btcusdt@aggTrade") == "wss://fstream.binance.com/market/ws/btcusdt@aggTrade"
    assert client._stream_url("bookTicker", "btcusdt@bookTicker") == "wss://fstream.binance.com/public/ws/btcusdt@bookTicker"
    assert client._stream_url("depth", "btcusdt@depth") == "wss://fstream.binance.com/public/ws/btcusdt@depth"
    assert client._stream_bundle_url("market", ["btcusdt@kline_15m", "btcusdt@aggTrade"]) == (
        "wss://fstream.binance.com/market/stream?streams=btcusdt@kline_15m/btcusdt@aggTrade"
    )
    assert client._stream_bundle_url("public", ["btcusdt@bookTicker", "btcusdt@depth"]) == (
        "wss://fstream.binance.com/public/stream?streams=btcusdt@bookTicker/btcusdt@depth"
    )


def test_binance_stream_urls_normalize_legacy_or_routed_ws_base() -> None:
    client = BinanceCandleClient("https://example.invalid", ws_base_url="wss://fstream.binance.com/ws")
    assert client._stream_url("depth", "btcusdt@depth") == "wss://fstream.binance.com/public/ws/btcusdt@depth"

    routed_client = BinanceCandleClient("https://example.invalid", ws_base_url="wss://fstream.binance.com/market")
    assert routed_client._stream_url("bookTicker", "btcusdt@bookTicker") == "wss://fstream.binance.com/public/ws/btcusdt@bookTicker"


@pytest.mark.asyncio
async def test_binance_microstructure_snapshot_computes_signed_imbalance_and_book_imbalance() -> None:
    class StreamReadyBinanceClient(BinanceCandleClient):
        async def _ensure_stream(self, symbol: str) -> None:
            return None

    client = StreamReadyBinanceClient(
        "https://example.invalid",
        ws_base_url="wss://example.invalid",
        ws_stale_after_ms=60_000,
        depth_required_levels=1,
    )
    client._stream_started_ms_by_symbol["BTCUSDT"] = 1000
    order_book = client._order_book("BTCUSDT")
    order_book.synced = True
    order_book.sync_state = DEPTH_SYNC_SYNCED
    order_book.last_update_id = 200
    order_book.last_event_u = 200
    order_book.snapshot_time_ms = 9_000
    order_book.bids = {Decimal("70000"): Decimal("4.0"), Decimal("69999"): Decimal("2.0")}
    order_book.asks = {Decimal("70002"): Decimal("1.0"), Decimal("70003"): Decimal("2.0")}
    client._handle_agg_trade_message(
        {"e": "aggTrade", "E": 10_000, "T": 10_000, "s": "BTCUSDT", "p": "70000", "q": "0.5", "m": False}
    )
    client._handle_agg_trade_message(
        {"e": "aggTrade", "E": 12_000, "T": 12_000, "s": "BTCUSDT", "p": "70010", "q": "0.2", "m": True}
    )
    client._handle_book_ticker_message(
        {"e": "bookTicker", "E": 12_500, "s": "BTCUSDT", "b": "70000", "B": "4.0", "a": "70002", "A": "1.0"}
    )
    client._last_depth_ws_message_ms_by_symbol["BTCUSDT"] = 12_400

    snapshot = await client.get_microstructure_snapshot("BTCUSDT", windows_seconds=(10, 20), now_ms=15_000)

    assert snapshot["healthy"] is True
    assert snapshot["windows"]["10"]["signed_qty"] == "0.3"
    assert snapshot["windows"]["10"]["signed_ratio"] == str(Decimal("0.3") / Decimal("0.7"))
    buy_sqrt = Decimal("35000").sqrt()
    sell_sqrt = Decimal("14002").sqrt()
    assert Decimal(snapshot["windows"]["10"]["sqrt_signed_ratio"]) == (buy_sqrt - sell_sqrt) / (buy_sqrt + sell_sqrt)
    assert snapshot["windows"]["10"]["trade_sign_acf_lag1"] is None
    assert Decimal(snapshot["windows"]["10"]["flow_price_alignment_bps"]) == (Decimal("10") / Decimal("70000")) * Decimal("10000")
    assert snapshot["windows"]["10"]["impact_transform"] == "sqrt_notional"
    assert snapshot["top_of_book_imbalance"] == str(Decimal("0.6"))
    assert snapshot["mid_price"] == "70001"
    assert snapshot["queue_imbalance_l1"] == str(Decimal("0.6"))
    assert snapshot["local_order_book"]["queue_imbalance_l5"] == str(Decimal("3") / Decimal("9"))
    assert snapshot["depth_update_speed_ms"] == 250
    assert snapshot["depth_snapshot_limit"] == 1000
    await client.close()


@pytest.mark.asyncio
async def test_binance_agg_trade_prefers_normal_qty_when_available() -> None:
    class StreamReadyBinanceClient(BinanceCandleClient):
        async def _ensure_stream(self, symbol: str) -> None:
            return None

    client = StreamReadyBinanceClient(
        "https://example.invalid",
        ws_base_url="wss://example.invalid",
        ws_stale_after_ms=60_000,
        depth_required_levels=1,
    )
    client._stream_started_ms_by_symbol["BTCUSDT"] = 1000
    order_book = client._order_book("BTCUSDT")
    order_book.synced = True
    order_book.sync_state = DEPTH_SYNC_SYNCED
    order_book.last_update_id = 200
    order_book.last_event_u = 200
    order_book.snapshot_time_ms = 9_000
    order_book.bids = {Decimal("70000"): Decimal("4.0")}
    order_book.asks = {Decimal("70002"): Decimal("1.0")}
    client._handle_agg_trade_message(
        {"e": "aggTrade", "E": 10_000, "T": 10_000, "s": "BTCUSDT", "p": "70000", "q": "0.8", "nq": "0.5", "m": False}
    )
    client._handle_book_ticker_message(
        {"e": "bookTicker", "E": 12_500, "s": "BTCUSDT", "b": "70000", "B": "4.0", "a": "70002", "A": "1.0"}
    )
    client._last_depth_ws_message_ms_by_symbol["BTCUSDT"] = 12_400

    snapshot = await client.get_microstructure_snapshot("BTCUSDT", windows_seconds=(10,), now_ms=15_000)

    assert snapshot["windows"]["10"]["signed_qty"] == "0.5"
    assert snapshot["windows"]["10"]["buy_qty"] == "0.5"
    assert snapshot["windows"]["10"]["raw_buy_qty"] == "0.8"
    assert snapshot["windows"]["10"]["sqrt_signed_ratio"] == "1"
    assert snapshot["windows"]["10"]["rpi_adjusted_trade_count"] == 1
    await client.close()


@pytest.mark.asyncio
async def test_binance_microstructure_snapshot_stays_entry_ready_when_only_depth_is_unsynced() -> None:
    class StreamReadyBinanceClient(BinanceCandleClient):
        async def _ensure_stream(self, symbol: str) -> None:
            return None

    client = StreamReadyBinanceClient("https://example.invalid", ws_base_url="wss://example.invalid", ws_stale_after_ms=60_000)
    client._stream_started_ms_by_symbol["BTCUSDT"] = 1000
    client._handle_agg_trade_message(
        {"e": "aggTrade", "E": 10_000, "T": 10_000, "s": "BTCUSDT", "p": "70000", "q": "0.5", "m": False}
    )
    client._handle_book_ticker_message(
        {"e": "bookTicker", "E": 12_500, "s": "BTCUSDT", "b": "70000", "B": "4.0", "a": "70002", "A": "1.0"}
    )
    state = client._order_book("BTCUSDT")
    state.synced = False
    state.last_bootstrap_error = "depth gap"
    state.next_bootstrap_after_ms = 20_000
    client._last_depth_ws_message_ms_by_symbol["BTCUSDT"] = 12_400

    snapshot = await client.get_microstructure_snapshot("BTCUSDT", windows_seconds=(20,), now_ms=15_000)

    assert snapshot["healthy"] is True
    assert snapshot["entry_ready"] is True
    assert snapshot["degraded"] is True
    assert snapshot["depth_healthy"] is False
    assert "order_book_unsynced" in snapshot["warnings"]
    assert snapshot["queue_imbalance_l1"] is None


@pytest.mark.asyncio
async def test_binance_ensure_stream_bootstraps_once_when_cache_is_warm(sample_bars) -> None:
    class CountingBinanceClient(BinanceCandleClient):
        def __init__(self) -> None:
            super().__init__("https://example.invalid", ws_base_url="wss://example.invalid", depth_required_levels=1)
            self.bootstrap_calls = 0

        async def _bootstrap_recent_bars(self, symbol: str, limit: int):
            self.bootstrap_calls += 1
            bars = sample_bars[-limit:]
            self._replace_closed_bars(symbol, bars)
            self._latest_bar_by_symbol[symbol] = sample_bars[-1]
            return bars

        def _ensure_stream_bundle_task(self, symbol: str, bundle_key: str, route: str, stream_specs: list[tuple[str, str]]) -> None:
            self._stream_tasks[f"{symbol}:{bundle_key}"] = asyncio.create_task(asyncio.sleep(3600))

        async def _bootstrap_order_book(self, symbol: str) -> None:
            state = self._order_book(symbol)
            state.synced = True
            state.sync_state = DEPTH_SYNC_SYNCED
            state.last_update_id = 1
            state.last_event_u = 1
            state.snapshot_time_ms = sample_bars[-1].time_ms
            state.bids = {Decimal("70000"): Decimal("1.0")}
            state.asks = {Decimal("70001"): Decimal("1.0")}
            self._last_depth_ws_message_ms_by_symbol[symbol] = sample_bars[-1].time_ms

    client = CountingBinanceClient()
    try:
        await client.fetch_latest_bar("BTCUSDT")
        await client.fetch_recent_closed_bars("BTCUSDT", 1)
        await client.get_microstructure_snapshot("BTCUSDT", now_ms=sample_bars[-1].time_ms + 1_000)
    finally:
        await client.close()

    assert client.bootstrap_calls == 1


@pytest.mark.asyncio
async def test_binance_depth_bootstrap_replays_buffered_events() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/fapi/v1/depth"):
            return httpx.Response(
                200,
                json={
                    "lastUpdateId": 100,
                    "bids": [["70000", "2.0"], ["69999", "1.0"]],
                    "asks": [["70002", "3.0"], ["70003", "1.0"]],
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient(
            "https://example.invalid",
            client=http_client,
            ws_base_url="wss://example.invalid",
            depth_required_levels=1,
        )
        state = client._order_book("BTCUSDT")
        state.buffered_events.append(
            {
                "symbol": "BTCUSDT",
                "U": 100,
                "u": 101,
                "pu": 0,
                "b": [["70000", "2.5"]],
                "a": [["70002", "0"]],
                "time_ms": 10_000,
            }
        )
        await client._bootstrap_order_book("BTCUSDT")
        snapshot = client._local_book_snapshot("BTCUSDT")

    assert state.synced is True
    assert state.last_update_id == 101
    assert snapshot is not None
    assert snapshot["best_bid_qty"] == "2.5"
    assert snapshot["best_ask_price"] == "70003"


@pytest.mark.asyncio
async def test_binance_depth_bootstrap_accepts_first_replayed_event_without_matching_pu() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/fapi/v1/depth"):
            return httpx.Response(
                200,
                json={
                    "lastUpdateId": 100,
                    "bids": [["70000", "2.0"], ["69999", "1.0"]],
                    "asks": [["70002", "3.0"], ["70003", "1.0"]],
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient(
            "https://example.invalid",
            client=http_client,
            ws_base_url="wss://example.invalid",
            depth_required_levels=1,
        )
        state = client._order_book("BTCUSDT")
        state.buffered_events.append(
            {
                "symbol": "BTCUSDT",
                "U": 95,
                "u": 101,
                "pu": 94,
                "b": [["70000", "2.5"]],
                "a": [["70002", "0"]],
                "time_ms": 10_000,
            }
        )
        await client._bootstrap_order_book("BTCUSDT")
        snapshot = client._local_book_snapshot("BTCUSDT")

    assert state.synced is True
    assert state.last_update_id == 101
    assert snapshot is not None
    assert snapshot["best_bid_qty"] == "2.5"
    assert snapshot["best_ask_price"] == "70003"


@pytest.mark.asyncio
async def test_binance_depth_bootstrap_accepts_pu_chained_event_after_snapshot() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/fapi/v1/depth"):
            return httpx.Response(
                200,
                json={
                    "lastUpdateId": 100,
                    "bids": [["70000", "2.0"], ["69999", "1.0"]],
                    "asks": [["70002", "3.0"], ["70003", "1.0"]],
                },
            )
        raise AssertionError(f"unexpected path {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient(
            "https://example.invalid",
            client=http_client,
            ws_base_url="wss://example.invalid",
            depth_required_levels=1,
        )
        state = client._order_book("BTCUSDT")
        state.buffered_events.append(
            {
                "symbol": "BTCUSDT",
                "U": 101,
                "u": 102,
                "pu": 100,
                "b": [["70000", "2.5"]],
                "a": [["70002", "0"]],
                "time_ms": 10_000,
            }
        )
        await client._bootstrap_order_book("BTCUSDT")
        snapshot = client._local_book_snapshot("BTCUSDT")

    assert state.synced is True
    assert state.last_update_id == 102
    assert snapshot is not None
    assert snapshot["best_bid_qty"] == "2.5"
    assert snapshot["best_ask_price"] == "70003"


@pytest.mark.asyncio
async def test_binance_depth_live_first_event_after_snapshot_accepts_pu_chain() -> None:
    client = BinanceCandleClient("https://example.invalid", ws_base_url="wss://example.invalid", depth_required_levels=1)
    state = client._order_book("BTCUSDT")
    state.synced = True
    state.sync_state = DEPTH_SYNC_SYNCED
    state.last_update_id = 100
    state.last_event_u = 100
    state.snapshot_time_ms = 9_000
    state.bids = {Decimal("70000"): Decimal("2.0"), Decimal("69999"): Decimal("1.0")}
    state.asks = {Decimal("70002"): Decimal("3.0"), Decimal("70003"): Decimal("1.0")}

    client._handle_depth_message(
        {
            "e": "depthUpdate",
            "E": 10_000,
            "s": "BTCUSDT",
            "U": 101,
            "u": 102,
            "pu": 100,
            "b": [["70000", "2.5"]],
            "a": [["70002", "0"]],
        }
    )
    snapshot = client._local_book_snapshot("BTCUSDT")
    await client.close()

    assert state.synced is True
    assert state.last_update_id == 102
    assert snapshot is not None
    assert snapshot["best_bid_qty"] == "2.5"
    assert snapshot["best_ask_price"] == "70003"


@pytest.mark.asyncio
async def test_binance_depth_bootstrap_retains_buffer_after_alignment_mismatch_and_recovers() -> None:
    snapshot_payloads = [
        {
            "lastUpdateId": 100,
            "bids": [["70000", "2.0"], ["69999", "1.0"]],
            "asks": [["70002", "3.0"], ["70003", "1.0"]],
        },
        {
            "lastUpdateId": 105,
            "bids": [["70000", "2.0"], ["69999", "1.0"]],
            "asks": [["70002", "3.0"], ["70003", "1.0"]],
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/fapi/v1/depth"):
            return httpx.Response(200, json=snapshot_payloads.pop(0))
        raise AssertionError(f"unexpected path {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient(
            "https://example.invalid",
            client=http_client,
            ws_base_url="wss://example.invalid",
            depth_required_levels=1,
        )
        state = client._order_book("BTCUSDT")
        buffered_event = {
            "symbol": "BTCUSDT",
            "U": 105,
            "u": 106,
            "pu": 104,
            "b": [["70000", "2.5"]],
            "a": [["70002", "0"]],
            "time_ms": 10_000,
        }
        state.buffered_events.append(buffered_event)
        with pytest.raises(ValueError, match="unable to align Binance depth snapshot"):
            await client._bootstrap_order_book("BTCUSDT")

        assert list(state.buffered_events) == [buffered_event]

        await client._bootstrap_order_book("BTCUSDT")
        snapshot = client._local_book_snapshot("BTCUSDT")

    assert state.synced is True
    assert state.last_update_id == 106
    assert snapshot is not None
    assert snapshot["best_bid_qty"] == "2.5"
    assert snapshot["best_ask_price"] == "70003"


@pytest.mark.asyncio
async def test_binance_depth_gap_marks_book_unsynced_and_requests_resync() -> None:
    class GapAwareBinanceClient(BinanceCandleClient):
        def __init__(self) -> None:
            super().__init__("https://example.invalid", ws_base_url="wss://example.invalid", depth_required_levels=1)
            self.resync_requests: list[str] = []

        def _schedule_depth_resync_with_reason(self, symbol: str, *, reason: str, immediate: bool = False) -> None:
            super()._schedule_depth_resync_with_reason(symbol, reason=reason, immediate=immediate)
            self.resync_requests.append(symbol)

    client = GapAwareBinanceClient()
    state = client._order_book("BTCUSDT")
    state.synced = True
    state.last_update_id = 101
    state.last_event_u = 101
    state.bids = {Decimal("70000"): Decimal("1.0")}
    state.asks = {Decimal("70001"): Decimal("1.0")}

    client._handle_depth_message(
        {
            "e": "depthUpdate",
            "E": 20_000,
            "s": "BTCUSDT",
            "U": 105,
            "u": 106,
            "pu": 103,
            "b": [["70000", "1.1"]],
            "a": [],
        }
    )

    assert state.synced is False
    assert client.resync_requests == ["BTCUSDT"]
    assert client._depth_counters("BTCUSDT").gap_count == 1
    assert state.next_bootstrap_after_ms > 0


@pytest.mark.asyncio
async def test_binance_microstructure_snapshot_degrades_on_depth_rate_limit(sample_bars) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/fapi/v1/klines"):
            rows = [_kline_row(sample_bars[-3]), _kline_row(sample_bars[-2]), _kline_row(sample_bars[-1])]
            return httpx.Response(200, json=rows)
        if request.url.path.endswith("/fapi/v1/depth"):
            return httpx.Response(429, json={"code": -1003, "msg": "Too many requests"}, headers={"Retry-After": "1"})
        raise AssertionError(f"unexpected path {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient("https://example.invalid", client=http_client, ws_base_url="wss://example.invalid")
        with pytest.raises(httpx.HTTPStatusError):
            await client._bootstrap_order_book("BTCUSDT")
        snapshot = await client.get_microstructure_snapshot("BTCUSDT", now_ms=20_000)

    assert snapshot["healthy"] is False
    assert "bootstrap_error" in snapshot["warnings"]
    assert snapshot["bootstrap_error"] is not None
    assert snapshot["depth_bootstrap_retry_after_ms"] is not None
    assert snapshot["depth_rate_limit_count"] == 1


@pytest.mark.asyncio
async def test_binance_microstructure_snapshot_is_passive_and_does_not_bootstrap_depth(sample_bars) -> None:
    request_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_paths.append(request.url.path)
        if request.url.path.endswith("/fapi/v1/klines"):
            rows = [_kline_row(sample_bars[-3]), _kline_row(sample_bars[-2]), _kline_row(sample_bars[-1])]
            return httpx.Response(200, json=rows)
        if request.url.path.endswith("/fapi/v1/depth"):
            raise AssertionError("passive microstructure snapshot must not fetch depth")
        raise AssertionError(f"unexpected path {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient("https://example.invalid", client=http_client, ws_base_url="wss://example.invalid")
        snapshot = await client.get_microstructure_snapshot("BTCUSDT", now_ms=20_000)

    assert snapshot["healthy"] is False
    assert snapshot["queue_imbalance_available"] is False
    assert all(not path.endswith("/fapi/v1/depth") for path in request_paths)


@pytest.mark.asyncio
async def test_binance_recent_closed_bars_uses_cache_before_kline_backoff(sample_bars) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(418))) as http_client:
        client = BinanceCandleClient("https://example.invalid", client=http_client, ws_base_url="wss://example.invalid")
        client._replace_closed_bars("BTCUSDT", sample_bars[-3:])
        bars = await client.fetch_recent_closed_bars("BTCUSDT", 1)
    assert bars[-1].time_ms == sample_bars[-1].time_ms


@pytest.mark.asyncio
async def test_binance_recent_closed_bars_sets_backoff_on_kline_ban() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(418, json={"code": -1003, "msg": "IP banned"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient("https://example.invalid", client=http_client, ws_base_url="wss://example.invalid")
        with pytest.raises(RuntimeError, match="Binance kline bootstrap rate limited"):
            await client.fetch_recent_closed_bars("BTCUSDT", 1)

    assert client._next_bar_bootstrap_after_ms_by_symbol["BTCUSDT"] > 0


@pytest.mark.asyncio
async def test_binance_open_interest_context_skips_current_endpoint_for_historical_timestamp() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path.endswith("/futures/data/openInterestHist"):
            return httpx.Response(
                200,
                json=[
                    {"timestamp": 1712649000000, "sumOpenInterest": "1000", "sumOpenInterestValue": "70000000"},
                    {"timestamp": 1712649300000, "sumOpenInterest": "1025", "sumOpenInterestValue": "71750000"},
                ],
            )
        if request.url.path.endswith("/fapi/v1/openInterest"):
            return httpx.Response(429, json={"code": -1003, "msg": "too many requests"})
        raise AssertionError(f"unexpected path {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient("https://example.invalid", client=http_client, ws_base_url="wss://example.invalid")
        context = await client.fetch_open_interest_context("BTCUSDT", as_of_ms=1712649600000, period="5m", lookback_points=13)

    assert "/fapi/v1/openInterest" not in requested_paths
    assert context["open_interest"] == "1025"
    assert context["open_interest_change"] == "25"


@pytest.mark.asyncio
async def test_binance_premium_context_uses_historical_mark_and_index_klines_for_replay() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path.endswith("/fapi/v1/premiumIndexKlines"):
            return httpx.Response(200, json=[[0, "0", "0", "0", "0.0002"], [1, "0", "0", "0", "0.0003"]])
        if request.url.path.endswith("/fapi/v1/markPriceKlines"):
            return httpx.Response(200, json=[[0, "0", "0", "0", "70010"], [1, "0", "0", "0", "70025"]])
        if request.url.path.endswith("/fapi/v1/indexPriceKlines"):
            return httpx.Response(200, json=[[0, "0", "0", "0", "70000"], [1, "0", "0", "0", "70005"]])
        if request.url.path.endswith("/fapi/v1/premiumIndex"):
            return httpx.Response(429, json={"code": -1003, "msg": "too many requests"})
        raise AssertionError(f"unexpected path {request.url.path}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient("https://example.invalid", client=http_client, ws_base_url="wss://example.invalid")
        context = await client.fetch_premium_context("BTCUSDT", as_of_ms=1712649600000, interval="5m")

    assert "/fapi/v1/premiumIndex" not in requested_paths
    assert context["mark_price"] == "70025"
    assert context["index_price"] == "70005"
    assert context["basis"] == "20"


@pytest.mark.asyncio
async def test_binance_historical_closed_bar_range_retries_on_429(sample_bars) -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(429, json={"code": -1003, "msg": "too many requests"}, headers={"Retry-After": "0"})
        return httpx.Response(200, json=[_kline_row(sample_bars[0]), _kline_row(sample_bars[1]), _kline_row(sample_bars[2]), _kline_row(sample_bars[3])])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceCandleClient("https://example.invalid", client=http_client, ws_base_url="wss://example.invalid")
        bars = await client.fetch_historical_closed_bar_range(
            "BTCUSDT",
            start_time_ms=sample_bars[0].time_ms,
            end_time_ms=sample_bars[3].time_ms + 899_999,
        )

    assert request_count >= 2
    assert [bar.time_ms for bar in bars] == [sample_bars[0].time_ms, sample_bars[1].time_ms, sample_bars[2].time_ms, sample_bars[3].time_ms]


@pytest.mark.asyncio
async def test_binance_crossed_local_book_degrades_queue_without_poisoning_entry_streams() -> None:
    class NoopResyncBinanceClient(BinanceCandleClient):
        async def _run_depth_resync(self, symbol: str) -> None:
            await asyncio.sleep(3600)

    client = NoopResyncBinanceClient(
        "https://example.invalid",
        ws_base_url="wss://example.invalid",
        ws_stale_after_ms=60_000,
        depth_required_levels=1,
    )
    state = client._order_book("BTCUSDT")
    state.synced = True
    state.sync_state = DEPTH_SYNC_SYNCED
    state.last_update_id = 100
    state.last_event_u = 100
    state.bids = {Decimal("70000"): Decimal("1")}
    state.asks = {Decimal("70002"): Decimal("1")}
    state.snapshot_time_ms = 9_000
    client._last_depth_ws_message_ms_by_symbol["BTCUSDT"] = 10_000
    client._handle_agg_trade_message(
        {"e": "aggTrade", "E": 10_000, "T": 10_000, "s": "BTCUSDT", "p": "70000", "q": "0.5", "m": False}
    )
    client._handle_book_ticker_message(
        {"e": "bookTicker", "E": 10_000, "s": "BTCUSDT", "b": "70000", "B": "1", "a": "70002", "A": "1"}
    )

    client._handle_depth_message(
        {
            "e": "depthUpdate",
            "E": 11_000,
            "s": "BTCUSDT",
            "U": 101,
            "u": 102,
            "pu": 100,
            "b": [["70003", "2"]],
            "a": [],
        }
    )
    snapshot = await client.get_microstructure_snapshot("BTCUSDT", windows_seconds=(20,), now_ms=12_000)

    try:
        assert snapshot["healthy"] is True
        assert snapshot["entry_ready"] is True
        assert snapshot["depth_healthy"] is False
        assert snapshot["queue_imbalance_l1"] is None
        assert snapshot["book_validity_issue"] is not None
        assert snapshot["depth_invalid_book_count"] == 1
        assert "order_book_unsynced" in snapshot["warnings"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_binance_gap_storm_uses_one_depth_repair_task() -> None:
    class SlowRepairBinanceClient(BinanceCandleClient):
        async def _run_depth_resync(self, symbol: str) -> None:
            await asyncio.sleep(3600)

    client = SlowRepairBinanceClient("https://example.invalid", ws_base_url="wss://example.invalid")
    try:
        client._schedule_depth_resync_with_reason("BTCUSDT", reason="gap")
        first_task = client._depth_bootstrap_tasks["BTCUSDT"]
        client._schedule_depth_resync_with_reason("BTCUSDT", reason="gap")
        second_task = client._depth_bootstrap_tasks["BTCUSDT"]

        assert first_task is second_task
        assert len(client._depth_bootstrap_tasks) == 1
        assert client._depth_counters("BTCUSDT").gap_resync_count == 2
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_binance_planned_depth_reconnect_is_not_counted_as_error() -> None:
    class SlowRepairBinanceClient(BinanceCandleClient):
        async def _run_depth_resync(self, symbol: str) -> None:
            await asyncio.sleep(3600)

    client = SlowRepairBinanceClient("https://example.invalid", ws_base_url="wss://example.invalid")
    state = client._order_book("BTCUSDT")
    state.synced = True
    state.sync_state = DEPTH_SYNC_SYNCED
    state.last_update_id = 100
    state.last_event_u = 100
    state.bids = {Decimal("70000"): Decimal("1")}
    state.asks = {Decimal("70002"): Decimal("1")}

    try:
        client._handle_depth_disconnect("BTCUSDT", "planned_reconnect", planned=True)

        counters = client._depth_counters("BTCUSDT")
        assert counters.planned_reconnect_count == 1
        assert counters.error_reconnect_count == 0
        assert counters.reconnect_resync_count == 1
        assert state.last_bootstrap_error is None
        assert state.last_resync_reason == "planned_reconnect"
        assert state.last_planned_reconnect_time_ms is not None
    finally:
        await client.close()
