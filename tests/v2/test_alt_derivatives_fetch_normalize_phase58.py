from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.alt_derivatives import (
    AltDerivativesFetchStatus,
    AltDerivativesGetResult,
    build_alt_derivatives_availability_request,
    fetch_alt_derivatives_public_market_request,
)
from tradingbotsuite.v2.data_sources.schemas import SourceRegistryEntry


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"


def test_alt_derivatives_fixture_fetch_normalizes_all_venue_rows() -> None:
    cases = (
        (
            "bitget_mix_candles",
            "BTCUSDT",
            "source_registry_bitget_public_mix_market.json",
            {"code": "00000", "data": [["1704067200000", "1", "2", "0.5", "1.5", "10", "15"]]},
        ),
        (
            "mexc_contract_kline",
            "BTC_USDT",
            "source_registry_mexc_contract_public.json",
            {
                "success": True,
                "data": {
                    "time": [1704067200],
                    "open": ["1"],
                    "high": ["2"],
                    "low": ["0.5"],
                    "close": ["1.5"],
                    "vol": ["10"],
                },
            },
        ),
        (
            "gate_futures_candlesticks",
            "BTC_USDT",
            "source_registry_gate_futures_public.json",
            [{"t": 1704067200, "o": "1", "h": "2", "l": "0.5", "c": "1.5", "v": "10"}],
        ),
        (
            "kucoin_futures_kline",
            "BTCUSDTM",
            "source_registry_kucoin_futures_public.json",
            {"code": "200000", "data": [[1704067200, "1", "1.5", "2", "0.5", "10", "15"]]},
        ),
        (
            "htx_swap_history_kline",
            "BTC-USDT",
            "source_registry_htx_swap_public.json",
            {
                "status": "ok",
                "data": [
                    {
                        "id": 1704067200,
                        "open": "1",
                        "high": "2",
                        "low": "0.5",
                        "close": "1.5",
                        "amount": "10",
                        "vol": "15",
                    }
                ],
            },
        ),
    )

    for endpoint_id, symbol, source_filename, payload in cases:
        request = build_alt_derivatives_availability_request(
            endpoint_id=endpoint_id,
            symbol=symbol,
            day=date(2024, 1, 1),
        )
        result = fetch_alt_derivatives_public_market_request(
            request=request,
            source_entry=_source_entry(source_filename),
            get_probe=lambda url, payload=payload: AltDerivativesGetResult(
                status_code=200,
                payload=payload,
            ),
        )

        assert result.status == AltDerivativesFetchStatus.COMPLETED
        assert result.row_count == 1
        row = result.normalized_rows[0]
        assert row.endpoint_id == endpoint_id
        assert row.venue_symbol == symbol
        assert row.source_timestamp_ms == 1704067200000
        assert len(row.row_hash) == 64
        assert row.native_to_hyperliquid is False
        assert row.accepted_historical_coverage_proof is False


def test_alt_derivatives_fetch_empty_payload_fails_closed() -> None:
    request = build_alt_derivatives_availability_request(
        endpoint_id="htx_swap_history_kline",
        symbol="BTC-USDT",
        day=date(2024, 1, 1),
    )

    result = fetch_alt_derivatives_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_htx_swap_public.json"),
        get_probe=lambda url: AltDerivativesGetResult(
            status_code=200,
            payload={"status": "ok", "data": []},
        ),
    )

    assert result.status == AltDerivativesFetchStatus.EMPTY
    assert result.row_count == 0
    assert result.blocked_reasons == ("empty_response",)


def test_alt_derivatives_fetch_malformed_payload_fails_closed_without_rows() -> None:
    request = build_alt_derivatives_availability_request(
        endpoint_id="bitget_mix_candles",
        symbol="BTCUSDT",
        day=date(2024, 1, 1),
    )

    result = fetch_alt_derivatives_public_market_request(
        request=request,
        source_entry=_source_entry("source_registry_bitget_public_mix_market.json"),
        get_probe=lambda url: AltDerivativesGetResult(
            status_code=200,
            payload={"code": "00000", "data": [["1704067200000", "1"]]},
        ),
    )

    assert result.status == AltDerivativesFetchStatus.PARSE_ERROR
    assert result.row_count == 0
    assert result.blocked_reasons == ("candle row is malformed",)


def test_alt_derivatives_fetch_rejects_historical_coverage_source_claim() -> None:
    request = build_alt_derivatives_availability_request(
        endpoint_id="bitget_mix_candles",
        symbol="BTCUSDT",
        day=date(2024, 1, 1),
    )
    payload = _source_entry("source_registry_bitget_public_mix_market.json").model_dump(mode="json")
    payload["accepted_historical_coverage_proof"] = True
    source = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="cannot be accepted historical coverage proof"):
        fetch_alt_derivatives_public_market_request(
            request=request,
            source_entry=source,
            get_probe=lambda url: AltDerivativesGetResult(status_code=200),
        )


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )
