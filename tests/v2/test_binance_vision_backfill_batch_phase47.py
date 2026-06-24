from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, date, datetime

from tradingbotsuite.v2.data_sources import (
    BinanceVisionAvailabilityManifest,
    BinanceVisionAvailabilityRow,
    BinanceVisionAvailabilityStatus,
    BinanceVisionBackfillStatus,
    BinanceVisionChecksumStatus,
    BinanceVisionGetResult,
    CostClass,
    run_binance_vision_backfill_batch,
)
from tradingbotsuite.v2.data_sources.binance_vision import (
    binance_vision_availability_manifest_id_for,
    binance_vision_availability_rows_hash,
)


DAY = date(2024, 1, 1)
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
SYMBOL_MAP_SNAPSHOT_ID = "a" * 64
UNIVERSE_SNAPSHOT_REF = "manifests/universe/hyperliquid_asof_2024-01-01.json"
ARCHIVE_SNAPSHOT_REF = "manifests/archive_snapshots/binance_vision_snapshot.json"


def test_binance_vision_backfill_batch_runs_matching_rows_and_writes_manifest(tmp_path) -> None:
    kline_zip = _full_day_kline_zip()
    trade_zip = _full_day_trade_zip()

    def fake_get(url: str) -> BinanceVisionGetResult:
        if "daily/trades" in url:
            return BinanceVisionGetResult(status_code=200, content=trade_zip)
        return BinanceVisionGetResult(status_code=200, content=kline_zip)

    manifest = _manifest(
        (
            _availability_row(
                source_id="binance_vision_usdm_klines",
                family="klines",
                data_family="candles_1m",
                interval="1m",
            ),
            _availability_row(
                source_id="binance_vision_usdm_trades",
                family="trades",
                data_family="trades",
                interval=None,
            ),
        )
    )

    result = run_binance_vision_backfill_batch(
        archive_root=tmp_path / "archive",
        availability_manifest=manifest,
        target_source_id="binance_vision_usdm_klines",
        comparison_source_id="binance_vision_usdm_trades",
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
        archive_snapshot_ref=ARCHIVE_SNAPSHOT_REF,
        get=fake_get,
        max_rows=10,
    )

    assert result.selected_count == 1
    assert result.completed_count == 1
    assert result.blocked_count == 0
    assert result.accepted_count == 1
    assert result.daily_results[0].status == BinanceVisionBackfillStatus.COMPLETED
    batch_manifest = json.loads((tmp_path / "archive" / result.batch_manifest_ref).read_text(encoding="utf-8"))
    assert batch_manifest["batch_id"] == result.batch_id
    assert batch_manifest["daily_result_ids"] == list(result.daily_result_ids)
    assert batch_manifest["research_only"] is True


def test_binance_vision_backfill_batch_preserves_blocked_daily_results(tmp_path) -> None:
    def forbidden_get(url: str) -> BinanceVisionGetResult:
        raise AssertionError(f"unexpected network call: {url}")

    manifest = _manifest(
        (
            _availability_row(
                source_id="binance_vision_usdm_klines",
                family="klines",
                data_family="candles_1m",
                interval="1m",
                zip_status=BinanceVisionAvailabilityStatus.BLOCKED_MAPPING,
                binance_symbol=None,
                blocked_reasons=("binance_usdm mapping is missing",),
            ),
        )
    )

    result = run_binance_vision_backfill_batch(
        archive_root=tmp_path / "archive",
        availability_manifest=manifest,
        target_source_id="binance_vision_usdm_klines",
        comparison_source_id="binance_vision_usdm_trades",
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
        get=forbidden_get,
    )

    assert result.selected_count == 1
    assert result.completed_count == 0
    assert result.blocked_count == 1
    assert result.accepted_count == 0
    assert "binance_usdm mapping is missing" in result.blocker_reasons
    assert result.daily_results[0].coverage_report_ref.startswith("manifests/coverage_reports/")
    assert (tmp_path / "archive" / result.batch_manifest_ref).exists()


