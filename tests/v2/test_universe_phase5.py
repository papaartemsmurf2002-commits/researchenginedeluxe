from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.universe.hyperliquid import (
    diff_snapshots,
    refresh_hyperliquid_universe,
    select_asof_universe,
)
from tradingbotsuite.v2.universe.models import UniverseMode
from tradingbotsuite.v2.venues.hyperliquid import HyperliquidInfoClient, HyperliquidWebSocketClient
from tradingbotsuite.v2.universe.rules import (
    CURRENT_UNIVERSE_SANDBOX_ONLY,
    MISSING_HIP3_METADATA,
    VOLUME_BELOW_THRESHOLD,
)


ROOT = Path(__file__).resolve().parents[2]


def test_hyperliquid_universe_includes_non_btc_eth_above_5m(tmp_path) -> None:
    result = refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(day_sol=12_000_000),
        asof_date=date(2026, 6, 1),
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
        eligible_only=True,
    )

    assert result.eligible_count >= 2
    assert "hyperliquid:perp:SOL" in {row.instrument_id for row in rows}


def test_hyperliquid_info_client_records_public_unsigned_provenance() -> None:
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        assert request.method == "POST"
        assert json.loads(request.content.decode("utf-8")) == {"type": "metaAndAssetCtxs"}
        return httpx.Response(
            200,
            json=_payload(day_sol=12_000_000),
            headers={"x-ratelimit-remaining": "42"},
        )

    client = HyperliquidInfoClient(
        base_url="https://example.test/info",
        timeout=3.0,
        transport=httpx.MockTransport(handler),
    )
    result = client.fetch_meta_and_asset_contexts()

    assert len(seen_requests) == 1
    assert result.capability.access_mode == "public_unsigned"
    assert result.capability.supports_universe_metadata is True
    assert result.capability.order_placement_allowed is False
    assert result.raw_request.source == "info/metaAndAssetCtxs"
    assert result.raw_request.params["type"] == "metaAndAssetCtxs"
    assert result.raw_response.evidence_scope == "public_unsigned_universe_metadata"
    assert result.raw_response.row_count == 3
    assert result.raw_response.rate_limit_metadata["x-ratelimit-remaining"] == "42"
    assert result.raw_response.order_placement_instruction is False


def test_hyperliquid_info_client_records_public_candle_snapshot_provenance() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 1, 0, 2, tzinfo=UTC)
    expected_body = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "1m",
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
        },
    }
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        assert request.method == "POST"
        assert json.loads(request.content.decode("utf-8")) == expected_body
        return httpx.Response(
            200,
            json=[
                {
                    "t": expected_body["req"]["startTime"],
                    "T": expected_body["req"]["startTime"] + 60_000,
                    "s": "BTC",
                    "i": "1m",
                    "o": "100",
                    "h": "101",
                    "l": "99",
                    "c": "100.5",
                    "v": "10",
                    "n": 3,
                },
                {
                    "t": expected_body["req"]["startTime"] + 60_000,
                    "T": expected_body["req"]["endTime"],
                    "s": "BTC",
                    "i": "1m",
                    "o": "100.5",
                    "h": "102",
                    "l": "100",
                    "c": "101",
                    "v": "12",
                    "n": 2,
                },
            ],
            headers={"x-ratelimit-remaining": "17"},
        )

    client = HyperliquidInfoClient(
        base_url="https://example.test/info",
        timeout=3.0,
        transport=httpx.MockTransport(handler),
    )
    result = client.fetch_candle_snapshot(
        coin="BTC",
        interval="1m",
        start_time=start,
        end_time=end,
    )

    assert len(seen_requests) == 1
    assert result.capability.access_mode == "public_unsigned"
    assert result.capability.supports_bars is True
    assert result.capability.order_placement_allowed is False
    assert result.raw_request.source == "info/candleSnapshot"
    assert result.raw_request.params["type"] == "candleSnapshot"
    assert result.raw_request.params["req"] == expected_body["req"]
    assert result.raw_request.params["documented_limit"] == "most_recent_5000_candles"
    assert result.raw_response.evidence_scope == "public_unsigned_recent_candle_snapshot"
    assert result.raw_response.row_count == 2
    assert result.raw_response.rate_limit_metadata["x-ratelimit-remaining"] == "17"
    assert result.raw_response.order_placement_instruction is False


