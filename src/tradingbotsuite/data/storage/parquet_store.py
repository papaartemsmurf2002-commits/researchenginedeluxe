from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


@dataclass(frozen=True, slots=True)
class ParquetWriteResult:
    data_path: Path
    content_hash: str
    row_count: int
    storage_layout: str


class PartitionedParquetStore:
    storage_layout = "source=<source>/family=<family>/symbol=<symbol>/date=<YYYY-MM-DD>/part-000.parquet"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def write_records(
        self,
        *,
        source_name: str,
        data_family: str,
        symbol: str,
        records: list[Mapping[str, Any]],
        event_time_field: str,
    ) -> ParquetWriteResult:
        if not records:
            raise ValueError("records must not be empty")
        if event_time_field not in records[0]:
            raise ValueError(f"event_time_field {event_time_field} is missing from records")
        first_event_time_ms = int(records[0][event_time_field])
        date_part = datetime.fromtimestamp(first_event_time_ms / 1000, tz=UTC).date().isoformat()
        output_dir = (
            self.root
            / f"source={source_name}"
            / f"family={data_family}"
            / f"symbol={symbol.strip().upper()}"
            / f"date={date_part}"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        data_path = output_dir / "part-000.parquet"
        frame = pd.DataFrame([dict(record) for record in records])
        frame.to_parquet(data_path, index=False)
        return ParquetWriteResult(
            data_path=data_path,
            content_hash=f"sha256:{_hash_file(data_path)}",
            row_count=len(records),
            storage_layout=self.storage_layout,
        )


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
