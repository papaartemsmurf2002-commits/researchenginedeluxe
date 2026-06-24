# V2-AUDIT-ID: V2-AUD-DATASRC-004
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, strict_free_data_sources, no_live_imports
# V2-OWNER: v2_data_sources
"""Bridge universe snapshots into data-source registry and symbol-map manifests."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import file_sha256
from tradingbotsuite.v2.archive.layout import ArchiveLayout, safe_partition_value
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.data_sources.schemas import (
    SourceRegistryEntry,
    SourceRegistrySnapshot,
    SymbolMapSnapshot,
    source_registry_entries_hash,
    source_registry_snapshot_id_for,
    symbol_map_rows_hash,
    symbol_map_snapshot_id_for,
)
from tradingbotsuite.v2.data_sources.symbol_resolver import (
    SymbolProbeResult,
    resolve_symbol_map_for_coin,
)
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.universe.models import UniverseSnapshotRow


class UniverseDataSourceManifestBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    manifest_type: str = "universe_data_source_manifest_bundle"
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_ref: str = Field(min_length=1)
    as_of_date: date
    source_registry_snapshot_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    source_registry_sha256: str = Field(min_length=64, max_length=64)
    symbol_map_snapshot_id: str = Field(min_length=64, max_length=64)
    symbol_map_ref: str = Field(min_length=1)
    symbol_map_sha256: str = Field(min_length=64, max_length=64)
    source_count: int = Field(ge=1)
    symbol_map_count: int = Field(ge=0)
    liquid_symbol_count: int = Field(ge=0)
    above_day_notional_threshold_count: int = Field(ge=0)
    blocker_count: int = Field(ge=0)
    strict_zero_dollar_mode: bool = True
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False
    candidate_evidence: bool = False
    candidate_pack_eligible: bool = False
    live_signal: bool = False
    paper_signal: bool = False
    sizing_instruction: bool = False
    order_placement_instruction: bool = False
    runtime_mode_change: bool = False

    @model_validator(mode="after")
    def _validate_bundle(self) -> "UniverseDataSourceManifestBundle":
        require_research_boundary(self, context="universe data-source manifest bundle")
        if self.manifest_type != "universe_data_source_manifest_bundle":
            raise ValueError("manifest_type must be universe_data_source_manifest_bundle")
        return self


def write_universe_data_source_manifests(
    *,
    archive_root: str | Path,
    universe_rows: Iterable[UniverseSnapshotRow | Mapping[str, Any]],
    source_entries: Iterable[SourceRegistryEntry | Mapping[str, Any]],
    probes_by_coin: Mapping[str, Iterable[SymbolProbeResult | Mapping[str, object]]] | None = None,
    coin_by_instrument_id: Mapping[str, str] | None = None,
    external_exchange_info_refs: Sequence[str] = (),
    strict_zero_dollar_mode: bool = True,
) -> UniverseDataSourceManifestBundle:
    """Write source-registry and symbol-map manifests for one universe snapshot."""

    layout = ArchiveLayout(archive_root)
    layout.initialize()
    rows = _materialize_universe_rows(universe_rows)
    scope = _single_universe_scope(rows)
    entries = _materialize_source_entries(source_entries)
    _require_hyperliquid_universe_source(entries)

    entry_hash = source_registry_entries_hash(entries)
    registry_snapshot_id = source_registry_snapshot_id_for(
        as_of_date=scope.as_of_date,
        universe_snapshot_id=scope.universe_snapshot_id,
        strict_zero_dollar_mode=strict_zero_dollar_mode,
        entry_manifest_hash=entry_hash,
    )
    universe_ref = _universe_snapshot_ref(scope.universe_snapshot_id)
    registry_snapshot = SourceRegistrySnapshot(
        registry_snapshot_id=registry_snapshot_id,
        as_of_date=scope.as_of_date,
        universe_snapshot_id=scope.universe_snapshot_id,
        universe_snapshot_ref=universe_ref,
        strict_zero_dollar_mode=strict_zero_dollar_mode,
        source_entries=entries,
        source_ids=tuple(sorted(entry.source_id for entry in entries)),
        source_count=len(entries),
        entry_manifest_hash=entry_hash,
    )
    registry_path = layout.resolve(
        "manifests",
        "source_registry",
        f"source_registry_{scope.as_of_date.isoformat()}_{registry_snapshot_id[:16]}.json",
    )
    _write_json_model(registry_path, registry_snapshot)
    registry_ref = layout.relative_to_root(registry_path)

    symbol_rows = _symbol_rows_for_universe(
        rows=rows,
        universe_snapshot_ref=universe_ref,
        source_registry_ref=registry_ref,
        probes_by_coin=probes_by_coin or {},
        coin_by_instrument_id=coin_by_instrument_id or {},
        external_exchange_info_refs=external_exchange_info_refs,
    )
    row_hash = symbol_map_rows_hash(symbol_rows)
    symbol_snapshot_id = symbol_map_snapshot_id_for(
        as_of_date=scope.as_of_date,
        universe_snapshot_id=scope.universe_snapshot_id,
        source_registry_snapshot_id=registry_snapshot_id,
        row_manifest_hash=row_hash,
    )
    symbol_snapshot = SymbolMapSnapshot(
        symbol_map_snapshot_id=symbol_snapshot_id,
        as_of_date=scope.as_of_date,
        universe_snapshot_id=scope.universe_snapshot_id,
        universe_snapshot_ref=universe_ref,
        source_registry_snapshot_id=registry_snapshot_id,
        source_registry_ref=registry_ref,
        symbol_map_rows=symbol_rows,
        symbol_map_count=len(symbol_rows),
        liquid_symbol_count=sum(1 for row in symbol_rows if row.hyperliquid_liquid_as_of),
        above_day_notional_threshold_count=sum(
            1 for row in symbol_rows if row.above_day_notional_threshold
        ),
        blocker_count=sum(1 for row in symbol_rows if row.blocker_reasons),
        row_manifest_hash=row_hash,
    )
    symbol_path = layout.resolve(
        "manifests",
        "symbol_maps",
        f"symbol_map_{scope.as_of_date.isoformat()}_{symbol_snapshot_id[:16]}.json",
    )
    _write_json_model(symbol_path, symbol_snapshot)

    return UniverseDataSourceManifestBundle(
        universe_snapshot_id=scope.universe_snapshot_id,
        universe_snapshot_ref=universe_ref,
        as_of_date=scope.as_of_date,
        source_registry_snapshot_id=registry_snapshot_id,
        source_registry_ref=registry_ref,
        source_registry_sha256=file_sha256(registry_path),
        symbol_map_snapshot_id=symbol_snapshot_id,
        symbol_map_ref=layout.relative_to_root(symbol_path),
        symbol_map_sha256=file_sha256(symbol_path),
        source_count=len(entries),
        symbol_map_count=len(symbol_rows),
        liquid_symbol_count=symbol_snapshot.liquid_symbol_count,
        above_day_notional_threshold_count=symbol_snapshot.above_day_notional_threshold_count,
        blocker_count=symbol_snapshot.blocker_count,
        strict_zero_dollar_mode=strict_zero_dollar_mode,
    )


class _UniverseScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    universe_snapshot_id: str
    as_of_date: date


def _materialize_universe_rows(
    rows: Iterable[UniverseSnapshotRow | Mapping[str, Any]],
) -> tuple[UniverseSnapshotRow, ...]:
    materialized = tuple(
        row if isinstance(row, UniverseSnapshotRow) else UniverseSnapshotRow.model_validate(dict(row))
        for row in rows
    )
    if not materialized:
        raise ValueError("universe_rows cannot be empty")
    return materialized


def _materialize_source_entries(
    entries: Iterable[SourceRegistryEntry | Mapping[str, Any]],
) -> tuple[SourceRegistryEntry, ...]:
    materialized = tuple(
        entry if isinstance(entry, SourceRegistryEntry) else SourceRegistryEntry.model_validate(dict(entry))
        for entry in entries
    )
    if not materialized:
        raise ValueError("source_entries cannot be empty")
    return materialized


def _single_universe_scope(rows: tuple[UniverseSnapshotRow, ...]) -> _UniverseScope:
    snapshot_ids = {row.snapshot_id for row in rows}
    as_of_dates = {row.asof_date for row in rows}
    venues = {row.venue for row in rows}
    if len(snapshot_ids) != 1:
        raise ValueError("universe_rows must belong to exactly one snapshot")
    if len(as_of_dates) != 1:
        raise ValueError("universe_rows must share one as-of date")
    if venues != {"hyperliquid"}:
        raise ValueError("universe data-source bridge currently supports Hyperliquid rows only")
    return _UniverseScope(
        universe_snapshot_id=next(iter(snapshot_ids)),
        as_of_date=next(iter(as_of_dates)),
    )


def _require_hyperliquid_universe_source(entries: tuple[SourceRegistryEntry, ...]) -> None:
    for entry in entries:
        if (
            entry.venue == "hyperliquid"
            and entry.native_to_hyperliquid
            and {"universe_metadata", "universe_snapshot"} & set(entry.data_families)
        ):
            return
    raise ValueError("source_entries must include a Hyperliquid-native universe source")


def _universe_snapshot_ref(snapshot_id: str) -> str:
    return f"manifests/universe_snapshots.parquet#snapshot_id={snapshot_id}"


def _symbol_rows_for_universe(
    *,
    rows: tuple[UniverseSnapshotRow, ...],
    universe_snapshot_ref: str,
    source_registry_ref: str,
    probes_by_coin: Mapping[str, Iterable[SymbolProbeResult | Mapping[str, object]]],
    coin_by_instrument_id: Mapping[str, str],
    external_exchange_info_refs: Sequence[str],
) -> tuple:
    resolved = []
    for row in sorted(rows, key=lambda item: item.instrument_id):
        coin = coin_by_instrument_id.get(row.instrument_id, row.instrument_id.rsplit(":", 1)[-1])
        symbol_row = resolve_symbol_map_for_coin(
            hyperliquid_coin=coin,
            as_of_date=row.asof_date,
            hyperliquid_liquid_as_of=row.eligible_status,
            above_day_notional_threshold=row.eligible_volume,
            probes=probes_by_coin.get(coin, ()),
            universe_snapshot_ref=universe_snapshot_ref,
            external_exchange_info_refs=external_exchange_info_refs,
        )
        provenance = dict(symbol_row.provenance)
        provenance.update(
            {
                "universe_snapshot_id": row.snapshot_id,
                "universe_snapshot_ref": universe_snapshot_ref,
                "source_registry_ref": source_registry_ref,
                "instrument_id": row.instrument_id,
                "eligible": row.eligible,
                "eligible_volume": row.eligible_volume,
                "eligible_coverage": row.eligible_coverage,
                "eligible_history": row.eligible_history,
                "eligible_status": row.eligible_status,
                "eligible_hip3_metadata": row.eligible_hip3_metadata,
                "exclusion_reason": row.exclusion_reason,
                "raw_payload_sha256": row.raw_payload_sha256,
                "raw_file_id": row.raw_file_id,
            }
        )
        blockers = list(symbol_row.blocker_reasons)
        if not row.eligible_volume:
            blockers.append("below_day_notional_threshold")
        if row.exclusion_reason:
            blockers.append(f"universe_excluded:{safe_partition_value(row.exclusion_reason)}")
        resolved.append(
            symbol_row.model_copy(
                update={
                    "provenance": provenance,
                    "blocker_reasons": tuple(sorted(set(blockers))),
                }
            )
        )
    return tuple(resolved)


def _write_json_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