def test_hyperliquid_info_client_records_public_funding_history_provenance() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 1, 2, tzinfo=UTC)
    expected_body = {
        "type": "fundingHistory",
        "coin": "BTC",
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000),
    }
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        assert request.method == "POST"
        assert json.loads(request.content.decode("utf-8")) == expected_body
        return httpx.Response(
            200,
            json=[
                {
                    "coin": "BTC",
                    "fundingRate": "0.0001",
                    "premium": "0.0",
                    "time": expected_body["startTime"],
                },
                {
                    "coin": "BTC",
                    "fundingRate": "-0.0002",
                    "premium": "0.0",
                    "time": expected_body["startTime"] + 3_600_000,
                },
            ],
            headers={"x-ratelimit-remaining": "11"},
        )

    client = HyperliquidInfoClient(
        base_url="https://example.test/info",
        timeout=3.0,
        transport=httpx.MockTransport(handler),
    )
    result = client.fetch_funding_history(
        coin="BTC",
        start_time=start,
        end_time=end,
    )

    assert len(seen_requests) == 1
    assert result.capability.access_mode == "public_unsigned"
    assert result.capability.supports_funding is True
    assert result.capability.order_placement_allowed is False
    assert result.raw_request.source == "info/fundingHistory"
    assert result.raw_request.params["type"] == "fundingHistory"
    assert result.raw_request.params["coin"] == "BTC"
    assert result.raw_request.params["startTime"] == expected_body["startTime"]
    assert result.raw_request.params["endTime"] == expected_body["endTime"]
    assert result.raw_request.params["documented_limit"] == "time_range_responses_return_500_elements_or_blocks"
    assert result.raw_response.evidence_scope == "public_unsigned_historical_funding_rates"
    assert result.raw_response.row_count == 2
    assert result.raw_response.rate_limit_metadata["x-ratelimit-remaining"] == "11"
    assert result.raw_response.order_placement_instruction is False


def test_hyperliquid_info_client_records_public_l2_book_provenance() -> None:
    expected_body = {
        "type": "l2Book",
        "coin": "BTC",
        "nSigFigs": 5,
        "mantissa": 2,
    }
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        assert request.method == "POST"
        assert json.loads(request.content.decode("utf-8")) == expected_body
        return httpx.Response(
            200,
            json={
                "coin": "BTC",
                "time": 1_767_225_600_000,
                "levels": [
                    [
                        {"px": "100.0", "sz": "1.25", "n": 2},
                        {"px": "99.5", "sz": "2.00", "n": 1},
                    ],
                    [
                        {"px": "100.5", "sz": "1.50", "n": 3},
                        {"px": "101.0", "sz": "3.25", "n": 1},
                    ],
                ],
            },
            headers={"x-ratelimit-remaining": "9"},
        )

    client = HyperliquidInfoClient(
        base_url="https://example.test/info",
        timeout=3.0,
        transport=httpx.MockTransport(handler),
    )
    result = client.fetch_l2_book(coin="BTC", n_sig_figs=5, mantissa=2)

    assert len(seen_requests) == 1
    assert result.capability.access_mode == "public_unsigned"
    assert result.capability.supports_bbo is True
    assert result.capability.supports_l2 is True
    assert result.capability.order_placement_allowed is False
    assert result.raw_request.source == "info/l2Book"
    assert result.raw_request.params["type"] == "l2Book"
    assert result.raw_request.params["coin"] == "BTC"
    assert result.raw_request.params["nSigFigs"] == 5
    assert result.raw_request.params["mantissa"] == 2
    assert result.raw_request.params["documented_limit"] == "max_20_levels_per_side"
    assert result.raw_response.evidence_scope == "public_unsigned_l2_book_snapshot"
    assert result.raw_response.row_count == 4
    assert result.raw_response.rate_limit_metadata["x-ratelimit-remaining"] == "9"
    assert result.raw_response.order_placement_instruction is False


