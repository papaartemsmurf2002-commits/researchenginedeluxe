from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import date

import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.data_sources import (
    BinanceVisionRowType,
    ingest_binance_vision_zip_bytes_to_archive,
)


def test_ingest_binance_vision_kline_zip_writes_raw_bronze_and_silver(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    csv_payload = "\n".join(
        [
            "open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,"
            "taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore",
            "0,100,101,99,100.5,1,59999,100,10,0.5,50,0",
            "60000,100.5,102,100,101.0,2,119999,202,20,1.0,101,0",
        ]
    )
    zip_bytes = _zip_bytes("BTCUSDT-1m-2024-01-01.csv", csv_payload)
    sha256 = hashlib.sha256(zip_bytes).hexdigest()

    result = ingest_binance_vision_zip_bytes_to_archive(
        archive_root=archive_root,
        source_id="binance_vision_usdm_klines",
        symbol="BTCUSDT",
        archive_date=date(2024, 1, 1),
        zip_bytes=zip_bytes,
        checksum_payload=f"{sha256}  BTCUSDT-1m-2024-01-01.zip",
    )

    assert result.row_type == BinanceVisionRowType.KLINE
    assert result.raw_file_id
    assert result.bronze_file_id
    assert result.silver_file_id
    assert result.microstructure_quality_report_id is None
    assert result.checksum_verified is True
    assert result.accepted_research_evidence is False
    assert result.native_to_hyperliquid is False

    parser_manifest = json.loads((archive_root / result.parser_manifest_ref).read_text(encoding="utf-8"))
    assert parser_manifest["row_count"] == 2
    assert parser_manifest["checksum_verified"] is True

    store = ArchiveManifestStore(ArchiveLayout(archive_root))
    file_rows = {row.file_id: row for row in store.load_file_manifest()}
    assert file_rows[result.raw_file_id].layer.value == "raw"
    assert file_rows[result.bronze_file_id].layer.value == "bronze"
    assert file_rows[result.silver_file_id].layer.value == "silver"

    silver_path = ArchiveLayout(archive_root).resolve(file_rows[result.silver_file_id].path)
    silver_rows = pq.ParquetFile(silver_path).read().to_pylist()
    assert [row["close"] for row in silver_rows] == [100.5, 101.0]
    assert all(row["research_only"] is True for row in silver_rows)


def test_ingest_binance_vision_agg_trades_zip_writes_microstructure_raw_capture(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    csv_payload = "\n".join(
        [
            "7,100.0,0.10,70,71,3000,false,true",
            "6,99.5,0.20,68,69,1000,true,true",
        ]
    )
    zip_bytes = _zip_bytes("BTCUSDT-aggTrades-2024-01-01.csv", csv_payload)

    result = ingest_binance_vision_zip_bytes_to_archive(
        archive_root=archive_root,
        source_id="binance_vision_usdm_agg_trades",
        symbol="BTCUSDT",
        archive_date=date(2024, 1, 1),
        zip_bytes=zip_bytes,
        storage_budget_bytes=1_000_000,
    )

    assert result.row_type == BinanceVisionRowType.AGG_TRADE
    assert result.raw_file_id
    assert result.bronze_file_id is None
    assert result.silver_file_id is None
    assert result.microstructure_quality_report_id
    assert result.storage_report_id
    assert result.row_count == 2

    quality_path = (
        archive_root
        / "manifests"
        / "microstructure_quality_reports"
        / f"{result.microstructure_quality_report_id}.json"
    )
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    assert quality["venue"] == "binance"
    assert quality["datatype"] == "trades"
    assert quality["row_count"] == 2
    assert quality["research_only"] is True

    store = ArchiveManifestStore(ArchiveLayout(archive_root))
    raw_row = next(row for row in store.load_file_manifest() if row.file_id == result.raw_file_id)
    assert raw_row.layer.value == "raw"
    assert raw_row.datatype == "trades"
    assert raw_row.instrument_id == "binance:perp:BTCUSDT"


def _zip_bytes(member_name: str, payload: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member_name, payload)
    return buffer.getvalue()
