from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources.schemas import (
    MappingStatus,
    MarketType,
    VenueSymbolMapRow,
    require_verified_external_mapping,
)
from tradingbotsuite.v2.data_sources.symbol_resolver import (
    ProbeStatus,
    SymbolProbeResult,
    binance_contract_base_from_hyperliquid_coin,
    candidate_symbols_for_hyperliquid_coin,
    canonical_base_asset_from_hyperliquid_coin,
    resolve_symbol_map_for_coin,
    resolve_symbol_maps_from_universe_rows,
)
from tradingbotsuite.v2.universe.models import UniverseMode, UniverseSnapshotRow


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"
HEX_A = "a" * 64
HEX_B = "b" * 64


def test_candidate_symbols_cover_required_venue_keys_and_market_types() -> None:
    candidates = {item.venue_key: item for item in candidate_symbols_for_hyperliquid_coin("SOL")}

    assert set(candidates) == {
        "binance_usdm",
        "binance_spot",
        "bybit_linear",
        "okx_swap",
        "bitget_mix",
        "mexc_contract",
        "gate_futures",
        "kucoin_futures",
        "htx_swap",
        "dydx",
        "deribit_perpetual",
        "coinbase_spot",
        "kraken_spot",
        "pyth_feed",
        "defillama_context",
        "dexscreener",
        "geckoterminal",
    }
    assert candidates["binance_usdm"].symbol == "SOLUSDT"
    assert candidates["okx_swap"].symbol == "SOL-USDT-SWAP"
    assert candidates["deribit_perpetual"].symbol == "SOL-PERPETUAL"
    assert candidates["coinbase_spot"].market_type == MarketType.SPOT
    assert candidates["pyth_feed"].market_type == MarketType.ORACLE
    assert candidates["defillama_context"].market_type == MarketType.CONTEXT


def test_k_prefixed_coin_generates_binance_1000_contract_candidate() -> None:
    assert canonical_base_asset_from_hyperliquid_coin("kPEPE") == "PEPE"
    assert binance_contract_base_from_hyperliquid_coin("kPEPE") == "1000PEPE"

    candidates = {item.venue_key: item for item in candidate_symbols_for_hyperliquid_coin("kPEPE")}
    assert candidates["binance_usdm"].symbol == "1000PEPEUSDT"
    assert candidates["binance_spot"].symbol == "PEPEUSDT"


def test_symbol_map_resolver_marks_only_probed_venues_verified() -> None:
    row = resolve_symbol_map_for_coin(
        hyperliquid_coin="SOL",
        as_of_date=date(2026, 6, 22),
        hyperliquid_liquid_as_of=True,
        above_day_notional_threshold=True,
        probes=[
            SymbolProbeResult(
                venue_key="binance_usdm",
                status=ProbeStatus.VERIFIED,
                symbol="SOLUSDT",
                source_refs=("binance_exchange_info:2026-06-22",),
            )
        ],
        universe_snapshot_ref="manifests/universe/hyperliquid_asof_2026-06-22.json",
    )

    assert row.symbols["hyperliquid_perp"].symbol == "SOL"
    assert row.symbols["binance_usdm"].status == MappingStatus.VERIFIED
    assert row.symbols["okx_swap"].status == MappingStatus.NOT_CHECKED
    assert row.external_mapping_verified == MappingStatus.VERIFIED
    assert require_verified_external_mapping(row, "binance_usdm").symbol == "SOLUSDT"
    with pytest.raises(ValueError, match="okx_swap mapping is not_checked"):
        require_verified_external_mapping(row, "okx_swap")


