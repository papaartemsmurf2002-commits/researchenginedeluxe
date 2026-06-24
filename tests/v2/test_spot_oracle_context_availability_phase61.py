from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.schemas import (
    SourceRegistryEntry,
    SymbolMapSnapshot,
    symbol_map_rows_hash,
    symbol_map_snapshot_id_for,
)
from tradingbotsuite.v2.data_sources.spot_oracle_context import (
    SpotOracleContextAvailabilityManifest,
    SpotOracleContextAvailabilityStatus,
    SpotOracleContextGetResult,
    build_spot_oracle_context_availability_request,
    write_spot_oracle_context_availability_manifest,
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


def test_spot_oracle_context_request_builders_are_stable() -> None:
    day = date(2024, 1, 2)

    coinbase = build_spot_oracle_context_availability_request(
        endpoint_id="coinbase_spot_candles",
        symbol="btc-usd",
        day=day,
    )
    assert coinbase.request_url == (
        "https://api.exchange.coinbase.com/products/BTC-USD/candles?"
        "start=2024-01-02T00%3A00%3A00Z&end=2024-01-03T00%3A00%3A00Z&granularity=60"
    )

    kraken = build_spot_oracle_context_availability_request(
        endpoint_id="kraken_spot_ohlc",
        symbol="btc/usd",
        day=day,
    )
    assert kraken.request_url == (
        "https://api.kraken.com/0/public/OHLC?"
        "pair=BTC%2FUSD&interval=1&since=1704153600"
    )

    pyth = build_spot_oracle_context_availability_request(
        endpoint_id="pyth_hermes_latest_price",
        symbol="0xbtcfeed",
        day=day,
    )
    assert pyth.request_url == (
        "https://hermes.pyth.network/v2/updates/price/latest?ids%5B%5D=0xbtcfeed"
    )

    defillama = build_spot_oracle_context_availability_request(
        endpoint_id="defillama_current_price",
        symbol="coingecko:bitcoin",
        day=day,
    )
    assert defillama.request_url == "https://coins.llama.fi/prices/current/coingecko:bitcoin"

    dexscreener = build_spot_oracle_context_availability_request(
        endpoint_id="dexscreener_pair_search",
        symbol="BTC",
        day=day,
    )
    assert dexscreener.request_url == "https://api.dexscreener.com/latest/dex/search?q=BTC"

    geckoterminal = build_spot_oracle_context_availability_request(
        endpoint_id="geckoterminal_pool_search",
        symbol="BTC",
        day=day,
    )
    assert geckoterminal.request_url == "https://api.geckoterminal.com/api/v2/search/pools?query=BTC"


def test_spot_oracle_context_availability_manifest_records_available_rows(tmp_path) -> None:
    calls: list[str] = []

    def fake_get(url: str) -> SpotOracleContextGetResult:
        calls.append(url)
        if "coinbase" in url:
            return SpotOracleContextGetResult(
                status_code=200,
                payload=[["1704067200", "0.5", "2", "1", "1.5", "10"]],
            )
        if "kraken" in url:
            return SpotOracleContextGetResult(
                status_code=200,
                payload={
                    "error": [],
                    "result": {
                        "XXBTZUSD": [
                            [1704067200, "1", "2", "0.5", "1.5", "10", "1704067200", "1"]
                        ],
                        "last": "1704067200",
                    },
                },
            )
        if "pyth" in url:
            return SpotOracleContextGetResult(status_code=200, payload={"parsed": [{"id": "0xbtcfeed"}]})
        if "llama" in url:
            return SpotOracleContextGetResult(
                status_code=200,
                payload={"coins": {"coingecko:bitcoin": {"price": 1}}},
            )
        if "dexscreener" in url:
            return SpotOracleContextGetResult(status_code=200, payload={"pairs": [{"pairAddress": "x"}]})
        return SpotOracleContextGetResult(status_code=200, payload={"data": [{"id": "x"}]})

    result = write_spot_oracle_context_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(
            verified=(
                "coinbase_spot",
                "kraken_spot",
                "pyth_feed",
                "defillama_context",
                "dexscreener",
                "geckoterminal",
            )
        ),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[
            _source_entry("source_registry_coinbase_spot_public.json"),
            _source_entry("source_registry_kraken_spot_public.json"),
            _source_entry("source_registry_pyth_hermes_public.json"),
            _source_entry("source_registry_defillama_public.json"),
            _source_entry("source_registry_dexscreener_public.json"),
            _source_entry("source_registry_geckoterminal_public.json"),
        ],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=fake_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.row_count == 6
    assert manifest.available_count == 6
    assert manifest.missing_count == 0
    assert manifest.probe_error_count == 0
    assert len(calls) == 6
    assert result.research_only is True
    assert result.candidate_pack_eligible is False

    defillama = next(row for row in manifest.rows if row.endpoint_id == "defillama_current_price")
    assert defillama.availability_status == SpotOracleContextAvailabilityStatus.AVAILABLE
    assert defillama.venue_symbol == "coingecko:bitcoin"
    assert defillama.native_to_hyperliquid is False
    assert defillama.accepted_historical_coverage_proof is False
    assert defillama.symbol_map_ref == SYMBOL_MAP_REF


def test_spot_oracle_context_blocks_unverified_mapping_without_probe(tmp_path) -> None:
    def forbidden_get(url: str) -> SpotOracleContextGetResult:
        raise AssertionError(f"unexpected probe: {url}")

    result = write_spot_oracle_context_availability_manifest(
        archive_root=tmp_path / "archive",
        symbol_map_snapshot=_symbol_map_snapshot(verified=("coinbase_spot",)),
        symbol_map_ref=SYMBOL_MAP_REF,
        source_entries=[_source_entry("source_registry_defillama_public.json")],
        source_ids=("defillama_public",),
        endpoint_ids=("defillama_current_price",),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 1),
        get_probe=forbidden_get,
    )

    manifest = _load_manifest(tmp_path / "archive", result.manifest_ref)
    assert manifest.blocked_mapping_count == 1
    row = manifest.rows[0]
    assert row.availability_status == SpotOracleContextAvailabilityStatus.BLOCKED_MAPPING
    assert row.request_url is None
    assert row.blocked_reasons == ("defillama_context mapping is not_checked",)


