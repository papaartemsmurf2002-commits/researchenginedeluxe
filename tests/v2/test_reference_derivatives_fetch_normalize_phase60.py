from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.reference_derivatives import (
    ReferenceDerivativesFetchStatus,
    ReferenceDerivativesGetResult,
    build_reference_derivatives_availability_request,
    fetch_reference_derivatives_public_market_request,
)
from tradingbotsuite.v2.data_sources.schemas import SourceRegistryEntry


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"


def test_reference_derivatives_fixture_fetch_normalizes_dydx_and_deribit_rows() -> None:
    cases = (
        (
            "dydx_indexer_candles",
            "BTC-USD",
            "source_registry_dydx_indexer_public.json",
            {
                "candles": [
                    {
                        "startedAt": "2024-01-01T00:00:00Z",
                        "open": "1",
                        "high": "2",
                        "low": "0.5",
                        "close": "1.5",
                        "baseTokenVolume": "10",
                        "usdVolume": "15",
                        "trades": "3",
                    }
                ]
            },
        ),
        (
            "deribit_tradingview_chart",
            "BTC-PERPETUAL",
            "source_registry_deribit_public.json",
            {
                "jsonrpc": "2.0",
                "result": {
                    "status": "ok",
                    "ticks": [1704067200000],
                    "open": [1],
                    "high": [2],
                    "low": [0.5],
                    "close": [1.5],
                    "volume": [10],
                    "cost": [15],
                },
            },
        ),
    )

    for endpoint_id, symbol, source_filename, payload in cases:
        request = build_reference_derivatives_availability_request(
            endpoint_id=endpoint_id,
            symbol=symbol,
            day=date(2024, 1, 1),
        )
        result = fetch_reference_derivatives_public_market_request(
            request=request,
            source_entry=_source_entry(source_filename),
            get_probe=lambda url, payload=payload: ReferenceDerivativesGetResult(
                status_code=200,
                payload=payload,
            ),
        )

        assert result.status == ReferenceDerivativesFetchStatus.COMPLETED
        assert result.row_count == 1
        row = result.normalized_rows[0]
        assert row.endpoint_id == endpoint_id
        assert row.venue_symbol == symbol
        assert row.source_timestamp_ms == 1704067200000
        assert len(row.row_hash) == 64
        assert row.native_to_hyperliquid is False
        assert row.accepted_historical_coverage_proof is False


def test_reference_derivatives_fetch_empty_payload_fails_closed() -> None:
    request = build_reference_derivatives_availability_request(
        endpoint_id="deribit_tradingview_chart",
        symbol="BTC-PERPETUAL",
        day=date(2024, 1, 1),
    )

    result = fetch_reference_derivatives_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_deribit_public.json"),
        get_probe=lambda url: ReferenceDerivativesGetResult(
            status_code=200,
            payload={"jsonrpc": "2.0", "result": {"status": "no_data", "ticks": []}},
        ),
    )

    assert result.status == ReferenceDerivativesFetchStatus.EMPTY
    assert result.row_count == 0
    assert result.blocked_reasons == ("empty_response",)


def test_reference_derivatives_fetch_malformed_payload_fails_closed_without_rows() -> None:
    request = build_reference_derivatives_availability_request(
        endpoint_id="dydx_indexer_candles",
        symbol="BTC-USD",
        day=date(2024, 1, 1),
    )

    result = fetch_reference_derivatives_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_dydx_indexer_public.json"),
        get_probe=lambda url: ReferenceDerivativesGetResult(
            status_code=200,
            payload={"candles": [{"open": "1", "high": "2", "low": "0.5", "close": "1.5"}]},
        ),
    )

    assert result.status == ReferenceDerivativesFetchStatus.PARSE_ERROR
    assert result.row_count == 0
    assert result.blocked_reasons == ("dydx_indexer_candles candle row is missing timestamp",)


def test_reference_derivatives_fetch_api_error_fails_closed() -> None:
    request = build_reference_derivatives_availability_request(
        endpoint_id="deribit_tradingview_chart",
        symbol="BTC-PERPETUAL",
        day=date(2024, 1, 1),
    )

    result = fetch_reference_derivatives_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_deribit_public.json"),
        get_probe=lambda url: ReferenceDerivativesGetResult(
            status_code=200,
            payload={"jsonrpc": "2.0", "error": {"code": -32602, "message": "bad params"}},
        ),
    )

    assert result.status == ReferenceDerivativesFetchStatus.FETCH_ERROR
    assert result.row_count == 0
    assert result.blocked_reasons == ("deribit_error:-32602",)


def test_reference_derivatives_fetch_rejects_historical_coverage_source_claim() -> None:
    request = build_reference_derivatives_availability_request(
        endpoint_id="dydx_indexer_candles",
        symbol="BTC-USD",
        day=date(2024, 1, 1),
    )
    payload = _source_entry("source_registry_dydx_indexer_public.json").model_dump(mode="json")
    payload["accepted_historical_coverage_proof"] = True
    source = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="cannot be accepted historical coverage proof"):
        fetch_reference_derivatives_public_market_request(
            request=request,
            source_entry=source,
            get_probe=lambda url: ReferenceDerivativesGetResult(status_code=200),
        )


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )
