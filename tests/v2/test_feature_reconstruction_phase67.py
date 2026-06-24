from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tradingbotsuite.v2.archive.microstructure import L2BookSnapshotRow
from tradingbotsuite.v2.data_sources import (
    CoverageLabel,
    L2DepthFeatureInputRow,
    reconstruct_l2_depth_features_from_rows,
)


SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"


def test_l2_depth_feature_reconstruction_builds_total_depth_and_imbalance() -> None:
    report = reconstruct_l2_depth_features_from_rows(
        l2_rows=[
            _l2_row(timestamp_ms=2_000, sequence=2, bid_depth=150.0, ask_depth=50.0, book_levels=20),
            _l2_row(timestamp_ms=1_000, sequence=1, bid_depth=100.0, ask_depth=300.0, book_levels=10),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 2
    assert report.input_row_count == 2
    assert report.coverage_label == CoverageLabel.EXTERNAL_COMPARISON
    first = report.rows[0]
    assert first.feature_timestamp_ms == 1_000
    assert first.total_depth == 400.0
    assert first.depth_imbalance == -0.5
    assert first.book_levels == 10
    assert first.accepted_historical_coverage_proof is False
    assert first.candidate_pack_eligible is False


def test_l2_depth_feature_reconstruction_accepts_archive_l2_rows() -> None:
    report = reconstruct_l2_depth_features_from_rows(
        l2_rows=[
            L2BookSnapshotRow(
                ts=datetime(2026, 1, 1, tzinfo=UTC),
                instrument_id="BTC",
                event_type="l2",
                sequence=1,
                bid_depth=12.0,
                ask_depth=8.0,
                book_levels=20,
                source="fixture_l2_source",
            )
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 1
    assert report.source_ids == ("fixture_l2_source",)
    assert report.rows[0].venue_symbol == "BTC"
    assert report.rows[0].feature_timestamp_ms == 1_767_225_600_000
    assert report.rows[0].depth_imbalance == 0.2


def test_l2_depth_feature_reconstruction_native_rows_keep_native_label() -> None:
    report = reconstruct_l2_depth_features_from_rows(
        l2_rows=[
            _l2_row(
                source_id="hyperliquid_ws_l2_book",
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


def test_l2_depth_feature_reconstruction_empty_rows_are_blocker_report() -> None:
    report = reconstruct_l2_depth_features_from_rows(
        l2_rows=[],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.input_row_count == 0
    assert report.blocker_reasons == ("empty_l2_rows",)
    assert report.accepted_historical_coverage_proof is False


def test_l2_depth_feature_reconstruction_blocks_missing_timestamp_and_zero_depth() -> None:
    report = reconstruct_l2_depth_features_from_rows(
        l2_rows=[
            _l2_row(timestamp_ms=None, bid_depth=0.0, ask_depth=0.0),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.missing_timestamp_count == 1
    assert report.zero_depth_count == 1
    assert report.blocker_reasons == ("missing_l2_timestamp", "zero_l2_depth")


def test_l2_depth_feature_reconstruction_rejects_negative_depth() -> None:
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        reconstruct_l2_depth_features_from_rows(
            l2_rows=[
                {
                    "source_id": "bybit_public_market",
                    "venue": "bybit",
                    "venue_symbol": "BTCUSDT",
                    "hyperliquid_coin": "BTC",
                    "market_type": "perpetual",
                    "event_type": "l2",
                    "timestamp_ms": 1_000,
                    "bid_depth": -1.0,
                    "ask_depth": 2.0,
                }
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def test_l2_depth_feature_reconstruction_rejects_mixed_native_and_external_rows() -> None:
    with pytest.raises(ValueError, match="cannot mix native and external L2 rows"):
        reconstruct_l2_depth_features_from_rows(
            l2_rows=[
                _l2_row(timestamp_ms=1_000),
                _l2_row(
                    source_id="hyperliquid_ws_l2_book",
                    venue="hyperliquid",
                    venue_symbol="BTC",
                    timestamp_ms=2_000,
                    native_to_hyperliquid=True,
                ),
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def _l2_row(
    *,
    timestamp_ms: int | None,
    source_id: str = "bybit_public_market",
    venue: str = "bybit",
    venue_symbol: str = "BTCUSDT",
    sequence: int = 0,
    bid_depth: float = 10.0,
    ask_depth: float = 5.0,
    book_levels: int | None = 20,
    native_to_hyperliquid: bool = False,
) -> L2DepthFeatureInputRow:
    return L2DepthFeatureInputRow(
        source_id=source_id,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin="BTC",
        market_type="perpetual",
        timestamp_ms=timestamp_ms,
        sequence=sequence,
        bid_depth=bid_depth,
        ask_depth=ask_depth,
        book_levels=book_levels,
        native_to_hyperliquid=native_to_hyperliquid,
    )
