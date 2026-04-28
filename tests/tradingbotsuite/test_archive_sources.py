from __future__ import annotations

import pytest

from tradingbotsuite.research.archive_sources import (
    ARCHIVE_SOURCE_CONTRACT_VERSION,
    SUPPORTED_ARCHIVE_SOURCES,
    archive_source_descriptors,
    assert_valid_archive_source_manifest,
    validate_archive_source_manifest,
)


def _base_manifest(**updates: object) -> dict[str, object]:
    manifest: dict[str, object] = {
        "source_name": "binance_vision",
        "source_type": "public_archive",
        "symbol": "BTCUSDT",
        "data_family": "agg_trade",
        "start_time_ms": 1712649600000,
        "end_time_ms": 1712736000000,
        "row_count": 250_000,
        "event_time_field": "event_time_ms",
        "receive_time_field": "receive_time_ms",
        "schema_version": ARCHIVE_SOURCE_CONTRACT_VERSION,
        "content_hash": "sha256:abc123",
        "research_only": True,
        "schema_fields": [
            "event_time_ms",
            "receive_time_ms",
            "trade_id",
            "price",
            "quantity",
            "is_buyer_maker",
        ],
        "missing_fields": [],
        "zero_filled_fields": [],
    }
    manifest.update(updates)
    return manifest


def test_supported_archive_descriptors_are_research_only_diagnostic_contracts() -> None:
    descriptors = archive_source_descriptors()

    assert {descriptor.source_name for descriptor in descriptors} == {
        "binance_vision",
        "crypto_lake",
        "hyperliquid_archive",
    }
    for descriptor in descriptors:
        assert descriptor.source_name in SUPPORTED_ARCHIVE_SOURCES
        assert "BTCUSDT" in descriptor.symbol_scope
        assert "ETHUSDT" in descriptor.symbol_scope
        assert descriptor.likely_data_families
        assert descriptor.timestamp_requirements
        assert descriptor.promotional_eligible_by_default is False
        assert descriptor.diagnostic_only_by_default is True


def test_valid_archive_manifest_preserves_timestamp_and_research_contract() -> None:
    result = assert_valid_archive_source_manifest(_base_manifest())

    assert result.valid is True
    assert result.research_only is True
    assert result.point_in_time_compatible is True
    assert result.promotable is False
    assert result.diagnostic_only is True
    assert result.errors == ()


def test_missing_event_time_field_is_invalid_for_point_in_time_research() -> None:
    manifest = _base_manifest()
    manifest.pop("event_time_field")

    result = validate_archive_source_manifest(manifest)

    assert result.valid is False
    assert result.point_in_time_compatible is False
    assert "missing_required_field:event_time_field" in result.errors
    assert "event_time_field_required" in result.errors
    with pytest.raises(ValueError, match="event_time_field"):
        assert_valid_archive_source_manifest(manifest)


def test_missing_receive_time_requires_unavailable_reason_and_blocks_promotion() -> None:
    no_reason = _base_manifest()
    no_reason.pop("receive_time_field")

    invalid = validate_archive_source_manifest(no_reason)
    assert invalid.valid is False
    assert "receive_time_field_or_unavailable_reason_required" in invalid.errors

    with_reason = _base_manifest(
        receive_time_unavailable_reason="Binance Vision historical ZIP has exchange event time but no local ingest receive timestamp."
    )
    with_reason.pop("receive_time_field")
    valid = assert_valid_archive_source_manifest(with_reason)

    assert valid.valid is True
    assert valid.point_in_time_compatible is False
    assert valid.promotable is False
    assert "receive_time_unavailable_non_promotable" in valid.quality_flags
    assert valid.unavailable_reason is not None


def test_hyperliquid_archive_is_diagnostic_only_without_account_journal_reconciliation() -> None:
    result = assert_valid_archive_source_manifest(
        _base_manifest(
            source_name="hyperliquid_archive",
            source_type="venue_archive",
            data_family="order_event",
            schema_fields=["event_time_ms", "receive_time_ms", "order_id", "cloid", "order_status"],
            missing_fields=["position_size", "funding_payment"],
        )
    )

    assert result.valid is True
    assert result.promotable is False
    assert result.diagnostic_only is True
    assert "account_execution_missingness_preserved" in result.quality_flags
    assert result.missing_fields == ("funding_payment", "position_size")


def test_missing_book_fields_are_preserved_and_not_treated_as_zero() -> None:
    result = assert_valid_archive_source_manifest(
        _base_manifest(
            source_name="crypto_lake",
            source_type="commercial_archive",
            data_family="order_book_l2",
            schema_fields=["event_time_ms", "receive_time_ms", "best_bid_price", "best_bid_size"],
            missing_fields=["best_ask_price", "best_ask_size", "depth_10bps_usd"],
        )
    )

    assert result.valid is True
    assert result.missing_fields == ("best_ask_price", "best_ask_size", "depth_10bps_usd")
    assert "book_field_missingness_preserved" in result.quality_flags


def test_zero_filled_book_or_execution_fields_are_rejected() -> None:
    result = validate_archive_source_manifest(
        _base_manifest(
            data_family="book_ticker",
            schema_fields=["event_time_ms", "receive_time_ms", "best_bid_price", "best_ask_price"],
            zero_filled_fields=["best_ask_size"],
        )
    )

    assert result.valid is False
    assert "protected_fields_must_not_be_zero_filled:best_ask_size" in result.errors


def test_source_mismatch_is_first_class_quality_flag_and_blocks_promotion() -> None:
    result = assert_valid_archive_source_manifest(
        _base_manifest(
            provider_symbol="BTC-PERP",
            source_mismatch_reason="Provider symbol and venue schema differ from Binance USD-M BTCUSDT.",
        )
    )

    assert "source_mismatch" in result.quality_flags
    assert "provider_symbol_differs_from_symbol" in result.quality_flags
    assert result.promotable is False
    assert result.diagnostic_only is True
