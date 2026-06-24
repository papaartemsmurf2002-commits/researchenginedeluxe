from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources.binance_derivatives import (
    BinanceDerivativesContextFetchResult,
    BinanceDerivativesContextFetchStatus,
    BinanceDerivativesContextGetResult,
    build_binance_derivatives_context_request,
    fetch_binance_derivatives_context_request,
)


def test_fetch_normalizes_funding_and_open_interest_payloads() -> None:
    funding_request = build_binance_derivatives_context_request(
        family="funding_rate_history",
        symbol="btcusdt",
        start_time_ms=1,
        end_time_ms=2,
        limit=2,
    )
    funding = fetch_binance_derivatives_context_request(
        funding_request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            headers={"x-mbx-used-weight-1m": "1"},
            content=_json_bytes(
                [
                    {
                        "symbol": "BTCUSDT",
                        "fundingRate": "0.00010000",
                        "fundingTime": 1704067200000,
                        "markPrice": "42000.5",
                    }
                ]
            ),
        ),
    )

    assert funding.status == BinanceDerivativesContextFetchStatus.FETCHED
    assert funding.status_code == 200
    assert funding.headers["x-mbx-used-weight-1m"] == "1"
    assert funding.raw_row_count == 1
    assert funding.normalized_row_count == 1
    assert funding.content_sha256 is not None
    row = funding.rows[0]
    assert row.family.value == "funding_rate_history"
    assert row.timestamp_ms == 1704067200000
    assert row.publication_time_ms == 1704067200000
    assert row.numeric_fields == {
        "funding_rate": "0.00010000",
        "mark_price": "42000.5",
    }
    assert row.unit_fields == {"funding_rate": "rate", "mark_price": "USDT"}
    assert row.native_to_hyperliquid is False
    assert row.promotion_ready is False

    oi_request = build_binance_derivatives_context_request(
        family="open_interest",
        symbol="ethusdt",
    )
    oi = fetch_binance_derivatives_context_request(
        oi_request,
        get=lambda url: {
            "status_code": 200,
            "content": _json_bytes(
                {
                    "symbol": "ETHUSDT",
                    "openInterest": "123.456",
                    "time": "1704067200000",
                }
            ),
        },
    )

    assert oi.status == BinanceDerivativesContextFetchStatus.FETCHED
    assert oi.raw_row_count == 1
    assert oi.rows[0].numeric_fields == {"open_interest_contracts": "123.456"}
    assert oi.rows[0].unit_fields == {"open_interest_contracts": "contracts"}


def test_fetch_normalizes_kline_ratio_and_basis_units() -> None:
    mark_request = build_binance_derivatives_context_request(
        family="mark_price_klines",
        symbol="solusdt",
        interval="5m",
        limit=2,
    )
    mark = fetch_binance_derivatives_context_request(
        mark_request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    [
                        1704067200000,
                        "101.1",
                        "103.2",
                        "100.0",
                        "102.0",
                        "0",
                        1704067499999,
                    ]
                ]
            ),
        ),
    )

    assert mark.rows[0].bucket_seconds == 300
    assert mark.rows[0].open_time_ms == 1704067200000
    assert mark.rows[0].close_time_ms == 1704067499999
    assert mark.rows[0].numeric_fields == {
        "open_price": "101.1",
        "high_price": "103.2",
        "low_price": "100.0",
        "close_price": "102.0",
    }
    assert set(mark.rows[0].unit_fields.values()) == {"USDT"}

    taker_request = build_binance_derivatives_context_request(
        family="taker_buy_sell_volume",
        symbol="solusdt",
        period="1h",
        limit=1,
    )
    taker = fetch_binance_derivatives_context_request(
        taker_request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    {
                        "buySellRatio": "1.5",
                        "buyVol": "10.25",
                        "sellVol": "8.00",
                        "timestamp": "1704067200000",
                    }
                ]
            ),
        ),
    )

    assert taker.rows[0].bucket_seconds == 3600
    assert taker.rows[0].numeric_fields == {
        "buy_sell_ratio": "1.5",
        "taker_buy_base_asset_volume": "10.25",
        "taker_sell_base_asset_volume": "8.00",
    }
    assert taker.rows[0].unit_fields == {
        "buy_sell_ratio": "ratio",
        "taker_buy_base_asset_volume": "SOL",
        "taker_sell_base_asset_volume": "SOL",
    }

    basis_request = build_binance_derivatives_context_request(
        family="basis",
        symbol="solusdt",
        period="1d",
        limit=1,
    )
    basis = fetch_binance_derivatives_context_request(
        basis_request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    {
                        "pair": "SOLUSDT",
                        "contractType": "PERPETUAL",
                        "basis": "0.12",
                        "basisRate": "0.0003",
                        "annualizedBasisRate": "0.1095",
                        "timestamp": 1704067200000,
                    }
                ]
            ),
        ),
    )

    assert basis.rows[0].numeric_fields == {
        "basis_value": "0.12",
        "basis_rate": "0.0003",
        "annualized_basis_rate": "0.1095",
    }
    assert basis.rows[0].unit_fields == {
        "basis_value": "USDT",
        "basis_rate": "rate",
        "annualized_basis_rate": "rate",
    }


