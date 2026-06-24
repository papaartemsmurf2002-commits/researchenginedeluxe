from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, date, datetime

from tradingbotsuite.v2.data_sources import (
    BinanceVisionAvailabilityRow,
    BinanceVisionAvailabilityStatus,
    BinanceVisionBackfillStatus,
    BinanceVisionChecksumStatus,
    BinanceVisionGetResult,
    CostClass,
    run_binance_vision_daily_backfill,
)


DAY = date(2024, 1, 1)
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
SYMBOL_MAP_SNAPSHOT_ID = "a" * 64
UNIVERSE_SNAPSHOT_REF = "manifests/universe/hyperliquid_asof_2024-01-01.json"
ARCHIVE_SNAPSHOT_REF = "manifests/archive_snapshots/binance_vision_snapshot.json"


def test_binance_vision_daily_backfill_writes_accepted_kline_coverage(tmp_path) -> None:
    kline_zip = _full_day_kline_zip()
    trade_zip = _full_day_trade_zip()

    def fake_get(url: str) -> BinanceVisionGetResult:
        if "daily/trades" in url:
            return BinanceVisionGetResult(status_code=200, content=trade_zip)
        return BinanceVisionGetResult(status_code=200, content=kline_zip)

    result = run_binance_vision_daily_backfill(
        archive_root=tmp_path / "archive",
        availability_row=_availability_row(
            source_id="binance_vision_usdm_klines",
            family="klines",
            data_family="candles_1m",
            interval="1m",
        ),
        comparison_availability_row=_availability_row(
            source_id="binance_vision_usdm_trades",
            family="trades",
            data_family="trades",
            interval=None,
        ),
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
        archive_snapshot_ref=ARCHIVE_SNAPSHOT_REF,
        get=fake_get,
    )

    assert result.status == BinanceVisionBackfillStatus.COMPLETED
    assert result.accepted_for_research_reporting is True
    assert result.blocker_reasons == ()
    assert result.target_ingest_id is not None
    assert result.comparison_report_id is not None
    coverage_path = tmp_path / "archive" / result.coverage_report_ref
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert coverage["coverage_report_id"] == result.coverage_report_id
    assert coverage["accepted_for_research_reporting"] is True
    assert coverage["coverage_ratio"] == 1.0
    assert coverage["labels"] == ["external_comparison"]


def test_binance_vision_daily_backfill_writes_blocked_coverage_for_missing_row(tmp_path) -> None:
    def forbidden_get(url: str) -> BinanceVisionGetResult:
        raise AssertionError(f"unexpected network call: {url}")

    result = run_binance_vision_daily_backfill(
        archive_root=tmp_path / "archive",
        availability_row=_availability_row(
            source_id="binance_vision_usdm_klines",
            family="klines",
            data_family="candles_1m",
            interval="1m",
            zip_status=BinanceVisionAvailabilityStatus.BLOCKED_MAPPING,
            binance_symbol=None,
            blocked_reasons=("binance_usdm mapping is missing",),
        ),
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
        get=forbidden_get,
    )

    assert result.status == BinanceVisionBackfillStatus.BLOCKED
    assert result.accepted_for_research_reporting is False
    assert "binance_usdm mapping is missing" in result.blocker_reasons
    coverage = json.loads((tmp_path / "archive" / result.coverage_report_ref).read_text(encoding="utf-8"))
    assert coverage["accepted_for_research_reporting"] is False
    assert "zip_status_blocked_mapping" in coverage["reason"]


def test_binance_vision_daily_backfill_propagates_checksum_mismatch_to_coverage(tmp_path) -> None:
    def fake_get(url: str) -> BinanceVisionGetResult:
        if url.endswith(".CHECKSUM"):
            return BinanceVisionGetResult(status_code=200, content=b"0" * 64)
        return BinanceVisionGetResult(status_code=200, content=_full_day_kline_zip())

    result = run_binance_vision_daily_backfill(
        archive_root=tmp_path / "archive",
        availability_row=_availability_row(
            source_id="binance_vision_usdm_klines",
            family="klines",
            data_family="candles_1m",
            interval="1m",
            checksum_status=BinanceVisionChecksumStatus.AVAILABLE,
        ),
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
        archive_snapshot_ref=ARCHIVE_SNAPSHOT_REF,
        get=fake_get,
    )

    assert result.status == BinanceVisionBackfillStatus.BLOCKED
    assert "checksum_mismatch" in result.blocker_reasons
    coverage = json.loads((tmp_path / "archive" / result.coverage_report_ref).read_text(encoding="utf-8"))
    assert "checksum_mismatch" in coverage["reason"]
    assert "download_status_checksum_mismatch" in coverage["reason"]


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
