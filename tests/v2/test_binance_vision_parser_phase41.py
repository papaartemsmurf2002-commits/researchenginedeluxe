from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

from tradingbotsuite.v2.data_sources import (
    BinanceVisionRowType,
    parse_binance_vision_zip_bytes,
)


def test_parse_binance_vision_kline_zip_reports_gaps_duplicates_and_checksum() -> None:
    csv_payload = "\n".join(
        [
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
            "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
            "120000,102,103,101,102.5,2,179999,205,20,1,102,0",
            "0,100,101,99,100.5,1,59999,100,10,0.5,50,0",
            "120000,102,103,101,102.6,3,179999,307,30,1.5,154,0",
        ]
    )
    zip_bytes = _zip_bytes("BTCUSDT-1m-2024-01-01.csv", csv_payload)
    sha256 = hashlib.sha256(zip_bytes).hexdigest()

    result = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_klines",
        symbol="btcusdt",
        zip_bytes=zip_bytes,
        checksum_payload=f"{sha256}  BTCUSDT-1m-2024-01-01.zip\n",
    )

    assert result.binance_symbol == "BTCUSDT"
    assert result.row_type == BinanceVisionRowType.KLINE
    assert result.checksum_verified is True
    assert result.row_count == 3
    assert result.duplicate_count == 1
    assert result.duplicate_ids == (120_000,)
    assert result.gap_count == 1
    assert result.input_monotonic is False
    assert result.interval_alignment_status == "aligned"
    assert [row.event_time_ms for row in result.rows] == [0, 120_000, 120_000]
    assert result.rows[0].open == 100.0
    assert result.rows[0].trade_count == 10
    assert "input_timestamps_not_monotonic" in result.warnings
    assert result.research_only is True
    assert result.candidate_pack_eligible is False


def test_parse_binance_vision_agg_trades_headerless_zip_reports_duplicate_ids() -> None:
    csv_payload = "\n".join(
        [
            "7,100.0,0.10,70,71,3000,false,true",
            "6,99.5,0.20,68,69,1000,true,true",
            "7,100.1,0.15,72,73,2000,false,true",
        ]
    )
    zip_bytes = _zip_bytes("BTCUSDT-aggTrades-2024-01-01.csv", csv_payload)

    result = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_agg_trades",
        symbol="BTCUSDT",
        zip_bytes=zip_bytes,
    )

    assert result.row_type == BinanceVisionRowType.AGG_TRADE
    assert result.row_count == 3
    assert result.duplicate_ids == (7,)
    assert [row.event_time_ms for row in result.rows] == [1000, 2000, 3000]
    assert [row.aggregate_trade_id for row in result.rows] == [6, 7, 7]
    assert result.rows[0].buyer_maker is True
    assert result.interval_alignment_status == "not_applicable"


def test_parse_binance_vision_trades_headered_zip_preserves_native_trade_id() -> None:
    csv_payload = "\n".join(
        [
            "trade_id,price,quantity,quote_quantity,time,is_buyer_maker,is_best_match",
            "11,100.0,0.5,50.0,2000,false,true",
            "10,99.5,0.2,19.9,1000,true,true",
        ]
    )
    zip_bytes = _zip_bytes("BTCUSDT-trades-2024-01-01.csv", csv_payload)

    result = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_trades",
        symbol="BTCUSDT",
        zip_bytes=zip_bytes,
    )

    assert result.row_type == BinanceVisionRowType.TRADE
    assert result.duplicate_count == 0
    assert [row.trade_id for row in result.rows] == [10, 11]
    assert result.rows[0].price == 99.5
    assert result.rows[0].raw_fields["quote_quantity"] == "19.9"


def test_parse_binance_vision_zip_rejects_checksum_mismatch_before_csv_parse() -> None:
    zip_bytes = _zip_bytes("BTCUSDT-trades-2024-01-01.csv", "not,a,valid,trade,row")

    with pytest.raises(ValueError, match="checksum mismatch"):
        parse_binance_vision_zip_bytes(
            source_id="binance_vision_usdm_trades",
            symbol="BTCUSDT",
            zip_bytes=zip_bytes,
            checksum_payload="0" * 64,
        )


def test_parse_binance_vision_zip_requires_exactly_one_csv_member() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("one.csv", "1,2,3")
        archive.writestr("two.csv", "4,5,6")

    with pytest.raises(ValueError, match="exactly one CSV"):
        parse_binance_vision_zip_bytes(
            source_id="binance_vision_usdm_trades",
            symbol="BTCUSDT",
            zip_bytes=buffer.getvalue(),
        )


def _zip_bytes(member_name: str, payload: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member_name, payload)
    return buffer.getvalue()
