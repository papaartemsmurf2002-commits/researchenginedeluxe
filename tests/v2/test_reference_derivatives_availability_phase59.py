from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.reference_derivatives import (
    ReferenceDerivativesAvailabilityManifest,
    ReferenceDerivativesAvailabilityStatus,
    ReferenceDerivativesGetResult,
    build_reference_derivatives_availability_request,
    write_reference_derivatives_availability_manifest,
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


def test_reference_derivatives_request_builders_are_stable() -> None:
    day = date(2024, 1, 2)

    dydx = build_reference_derivatives_availability_request(
        endpoint_id="dydx_indexer_candles",
        symbol="btc-usd",
        day=day,
    )
    assert dydx.request_url == (
        "https://indexer.dydx.trade/v4/candles/perpetualMarkets/BTC-USD?"
        "resolution=1MIN&fromISO=2024-01-02T00%3A00%3A00Z"
        "&toISO=2024-01-03T00%3A00%3A00Z&limit=100"
    )

    deribit = build_reference_derivatives_availability_request(
        endpoint_id="deribit_tradingview_chart",
        symbol="btc-perpetual",
        day=day,
    )
    assert deribit.request_url == (
        "https://www.deribit.com/api/v2/public/get_tradingview_chart_data?"
        "instrument_name=BTC-PERPETUAL&start_timestamp=1704153600000"
        "&end_timestamp=1704240000000&resolution=1"
    )


def test_reference_derivatives_availability_manifest_records_available_rows(tmp_path) -> None:
    calls: list[str] = []

    def fake_get(url: str) -> ReferenceDerivativesGetResult:
        calls.append(url)
        if "dydx" in url:
            return ReferenceDerivativesGetResult(
                status_code=200,
                payload={"candles": [{"startedAt": "2024-01-01T00:00:00Z"}]},
            )
        return ReferenceDerivativesGetResult(
            status_code=200,
            payload={
                "jsonrpc": "2.0",
                "result": {
                    "status": "ok",
                    "ticks": [1704067200000],
                    "open": [1],
                },
            },
        )

    result = write_reference_derivatives_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(verified=("dydx", "deribit_perpetual")),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[
            _source_entry("source_registry_dydx_indexer_public.json"),
            _source_entry("source_registry_deribit_public.json"),
        ],
        endpoint_ids=("dydx_indexer_candles", "deribit_tradingview_chart"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=fake_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.row_count == 2
    assert manifest.available_count == 2
    assert manifest.missing_count == 0
    assert manifest.probe_error_count == 0
    assert len(calls) == 2
    assert result.research_only is True
    assert result.candidate_pack_eligible is False

    deribit = next(row for row in manifest.rows if row.endpoint_id == "deribit_tradingview_chart")
    assert deribit.availability_status == ReferenceDerivativesAvailabilityStatus.AVAILABLE
    assert deribit.venue_symbol == "BTC-PERPETUAL"
    assert deribit.native_to_hyperliquid is False
    assert deribit.accepted_historical_coverage_proof is False
    assert deribit.symbol_map_ref == SYMBOL_MAP_REF


def test_reference_derivatives_blocks_unverified_mapping_without_probe(tmp_path) -> None:
    def forbidden_get(url: str) -> ReferenceDerivativesGetResult:
        raise AssertionError(f"unexpected probe: {url}")

    result = write_reference_derivatives_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(verified=("dydx",)),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[_source_entry("source_registry_deribit_public.json")],
        source_ids=("deribit_public",),
        endpoint_ids=("deribit_tradingview_chart",),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=forbidden_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.blocked_mapping_count == 1
    row = manifest.rows[0]
    assert row.availability_status == ReferenceDerivativesAvailabilityStatus.BLOCKED_MAPPING
    assert row.request_url is None
    assert row.blocked_reasons == ("deribit_perpetual mapping is not_checked",)


def test_reference_derivatives_rejects_historical_coverage_source_claim(tmp_path) -> None:
    payload = _source_entry("source_registry_dydx_indexer_public.json").model_dump(mode="json")
    payload["accepted_historical_coverage_proof"] = True
    source = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="cannot be accepted historical coverage proof"):
        write_reference_derivatives_availability_manifest(
            archive_root=tmp_path / "archive",
            symbol_map_snapshot=_symbol_map_snapshot(verified=("dydx",)),
            source_entries=[source],
            source_ids=("dydx_indexer_public",),
            endpoint_ids=("dydx_indexer_candles",),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            get_probe=lambda url: ReferenceDerivativesGetResult(status_code=200),
        )

    assert not (tmp_path / "archive" / "manifests" / "source_availability").exists()


def _load_manifest(archive_root: Path, ref: str) -> ReferenceDerivativesAvailabilityManifest:
    return ReferenceDerivativesAvailabilityManifest(
        **json.loads((archive_root / ref).read_text(encoding="utf-8"))
    )


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )


def _symbol_map_snapshot(*, verified: tuple[str, ...]) -> SymbolMapSnapshot:
    symbols = {
        "dydx": "BTC-USD",
        "deribit_perpetual": "BTC-PERPETUAL",
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
