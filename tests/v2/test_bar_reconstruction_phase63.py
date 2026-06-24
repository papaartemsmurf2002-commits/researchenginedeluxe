from __future__ import annotations

import pytest

from tradingbotsuite.v2.data_sources import (
    CoverageLabel,
    SourceNativeBarInputRow,
    TradeBarInputRow,
    compare_reconstructed_trade_bars_to_source_bars,
    reconstruct_trade_bars_from_rows,
)


SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"


def test_trade_bar_reconstruction_builds_minute_ohlcv_from_external_rows() -> None:
    report = reconstruct_trade_bars_from_rows(
        trade_rows=[
            _trade_row(timestamp_ms=1_000, price=100.0, quantity=0.5, quote_quantity=50.0),
            _trade_row(timestamp_ms=59_000, price=101.0, quantity=1.5, quote_quantity=151.5),
            _trade_row(timestamp_ms=61_000, price=99.0, quantity=2.0, quote_quantity=198.0),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        bucket_seconds=60,
        expected_start_ms=0,
        expected_end_ms=120_000,
    )

    assert report.row_count == 2
    assert report.input_row_count == 3
    assert report.coverage_label == CoverageLabel.EXTERNAL_COMPARISON
    assert report.native_to_hyperliquid is False
    assert report.accepted_historical_coverage_proof is False
    first = report.rows[0]
    assert first.bar_start_ms == 0
    assert first.open == 100.0
    assert first.high == 101.0
    assert first.low == 100.0
    assert first.close == 101.0
    assert first.volume == 2.0
    assert first.quote_volume == 201.5
    assert first.trade_count == 2
    assert first.native_to_hyperliquid is False
    assert first.candidate_pack_eligible is False
    assert len(first.row_hash) == 64


def test_trade_bar_reconstruction_native_rows_keep_native_label_without_promotion() -> None:
    report = reconstruct_trade_bars_from_rows(
        trade_rows=[
            _trade_row(
                source_id="hyperliquid_ws_trades",
                venue="hyperliquid",
                venue_symbol="BTC",
                hyperliquid_coin="BTC",
                timestamp_ms=1_000,
                price=100.0,
                quantity=1.0,
                native_to_hyperliquid=True,
            )
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 1
    assert report.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID
    assert report.native_to_hyperliquid is True
    assert report.promotion_ready is False
    assert report.rows[0].native_to_hyperliquid is True
    assert report.rows[0].accepted_historical_coverage_proof is False
    assert report.rows[0].live_signal is False


def test_trade_bar_reconstruction_empty_rows_are_blocker_report() -> None:
    report = reconstruct_trade_bars_from_rows(
        trade_rows=[],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.input_row_count == 0
    assert report.blocker_reasons == ("empty_trade_rows",)
    assert report.accepted_historical_coverage_proof is False


def test_trade_bar_reconstruction_rejects_mixed_native_and_external_rows() -> None:
    with pytest.raises(ValueError, match="cannot mix native and external trade rows"):
        reconstruct_trade_bars_from_rows(
            trade_rows=[
                _trade_row(timestamp_ms=1_000, price=100.0, quantity=1.0),
                _trade_row(
                    source_id="hyperliquid_ws_trades",
                    venue="hyperliquid",
                    venue_symbol="BTC",
                    hyperliquid_coin="BTC",
                    timestamp_ms=2_000,
                    price=101.0,
                    quantity=1.0,
                    native_to_hyperliquid=True,
                ),
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def test_trade_bar_reconstruction_rejects_historical_coverage_input_claim() -> None:
    with pytest.raises(ValueError, match="not accepted historical coverage proof"):
        TradeBarInputRow(
            source_id="binance_vision_usdm_trades",
            venue="binance",
            venue_symbol="BTCUSDT",
            hyperliquid_coin="BTC",
            market_type="perpetual",
            source_timestamp_ms=1_000,
            price=100.0,
            quantity=1.0,
            accepted_historical_coverage_proof=True,
        )


def test_reconstructed_bar_comparison_passes_matching_source_bars() -> None:
    reconstruction = reconstruct_trade_bars_from_rows(
        trade_rows=[
            _trade_row(timestamp_ms=1_000, price=100.0, quantity=0.5, quote_quantity=50.0),
            _trade_row(timestamp_ms=59_000, price=101.0, quantity=1.5, quote_quantity=151.5),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    comparison = compare_reconstructed_trade_bars_to_source_bars(
        reconstruction_report=reconstruction,
        source_bars=[
            _source_bar(
                bar_start_ms=0,
                open_price=100.0,
                high=101.0,
                low=100.0,
                close=101.0,
                volume=2.0,
                quote_volume=201.5,
            )
        ],
    )

    assert comparison.passed is True
    assert comparison.blocker_reasons == ()
    assert comparison.passed_bucket_count == 1
    assert comparison.rows[0].status == "passed"
    assert comparison.rows[0].close_abs_diff == 0.0
    assert comparison.accepted_historical_coverage_proof is False
    assert comparison.candidate_pack_eligible is False


def test_reconstructed_bar_comparison_fails_missing_reconstructed_bucket() -> None:
    reconstruction = reconstruct_trade_bars_from_rows(
        trade_rows=[_trade_row(timestamp_ms=1_000, price=100.0, quantity=1.0)],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    comparison = compare_reconstructed_trade_bars_to_source_bars(
        reconstruction_report=reconstruction,
        source_bars=[
            _source_bar(bar_start_ms=0, open_price=100.0, high=100.0, low=100.0, close=100.0, volume=1.0),
            _source_bar(bar_start_ms=60_000, open_price=101.0, high=101.0, low=101.0, close=101.0, volume=1.0),
        ],
    )

    assert comparison.passed is False
    assert comparison.missing_reconstructed_count == 1
    assert comparison.blocker_reasons == ("missing_reconstructed_buckets",)
    assert comparison.rows[1].status == "missing_reconstructed"


def test_reconstructed_bar_comparison_fails_tolerance_breach() -> None:
    reconstruction = reconstruct_trade_bars_from_rows(
        trade_rows=[
            _trade_row(timestamp_ms=1_000, price=100.0, quantity=1.0),
            _trade_row(timestamp_ms=59_000, price=101.0, quantity=1.0),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    comparison = compare_reconstructed_trade_bars_to_source_bars(
        reconstruction_report=reconstruction,
        source_bars=[
            _source_bar(
                bar_start_ms=0,
                open_price=100.0,
                high=102.0,
                low=100.0,
                close=102.0,
                volume=2.0,
            )
        ],
    )

    assert comparison.passed is False
    assert comparison.failed_bucket_count == 1
    assert comparison.blocker_reasons == ("ohlcv_tolerance_failed",)
    assert "close_tolerance_exceeded" in comparison.rows[0].reasons


def test_reconstructed_bar_comparison_rejects_mismatched_venue() -> None:
    reconstruction = reconstruct_trade_bars_from_rows(
        trade_rows=[_trade_row(timestamp_ms=1_000, price=100.0, quantity=1.0)],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    with pytest.raises(ValueError, match="must share one venue"):
        compare_reconstructed_trade_bars_to_source_bars(
            reconstruction_report=reconstruction,
            source_bars=[
                _source_bar(
                    venue="okx",
                    venue_symbol="BTC-USDT-SWAP",
                    bar_start_ms=0,
                    open_price=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                    volume=1.0,
                )
            ],
        )


def _trade_row(
    *,
    timestamp_ms: int,
    price: float,
    quantity: float,
    quote_quantity: float | None = None,
    source_id: str = "binance_vision_usdm_trades",
    venue: str = "binance",
    venue_symbol: str = "BTCUSDT",
    hyperliquid_coin: str = "BTC",
    native_to_hyperliquid: bool = False,
) -> TradeBarInputRow:
    return TradeBarInputRow(
        source_id=source_id,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        market_type="perpetual",
        source_timestamp_ms=timestamp_ms,
        price=price,
        quantity=quantity,
        quote_quantity=quote_quantity,
        native_to_hyperliquid=native_to_hyperliquid,
    )


def _source_bar(
    *,
    bar_start_ms: int,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    quote_volume: float | None = None,
    source_id: str = "binance_vision_usdm_klines",
    venue: str = "binance",
    venue_symbol: str = "BTCUSDT",
    hyperliquid_coin: str = "BTC",
    native_to_hyperliquid: bool = False,
) -> SourceNativeBarInputRow:
    return SourceNativeBarInputRow(
        source_id=source_id,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        market_type="perpetual",
        coverage_label=(
            CoverageLabel.NATIVE_HYPERLIQUID
            if native_to_hyperliquid
            else CoverageLabel.EXTERNAL_COMPARISON
        ),
        bucket_seconds=60,
        bar_start_ms=bar_start_ms,
        bar_end_ms=bar_start_ms + 60_000,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        quote_volume=quote_volume,
        native_to_hyperliquid=native_to_hyperliquid,
    )
