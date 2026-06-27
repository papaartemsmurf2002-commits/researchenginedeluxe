from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from tradingbotsuite.v2.data_sources import (
    CentralMarketHistoryFamily,
    CentralMarketHistoryProviderStatus,
    CentralMarketHistorySourceMetadata,
    append_central_market_history_manifest_entry,
    central_market_history_row_from_event,
    central_market_history_row_from_ohlcv,
    write_central_market_history_batch,
    write_central_market_history_event_payload_batch,
    write_central_market_history_ohlcv_payload_batch,
)


def test_central_market_history_store_writes_append_manifest_and_dedupes_ohlcv(tmp_path: Path) -> None:
    rows = [
        _ohlcv("binance_usdm", "BTC", "BTCUSDT", close=100.0, volume=10.0),
        _ohlcv("binance_usdm", "BTC", "BTCUSDT", close=100.0, volume=10.0),
        _ohlcv("bybit_linear", "BTC", "BTCUSDT", close=101.0, volume=30.0),
    ]

    result = write_central_market_history_batch(
        root=tmp_path / "central_market_history",
        run_id="unit-central-market-history",
        rows=rows,
        source_metadata=_sources("binance_usdm", "bybit_linear"),
    )

    assert result.centralized_market_history_ready is True
    assert result.row_count == 2
    assert result.duplicate_row_count == 1

    root = tmp_path / "central_market_history"
    manifest = json.loads((root / result.manifest_ref).read_text(encoding="utf-8"))
    assert manifest["quality_report"]["hyperliquid_rows_present"] is False
    assert manifest["quality_report"]["hyperliquid_missing_not_blocking"] is True
    assert manifest["quality_report"]["equivalent_ohlcv_pair_count"] == 1
    assert manifest["quality_report"]["ohlcv_comparisons"][0]["status"] == (
        CentralMarketHistoryProviderStatus.EQUIVALENT_RESEARCH_DATA.value
    )
    assert manifest["research_only"] is True
    assert manifest["promotion_ready"] is False
    assert manifest["candidate_pack_eligible"] is False
    assert manifest["live_signal"] is False
    assert manifest["paper_signal"] is False
    assert manifest["order_placement_instruction"] is False
    assert manifest["sizing_instruction"] is False
    assert manifest["runtime_mode_change"] is False

    append_lines = (root / "manifests" / "append_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(append_lines) == 1
    assert json.loads(append_lines[0])["manifest_id"] == result.manifest_id
    table = pq.read_table(root / result.normalized_ref)
    assert table.num_rows == 2


def test_central_market_history_marks_ohlcv_divergence_provider_specific(tmp_path: Path) -> None:
    rows = [
        _ohlcv("binance_usdm", "ETH", "ETHUSDT", close=100.0),
        _ohlcv("bybit_linear", "ETH", "ETHUSDT", close=107.0),
    ]

    result = write_central_market_history_batch(
        root=tmp_path / "central_market_history",
        run_id="unit-divergent-market-history",
        rows=rows,
        source_metadata=_sources("binance_usdm", "bybit_linear"),
    )

    manifest = json.loads((tmp_path / "central_market_history" / result.manifest_ref).read_text(encoding="utf-8"))
    comparison = manifest["quality_report"]["ohlcv_comparisons"][0]
    assert result.centralized_market_history_ready is True
    assert comparison["status"] == CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_DIVERGENT.value
    assert comparison["max_abs_price_pct_diff"] > 0.05
    assert manifest["quality_report"]["provider_specific_pair_count"] == 1


def test_central_market_history_relaxes_cross_provider_equality_for_trade_rows(tmp_path: Path) -> None:
    rows = [
        central_market_history_row_from_event(
            provider="binance_usdm",
            source_id="unit_binance_usdm",
            source_access_mode="zero_cost_public_api",
            family=CentralMarketHistoryFamily.TRADE,
            normalized_symbol="BTC",
            venue_symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            event_id="b-1",
            numeric_fields={"price": 100.0, "quantity": 1.0},
            raw_fields={"trade_id": "b-1"},
            provenance_refs=("unit-binance-trades",),
        ),
        central_market_history_row_from_event(
            provider="bybit_linear",
            source_id="unit_bybit_linear",
            source_access_mode="zero_cost_public_api",
            family=CentralMarketHistoryFamily.TRADE,
            normalized_symbol="BTC",
            venue_symbol="BTCUSDT",
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            event_id="y-1",
            numeric_fields={"price": 110.0, "quantity": 2.0},
            raw_fields={"trade_id": "y-1"},
            provenance_refs=("unit-bybit-trades",),
        ),
    ]

    result = write_central_market_history_batch(
        root=tmp_path / "central_market_history",
        run_id="unit-trade-market-history",
        rows=rows,
        source_metadata=_sources("binance_usdm", "bybit_linear"),
    )

    manifest = json.loads((tmp_path / "central_market_history" / result.manifest_ref).read_text(encoding="utf-8"))
    assert result.centralized_market_history_ready is True
    assert manifest["quality_report"]["ohlcv_comparisons"] == []
    assert {
        report["quality_status"]
        for report in manifest["quality_report"]["coverage_reports"]
    } == {CentralMarketHistoryProviderStatus.PROVIDER_SPECIFIC_PASS.value}


def test_fast_ohlcv_payload_writer_uses_compact_raw_source_index(tmp_path: Path) -> None:
    raw_sha = "a" * 64
    rows = [
        {
            "provider": "binance_usdm",
            "source_id": "unit_binance_usdm_archive",
            "source_access_mode": "zero_cost_public_archive",
            "normalized_symbol": "BTC",
            "venue_symbol": "BTCUSDT",
            "timeframe": "1m",
            "timestamp_ms": 1704067200000,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 10.0,
            "quote_volume": 1005.0,
            "trade_count": 7,
            "provenance_refs": ["raw_sources/binance/BTCUSDT-2024-01.zip"],
            "raw_ref": "raw_sources/binance/BTCUSDT-2024-01.zip",
            "raw_sha256": raw_sha,
        },
        {
            "provider": "binance_usdm",
            "source_id": "unit_binance_usdm_archive",
            "source_access_mode": "zero_cost_public_archive",
            "normalized_symbol": "BTC",
            "venue_symbol": "BTCUSDT",
            "timeframe": "1m",
            "timestamp_ms": 1704067260000,
            "open": 100.5,
            "high": 101.5,
            "low": 100.0,
            "close": 101.0,
            "volume": 11.0,
            "quote_volume": 1111.0,
            "trade_count": 8,
            "provenance_refs": ["raw_sources/binance/BTCUSDT-2024-01.zip"],
            "raw_ref": "raw_sources/binance/BTCUSDT-2024-01.zip",
            "raw_sha256": raw_sha,
        },
    ]

    result = write_central_market_history_ohlcv_payload_batch(
        root=tmp_path / "central_market_history",
        run_id="unit-fast-ohlcv-payload-market-history",
        rows=rows,
        source_metadata=(
            CentralMarketHistorySourceMetadata(
                provider="binance_usdm",
                source_id="unit_binance_usdm_archive",
                source_access_mode="zero_cost_public_archive",
                source_ref="https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01.zip",
                raw_ref="raw_sources/binance/BTCUSDT-2024-01.zip",
                raw_sha256=raw_sha,
                official_public_source=True,
            ),
        ),
    )

    root = tmp_path / "central_market_history"
    manifest = json.loads((root / result.manifest_ref).read_text(encoding="utf-8"))
    raw_index = json.loads((root / manifest["raw_ref"]).read_text(encoding="utf-8"))
    table = pq.read_table(root / result.normalized_ref)

    assert result.centralized_market_history_ready is True
    assert result.row_count == 2
    assert result.duplicate_row_count == 0
    assert manifest["raw_ref"].endswith("-raw_sources.json")
    assert raw_index["manifest_type"] == "central_market_history_raw_source_index"
    assert raw_index["raw_sources"][0]["row_count"] == 2
    assert table.num_rows == 2
    assert set(table.column_names) >= {"row_hash", "source_row_hash", "raw_ref", "timestamp_ms"}
    assert manifest["quality_report"]["coverage_reports"][0]["coverage_ratio"] == 1.0
    assert manifest["research_only"] is True
    assert manifest["candidate_pack_eligible"] is False
    assert manifest["runtime_mode_change"] is False
    append_lines = (root / "manifests" / "append_manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(append_lines[0])["writer"] == "fast_ohlcv_payload_batch_v1"


def test_fast_ohlcv_payload_writer_can_defer_verified_manifest_append(tmp_path: Path) -> None:
    root = tmp_path / "central_market_history"
    raw_ref = "raw_sources/binance/BTCUSDT-2024-01.zip"
    raw_sha = "a" * 64
    rows = [
        {
            "provider": "binance_usdm",
            "source_id": "unit_binance_usdm_archive",
            "source_access_mode": "zero_cost_public_archive",
            "normalized_symbol": "BTC",
            "venue_symbol": "BTCUSDT",
            "timeframe": "1m",
            "timestamp_ms": 1704067200000,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 10.0,
            "quote_volume": 1005.0,
            "trade_count": 7,
            "provenance_refs": [raw_ref],
            "raw_ref": raw_ref,
            "raw_sha256": raw_sha,
        },
    ]

    result = write_central_market_history_ohlcv_payload_batch(
        root=root,
        run_id="unit-fast-deferred-append-market-history",
        rows=rows,
        source_metadata=(
            CentralMarketHistorySourceMetadata(
                provider="binance_usdm",
                source_id="unit_binance_usdm_archive",
                source_access_mode="zero_cost_public_archive",
                source_ref="https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01.zip",
                raw_ref=raw_ref,
                raw_sha256=raw_sha,
                official_public_source=True,
            ),
        ),
        append_to_manifest=False,
    )

    append_path = root / "manifests" / "append_manifest.jsonl"
    assert not append_path.exists()

    append_central_market_history_manifest_entry(
        root=root,
        run_id="unit-fast-deferred-append-market-history",
        manifest_ref=result.manifest_ref,
        manifest_sha256=result.manifest_sha256,
    )
    append_central_market_history_manifest_entry(
        root=root,
        run_id="unit-fast-deferred-append-market-history",
        manifest_ref=result.manifest_ref,
        manifest_sha256=result.manifest_sha256,
    )

    append_lines = append_path.read_text(encoding="utf-8").splitlines()
    assert len(append_lines) == 1
    appended = json.loads(append_lines[0])
    assert appended["manifest_ref"] == result.manifest_ref
    assert appended["manifest_sha256"] == result.manifest_sha256
    assert appended["research_only"] is True
    assert appended["candidate_pack_eligible"] is False
    assert appended["runtime_mode_change"] is False


def test_fast_event_payload_writer_preserves_same_millisecond_events(tmp_path: Path) -> None:
    root = tmp_path / "central_market_history"
    raw_ref = "raw_sources/binance/BTCUSDT-trades-2024-01-01.zip"
    raw_sha = "b" * 64
    rows = [
        {
            "provider": "binance_usdm",
            "source_id": "binance_vision_futures_um_daily_trades_archive",
            "source_access_mode": "zero_cost_public_archive",
            "family": CentralMarketHistoryFamily.TRADE.value,
            "normalized_symbol": "BTC",
            "venue_symbol": "BTCUSDT",
            "timestamp_ms": 1704067203175,
            "event_id": "350343208",
            "numeric_fields": {"price": 108.77, "quantity": 1.4, "is_buyer_maker": 1.0},
            "raw_fields": {"id": "350343208"},
            "provenance_refs": [raw_ref],
            "raw_ref": raw_ref,
            "raw_sha256": raw_sha,
        },
        {
            "provider": "binance_usdm",
            "source_id": "binance_vision_futures_um_daily_trades_archive",
            "source_access_mode": "zero_cost_public_archive",
            "family": CentralMarketHistoryFamily.TRADE.value,
            "normalized_symbol": "BTC",
            "venue_symbol": "BTCUSDT",
            "timestamp_ms": 1704067203175,
            "event_id": "350343209",
            "numeric_fields": {"price": 108.76, "quantity": 0.4, "is_buyer_maker": 1.0},
            "raw_fields": {"id": "350343209"},
            "provenance_refs": [raw_ref],
            "raw_ref": raw_ref,
            "raw_sha256": raw_sha,
        },
    ]

    result = write_central_market_history_event_payload_batch(
        root=root,
        run_id="unit-fast-event-payload-market-history",
        rows=rows,
        source_metadata=(
            CentralMarketHistorySourceMetadata(
                provider="binance_usdm",
                source_id="binance_vision_futures_um_daily_trades_archive",
                source_access_mode="zero_cost_public_archive",
                source_ref="https://data.binance.vision/data/futures/um/daily/trades/BTCUSDT/BTCUSDT-trades-2024-01-01.zip",
                raw_ref=raw_ref,
                raw_sha256=raw_sha,
                official_public_source=True,
            ),
        ),
    )

    manifest = json.loads((root / result.manifest_ref).read_text(encoding="utf-8"))
    raw_index = json.loads((root / manifest["raw_ref"]).read_text(encoding="utf-8"))
    table = pq.read_table(root / result.normalized_ref)
    append_lines = (root / "manifests" / "append_manifest.jsonl").read_text(encoding="utf-8").splitlines()

    assert result.centralized_market_history_ready is True
    assert result.row_count == 2
    assert result.duplicate_row_count == 0
    assert raw_index["writer"] == "fast_event_payload_batch_v1"
    assert raw_index["raw_sources"][0]["row_count"] == 2
    assert table.num_rows == 2
    assert manifest["quality_report"]["coverage_reports"][0]["family"] == CentralMarketHistoryFamily.TRADE.value
    assert json.loads(append_lines[0])["writer"] == "fast_event_payload_batch_v1"
    assert manifest["research_only"] is True
    assert manifest["order_placement_instruction"] is False


def test_central_market_history_source_metadata_rejects_paid_or_unverifiable_sources() -> None:
    with pytest.raises(ValueError, match="paid_source_excluded"):
        CentralMarketHistorySourceMetadata(
            provider="paid_vendor",
            source_id="paid_vendor_history",
            source_access_mode="paid_api",
            source_ref="https://vendor.invalid/history",
            paid_required=True,
        )

    with pytest.raises(ValueError, match="unverifiable_source_excluded"):
        CentralMarketHistorySourceMetadata(
            provider="local_dump",
            source_id="unverified_dump",
            source_access_mode="zero_cost_public_api",
            source_ref="local/unverified.jsonl",
            local_existing_repo_ref=True,
            verifiable=False,
        )


def _ohlcv(
    provider: str,
    symbol: str,
    venue_symbol: str,
    *,
    close: float,
    volume: float = 10.0,
) -> object:
    return central_market_history_row_from_ohlcv(
        provider=provider,
        source_id=f"unit_{provider}",
        source_access_mode="zero_cost_public_api",
        normalized_symbol=symbol,
        venue_symbol=venue_symbol,
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        timeframe="1h",
        open=close,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=volume,
        provenance_refs=(f"unit-{provider}-candles",),
    )


def _sources(*providers: str) -> tuple[CentralMarketHistorySourceMetadata, ...]:
    return tuple(
        CentralMarketHistorySourceMetadata(
            provider=provider,
            source_id=f"unit_{provider}",
            source_access_mode="zero_cost_public_api",
            source_ref=f"unit-{provider}",
            official_public_source=True,
        )
        for provider in providers
    )