def test_hyperliquid_websocket_client_records_public_trade_snapshot_provenance() -> None:
    sent_messages: list[dict[str, object]] = []

    class FakeWebSocket:
        def __init__(self) -> None:
            self.messages = [
                {"channel": "subscriptionResponse", "data": {"subscription": {"type": "trades", "coin": "BTC"}}},
                {
                    "channel": "trades",
                    "data": [
                        {
                            "coin": "BTC",
                            "side": "A",
                            "px": "100.0",
                            "sz": "1.25",
                            "hash": "0xabc",
                            "time": 1_767_225_600_000,
                            "tid": 123,
                            "users": ["0x1", "0x2"],
                        },
                        {
                            "coin": "BTC",
                            "side": "B",
                            "px": "100.5",
                            "sz": "2.00",
                            "hash": "0xdef",
                            "time": 1_767_225_600_500,
                            "tid": 124,
                            "users": ["0x3", "0x4"],
                        },
                    ],
                },
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def send(self, raw_message: str) -> None:
            sent_messages.append(json.loads(raw_message))

        def recv(self, timeout=None) -> str:
            if not self.messages:
                raise TimeoutError("no more messages")
            return json.dumps(self.messages.pop(0))

    seen_connects = []

    def fake_connect(url: str, **kwargs):
        seen_connects.append((url, kwargs))
        return FakeWebSocket()

    client = HyperliquidWebSocketClient(
        ws_url="wss://example.test/ws",
        timeout=3.0,
        connect=fake_connect,
    )
    result = client.fetch_trade_snapshot(
        coin="BTC",
        max_messages=2,
        max_rows=2,
        max_seconds=3.0,
    )

    assert seen_connects == [("wss://example.test/ws", {"open_timeout": 3.0})]
    assert sent_messages == [
        {"method": "subscribe", "subscription": {"type": "trades", "coin": "BTC"}}
    ]
    assert result.capability.access_mode == "public_unsigned"
    assert result.capability.supports_trades is True
    assert result.capability.order_placement_allowed is False
    assert result.raw_request.source == "websocket/trades"
    assert result.raw_request.params["subscription"] == {"type": "trades", "coin": "BTC"}
    assert result.raw_request.params["max_messages"] == 2
    assert result.raw_request.params["max_rows"] == 2
    assert result.raw_response.evidence_scope == "public_unsigned_websocket_trade_snapshot"
    assert result.raw_response.row_count == 2
    assert result.raw_response.order_placement_instruction is False


def test_hyperliquid_websocket_client_records_public_candle_snapshot_provenance() -> None:
    sent_messages: list[dict[str, object]] = []

    class FakeWebSocket:
        def __init__(self) -> None:
            self.messages = [
                {
                    "channel": "subscriptionResponse",
                    "data": {"subscription": {"type": "candle", "coin": "BTC", "interval": "1m"}},
                },
                {
                    "channel": "candle",
                    "data": [
                        _hyperliquid_candle_row(0),
                        _hyperliquid_candle_row(1),
                    ],
                },
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def send(self, raw_message: str) -> None:
            sent_messages.append(json.loads(raw_message))

        def recv(self, timeout=None) -> str:
            if not self.messages:
                raise TimeoutError("no more messages")
            return json.dumps(self.messages.pop(0))

    seen_connects = []

    def fake_connect(url: str, **kwargs):
        seen_connects.append((url, kwargs))
        return FakeWebSocket()

    client = HyperliquidWebSocketClient(
        ws_url="wss://example.test/ws",
        timeout=3.0,
        connect=fake_connect,
    )
    result = client.fetch_candle_snapshot(
        coin="BTC",
        interval="1m",
        max_messages=2,
        max_rows=2,
        max_seconds=3.0,
    )

    assert seen_connects == [("wss://example.test/ws", {"open_timeout": 3.0})]
    assert sent_messages == [
        {
            "method": "subscribe",
            "subscription": {"type": "candle", "coin": "BTC", "interval": "1m"},
        }
    ]
    assert result.capability.access_mode == "public_unsigned"
    assert result.capability.supports_bars is True
    assert result.capability.supports_trades is True
    assert result.capability.order_placement_allowed is False
    assert result.raw_request.source == "websocket/candle"
    assert result.raw_request.params["subscription"] == {
        "type": "candle",
        "coin": "BTC",
        "interval": "1m",
    }
    assert result.raw_request.params["max_messages"] == 2
    assert result.raw_request.params["max_rows"] == 2
    assert result.raw_response.evidence_scope == "public_unsigned_websocket_candle_snapshot"
    assert result.raw_response.row_count == 2
    assert result.raw_response.order_placement_instruction is False


def test_hyperliquid_websocket_client_records_public_bbo_snapshot_provenance() -> None:
    sent_messages: list[dict[str, object]] = []

    class FakeWebSocket:
        def __init__(self) -> None:
            self.messages = [
                {
                    "channel": "subscriptionResponse",
                    "data": {"subscription": {"type": "bbo", "coin": "BTC"}},
                },
                {
                    "channel": "bbo",
                    "data": {
                        "coin": "BTC",
                        "time": 1_767_225_600_000,
                        "bbo": [
                            {"px": "100.0", "sz": "1.25", "n": 2},
                            {"px": "100.5", "sz": "1.50", "n": 3},
                        ],
                    },
                },
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def send(self, raw_message: str) -> None:
            sent_messages.append(json.loads(raw_message))

        def recv(self, timeout=None) -> str:
            if not self.messages:
                raise TimeoutError("no more messages")
            return json.dumps(self.messages.pop(0))

    seen_connects = []

    def fake_connect(url: str, **kwargs):
        seen_connects.append((url, kwargs))
        return FakeWebSocket()

    client = HyperliquidWebSocketClient(
        ws_url="wss://example.test/ws",
        timeout=3.0,
        connect=fake_connect,
    )
    result = client.fetch_bbo_snapshot(
        coin="BTC",
        max_messages=2,
        max_rows=2,
        max_seconds=3.0,
    )

    assert seen_connects == [("wss://example.test/ws", {"open_timeout": 3.0})]
    assert sent_messages == [
        {"method": "subscribe", "subscription": {"type": "bbo", "coin": "BTC"}}
    ]
    assert result.capability.access_mode == "public_unsigned"
    assert result.capability.supports_bbo is True
    assert result.capability.supports_l2 is True
    assert result.capability.order_placement_allowed is False
    assert result.raw_request.source == "websocket/bbo"
    assert result.raw_request.params["subscription"] == {"type": "bbo", "coin": "BTC"}
    assert result.raw_request.params["max_messages"] == 2
    assert result.raw_request.params["max_rows"] == 2
    assert result.raw_response.evidence_scope == "public_unsigned_websocket_bbo_snapshot"
    assert result.raw_response.row_count == 1
    assert result.raw_response.order_placement_instruction is False


def test_hyperliquid_websocket_client_records_public_l2_book_snapshot_provenance() -> None:
    sent_messages: list[dict[str, object]] = []

    class FakeWebSocket:
        def __init__(self) -> None:
            self.messages = [
                {
                    "channel": "subscriptionResponse",
                    "data": {
                        "subscription": {
                            "type": "l2Book",
                            "coin": "BTC",
                            "nSigFigs": 5,
                            "mantissa": 2,
                        }
                    },
                },
                {
                    "channel": "l2Book",
                    "data": {
                        "coin": "BTC",
                        "time": 1_767_225_600_000,
                        "levels": [
                            [
                                {"px": "100.0", "sz": "1.25", "n": 2},
                                {"px": "99.5", "sz": "2.00", "n": 1},
                            ],
                            [
                                {"px": "100.5", "sz": "1.50", "n": 3},
                                {"px": "101.0", "sz": "3.25", "n": 1},
                            ],
                        ],
                    },
                },
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def send(self, raw_message: str) -> None:
            sent_messages.append(json.loads(raw_message))

        def recv(self, timeout=None) -> str:
            if not self.messages:
                raise TimeoutError("no more messages")
            return json.dumps(self.messages.pop(0))

    seen_connects = []

    def fake_connect(url: str, **kwargs):
        seen_connects.append((url, kwargs))
        return FakeWebSocket()

    client = HyperliquidWebSocketClient(
        ws_url="wss://example.test/ws",
        timeout=3.0,
        connect=fake_connect,
    )
    result = client.fetch_l2_book_snapshot(
        coin="BTC",
        n_sig_figs=5,
        mantissa=2,
        max_messages=2,
        max_rows=4,
        max_seconds=3.0,
    )

    assert seen_connects == [("wss://example.test/ws", {"open_timeout": 3.0})]
    assert sent_messages == [
        {
            "method": "subscribe",
            "subscription": {"type": "l2Book", "coin": "BTC", "nSigFigs": 5, "mantissa": 2},
        }
    ]
    assert result.capability.access_mode == "public_unsigned"
    assert result.capability.supports_bbo is True
    assert result.capability.supports_l2 is True
    assert result.capability.order_placement_allowed is False
    assert result.raw_request.source == "websocket/l2Book"
    assert result.raw_request.params["subscription"] == {
        "type": "l2Book",
        "coin": "BTC",
        "nSigFigs": 5,
        "mantissa": 2,
    }
    assert result.raw_request.params["max_messages"] == 2
    assert result.raw_request.params["max_rows"] == 4
    assert result.raw_response.evidence_scope == "public_unsigned_websocket_l2_book_snapshot"
    assert result.raw_response.row_count == 4
    assert result.raw_response.order_placement_instruction is False


def test_hyperliquid_universe_public_api_source_records_fetch_provenance(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_payload(day_sol=12_000_000))

    archive_root = tmp_path / "archive"
    client = HyperliquidInfoClient(
        base_url="https://example.test/info",
        transport=httpx.MockTransport(handler),
    )
    result = refresh_hyperliquid_universe(
        archive_root=archive_root,
        client=client,
        asof_date=date(2026, 6, 1),
    )
    layout = ArchiveLayout(archive_root)
    ingestion_runs = ArchiveManifestStore(layout).load_ingestion_runs()

    assert result.payload_source == "public_api"
    assert result.raw_request_id is not None
    assert result.raw_response_id is not None
    assert result.venue_adapter_id == "hyperliquid_public_info_v1"
    assert result.source_endpoint_or_subscription == "info/metaAndAssetCtxs"
    assert ingestion_runs[0].adapter_id == "hyperliquid_public_info_v1"
    assert ingestion_runs[0].source_endpoint_or_subscription == "info/metaAndAssetCtxs"
    assert "hyperliquid:perp:SOL" in {
        row.instrument_id
        for row in select_asof_universe(
            archive_root=archive_root,
            asof_date=date(2026, 6, 1),
            eligible_only=True,
        )
    }


def test_hyperliquid_universe_excludes_below_5m_day_ntl_volume(tmp_path) -> None:
    refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(day_sol=4_999_999),
        asof_date=date(2026, 6, 1),
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
    )
    sol = _by_id(rows, "hyperliquid:perp:SOL")

    assert sol.eligible is False
    assert sol.exclusion_reason == VOLUME_BELOW_THRESHOLD


def test_hyperliquid_universe_archives_excluded_instruments(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    result = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(day_sol=1),
        asof_date=date(2026, 6, 1),
    )
    layout = ArchiveLayout(archive_root)
    catalog_rows = pq.read_table(layout.resolve("manifests", "instrument_catalog.parquet")).to_pylist()
    snapshot_rows = pq.read_table(layout.resolve("manifests", "universe_snapshots.parquet")).to_pylist()

    assert any(row["instrument_id"] == "hyperliquid:perp:SOL" for row in catalog_rows)
    assert any(
        row["instrument_id"] == "hyperliquid:perp:SOL" and row["eligible"] is False
        for row in snapshot_rows
    )
    assert any(layout.layer_root("raw").rglob("*.jsonl.zst"))
    assert result.raw_file_id


def test_hyperliquid_universe_handles_hip3_prefixed_symbols(tmp_path) -> None:
    refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(include_complete_hip3=True),
        asof_date=date(2026, 6, 1),
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
    )
    hip3 = _by_id(rows, "hyperliquid:hip3:xyz:ABC")

    assert hip3.eligible is True
    assert hip3.accepted_research_evidence_allowed is True


def test_missing_hip3_reference_metadata_blocks_evidence(tmp_path) -> None:
    refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(include_incomplete_hip3=True),
        asof_date=date(2026, 6, 1),
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
    )
    hip3 = _by_id(rows, "hyperliquid:hip3:xyz:ABC")

    assert hip3.eligible is False
    assert hip3.exclusion_reason == MISSING_HIP3_METADATA
    assert hip3.accepted_research_evidence_allowed is False


def test_asof_universe_does_not_use_future_volume_snapshot(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    first = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(day_sol=4_000_000),
        asof_date=date(2026, 6, 1),
    )
    second = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(day_sol=12_000_000),
        asof_date=date(2026, 6, 2),
    )

    june_one = select_asof_universe(
        archive_root=archive_root,
        asof_date=date(2026, 6, 1),
        eligible_only=True,
    )
    june_two = select_asof_universe(
        archive_root=archive_root,
        asof_date=date(2026, 6, 2),
        eligible_only=True,
    )

    assert "hyperliquid:perp:SOL" not in {row.instrument_id for row in june_one}
    assert "hyperliquid:perp:SOL" in {row.instrument_id for row in june_two}
    diff = diff_snapshots(
        archive_root=archive_root,
        left_snapshot_id=first.snapshot_id,
        right_snapshot_id=second.snapshot_id,
    )
    assert diff["added"] == ["hyperliquid:perp:SOL"]


