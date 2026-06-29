from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from tradingbotsuite.v2.data_sources.bybit_okx import (
    BybitOkxFetchStatus,
    BybitOkxGetResult,
    build_bybit_okx_availability_request,
    build_bybit_okx_paginated_request_plan,
    fetch_bybit_okx_public_market_pages,
    fetch_bybit_okx_public_market_request,
)
from tradingbotsuite.v2.data_sources.schemas import SourceRegistryEntry


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"


def test_bybit_kline_fixture_fetch_normalizes_stable_rows() -> None:
    request = build_bybit_okx_availability_request(
        endpoint_id="bybit_kline",
        symbol="BTCUSDT",
        day=date(2024, 1, 1),
    )

    def fake_get(url: str) -> BybitOkxGetResult:
        assert url == request.request_url
        return BybitOkxGetResult(
            status_code=200,
            payload={
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "symbol": "BTCUSDT",
                    "category": "linear",
                    "list": [
                        [
                            "1704067200000",
                            "42000.0",
                            "42100.0",
                            "41900.0",
                            "42050.0",
                            "123.45",
                            "5190000.00",
                        ]
                    ],
                },
            },
        )

    result = fetch_bybit_okx_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_bybit_public_market.json"),
        get_probe=fake_get,
    )

    assert result.status == BybitOkxFetchStatus.COMPLETED
    assert result.row_count == 1
    assert result.response_row_count == 1
    assert result.response_payload_hash is not None

    row = result.normalized_rows[0]
    assert row.source_id == "bybit_public_market"
    assert row.endpoint_id == "bybit_kline"
    assert row.venue_symbol == "BTCUSDT"
    assert row.source_timestamp_ms == 1704067200000
    assert row.numeric_fields["close"] == "42050.0"
    assert row.numeric_fields["turnover"] == "5190000.00"
    assert len(row.row_hash) == 64
    assert row.native_to_hyperliquid is False
    assert row.accepted_historical_coverage_proof is False


def test_okx_history_candle_fixture_fetch_normalizes_stable_rows() -> None:
    request = build_bybit_okx_availability_request(
        endpoint_id="okx_history_candles",
        symbol="BTC-USDT-SWAP",
        day=date(2024, 1, 1),
    )

    result = fetch_bybit_okx_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_okx_public_market.json"),
        get_probe=lambda url: BybitOkxGetResult(
            status_code=200,
            payload={
                "code": "0",
                "msg": "",
                "data": [
                    [
                        "1704067200000",
                        "42000.0",
                        "42100.0",
                        "41900.0",
                        "42050.0",
                        "10",
                        "0.25",
                        "10512.5",
                        "1",
                    ]
                ],
            },
        ),
    )

    assert result.status == BybitOkxFetchStatus.COMPLETED
    row = result.normalized_rows[0]
    assert row.source_id == "okx_public_market"
    assert row.endpoint_id == "okx_history_candles"
    assert row.venue_symbol == "BTC-USDT-SWAP"
    assert row.numeric_fields["volume_quote"] == "10512.5"
    assert row.raw_fields["confirm"] == "1"


def test_bybit_okx_fetch_blocks_snapshot_endpoint_before_probe() -> None:
    request = build_bybit_okx_availability_request(
        endpoint_id="bybit_orderbook",
        symbol="BTCUSDT",
        day=date(2024, 1, 1),
    )

    def forbidden_get(url: str) -> BybitOkxGetResult:
        raise AssertionError(f"unexpected fetch: {url}")

    result = fetch_bybit_okx_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_bybit_public_market.json"),
        get_probe=forbidden_get,
    )

    assert result.status == BybitOkxFetchStatus.BLOCKED
    assert result.row_count == 0
    assert result.http_status_code is None
    assert result.blocked_reasons == ("endpoint_does_not_support_date_window",)


