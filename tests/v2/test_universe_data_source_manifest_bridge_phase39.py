from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tradingbotsuite.v2.data_sources.manifest_bridge import (
    write_universe_data_source_manifests,
)
from tradingbotsuite.v2.data_sources.schemas import (
    CostClass,
    SourceRegistryEntry,
    SourceRegistrySnapshot,
    SymbolMapSnapshot,
)
from tradingbotsuite.v2.data_sources.symbol_resolver import ProbeStatus, SymbolProbeResult
from tradingbotsuite.v2.universe.models import UniverseMode, UniverseSnapshotRow
from tradingbotsuite.v2.universe.rules import VOLUME_BELOW_THRESHOLD


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"
SNAPSHOT_ID = "a" * 64
RAW_HASH = "b" * 64
RAW_FILE_ID = "c" * 64


def test_universe_data_source_bridge_writes_registry_and_symbol_map_manifests(tmp_path) -> None:
    bundle = write_universe_data_source_manifests(
        archive_root=tmp_path / "archive",
        universe_rows=_universe_rows(),
        source_entries=[_hyperliquid_universe_source()],
        probes_by_coin={
            "BTC": [
                SymbolProbeResult(
                    venue_key="binance_usdm",
                    status=ProbeStatus.VERIFIED,
                    symbol="BTCUSDT",
                    source_refs=("binance_exchange_info:2026-06-22",),
                )
            ],
            "kPEPE": [
                SymbolProbeResult(
                    venue_key="bybit_linear",
                    status=ProbeStatus.AMBIGUOUS,
                    symbol="PEPEUSDT",
                    notes=("multiple PEPE-like contracts returned",),
                )
            ],
        },
        coin_by_instrument_id={"hyperliquid:perp:KPEPE": "kPEPE"},
        external_exchange_info_refs=("binance_exchange_info:2026-06-22",),
    )

    registry_payload = _load_archive_json(tmp_path / "archive", bundle.source_registry_ref)
    registry = SourceRegistrySnapshot(**registry_payload)
    assert registry.source_ids == ("hyperliquid_info_meta_asset_ctxs",)
    assert registry.strict_zero_dollar_mode is True
    assert registry.research_only is True
    assert registry.promotion_ready is False

    symbol_payload = _load_archive_json(tmp_path / "archive", bundle.symbol_map_ref)
    symbol_snapshot = SymbolMapSnapshot(**symbol_payload)
    assert symbol_snapshot.source_registry_ref == bundle.source_registry_ref
    assert symbol_snapshot.symbol_map_count == 2
    assert symbol_snapshot.above_day_notional_threshold_count == 1
    assert symbol_snapshot.blocker_count == 1

    btc = _symbol_row(symbol_snapshot, "BTC")
    assert btc.symbols["binance_usdm"].symbol == "BTCUSDT"
    assert btc.provenance["source_registry_ref"] == bundle.source_registry_ref
    assert btc.provenance["universe_snapshot_id"] == SNAPSHOT_ID

    kpepe = _symbol_row(symbol_snapshot, "kPEPE")
    assert kpepe.symbols["hyperliquid_perp"].symbol == "kPEPE"
    assert kpepe.above_day_notional_threshold is False
    assert kpepe.provenance["instrument_id"] == "hyperliquid:perp:KPEPE"
    assert kpepe.provenance["exclusion_reason"] == VOLUME_BELOW_THRESHOLD
    assert "below_day_notional_threshold" in kpepe.blocker_reasons
    assert "bybit_linear_ambiguous" in kpepe.blocker_reasons
    assert bundle.research_only is True
    assert bundle.candidate_pack_eligible is False


def test_universe_data_source_bridge_snapshot_ids_are_stable(tmp_path) -> None:
    kwargs = {
        "archive_root": tmp_path / "archive",
        "universe_rows": _universe_rows(),
        "source_entries": [_hyperliquid_universe_source()],
        "coin_by_instrument_id": {"hyperliquid:perp:KPEPE": "kPEPE"},
    }

    first = write_universe_data_source_manifests(**kwargs)
    second = write_universe_data_source_manifests(**kwargs)

    assert first.source_registry_snapshot_id == second.source_registry_snapshot_id
    assert first.symbol_map_snapshot_id == second.symbol_map_snapshot_id
    assert first.source_registry_ref == second.source_registry_ref
    assert first.symbol_map_ref == second.symbol_map_ref


