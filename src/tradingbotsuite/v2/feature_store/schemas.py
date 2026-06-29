# V2-AUDIT-ID: V2-AUD-DATASRC-060
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, feature_catalog, no_live_imports, no_archive_writes
# V2-OWNER: v2_feature_store
"""Read-only feature-store catalog schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import ensure_utc
from tradingbotsuite.v2.security.boundary import require_research_boundary


class FeatureCatalogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    feature_catalog_id: str = Field(min_length=64, max_length=64)
    feature_family: str = Field(min_length=1)
    source_family: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    timeframe: str | None = None
    start_ts: datetime | None = None
    end_ts: datetime | None = None
    row_count: int = Field(ge=0)
    input_row_count: int = Field(ge=0)
    output_format: str = Field(min_length=1)
    output_ref: str = Field(min_length=1)
    output_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    output_part_refs: tuple[str, ...] = ()
    materialization_report_id: str = Field(min_length=1)
    materialization_report_ref: str = Field(min_length=1)
    evidence_scope: str = "feature_materialization"
    accepted_research_evidence_allowed: bool = False
    usable_archive_ref: str = Field(min_length=1)
    blocker_reasons: tuple[str, ...] = ()
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

    @field_validator("start_ts", "end_ts")
    @classmethod
    def _utc_timestamps(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    @model_validator(mode="after")
    def _validate_entry(self) -> "FeatureCatalogEntry":
        if self.start_ts is not None and self.end_ts is not None and self.end_ts <= self.start_ts:
            raise ValueError("feature catalog end_ts must be greater than start_ts")
        require_research_boundary(self, context="feature catalog entry")
        return self


class FeatureCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    catalog_id: str = Field(min_length=64, max_length=64)
    entries: tuple[FeatureCatalogEntry, ...] = ()
    feature_families: tuple[str, ...] = ()
    source_families: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    entry_count: int = Field(ge=0)
    total_feature_rows: int = Field(ge=0)
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

    @model_validator(mode="after")
    def _validate_catalog(self) -> "FeatureCatalog":
        if self.entry_count != len(self.entries):
            raise ValueError("entry_count must equal entries length")
        if self.total_feature_rows != sum(entry.row_count for entry in self.entries):
            raise ValueError("total_feature_rows must match entries")
        require_research_boundary(self, context="feature catalog")
        return self
