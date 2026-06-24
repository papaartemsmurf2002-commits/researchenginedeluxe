from __future__ import annotations

import pytest

from tradingbotsuite.v2.data_sources import (
    BinanceDerivativesContextNormalizedRow,
    CoverageLabel,
    DerivativesContextFeatureInputRow,
    reconstruct_funding_oi_features_from_context_rows,
)


SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"


def test_funding_oi_feature_reconstruction_accepts_binance_normalized_rows() -> None:
    report = reconstruct_funding_oi_features_from_context_rows(
        context_rows=[
            BinanceDerivativesContextNormalizedRow(
                family="funding_rate_history",
                symbol="BTCUSDT",
                timestamp_ms=1_704_067_200_000,
                publication_time_ms=1_704_067_200_000,
                numeric_fields={
                    "funding_rate": "0.00010000",
                    "mark_price": "42000.5",
                },
                unit_fields={"funding_rate": "rate", "mark_price": "USDT"},
            ),
            BinanceDerivativesContextNormalizedRow(
                family="open_interest_statistics",
                symbol="BTCUSDT",
                timestamp_ms=1_704_067_500_000,
                publication_time_ms=1_704_067_500_000,
                period="5m",
                bucket_seconds=300,
                numeric_fields={
                    "open_interest_contracts": "20403.123",
                    "open_interest_value": "150570784.07809979",
                },
                unit_fields={
                    "open_interest_contracts": "contracts",
                    "open_interest_value": "USDT",
                },
            ),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 2
    assert report.input_row_count == 2
    assert report.families == ("funding_rate_history", "open_interest_statistics")
    assert report.coverage_label == CoverageLabel.EXTERNAL_COMPARISON
    assert report.native_to_hyperliquid is False
    first = report.rows[0]
    assert first.venue == "binance"
    assert first.venue_symbol == "BTCUSDT"
    assert first.numeric_features == {
        "funding_rate": 0.0001,
        "mark_price": 42000.5,
    }
    assert first.unit_fields == {"funding_rate": "rate", "mark_price": "USDT"}
    assert first.accepted_historical_coverage_proof is False
    assert first.candidate_pack_eligible is False


def test_funding_oi_feature_reconstruction_native_rows_keep_native_label() -> None:
    report = reconstruct_funding_oi_features_from_context_rows(
        context_rows=[
            _context_row(
                source_id="hyperliquid_info_funding_history",
                venue="hyperliquid",
                venue_symbol="BTC",
                family="funding_rate_history",
                timestamp_ms=1_704_067_200_000,
                numeric_fields={"funding_rate": 0.0002},
                unit_fields={"funding_rate": "rate"},
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


def test_funding_oi_feature_reconstruction_empty_rows_are_blocker_report() -> None:
    report = reconstruct_funding_oi_features_from_context_rows(
        context_rows=[],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.input_row_count == 0
    assert report.blocker_reasons == ("empty_context_rows",)
    assert report.accepted_historical_coverage_proof is False


def test_funding_oi_feature_reconstruction_blocks_unsupported_family() -> None:
    report = reconstruct_funding_oi_features_from_context_rows(
        context_rows=[
            _context_row(
                family="mark_price_klines",
                timestamp_ms=1_704_067_200_000,
                numeric_fields={"close_price": 100.0},
                unit_fields={"close_price": "USDT"},
            )
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.input_row_count == 1
    assert report.blocker_reasons == ("unsupported_context_family",)


def test_funding_oi_feature_reconstruction_blocks_missing_timestamp_and_numeric_fields() -> None:
    report = reconstruct_funding_oi_features_from_context_rows(
        context_rows=[
            _context_row(timestamp_ms=None, numeric_fields={}, unit_fields={}),
        ],
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
    )

    assert report.row_count == 0
    assert report.missing_timestamp_count == 1
    assert report.missing_numeric_count == 1
    assert report.blocker_reasons == (
        "missing_context_timestamp",
        "missing_numeric_fields",
    )


def test_funding_oi_feature_reconstruction_rejects_nonfinite_numeric_feature() -> None:
    with pytest.raises(ValueError, match="must be finite"):
        reconstruct_funding_oi_features_from_context_rows(
            context_rows=[
                _context_row(
                    timestamp_ms=1_704_067_200_000,
                    numeric_fields={"funding_rate": float("nan")},
                    unit_fields={"funding_rate": "rate"},
                )
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def test_funding_oi_feature_reconstruction_rejects_mixed_native_and_external_rows() -> None:
    with pytest.raises(ValueError, match="cannot mix native and external context rows"):
        reconstruct_funding_oi_features_from_context_rows(
            context_rows=[
                _context_row(timestamp_ms=1_704_067_200_000),
                _context_row(
                    source_id="hyperliquid_info_funding_history",
                    venue="hyperliquid",
                    venue_symbol="BTC",
                    timestamp_ms=1_704_067_500_000,
                    native_to_hyperliquid=True,
                ),
            ],
            source_registry_ref=SOURCE_REGISTRY_REF,
            symbol_map_ref=SYMBOL_MAP_REF,
        )


def _context_row(
    *,
    timestamp_ms: int | None,
    family: str = "funding_rate_history",
    source_id: str = "binance_usdm_public_derivatives_context",
    venue: str = "binance",
    venue_symbol: str = "BTCUSDT",
    numeric_fields: dict[str, float] | None = None,
    unit_fields: dict[str, str] | None = None,
    native_to_hyperliquid: bool = False,
) -> DerivativesContextFeatureInputRow:
    return DerivativesContextFeatureInputRow(
        source_id=source_id,
        family=family,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin="BTC",
        market_type="perpetual",
        timestamp_ms=timestamp_ms,
        numeric_fields={"funding_rate": 0.0001} if numeric_fields is None else numeric_fields,
        unit_fields={"funding_rate": "rate"} if unit_fields is None else unit_fields,
        native_to_hyperliquid=native_to_hyperliquid,
    )