def test_spot_oracle_context_rejects_historical_coverage_source_claim(tmp_path) -> None:
    payload = _source_entry("source_registry_pyth_hermes_public.json").model_dump(mode="json")
    payload["accepted_historical_coverage_proof"] = True
    source = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="cannot be accepted historical coverage proof"):
        write_spot_oracle_context_availability_manifest(
            archive_root=tmp_path / "archive",
            symbol_map_snapshot=_symbol_map_snapshot(verified=("pyth_feed",)),
            source_entries=[source],
            source_ids=("pyth_hermes_public",),
            endpoint_ids=("pyth_hermes_latest_price",),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            get_probe=lambda url: SpotOracleContextGetResult(status_code=200),
        )

    assert not (tmp_path / "archive" / "manifests" / "source_availability").exists()


def _load_manifest(archive_root: Path, ref: str) -> SpotOracleContextAvailabilityManifest:
    return SpotOracleContextAvailabilityManifest(
        **json.loads((archive_root / ref).read_text(encoding="utf-8"))
    )


def _source_entry(filename: str) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads((CONFIG_ROOT / "samples" / filename).read_text(encoding="utf-8"))
    )


def _symbol_map_snapshot(*, verified: tuple[str, ...]) -> SymbolMapSnapshot:
    symbols = {
        "coinbase_spot": "BTC-USD",
        "kraken_spot": "BTC/USD",
        "pyth_feed": "0xbtcfeed",
        "defillama_context": "coingecko:bitcoin",
        "dexscreener": "BTC",
        "geckoterminal": "BTC",
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
