# V2-AUDIT-ID: V2-AUD-XVENUE-001
# V2-CONTRACTS: docs/contracts/universe_contract.md, docs/contracts/venue_adapter_contract.md
# V2-BOUNDARY: research_only, cross_venue_universe_rows, no_live_imports
# V2-OWNER: v2_universe
"""Generic universe manifest table helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.universe.models import (
    AssetContextSnapshotRow,
    InstrumentCatalogRow,
    UniverseSnapshotRow,
)


def append_universe_tables(
    *,
    layout: ArchiveLayout,
    instruments: list[InstrumentCatalogRow],
    contexts: list[AssetContextSnapshotRow],
    rows: list[UniverseSnapshotRow],
) -> None:
    _append_model_rows(layout.resolve("manifests", "instrument_catalog.parquet"), instruments, ["instrument_id"])
    _append_model_rows(
        layout.resolve("manifests", "asset_context_snapshots.parquet"),
        contexts,
        ["instrument_id"],
    )
    _append_model_rows(
        layout.resolve("manifests", "universe_snapshots.parquet"),
        rows,
        ["snapshot_id", "instrument_id"],
    )


def _append_model_rows(path: Path, records: list[Any], key_fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.exists():
        existing = pq.read_table(path).to_pylist()
    rows = [record.model_dump(mode="json") for record in records]
    by_key = {tuple(row.get(field) for field in key_fields): row for row in existing}
    for row in rows:
        by_key[tuple(row.get(field) for field in key_fields)] = row
    ordered = sorted(by_key.values(), key=lambda row: tuple(str(row.get(field, "")) for field in key_fields))
    pq.write_table(pa.Table.from_pylist(ordered), path, compression="zstd")
