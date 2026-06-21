# V2-AUDIT-ID: V2-AUD-BTDATA-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md, docs/contracts/validation_contract.md
# V2-BOUNDARY: research_only, no_live_imports, lockbox_enforced
# V2-OWNER: v2_backtest_data
"""Backtest data service request, result, and manifest schemas."""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.security.boundary import require_research_boundary
from tradingbotsuite.v2.validation.policies import ValidationConfig

_FIELD_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class BacktestEvidenceMode(str, Enum):
    ACCEPTED_RESEARCH = "accepted_research"
    REPORTED_EVIDENCE = "reported_evidence"
    SANDBOX_DIAGNOSTIC = "sandbox_diagnostic"


EVIDENCE_MODES = {
    BacktestEvidenceMode.ACCEPTED_RESEARCH,
    BacktestEvidenceMode.REPORTED_EVIDENCE,
}


class BacktestDataRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    archive_root: str = Field(min_length=1)
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    family: str = Field(default="bars", min_length=1)
    timeframe: str = Field(min_length=1)
    start_ts: datetime
    end_ts: datetime
    warmup_start_ts: datetime | None = None
    requested_fields: tuple[str, ...] = (
        "ts",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )
    evidence_mode: BacktestEvidenceMode = BacktestEvidenceMode.ACCEPTED_RESEARCH
    exclude_lockbox: bool = True
    validation_config: ValidationConfig = Field(default_factory=ValidationConfig)
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

    @field_validator("start_ts", "end_ts", "warmup_start_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @field_validator("requested_fields")
    @classmethod
    def _requested_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("requested_fields must not be empty")
        seen: set[str] = set()
        normalized: list[str] = []
        for field in value:
            if not _FIELD_NAME_RE.fullmatch(field):
                raise ValueError(f"unsupported requested field name: {field!r}")
            if field not in seen:
                normalized.append(field)
                seen.add(field)
        return tuple(normalized)

    @model_validator(mode="after")
    def _validate_request(self) -> "BacktestDataRequest":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if self.warmup_start_ts is not None and self.warmup_start_ts > self.start_ts:
            raise ValueError("warmup_start_ts must be <= start_ts")
        require_research_boundary(self, context="backtest data request")
        return self


class BacktestDataManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_manifest_id: str = Field(min_length=64, max_length=64)
    schema_version: str = V2_SCHEMA_VERSION
    request_hash: str = Field(min_length=64, max_length=64)
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    coverage_report_id: str = Field(min_length=64, max_length=64)
    source_file_ids: tuple[str, ...]
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    family: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    evidence_mode: BacktestEvidenceMode
    loaded_fields: tuple[str, ...]
    start_ts: datetime
    end_ts: datetime
    warmup_start_ts: datetime | None = None
    lockbox_start_ts: datetime | None = None
    lockbox_end_ts: datetime | None = None
    coverage_ratio: float = Field(ge=0.0, le=1.0)
    coverage_min: float = Field(ge=0.0, le=1.0)
    row_count: int = Field(ge=0)
    warmup_row_count: int = Field(ge=0)
    reported_row_count: int = Field(ge=0)
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

    @field_validator(
        "start_ts",
        "end_ts",
        "warmup_start_ts",
        "lockbox_start_ts",
        "lockbox_end_ts",
    )
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_manifest(self) -> "BacktestDataManifest":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be greater than start_ts")
        if self.warmup_row_count + self.reported_row_count != self.row_count:
            raise ValueError("warmup_row_count + reported_row_count must equal row_count")
        require_research_boundary(self, context="backtest data manifest")
        return self


class BacktestDataSlice(BaseModel):
    model_config = ConfigDict(frozen=True)

    request: BacktestDataRequest
    rows: tuple[dict[str, Any], ...]
    data_manifest: BacktestDataManifest
    archive_snapshot_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_id: str = Field(min_length=64, max_length=64)
    coverage_report_id: str = Field(min_length=64, max_length=64)
    loaded_fields: tuple[str, ...]
    warmup_row_count: int = Field(ge=0)
    reported_row_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_slice(self) -> "BacktestDataSlice":
        if len(self.rows) != self.warmup_row_count + self.reported_row_count:
            raise ValueError("slice row count must match warmup + reported counts")
        return self