def test_current_universe_mode_is_sandbox_only(tmp_path) -> None:
    refresh_hyperliquid_universe(
        archive_root=tmp_path / "archive",
        payload=_payload(day_sol=12_000_000),
        asof_date=date(2026, 6, 1),
        mode=UniverseMode.CURRENT_LABELED_SANDBOX,
    )
    rows = select_asof_universe(
        archive_root=tmp_path / "archive",
        asof_date=date(2026, 6, 1),
        mode=UniverseMode.CURRENT_LABELED_SANDBOX,
    )

    assert rows
    assert all(row.evidence_scope == "current_sandbox_only" for row in rows)
    assert all(row.accepted_research_evidence_allowed is False for row in rows)


def test_universe_refresh_cli_with_fixture_creates_snapshot(tmp_path) -> None:
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps(_payload(day_sol=12_000_000)), encoding="utf-8")
    archive_root = tmp_path / "archive"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "universe",
            "refresh",
            "--venue",
            "hyperliquid",
            "--min-day-notional-usd",
            "5000000",
            "--payload-file",
            str(payload_file),
            "--archive-root",
            str(archive_root),
            "--asof-date",
            "2026-06-01",
            "--include-hip3-dexs",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "universe_snapshot_id=" in result.stdout
    assert "eligible_count=" in result.stdout
    rows = select_asof_universe(
        archive_root=archive_root,
        asof_date=date(2026, 6, 1),
        eligible_only=True,
    )
    assert "hyperliquid:perp:SOL" in {row.instrument_id for row in rows}


