# V2-AUDIT-ID: V2-AUD-ARCH-002
# V2-CONTRACTS: docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, deterministic_tables, no_live_imports
# V2-OWNER: v2_archive
"""Parquet table writer for bronze, silver, and gold archive layers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, FileManifestRow
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION

WRITABLE_TABLE_LAYERS = {ArchiveLayer.BRONZE, ArchiveLayer.SILVER, ArchiveLayer.GOLD}


def write_parquet_rows(
    *,
    layout: ArchiveLayout,
    store: ArchiveManifestStore,
    rows: Iterable[Mapping[str, Any]],
    layer: ArchiveLayer,
    dataset: str,
    venue: str,
    datatype: str,
    date: str,
    job_id: str,
    source_file_ids: tuple[str, ...],
    filename: str | None = None,
    timeframe: str | None = None,
    hour: int | None = None,
    snapshot_id: str | None = None,
    instrument_id: str | None = None,
    schema_version: str = V2_SCHEMA_VERSION,
) -> FileManifestRow:
    if layer not in WRITABLE_TABLE_LAYERS:
        raise ValueError(f"parquet writer does not write layer {layer.value}")
    materialized = _normalize_rows(rows)
    if not materialized:
        raise ValueError("parquet writer requires at least one row")
    if filename is None:
        filename = f"part-{canonical_json_hash(materialized)[:16]}"
    path = layout.parquet_file_path(
        layer=layer,
        dataset=dataset,
        venue=venue,
        date=date,
        filename=filename,
        timeframe=timeframe,
        hour=hour,
        snapshot_id=snapshot_id,
    )
    if path.exists():
        raise FileExistsError(f"archive table file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(materialized)
    pq.write_table(table, path, compression="zstd")
    sha256 = file_sha256(path)
    row = FileManifestRow(
        file_id=sha256,
        path=layout.relative_to_root(path),
        layer=layer,
        venue=venue,
        datatype=datatype,
        instrument_id=instrument_id,
        timeframe=timeframe,
        date=date,
        hour=hour,
        sha256=sha256,
        size_bytes=path.stat().st_size,
        row_count=len(materialized),
        schema_version=schema_version,
        source_file_ids=source_file_ids,
        created_by_job_id=job_id,
    )
    store.upsert_file_manifest(row)
    return row


def _normalize_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    materialized = [dict(row) for row in rows]
    if not materialized:
        return []
    keys = sorted({key for row in materialized for key in row})
    return [{key: row.get(key) for key in keys} for row in materialized]
