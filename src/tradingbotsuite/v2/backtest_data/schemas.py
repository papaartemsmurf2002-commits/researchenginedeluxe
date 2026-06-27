# V2-AUDIT-ID: V2-AUD-BTDATA-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md, docs/contracts/validation_contract.md
# V2-BOUNDARY: research_only, no_live_imports, lockbox_enforced
# V2-OWNER: v2_backtest_data
"""Backtest data service request, result, and manifest schemas."""

from __future__ import annotations

import re
from collections.abc import Mapping
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
    instrument_ids: tuple[str, ...] = ()
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

    @model_validator(mode="before")
    @classmethod
    def _normalize_instrument_ids(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        payload = dict(data)
        instrument_id = str(payload.get("instrument_id", "")).strip()
        raw_instrument_ids = payload.get("instrument_ids")
        if raw_instrument_ids is None or raw_instrument_ids == ():
            if instrument_id:
                payload["instrument_ids"] = (instrument_id,)
            return payload
        if isinstance(raw_instrument_ids, str):
            raise ValueError("instrument_ids must be a list of instrument ids")
        normalized: list[str] = []
        for item in raw_instrument_ids:
            text = str(item).strip()
            if not text:
                raise ValueError("instrument_ids must not contain empty values")
            if text not in normalized:
                normalized.append(text)
        if not normalized:
            raise ValueError("instrument_ids must not be empty when provided")
        if not instrument_id:
            payload["instrument_id"] = normalized[0]
        elif instrument_id not in normalized:
            normalized.insert(0, instrument_id)
        payload["instrument_ids"] = tuple(normalized)
        return payload

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
        if not self.instrument_ids:
            raise ValueError("instrument_ids must not be empty")
        if self.instrument_id != self.instrument_ids[0]:
            raise ValueError("instrument_id must match the first instrument_ids entry")
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
    coverage_report_ids: tuple[str, ...] = ()
    source_file_ids: tuple[str, ...]
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    instrument_ids: tuple[str, ...] = ()
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

    @model_validator(mode="before")
    @classmethod
    def _normalize_manifest_instrument_ids(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            return data
        payload = dict(data)
        if not payload.get("instrument_ids") and payload.get("instrument_id"):
            payload["instrument_ids"] = (str(payload["instrument_id"]),)
        if not payload.get("coverage_report_ids") and payload.get("coverage_report_id"):
            payload["coverage_report_ids"] = (str(payload["coverage_report_id"]),)
        return payload

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
        if not self.instrument_ids:
            raise ValueError("instrument_ids must not be empty")
        if self.instrument_id != self.instrument_ids[0]:
            raise ValueError("instrument_id must match the first instrument_ids entry")
        if not self.coverage_report_ids:
            raise ValueError("coverage_report_ids must not be empty")
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
    coverage_report_ids: tuple[str, ...] = ()
    loaded_fields: tuple[str, ...]
    warmup_row_count: int = Field(ge=0)
    reported_row_count: int = Field(ge=0)

    @model_validator(mode="after")
    def _validate_slice(self) -> "BacktestDataSlice":
        if len(self.rows) != self.warmup_row_count + self.reported_row_count:
            raise ValueError("slice row count must match warmup + reported counts")
        return self
