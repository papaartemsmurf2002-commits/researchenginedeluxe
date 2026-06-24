from __future__ import annotations

import pytest

from tradingbotsuite.v2.data_sources import (
    CoverageLabel,
    TradeBarInputRow,
    reconstruct_orderflow_features_from_trades,
)


SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"


def test_orderflow_feature_reconstruction_builds_vwap_and_imbalance() -> None:
    report = reconstruct_orderflow_features_from_trades(
        trade_rows=[
            _trade_row(timestamp_ms=1_000, price=100.0, quantity=1.0, side="buy"),
            _trade_row(timestamp_ms=2_000, price=102.0, quantity=3.0, side="sell"),
            _trade_row(timestamp_ms=61_000, price=99.0, quantity=2.0, side="buy"),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        bucket_seconds=60,
    )

    assert report.row_count == 2
    assert report.input_row_count == 3
    assert report.coverage_label == CoverageLabel.EXTERNAL_COMPARISON
    assert report.native_to_hyperliquid is False
    first = report.rows[0]
    assert first.trade_count == 2
    assert first.total_volume == 4.0
    assert first.total_quote_volume == 406.0
    assert first.vwap == 101.5
    assert first.buy_volume == 1.0
    assert first.sell_volume == 3.0
    assert first.trade_imbalance == -0.5
    assert first.quote_trade_imbalance == pytest.approx((100.0 - 306.0) / 406.0)
    assert first.accepted_historical_coverage_proof is False
    assert first.candidate_pack_eligible is False


def test_orderflow_feature_reconstruction_native_rows_keep_native_label() -> None:
    report = reconstruct_orderflow_features_from_trades(
        trade_rows=[
            _trade_row(
                source_id="hyperliquid_ws_trades",
                venue="hyperliquid",
                venue_symbol="BTC",
                timestamp_ms=1_000,
                price=100.0,
                quantity=1.0,
                side="buy",
                native_to_hyperliquid=True,
            )
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID
    assert report.native_to_hyperliquid is True
    assert report.promotion_ready is False
    assert report.rows[0].native_to_hyperliquid is True
    assert report.rows[0].live_signal is False


def test_orderflow_feature_reconstruction_empty_rows_are_blocker_report() -> None:
    report = reconstruct_orderflow_features_from_trades(
        trade_rows=[],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.input_row_count == 0
    assert report.blocker_reasons == ("empty_trade_rows",)
    assert report.accepted_historical_coverage_proof is False


def test_orderflow_feature_reconstruction_records_missing_side_blocker() -> None:
    report = reconstruct_orderflow_features_from_trades(
        trade_rows=[
            _trade_row(timestamp_ms=1_000, price=100.0, quantity=1.0, side=None),
            _trade_row(timestamp_ms=2_000, price=101.0, quantity=1.0, side="unknown"),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 1
    assert report.missing_side_count == 2
    assert report.blocker_reasons == ("missing_trade_side",)
    row = report.rows[0]
    assert row.unknown_side_volume == 2.0
    assert row.trade_imbalance == 0.0


def test_orderflow_feature_reconstruction_rejects_zero_volume_bucket() -> None:
    with pytest.raises(ValueError, match="total_volume must be positive"):
        reconstruct_orderflow_features_from_trades(
            trade_rows=[
                _trade_row(timestamp_ms=1_000, price=100.0, quantity=0.0, side="buy"),
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def test_orderflow_feature_reconstruction_rejects_mixed_native_and_external_rows() -> None:
    with pytest.raises(ValueError, match="cannot mix native and external trade rows"):
        reconstruct_orderflow_features_from_trades(
            trade_rows=[
                _trade_row(timestamp_ms=1_000, price=100.0, quantity=1.0, side="buy"),
                _trade_row(
                    source_id="hyperliquid_ws_trades",
                    venue="hyperliquid",
                    venue_symbol="BTC",
                    timestamp_ms=2_000,
                    price=101.0,
                    quantity=1.0,
                    side="sell",
                    native_to_hyperliquid=True,
                ),
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def _trade_row(
    *,
    timestamp_ms: int,
    price: float,
    quantity: float,
    side: str | None,
    source_id: str = "binance_vision_usdm_trades",
    venue: str = "binance",
    venue_symbol: str = "BTCUSDT",
    native_to_hyperliquid: bool = False,
) -> TradeBarInputRow:
    return TradeBarInputRow(
        source_id=source_id,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin="BTC",
        market_type="perpetual",
        source_timestamp_ms=timestamp_ms,
        price=price,
        quantity=quantity,
        side=side,
        native_to_hyperliquid=native_to_hyperliquid,
    )
