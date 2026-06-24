from __future__ import annotations

import io
import zipfile
from datetime import UTC, date, datetime

import pytest

from tradingbotsuite.v2.data_sources import (
    BinanceVisionAvailabilityRow,
    BinanceVisionAvailabilityStatus,
    BinanceVisionChecksumStatus,
    CostClass,
    build_binance_vision_data_family_coverage_report,
    compare_binance_vision_reconstructed_bars,
    ingest_binance_vision_zip_bytes_to_archive,
    parse_binance_vision_zip_bytes,
)


DAY = date(2024, 1, 1)
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
SYMBOL_MAP_SNAPSHOT_ID = "a" * 64
UNIVERSE_SNAPSHOT_REF = "manifests/universe/hyperliquid_asof_2024-01-01.json"
ARCHIVE_SNAPSHOT_REF = "manifests/archive_snapshots/binance_vision_snapshot.json"


def test_binance_vision_kline_coverage_accepts_full_archived_reconstructed_day(tmp_path) -> None:
    kline_zip = _full_day_kline_zip()
    trade_zip = _full_day_trade_zip()
    kline_parse = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_klines",
        symbol="BTCUSDT",
        zip_bytes=kline_zip,
    )
    trade_parse = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_trades",
        symbol="BTCUSDT",
        zip_bytes=trade_zip,
    )
    ingest = ingest_binance_vision_zip_bytes_to_archive(
        archive_root=tmp_path / "archive",
        source_id="binance_vision_usdm_klines",
        symbol="BTCUSDT",
        archive_date=DAY,
        zip_bytes=kline_zip,
    )
    comparison = compare_binance_vision_reconstructed_bars(
        source_result=trade_parse,
        kline_result=kline_parse,
    )

    report = build_binance_vision_data_family_coverage_report(
        availability_row=_availability_row(
            source_id="binance_vision_usdm_klines",
            family="klines",
            data_family="candles_1m",
            interval="1m",
        ),
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
        parse_result=kline_parse,
        ingest_result=ingest,
        comparison_report=comparison,
        archive_snapshot_ref=ARCHIVE_SNAPSHOT_REF,
    )
    repeat = build_binance_vision_data_family_coverage_report(
        availability_row=_availability_row(
            source_id="binance_vision_usdm_klines",
            family="klines",
            data_family="candles_1m",
            interval="1m",
        ),
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
        parse_result=kline_parse,
        ingest_result=ingest,
        comparison_report=comparison,
        archive_snapshot_ref=ARCHIVE_SNAPSHOT_REF,
    )

    assert report.coverage_report_id == repeat.coverage_report_id
    assert report.accepted_for_research_reporting is True
    assert report.symbol == "BTC"
    assert report.family == "candles_1m"
    assert report.venue == "binance"
    assert report.source_ids == ("binance_vision_usdm_klines",)
    assert report.observed_buckets == 1440
    assert report.expected_buckets.count == 1440
    assert report.coverage_ratio == 1.0
    assert report.missing_buckets == ()
    assert report.reason == ()
    assert report.research_only is True
    assert report.candidate_pack_eligible is False


def test_binance_vision_coverage_blocks_missing_mapping_without_parse_evidence() -> None:
    report = build_binance_vision_data_family_coverage_report(
        availability_row=_availability_row(
            source_id="binance_vision_usdm_trades",
            family="trades",
            data_family="trades",
            zip_status=BinanceVisionAvailabilityStatus.BLOCKED_MAPPING,
            blocked_reasons=("binance_usdm mapping is missing",),
            binance_symbol=None,
        ),
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
    )

    assert report.accepted_for_research_reporting is False
    assert report.expected_buckets.count == 1
    assert report.observed_buckets == 0
    assert report.coverage_ratio == 0.0
    assert report.missing_buckets == ("2024-01-01T00:00:00+00:00",)
    assert "binance_usdm mapping is missing" in report.reason
    assert "coverage_below_minimum" in report.reason


def test_binance_vision_kline_coverage_records_parser_ingest_and_comparison_blockers() -> None:
    partial_zip = _zip_bytes(
        "BTCUSDT-1m-2024-01-01.csv",
        "\n".join(
            [
                "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
                "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                f"{_day_start_ms()},100,100,100,100,1,{_day_start_ms() + 59_999},100,1,1,100,0",
                f"{_day_start_ms() + 120_000},101,101,101,101,1,{_day_start_ms() + 179_999},101,1,1,101,0",
            ]
        ),
    )
    parse_result = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_klines",
        symbol="BTCUSDT",
        zip_bytes=partial_zip,
    )

    report = build_binance_vision_data_family_coverage_report(
        availability_row=_availability_row(
            source_id="binance_vision_usdm_klines",
            family="klines",
            data_family="candles_1m",
            interval="1m",
        ),
        universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
        parse_result=parse_result,
    )

    assert report.accepted_for_research_reporting is False
    assert report.observed_buckets == 2
    assert report.coverage_ratio == pytest.approx(2 / 1440)
    assert "2024-01-01T00:01:00+00:00" in report.missing_buckets
    assert "ingest_result_missing" in report.reason
    assert "archive_snapshot_ref_missing" in report.reason
    assert "kline_gap_detected" in report.reason
    assert "reconstructed_bar_comparison_missing" in report.reason
    assert "parsed_rows_partial" in report.reason


def test_binance_vision_coverage_rejects_mismatched_parse_result() -> None:
    trade_parse = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_trades",
        symbol="BTCUSDT",
        zip_bytes=_zip_bytes(
            "BTCUSDT-trades-2024-01-01.csv",
            "trade_id,price,quantity,quote_quantity,time,is_buyer_maker,is_best_match\n"
            f"1,100.0,1.0,100.0,{_day_start_ms() + 1000},false,true",
        ),
    )

    with pytest.raises(ValueError, match="parse_result source_id does not match"):
        build_binance_vision_data_family_coverage_report(
            availability_row=_availability_row(
                source_id="binance_vision_usdm_klines",
                family="klines",
                data_family="candles_1m",
                interval="1m",
            ),
            universe_snapshot_ref=UNIVERSE_SNAPSHOT_REF,
            parse_result=trade_parse,
        )


def _availability_row(
    *,
    source_id: str,
    family: str,
    data_family: str,
    interval: str | None = None,
    zip_status: BinanceVisionAvailabilityStatus = BinanceVisionAvailabilityStatus.AVAILABLE,
    checksum_status: BinanceVisionChecksumStatus = BinanceVisionChecksumStatus.MISSING,
    blocked_reasons: tuple[str, ...] = (),
    binance_symbol: str | None = "BTCUSDT",
) -> BinanceVisionAvailabilityRow:
    zip_url = None
    checksum_url = None
    if zip_status == BinanceVisionAvailabilityStatus.AVAILABLE:
        assert binance_symbol is not None
        zip_url = f"https://data.binance.vision/{source_id}/{binance_symbol}/2024-01-01.zip"
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
