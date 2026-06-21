# V2-AUDIT-ID: V2-AUD-ARCH-002
# V2-CONTRACTS: docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, raw_append_only, no_live_imports
# V2-OWNER: v2_archive
"""Raw JSONL.zst writer for the v2 archive."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa

from tradingbotsuite.v2.archive.hashing import canonical_json_bytes, file_sha256
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, FileManifestRow, IngestionRunRecord
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION


class RawJsonlZstdWriter:
    def __init__(self, layout: ArchiveLayout, store: ArchiveManifestStore) -> None:
        self.layout = layout
        self.store = store
        self._codec = pa.Codec("zstd")

    def write_records(
        self,
        *,
        records: Iterable[Mapping[str, Any]],
        venue: str,
        datatype: str,
        date: str,
        run_id: str,
        job_id: str,
        adapter_id: str,
        source_endpoint_or_subscription: str,
        symbols: tuple[str, ...],
        start_ts: datetime,
        end_ts: datetime,
        instrument_id: str | None = None,
        timeframe: str | None = None,
        hour: int | None = None,
        filename: str = "payload",
        schema_version: str = V2_SCHEMA_VERSION,
    ) -> FileManifestRow:
        materialized = [dict(record) for record in records]
        payload = b"".join(canonical_json_bytes(record) + b"\n" for record in materialized)
        path = self.layout.raw_file_path(
            venue=venue,
            datatype=datatype,
            date=date,
            run_id=run_id,
            filename=filename,
            interval=timeframe,
            instrument_id=instrument_id,
            hour=hour,
        )
        if path.exists():
            raise FileExistsError(f"raw archive file already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        compressed = self._codec.compress(payload)
        path.write_bytes(bytes(compressed))
        sha256 = file_sha256(path)
        relative_path = self.layout.relative_to_root(path)
        manifest_row = FileManifestRow(
            file_id=sha256,
            path=relative_path,
            layer=ArchiveLayer.RAW,
            venue=venue,
            datatype=datatype,
            instrument_id=instrument_id,
            timeframe=timeframe,
            date=date,
            hour=hour,
            sha256=sha256,
            size_bytes=path.stat().st_size,
            uncompressed_size_bytes=len(payload),
            row_count=len(materialized),
            schema_version=schema_version,
            source_file_ids=(),
            created_by_job_id=job_id,
        )
        self.store.upsert_file_manifest(manifest_row)
        self.store.append_ingestion_run(
            IngestionRunRecord(
                ingestion_run_id=run_id,
                job_id=job_id,
                adapter_id=adapter_id,
                venue=venue,
                datatype=datatype,
                source_endpoint_or_subscription=source_endpoint_or_subscription,
                symbols=symbols,
                start_ts=start_ts,
                end_ts=end_ts,
                row_count=len(materialized),
                byte_count=path.stat().st_size,
                schema_version=schema_version,
            )
        )
        return manifest_row


def read_jsonl_zstd(path: str | Path, *, uncompressed_size: int) -> list[dict[str, Any]]:
    import json

    codec = pa.Codec("zstd")
    compressed = Path(path).read_bytes()
    payload = bytes(codec.decompress(compressed, decompressed_size=uncompressed_size))
    if not payload:
        return []
    return [json.loads(line) for line in payload.decode("utf-8").splitlines() if line]
