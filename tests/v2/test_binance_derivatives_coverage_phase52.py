from __future__ import annotations

import json

from tradingbotsuite.v2.data_sources.binance_derivatives import (
    BinanceDerivativesContextGetResult,
    build_binance_derivatives_context_coverage_report,
    fetch_binance_derivatives_context_pages,
    ingest_binance_derivatives_context_pages_to_archive,
)


def test_derivatives_funding_coverage_accepts_complete_archived_window(tmp_path) -> None:
    page_result = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        start_time_ms=0,
        end_time_ms=57_599_999,
        limit=1000,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    {
                        "symbol": "BTCUSDT",
                        "fundingRate": "0.0001",
                        "fundingTime": 0,
                        "markPrice": "42000",
                    },
                    {
                        "symbol": "BTCUSDT",
                        "fundingRate": "0.0002",
                        "fundingTime": 28_800_000,
                        "markPrice": "42100",
                    },
                ]
            ),
        ),
    )
    ingest = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=tmp_path / "archive",
        page_result=page_result,
        instrument_id="binance:perp:BTCUSDT",
    )

    report = build_binance_derivatives_context_coverage_report(
        page_result=page_result,
        archive_ingest=ingest,
        universe_snapshot_ref="manifests/universe/u.json",
        source_registry_ref="manifests/source_registry/s.json",
        symbol_map_ref="manifests/symbol_maps/m.json",
        archive_snapshot_ref="manifests/archive_snapshots/a.json",
    )

    assert report.family == "funding_rate_history"
    assert report.labels[0].value == "external_comparison"
    assert report.source_ids == ("binance_usdm_public_derivatives_context",)
    assert report.expected_buckets.bucket_seconds == 28_800
    assert report.expected_buckets.count == 2
    assert report.observed_buckets == 2
    assert report.coverage_ratio == 1.0
    assert report.accepted_for_research_reporting is True
    assert report.reason == ()
    assert report.promotion_ready is False


def test_derivatives_context_coverage_reports_missing_buckets(tmp_path) -> None:
    page_result = fetch_binance_derivatives_context_pages(
        family="mark_price_klines",
        symbol="solusdt",
        start_time_ms=0,
        end_time_ms=179_999,
        interval="1m",
        limit=1000,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    [0, "10", "11", "9", "10.5", "0", 59_999],
                    [120_000, "11", "12", "10", "11.5", "0", 179_999],
                ]
            ),
        ),
    )
    ingest = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=tmp_path / "archive",
        page_result=page_result,
        instrument_id="binance:perp:SOLUSDT",
    )

    report = build_binance_derivatives_context_coverage_report(
        page_result=page_result,
        archive_ingest=ingest,
        universe_snapshot_ref="manifests/universe/u.json",
        source_registry_ref="manifests/source_registry/s.json",
        symbol_map_ref="manifests/symbol_maps/m.json",
        archive_snapshot_ref="manifests/archive_snapshots/a.json",
    )

    assert report.family == "mark_price_klines"
    assert report.expected_buckets.bucket_seconds == 60
    assert report.expected_buckets.count == 3
    assert report.observed_buckets == 2
    assert report.accepted_for_research_reporting is False
    assert "missing_buckets" in report.reason
    assert "coverage_below_min" in report.reason
    assert report.missing_buckets == ("1970-01-01T00:01:00+00:00",)


def test_current_open_interest_coverage_is_reported_but_not_accepted(tmp_path) -> None:
    page_result = fetch_binance_derivatives_context_pages(
        family="open_interest",
        symbol="ethusdt",
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                {
                    "symbol": "ETHUSDT",
                    "openInterest": "123.4",
                    "time": 1704067200000,
                }
            ),
        ),
    )
    ingest = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=tmp_path / "archive",
        page_result=page_result,
        instrument_id="binance:perp:ETHUSDT",
    )

    report = build_binance_derivatives_context_coverage_report(
        page_result=page_result,
        archive_ingest=ingest,
        universe_snapshot_ref="manifests/universe/u.json",
        source_registry_ref="manifests/source_registry/s.json",
        symbol_map_ref="manifests/symbol_maps/m.json",
        archive_snapshot_ref="manifests/archive_snapshots/a.json",
    )

    assert report.family == "open_interest"
    assert report.expected_buckets.count == 1
    assert report.coverage_ratio == 1.0
    assert report.accepted_for_research_reporting is False
    assert report.reason == ("current_context_snapshot_only",)


def test_derivatives_context_coverage_blocks_missing_archive_evidence(tmp_path) -> None:
    blocked_page = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        max_pages=1,
        get=lambda url: BinanceDerivativesContextGetResult(status_code=200, content=b"[]"),
    )
    blocked_ingest = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=tmp_path / "archive",
        page_result=blocked_page,
        instrument_id="binance:perp:BTCUSDT",
    )

    report = build_binance_derivatives_context_coverage_report(
        page_result=blocked_page,
        archive_ingest=blocked_ingest,
        universe_snapshot_ref="manifests/universe/u.json",
        source_registry_ref="manifests/source_registry/s.json",
        symbol_map_ref="manifests/symbol_maps/m.json",
    )

    assert report.accepted_for_research_reporting is False
    assert "page_result_blocked" in report.reason
    assert "archive_ingest_blocked" in report.reason
    assert "missing_archive_refs" in report.reason
    assert "missing_archive_snapshot_ref" in report.reason
    assert "no_rows" in report.reason


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")
