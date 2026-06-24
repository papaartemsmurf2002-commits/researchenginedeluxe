from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.bybit_okx import (
    BybitOkxAvailabilityManifest,
    BybitOkxAvailabilityStatus,
    BybitOkxGetResult,
    build_bybit_okx_availability_request,
    write_bybit_okx_availability_manifest,
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


def test_bybit_okx_request_builders_are_stable() -> None:
    day = date(2024, 1, 2)

    bybit = build_bybit_okx_availability_request(
        endpoint_id="bybit_kline",
        symbol="btcusdt",
        day=day,
    )
    assert bybit.request_url == (
        "https://api.bybit.com/v5/market/kline?"
        "category=linear&symbol=BTCUSDT&interval=1&start=1704153600000"
        "&end=1704240000000&limit=1000"
    )
    assert bybit.probe_start_ms == 1704153600000
    assert bybit.probe_end_ms == 1704240000000

    okx = build_bybit_okx_availability_request(
        endpoint_id="okx_history_candles",
        symbol="btc-usdt-swap",
        day=day,
    )
    assert okx.request_url == (
        "https://www.okx.com/api/v5/market/history-candles?"
        "instId=BTC-USDT-SWAP&bar=1m&after=1704153600000"
        "&before=1704240000000&limit=100"
    )


def test_bybit_okx_availability_manifest_records_available_and_endpoint_limited_rows(
    tmp_path,
) -> None:
    calls: list[str] = []

    def fake_get(url: str) -> BybitOkxGetResult:
        calls.append(url)
        if "api.bybit.com" in url:
            return BybitOkxGetResult(
                status_code=200,
                payload={"retCode": 0, "result": {"list": [["1704067200000", "1"]]}},
            )
        return BybitOkxGetResult(
            status_code=200,
            payload={"code": "0", "data": [["1704067200000", "1"]]},
        )

    result = write_bybit_okx_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(bybit_verified=True, okx_verified=True),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[
            _source_entry("source_registry_bybit_public_market.json"),
            _source_entry("source_registry_okx_public_market.json"),
        ],
        source_ids=("bybit_public_market", "okx_public_market"),
        endpoint_ids=("bybit_kline", "okx_history_candles", "bybit_orderbook"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=fake_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.row_count == 3
    assert manifest.available_count == 2
    assert manifest.blocked_endpoint_limit_count == 1
    assert manifest.missing_count == 0
    assert manifest.probe_error_count == 0
    assert len(calls) == 2
    assert not any("/v5/market/orderbook" in call for call in calls)

    bybit_kline = next(row for row in manifest.rows if row.endpoint_id == "bybit_kline")
    assert bybit_kline.availability_status == BybitOkxAvailabilityStatus.AVAILABLE
    assert bybit_kline.response_row_count == 1
    assert bybit_kline.native_to_hyperliquid is False
    assert bybit_kline.accepted_historical_coverage_proof is False
    assert bybit_kline.symbol_map_ref == SYMBOL_MAP_REF

    orderbook = next(row for row in manifest.rows if row.endpoint_id == "bybit_orderbook")
    assert orderbook.availability_status == BybitOkxAvailabilityStatus.BLOCKED_ENDPOINT_LIMIT
    assert orderbook.blocked_reasons == ("endpoint_does_not_support_date_window",)
    assert orderbook.endpoint_caveats == ("snapshot_not_historical",)
    assert orderbook.request_url is not None


def test_bybit_okx_availability_records_missing_and_probe_errors(tmp_path) -> None:
    def fake_get(url: str) -> BybitOkxGetResult:
        if "retCode=bad" in url:
            raise AssertionError("query sentinel should not appear")
        return BybitOkxGetResult(
            status_code=200,
            payload={"retCode": 0, "result": {"list": []}},
        )

    result = write_bybit_okx_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(bybit_verified=True, okx_verified=False),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[_source_entry("source_registry_bybit_public_market.json")],
        source_ids=("bybit_public_market",),
        endpoint_ids=("bybit_kline",),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=fake_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.row_count == 1
    assert manifest.missing_count == 1
    row = manifest.rows[0]
    assert row.availability_status == BybitOkxAvailabilityStatus.MISSING
    assert row.response_row_count == 0
    assert row.blocked_reasons == ()


def test_bybit_okx_availability_blocks_unverified_mapping_without_probe(tmp_path) -> None:
    def forbidden_get(url: str) -> BybitOkxGetResult:
        raise AssertionError(f"unexpected probe: {url}")

    result = write_bybit_okx_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(bybit_verified=True, okx_verified=False),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[_source_entry("source_registry_okx_public_market.json")],
        source_ids=("okx_public_market",),
        endpoint_ids=("okx_history_candles",),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=forbidden_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.blocked_mapping_count == 1
    row = manifest.rows[0]
    assert row.availability_status == BybitOkxAvailabilityStatus.BLOCKED_MAPPING
    assert row.request_url is None
    assert row.blocked_reasons == ("okx_swap mapping is not_checked",)


def test_bybit_okx_availability_rejects_historical_coverage_source_claim(
    tmp_path,
) -> None:
    payload = _source_entry("source_registry_bybit_public_market.json").model_dump(mode="json")
    payload["accepted_historical_coverage_proof"] = True
    source = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="cannot be accepted historical coverage proof"):
        write_bybit_okx_availability_manifest(
            archive_root=tmp_path / "archive",
            symbol_map_snapshot=_symbol_map_snapshot(bybit_verified=True, okx_verified=True),
            source_entries=[source],
            source_ids=("bybit_public_market",),
            endpoint_ids=("bybit_kline",),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            get_probe=lambda url: BybitOkxGetResult(status_code=200),
        )

    assert not (tmp_path / "archive" / "manifests" / "source_availability").exists()


def _load_manifest(archive_root: Path, ref: str) -> BybitOkxAvailabilityManifest:
    return BybitOkxAvailabilityManifest(
        **json.loads((archive_root / ref).read_text(encoding="utf-8"))
    )


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )


def _symbol_map_snapshot(*, bybit_verified: bool, okx_verified: bool) -> SymbolMapSnapshot:
    probes = []
    if bybit_verified:
        probes.append(
            SymbolProbeResult(
                venue_key="bybit_linear",
                status=ProbeStatus.VERIFIED,
                symbol="BTCUSDT",
            )
        )
    if okx_verified:
        probes.append(
            SymbolProbeResult(
                venue_key="okx_swap",
                status=ProbeStatus.VERIFIED,
                symbol="BTC-USDT-SWAP",
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
