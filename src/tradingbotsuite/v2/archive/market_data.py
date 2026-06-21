# V2-AUDIT-ID: V2-AUD-ARCH-004
# V2-CONTRACTS: docs/contracts/archive_contract.md, docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, market_data_normalization, no_live_imports
# V2-OWNER: v2_archive
"""Market-data row schemas and normalization manifest records."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.schemas import ArchiveLayer
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now


class BronzeCandleRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    ts: datetime
    end_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(ge=0)
    trade_count: int | None = Field(default=None, ge=0)
    raw_file_id: str = Field(min_length=64, max_length=64)
    source_sequence: int = Field(ge=0)
    parse_warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_candle(self) -> "BronzeCandleRow":
        if self.end_ts <= self.ts:
            raise ValueError("end_ts must be greater than ts")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low cannot exceed open/high/close")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high cannot be below open/low/close")
        return self


class SilverBarRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    ts: datetime
    end_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(ge=0)
    trade_count: int | None = Field(default=None, ge=0)
    source_timeframe: str = Field(min_length=1)
    source_file_id: str = Field(min_length=64, max_length=64)
    source_layer: ArchiveLayer = ArchiveLayer.BRONZE
    normalization_warnings: tuple[str, ...] = ()
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_bar(self) -> "SilverBarRow":
        if self.end_ts <= self.ts:
            raise ValueError("end_ts must be greater than ts")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low cannot exceed open/high/close")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high cannot be below open/low/close")
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("silver bars must preserve the v2 research boundary")
        return self


class BronzeFundingRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    ts: datetime
    end_ts: datetime
    funding_rate: float
    raw_file_id: str = Field(min_length=64, max_length=64)
    source_sequence: int = Field(ge=0)
    parse_warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_funding(self) -> "BronzeFundingRow":
        if self.end_ts <= self.ts:
            raise ValueError("end_ts must be greater than ts")
        return self


class SilverFundingIntervalRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    interval_start_ts: datetime
    interval_end_ts: datetime
    funding_rate: float
    source_file_id: str = Field(min_length=64, max_length=64)
    source_layer: ArchiveLayer = ArchiveLayer.BRONZE
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_interval(self) -> "SilverFundingIntervalRow":
        if self.interval_end_ts <= self.interval_start_ts:
            raise ValueError("interval_end_ts must be greater than interval_start_ts")
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("silver funding intervals must preserve the v2 research boundary")
        return self


class BronzeAssetContextRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    ts: datetime
    mark_price: float | None = None
    oracle_price: float | None = None
    open_interest: float | None = Field(default=None, ge=0)
    day_notional_volume_usd: float | None = Field(default=None, ge=0)
    funding_rate: float | None = None
    raw_file_id: str = Field(min_length=64, max_length=64)
    source_sequence: int = Field(ge=0)
    parse_warnings: tuple[str, ...] = ()


class SilverAssetContextRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    venue: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    ts: datetime
    mark_price: float | None = None
    oracle_price: float | None = None
    open_interest: float | None = Field(default=None, ge=0)
    day_notional_volume_usd: float | None = Field(default=None, ge=0)
    funding_rate: float | None = None
    source_file_id: str = Field(min_length=64, max_length=64)
    source_layer: ArchiveLayer = ArchiveLayer.BRONZE
    missing_fields: tuple[str, ...] = ()
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_context(self) -> "SilverAssetContextRow":
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("silver context rows must preserve the v2 research boundary")
        return self


class NormalizationManifestRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    normalization_manifest_id: str = Field(min_length=64, max_length=64)
    schema_version: str = V2_SCHEMA_VERSION
    created_at: datetime = Field(default_factory=utc_now)
    source_file_id: str = Field(min_length=64, max_length=64)
    output_file_id: str | None = Field(default=None, min_length=64, max_length=64)
    source_layer: ArchiveLayer
    output_layer: ArchiveLayer
    dataset: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    instrument_id: str | None = None
    timeframe: str | None = None
    row_count_in: int = Field(ge=0)
    row_count_out: int = Field(ge=0)
    dropped_rows: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    gap_reasons: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    status: str = "succeeded"
    research_only: bool = True
    observe_only: bool = True
    promotion_ready: bool = False

    @model_validator(mode="after")
    def _validate_manifest(self) -> "NormalizationManifestRow":
        if not self.research_only or not self.observe_only or self.promotion_ready:
            raise ValueError("normalization manifests must preserve the v2 research boundary")
        return self
