# V2-AUDIT-ID: V2-AUD-ARCH-002
# V2-CONTRACTS: docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, manifest_identity, no_live_imports
# V2-OWNER: v2_archive
"""Parquet-backed manifest store for the v2 archive."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.schemas import (
    ArchiveSnapshotRecord,
    ArchiveValidationIssue,
    FileManifestRow,
    IngestionRunRecord,
)
from tradingbotsuite.v2.archive.hashing import file_sha256

ModelT = TypeVar("ModelT", bound=BaseModel)


class ArchiveManifestStore:
    def __init__(self, layout: ArchiveLayout) -> None:
        self.layout = layout

    @property
    def file_manifest_path(self) -> Path:
        return self.layout.resolve("manifests", "file_manifest.parquet")

    @property
    def ingestion_runs_path(self) -> Path:
        return self.layout.resolve("manifests", "ingestion_runs.parquet")

    @property
    def archive_snapshots_path(self) -> Path:
        return self.layout.resolve("manifests", "archive_snapshots.parquet")

    def append_ingestion_run(self, record: IngestionRunRecord) -> None:
        records = self.load_ingestion_runs()
        records.append(record)
        self._write_models(self.ingestion_runs_path, records)

    def upsert_file_manifest(self, row: FileManifestRow) -> None:
        records = [record for record in self.load_file_manifest() if record.file_id != row.file_id]
        records.append(row)
        records.sort(key=lambda item: (item.layer.value, item.path, item.file_id))
        self._write_models(self.file_manifest_path, records)

    def append_archive_snapshot(self, record: ArchiveSnapshotRecord) -> None:
        records = self.load_archive_snapshots()
        if not any(existing.archive_snapshot_id == record.archive_snapshot_id for existing in records):
            records.append(record)
            records.sort(key=lambda item: (item.layer.value, item.archive_snapshot_id))
            self._write_models(self.archive_snapshots_path, records)

    def load_file_manifest(self) -> list[FileManifestRow]:
        return self._read_models(self.file_manifest_path, FileManifestRow)

    def load_ingestion_runs(self) -> list[IngestionRunRecord]:
        return self._read_models(self.ingestion_runs_path, IngestionRunRecord)

    def load_archive_snapshots(self) -> list[ArchiveSnapshotRecord]:
        return self._read_models(self.archive_snapshots_path, ArchiveSnapshotRecord)

    def validate_files(self) -> list[ArchiveValidationIssue]:
        issues: list[ArchiveValidationIssue] = []
        for row in self.load_file_manifest():
            path = self.layout.resolve(row.path)
            if not path.exists():
                issues.append(
                    ArchiveValidationIssue(
                        code="manifest_file_missing",
                        path=row.path,
                        message="file_manifest row points to a missing file",
                    )
                )
                continue
            if path.stat().st_size != row.size_bytes:
                issues.append(
                    ArchiveValidationIssue(
                        code="manifest_size_mismatch",
                        path=row.path,
                        message="file size does not match file_manifest",
                    )
                )
            if file_sha256(path) != row.sha256:
                issues.append(
                    ArchiveValidationIssue(
                        code="manifest_sha256_mismatch",
                        path=row.path,
                        message="file SHA-256 does not match file_manifest",
                    )
                )
        return issues

    def _read_models(self, path: Path, model: type[ModelT]) -> list[ModelT]:
        if not path.exists():
            return []
        table = pq.read_table(path)
        return [model.model_validate(row) for row in table.to_pylist()]

    def _write_models(self, path: Path, records: Iterable[BaseModel]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [_model_row(record) for record in records]
        table = pa.Table.from_pylist(rows)
        pq.write_table(table, path, compression="zstd")


def _model_row(record: BaseModel) -> dict[str, Any]:
    return record.model_dump(mode="json")
