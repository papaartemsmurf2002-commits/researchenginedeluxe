from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.alt_derivatives import (
    AltDerivativesAvailabilityManifest,
    AltDerivativesAvailabilityStatus,
    AltDerivativesGetResult,
    build_alt_derivatives_availability_request,
    write_alt_derivatives_availability_manifest,
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


def test_alt_derivatives_request_builders_are_stable() -> None:
    day = date(2024, 1, 2)

    bitget = build_alt_derivatives_availability_request(
        endpoint_id="bitget_mix_candles",
        symbol="btcusdt",
        day=day,
    )
    assert bitget.request_url == (
        "https://api.bitget.com/api/v2/mix/market/candles?"
        "symbol=BTCUSDT&productType=USDT-FUTURES&granularity=1m"
        "&startTime=1704153600000&endTime=1704240000000&limit=100"
    )

    mexc = build_alt_derivatives_availability_request(
        endpoint_id="mexc_contract_kline",
        symbol="btc_usdt",
        day=day,
    )
    assert mexc.request_url == (
        "https://contract.mexc.com/api/v1/contract/kline/BTC_USDT?"
        "interval=Min1&start=1704153600&end=1704240000"
    )


def test_alt_derivatives_availability_manifest_records_available_rows(tmp_path) -> None:
    calls: list[str] = []

    def fake_get(url: str) -> AltDerivativesGetResult:
        calls.append(url)
        if "bitget" in url:
            return AltDerivativesGetResult(status_code=200, payload={"code": "00000", "data": [["1"]]})
        if "mexc" in url:
            return AltDerivativesGetResult(status_code=200, payload={"success": True, "data": {"time": [1]}})
        if "gateio" in url:
            return AltDerivativesGetResult(status_code=200, payload=[["1"]])
        if "kucoin" in url:
            return AltDerivativesGetResult(status_code=200, payload={"code": "200000", "data": [["1"]]})
        return AltDerivativesGetResult(status_code=200, payload={"status": "ok", "data": [["1"]]})

    result = write_alt_derivatives_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(
            verified=("bitget_mix", "mexc_contract", "gate_futures", "kucoin_futures", "htx_swap")
        ),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[
            _source_entry("source_registry_bitget_public_mix_market.json"),
            _source_entry("source_registry_mexc_contract_public.json"),
            _source_entry("source_registry_gate_futures_public.json"),
            _source_entry("source_registry_kucoin_futures_public.json"),
            _source_entry("source_registry_htx_swap_public.json"),
        ],
        endpoint_ids=(
            "bitget_mix_candles",
            "mexc_contract_kline",
            "gate_futures_candlesticks",
            "kucoin_futures_kline",
            "htx_swap_history_kline",
        ),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=fake_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.row_count == 5
    assert manifest.available_count == 5
    assert manifest.missing_count == 0
    assert manifest.probe_error_count == 0
    assert len(calls) == 5
    assert result.research_only is True
    assert result.candidate_pack_eligible is False

    htx = next(row for row in manifest.rows if row.endpoint_id == "htx_swap_history_kline")
    assert htx.availability_status == AltDerivativesAvailabilityStatus.AVAILABLE
    assert htx.venue_symbol == "BTC-USDT"
    assert htx.native_to_hyperliquid is False
    assert htx.accepted_historical_coverage_proof is False
    assert htx.symbol_map_ref == SYMBOL_MAP_REF


def test_alt_derivatives_availability_blocks_unverified_mapping_without_probe(tmp_path) -> None:
    def forbidden_get(url: str) -> AltDerivativesGetResult:
        raise AssertionError(f"unexpected probe: {url}")

    result = write_alt_derivatives_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(verified=("bitget_mix",)),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[_source_entry("source_registry_htx_swap_public.json")],
        source_ids=("htx_swap_public",),
        endpoint_ids=("htx_swap_history_kline",),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=forbidden_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.blocked_mapping_count == 1
    row = manifest.rows[0]
    assert row.availability_status == AltDerivativesAvailabilityStatus.BLOCKED_MAPPING
    assert row.request_url is None
    assert row.blocked_reasons == ("htx_swap mapping is not_checked",)


def test_alt_derivatives_availability_rejects_historical_coverage_source_claim(tmp_path) -> None:
    payload = _source_entry("source_registry_gate_futures_public.json").model_dump(mode="json")
    payload["accepted_historical_coverage_proof"] = True
    source = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="cannot be accepted historical coverage proof"):
        write_alt_derivatives_availability_manifest(
            archive_root=tmp_path / "archive",
            symbol_map_snapshot=_symbol_map_snapshot(verified=("gate_futures",)),
            source_entries=[source],
            source_ids=("gate_futures_public",),
            endpoint_ids=("gate_futures_candlesticks",),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            get_probe=lambda url: AltDerivativesGetResult(status_code=200),
        )

    assert not (tmp_path / "archive" / "manifests" / "source_availability").exists()


def _load_manifest(archive_root: Path, ref: str) -> AltDerivativesAvailabilityManifest:
    return AltDerivativesAvailabilityManifest(
        **json.loads((archive_root / ref).read_text(encoding="utf-8"))
    )


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )


def _symbol_map_snapshot(*, verified: tuple[str, ...]) -> SymbolMapSnapshot:
    symbols = {
        "bitget_mix": "BTCUSDT",
        "mexc_contract": "BTC_USDT",
        "gate_futures": "BTC_USDT",
        "kucoin_futures": "BTCUSDTM",
        "htx_swap": "BTC-USDT",
    }
    probes = [
        SymbolProbeResult(
            venue_key=venue_key,
            status=ProbeStatus.VERIFIED,
            symbol=symbols[venue_key],
        )
        for venue_key in verified
    ]
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