def test_fetch_normalizes_open_interest_stats_and_long_short_ratio() -> None:
    oi_stats_request = build_binance_derivatives_context_request(
        family="open_interest_statistics",
        symbol="btcusdt",
        period="5m",
        limit=1,
    )
    oi_stats = fetch_binance_derivatives_context_request(
        oi_stats_request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    {
                        "symbol": "BTCUSDT",
                        "sumOpenInterest": "20403.123",
                        "sumOpenInterestValue": "150570784.07809979",
                        "timestamp": 1704067200000,
                    }
                ]
            ),
        ),
    )

    assert oi_stats.rows[0].bucket_seconds == 300
    assert oi_stats.rows[0].numeric_fields == {
        "open_interest_contracts": "20403.123",
        "open_interest_value": "150570784.07809979",
    }
    assert oi_stats.rows[0].unit_fields == {
        "open_interest_contracts": "contracts",
        "open_interest_value": "USDT",
    }

    ratio_request = build_binance_derivatives_context_request(
        family="long_short_ratios",
        symbol="btcusdt",
        period="1d",
        limit=1,
    )
    ratio = fetch_binance_derivatives_context_request(
        ratio_request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    {
                        "symbol": "BTCUSDT",
                        "longShortRatio": "1.96",
                        "longAccount": "0.6622",
                        "shortAccount": "0.3378",
                        "timestamp": 1704067200000,
                    }
                ]
            ),
        ),
    )

    assert ratio.rows[0].numeric_fields == {
        "long_short_ratio": "1.96",
        "long_account_share": "0.6622",
        "short_account_share": "0.3378",
    }
    assert ratio.rows[0].unit_fields == {
        "long_short_ratio": "ratio",
        "long_account_share": "share",
        "short_account_share": "share",
    }


def test_fetch_failures_are_blocker_metadata() -> None:
    request = build_binance_derivatives_context_request(
        family="funding_rate_history",
        symbol="btcusdt",
    )

    http_error = fetch_binance_derivatives_context_request(
        request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=429,
            content=b"too many requests",
        ),
    )
    assert http_error.status == BinanceDerivativesContextFetchStatus.FETCH_ERROR
    assert http_error.blocked_reasons == ("http_status:429",)
    assert http_error.normalized_row_count == 0

    oversized = fetch_binance_derivatives_context_request(
        request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=b"{}",
        ),
        max_bytes=1,
    )
    assert oversized.status == BinanceDerivativesContextFetchStatus.BLOCKED
    assert oversized.blocked_reasons == ("max_bytes_exceeded",)

    invalid_json = fetch_binance_derivatives_context_request(
        request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=b"not-json",
        ),
    )
    assert invalid_json.status == BinanceDerivativesContextFetchStatus.PARSE_ERROR
    assert invalid_json.blocked_reasons[0].startswith("parse_error:")

    invalid_row = fetch_binance_derivatives_context_request(
        request,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes([["not", "an", "object"]]),
        ),
    )
    assert invalid_row.status == BinanceDerivativesContextFetchStatus.PARSE_ERROR
    assert invalid_row.blocked_reasons[0].startswith("parse_error:")


def test_fetch_result_identity_and_boundary_fail_closed() -> None:
    request = build_binance_derivatives_context_request(
        family="open_interest",
        symbol="btcusdt",
    )
    result = fetch_binance_derivatives_context_request(
        request,
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
    payload["normalized_rows_hash"] = "0" * 64
    with pytest.raises(ValidationError, match="normalized_rows_hash does not match"):
        BinanceDerivativesContextFetchResult(**payload)

    boundary_payload = result.model_dump()
    boundary_payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        BinanceDerivativesContextFetchResult(**boundary_payload)


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")
