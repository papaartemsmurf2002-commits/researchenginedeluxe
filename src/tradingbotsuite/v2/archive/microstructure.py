# V2-AUDIT-ID: V2-AUD-ARCH-005
# V2-CONTRACTS: docs/contracts/archive_contract.md, docs/contracts/collector_job_contract.md
# V2-BOUNDARY: research_only, raw_microstructure_archive, no_live_imports
# V2-OWNER: v2_archive
"""Microstructure archive schemas and storage policy helpers."""

from __future__ import annotations

import shutil
import re
from collections.abc import Iterable, Mapping
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, file_sha256
from tradingbotsuite.v2.archive.layout import ArchiveLayout
from tradingbotsuite.v2.archive.manifest_store import ArchiveManifestStore
from tradingbotsuite.v2.archive.raw_writer import RawJsonlZstdWriter
from tradingbotsuite.v2.archive.schemas import ArchiveLayer, FileManifestRow, IngestionRunRecord
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc, utc_isoformat, utc_now


class MicrostructureDataType(str, Enum):
    TRADES = "trades"
    BBO = "bbo"
    L2 = "l2"
    OFFICIAL_S3 = "official_s3"


SECRET_OR_LOCAL_STATE_SOURCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(^|[._-])env($|[._-])", re.IGNORECASE),
    re.compile(r"(secret|credential|private|token|apikey|api_key)", re.IGNORECASE),
    re.compile(r"\.(pem|key|p12|pfx|sqlite|sqlite3|db|env)$", re.IGNORECASE),
)


class TradeEventRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    ts: datetime
    instrument_id: str = Field(min_length=1)
    event_type: Literal["trade"]
    sequence: int = Field(default=0, ge=0)
    price: float = Field(gt=0)
    size: float = Field(gt=0)
    side: str | None = None
    trade_id: str | None = None
    source: str = "fixture"
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _boundary(self) -> "TradeEventRow":
        _require_research_boundary(self.research_only, self.observe_only, self.promotion_ready)
        ensure_utc(self.ts)
        return self


class BBOEventRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    ts: datetime
    instrument_id: str = Field(min_length=1)
    event_type: Literal["bbo"]
    sequence: int = Field(default=0, ge=0)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    bid_size: float | None = Field(default=None, ge=0)
    ask_size: float | None = Field(default=None, ge=0)
    source: str = "fixture"
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_bbo(self) -> "BBOEventRow":
        _require_research_boundary(self.research_only, self.observe_only, self.promotion_ready)
        ensure_utc(self.ts)
        if self.ask < self.bid:
            raise ValueError("bbo ask must be >= bid")
        return self


class L2BookSnapshotRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    ts: datetime
    instrument_id: str = Field(min_length=1)
    event_type: Literal["l2"]
    sequence: int = Field(default=0, ge=0)
    bid_depth: float = Field(ge=0)
    ask_depth: float = Field(ge=0)
    book_levels: int | None = Field(default=None, ge=0)
    source: str = "fixture"
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_l2(self) -> "L2BookSnapshotRow":
        _require_research_boundary(self.research_only, self.observe_only, self.promotion_ready)
        ensure_utc(self.ts)
        return self


class MicrostructureQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    quality_report_id: str = Field(min_length=64, max_length=64)
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    datatype: MicrostructureDataType
    start_ts: datetime
    end_ts: datetime
    first_event_ts: datetime | None = None
    last_event_ts: datetime | None = None
    row_count: int = Field(ge=0)
    gap_count: int = Field(default=0, ge=0)
    reconnect_attempts: int = Field(default=0, ge=0)
    quality_status: str = Field(min_length=1)
    warnings: tuple[str, ...] = ()
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> "MicrostructureQualityReport":
        _require_research_boundary(self.research_only, self.observe_only, self.promotion_ready)
        if ensure_utc(self.end_ts) < ensure_utc(self.start_ts):
            raise ValueError("end_ts must be >= start_ts")
        return self


class StorageFileSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)


class StorageBudgetReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    storage_report_id: str = Field(min_length=64, max_length=64)
    archive_root: str = Field(min_length=1)
    max_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    file_count: int = Field(ge=0)
    layer_bytes: dict[str, int]
    largest_files: tuple[StorageFileSummary, ...] = ()
    within_budget: bool
    usage_ratio: float = Field(ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> "StorageBudgetReport":
        _require_research_boundary(self.research_only, self.observe_only, self.promotion_ready)
        return self


class RetentionBackupPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_id: str = Field(min_length=64, max_length=64)
    retention_days: int = Field(ge=1)
    backup_target: str = Field(min_length=1)
    scope: str = "raw_microstructure"
    enforcement_mode: Literal["record_only"] = "record_only"
    deletion_authorized: bool = False
    backup_transfer_authorized: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    schema_version: str = V2_SCHEMA_VERSION
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> "RetentionBackupPolicyRecord":
        _require_research_boundary(self.research_only, self.observe_only, self.promotion_ready)
        if self.deletion_authorized or self.backup_transfer_authorized:
            raise ValueError("retention/backup policy records cannot authorize deletion or transfer")
        return self


class MicrostructureCaptureResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_file: FileManifestRow
    quality_report: MicrostructureQualityReport
    storage_report: StorageBudgetReport
    normalized_rows: tuple[dict[str, Any], ...]


def normalize_microstructure_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    datatype: MicrostructureDataType | str,
) -> tuple[dict[str, Any], ...]:
    parsed_type = parse_microstructure_datatype(datatype)
    model_by_type = {
        MicrostructureDataType.TRADES: TradeEventRow,
        MicrostructureDataType.BBO: BBOEventRow,
        MicrostructureDataType.L2: L2BookSnapshotRow,
    }
    if parsed_type not in model_by_type:
        raise ValueError(f"datatype {parsed_type.value} does not contain microstructure event rows")
    materialized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if "event_type" not in row:
            raise ValueError(f"microstructure row {index} missing event_type")
        try:
            parsed = model_by_type[parsed_type].model_validate(dict(row))
        except Exception as exc:
            raise ValueError(f"invalid_{parsed_type.value}_row:{index}:{exc}") from exc
        normalized = parsed.model_dump(mode="json")
        materialized.append(normalized)
    if not materialized:
        raise ValueError("microstructure_capture_rows_required")
    return tuple(
        sorted(
            materialized,
            key=lambda item: (item["ts"], item["instrument_id"], int(item.get("sequence", 0))),
        )
    )


def write_microstructure_raw_capture(
    *,
    archive_root: str | Path,
    records: Iterable[Mapping[str, Any]],
    venue: str,
    datatype: MicrostructureDataType | str,
    date: str,
    run_id: str,
    job_id: str,
    adapter_id: str,
    source_endpoint_or_subscription: str,
    instrument_id: str,
    start_ts: datetime,
    end_ts: datetime,
    storage_budget_bytes: int,
    reconnect_attempts: int = 0,
    gap_count: int = 0,
) -> MicrostructureCaptureResult:
    parsed_type = parse_microstructure_datatype(datatype)
    normalized = normalize_microstructure_rows(records, datatype=parsed_type)
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    raw_file = RawJsonlZstdWriter(layout, store).write_records(
        records=normalized,
        venue=venue,
        datatype=parsed_type.value,
        date=date,
        run_id=run_id,
        job_id=job_id,
        adapter_id=adapter_id,
        source_endpoint_or_subscription=source_endpoint_or_subscription,
        symbols=(instrument_id,),
        start_ts=start_ts,
        end_ts=end_ts,
        instrument_id=instrument_id,
    )
    quality_report = build_microstructure_quality_report(
        records=normalized,
        venue=venue,
        instrument_id=instrument_id,
        datatype=parsed_type,
        start_ts=start_ts,
        end_ts=end_ts,
        reconnect_attempts=reconnect_attempts,
        gap_count=gap_count,
    )
    _write_json_manifest(
        layout.resolve("manifests", "microstructure_quality_reports", f"{quality_report.quality_report_id}.json"),
        quality_report.model_dump(mode="json"),
    )
    storage_report = write_storage_budget_report(
        layout,
        build_storage_budget_report(layout, max_bytes=storage_budget_bytes),
    )
    return MicrostructureCaptureResult(
        raw_file=raw_file,
        quality_report=quality_report,
        storage_report=storage_report,
        normalized_rows=normalized,
    )


