from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.data_sources.binance_derivatives import (
    BinanceDerivativesContextBackfillResult,
    BinanceDerivativesContextBackfillStatus,
    BinanceDerivativesContextGetResult,
    run_binance_derivatives_context_backfill,
)


def test_derivatives_backfill_runs_fetch_archive_and_coverage_json(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    result = run_binance_derivatives_context_backfill(
        archive_root=archive_root,
        family="funding_rate_history",
        symbol="btcusdt",
        instrument_id="binance:perp:BTCUSDT",
        start_time_ms=0,
        end_time_ms=57_599_999,
        limit=1000,
        universe_snapshot_ref="manifests/universe/u.json",
        source_registry_ref="manifests/source_registry/s.json",
        symbol_map_ref="manifests/symbol_maps/m.json",
        archive_snapshot_ref="manifests/archive_snapshots/a.json",
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

    assert result.status == BinanceDerivativesContextBackfillStatus.COMPLETED
    assert result.accepted_for_research_reporting is True
    assert result.blocker_reasons == ()
    assert result.coverage_report_ref.startswith("manifests/coverage_reports/")
    coverage_payload = json.loads(
        ArchiveLayout(archive_root).resolve(result.coverage_report_ref).read_text(
            encoding="utf-8"
        )
    )
    assert coverage_payload["family"] == "funding_rate_history"
    assert coverage_payload["accepted_for_research_reporting"] is True
    assert coverage_payload["archive_snapshot_ref"] == "manifests/archive_snapshots/a.json"


def test_derivatives_backfill_writes_blocked_coverage_for_missing_buckets(tmp_path) -> None:
    result = run_binance_derivatives_context_backfill(
        archive_root=tmp_path / "archive",
        family="mark_price_klines",
        symbol="solusdt",
        instrument_id="binance:perp:SOLUSDT",
        start_time_ms=0,
        end_time_ms=179_999,
        interval="1m",
        limit=1000,
        universe_snapshot_ref="manifests/universe/u.json",
        source_registry_ref="manifests/source_registry/s.json",
        symbol_map_ref="manifests/symbol_maps/m.json",
        archive_snapshot_ref="manifests/archive_snapshots/a.json",
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

    assert result.status == BinanceDerivativesContextBackfillStatus.BLOCKED
    assert result.accepted_for_research_reporting is False
    assert "missing_buckets" in result.blocker_reasons
    assert "coverage_below_min" in result.blocker_reasons
    assert result.coverage_report_ref.startswith("manifests/coverage_reports/")


def test_derivatives_backfill_blocks_current_open_interest_snapshot(tmp_path) -> None:
    result = run_binance_derivatives_context_backfill(
        archive_root=tmp_path / "archive",
        family="open_interest",
        symbol="ethusdt",
        instrument_id="binance:perp:ETHUSDT",
        universe_snapshot_ref="manifests/universe/u.json",
        source_registry_ref="manifests/source_registry/s.json",
        symbol_map_ref="manifests/symbol_maps/m.json",
        archive_snapshot_ref="manifests/archive_snapshots/a.json",
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

    assert result.status == BinanceDerivativesContextBackfillStatus.BLOCKED
    assert result.blocker_reasons == ("current_context_snapshot_only",)
    assert result.coverage_report_ref.startswith("manifests/coverage_reports/")


def test_derivatives_backfill_result_identity_and_boundary_fail_closed(tmp_path) -> None:
    result = run_binance_derivatives_context_backfill(
        archive_root=tmp_path / "archive",
        family="open_interest",
        symbol="btcusdt",
        instrument_id="binance:perp:BTCUSDT",
        universe_snapshot_ref="manifests/universe/u.json",
        source_registry_ref="manifests/source_registry/s.json",
        symbol_map_ref="manifests/symbol_maps/m.json",
        archive_snapshot_ref="manifests/archive_snapshots/a.json",
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                {
                    "symbol": "BTCUSDT",
                    "openInterest": "1.0",
                    "time": 1704067200000,
                }
            ),
        ),
    )

    payload = result.model_dump()
    payload["backfill_id"] = "0" * 64
    with pytest.raises(ValidationError, match="backfill_id does not match"):
        BinanceDerivativesContextBackfillResult(**payload)

    boundary_payload = result.model_dump()
    boundary_payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        BinanceDerivativesContextBackfillResult(**boundary_payload)


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")
