from __future__ import annotations

import json

import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.raw_writer import read_jsonl_zstd
from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.data_sources.binance_derivatives import (
    BinanceDerivativesContextArchiveIngestResult,
    BinanceDerivativesContextArchiveIngestStatus,
    BinanceDerivativesContextGetResult,
    BinanceDerivativesContextPageStatus,
    fetch_binance_derivatives_context_pages,
    ingest_binance_derivatives_context_pages_to_archive,
)


def test_derivatives_context_page_result_writes_raw_and_silver_archive(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    page_result = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        start_time_ms=1000,
        end_time_ms=3000,
        limit=2,
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes(
                [
                    {
                        "symbol": "BTCUSDT",
                        "fundingRate": "0.0001",
                        "fundingTime": 1000,
                        "markPrice": "42000",
                    }
                ]
            ),
        ),
    )

    result = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=archive_root,
        page_result=page_result,
        instrument_id="binance:perp:BTCUSDT",
    )

    assert result.status == BinanceDerivativesContextArchiveIngestStatus.COMPLETED
    assert result.raw_row_count == 1
    assert result.silver_row_count == 1
    assert result.raw_file_id is not None
    assert result.silver_file_id is not None
    assert result.accepted_research_evidence is False
    assert result.native_to_hyperliquid is False
    assert result.promotion_ready is False

    layout = ArchiveLayout(archive_root)
    store = ArchiveManifestStore(layout)
    manifest_rows = {row.file_id: row for row in store.load_file_manifest()}
    raw_manifest = manifest_rows[result.raw_file_id]
    silver_manifest = manifest_rows[result.silver_file_id]
    assert raw_manifest.layer == ArchiveLayer.RAW
    assert silver_manifest.layer == ArchiveLayer.SILVER
    assert raw_manifest.datatype == "derivatives_context"
    assert silver_manifest.datatype == "derivatives_context"

    raw_rows = read_jsonl_zstd(
        layout.resolve(raw_manifest.path),
        uncompressed_size=raw_manifest.uncompressed_size_bytes or 0,
    )
    assert raw_rows[0]["page_result_id"] == page_result.page_result_id
    assert raw_rows[0]["numeric_fields"]["funding_rate"] == "0.0001"
    assert raw_rows[0]["accepted_research_evidence"] is False

    silver_rows = pq.ParquetFile(layout.resolve(silver_manifest.path)).read().to_pylist()
    assert silver_rows[0]["instrument_id"] == "binance:perp:BTCUSDT"
    assert silver_rows[0]["family"] == "funding_rate_history"
    assert json.loads(silver_rows[0]["numeric_fields_json"]) == {
        "funding_rate": "0.0001",
        "mark_price": "42000",
    }
    assert json.loads(silver_rows[0]["unit_fields_json"]) == {
        "funding_rate": "rate",
        "mark_price": "USDT",
    }
    assert silver_rows[0]["source_file_id"] == result.raw_file_id
    assert silver_rows[0]["source_layer"] == "raw"


def test_derivatives_context_archive_ingest_blocks_bad_page_results(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    blocked_page = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        max_pages=1,
        get=lambda url: BinanceDerivativesContextGetResult(status_code=200, content=b"[]"),
    )

    blocked = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=archive_root,
        page_result=blocked_page,
        instrument_id="binance:perp:BTCUSDT",
    )

    assert blocked.status == BinanceDerivativesContextArchiveIngestStatus.BLOCKED
    assert blocked.blocked_reasons == ("page_result_blocked",)
    assert blocked.raw_file_id is None
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()

    empty_page = fetch_binance_derivatives_context_pages(
        family="funding_rate_history",
        symbol="btcusdt",
        start_time_ms=1,
        end_time_ms=2,
        max_pages=1,
        get=lambda url: BinanceDerivativesContextGetResult(status_code=200, content=b"[]"),
    )
    assert empty_page.status == BinanceDerivativesContextPageStatus.COMPLETED

    empty = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=archive_root,
        page_result=empty_page,
        instrument_id="binance:perp:BTCUSDT",
    )
    assert empty.status == BinanceDerivativesContextArchiveIngestStatus.BLOCKED
    assert empty.blocked_reasons == ("no_rows_to_ingest",)
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_derivatives_context_archive_ingest_blocks_missing_timestamps(tmp_path) -> None:
    archive_root = tmp_path / "archive"
    page_result = fetch_binance_derivatives_context_pages(
        family="open_interest",
        symbol="btcusdt",
        get=lambda url: BinanceDerivativesContextGetResult(
            status_code=200,
            content=_json_bytes({"symbol": "BTCUSDT", "openInterest": "1.0"}),
        ),
    )

    result = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=archive_root,
        page_result=page_result,
        instrument_id="binance:perp:BTCUSDT",
    )

    assert result.status == BinanceDerivativesContextArchiveIngestStatus.BLOCKED
    assert result.blocked_reasons == ("missing_row_timestamp",)
    assert not (archive_root / "manifests" / "file_manifest.parquet").exists()


def test_derivatives_context_archive_ingest_identity_and_boundary_fail_closed(tmp_path) -> None:
    page_result = fetch_binance_derivatives_context_pages(
        family="open_interest",
        symbol="btcusdt",
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
    result = ingest_binance_derivatives_context_pages_to_archive(
        archive_root=tmp_path / "archive",
        page_result=page_result,
        instrument_id="binance:perp:BTCUSDT",
    )

    payload = result.model_dump()
    payload["ingest_id"] = "0" * 64
    with pytest.raises(ValidationError, match="ingest_id does not match"):
        BinanceDerivativesContextArchiveIngestResult(**payload)

    boundary_payload = result.model_dump()
    boundary_payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        BinanceDerivativesContextArchiveIngestResult(**boundary_payload)


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload).encode("utf-8")