def test_universe_data_source_bridge_rejects_requester_pays_source_before_writes(tmp_path) -> None:
    payload = _hyperliquid_universe_source().model_dump(mode="json")
    payload.update(
        {
            "source_id": "hyperliquid_requester_pays_universe_archive",
            "cost_class": "public_requester_pays_transfer",
            "strict_zero_dollar_allowed": False,
            "accepted_under_strict_free": False,
            "accepted_historical_coverage_proof": False,
            "required_operator_gate": ["operator_cost_ack"],
        }
    )
    requester_pays = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="not allowed in strict-zero-dollar mode"):
        write_universe_data_source_manifests(
            archive_root=tmp_path / "archive",
            universe_rows=_universe_rows(),
            source_entries=[requester_pays],
        )

    assert not (tmp_path / "archive" / "manifests" / "source_registry").exists()
    assert not (tmp_path / "archive" / "manifests" / "symbol_maps").exists()


def test_universe_data_source_bridge_rejects_free_sample_as_strict_free_accepted(tmp_path) -> None:
    payload = _hyperliquid_universe_source().model_dump(mode="json")
    payload.update(
        {
            "source_id": "hyperliquid_universe_free_sample",
            "cost_class": "free_sample_only",
            "accepted_under_strict_free": False,
            "accepted_historical_coverage_proof": False,
        }
    )
    free_sample = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="not accepted under strict-free mode"):
        write_universe_data_source_manifests(
            archive_root=tmp_path / "archive",
            universe_rows=_universe_rows(),
            source_entries=[free_sample],
        )


def test_hyperliquid_universe_source_sample_validates_as_strict_free() -> None:
    entry = _hyperliquid_universe_source()

    assert entry.source_id == "hyperliquid_info_meta_asset_ctxs"
    assert entry.venue == "hyperliquid"
    assert entry.cost_class == CostClass.ZERO_COST_PUBLIC
    assert "universe_snapshot" in entry.data_families


def _load_archive_json(archive_root: Path, ref: str) -> dict:
    return json.loads((archive_root / ref).read_text(encoding="utf-8"))


def _hyperliquid_universe_source() -> SourceRegistryEntry:
    return SourceRegistryEntry(
        **json.loads(
            (CONFIG_ROOT / "samples" / "source_registry_hyperliquid_info_meta_asset_ctxs.json")
            .read_text(encoding="utf-8")
        )
    )


def _universe_rows() -> list[UniverseSnapshotRow]:
    return [
        UniverseSnapshotRow(
            snapshot_id=SNAPSHOT_ID,
            asof_date=date(2026, 6, 22),
            venue="hyperliquid",
            universe_rule_id="hl_perps_day_ntl_vlm_gte_5m_v1",
            universe_mode=UniverseMode.AS_OF,
            instrument_id="hyperliquid:perp:BTC",
            day_ntl_vlm_usd=100_000_000,
            eligible_volume=True,
            eligible=True,
            raw_payload_sha256=RAW_HASH,
            raw_file_id=RAW_FILE_ID,
        ),
        UniverseSnapshotRow(
            snapshot_id=SNAPSHOT_ID,
            asof_date=date(2026, 6, 22),
            venue="hyperliquid",
            universe_rule_id="hl_perps_day_ntl_vlm_gte_5m_v1",
            universe_mode=UniverseMode.AS_OF,
            instrument_id="hyperliquid:perp:KPEPE",
            day_ntl_vlm_usd=4_999_999,
            eligible_volume=False,
            eligible=False,
            exclusion_reason=VOLUME_BELOW_THRESHOLD,
            raw_payload_sha256=RAW_HASH,
            raw_file_id=RAW_FILE_ID,
        ),
    ]


def _symbol_row(snapshot: SymbolMapSnapshot, coin: str):
    matches = [row for row in snapshot.symbol_map_rows if row.hyperliquid_coin == coin]
    assert len(matches) == 1
    return matches[0]
