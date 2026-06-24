from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tradingbotsuite.v2.archive.microstructure import BBOEventRow
from tradingbotsuite.v2.data_sources import (
    BBOFeatureInputRow,
    CoverageLabel,
    reconstruct_bbo_spread_features_from_rows,
)


SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"


def test_bbo_feature_reconstruction_builds_spread_mid_and_size_imbalance() -> None:
    report = reconstruct_bbo_spread_features_from_rows(
        bbo_rows=[
            _bbo_row(timestamp_ms=2_000, sequence=2, bid=100.0, ask=100.2, bid_size=12.0, ask_size=8.0),
            _bbo_row(timestamp_ms=1_000, sequence=1, bid=99.9, ask=100.1, bid_size=10.0, ask_size=15.0),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 2
    assert report.input_row_count == 2
    assert report.coverage_label == CoverageLabel.EXTERNAL_COMPARISON
    first = report.rows[0]
    assert first.feature_timestamp_ms == 1_000
    assert first.mid_price == 100.0
    assert first.spread == pytest.approx(0.2)
    assert first.spread_bps == pytest.approx(20.0)
    assert first.top_size_imbalance == pytest.approx(-0.2)
    assert first.accepted_historical_coverage_proof is False
    assert first.candidate_pack_eligible is False


def test_bbo_feature_reconstruction_accepts_archive_bbo_event_rows() -> None:
    report = reconstruct_bbo_spread_features_from_rows(
        bbo_rows=[
            BBOEventRow(
                ts=datetime(2026, 1, 1, tzinfo=UTC),
                instrument_id="BTC",
                event_type="bbo",
                sequence=1,
                bid=100.0,
                ask=100.5,
                bid_size=5.0,
                ask_size=10.0,
                source="fixture_bbo_source",
            )
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 1
    assert report.source_ids == ("fixture_bbo_source",)
    assert report.rows[0].venue_symbol == "BTC"
    assert report.rows[0].feature_timestamp_ms == 1_767_225_600_000
    assert report.rows[0].top_size_imbalance == pytest.approx(-1 / 3)


def test_bbo_feature_reconstruction_native_rows_keep_native_label() -> None:
    report = reconstruct_bbo_spread_features_from_rows(
        bbo_rows=[
            _bbo_row(
                source_id="hyperliquid_ws_bbo",
                venue="hyperliquid",
                venue_symbol="BTC",
                timestamp_ms=1_000,
                native_to_hyperliquid=True,
            )
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID
    assert report.native_to_hyperliquid is True
    assert report.rows[0].native_to_hyperliquid is True
    assert report.rows[0].promotion_ready is False
    assert report.rows[0].live_signal is False


def test_bbo_feature_reconstruction_empty_rows_are_blocker_report() -> None:
    report = reconstruct_bbo_spread_features_from_rows(
        bbo_rows=[],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.input_row_count == 0
    assert report.blocker_reasons == ("empty_bbo_rows",)
    assert report.accepted_historical_coverage_proof is False


def test_bbo_feature_reconstruction_blocks_missing_timestamp_and_size() -> None:
    report = reconstruct_bbo_spread_features_from_rows(
        bbo_rows=[
            _bbo_row(timestamp_ms=None, bid_size=None, ask_size=10.0),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.missing_timestamp_count == 1
    assert report.missing_size_count == 1
    assert report.blocker_reasons == ("missing_bbo_timestamp", "missing_bbo_size")


def test_bbo_feature_reconstruction_rejects_crossed_books() -> None:
    with pytest.raises(ValueError, match="ask must be greater than or equal to bid"):
        reconstruct_bbo_spread_features_from_rows(
            bbo_rows=[
                _bbo_row(timestamp_ms=1_000, bid=101.0, ask=100.0),
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def test_bbo_feature_reconstruction_rejects_mixed_native_and_external_rows() -> None:
    with pytest.raises(ValueError, match="cannot mix native and external BBO rows"):
        reconstruct_bbo_spread_features_from_rows(
            bbo_rows=[
                _bbo_row(timestamp_ms=1_000),
                _bbo_row(
                    source_id="hyperliquid_ws_bbo",
                    venue="hyperliquid",
                    venue_symbol="BTC",
                    timestamp_ms=2_000,
                    native_to_hyperliquid=True,
                ),
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def _bbo_row(
    *,
    timestamp_ms: int | None,
    source_id: str = "bybit_public_market",
    venue: str = "bybit",
    venue_symbol: str = "BTCUSDT",
    sequence: int = 0,
    bid: float = 100.0,
    ask: float = 100.5,
    bid_size: float | None = 1.0,
    ask_size: float | None = 2.0,
    native_to_hyperliquid: bool = False,
) -> BBOFeatureInputRow:
    return BBOFeatureInputRow(
        source_id=source_id,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin="BTC",
        market_type="perpetual",
        timestamp_ms=timestamp_ms,
        sequence=sequence,
        bid=bid,
        ask=ask,
        bid_size=bid_size,
        ask_size=ask_size,
        native_to_hyperliquid=native_to_hyperliquid,
    )