def test_bybit_okx_fetch_empty_payload_fails_closed() -> None:
    request = build_bybit_okx_availability_request(
        endpoint_id="bybit_kline",
        symbol="BTCUSDT",
        day=date(2024, 1, 1),
    )

    result = fetch_bybit_okx_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_bybit_public_market.json"),
        get_probe=lambda url: BybitOkxGetResult(
            status_code=200,
            payload={"retCode": 0, "result": {"list": []}},
        ),
    )

    assert result.status == BybitOkxFetchStatus.EMPTY
    assert result.row_count == 0
    assert result.blocked_reasons == ("empty_response",)


def test_bybit_okx_fetch_malformed_payload_fails_closed_without_rows() -> None:
    request = build_bybit_okx_availability_request(
        endpoint_id="okx_history_candles",
        symbol="BTC-USDT-SWAP",
        day=date(2024, 1, 1),
    )

    result = fetch_bybit_okx_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_okx_public_market.json"),
        get_probe=lambda url: BybitOkxGetResult(
            status_code=200,
            payload={"code": "0", "data": [["1704067200000", "42000.0"]]},
        ),
    )

    assert result.status == BybitOkxFetchStatus.PARSE_ERROR
    assert result.row_count == 0
    assert result.blocked_reasons == ("okx_history_candles candle row is malformed",)


def test_bybit_okx_paginated_plan_splits_date_windows_and_caps_pages() -> None:
    day = date(2024, 1, 2)

    bybit = build_bybit_okx_paginated_request_plan(
        endpoint_id="bybit_kline",
        symbol="BTCUSDT",
        day=day,
        max_pages=4,
    )

    assert bybit.request_count == 2
    assert bybit.truncated is False
    assert bybit.page_span_ms == 60_000_000
    assert bybit.requests[0].probe_start_ms == 1704153600000
    assert bybit.requests[0].probe_end_ms == 1704213600000
    assert bybit.requests[1].probe_start_ms == 1704213600000
    assert bybit.requests[1].probe_end_ms == 1704240000000

    okx = build_bybit_okx_paginated_request_plan(
        endpoint_id="okx_history_candles",
        symbol="BTC-USDT-SWAP",
        day=day,
        max_pages=2,
    )

    assert okx.request_count == 2
    assert okx.truncated is True
    assert okx.truncation_reasons == ("page_cap_exceeded",)
    assert okx.page_span_ms == 6_000_000
    assert okx.requests[0].request_params["after"] == "1704153600000"
    assert okx.requests[0].request_params["before"] == "1704159600000"
    assert okx.requests[1].request_params["after"] == "1704159600000"

    blocked = build_bybit_okx_paginated_request_plan(
        endpoint_id="bybit_orderbook",
        symbol="BTCUSDT",
        day=day,
        max_pages=2,
    )
    assert blocked.request_count == 0
    assert blocked.blocked_reasons == ("endpoint_does_not_support_date_window",)


def test_bybit_okx_paginated_pages_fetch_with_injected_probe() -> None:
    plan = build_bybit_okx_paginated_request_plan(
        endpoint_id="bybit_open_interest",
        symbol="BTCUSDT",
        day=date(2024, 1, 1),
        max_pages=2,
    )
    assert plan.request_count == 2

    def fake_get(url: str) -> BybitOkxGetResult:
        if "startTime=1704067200000" in url:
            timestamp = "1704067200000"
            open_interest = "100"
        else:
            timestamp = "1704127200000"
            open_interest = "200"
        return BybitOkxGetResult(
            status_code=200,
            payload={
                "retCode": 0,
                "retMsg": "OK",
                "result": {
                    "list": [
                        {
                            "openInterest": open_interest,
                            "openInterestValue": "12345",
                            "timestamp": timestamp,
                        }
                    ]
                },
            },
        )

    results = fetch_bybit_okx_public_market_pages(
        plan=plan,
        source_entry=_source_entry("source_registry_bybit_public_market.json"),
        get_probe=fake_get,
    )

    assert len(results) == 2
    assert all(result.status == BybitOkxFetchStatus.COMPLETED for result in results)
    assert [result.normalized_rows[0].source_timestamp_ms for result in results] == [
        1704067200000,
        1704127200000,
    ]
    assert [result.normalized_rows[0].numeric_fields["openInterest"] for result in results] == [
        "100",
        "200",
    ]


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )
