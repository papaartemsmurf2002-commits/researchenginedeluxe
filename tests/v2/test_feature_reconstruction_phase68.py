from __future__ import annotations

import pytest

from tradingbotsuite.v2.data_sources import (
    CoverageLabel,
    CrossVenuePriceInputRow,
    reconstruct_cross_venue_basis_features_from_prices,
)


SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"


def test_cross_venue_basis_feature_reconstruction_builds_basis_rows() -> None:
    report = reconstruct_cross_venue_basis_features_from_prices(
        price_rows=[
            _price_row(
                source_id="hyperliquid_info_candle_snapshot_recent",
                venue="hyperliquid",
                venue_symbol="BTC",
                timestamp_ms=1_000,
                price=100.0,
                native_to_hyperliquid=True,
            ),
            _price_row(
                source_id="binance_vision_usdm_klines",
                venue="binance",
                venue_symbol="BTCUSDT",
                timestamp_ms=1_000,
                price=101.0,
            ),
            _price_row(
                source_id="bybit_public_market",
                venue="bybit",
                venue_symbol="BTCUSDT",
                timestamp_ms=1_000,
                price=99.5,
            ),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        primary_venue="hyperliquid",
    )

    assert report.row_count == 2
    assert report.input_row_count == 3
    assert report.coverage_label == CoverageLabel.EXTERNAL_COMPARISON
    assert report.native_to_hyperliquid is False
    binance = next(row for row in report.rows if row.comparison_venue == "binance")
    assert binance.primary_price == 100.0
    assert binance.comparison_price == 101.0
    assert binance.basis_abs == 1.0
    assert binance.basis_bps == 100.0
    assert binance.primary_native_to_hyperliquid is True
    assert binance.comparison_native_to_hyperliquid is False
    assert binance.accepted_historical_coverage_proof is False
    assert binance.candidate_pack_eligible is False


def test_cross_venue_basis_feature_reconstruction_empty_rows_are_blocker_report() -> None:
    report = reconstruct_cross_venue_basis_features_from_prices(
        price_rows=[],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.input_row_count == 0
    assert report.blocker_reasons == ("empty_cross_venue_price_rows",)
    assert report.accepted_historical_coverage_proof is False


def test_cross_venue_basis_feature_reconstruction_blocks_insufficient_venues_and_missing_primary() -> None:
    report = reconstruct_cross_venue_basis_features_from_prices(
        price_rows=[
            _price_row(venue="binance", venue_symbol="BTCUSDT", timestamp_ms=1_000, price=101.0),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        primary_venue="hyperliquid",
    )

    assert report.row_count == 0
    assert report.blocker_reasons == (
        "insufficient_cross_venue_coverage",
        "missing_primary_venue_price",
    )
    assert report.missing_primary_count == 1


def test_cross_venue_basis_feature_reconstruction_blocks_duplicate_primary() -> None:
    report = reconstruct_cross_venue_basis_features_from_prices(
        price_rows=[
            _price_row(venue="hyperliquid", venue_symbol="BTC", timestamp_ms=1_000, price=100.0),
            _price_row(venue="hyperliquid", venue_symbol="BTC", timestamp_ms=1_000, price=100.1),
            _price_row(venue="binance", venue_symbol="BTCUSDT", timestamp_ms=1_000, price=101.0),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        primary_venue="hyperliquid",
    )

    assert report.row_count == 0
    assert report.duplicate_primary_count == 1
    assert report.blocker_reasons == ("duplicate_primary_venue_price",)


def test_cross_venue_basis_feature_reconstruction_blocks_missing_timestamps() -> None:
    report = reconstruct_cross_venue_basis_features_from_prices(
        price_rows=[
            _price_row(venue="hyperliquid", venue_symbol="BTC", timestamp_ms=None, price=100.0),
            _price_row(venue="binance", venue_symbol="BTCUSDT", timestamp_ms=1_000, price=101.0),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        primary_venue="hyperliquid",
    )

    assert report.row_count == 0
    assert report.missing_timestamp_count == 1
    assert report.blocker_reasons == ("missing_cross_venue_timestamp",)


def test_cross_venue_basis_feature_reconstruction_rejects_nonpositive_prices() -> None:
    with pytest.raises(ValueError, match="greater than 0"):
        reconstruct_cross_venue_basis_features_from_prices(
            price_rows=[
                {
                    "source_id": "hyperliquid_info_candle_snapshot_recent",
                    "venue": "hyperliquid",
                    "venue_symbol": "BTC",
                    "hyperliquid_coin": "BTC",
                    "market_type": "perpetual",
                    "price_kind": "mid",
                    "timestamp_ms": 1_000,
                    "price": 0.0,
                    "native_to_hyperliquid": True,
                }
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def test_cross_venue_basis_feature_reconstruction_rejects_mixed_context() -> None:
    with pytest.raises(ValueError, match="must share one hyperliquid_coin"):
        reconstruct_cross_venue_basis_features_from_prices(
            price_rows=[
                _price_row(venue="hyperliquid", venue_symbol="BTC", hyperliquid_coin="BTC", timestamp_ms=1_000),
                _price_row(venue="binance", venue_symbol="ETHUSDT", hyperliquid_coin="ETH", timestamp_ms=1_000),
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def _price_row(
    *,
    timestamp_ms: int | None,
    source_id: str = "binance_vision_usdm_klines",
    venue: str = "binance",
    venue_symbol: str = "BTCUSDT",
    hyperliquid_coin: str = "BTC",
    price: float = 100.0,
    price_kind: str = "mid",
    native_to_hyperliquid: bool = False,
) -> CrossVenuePriceInputRow:
    return CrossVenuePriceInputRow(
        source_id=source_id,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        market_type="perpetual",
        price_kind=price_kind,
        timestamp_ms=timestamp_ms,
        price=price,
        native_to_hyperliquid=native_to_hyperliquid,
    )
