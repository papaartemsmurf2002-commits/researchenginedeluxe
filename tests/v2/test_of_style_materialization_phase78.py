import csv
import io
import json
import zipfile
from pathlib import Path

import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.config.schemas import RESEARCH_BOUNDARY
from tradingbotsuite.v2.data_sources.of_style_materialization import (
    OF_STYLE_FAMILIES,
    OFStyleMaterializationConfig,
    materialize_of_style_archive,
    materialize_of_style_source,
    of_style_materialization_report_id_for,
)


def test_materializes_agg_trades_orderflow_rows(tmp_path):
    archive_root = tmp_path / "archive"
    output_root = tmp_path / "out"
    path = _write_source(
        archive_root,
        family="aggTrades",
        venue_symbol="BTCUSDT",
        header=("agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"),
        rows=(
            ("1", "10", "2", "1", "1", "1704067200000", "false"),
            ("2", "11", "1", "2", "2", "1704067201000", "true"),
        ),
    )

    result = materialize_of_style_source(path, archive_root=archive_root, output_root=output_root)

    assert result.status == "materialized"
    assert result.family == "aggTrades"
    assert result.feature_family == "orderflow"
    assert result.input_row_count == 2
    assert result.feature_row_count == 1
    rows = _read_jsonl(output_root / result.output_ref)
    assert rows[0]["trade_count"] == 2
    assert rows[0]["total_volume"] == 3.0
    assert rows[0]["total_quote_volume"] == 31.0
    assert rows[0]["buy_volume"] == 2.0
    assert rows[0]["sell_volume"] == 1.0
    assert rows[0]["trade_imbalance"] == 0.333333333333
    assert rows[0]["vwap"] == 10.333333333333
    assert rows[0]["research_only"] is True
    assert rows[0]["promotion_ready"] is False
    assert result.output_format == "jsonl"
    assert result.output_part_refs == ()
    assert (output_root / result.output_ref).with_name(Path(result.output_ref).name + ".sha256").exists()


def test_materializes_parquet_part_index_when_requested(tmp_path):
    archive_root = tmp_path / "archive"
    output_root = tmp_path / "out"
    path = _write_source(
        archive_root,
        family="aggTrades",
        venue_symbol="BTCUSDT",
        header=("agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"),
        rows=(
            ("1", "10", "2", "1", "1", "1704067200000", "false"),
            ("2", "11", "1", "2", "2", "1704067260000", "true"),
        ),
    )

    result = materialize_of_style_source(
        path,
        archive_root=archive_root,
        output_root=output_root,
        output_format="parquet_parts",
        output_chunk_row_limit=1,
    )

    assert result.status == "materialized"
    assert result.output_format == "parquet_parts"
    assert result.output_ref.endswith(".parts/index.json")
    assert result.output_part_count == 2
    assert len(result.output_part_refs) == 2
    index_path = output_root / result.output_ref
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["manifest_type"] == "of_style_feature_part_index_v1"
    assert index["part_count"] == 2
    assert index["row_manifest_hash"] == result.row_manifest_hash
    assert index["part_manifest_hash"] == result.output_part_manifest_hash
    assert index["research_only"] is True
    assert index["promotion_ready"] is False
    first_part_rows = pq.read_table(output_root / result.output_part_refs[0]).to_pylist()
    second_part_rows = pq.read_table(output_root / result.output_part_refs[1]).to_pylist()
    assert first_part_rows[0]["bucket_start_ms"] == 1704067200000
    assert second_part_rows[0]["bucket_start_ms"] == 1704067260000
    assert index_path.with_name("index.json.sha256").exists()
    assert (output_root / result.output_part_refs[0]).with_name("part-000000.parquet.sha256").exists()


