# V2-AUDIT-ID: V2-AUD-ARCH-003
# V2-CONTRACTS: docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, deterministic_snapshots, no_live_imports
# V2-OWNER: v2_archive
"""Deterministic archive snapshot builder."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, ArchiveSnapshotRecord, FileManifestRow

EMPTY_MANIFEST_HASH = manifest_rows_hash([])


def create_archive_snapshot(
    *,
    store: ArchiveManifestStore,
    layer: ArchiveLayer,
    venue_scope: str,
    start_ts: datetime,
    end_ts: datetime,
    coverage_rows: Iterable[Mapping[str, Any]] = (),
    quality_rows: Iterable[Mapping[str, Any]] = (),
    lockbox_policy_id: str | None = None,
    notes: str | None = None,
) -> ArchiveSnapshotRecord:
    files = [row for row in store.load_file_manifest() if row.layer == layer]
    file_manifest_hash = manifest_rows_hash(_manifest_dicts(files))
    coverage_manifest_hash = manifest_rows_hash(coverage_rows)
    quality_manifest_hash = manifest_rows_hash(quality_rows)
    identity = {
        "layer": layer.value,
        "venue_scope": venue_scope,
        "start_ts": start_ts.isoformat(),
        "end_ts": end_ts.isoformat(),
        "file_manifest_hash": file_manifest_hash,
        "coverage_manifest_hash": coverage_manifest_hash,
        "quality_manifest_hash": quality_manifest_hash,
        "lockbox_policy_id": lockbox_policy_id,
    }
    snapshot_id = canonical_json_hash(identity)
    record = ArchiveSnapshotRecord(
        archive_snapshot_id=snapshot_id,
        layer=layer,
        venue_scope=venue_scope,
        start_ts=start_ts,
        end_ts=end_ts,
        file_manifest_hash=file_manifest_hash,
        coverage_manifest_hash=coverage_manifest_hash,
        quality_manifest_hash=quality_manifest_hash,
        lockbox_policy_id=lockbox_policy_id,
        notes=notes,
        included_file_ids=tuple(sorted(row.file_id for row in files)),
    )
    store.append_archive_snapshot(record)
    return record


def _manifest_dicts(rows: Iterable[FileManifestRow]) -> list[dict[str, Any]]:
    return [
        row.model_dump(
            mode="json",
            exclude={"created_at"},
        )
        for row in rows
    ]