def test_universe_list_and_explain_cli(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    result = refresh_hyperliquid_universe(
        archive_root=archive_root,
        payload=_payload(day_sol=12_000_000),
        asof_date=date(2026, 6, 1),
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    listed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "universe",
            "list",
            "--archive-root",
            str(archive_root),
            "--asof-date",
            "2026-06-01",
            "--eligible-only",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    explained = subprocess.run(
        [
            sys.executable,
            "-m",
            "tradingbotsuite.v2.cli.main",
            "universe",
            "explain",
            "--archive-root",
            str(archive_root),
            "--snapshot",
            result.snapshot_id,
            "--instrument",
            "hyperliquid:perp:SOL",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert listed.returncode == 0
    assert "hyperliquid:perp:SOL" in listed.stdout
    assert explained.returncode == 0
    assert '"instrument_id":"hyperliquid:perp:SOL"' in explained.stdout


def _by_id(rows, instrument_id):
    matches = [row for row in rows if row.instrument_id == instrument_id]
    assert len(matches) == 1
    return matches[0]


def _payload(
    *,
    day_sol: float = 12_000_000,
    include_complete_hip3: bool = False,
    include_incomplete_hip3: bool = False,
):
    universe = [
        {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
        {"name": "SOL", "szDecimals": 2, "maxLeverage": 20},
        {"name": "LOW", "szDecimals": 1, "maxLeverage": 5},
    ]
    contexts = [
        {"dayNtlVlm": "100000000", "openInterest": "10", "markPx": "60000", "oraclePx": "60001", "funding": "0.0001"},
        {"dayNtlVlm": str(day_sol), "openInterest": "20", "markPx": "150", "oraclePx": "151", "funding": "0.0002"},
        {"dayNtlVlm": "1000", "openInterest": "1", "markPx": "1", "oraclePx": "1", "funding": "0.0"},
    ]
    if include_complete_hip3 or include_incomplete_hip3:
        hip3 = {"name": "xyz:ABC", "szDecimals": 2, "maxLeverage": 3}
        if include_complete_hip3:
            hip3.update(
                {
                    "referenceMarket": "NYSE:ABC",
                    "oracleSource": "official_reference",
                    "referenceSessionCalendar": "us_equities",
                    "weekendBehaviorDocumented": True,
                    "listingAgeDays": 200,
                    "proxyDataAvailable": True,
                }
            )
        universe.append(hip3)
        contexts.append(
            {
                "dayNtlVlm": "9000000",
                "openInterest": "4",
                "markPx": "12",
                "oraclePx": "12",
                "funding": "0.0",
            }
        )
    return [{"universe": universe}, contexts]


def _hyperliquid_candle_row(index: int) -> dict[str, object]:
    ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=index)
    open_price = 100 + index
    return {
        "t": int(ts.timestamp() * 1000),
        "T": int((ts + timedelta(minutes=1)).timestamp() * 1000),
        "s": "BTC",
        "i": "1m",
        "o": str(open_price),
        "h": str(open_price + 2),
        "l": str(open_price - 2),
        "c": str(open_price + 1),
        "v": str(10 + index),
        "n": index + 1,
    }
