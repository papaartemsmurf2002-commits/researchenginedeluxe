# V2-AUDIT-ID: V2-AUD-ARCH-004
# V2-CONTRACTS: docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, normalization_manifests, no_live_imports
# V2-OWNER: v2_archive
"""Parquet-backed normalization manifest store."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.market_data import NormalizationManifestRow

ModelT = TypeVar("ModelT", bound=BaseModel)


class NormalizationManifestStore:
    def __init__(self, layout: ArchiveLayout) -> None:
        self.layout = layout

    @property
    def normalization_manifest_path(self) -> Path:
        return self.layout.resolve("manifests", "normalization_manifests.parquet")

    def append(self, row: NormalizationManifestRow) -> None:
        records = [
            existing
            for existing in self.load()
            if existing.normalization_manifest_id != row.normalization_manifest_id
        ]
        records.append(row)
        records.sort(
            key=lambda item: (
                item.venue,
                item.dataset,
                item.instrument_id or "",
                item.timeframe or "",
                item.source_file_id,
                item.output_file_id or "",
            )
        )
        _write_models(self.normalization_manifest_path, records)

    def extend(self, rows: Iterable[NormalizationManifestRow]) -> None:
        for row in rows:
            self.append(row)

    def load(self) -> list[NormalizationManifestRow]:
        return _read_models(self.normalization_manifest_path, NormalizationManifestRow)


def _read_models(path: Path, model: type[ModelT]) -> list[ModelT]:
    if not path.exists():
        return []
    return [model.model_validate(row) for row in pq.read_table(path).to_pylist()]


def _write_models(path: Path, records: Iterable[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist([record.model_dump(mode="json") for record in records]),
        path,
        compression="zstd",
    )
