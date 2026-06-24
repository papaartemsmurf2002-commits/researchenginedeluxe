from __future__ import annotations

import io
import zipfile

from tradingbotsuite.v2.data_sources import (
    compare_binance_vision_reconstructed_bars,
    parse_binance_vision_zip_bytes,
)


def test_reconstructed_trade_bars_pass_when_ohlcv_matches_klines() -> None:
    trades = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_trades",
        symbol="BTCUSDT",
        zip_bytes=_zip_bytes(
            "BTCUSDT-trades-2024-01-01.csv",
            "\n".join(
                [
                    "trade_id,price,quantity,quote_quantity,time,is_buyer_maker,is_best_match",
                    "1,100.0,0.5,50.0,1000,false,true",
                    "2,101.0,1.5,151.5,59000,true,true",
                ]
            ),
        ),
    )
    klines = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_klines",
        symbol="BTCUSDT",
        zip_bytes=_zip_bytes(
            "BTCUSDT-1m-2024-01-01.csv",
            "\n".join(
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
                    "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    "0,100,101,100,101,2.0,59999,201,2,1.5,151.5,0",
                ]
            ),
        ),
    )

    report = compare_binance_vision_reconstructed_bars(
        source_result=trades,
        kline_result=klines,
    )

    assert report.passed is True
    assert report.blocker_reasons == ()
    assert report.passed_bucket_count == 1
    assert report.rows[0].reconstructed_event_count == 2
    assert report.rows[0].close_abs_diff == 0.0
    assert report.research_only is True
    assert report.candidate_pack_eligible is False


def test_reconstructed_bar_report_fails_missing_bucket() -> None:
    trades = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_trades",
        symbol="BTCUSDT",
        zip_bytes=_zip_bytes(
            "BTCUSDT-trades-2024-01-01.csv",
            "trade_id,price,quantity,quote_quantity,time,is_buyer_maker,is_best_match\n"
            "1,100.0,1.0,100.0,1000,false,true",
        ),
    )
    klines = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_klines",
        symbol="BTCUSDT",
        zip_bytes=_zip_bytes(
            "BTCUSDT-1m-2024-01-01.csv",
            "\n".join(
                [
                    "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
                    "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
                    "0,100,100,100,100,1,59999,100,1,1,100,0",
                    "60000,101,101,101,101,1,119999,101,1,1,101,0",
                ]
            ),
        ),
    )

    report = compare_binance_vision_reconstructed_bars(
        source_result=trades,
        kline_result=klines,
    )

    assert report.passed is False
    assert report.missing_reconstructed_count == 1
    assert report.blocker_reasons == ("missing_reconstructed_buckets",)
    assert report.rows[1].status == "missing_reconstructed"


def test_reconstructed_bar_report_fails_ohlcv_tolerance_mismatch() -> None:
    agg_trades = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_agg_trades",
        symbol="BTCUSDT",
        zip_bytes=_zip_bytes(
            "BTCUSDT-aggTrades-2024-01-01.csv",
            "aggregate_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker,is_best_match\n"
            "1,100.0,1.0,1,1,1000,false,true\n"
            "2,101.0,1.0,2,2,59000,true,true",
        ),
    )
    klines = parse_binance_vision_zip_bytes(
        source_id="binance_vision_usdm_klines",
        symbol="BTCUSDT",
        zip_bytes=_zip_bytes(
            "BTCUSDT-1m-2024-01-01.csv",
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
            "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore\n"
            "0,100,102,100,102,2,59999,202,2,1,101,0",
        ),
    )

    report = compare_binance_vision_reconstructed_bars(
        source_result=agg_trades,
        kline_result=klines,
    )

    assert report.passed is False
    assert report.failed_bucket_count == 1
    assert report.blocker_reasons == ("ohlcv_tolerance_failed",)
    assert report.rows[0].status == "failed"
    assert "close_tolerance_exceeded" in report.rows[0].reasons


def _zip_bytes(member_name: str, payload: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member_name, payload)
    return buffer.getvalue()
