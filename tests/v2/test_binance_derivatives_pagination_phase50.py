from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources.binance_derivatives import (
    BinanceDerivativesContextGetResult,
    BinanceDerivativesContextPageResult,
    BinanceDerivativesContextPageStatus,
    fetch_binance_derivatives_context_pages,
)


def test_paginated_funding_fetch_advances_by_timestamp() -> None:
    requested_urls: list[str] = []

    def fake_get(url: str) -> BinanceDerivativesContextGetResult:
        requested_urls.append(url)
        if "startTime=1000" in url:
            rows = [
                {
                    "symbol": "BTCUSDT",
                    "fundingRate": "0.0001",
                    "fundingTime": 1000,
                    "markPrice": "42000",
                },
                {
                    "symbol": "BTCUSDT",
                    "fundingRate": "0.0002",
                    "fundingTime": 2000,
                    "markPrice": "42100",
                },
            ]
        elif "startTime=2001" in url:
            rows = [
                {
                    "symbol": "BTCUSDT",
                    "fundingRate": "0.0003",
                    "fundingTime": 3000,
                    "markPrice": "42200",
                }
            ]
        else:
            raise AssertionError(f"unexpected url: {url}")
        return BinanceDerivativesContextGetResult(status_code=200, content=_json_bytes(rows))

    result = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        start_time_ms=1000,
        end_time_ms=3000,
        limit=2,
        max_pages=3,
        get=fake_get,
    )

    assert result.status == BinanceDerivativesContextPageStatus.COMPLETED
    assert result.page_count == 2
    assert result.normalized_row_count == 3
    assert result.rows[-1].timestamp_ms == 3000
    assert requested_urls == list(result.page_request_urls)
    assert "startTime=2001" in requested_urls[1]
    assert len(result.page_fetch_result_ids) == 2


def test_paginated_kline_fetch_advances_by_bucket_seconds() -> None:
    requested_urls: list[str] = []

    def fake_get(url: str) -> BinanceDerivativesContextGetResult:
        requested_urls.append(url)
        if "startTime=0" in url:
            rows = [
                [0, "10", "11", "9", "10.5", "0", 59999],
                [60000, "10.5", "12", "10", "11.5", "0", 119999],
            ]
        elif "startTime=120000" in url:
            rows = [[120000, "11.5", "13", "11", "12.5", "0", 179999]]
        else:
            raise AssertionError(f"unexpected url: {url}")
        return BinanceDerivativesContextGetResult(status_code=200, content=_json_bytes(rows))

    result = fetch_binance_derivatives_context_pages(
        family="mark_price_klines",
        symbol="solusdt",
        start_time_ms=0,
        end_time_ms=179999,
        interval="1m",
        limit=2,
        max_pages=3,
        get=fake_get,
    )

    assert result.status == BinanceDerivativesContextPageStatus.COMPLETED
    assert result.page_count == 2
    assert result.normalized_row_count == 3
    assert result.rows[0].bucket_seconds == 60
    assert "startTime=120000" in requested_urls[1]


def test_current_open_interest_fetches_one_page_without_time_range() -> None:
    result = fetch_binance_derivatives_context_pages(
        family="open_interest",
        symbol="ethusdt",
        max_pages=5,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                {
                    "symbol": "ETHUSDT",
                    "openInterest": "123.4",
                    "time": 1704067200000,
                }
            ),
        ),
    )

    assert result.status == BinanceDerivativesContextPageStatus.COMPLETED
    assert result.page_count == 1
    assert result.page_request_urls == (
        "https://fapi.binance.com/fapi/v1/openInterest?symbol=ETHUSDT",
    )
    assert result.rows[0].numeric_fields == {"open_interest_contracts": "123.4"}


def test_paginated_fetch_failures_are_blocker_metadata() -> None:
    missing_bounds = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        limit=2,
        max_pages=2,
        get=lambda url: BinanceDerivativesContextGetResult(status_code=200, content=b"[]"),
    )
    assert missing_bounds.status == BinanceDerivativesContextPageStatus.BLOCKED
    assert missing_bounds.blocked_reasons == ("bounded_start_end_required",)

    blocked_page = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        start_time_ms=1,
        end_time_ms=2,
        limit=2,
        max_pages=2,
        get=lambda url: BinanceDerivativesContextGetResult(status_code=429, content=b"rate"),
    )
    assert blocked_page.status == BinanceDerivativesContextPageStatus.BLOCKED
    assert blocked_page.page_count == 1
    assert blocked_page.blocked_reasons == ("page_blocked:http_status:429",)

    max_pages = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        start_time_ms=1000,
        end_time_ms=5000,
        limit=1,
        max_pages=1,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    {
                        "symbol": "BTCUSDT",
                        "fundingRate": "0.0001",
                        "fundingTime": 1000,
                    }
                ]
            ),
        ),
    )
    assert max_pages.status == BinanceDerivativesContextPageStatus.BLOCKED
    assert max_pages.blocked_reasons == ("max_pages_exceeded",)

    invalid_max_pages = fetch_binance_derivatives_context_pages(
        family="open_interest",
        symbol="btcusdt",
        max_pages=0,
        get=lambda url: BinanceDerivativesContextGetResult(status_code=200, content=b"{}"),
    )
    assert invalid_max_pages.status == BinanceDerivativesContextPageStatus.BLOCKED
    assert invalid_max_pages.blocked_reasons == ("max_pages_must_be_positive",)


def test_page_result_identity_and_boundary_fail_closed() -> None:
    result = fetch_binance_derivatives_context_pages(
        family="open_interest",
        symbol="btcusdt",
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                {
                    "symbol": "BTCUSDT",
                    "openInterest": "1.0",
                    "time": 1704067200000,
                }
            ),
        ),
    )

    payload = result.model_dump()
    payload["page_result_id"] = "0" * 64
    with pytest.raises(ValidationError, match="page_result_id does not match"):
        BinanceDerivativesContextPageResult(**payload)

    boundary_payload = result.model_dump()
    boundary_payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        BinanceDerivativesContextPageResult(**boundary_payload)


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")
