from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.schemas import SourceRegistryEntry
from tradingbotsuite.v2.data_sources.spot_oracle_context import (
    SpotOracleContextFetchStatus,
    SpotOracleContextGetResult,
    build_spot_oracle_context_availability_request,
    fetch_spot_oracle_context_public_market_request,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"


def test_spot_oracle_context_fixture_fetch_normalizes_all_endpoint_rows() -> None:
    cases = (
        (
            "coinbase_spot_candles",
            "BTC-USD",
            "source_registry_coinbase_spot_public.json",
            [["1704067200", "0.5", "2", "1", "1.5", "10"]],
        ),
        (
            "kraken_spot_ohlc",
            "BTC/USD",
            "source_registry_kraken_spot_public.json",
            {
                "error": [],
                "result": {
                    "XXBTZUSD": [
                        [1704067200, "1", "2", "0.5", "1.5", "1.2", "10", "3"]
                    ],
                    "last": "1704067200",
                },
            },
        ),
        (
            "pyth_hermes_latest_price",
            "0xbtcfeed",
            "source_registry_pyth_hermes_public.json",
            {
                "parsed": [
                    {
                        "id": "0xbtcfeed",
                        "price": {"price": "4200000000000", "expo": -8, "publish_time": 1704067200},
                    }
                ]
            },
        ),
        (
            "defillama_current_price",
            "coingecko:bitcoin",
            "source_registry_defillama_public.json",
            {"coins": {"coingecko:bitcoin": {"price": 42000.5, "timestamp": 1704067200}}},
        ),
        (
            "dexscreener_pair_search",
            "BTC",
            "source_registry_dexscreener_public.json",
            {
                "pairs": [
                    {
                        "pairAddress": "0xpair",
                        "priceUsd": "42000.5",
                        "liquidity": {"usd": 123456},
                        "pairCreatedAt": 1704067200000,
                    }
                ]
            },
        ),
        (
            "geckoterminal_pool_search",
            "BTC",
            "source_registry_geckoterminal_public.json",
            {
                "data": [
                    {
                        "id": "eth_0xpool",
                        "type": "pool",
                        "attributes": {
                            "base_token_price_usd": "42000.5",
                            "updated_at": "2024-01-01T00:00:00Z",
                        },
                    }
                ]
            },
        ),
    )

    for endpoint_id, symbol, source_filename, payload in cases:
        request = build_spot_oracle_context_availability_request(
            endpoint_id=endpoint_id,
            symbol=symbol,
            day=date(2024, 1, 1),
        )
        result = fetch_spot_oracle_context_public_market_request(
            request=request,
            source_entry=_source_entry(source_filename),
            get_probe=lambda url, payload=payload: SpotOracleContextGetResult(
                status_code=200,
                payload=payload,
            ),
        )

        assert result.status == SpotOracleContextFetchStatus.COMPLETED
        assert result.row_count == 1
        row = result.normalized_rows[0]
        assert row.endpoint_id == endpoint_id
        assert row.venue_symbol == symbol
        assert row.source_timestamp_ms == 1704067200000
        assert len(row.row_hash) == 64
        assert row.native_to_hyperliquid is False
        assert row.accepted_historical_coverage_proof is False
        assert row.candidate_pack_eligible is False


def test_spot_oracle_context_fetch_empty_payload_fails_closed() -> None:
    request = build_spot_oracle_context_availability_request(
        endpoint_id="geckoterminal_pool_search",
        symbol="BTC",
        day=date(2024, 1, 1),
    )

    result = fetch_spot_oracle_context_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_geckoterminal_public.json"),
        get_probe=lambda url: SpotOracleContextGetResult(status_code=200, payload={"data": []}),
    )

    assert result.status == SpotOracleContextFetchStatus.EMPTY
    assert result.row_count == 0
    assert result.blocked_reasons == ("empty_response",)


def test_spot_oracle_context_fetch_malformed_payload_fails_closed_without_rows() -> None:
    request = build_spot_oracle_context_availability_request(
        endpoint_id="coinbase_spot_candles",
        symbol="BTC-USD",
        day=date(2024, 1, 1),
    )

    result = fetch_spot_oracle_context_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_coinbase_spot_public.json"),
        get_probe=lambda url: SpotOracleContextGetResult(status_code=200, payload=[["1704067200", "1"]]),
    )

    assert result.status == SpotOracleContextFetchStatus.PARSE_ERROR
    assert result.row_count == 0
    assert result.blocked_reasons == (
        "coinbase_spot_candles candle row must have at least 6 fields",
    )


def test_spot_oracle_context_fetch_api_error_fails_closed() -> None:
    request = build_spot_oracle_context_availability_request(
        endpoint_id="dexscreener_pair_search",
        symbol="BTC",
        day=date(2024, 1, 1),
    )

    result = fetch_spot_oracle_context_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_dexscreener_public.json"),
        get_probe=lambda url: SpotOracleContextGetResult(status_code=200, payload={"error": "bad"}),
    )

    assert result.status == SpotOracleContextFetchStatus.FETCH_ERROR
    assert result.row_count == 0
    assert result.blocked_reasons == ("dexscreener_error:bad",)


def test_spot_oracle_context_fetch_rejects_historical_coverage_source_claim() -> None:
    request = build_spot_oracle_context_availability_request(
        endpoint_id="pyth_hermes_latest_price",
        symbol="0xbtcfeed",
        day=date(2024, 1, 1),
    )
    payload = _source_entry("source_registry_pyth_hermes_public.json").model_dump(mode="json")
    payload["accepted_historical_coverage_proof"] = True
    source = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="cannot be accepted historical coverage proof"):
        fetch_spot_oracle_context_public_market_request(
            request=request,
            source_entry=source,
            get_probe=lambda url: SpotOracleContextGetResult(status_code=200),
        )


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )
