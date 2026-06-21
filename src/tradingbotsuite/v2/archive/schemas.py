# V2-AUDIT-ID: V2-AUD-ARCH-001
# V2-CONTRACTS: docs/contracts/archive_contract.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_archive
"""Archive schema skeletons for v2."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.config.defaults import DEFAULT_ARCHIVE_ROOT
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now


class ArchiveLayer(str, Enum):
    RAW = "raw"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class ArchiveConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    archive_root: str = DEFAULT_ARCHIVE_ROOT
    layers: tuple[ArchiveLayer, ...] = (
        ArchiveLayer.RAW,
        ArchiveLayer.BRONZE,
        ArchiveLayer.SILVER,
        ArchiveLayer.GOLD,
    )
    hash_algorithm: str = "sha256"


class ArchiveSnapshotRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(min_length=1)
    manifest_hash: str = Field(min_length=64, max_length=64)
    archive_root: str = DEFAULT_ARCHIVE_ROOT


class IngestionRunRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    ingestion_run_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    adapter_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    datatype: str = Field(min_length=1)
    source_endpoint_or_subscription: str = Field(min_length=1)
    symbols: tuple[str, ...]
    start_ts: datetime
    end_ts: datetime
    ingested_at: datetime = Field(default_factory=utc_now)
    status: str = "success"
    row_count: int = Field(ge=0)
    byte_count: int = Field(ge=0)
    schema_version: str = V2_SCHEMA_VERSION
    error_summary: str | None = None
    retry_count: int = Field(default=0, ge=0)
    gap_status: str = "none"

    @model_validator(mode="after")
    def _window_order(self) -> "IngestionRunRecord":
        if self.end_ts < self.start_ts:
            raise ValueError("end_ts must be >= start_ts")
        return self


class FileManifestRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    file_id: str = Field(min_length=64, max_length=64)
    path: str = Field(min_length=1)
    layer: ArchiveLayer
    venue: str = Field(min_length=1)
    datatype: str = Field(min_length=1)
    instrument_id: str | None = None
    timeframe: str | None = None
    date: str | None = None
    hour: int | None = Field(default=None, ge=0, le=23)
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    uncompressed_size_bytes: int | None = Field(default=None, ge=0)
    row_count: int | None = Field(default=None, ge=0)
    schema_version: str = V2_SCHEMA_VERSION
    source_file_ids: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
    created_by_job_id: str = Field(min_length=1)


class ArchiveSnapshotRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    created_at: datetime = Field(default_factory=utc_now)
    layer: ArchiveLayer
    venue_scope: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    file_manifest_hash: str = Field(min_length=64, max_length=64)
    coverage_manifest_hash: str = Field(min_length=64, max_length=64)
    quality_manifest_hash: str = Field(min_length=64, max_length=64)
    lockbox_policy_id: str | None = None
    notes: str | None = None
    included_file_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _window_order(self) -> "ArchiveSnapshotRecord":
        if self.end_ts < self.start_ts:
            raise ValueError("end_ts must be >= start_ts")
        return self


class ArchiveValidationIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1)
    path: str = Field(min_length=1)
    message: str = Field(min_length=1)
