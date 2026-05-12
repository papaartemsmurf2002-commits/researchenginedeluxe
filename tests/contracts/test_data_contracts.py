from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradingbotsuite.data.contracts import (
    CANONICAL_DATA_FAMILIES,
    DATA_MANIFEST_VERSION,
    build_data_manifest,
    data_family_contracts,
    data_source_descriptors,
    normalize_legacy_research_manifest,
    registered_only_manifest,
    validate_data_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _valid_manifest(**updates: object) -> dict[str, object]:
    manifest: dict[str, object] = {
        "manifest_version": DATA_MANIFEST_VERSION,
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "source_name": "binance_rest",
        "source_type": "rest",
        "symbol": "BTCUSDT",
        "data_family": "kline",
        "event_time_field": "event_time_ms",
        "receive_time_field": None,
        "receive_time_unavailable_reason": "historical REST backfill has no original live receive timestamp",
        "start_time_ms": 1_000,
        "end_time_ms": 61_000,
        "row_count": 1,
        "schema_version": "family-schema-v1",
        "content_hash": "sha256:abc123",
        "normalized_fields": [
            "event_time_ms",
            "symbol",
            "interval",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ],
        "missing_fields": ["receive_time_ms"],
        "quality_flags": [],
        "non_promotable_reasons": ["receive_time_unavailable"],
    }
    manifest.update(updates)
    return manifest


def test_data_family_contracts_cover_required_stage_three_families() -> None:
    assert tuple(contract.data_family for contract in data_family_contracts()) == CANONICAL_DATA_FAMILIES
    assert {
        "kline",
        "trade",
        "agg_trade",
        "book_ticker",
        "depth_snapshot",
        "funding_rate",
        "open_interest",
        "premium_index",
        "liquidation",
        "user_fill",
        "order_event",
        "position_snapshot",
    }.issubset(CANONICAL_DATA_FAMILIES)


def test_data_sources_include_implemented_and_registered_only_providers() -> None:
    descriptors = {descriptor.source_name: descriptor for descriptor in data_source_descriptors()}

    assert set(descriptors) == {
        "binance_rest",
        "binance_vision",
        "crypto_lake",
        "hyperliquid_archive",
    }
    assert descriptors["binance_rest"].implemented_for_ingestion is True
    assert descriptors["binance_vision"].implemented_for_ingestion is True
    assert descriptors["crypto_lake"].implemented_for_ingestion is True
    assert descriptors["hyperliquid_archive"].implemented_for_ingestion is False
    assert descriptors["hyperliquid_archive"].diagnostic_only_by_default is True


def test_durable_public_archive_readiness_configs_are_research_only_templates() -> None:
    for symbol in ("btcusdt", "ethusdt"):
        path = REPO_ROOT / "configs" / "research" / f"durable_public_archive_fixture_readiness_{symbol}_v1.json"
        payload = json.loads(path.read_text(encoding="utf-8"))

        assert payload["research_only"] is True
        assert payload["observe_only"] is True
        assert payload["promotion_ready"] is False
        assert payload["base_interval"] == "15m"
        assert payload["required_primary_source"] == "binance_vision"
        assert payload["required_families"] == ["bars", "lower_timeframe_bars", "agg_trade"]
        assert payload["required_context"]["agg_trade"]["feature_claim_scope"] == (
            "trade_flow_proxy_not_order_book_imbalance_or_ofi"
        )
        assert "binance_usdm_rest_latest_window_context" in payload["diagnostic_only_sources"]


def test_valid_data_manifest_is_research_only_and_non_promotable_without_receive_time() -> None:
    result = validate_data_manifest(_valid_manifest())

    assert result.valid is True
    assert result.point_in_time_compatible is False
    assert result.promotable is False
    assert validate_data_manifest(_valid_manifest(promotion_ready=True)).valid is False
    assert validate_data_manifest(_valid_manifest(observe_only=False)).valid is False
    assert "missing_receive_time" in result.quality_flags
    assert result.missing_fields == ("receive_time_ms",)


def test_missing_required_normalized_fields_are_invalid_unless_explicit() -> None:
    missing_unreported = validate_data_manifest(
        _valid_manifest(normalized_fields=["event_time_ms", "symbol", "interval", "open_price"])
    )

    assert missing_unreported.valid is False
    assert any(error.startswith("normalized_fields_missing_required") for error in missing_unreported.errors)

    missing_explicit = validate_data_manifest(
        _valid_manifest(
            normalized_fields=["event_time_ms", "symbol", "interval", "open_price"],
            missing_fields=["high_price", "low_price", "close_price", "volume", "receive_time_ms"],
        )
    )

    assert missing_explicit.valid is True
    assert "missing_required_normalized_fields" in missing_explicit.quality_flags


def test_zero_filled_protected_fields_are_rejected() -> None:
    result = validate_data_manifest(
        _valid_manifest(
            source_name="crypto_lake",
            source_type="local_file",
            data_family="depth_snapshot",
            normalized_fields=["event_time_ms", "symbol", "last_update_id", "bids", "asks"],
            zero_filled_fields=["best_ask_price"],
        )
    )

    assert result.valid is False
    assert "protected_fields_must_not_be_zero_filled:best_ask_price" in result.errors


def test_registered_only_hyperliquid_manifest_is_valid_but_diagnostic() -> None:
    manifest = registered_only_manifest(
        source_name="hyperliquid_archive",
        symbol="BTCUSDT",
        data_family="order_event",
    )

    result = validate_data_manifest(manifest)

    assert result.valid is True
    assert result.promotable is False
    assert result.point_in_time_compatible is False
    assert "registered_only" in result.quality_flags


def test_build_data_manifest_rejects_extra_boundary_overrides() -> None:
    with pytest.raises(ValueError, match="extra_must_not_override_reserved_manifest_fields:promotion_ready"):
        build_data_manifest(
            source_name="binance_rest",
            source_type="rest",
            symbol="BTCUSDT",
            data_family="kline",
            event_time_field="event_time_ms",
            receive_time_field=None,
            receive_time_unavailable_reason="unit test backfill has no receive time",
            start_time_ms=1_000,
            end_time_ms=61_000,
            row_count=1,
            content_hash="sha256:abc123",
            normalized_fields=["event_time_ms", "symbol", "interval", "open_price", "high_price", "low_price", "close_price", "volume"],
            missing_fields=["receive_time_ms"],
            non_promotable_reasons=["receive_time_unavailable"],
            extra={"promotion_ready": True},
        )


def test_data_manifest_accepts_optional_perp_context_metadata() -> None:
    result = validate_data_manifest(
        _valid_manifest(
            context_family_role="perp_context",
            latest_window_only=True,
            coverage_scope="latest_window_backfill",
            retention_policy={"scope": "direct_endpoint_latest_window", "claim": "not_multi_year_coverage"},
            stream_health={"status": "not_applicable_batch_backfill"},
        )
    )

    assert result.valid is True
    assert "perp_context_family" in result.quality_flags
    assert "latest_window_only_context" in result.quality_flags


def test_data_manifest_rejects_latest_window_multi_year_claim() -> None:
    result = validate_data_manifest(
        _valid_manifest(
            latest_window_only=True,
            coverage_scope="multi_year",
        )
    )

    assert result.valid is False
    assert "latest_window_context_cannot_claim_broad_coverage:multi_year" in result.errors


def test_data_manifest_rejects_free_sample_without_diagnostic_flag() -> None:
    result = validate_data_manifest(
        _valid_manifest(
            source_name="crypto_lake",
            source_type="local_file",
            source_access_mode="free_sample",
            coverage_scope="broad_historical",
            diagnostic_only=False,
        )
    )

    assert result.valid is False
    assert "free_sample_manifest_must_be_diagnostic_only" in result.errors
    assert "free_sample_manifest_cannot_claim_coverage_scope:broad_historical" in result.errors


def test_legacy_research_manifest_can_be_viewed_as_data_contract() -> None:
    manifest = normalize_legacy_research_manifest(
        {
            "source": "binance_usdm_klines",
            "symbol": "BTCUSDT",
            "interval": "1m",
            "start_time_ms": 1_000,
            "end_time_ms": 61_000,
            "row_count": 1,
            "sha256": "sha256:legacy",
            "normalized_fields": [
                "event_time_ms",
                "symbol",
                "interval",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
            ],
        }
    )

    result = validate_data_manifest(manifest)

    assert manifest["source_name"] == "binance_rest"
    assert manifest["data_family"] == "kline"
    assert result.valid is True


def test_data_manifest_rejects_wrong_source_type() -> None:
    result = validate_data_manifest(_valid_manifest(source_type="archive"))

    assert result.valid is False
    assert "source_type_mismatch:archive:rest" in result.errors