def _manifest(rows: tuple[BinanceVisionAvailabilityRow, ...]) -> BinanceVisionAvailabilityManifest:
    row_hash = binance_vision_availability_rows_hash(rows)
    source_ids = tuple(sorted({row.source_id for row in rows}))
    manifest_id = binance_vision_availability_manifest_id_for(
        start_date=min(row.probe_date for row in rows),
        end_date=max(row.probe_date for row in rows),
        source_ids=source_ids,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_snapshot_id=SYMBOL_MAP_SNAPSHOT_ID,
        row_manifest_hash=row_hash,
    )
    return BinanceVisionAvailabilityManifest(
        availability_manifest_id=manifest_id,
        start_date=min(row.probe_date for row in rows),
        end_date=max(row.probe_date for row in rows),
        source_ids=source_ids,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        symbol_map_snapshot_id=SYMBOL_MAP_SNAPSHOT_ID,
        rows=rows,
        row_count=len(rows),
        available_count=sum(1 for row in rows if row.zip_status == BinanceVisionAvailabilityStatus.AVAILABLE),
        missing_count=sum(1 for row in rows if row.zip_status == BinanceVisionAvailabilityStatus.MISSING),
        blocked_mapping_count=sum(
            1 for row in rows if row.zip_status == BinanceVisionAvailabilityStatus.BLOCKED_MAPPING
        ),
        probe_error_count=sum(1 for row in rows if row.zip_status == BinanceVisionAvailabilityStatus.PROBE_ERROR),
        checksum_available_count=sum(
            1 for row in rows if row.checksum_status == BinanceVisionChecksumStatus.AVAILABLE
        ),
        checksum_missing_count=sum(
            1 for row in rows if row.checksum_status == BinanceVisionChecksumStatus.MISSING
        ),
        row_manifest_hash=row_hash,
    )


def _availability_row(
    *,
    source_id: str,
    family: str,
    data_family: str,
    interval: str | None,
    zip_status: BinanceVisionAvailabilityStatus = BinanceVisionAvailabilityStatus.AVAILABLE,
    checksum_status: BinanceVisionChecksumStatus = BinanceVisionChecksumStatus.MISSING,
    binance_symbol: str | None = "BTCUSDT",
    blocked_reasons: tuple[str, ...] = (),
) -> BinanceVisionAvailabilityRow:
    zip_url = None
    checksum_url = None
    if zip_status == BinanceVisionAvailabilityStatus.AVAILABLE:
        assert binance_symbol is not None
        if family == "trades":
            path = f"data/futures/um/daily/trades/{binance_symbol}/{binance_symbol}-trades-2024-01-01.zip"
        else:
            path = f"data/futures/um/daily/klines/{binance_symbol}/1m/{binance_symbol}-1m-2024-01-01.zip"
        zip_url = f"https://data.binance.vision/{path}"
        checksum_url = f"{zip_url}.CHECKSUM"
    return BinanceVisionAvailabilityRow(
        source_id=source_id,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        symbol_map_snapshot_id=SYMBOL_MAP_SNAPSHOT_ID,
        hyperliquid_coin="BTC",
        venue_key="binance_usdm",
        binance_symbol=binance_symbol,
        probe_date=DAY,
        market_scope="futures_um",
        market_type="perpetual",
        family=family,
        data_family=data_family,
        interval=interval,
        zip_url=zip_url,
        checksum_url=checksum_url,
        zip_status=zip_status,
        checksum_status=checksum_status,
        http_status_code=200 if zip_status == BinanceVisionAvailabilityStatus.AVAILABLE else None,
        checksum_http_status_code=200 if checksum_status == BinanceVisionChecksumStatus.AVAILABLE else None,
        source_cost_class=CostClass.ZERO_COST_PUBLIC,
        blocked_reasons=blocked_reasons,
    )


def _full_day_kline_zip() -> bytes:
    rows = [
        "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
        "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore"
    ]
    for index in range(1440):
        ts = _day_start_ms() + index * 60_000
        price = 100.0 + index / 10_000
        rows.append(
            f"{ts},{price:.4f},{price:.4f},{price:.4f},{price:.4f},1,"
            f"{ts + 59_999},{price:.4f},1,1,{price:.4f},0"
        )
    return _zip_bytes("BTCUSDT-1m-2024-01-01.csv", "\n".join(rows))


def _full_day_trade_zip() -> bytes:
    rows = ["trade_id,price,quantity,quote_quantity,time,is_buyer_maker,is_best_match"]
    for index in range(1440):
        ts = _day_start_ms() + index * 60_000 + 1_000
        price = 100.0 + index / 10_000
        rows.append(f"{index + 1},{price:.4f},1,{price:.4f},{ts},false,true")
    return _zip_bytes("BTCUSDT-trades-2024-01-01.csv", "\n".join(rows))


def _day_start_ms() -> int:
    return int(datetime(DAY.year, DAY.month, DAY.day, tzinfo=UTC).timestamp() * 1000)


def _zip_bytes(member_name: str, payload: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member_name, payload)
    return buffer.getvalue()