def test_symbol_map_resolver_surfaces_missing_ambiguous_and_manual_review() -> None:
    row = resolve_symbol_map_for_coin(
        hyperliquid_coin="kPEPE",
        as_of_date=date(2026, 6, 22),
        hyperliquid_liquid_as_of=True,
        above_day_notional_threshold=True,
        probes=[
            {
                "venue_key": "binance_usdm",
                "status": "verified",
                "symbol": "1000PEPEUSDT",
                "source_refs": ["binance_exchange_info:2026-06-22"],
            },
            {
                "venue_key": "okx_swap",
                "status": "missing",
                "source_refs": ["okx_instruments:2026-06-22"],
            },
            {
                "venue_key": "bybit_linear",
                "status": "ambiguous",
                "symbol": "PEPEUSDT",
                "notes": ["multiple PEPE-like contracts returned"],
                "source_refs": ["bybit_instruments_info:2026-06-22"],
            },
            {
                "venue_key": "mexc_contract",
                "status": "manual_review_required",
                "symbol": "PEPE_USDT",
                "notes": ["contract size differs from Hyperliquid kPEPE"],
            },
        ],
        universe_snapshot_ref="manifests/universe/hyperliquid_asof_2026-06-22.json",
        external_exchange_info_refs=(
            "binance_exchange_info:2026-06-22",
            "okx_instruments:2026-06-22",
            "bybit_instruments_info:2026-06-22",
        ),
    )

    assert row.canonical_base_asset == "PEPE"
    assert row.symbols["binance_usdm"].symbol == "1000PEPEUSDT"
    assert row.symbols["okx_swap"].status == MappingStatus.MISSING
    assert row.symbols["bybit_linear"].status == MappingStatus.AMBIGUOUS
    assert row.symbols["mexc_contract"].status == MappingStatus.MANUAL_REVIEW_REQUIRED
    assert row.external_mapping_verified == MappingStatus.AMBIGUOUS
    assert "bybit_linear_ambiguous" in row.blocker_reasons
    assert "mexc_contract_manual_review_required" in row.blocker_reasons


def test_symbol_probe_requires_notes_for_ambiguous_or_manual_review() -> None:
    with pytest.raises(ValidationError, match="require notes"):
        SymbolProbeResult(venue_key="bybit_linear", status=ProbeStatus.AMBIGUOUS)


def test_symbol_map_sample_fixture_validates() -> None:
    payload = json.loads(
        (CONFIG_ROOT / "samples" / "symbol_map_kpepe_resolved_2026_06_22.json").read_text(
            encoding="utf-8"
        )
    )
    row = VenueSymbolMapRow(**payload)

    assert row.hyperliquid_coin == "kPEPE"
    assert row.symbols["binance_usdm"].symbol == "1000PEPEUSDT"
    assert row.external_mapping_verified == MappingStatus.AMBIGUOUS


def test_resolve_symbol_maps_from_universe_rows_preserves_venue_symbol_mapping() -> None:
    rows = [
        UniverseSnapshotRow(
            snapshot_id=HEX_A,
            asof_date=date(2026, 6, 22),
            venue="hyperliquid",
            universe_rule_id="hl_perps_day_ntl_vlm_gte_5m_v1",
            universe_mode=UniverseMode.AS_OF,
            instrument_id="hyperliquid:perp:KPEPE",
            day_ntl_vlm_usd=10_000_000,
            eligible_volume=True,
            eligible=True,
            raw_payload_sha256=HEX_B,
            raw_file_id=HEX_A,
        )
    ]

    resolved = resolve_symbol_maps_from_universe_rows(
        rows,
        probes_by_coin={
            "kPEPE": [
                SymbolProbeResult(
                    venue_key="binance_usdm",
                    status=ProbeStatus.VERIFIED,
                    symbol="1000PEPEUSDT",
                )
            ]
        },
        coin_by_instrument_id={"hyperliquid:perp:KPEPE": "kPEPE"},
        external_exchange_info_refs=("binance_exchange_info:2026-06-22",),
    )

    assert len(resolved) == 1
    assert resolved[0].hyperliquid_coin == "kPEPE"
    assert resolved[0].symbols["hyperliquid_perp"].symbol == "kPEPE"
    assert resolved[0].symbols["binance_usdm"].status == MappingStatus.VERIFIED