def preserve_official_s3_backfill_file(
    *,
    archive_root: str | Path,
    source_file: str | Path,
    trusted_source_root: str | Path,
    venue: str,
    date: str,
    run_id: str,
    job_id: str,
    adapter_id: str,
    source_endpoint_or_subscription: str,
    instrument_id: str | None,
    start_ts: datetime,
    end_ts: datetime,
    storage_budget_bytes: int,
    row_count: int = 0,
    filename: str | None = None,
) -> tuple[FileManifestRow, StorageBudgetReport]:
    source_path = _resolve_trusted_official_source(source_file, trusted_source_root=trusted_source_root)
    if not source_path.is_file():
        raise FileNotFoundError(f"official S3 backfill source file not found: {source_path}")
    layout = ArchiveLayout(archive_root)
    layout.initialize()
    store = ArchiveManifestStore(layout)
    target_name = filename or source_path.name
    target = layout.raw_native_file_path(
        venue=venue,
        datatype=MicrostructureDataType.OFFICIAL_S3.value,
        date=date,
        run_id=run_id,
        filename=target_name,
        instrument_id=instrument_id,
    )
    if target.exists():
        raise FileExistsError(f"official raw archive file already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    sha256 = file_sha256(target)
    row = FileManifestRow(
        file_id=sha256,
        path=layout.relative_to_root(target),
        layer=ArchiveLayer.RAW,
        venue=venue,
        datatype=MicrostructureDataType.OFFICIAL_S3.value,
        instrument_id=instrument_id,
        timeframe=None,
        date=date,
        hour=None,
        sha256=sha256,
        size_bytes=target.stat().st_size,
        uncompressed_size_bytes=None,
        row_count=row_count,
        schema_version=V2_SCHEMA_VERSION,
        source_file_ids=(),
        created_by_job_id=job_id,
    )
    store.upsert_file_manifest(row)
    store.append_ingestion_run(
        IngestionRunRecord(
            ingestion_run_id=run_id,
            job_id=job_id,
            adapter_id=adapter_id,
            venue=venue,
            datatype=MicrostructureDataType.OFFICIAL_S3.value,
            source_endpoint_or_subscription=source_endpoint_or_subscription,
            symbols=tuple([instrument_id] if instrument_id else ()),
            start_ts=start_ts,
            end_ts=end_ts,
            row_count=row_count,
            byte_count=target.stat().st_size,
            schema_version=V2_SCHEMA_VERSION,
        )
    )
    storage_report = write_storage_budget_report(
        layout,
        build_storage_budget_report(layout, max_bytes=storage_budget_bytes),
    )
    return row, storage_report


def _resolve_trusted_official_source(source_file: str | Path, *, trusted_source_root: str | Path) -> Path:
    root = Path(trusted_source_root).resolve()
    source_path = Path(source_file)
    resolved = source_path.resolve() if source_path.is_absolute() else (root / source_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("official S3 source_file must stay within trusted_source_root") from exc
    if any(part in {"", ".", ".."} for part in source_path.parts):
        raise ValueError("official S3 source_file must not contain traversal segments")
    name = resolved.name
    if any(pattern.search(name) for pattern in SECRET_OR_LOCAL_STATE_SOURCE_PATTERNS):
        raise ValueError("official S3 source_file looks like secret or local state")
    return resolved


def build_microstructure_quality_report(
    *,
    records: Iterable[Mapping[str, Any]],
    venue: str,
    instrument_id: str,
    datatype: MicrostructureDataType | str,
    start_ts: datetime,
    end_ts: datetime,
    reconnect_attempts: int = 0,
    gap_count: int = 0,
) -> MicrostructureQualityReport:
    parsed_type = parse_microstructure_datatype(datatype)
    materialized = [dict(record) for record in records]
    timestamps = [_parse_datetime(row["ts"]) for row in materialized if "ts" in row]
    warnings: list[str] = []
    if gap_count > 0:
        warnings.append("gap_evidence_recorded")
    if reconnect_attempts > 0:
        warnings.append("reconnect_attempts_recorded")
    if not materialized:
        warnings.append("empty_microstructure_capture")
    quality_status = "gap_evidence" if warnings else "ok"
    payload = {
        "venue": venue,
        "instrument_id": instrument_id,
        "datatype": parsed_type.value,
        "start_ts": utc_isoformat(start_ts),
        "end_ts": utc_isoformat(end_ts),
        "row_count": len(materialized),
        "gap_count": gap_count,
        "reconnect_attempts": reconnect_attempts,
        "warnings": tuple(warnings),
        "schema_version": V2_SCHEMA_VERSION,
    }
    return MicrostructureQualityReport(
        quality_report_id=canonical_json_hash(payload),
        venue=venue,
        instrument_id=instrument_id,
        datatype=parsed_type,
        start_ts=start_ts,
        end_ts=end_ts,
        first_event_ts=min(timestamps) if timestamps else None,
        last_event_ts=max(timestamps) if timestamps else None,
        row_count=len(materialized),
        gap_count=gap_count,
        reconnect_attempts=reconnect_attempts,
        quality_status=quality_status,
        warnings=tuple(warnings),
    )


def build_storage_budget_report(layout: ArchiveLayout, *, max_bytes: int) -> StorageBudgetReport:
    root = layout.root.resolve(strict=False)
    files: list[StorageFileSummary] = []
    layer_bytes: dict[str, int] = {}
    if root.exists():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            size = path.stat().st_size
            relative = path.relative_to(root).as_posix()
            files.append(StorageFileSummary(path=relative, size_bytes=size))
            layer = relative.split("/", 1)[0] if "/" in relative else "root"
            layer_bytes[layer] = layer_bytes.get(layer, 0) + size
    total_bytes = sum(item.size_bytes for item in files)
    usage_ratio = float(total_bytes / max_bytes) if max_bytes > 0 else (0.0 if total_bytes == 0 else 1.0)
    largest = tuple(sorted(files, key=lambda item: (-item.size_bytes, item.path))[:10])
    payload = {
        "archive_root": root.as_posix(),
        "max_bytes": max_bytes,
        "total_bytes": total_bytes,
        "file_count": len(files),
        "layer_bytes": layer_bytes,
        "largest_files": [item.model_dump(mode="json") for item in largest],
        "schema_version": V2_SCHEMA_VERSION,
    }
    return StorageBudgetReport(
        storage_report_id=canonical_json_hash(payload),
        archive_root=root.as_posix(),
        max_bytes=max_bytes,
        total_bytes=total_bytes,
        file_count=len(files),
        layer_bytes=layer_bytes,
        largest_files=largest,
        within_budget=total_bytes <= max_bytes,
        usage_ratio=usage_ratio,
    )


def write_storage_budget_report(layout: ArchiveLayout, report: StorageBudgetReport) -> StorageBudgetReport:
    _write_json_manifest(
        layout.resolve("manifests", "storage_budget_reports", f"{report.storage_report_id}.json"),
        report.model_dump(mode="json"),
    )
    return report


def build_retention_backup_policy(
    *,
    retention_days: int,
    backup_target: str,
    scope: str = "raw_microstructure",
) -> RetentionBackupPolicyRecord:
    payload = {
        "retention_days": retention_days,
        "backup_target": backup_target,
        "scope": scope,
        "enforcement_mode": "record_only",
        "deletion_authorized": False,
        "backup_transfer_authorized": False,
        "schema_version": V2_SCHEMA_VERSION,
    }
    return RetentionBackupPolicyRecord(
        policy_id=canonical_json_hash(payload),
        retention_days=retention_days,
        backup_target=backup_target,
        scope=scope,
    )


def record_retention_backup_policy(
    layout: ArchiveLayout,
    policy: RetentionBackupPolicyRecord,
) -> Path:
    path = layout.resolve("manifests", "retention_backup_policies", f"{policy.policy_id}.json")
    _write_json_manifest(path, policy.model_dump(mode="json"))
    return path


def parse_microstructure_datatype(datatype: MicrostructureDataType | str) -> MicrostructureDataType:
    if isinstance(datatype, MicrostructureDataType):
        return datatype
    if str(datatype) == "trade":
        return MicrostructureDataType.TRADES
    return MicrostructureDataType(str(datatype))


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return ensure_utc(value)
    if isinstance(value, str):
        return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    raise ValueError(f"unsupported timestamp value: {value!r}")


def _require_research_boundary(research_only: bool, observe_only: bool, promotion_ready: bool) -> None:
    if not research_only or not observe_only or promotion_ready:
        raise ValueError("microstructure archive records must preserve the v2 research boundary")


def _write_json_manifest(path: Path, payload: Mapping[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
