from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from tradingbotsuite.v2.data_sources import (
    BinanceVisionAvailabilityRow,
    BinanceVisionAvailabilityStatus,
    BinanceVisionChecksumStatus,
    BinanceVisionDownloadStatus,
    BinanceVisionGetResult,
    CostClass,
    download_binance_vision_availability_row_to_cache,
)


DAY = date(2024, 1, 1)
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
SYMBOL_MAP_SNAPSHOT_ID = "a" * 64


def test_binance_vision_downloader_writes_cache_manifest_and_reuses_cache(tmp_path) -> None:
    zip_bytes = b"binance-vision-daily-zip"
    expected_sha = hashlib.sha256(zip_bytes).hexdigest()
    checksum_bytes = f"{expected_sha}  BTCUSDT-1m-2024-01-01.zip\n".encode("utf-8")
    calls: list[str] = []

    def fake_get(url: str) -> BinanceVisionGetResult:
        calls.append(url)
        if url.endswith(".CHECKSUM"):
            return BinanceVisionGetResult(status_code=200, content=checksum_bytes)
        return BinanceVisionGetResult(status_code=200, content=zip_bytes)

    availability = _availability_row(checksum_status=BinanceVisionChecksumStatus.AVAILABLE)
    first = download_binance_vision_availability_row_to_cache(
        archive_root=tmp_path / "archive",
        availability_row=availability,
        get=fake_get,
    )

    assert first.status == BinanceVisionDownloadStatus.DOWNLOADED
    assert first.cache_hit is False
    assert first.zip_sha256 == expected_sha
    assert first.byte_count == len(zip_bytes)
    assert first.checksum_verified is True
    assert first.checksum_expected_sha256 == expected_sha
    assert first.zip_cache_ref is not None
    assert first.checksum_cache_ref is not None
    assert (tmp_path / "archive" / first.zip_cache_ref).read_bytes() == zip_bytes
    assert (tmp_path / "archive" / first.checksum_cache_ref).read_bytes() == checksum_bytes
    manifest = json.loads((tmp_path / "archive" / first.download_manifest_ref).read_text(encoding="utf-8"))
    assert manifest["download_id"] == first.download_id
    assert manifest["research_only"] is True
    assert manifest["candidate_pack_eligible"] is False

    def forbidden_get(url: str) -> BinanceVisionGetResult:
        raise AssertionError(f"unexpected network call: {url}")

    second = download_binance_vision_availability_row_to_cache(
        archive_root=tmp_path / "archive",
        availability_row=availability,
        get=forbidden_get,
    )

    assert calls == [availability.zip_url, availability.checksum_url]
    assert second.status == BinanceVisionDownloadStatus.CACHE_HIT
    assert second.cache_hit is True
    assert second.download_id == first.download_id
    assert second.zip_sha256 == first.zip_sha256


def test_binance_vision_downloader_blocks_non_available_rows_without_get(tmp_path) -> None:
    def forbidden_get(url: str) -> BinanceVisionGetResult:
        raise AssertionError(f"unexpected network call: {url}")

    result = download_binance_vision_availability_row_to_cache(
        archive_root=tmp_path / "archive",
        availability_row=_availability_row(
            zip_status=BinanceVisionAvailabilityStatus.BLOCKED_MAPPING,
            checksum_status=BinanceVisionChecksumStatus.NOT_CHECKED,
            binance_symbol=None,
            blocked_reasons=("binance_usdm mapping is missing",),
        ),
        get=forbidden_get,
    )

    assert result.status == BinanceVisionDownloadStatus.BLOCKED
    assert result.zip_cache_ref is None
    assert "zip_status_blocked_mapping" in result.blocked_reasons
    assert "binance_usdm mapping is missing" in result.blocked_reasons
    assert (tmp_path / "archive" / result.download_manifest_ref).exists()


def test_binance_vision_downloader_fails_closed_on_checksum_mismatch(tmp_path) -> None:
    zip_bytes = b"binance-vision-daily-zip"

    def fake_get(url: str) -> BinanceVisionGetResult:
        if url.endswith(".CHECKSUM"):
            return BinanceVisionGetResult(status_code=200, content=b"0" * 64)
        return BinanceVisionGetResult(status_code=200, content=zip_bytes)

    result = download_binance_vision_availability_row_to_cache(
        archive_root=tmp_path / "archive",
        availability_row=_availability_row(checksum_status=BinanceVisionChecksumStatus.AVAILABLE),
        get=fake_get,
    )

    assert result.status == BinanceVisionDownloadStatus.CHECKSUM_MISMATCH
    assert result.checksum_verified is False
    assert result.blocked_reasons == ("checksum_mismatch",)
    assert result.zip_cache_ref is not None
    assert result.checksum_cache_ref is not None
    assert Path(tmp_path / "archive" / result.zip_cache_ref).exists()


def _availability_row(
    *,
    zip_status: BinanceVisionAvailabilityStatus = BinanceVisionAvailabilityStatus.AVAILABLE,
    checksum_status: BinanceVisionChecksumStatus = BinanceVisionChecksumStatus.MISSING,
    binance_symbol: str | None = "BTCUSDT",
    blocked_reasons: tuple[str, ...] = (),
) -> BinanceVisionAvailabilityRow:
    zip_url = None
    checksum_url = None
    if zip_status == BinanceVisionAvailabilityStatus.AVAILABLE:
        assert binance_symbol is not None
        zip_url = (
            "https://data.binance.vision/data/futures/um/daily/klines/"
            f"{binance_symbol}/1m/{binance_symbol}-1m-2024-01-01.zip"
        )
        checksum_url = f"{zip_url}.CHECKSUM"
    return BinanceVisionAvailabilityRow(
        source_id="binance_vision_usdm_klines",
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_ref=SYMBOL_MAP_REF,
        symbol_map_snapshot_id=SYMBOL_MAP_SNAPSHOT_ID,
        hyperliquid_coin="BTC",
        venue_key="binance_usdm",
        binance_symbol=binance_symbol,
        probe_date=DAY,
        market_scope="futures_um",
        market_type="perpetual",
        family="klines",
        data_family="candles_1m",
        interval="1m",
        zip_url=zip_url,
        checksum_url=checksum_url,
        zip_status=zip_status,
        checksum_status=checksum_status,
        http_status_code=200 if zip_status == BinanceVisionAvailabilityStatus.AVAILABLE else None,
        checksum_http_status_code=200 if checksum_status == BinanceVisionChecksumStatus.AVAILABLE else None,
        source_cost_class=CostClass.ZERO_COST_PUBLIC,
        blocked_reasons=blocked_reasons,
    )
