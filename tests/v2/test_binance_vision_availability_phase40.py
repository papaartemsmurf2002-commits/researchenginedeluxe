from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.binance_vision import (
    DEFAULT_BINANCE_VISION_SOURCE_IDS,
    BinanceVisionAvailabilityManifest,
    BinanceVisionAvailabilityStatus,
    BinanceVisionChecksumStatus,
    BinanceVisionHeadResult,
    binance_vision_daily_zip_url,
    write_binance_vision_availability_manifest,
)
from tradingbotsuite.v2.data_sources.schemas import (
    SourceRegistryEntry,
    SymbolMapSnapshot,
    symbol_map_rows_hash,
    symbol_map_snapshot_id_for,
)
from tradingbotsuite.v2.data_sources.symbol_resolver import (
    ProbeStatus,
    SymbolProbeResult,
    resolve_symbol_map_for_coin,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"
SOURCE_REGISTRY_REF = "manifests/source_registry/source_registry_test.json"
SYMBOL_MAP_REF = "manifests/symbol_maps/symbol_map_test.json"
UNIVERSE_SNAPSHOT_ID = "a" * 64
SOURCE_REGISTRY_SNAPSHOT_ID = "b" * 64


def test_binance_vision_daily_url_builders_match_roadmap_paths() -> None:
    day = date(2024, 1, 2)

    assert binance_vision_daily_zip_url(
        source_id="binance_vision_usdm_trades",
        symbol="BTCUSDT",
        day=day,
    ) == (
        "https://data.binance.vision/data/futures/um/daily/trades/"
        "BTCUSDT/BTCUSDT-trades-2024-01-02.zip"
    )
    assert binance_vision_daily_zip_url(
        source_id="binance_vision_usdm_agg_trades",
        symbol="BTCUSDT",
        day=day,
    ) == (
        "https://data.binance.vision/data/futures/um/daily/aggTrades/"
        "BTCUSDT/BTCUSDT-aggTrades-2024-01-02.zip"
    )
    assert binance_vision_daily_zip_url(
        source_id="binance_vision_usdm_klines",
        symbol="BTCUSDT",
        day=day,
    ) == (
        "https://data.binance.vision/data/futures/um/daily/klines/"
        "BTCUSDT/1m/BTCUSDT-1m-2024-01-02.zip"
    )
    assert binance_vision_daily_zip_url(
        source_id="binance_vision_spot_trades",
        symbol="BTCUSDT",
        day=day,
    ) == (
        "https://data.binance.vision/data/spot/daily/trades/"
        "BTCUSDT/BTCUSDT-trades-2024-01-02.zip"
    )
    assert binance_vision_daily_zip_url(
        source_id="binance_vision_spot_agg_trades",
        symbol="BTCUSDT",
        day=day,
    ) == (
        "https://data.binance.vision/data/spot/daily/aggTrades/"
        "BTCUSDT/BTCUSDT-aggTrades-2024-01-02.zip"
    )
    assert binance_vision_daily_zip_url(
        source_id="binance_vision_spot_klines",
        symbol="BTCUSDT",
        day=day,
    ) == (
        "https://data.binance.vision/data/spot/daily/klines/"
        "BTCUSDT/1m/BTCUSDT-1m-2024-01-02.zip"
    )


def test_binance_vision_availability_manifest_records_zip_and_checksum_statuses(tmp_path) -> None:
    calls: list[str] = []

    def fake_head(url: str) -> BinanceVisionHeadResult:
        calls.append(url)
        if "2024-01-02" in url:
            return BinanceVisionHeadResult(status_code=404)
        if url.endswith(".CHECKSUM") and "trades" in url:
            return BinanceVisionHeadResult(status_code=200, headers={"content-length": "64"})
        if url.endswith(".CHECKSUM"):
            return BinanceVisionHeadResult(status_code=404)
        return BinanceVisionHeadResult(status_code=200, headers={"content-length": "1024"})

    result = write_binance_vision_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(binance_usdm_verified=True),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[
            _source_entry("source_registry_binance_vision_usdm_trades.json"),
            _source_entry("source_registry_binance_vision_usdm_klines.json"),
        ],
        source_ids=("binance_vision_usdm_trades", "binance_vision_usdm_klines"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        head_probe=fake_head,
        base_url="https://example.test",
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.row_count == 4
    assert manifest.available_count == 2
    assert manifest.missing_count == 2
    assert manifest.checksum_available_count == 1
    assert manifest.checksum_missing_count == 1
    assert result.research_only is True
    assert result.candidate_pack_eligible is False

    kline = next(row for row in manifest.rows if row.family == "klines" and row.probe_date == date(2024, 1, 1))
    assert kline.zip_url == (
        "https://example.test/data/futures/um/daily/klines/"
        "BTCUSDT/1m/BTCUSDT-1m-2024-01-01.zip"
    )
    assert kline.zip_status == BinanceVisionAvailabilityStatus.AVAILABLE
    assert kline.checksum_status == BinanceVisionChecksumStatus.MISSING
    assert kline.native_to_hyperliquid is False
    assert kline.symbol_map_ref == SYMBOL_MAP_REF

    missing = next(row for row in manifest.rows if row.family == "trades" and row.probe_date == date(2024, 1, 2))
    assert missing.zip_status == BinanceVisionAvailabilityStatus.MISSING
    assert missing.checksum_status == BinanceVisionChecksumStatus.NOT_CHECKED
    assert not any(call.endswith("2024-01-02.zip.CHECKSUM") for call in calls)


def test_binance_vision_availability_blocks_unverified_mapping_without_probe(tmp_path) -> None:
    def forbidden_head(url: str) -> BinanceVisionHeadResult:
        raise AssertionError(f"unexpected probe: {url}")

    result = write_binance_vision_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(binance_usdm_verified=True),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[_source_entry("source_registry_binance_vision_spot_trades.json")],
        source_ids=("binance_vision_spot_trades",),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        head_probe=forbidden_head,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.blocked_mapping_count == 1
    row = manifest.rows[0]
    assert row.zip_status == BinanceVisionAvailabilityStatus.BLOCKED_MAPPING
    assert row.zip_url is None
    assert row.checksum_status == BinanceVisionChecksumStatus.NOT_CHECKED
    assert row.blocked_reasons == ("binance_spot mapping is not_checked",)


def test_binance_vision_availability_rejects_paid_source_before_probe(tmp_path) -> None:
    payload = _source_entry("source_registry_binance_vision_usdm_trades.json").model_dump(mode="json")
    payload.update(
        {
            "cost_class": "paid_or_keyed",
            "auth_required": True,
            "secret_required": True,
            "paid_required": True,
            "strict_zero_dollar_allowed": False,
            "accepted_under_strict_free": False,
            "accepted_historical_coverage_proof": False,
        }
    )
    paid_source = SourceRegistryEntry(**payload)

    def forbidden_head(url: str) -> BinanceVisionHeadResult:
        raise AssertionError(f"unexpected probe: {url}")

    with pytest.raises(ValueError, match="not allowed in strict-zero-dollar mode"):
        write_binance_vision_availability_manifest(
            archive_root=tmp_path / "archive",
            symbol_map_snapshot=_symbol_map_snapshot(binance_usdm_verified=True),
            source_entries=[paid_source],
            source_ids=("binance_vision_usdm_trades",),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            head_probe=forbidden_head,
        )

    assert not (tmp_path / "archive" / "manifests" / "source_availability").exists()


def test_binance_vision_source_samples_validate() -> None:
    for source_id in DEFAULT_BINANCE_VISION_SOURCE_IDS:
        filename = f"source_registry_{source_id}.json"
        entry = _source_entry(filename)
        assert entry.source_id == source_id
        assert entry.venue == "binance"
        assert entry.native_to_hyperliquid is False
        assert entry.accepted_under_strict_free is True


def _load_manifest(archive_root: Path, ref: str) -> BinanceVisionAvailabilityManifest:
    return BinanceVisionAvailabilityManifest(
        **json.loads((archive_root / ref).read_text(encoding="utf-8"))
    )


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )


def _symbol_map_snapshot(*, binance_usdm_verified: bool) -> SymbolMapSnapshot:
    probes = []
    if binance_usdm_verified:
        probes.append(
            SymbolProbeResult(
                venue_key="binance_usdm",
                status=ProbeStatus.VERIFIED,
                symbol="BTCUSDT",
            )
        )
    row = resolve_symbol_map_for_coin(
        hyperliquid_coin="BTC",
        as_of_date=date(2026, 6, 22),
        hyperliquid_liquid_as_of=True,
        above_day_notional_threshold=True,
        probes=probes,
        universe_snapshot_ref=f"manifests/universe_snapshots.parquet#snapshot_id={UNIVERSE_SNAPSHOT_ID}",
    )
    rows = (row,)
    row_hash = symbol_map_rows_hash(rows)
    snapshot_id = symbol_map_snapshot_id_for(
        as_of_date=date(2026, 6, 22),
        universe_snapshot_id=UNIVERSE_SNAPSHOT_ID,
        source_registry_snapshot_id=SOURCE_REGISTRY_SNAPSHOT_ID,
        row_manifest_hash=row_hash,
    )
    return SymbolMapSnapshot(
        symbol_map_snapshot_id=snapshot_id,
        as_of_date=date(2026, 6, 22),
        universe_snapshot_id=UNIVERSE_SNAPSHOT_ID,
        universe_snapshot_ref=f"manifests/universe_snapshots.parquet#snapshot_id={UNIVERSE_SNAPSHOT_ID}",
        source_registry_snapshot_id=SOURCE_REGISTRY_SNAPSHOT_ID,
        source_registry_ref=SOURCE_REGISTRY_REF,
        symbol_map_rows=rows,
        symbol_map_count=1,
        liquid_symbol_count=1,
        above_day_notional_threshold_count=1,
        blocker_count=0,
        row_manifest_hash=row_hash,
    )