def test_materializes_all_of_style_family_shapes_for_archive_report(tmp_path):
    archive_root = tmp_path / "archive"
    output_root = tmp_path / "out"
    sources = [
        _write_source(
            archive_root,
            family="aggTrades",
            venue_symbol="BTCUSDT",
            header=("agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"),
            rows=(("1", "10", "2", "1", "1", "1704067200000", "false"),),
        ),
        _write_source(
            archive_root,
            family="trades",
            venue_symbol="BTCUSDT",
            header=("id", "price", "qty", "quote_qty", "time", "is_buyer_maker"),
            rows=(("1", "10", "2", "20", "1704067200000", "true"),),
        ),
        _write_source(
            archive_root,
            family="bookTicker",
            venue_symbol="BTCUSDT",
            header=(
                "update_id",
                "best_bid_price",
                "best_bid_qty",
                "best_ask_price",
                "best_ask_qty",
                "transaction_time",
                "event_time",
            ),
            rows=(("1", "9.9", "5", "10.1", "3", "1704067200000", "1704067200100"),),
        ),
        _write_source(
            archive_root,
            family="bookDepth",
            venue_symbol="BTCUSDT",
            header=("timestamp", "percentage", "depth", "notional"),
            rows=(
                ("2024-01-01 00:00:10", "-1", "5", "50"),
                ("2024-01-01 00:00:10", "1", "3", "30"),
            ),
        ),
        _write_source(
            archive_root,
            family="metrics",
            venue_symbol="BTCUSDT",
            header=(
                "create_time",
                "symbol",
                "sum_open_interest",
                "sum_open_interest_value",
                "count_toptrader_long_short_ratio",
                "sum_toptrader_long_short_ratio",
                "count_long_short_ratio",
                "sum_taker_long_short_vol_ratio",
            ),
            rows=(("2024-01-01 00:00:00", "BTCUSDT", "1", "2", "3", "4", "5", "6"),),
        ),
        _write_kline_source(archive_root, family="klines"),
        _write_kline_source(archive_root, family="markPriceKlines"),
        _write_kline_source(archive_root, family="indexPriceKlines"),
        _write_kline_source(archive_root, family="premiumIndexKlines"),
    ]
    report_path = archive_root / "manifests" / "wpr106-549-heavy-raw-archive-validation-report.json"
    _write_validation_report(report_path, source_count=len(sources))

    report = materialize_of_style_archive(
        OFStyleMaterializationConfig(
            archive_root=archive_root,
            validation_report_path=report_path,
            output_root=output_root,
            families=OF_STYLE_FAMILIES,
            symbols=("BTC",),
            intervals=("1m",),
            max_sources_per_symbol_per_family=1,
        )
    )

    assert report.final_audit_data_ready is True
    assert report.blocker_reasons == ()
    assert report.materialized_source_count == len(sources)
    assert report.blocked_source_count == 0
    assert report.archive_source_count == len(sources)
    assert report.feature_row_count >= len(sources)
    assert report.materialization_report_id == of_style_materialization_report_id_for(report)
    assert set(report.family_counts) == set(OF_STYLE_FAMILIES)
    assert (output_root / "manifests" / "wpr106-552-of-style-feature-materialization-report.json").exists()
    assert any(row.feature_family == "bbo_spread" for row in report.source_results)
    assert any(row.feature_family == "l2_depth" for row in report.source_results)
    assert any(row.feature_family == "derivatives_context" for row in report.source_results)
    assert any(row.feature_family == "kline_context" for row in report.source_results)
    assert report.research_only is True
    assert report.promotion_ready is False


def _write_kline_source(archive_root: Path, *, family: str) -> Path:
    return _write_source(
        archive_root,
        family=family,
        venue_symbol="BTCUSDT",
        interval="1m",
        header=(
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
        rows=(("1704067200000", "10", "11", "9", "10.5", "2", "1704067259999", "20", "4", "1", "10", "0"),),
    )


def _write_source(
    archive_root: Path,
    *,
    family: str,
    venue_symbol: str,
    header: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
    interval: str | None = None,
) -> Path:
    day = "2024-01-01"
    parent = archive_root / "data" / "futures" / "um" / "daily" / family / venue_symbol
    filename = f"{venue_symbol}-{family}-{day}.zip"
    if interval is not None:
        parent = parent / interval
        filename = f"{venue_symbol}-{interval}-{day}.zip"
    parent.mkdir(parents=True, exist_ok=True)
    path = parent / filename
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename.replace(".zip", ".csv"), csv_buffer.getvalue())
    raw_ref = path.relative_to(archive_root).as_posix()
    metadata = {
        "manifest_type": "wpr106_549_heavy_raw_source_metadata",
        "family": family,
        "dataset": f"{family}:{interval}" if interval else family,
        "symbol": venue_symbol.removesuffix("USDT"),
        "venue_symbol": venue_symbol,
        "interval": interval,
        "day": day,
        "raw_ref": raw_ref,
        "raw_sha256": file_sha256(path),
        "checksum_sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        **dict(RESEARCH_BOUNDARY),
    }
    path.with_name(path.name + ".metadata.json").write_text(
        json.dumps(metadata, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    path.with_name(path.name + ".sha256").write_text(file_sha256(path) + "\n", encoding="utf-8")
    return path


def _write_validation_report(path: Path, *, source_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "report_type": "wpr106_549_heavy_raw_archive_validation",
        "archive_root": str(path.parents[1]),
        "families": list(OF_STYLE_FAMILIES),
        "source_count": source_count,
        "complete_source_count": source_count,
        "missing_source_count": 0,
        "invalid_source_count": 0,
        "partial_file_count": 0,
        **dict(RESEARCH_BOUNDARY),
    }
    path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
