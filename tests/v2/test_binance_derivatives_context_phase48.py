from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources.binance_derivatives import (
    BINANCE_DERIVATIVES_CONTEXT_BASE_URL,
    BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID,
    BinanceDerivativesContextRequest,
    binance_derivatives_context_family_values,
    binance_derivatives_context_specs_payload,
    build_binance_derivatives_context_request,
)
from tradingbotsuite.v2.data_sources.schemas import (
    SourceRegistryEntry,
    require_strict_zero_dollar_source,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"


def _load_json(rel_path: str) -> dict:
    return json.loads((CONFIG_ROOT / rel_path).read_text(encoding="utf-8"))


def test_binance_derivatives_source_registry_sample_validates() -> None:
    schema = _load_json("v2_source_registry.schema.json")
    entry = SourceRegistryEntry(
        **_load_json(
            "samples/source_registry_binance_usdm_public_derivatives_context.json"
        )
    )

    require_strict_zero_dollar_source(entry)
    assert entry.source_id == BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID
    assert entry.native_to_hyperliquid is False
    assert entry.cost_class.value == "public_rate_limited"
    assert entry.accepted_historical_coverage_proof is False
    assert tuple(entry.data_families) == binance_derivatives_context_family_values()

    schema_families = set(schema["properties"]["data_families"]["items"]["enum"])
    assert set(binance_derivatives_context_family_values()).issubset(schema_families)


def test_derivatives_context_specs_cover_all_roadmap_families() -> None:
    specs = binance_derivatives_context_specs_payload()

    assert {spec["family"] for spec in specs} == set(
        binance_derivatives_context_family_values()
    )
    assert {
        spec["family"] for spec in specs if spec["history_window_days"] == 30
    } == {"taker_buy_sell_volume", "long_short_ratios", "basis"}
    assert {
        spec["family"] for spec in specs if spec["symbol_parameter"] == "pair"
    } == {"index_price_klines", "basis"}


def test_funding_and_current_open_interest_requests_are_deterministic() -> None:
    funding = build_binance_derivatives_context_request(
        family="funding_rate_history",
        symbol="btcusdt",
        start_time_ms=1_704_067_200_000,
        end_time_ms=1_704_096_000_000,
        limit=1000,
    )

    assert funding.source_id == BINANCE_DERIVATIVES_CONTEXT_SOURCE_ID
    assert funding.base_url == BINANCE_DERIVATIVES_CONTEXT_BASE_URL
    assert funding.params == {
        "symbol": "BTCUSDT",
        "startTime": 1_704_067_200_000,
        "endTime": 1_704_096_000_000,
        "limit": 1000,
    }
    assert funding.url == (
        "https://fapi.binance.com/fapi/v1/fundingRate?"
        "symbol=BTCUSDT&startTime=1704067200000&endTime=1704096000000&limit=1000"
    )
    assert funding.native_to_hyperliquid is False
    assert funding.research_only is True
    assert funding.promotion_ready is False

    open_interest = build_binance_derivatives_context_request(
        family="open_interest",
        symbol="ethusdt",
    )

    assert open_interest.params == {"symbol": "ETHUSDT"}
    assert open_interest.url == (
        "https://fapi.binance.com/fapi/v1/openInterest?symbol=ETHUSDT"
    )
    assert open_interest.limit_max is None
    assert open_interest.request_weight == 1


def test_kline_stat_ratio_and_basis_requests_use_endpoint_specific_params() -> None:
    mark = build_binance_derivatives_context_request(
        family="mark_price_klines",
        symbol="solusdt",
        interval="1m",
        start_time_ms=1,
        end_time_ms=2,
        limit=1500,
    )
    index = build_binance_derivatives_context_request(
        family="index_price_klines",
        symbol="solusdt",
        interval="5m",
        limit=500,
    )
    premium = build_binance_derivatives_context_request(
        family="premium_index_klines",
        symbol="solusdt",
        interval="1h",
        limit=10,
    )
    oi_stats = build_binance_derivatives_context_request(
        family="open_interest_statistics",
        symbol="solusdt",
        period="5m",
        limit=500,
    )
    taker = build_binance_derivatives_context_request(
        family="taker_buy_sell_volume",
        symbol="solusdt",
        period="1h",
        limit=99,
    )
    long_short = build_binance_derivatives_context_request(
        family="long_short_ratios",
        symbol="solusdt",
        period="1d",
        limit=30,
    )
    basis = build_binance_derivatives_context_request(
        family="basis",
        symbol="solusdt",
        period="1d",
        limit=30,
    )

    assert mark.endpoint == "/fapi/v1/markPriceKlines"
    assert mark.params == {
        "symbol": "SOLUSDT",
        "interval": "1m",
        "startTime": 1,
        "endTime": 2,
        "limit": 1500,
    }
    assert index.params == {"pair": "SOLUSDT", "interval": "5m", "limit": 500}
    assert premium.params == {"symbol": "SOLUSDT", "interval": "1h", "limit": 10}
    assert oi_stats.params == {"symbol": "SOLUSDT", "period": "5m", "limit": 500}
    assert oi_stats.history_window_days == 31
    assert taker.params == {"symbol": "SOLUSDT", "period": "1h", "limit": 99}
    assert long_short.params == {"symbol": "SOLUSDT", "period": "1d", "limit": 30}
    assert basis.params == {
        "pair": "SOLUSDT",
        "period": "1d",
        "contractType": "PERPETUAL",
        "limit": 30,
    }
    assert basis.url == (
        "https://fapi.binance.com/futures/data/basis?"
        "pair=SOLUSDT&period=1d&contractType=PERPETUAL&limit=30"
    )


def test_derivatives_context_request_validation_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported Binance derivatives"):
        build_binance_derivatives_context_request(
            family="unknown_family",
            symbol="BTCUSDT",
        )
    with pytest.raises(ValueError, match="requires interval"):
        build_binance_derivatives_context_request(
            family="mark_price_klines",
            symbol="BTCUSDT",
        )
    with pytest.raises(ValueError, match="requires period"):
        build_binance_derivatives_context_request(
            family="open_interest_statistics",
            symbol="BTCUSDT",
        )
    with pytest.raises(ValueError, match="limit exceeds max 500"):
        build_binance_derivatives_context_request(
            family="basis",
            symbol="BTCUSDT",
            period="1d",
            limit=501,
        )
    with pytest.raises(ValueError, match="does not accept start/end"):
        build_binance_derivatives_context_request(
            family="open_interest",
            symbol="BTCUSDT",
            start_time_ms=1,
        )
    with pytest.raises(ValueError, match="does not accept contract_type"):
        build_binance_derivatives_context_request(
            family="funding_rate_history",
            symbol="BTCUSDT",
            contract_type="CURRENT_QUARTER",
        )

    payload = build_binance_derivatives_context_request(
        family="funding_rate_history",
        symbol="BTCUSDT",
    ).model_dump()
    payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        BinanceDerivativesContextRequest(**payload)
