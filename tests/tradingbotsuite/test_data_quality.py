from __future__ import annotations

import pytest

from tradingbotsuite.research.data_quality import build_manifest_data_quality_report


def _archive_manifest(**updates: object) -> dict[str, object]:
    manifest: dict[str, object] = {
        "source_name": "binance_vision",
        "source_type": "public_archive",
        "symbol": "BTCUSDT",
        "data_family": "agg_trade",
        "start_time_ms": 1_000,
        "end_time_ms": 2_000,
        "row_count": 10,
        "event_time_field": "event_time_ms",
        "receive_time_field": "receive_time_ms",
        "schema_version": "test-schema-v1",
        "content_hash": "sha256:test",
        "research_only": True,
        "schema_fields": ["event_time_ms", "receive_time_ms", "price", "size"],
        "missing_fields": [],
        "zero_filled_fields": [],
    }
    manifest.update(updates)
    return manifest


def test_manifest_data_quality_report_aggregates_observe_only_alerts() -> None:
    archive = _archive_manifest(
        gap_count=2,
        duplicate_count=1,
        provider_symbol="BTC-PERP",
        source_mismatch_reason="Provider symbol differs from normalized Binance USD-M symbol.",
    )
    missing_market_data = {
        "source": "binance_usdm_klines",
        "symbol": "ETHUSDT",
        "interval": "1m",
        "start_time_ms": 1_000,
        "end_time_ms": 2_000,
        "first_time_ms": 1_000,
        "last_time_ms": 3_000,
        "row_count": 0,
        "gap_count": 1,
        "duplicate_count": 0,
    }
    stale_journal = _archive_manifest(
        source_name="hyperliquid_archive",
        source_type="venue_archive",
        data_family="order_event",
        symbol="BTCUSDT",
        event_time_max_ms=2_000,
        receive_time_max_ms=1_900,
        schema_fields=["event_time_ms", "receive_time_ms", "order_id", "cloid"],
    )

    report = build_manifest_data_quality_report([archive, missing_market_data, stale_journal])

    assert report["research_only"] is True
    assert report["observe_only"] is True
    assert report["promotion_ready"] is False
    assert report["manifest_count"] == 3
    assert report["source_counts"] == {
        "binance_usdm_klines": 1,
        "binance_vision": 1,
        "hyperliquid_archive": 1,
    }
    assert report["family_counts"] == {"agg_trade": 1, "kline": 1, "order_event": 1}
    assert report["symbol_counts"] == {"BTCUSDT": 2, "ETHUSDT": 1}
    assert report["gap_count_total"] == 3
    assert report["duplicate_count_total"] == 1
    assert report["missing_receive_time_count"] == 1
    assert report["non_promotable_count"] == 3
    assert report["source_mismatch_count"] == 1
    assert report["missing_research_only_count"] == 1
    assert report["zero_row_manifest_count"] == 1

    alert_codes = {alert["code"] for alert in report["alerts"]}
    assert {
        "missing_receive_time",
        "gaps_detected",
        "duplicates_detected",
        "source_mismatch",
        "non_promotable_source",
        "missing_research_only",
        "zero_row_manifest",
        "timestamp_drift",
        "stale_receive_time",
    }.issubset(alert_codes)
    assert all(alert["observe_only"] is True for alert in report["alerts"])
    assert report["timestamp_drift_flags"] == [
        {
            "manifest_index": 1,
            "source": "binance_usdm_klines",
            "symbol": "ETHUSDT",
            "code": "last_time_after_end_time",
            "field": "last_time_ms",
            "reference_field": "end_time_ms",
        }
    ]
    assert report["stale_receive_time_flags"] == [
        {
            "manifest_index": 2,
            "source": "hyperliquid_archive",
            "symbol": "BTCUSDT",
            "code": "receive_time_before_event_time",
            "field": "receive_time_max_ms",
            "reference_field": "event_time_max_ms",
        }
    ]


def test_manifest_data_quality_report_accepts_single_manifest_without_io() -> None:
    varargs_report = build_manifest_data_quality_report(
        _archive_manifest(source_name="crypto_lake", source_type="commercial_archive", data_family="trade"),
        _archive_manifest(source_name="hyperliquid_archive", source_type="venue_archive", data_family="order_event"),
    )
    assert varargs_report["manifest_count"] == 2

    report = build_manifest_data_quality_report(
        _archive_manifest(
            source_name="crypto_lake",
            source_type="commercial_archive",
            data_family="trade",
            symbol="ETHUSDT",
        )
    )

    assert report["manifest_count"] == 1
    assert report["source_counts"] == {"crypto_lake": 1}
    assert report["symbol_counts"] == {"ETHUSDT": 1}
    assert report["gap_count_total"] == 0
    assert report["duplicate_count_total"] == 0
    assert report["missing_receive_time_count"] == 0
    assert report["source_mismatch_count"] == 0
    assert report["alerts"] == [
        {
            "severity": "info",
            "code": "non_promotable_source",
            "message": "One or more input manifests are diagnostic or non-promotable.",
            "observe_only": True,
            "details": {"manifest_count": 1},
        }
    ]


def test_manifest_data_quality_report_requires_at_least_one_manifest() -> None:
    with pytest.raises(ValueError, match="at least one manifest"):
        build_manifest_data_quality_report([])
