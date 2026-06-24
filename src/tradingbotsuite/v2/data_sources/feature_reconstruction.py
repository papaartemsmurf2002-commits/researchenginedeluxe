# V2-AUDIT-ID: V2-AUD-DATASRC-038
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, no_archive_writes, no_gold_panel_claim
# V2-OWNER: v2_data_sources
"""Feature reconstruction helpers for v2 market-data research panels."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.data_sources.bar_reconstruction import TradeBarInputRow
from tradingbotsuite.v2.data_sources.schemas import CoverageLabel
from tradingbotsuite.v2.security.boundary import require_research_boundary


class OrderflowFeatureRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_ids: tuple[str, ...] = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    coverage_label: CoverageLabel
    bucket_seconds: int = Field(ge=1)
    bucket_start_ms: int = Field(ge=0)
    bucket_end_ms: int = Field(ge=0)
    trade_count: int = Field(ge=1)
    total_volume: float = Field(ge=0)
    total_quote_volume: float = Field(ge=0)
    buy_volume: float = Field(ge=0)
    sell_volume: float = Field(ge=0)
    unknown_side_volume: float = Field(ge=0)
    buy_quote_volume: float = Field(ge=0)
    sell_quote_volume: float = Field(ge=0)
    unknown_side_quote_volume: float = Field(ge=0)
    vwap: float = Field(gt=0)
    trade_imbalance: float = Field(ge=-1.0, le=1.0)
    quote_trade_imbalance: float = Field(ge=-1.0, le=1.0)
    source_row_hashes: tuple[str, ...] = ()
    row_hash: str = Field(min_length=64, max_length=64)
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_row(self) -> "OrderflowFeatureRow":
        require_research_boundary(self, context="orderflow feature row")
        if self.bucket_end_ms <= self.bucket_start_ms:
            raise ValueError("bucket_end_ms must be greater than bucket_start_ms")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native orderflow features require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external orderflow features cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("orderflow feature rows are not accepted historical coverage proof")
        if self.row_hash != orderflow_feature_row_hash(self):
            raise ValueError("row_hash does not match orderflow feature row")
        return self


class OrderflowFeatureReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "orderflow_feature_reconstruction_report"
    feature_report_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    venue: str | None = None
    venue_symbol: str | None = None
    hyperliquid_coin: str | None = None
    market_type: str | None = None
    coverage_label: CoverageLabel | None = None
    bucket_seconds: int = Field(ge=1)
    rows: tuple[OrderflowFeatureRow, ...] = ()
    row_count: int = Field(ge=0)
    input_row_count: int = Field(ge=0)
    missing_side_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    blocker_reasons: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_report(self) -> "OrderflowFeatureReport":
        require_research_boundary(self, context="orderflow feature report")
        if self.report_type != "orderflow_feature_reconstruction_report":
            raise ValueError("report_type must be orderflow_feature_reconstruction_report")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.row_manifest_hash != orderflow_feature_rows_hash(self.rows):
            raise ValueError("row_manifest_hash does not match rows")
        if self.row_count == 0 and not self.blocker_reasons:
            raise ValueError("empty orderflow reports require blocker reasons")
        if self.missing_side_count and "missing_trade_side" not in self.blocker_reasons:
            raise ValueError("missing_side_count requires missing_trade_side blocker")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native orderflow reports require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external orderflow reports cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("orderflow reports are not accepted historical coverage proof")
        expected_id = orderflow_feature_report_id_for(
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            source_ids=self.source_ids,
            venue=self.venue,
            venue_symbol=self.venue_symbol,
            hyperliquid_coin=self.hyperliquid_coin,
            bucket_seconds=self.bucket_seconds,
            row_manifest_hash=self.row_manifest_hash,
            blocker_reasons=self.blocker_reasons,
        )
        if self.feature_report_id != expected_id:
            raise ValueError("feature_report_id does not match report identity")
        return self


FUNDING_OI_CONTEXT_FAMILIES: tuple[str, ...] = (
    "funding_rate_history",
    "open_interest",
    "open_interest_statistics",
    "basis",
)


class DerivativesContextFeatureInputRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    family: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    timestamp_ms: int | None = Field(default=None, ge=0)
    open_time_ms: int | None = Field(default=None, ge=0)
    close_time_ms: int | None = Field(default=None, ge=0)
    publication_time_ms: int | None = Field(default=None, ge=0)
    interval: str | None = None
    period: str | None = None
    bucket_seconds: int | None = Field(default=None, ge=1)
    numeric_fields: dict[str, float] = Field(default_factory=dict)
    unit_fields: dict[str, str] = Field(default_factory=dict)
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_ref: str | None = None
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_input_row(self) -> "DerivativesContextFeatureInputRow":
        require_research_boundary(self, context="derivatives context feature input row")
        if self.accepted_historical_coverage_proof:
            raise ValueError("context feature input rows are not accepted historical coverage proof")
        return self


class DerivativesContextFeatureRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    family: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    coverage_label: CoverageLabel
    feature_timestamp_ms: int = Field(ge=0)
    open_time_ms: int | None = Field(default=None, ge=0)
    close_time_ms: int | None = Field(default=None, ge=0)
    publication_time_ms: int | None = Field(default=None, ge=0)
    interval: str | None = None
    period: str | None = None
    bucket_seconds: int | None = Field(default=None, ge=1)
    numeric_features: dict[str, float] = Field(default_factory=dict)
    unit_fields: dict[str, str] = Field(default_factory=dict)
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_ref: str | None = None
    row_hash: str = Field(min_length=64, max_length=64)
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_row(self) -> "DerivativesContextFeatureRow":
        require_research_boundary(self, context="derivatives context feature row")
        if self.family not in FUNDING_OI_CONTEXT_FAMILIES:
            raise ValueError("unsupported derivatives context feature family")
        if not self.numeric_features:
            raise ValueError("context feature rows require numeric_features")
        for key, value in self.numeric_features.items():
            if not isfinite(value):
                raise ValueError(f"numeric feature {key} must be finite")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native context features require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external context features cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("context feature rows are not accepted historical coverage proof")
        if self.row_hash != derivatives_context_feature_row_hash(self):
            raise ValueError("row_hash does not match derivatives context feature row")
        return self


class DerivativesContextFeatureReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "derivatives_context_feature_reconstruction_report"
    feature_report_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    families: tuple[str, ...] = ()
    venue: str | None = None
    venue_symbol: str | None = None
    hyperliquid_coin: str | None = None
    market_type: str | None = None
    coverage_label: CoverageLabel | None = None
    rows: tuple[DerivativesContextFeatureRow, ...] = ()
    row_count: int = Field(ge=0)
    input_row_count: int = Field(ge=0)
    missing_timestamp_count: int = Field(ge=0)
    missing_numeric_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    blocker_reasons: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_report(self) -> "DerivativesContextFeatureReport":
        require_research_boundary(self, context="derivatives context feature report")
        if self.report_type != "derivatives_context_feature_reconstruction_report":
            raise ValueError("report_type must be derivatives_context_feature_reconstruction_report")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.row_manifest_hash != derivatives_context_feature_rows_hash(self.rows):
            raise ValueError("row_manifest_hash does not match rows")
        if self.row_count == 0 and not self.blocker_reasons:
            raise ValueError("empty context feature reports require blocker reasons")
        if self.missing_timestamp_count and "missing_context_timestamp" not in self.blocker_reasons:
            raise ValueError("missing_timestamp_count requires missing_context_timestamp blocker")
        if self.missing_numeric_count and "missing_numeric_fields" not in self.blocker_reasons:
            raise ValueError("missing_numeric_count requires missing_numeric_fields blocker")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native context reports require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external context reports cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("context feature reports are not accepted historical coverage proof")
        expected_id = derivatives_context_feature_report_id_for(
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            source_ids=self.source_ids,
            families=self.families,
            venue=self.venue,
            venue_symbol=self.venue_symbol,
            hyperliquid_coin=self.hyperliquid_coin,
            row_manifest_hash=self.row_manifest_hash,
            blocker_reasons=self.blocker_reasons,
        )
        if self.feature_report_id != expected_id:
            raise ValueError("feature_report_id does not match context feature report identity")
        return self


class BBOFeatureInputRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    event_type: str = "bbo"
    ts: datetime | None = None
    timestamp_ms: int | None = Field(default=None, ge=0)
    sequence: int = Field(default=0, ge=0)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    bid_size: float | None = Field(default=None, ge=0)
    ask_size: float | None = Field(default=None, ge=0)
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_ref: str | None = None
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_input_row(self) -> "BBOFeatureInputRow":
        require_research_boundary(self, context="BBO feature input row")
        if self.event_type != "bbo":
            raise ValueError("BBO feature input rows require event_type=bbo")
        if self.ask < self.bid:
            raise ValueError("BBO ask must be greater than or equal to bid")
        if self.accepted_historical_coverage_proof:
            raise ValueError("BBO feature input rows are not accepted historical coverage proof")
        return self


class BBOFeatureRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    coverage_label: CoverageLabel
    feature_timestamp_ms: int = Field(ge=0)
    sequence: int = Field(default=0, ge=0)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    bid_size: float = Field(ge=0)
    ask_size: float = Field(ge=0)
    mid_price: float = Field(gt=0)
    spread: float = Field(ge=0)
    spread_bps: float = Field(ge=0)
    top_size_imbalance: float = Field(ge=-1.0, le=1.0)
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_ref: str | None = None
    row_hash: str = Field(min_length=64, max_length=64)
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_row(self) -> "BBOFeatureRow":
        require_research_boundary(self, context="BBO feature row")
        if self.ask < self.bid:
            raise ValueError("BBO ask must be greater than or equal to bid")
        if not isfinite(self.mid_price) or not isfinite(self.spread_bps):
            raise ValueError("BBO price features must be finite")
        if not isfinite(self.top_size_imbalance):
            raise ValueError("BBO size imbalance must be finite")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native BBO features require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external BBO features cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("BBO feature rows are not accepted historical coverage proof")
        if self.row_hash != bbo_feature_row_hash(self):
            raise ValueError("row_hash does not match BBO feature row")
        return self


class BBOFeatureReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "bbo_spread_feature_reconstruction_report"
    feature_report_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    venue: str | None = None
    venue_symbol: str | None = None
    hyperliquid_coin: str | None = None
    market_type: str | None = None
    coverage_label: CoverageLabel | None = None
    rows: tuple[BBOFeatureRow, ...] = ()
    row_count: int = Field(ge=0)
    input_row_count: int = Field(ge=0)
    missing_timestamp_count: int = Field(ge=0)
    missing_size_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    blocker_reasons: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_report(self) -> "BBOFeatureReport":
        require_research_boundary(self, context="BBO feature report")
        if self.report_type != "bbo_spread_feature_reconstruction_report":
            raise ValueError("report_type must be bbo_spread_feature_reconstruction_report")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.row_manifest_hash != bbo_feature_rows_hash(self.rows):
            raise ValueError("row_manifest_hash does not match rows")
        if self.row_count == 0 and not self.blocker_reasons:
            raise ValueError("empty BBO feature reports require blocker reasons")
        if self.missing_timestamp_count and "missing_bbo_timestamp" not in self.blocker_reasons:
            raise ValueError("missing_timestamp_count requires missing_bbo_timestamp blocker")
        if self.missing_size_count and "missing_bbo_size" not in self.blocker_reasons:
            raise ValueError("missing_size_count requires missing_bbo_size blocker")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native BBO reports require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external BBO reports cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("BBO feature reports are not accepted historical coverage proof")
        expected_id = bbo_feature_report_id_for(
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            source_ids=self.source_ids,
            venue=self.venue,
            venue_symbol=self.venue_symbol,
            hyperliquid_coin=self.hyperliquid_coin,
            row_manifest_hash=self.row_manifest_hash,
            blocker_reasons=self.blocker_reasons,
        )
        if self.feature_report_id != expected_id:
            raise ValueError("feature_report_id does not match BBO feature report identity")
        return self


class L2DepthFeatureInputRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    event_type: str = "l2"
    ts: datetime | None = None
    timestamp_ms: int | None = Field(default=None, ge=0)
    sequence: int = Field(default=0, ge=0)
    bid_depth: float = Field(ge=0)
    ask_depth: float = Field(ge=0)
    book_levels: int | None = Field(default=None, ge=0)
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_ref: str | None = None
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_input_row(self) -> "L2DepthFeatureInputRow":
        require_research_boundary(self, context="L2 depth feature input row")
        if self.event_type != "l2":
            raise ValueError("L2 depth feature input rows require event_type=l2")
        if self.accepted_historical_coverage_proof:
            raise ValueError("L2 feature input rows are not accepted historical coverage proof")
        return self


class L2DepthFeatureRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    coverage_label: CoverageLabel
    feature_timestamp_ms: int = Field(ge=0)
    sequence: int = Field(default=0, ge=0)
    bid_depth: float = Field(ge=0)
    ask_depth: float = Field(ge=0)
    total_depth: float = Field(gt=0)
    depth_imbalance: float = Field(ge=-1.0, le=1.0)
    book_levels: int | None = Field(default=None, ge=0)
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_ref: str | None = None
    row_hash: str = Field(min_length=64, max_length=64)
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_row(self) -> "L2DepthFeatureRow":
        require_research_boundary(self, context="L2 depth feature row")
        if not isfinite(self.total_depth) or not isfinite(self.depth_imbalance):
            raise ValueError("L2 depth features must be finite")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native L2 features require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external L2 features cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("L2 feature rows are not accepted historical coverage proof")
        if self.row_hash != l2_depth_feature_row_hash(self):
            raise ValueError("row_hash does not match L2 depth feature row")
        return self


class L2DepthFeatureReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "l2_depth_feature_reconstruction_report"
    feature_report_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    venue: str | None = None
    venue_symbol: str | None = None
    hyperliquid_coin: str | None = None
    market_type: str | None = None
    coverage_label: CoverageLabel | None = None
    rows: tuple[L2DepthFeatureRow, ...] = ()
    row_count: int = Field(ge=0)
    input_row_count: int = Field(ge=0)
    missing_timestamp_count: int = Field(ge=0)
    zero_depth_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    blocker_reasons: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_report(self) -> "L2DepthFeatureReport":
        require_research_boundary(self, context="L2 depth feature report")
        if self.report_type != "l2_depth_feature_reconstruction_report":
            raise ValueError("report_type must be l2_depth_feature_reconstruction_report")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.row_manifest_hash != l2_depth_feature_rows_hash(self.rows):
            raise ValueError("row_manifest_hash does not match rows")
        if self.row_count == 0 and not self.blocker_reasons:
            raise ValueError("empty L2 feature reports require blocker reasons")
        if self.missing_timestamp_count and "missing_l2_timestamp" not in self.blocker_reasons:
            raise ValueError("missing_timestamp_count requires missing_l2_timestamp blocker")
        if self.zero_depth_count and "zero_l2_depth" not in self.blocker_reasons:
            raise ValueError("zero_depth_count requires zero_l2_depth blocker")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native L2 reports require native_hyperliquid label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external L2 reports cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("L2 feature reports are not accepted historical coverage proof")
        expected_id = l2_depth_feature_report_id_for(
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            source_ids=self.source_ids,
            venue=self.venue,
            venue_symbol=self.venue_symbol,
            hyperliquid_coin=self.hyperliquid_coin,
            row_manifest_hash=self.row_manifest_hash,
            blocker_reasons=self.blocker_reasons,
        )
        if self.feature_report_id != expected_id:
            raise ValueError("feature_report_id does not match L2 feature report identity")
        return self


class CrossVenuePriceInputRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    price_kind: str = Field(min_length=1)
    ts: datetime | None = None
    timestamp_ms: int | None = Field(default=None, ge=0)
    price: float = Field(gt=0)
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_ref: str | None = None
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_input_row(self) -> "CrossVenuePriceInputRow":
        require_research_boundary(self, context="cross-venue price input row")
        if self.accepted_historical_coverage_proof:
            raise ValueError("cross-venue price input rows are not accepted historical coverage proof")
        return self


class CrossVenueBasisFeatureRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    primary_source_id: str = Field(min_length=1)
    comparison_source_id: str = Field(min_length=1)
    primary_venue: str = Field(min_length=1)
    comparison_venue: str = Field(min_length=1)
    primary_venue_symbol: str = Field(min_length=1)
    comparison_venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str = Field(min_length=1)
    market_type: str = Field(min_length=1)
    price_kind: str = Field(min_length=1)
    coverage_label: CoverageLabel = CoverageLabel.EXTERNAL_COMPARISON
    feature_timestamp_ms: int = Field(ge=0)
    primary_price: float = Field(gt=0)
    comparison_price: float = Field(gt=0)
    basis_abs: float
    basis_bps: float
    primary_native_to_hyperliquid: bool = False
    comparison_native_to_hyperliquid: bool = False
    source_row_hashes: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    row_hash: str = Field(min_length=64, max_length=64)
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_row(self) -> "CrossVenueBasisFeatureRow":
        require_research_boundary(self, context="cross-venue basis feature row")
        if self.coverage_label != CoverageLabel.EXTERNAL_COMPARISON:
            raise ValueError("cross-venue basis rows must use external_comparison label")
        if self.native_to_hyperliquid:
            raise ValueError("cross-venue basis rows are not Hyperliquid-native")
        if not isfinite(self.basis_abs) or not isfinite(self.basis_bps):
            raise ValueError("cross-venue basis features must be finite")
        expected_bps = (self.comparison_price - self.primary_price) / self.primary_price * 10_000.0
        if abs(self.basis_abs - (self.comparison_price - self.primary_price)) > 1e-12:
            raise ValueError("basis_abs does not match prices")
        if abs(self.basis_bps - expected_bps) > 1e-9:
            raise ValueError("basis_bps does not match prices")
        if self.accepted_historical_coverage_proof:
            raise ValueError("cross-venue basis rows are not accepted historical coverage proof")
        if self.row_hash != cross_venue_basis_feature_row_hash(self):
            raise ValueError("row_hash does not match cross-venue basis feature row")
        return self


class CrossVenueBasisFeatureReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "cross_venue_basis_feature_reconstruction_report"
    feature_report_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    venues: tuple[str, ...] = ()
    primary_venue: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str | None = None
    price_kind: str | None = None
    coverage_label: CoverageLabel = CoverageLabel.EXTERNAL_COMPARISON
    rows: tuple[CrossVenueBasisFeatureRow, ...] = ()
    row_count: int = Field(ge=0)
    input_row_count: int = Field(ge=0)
    missing_timestamp_count: int = Field(ge=0)
    missing_primary_count: int = Field(ge=0)
    duplicate_primary_count: int = Field(ge=0)
    missing_comparison_count: int = Field(ge=0)
    row_manifest_hash: str = Field(min_length=64, max_length=64)
    blocker_reasons: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    native_to_hyperliquid: bool = False
    accepted_historical_coverage_proof: bool = False
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
    def _validate_report(self) -> "CrossVenueBasisFeatureReport":
        require_research_boundary(self, context="cross-venue basis feature report")
        if self.report_type != "cross_venue_basis_feature_reconstruction_report":
            raise ValueError("report_type must be cross_venue_basis_feature_reconstruction_report")
        if self.coverage_label != CoverageLabel.EXTERNAL_COMPARISON:
            raise ValueError("cross-venue basis reports must use external_comparison label")
        if self.native_to_hyperliquid:
            raise ValueError("cross-venue basis reports are not Hyperliquid-native")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.row_manifest_hash != cross_venue_basis_feature_rows_hash(self.rows):
            raise ValueError("row_manifest_hash does not match rows")
        if self.row_count == 0 and not self.blocker_reasons:
            raise ValueError("empty cross-venue basis reports require blocker reasons")
        if self.missing_timestamp_count and "missing_cross_venue_timestamp" not in self.blocker_reasons:
            raise ValueError("missing_timestamp_count requires missing_cross_venue_timestamp blocker")
        if self.missing_primary_count and "missing_primary_venue_price" not in self.blocker_reasons:
            raise ValueError("missing_primary_count requires missing_primary_venue_price blocker")
        if self.duplicate_primary_count and "duplicate_primary_venue_price" not in self.blocker_reasons:
            raise ValueError("duplicate_primary_count requires duplicate_primary_venue_price blocker")
        if self.missing_comparison_count and "missing_comparison_venue_price" not in self.blocker_reasons:
            raise ValueError("missing_comparison_count requires missing_comparison_venue_price blocker")
        if self.accepted_historical_coverage_proof:
            raise ValueError("cross-venue basis reports are not accepted historical coverage proof")
        expected_id = cross_venue_basis_feature_report_id_for(
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            source_ids=self.source_ids,
            venues=self.venues,
            primary_venue=self.primary_venue,
            hyperliquid_coin=self.hyperliquid_coin,
            row_manifest_hash=self.row_manifest_hash,
            blocker_reasons=self.blocker_reasons,
        )
        if self.feature_report_id != expected_id:
            raise ValueError("feature_report_id does not match cross-venue basis report identity")
        return self


def reconstruct_orderflow_features_from_trades(
    *,
    trade_rows: Iterable[TradeBarInputRow | Mapping[str, Any]],
    source_registry_ref: str,
    symbol_map_ref: str,
    bucket_seconds: int = 60,
) -> OrderflowFeatureReport:
    if bucket_seconds < 1:
        raise ValueError("bucket_seconds must be positive")
    parsed_rows = tuple(
        row if isinstance(row, TradeBarInputRow) else TradeBarInputRow.model_validate(dict(row))
        for row in trade_rows
    )
    if not parsed_rows:
        return _orderflow_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            bucket_seconds=bucket_seconds,
            input_row_count=0,
            rows=(),
            blocker_reasons=("empty_trade_rows",),
        )
    _validate_single_trade_provenance(parsed_rows)
    source_ids = tuple(sorted({row.source_id for row in parsed_rows}))
    native_to_hyperliquid = parsed_rows[0].native_to_hyperliquid
    coverage_label = (
        CoverageLabel.NATIVE_HYPERLIQUID
        if native_to_hyperliquid
        else CoverageLabel.EXTERNAL_COMPARISON
    )
    feature_rows = _build_orderflow_rows(
        rows=parsed_rows,
        source_ids=source_ids,
        coverage_label=coverage_label,
        bucket_seconds=bucket_seconds,
    )
    missing_side_count = sum(1 for row in parsed_rows if row.side in {None, "unknown"})
    blockers = ("missing_trade_side",) if missing_side_count else ()
    return _orderflow_report(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        bucket_seconds=bucket_seconds,
        input_row_count=len(parsed_rows),
        rows=feature_rows,
        source_ids=source_ids,
        venue=parsed_rows[0].venue,
        venue_symbol=parsed_rows[0].venue_symbol,
        hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
        market_type=parsed_rows[0].market_type,
        coverage_label=coverage_label,
        native_to_hyperliquid=native_to_hyperliquid,
        missing_side_count=missing_side_count,
        blocker_reasons=blockers,
    )


def orderflow_feature_row_hash(row: OrderflowFeatureRow | Mapping[str, Any]) -> str:
    excluded = {
        "row_hash",
        "schema_version",
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    }
    if isinstance(row, OrderflowFeatureRow):
        payload = row.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: value for key, value in dict(row).items() if key not in excluded}
        payload.setdefault("accepted_historical_coverage_proof", False)
        if isinstance(payload.get("coverage_label"), CoverageLabel):
            payload["coverage_label"] = payload["coverage_label"].value
    return canonical_json_hash(payload)


def orderflow_feature_rows_hash(rows: tuple[OrderflowFeatureRow, ...]) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def orderflow_feature_report_id_for(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    source_ids: tuple[str, ...],
    venue: str | None,
    venue_symbol: str | None,
    hyperliquid_coin: str | None,
    bucket_seconds: int,
    row_manifest_hash: str,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "report_type": "orderflow_feature_reconstruction_report",
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "source_ids": source_ids,
            "venue": venue,
            "venue_symbol": venue_symbol,
            "hyperliquid_coin": hyperliquid_coin,
            "bucket_seconds": bucket_seconds,
            "row_manifest_hash": row_manifest_hash,
            "blocker_reasons": blocker_reasons,
        }
    )


def reconstruct_funding_oi_features_from_context_rows(
    *,
    context_rows: Iterable[DerivativesContextFeatureInputRow | Mapping[str, Any] | BaseModel],
    source_registry_ref: str,
    symbol_map_ref: str,
) -> DerivativesContextFeatureReport:
    parsed_rows = tuple(_parse_context_feature_input_row(row) for row in context_rows)
    if not parsed_rows:
        return _context_feature_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            input_row_count=0,
            rows=(),
            blocker_reasons=("empty_context_rows",),
        )
    _validate_single_context_provenance(parsed_rows)
    source_ids = tuple(sorted({row.source_id for row in parsed_rows}))
    families = tuple(sorted({row.family for row in parsed_rows}))
    native_to_hyperliquid = parsed_rows[0].native_to_hyperliquid
    coverage_label = (
        CoverageLabel.NATIVE_HYPERLIQUID
        if native_to_hyperliquid
        else CoverageLabel.EXTERNAL_COMPARISON
    )
    unsupported_families = tuple(
        family for family in families if family not in FUNDING_OI_CONTEXT_FAMILIES
    )
    missing_timestamp_count = sum(1 for row in parsed_rows if _context_feature_timestamp_ms(row) is None)
    missing_numeric_count = sum(1 for row in parsed_rows if not row.numeric_fields)
    blockers: list[str] = []
    if unsupported_families:
        blockers.append("unsupported_context_family")
    if missing_timestamp_count:
        blockers.append("missing_context_timestamp")
    if missing_numeric_count:
        blockers.append("missing_numeric_fields")
    if blockers:
        return _context_feature_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            input_row_count=len(parsed_rows),
            rows=(),
            source_ids=source_ids,
            families=families,
            venue=parsed_rows[0].venue,
            venue_symbol=parsed_rows[0].venue_symbol,
            hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
            market_type=parsed_rows[0].market_type,
            coverage_label=coverage_label,
            native_to_hyperliquid=native_to_hyperliquid,
            missing_timestamp_count=missing_timestamp_count,
            missing_numeric_count=missing_numeric_count,
            blocker_reasons=tuple(blockers),
        )
    feature_rows = tuple(
        _context_feature_row(row=row, coverage_label=coverage_label) for row in parsed_rows
    )
    return _context_feature_report(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        input_row_count=len(parsed_rows),
        rows=feature_rows,
        source_ids=source_ids,
        families=families,
        venue=parsed_rows[0].venue,
        venue_symbol=parsed_rows[0].venue_symbol,
        hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
        market_type=parsed_rows[0].market_type,
        coverage_label=coverage_label,
        native_to_hyperliquid=native_to_hyperliquid,
    )


def derivatives_context_feature_row_hash(
    row: DerivativesContextFeatureRow | Mapping[str, Any],
) -> str:
    excluded = {
        "row_hash",
        "schema_version",
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    }
    if isinstance(row, DerivativesContextFeatureRow):
        payload = row.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: value for key, value in dict(row).items() if key not in excluded}
        payload.setdefault("accepted_historical_coverage_proof", False)
        if isinstance(payload.get("coverage_label"), CoverageLabel):
            payload["coverage_label"] = payload["coverage_label"].value
    return canonical_json_hash(payload)


def derivatives_context_feature_rows_hash(
    rows: tuple[DerivativesContextFeatureRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def derivatives_context_feature_report_id_for(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    source_ids: tuple[str, ...],
    families: tuple[str, ...],
    venue: str | None,
    venue_symbol: str | None,
    hyperliquid_coin: str | None,
    row_manifest_hash: str,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "report_type": "derivatives_context_feature_reconstruction_report",
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "source_ids": source_ids,
            "families": families,
            "venue": venue,
            "venue_symbol": venue_symbol,
            "hyperliquid_coin": hyperliquid_coin,
            "row_manifest_hash": row_manifest_hash,
            "blocker_reasons": blocker_reasons,
        }
    )


def reconstruct_bbo_spread_features_from_rows(
    *,
    bbo_rows: Iterable[BBOFeatureInputRow | Mapping[str, Any] | BaseModel],
    source_registry_ref: str,
    symbol_map_ref: str,
) -> BBOFeatureReport:
    parsed_rows = tuple(_parse_bbo_feature_input_row(row) for row in bbo_rows)
    if not parsed_rows:
        return _bbo_feature_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            input_row_count=0,
            rows=(),
            blocker_reasons=("empty_bbo_rows",),
        )
    _validate_single_bbo_provenance(parsed_rows)
    source_ids = tuple(sorted({row.source_id for row in parsed_rows}))
    native_to_hyperliquid = parsed_rows[0].native_to_hyperliquid
    coverage_label = (
        CoverageLabel.NATIVE_HYPERLIQUID
        if native_to_hyperliquid
        else CoverageLabel.EXTERNAL_COMPARISON
    )
    missing_timestamp_count = sum(1 for row in parsed_rows if _bbo_timestamp_ms(row) is None)
    missing_size_count = sum(
        1 for row in parsed_rows if row.bid_size is None or row.ask_size is None
    )
    blockers: list[str] = []
    if missing_timestamp_count:
        blockers.append("missing_bbo_timestamp")
    if missing_size_count:
        blockers.append("missing_bbo_size")
    if blockers:
        return _bbo_feature_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            input_row_count=len(parsed_rows),
            rows=(),
            source_ids=source_ids,
            venue=parsed_rows[0].venue,
            venue_symbol=parsed_rows[0].venue_symbol,
            hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
            market_type=parsed_rows[0].market_type,
            coverage_label=coverage_label,
            native_to_hyperliquid=native_to_hyperliquid,
            missing_timestamp_count=missing_timestamp_count,
            missing_size_count=missing_size_count,
            blocker_reasons=tuple(blockers),
        )
    feature_rows = tuple(
        _bbo_feature_row(row=row, coverage_label=coverage_label)
        for row in sorted(
            parsed_rows,
            key=lambda item: (_bbo_timestamp_ms(item) or 0, item.sequence),
        )
    )
    return _bbo_feature_report(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        input_row_count=len(parsed_rows),
        rows=feature_rows,
        source_ids=source_ids,
        venue=parsed_rows[0].venue,
        venue_symbol=parsed_rows[0].venue_symbol,
        hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
        market_type=parsed_rows[0].market_type,
        coverage_label=coverage_label,
        native_to_hyperliquid=native_to_hyperliquid,
    )


def bbo_feature_row_hash(row: BBOFeatureRow | Mapping[str, Any]) -> str:
    excluded = {
        "row_hash",
        "schema_version",
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    }
    if isinstance(row, BBOFeatureRow):
        payload = row.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: value for key, value in dict(row).items() if key not in excluded}
        payload.setdefault("accepted_historical_coverage_proof", False)
        if isinstance(payload.get("coverage_label"), CoverageLabel):
            payload["coverage_label"] = payload["coverage_label"].value
    return canonical_json_hash(payload)


def bbo_feature_rows_hash(rows: tuple[BBOFeatureRow, ...]) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def bbo_feature_report_id_for(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    source_ids: tuple[str, ...],
    venue: str | None,
    venue_symbol: str | None,
    hyperliquid_coin: str | None,
    row_manifest_hash: str,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "report_type": "bbo_spread_feature_reconstruction_report",
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "source_ids": source_ids,
            "venue": venue,
            "venue_symbol": venue_symbol,
            "hyperliquid_coin": hyperliquid_coin,
            "row_manifest_hash": row_manifest_hash,
            "blocker_reasons": blocker_reasons,
        }
    )


def reconstruct_l2_depth_features_from_rows(
    *,
    l2_rows: Iterable[L2DepthFeatureInputRow | Mapping[str, Any] | BaseModel],
    source_registry_ref: str,
    symbol_map_ref: str,
) -> L2DepthFeatureReport:
    parsed_rows = tuple(_parse_l2_depth_feature_input_row(row) for row in l2_rows)
    if not parsed_rows:
        return _l2_depth_feature_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            input_row_count=0,
            rows=(),
            blocker_reasons=("empty_l2_rows",),
        )
    _validate_single_l2_provenance(parsed_rows)
    source_ids = tuple(sorted({row.source_id for row in parsed_rows}))
    native_to_hyperliquid = parsed_rows[0].native_to_hyperliquid
    coverage_label = (
        CoverageLabel.NATIVE_HYPERLIQUID
        if native_to_hyperliquid
        else CoverageLabel.EXTERNAL_COMPARISON
    )
    missing_timestamp_count = sum(1 for row in parsed_rows if _l2_timestamp_ms(row) is None)
    zero_depth_count = sum(1 for row in parsed_rows if row.bid_depth + row.ask_depth <= 0)
    blockers: list[str] = []
    if missing_timestamp_count:
        blockers.append("missing_l2_timestamp")
    if zero_depth_count:
        blockers.append("zero_l2_depth")
    if blockers:
        return _l2_depth_feature_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            input_row_count=len(parsed_rows),
            rows=(),
            source_ids=source_ids,
            venue=parsed_rows[0].venue,
            venue_symbol=parsed_rows[0].venue_symbol,
            hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
            market_type=parsed_rows[0].market_type,
            coverage_label=coverage_label,
            native_to_hyperliquid=native_to_hyperliquid,
            missing_timestamp_count=missing_timestamp_count,
            zero_depth_count=zero_depth_count,
            blocker_reasons=tuple(blockers),
        )
    feature_rows = tuple(
        _l2_depth_feature_row(row=row, coverage_label=coverage_label)
        for row in sorted(
            parsed_rows,
            key=lambda item: (_l2_timestamp_ms(item) or 0, item.sequence),
        )
    )
    return _l2_depth_feature_report(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        input_row_count=len(parsed_rows),
        rows=feature_rows,
        source_ids=source_ids,
        venue=parsed_rows[0].venue,
        venue_symbol=parsed_rows[0].venue_symbol,
        hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
        market_type=parsed_rows[0].market_type,
        coverage_label=coverage_label,
        native_to_hyperliquid=native_to_hyperliquid,
    )


def l2_depth_feature_row_hash(row: L2DepthFeatureRow | Mapping[str, Any]) -> str:
    excluded = {
        "row_hash",
        "schema_version",
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    }
    if isinstance(row, L2DepthFeatureRow):
        payload = row.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: value for key, value in dict(row).items() if key not in excluded}
        payload.setdefault("accepted_historical_coverage_proof", False)
        if isinstance(payload.get("coverage_label"), CoverageLabel):
            payload["coverage_label"] = payload["coverage_label"].value
    return canonical_json_hash(payload)


def l2_depth_feature_rows_hash(rows: tuple[L2DepthFeatureRow, ...]) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def l2_depth_feature_report_id_for(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    source_ids: tuple[str, ...],
    venue: str | None,
    venue_symbol: str | None,
    hyperliquid_coin: str | None,
    row_manifest_hash: str,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "report_type": "l2_depth_feature_reconstruction_report",
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "source_ids": source_ids,
            "venue": venue,
            "venue_symbol": venue_symbol,
            "hyperliquid_coin": hyperliquid_coin,
            "row_manifest_hash": row_manifest_hash,
            "blocker_reasons": blocker_reasons,
        }
    )


def reconstruct_cross_venue_basis_features_from_prices(
    *,
    price_rows: Iterable[CrossVenuePriceInputRow | Mapping[str, Any] | BaseModel],
    source_registry_ref: str,
    symbol_map_ref: str,
    primary_venue: str = "hyperliquid",
) -> CrossVenueBasisFeatureReport:
    if not primary_venue:
        raise ValueError("primary_venue is required")
    parsed_rows = tuple(_parse_cross_venue_price_input_row(row) for row in price_rows)
    if not parsed_rows:
        return _cross_venue_basis_feature_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            primary_venue=primary_venue,
            input_row_count=0,
            rows=(),
            blocker_reasons=("empty_cross_venue_price_rows",),
        )
    _validate_single_cross_venue_context(parsed_rows)
    source_ids = tuple(sorted({row.source_id for row in parsed_rows}))
    venues = tuple(sorted({row.venue for row in parsed_rows}))
    missing_timestamp_count = sum(
        1 for row in parsed_rows if _cross_venue_price_timestamp_ms(row) is None
    )
    blockers: list[str] = []
    if len(venues) < 2:
        blockers.append("insufficient_cross_venue_coverage")
    if missing_timestamp_count:
        blockers.append("missing_cross_venue_timestamp")
    grouped: dict[int, list[CrossVenuePriceInputRow]] = {}
    if not missing_timestamp_count:
        for row in parsed_rows:
            timestamp_ms = _cross_venue_price_timestamp_ms(row)
            if timestamp_ms is not None:
                grouped.setdefault(timestamp_ms, []).append(row)
    missing_primary_count = 0
    duplicate_primary_count = 0
    missing_comparison_count = 0
    for group_rows in grouped.values():
        primary_rows = [row for row in group_rows if row.venue == primary_venue]
        comparison_rows = [row for row in group_rows if row.venue != primary_venue]
        if not primary_rows:
            missing_primary_count += 1
        if len(primary_rows) > 1:
            duplicate_primary_count += 1
        if not comparison_rows:
            missing_comparison_count += 1
    if missing_primary_count:
        blockers.append("missing_primary_venue_price")
    if duplicate_primary_count:
        blockers.append("duplicate_primary_venue_price")
    if missing_comparison_count:
        blockers.append("missing_comparison_venue_price")
    if blockers:
        return _cross_venue_basis_feature_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            primary_venue=primary_venue,
            input_row_count=len(parsed_rows),
            rows=(),
            source_ids=source_ids,
            venues=venues,
            hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
            market_type=parsed_rows[0].market_type,
            price_kind=parsed_rows[0].price_kind,
            missing_timestamp_count=missing_timestamp_count,
            missing_primary_count=missing_primary_count,
            duplicate_primary_count=duplicate_primary_count,
            missing_comparison_count=missing_comparison_count,
            blocker_reasons=tuple(blockers),
        )
    feature_rows: list[CrossVenueBasisFeatureRow] = []
    for timestamp_ms, group_rows in sorted(grouped.items()):
        primary = next(row for row in group_rows if row.venue == primary_venue)
        for comparison in sorted(
            (row for row in group_rows if row.venue != primary_venue),
            key=lambda item: (item.venue, item.venue_symbol, item.source_id),
        ):
            feature_rows.append(
                _cross_venue_basis_feature_row(
                    timestamp_ms=timestamp_ms,
                    primary=primary,
                    comparison=comparison,
                )
            )
    return _cross_venue_basis_feature_report(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        primary_venue=primary_venue,
        input_row_count=len(parsed_rows),
        rows=tuple(feature_rows),
        source_ids=source_ids,
        venues=venues,
        hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
        market_type=parsed_rows[0].market_type,
        price_kind=parsed_rows[0].price_kind,
    )


def cross_venue_basis_feature_row_hash(
    row: CrossVenueBasisFeatureRow | Mapping[str, Any],
) -> str:
    excluded = {
        "row_hash",
        "schema_version",
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    }
    if isinstance(row, CrossVenueBasisFeatureRow):
        payload = row.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: value for key, value in dict(row).items() if key not in excluded}
        payload.setdefault("accepted_historical_coverage_proof", False)
        if isinstance(payload.get("coverage_label"), CoverageLabel):
            payload["coverage_label"] = payload["coverage_label"].value
    return canonical_json_hash(payload)


def cross_venue_basis_feature_rows_hash(
    rows: tuple[CrossVenueBasisFeatureRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def cross_venue_basis_feature_report_id_for(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    source_ids: tuple[str, ...],
    venues: tuple[str, ...],
    primary_venue: str,
    hyperliquid_coin: str | None,
    row_manifest_hash: str,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "report_type": "cross_venue_basis_feature_reconstruction_report",
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "source_ids": source_ids,
            "venues": venues,
            "primary_venue": primary_venue,
            "hyperliquid_coin": hyperliquid_coin,
            "row_manifest_hash": row_manifest_hash,
            "blocker_reasons": blocker_reasons,
        }
    )


def _validate_single_trade_provenance(rows: tuple[TradeBarInputRow, ...]) -> None:
    first = rows[0]
    for row in rows[1:]:
        if row.native_to_hyperliquid != first.native_to_hyperliquid:
            raise ValueError("cannot mix native and external trade rows")
        if row.venue != first.venue:
            raise ValueError("trade rows must share one venue")
        if row.venue_symbol != first.venue_symbol:
            raise ValueError("trade rows must share one venue_symbol")
        if row.hyperliquid_coin != first.hyperliquid_coin:
            raise ValueError("trade rows must share one hyperliquid_coin")
        if row.market_type != first.market_type:
            raise ValueError("trade rows must share one market_type")


def _parse_context_feature_input_row(
    row: DerivativesContextFeatureInputRow | Mapping[str, Any] | BaseModel,
) -> DerivativesContextFeatureInputRow:
    if isinstance(row, DerivativesContextFeatureInputRow):
        return row
    if isinstance(row, BaseModel):
        payload = row.model_dump(mode="json")
    else:
        payload = dict(row)
    if "venue_symbol" not in payload and "symbol" in payload:
        payload["venue_symbol"] = payload["symbol"]
    family = payload.get("family")
    if hasattr(family, "value"):
        payload["family"] = family.value
    elif family is not None:
        payload["family"] = str(family)
    return DerivativesContextFeatureInputRow.model_validate(payload)


def _validate_single_context_provenance(
    rows: tuple[DerivativesContextFeatureInputRow, ...],
) -> None:
    first = rows[0]
    for row in rows[1:]:
        if row.native_to_hyperliquid != first.native_to_hyperliquid:
            raise ValueError("cannot mix native and external context rows")
        if row.venue != first.venue:
            raise ValueError("context rows must share one venue")
        if row.venue_symbol != first.venue_symbol:
            raise ValueError("context rows must share one venue_symbol")
        if row.hyperliquid_coin != first.hyperliquid_coin:
            raise ValueError("context rows must share one hyperliquid_coin")
        if row.market_type != first.market_type:
            raise ValueError("context rows must share one market_type")


def _context_feature_timestamp_ms(row: DerivativesContextFeatureInputRow) -> int | None:
    for value in (
        row.timestamp_ms,
        row.open_time_ms,
        row.close_time_ms,
        row.publication_time_ms,
    ):
        if value is not None:
            return value
    return None


def _context_feature_row(
    *,
    row: DerivativesContextFeatureInputRow,
    coverage_label: CoverageLabel,
) -> DerivativesContextFeatureRow:
    feature_timestamp_ms = _context_feature_timestamp_ms(row)
    if feature_timestamp_ms is None:
        raise ValueError("context feature rows require a timestamp")
    numeric_features = dict(sorted(row.numeric_fields.items()))
    for key, value in numeric_features.items():
        if not isfinite(value):
            raise ValueError(f"numeric feature {key} must be finite")
    unit_fields = {
        key: row.unit_fields[key]
        for key in sorted(row.unit_fields)
        if key in numeric_features
    }
    payload: dict[str, Any] = {
        "source_id": row.source_id,
        "family": row.family,
        "venue": row.venue,
        "venue_symbol": row.venue_symbol,
        "hyperliquid_coin": row.hyperliquid_coin,
        "market_type": row.market_type,
        "coverage_label": coverage_label,
        "feature_timestamp_ms": feature_timestamp_ms,
        "open_time_ms": row.open_time_ms,
        "close_time_ms": row.close_time_ms,
        "publication_time_ms": row.publication_time_ms,
        "interval": row.interval,
        "period": row.period,
        "bucket_seconds": row.bucket_seconds,
        "numeric_features": numeric_features,
        "unit_fields": unit_fields,
        "source_row_hash": row.source_row_hash,
        "source_ref": row.source_ref,
        "native_to_hyperliquid": row.native_to_hyperliquid,
        "accepted_historical_coverage_proof": False,
    }
    return DerivativesContextFeatureRow(
        **payload,
        row_hash=derivatives_context_feature_row_hash(payload),
    )


def _parse_bbo_feature_input_row(
    row: BBOFeatureInputRow | Mapping[str, Any] | BaseModel,
) -> BBOFeatureInputRow:
    if isinstance(row, BBOFeatureInputRow):
        return row
    if isinstance(row, BaseModel):
        payload = row.model_dump(mode="json")
    else:
        payload = dict(row)
    if "source_id" not in payload and "source" in payload:
        payload["source_id"] = payload["source"]
    if "venue_symbol" not in payload and "instrument_id" in payload:
        payload["venue_symbol"] = payload["instrument_id"]
    if "venue" not in payload:
        payload["venue"] = "hyperliquid" if payload.get("native_to_hyperliquid") else "external"
    if "market_type" not in payload:
        payload["market_type"] = "perpetual"
    return BBOFeatureInputRow.model_validate(payload)


def _validate_single_bbo_provenance(rows: tuple[BBOFeatureInputRow, ...]) -> None:
    first = rows[0]
    for row in rows[1:]:
        if row.native_to_hyperliquid != first.native_to_hyperliquid:
            raise ValueError("cannot mix native and external BBO rows")
        if row.venue != first.venue:
            raise ValueError("BBO rows must share one venue")
        if row.venue_symbol != first.venue_symbol:
            raise ValueError("BBO rows must share one venue_symbol")
        if row.hyperliquid_coin != first.hyperliquid_coin:
            raise ValueError("BBO rows must share one hyperliquid_coin")
        if row.market_type != first.market_type:
            raise ValueError("BBO rows must share one market_type")


def _bbo_timestamp_ms(row: BBOFeatureInputRow) -> int | None:
    if row.timestamp_ms is not None:
        return row.timestamp_ms
    if row.ts is None:
        return None
    if row.ts.tzinfo is None:
        raise ValueError("BBO ts must be timezone-aware")
    return int(row.ts.timestamp() * 1000)


def _bbo_feature_row(
    *,
    row: BBOFeatureInputRow,
    coverage_label: CoverageLabel,
) -> BBOFeatureRow:
    timestamp_ms = _bbo_timestamp_ms(row)
    if timestamp_ms is None:
        raise ValueError("BBO feature rows require a timestamp")
    if row.bid_size is None or row.ask_size is None:
        raise ValueError("BBO feature rows require bid_size and ask_size")
    mid_price = (row.bid + row.ask) / 2.0
    spread = row.ask - row.bid
    size_total = row.bid_size + row.ask_size
    top_size_imbalance = 0.0 if size_total == 0 else (row.bid_size - row.ask_size) / size_total
    payload: dict[str, Any] = {
        "source_id": row.source_id,
        "venue": row.venue,
        "venue_symbol": row.venue_symbol,
        "hyperliquid_coin": row.hyperliquid_coin,
        "market_type": row.market_type,
        "coverage_label": coverage_label,
        "feature_timestamp_ms": timestamp_ms,
        "sequence": row.sequence,
        "bid": row.bid,
        "ask": row.ask,
        "bid_size": row.bid_size,
        "ask_size": row.ask_size,
        "mid_price": mid_price,
        "spread": spread,
        "spread_bps": (spread / mid_price) * 10_000.0,
        "top_size_imbalance": top_size_imbalance,
        "source_row_hash": row.source_row_hash,
        "source_ref": row.source_ref,
        "native_to_hyperliquid": row.native_to_hyperliquid,
        "accepted_historical_coverage_proof": False,
    }
    return BBOFeatureRow(
        **payload,
        row_hash=bbo_feature_row_hash(payload),
    )


def _parse_l2_depth_feature_input_row(
    row: L2DepthFeatureInputRow | Mapping[str, Any] | BaseModel,
) -> L2DepthFeatureInputRow:
    if isinstance(row, L2DepthFeatureInputRow):
        return row
    if isinstance(row, BaseModel):
        payload = row.model_dump(mode="json")
    else:
        payload = dict(row)
    if "source_id" not in payload and "source" in payload:
        payload["source_id"] = payload["source"]
    if "venue_symbol" not in payload and "instrument_id" in payload:
        payload["venue_symbol"] = payload["instrument_id"]
    if "venue" not in payload:
        payload["venue"] = "hyperliquid" if payload.get("native_to_hyperliquid") else "external"
    if "market_type" not in payload:
        payload["market_type"] = "perpetual"
    return L2DepthFeatureInputRow.model_validate(payload)


def _validate_single_l2_provenance(rows: tuple[L2DepthFeatureInputRow, ...]) -> None:
    first = rows[0]
    for row in rows[1:]:
        if row.native_to_hyperliquid != first.native_to_hyperliquid:
            raise ValueError("cannot mix native and external L2 rows")
        if row.venue != first.venue:
            raise ValueError("L2 rows must share one venue")
        if row.venue_symbol != first.venue_symbol:
            raise ValueError("L2 rows must share one venue_symbol")
        if row.hyperliquid_coin != first.hyperliquid_coin:
            raise ValueError("L2 rows must share one hyperliquid_coin")
        if row.market_type != first.market_type:
            raise ValueError("L2 rows must share one market_type")


def _l2_timestamp_ms(row: L2DepthFeatureInputRow) -> int | None:
    if row.timestamp_ms is not None:
        return row.timestamp_ms
    if row.ts is None:
        return None
    if row.ts.tzinfo is None:
        raise ValueError("L2 ts must be timezone-aware")
    return int(row.ts.timestamp() * 1000)


def _l2_depth_feature_row(
    *,
    row: L2DepthFeatureInputRow,
    coverage_label: CoverageLabel,
) -> L2DepthFeatureRow:
    timestamp_ms = _l2_timestamp_ms(row)
    if timestamp_ms is None:
        raise ValueError("L2 feature rows require a timestamp")
    total_depth = row.bid_depth + row.ask_depth
    if total_depth <= 0:
        raise ValueError("L2 feature rows require positive total depth")
    payload: dict[str, Any] = {
        "source_id": row.source_id,
        "venue": row.venue,
        "venue_symbol": row.venue_symbol,
        "hyperliquid_coin": row.hyperliquid_coin,
        "market_type": row.market_type,
        "coverage_label": coverage_label,
        "feature_timestamp_ms": timestamp_ms,
        "sequence": row.sequence,
        "bid_depth": row.bid_depth,
        "ask_depth": row.ask_depth,
        "total_depth": total_depth,
        "depth_imbalance": (row.bid_depth - row.ask_depth) / total_depth,
        "book_levels": row.book_levels,
        "source_row_hash": row.source_row_hash,
        "source_ref": row.source_ref,
        "native_to_hyperliquid": row.native_to_hyperliquid,
        "accepted_historical_coverage_proof": False,
    }
    return L2DepthFeatureRow(
        **payload,
        row_hash=l2_depth_feature_row_hash(payload),
    )


def _parse_cross_venue_price_input_row(
    row: CrossVenuePriceInputRow | Mapping[str, Any] | BaseModel,
) -> CrossVenuePriceInputRow:
    if isinstance(row, CrossVenuePriceInputRow):
        return row
    if isinstance(row, BaseModel):
        payload = row.model_dump(mode="json")
    else:
        payload = dict(row)
    if "venue_symbol" not in payload and "symbol" in payload:
        payload["venue_symbol"] = payload["symbol"]
    if "price" not in payload:
        for key in ("mid_price", "close", "mark_price", "oracle_price", "vwap"):
            if key in payload:
                payload["price"] = payload[key]
                payload.setdefault("price_kind", key)
                break
    payload.setdefault("price_kind", "price")
    payload.setdefault("market_type", "perpetual")
    return CrossVenuePriceInputRow.model_validate(payload)


def _validate_single_cross_venue_context(rows: tuple[CrossVenuePriceInputRow, ...]) -> None:
    first = rows[0]
    for row in rows[1:]:
        if row.hyperliquid_coin != first.hyperliquid_coin:
            raise ValueError("cross-venue price rows must share one hyperliquid_coin")
        if row.market_type != first.market_type:
            raise ValueError("cross-venue price rows must share one market_type")
        if row.price_kind != first.price_kind:
            raise ValueError("cross-venue price rows must share one price_kind")


def _cross_venue_price_timestamp_ms(row: CrossVenuePriceInputRow) -> int | None:
    if row.timestamp_ms is not None:
        return row.timestamp_ms
    if row.ts is None:
        return None
    if row.ts.tzinfo is None:
        raise ValueError("cross-venue price ts must be timezone-aware")
    return int(row.ts.timestamp() * 1000)


def _cross_venue_basis_feature_row(
    *,
    timestamp_ms: int,
    primary: CrossVenuePriceInputRow,
    comparison: CrossVenuePriceInputRow,
) -> CrossVenueBasisFeatureRow:
    source_row_hashes = tuple(
        value for value in (primary.source_row_hash, comparison.source_row_hash) if value
    )
    source_refs = tuple(value for value in (primary.source_ref, comparison.source_ref) if value)
    payload: dict[str, Any] = {
        "primary_source_id": primary.source_id,
        "comparison_source_id": comparison.source_id,
        "primary_venue": primary.venue,
        "comparison_venue": comparison.venue,
        "primary_venue_symbol": primary.venue_symbol,
        "comparison_venue_symbol": comparison.venue_symbol,
        "hyperliquid_coin": primary.hyperliquid_coin,
        "market_type": primary.market_type,
        "price_kind": primary.price_kind,
        "coverage_label": CoverageLabel.EXTERNAL_COMPARISON,
        "feature_timestamp_ms": timestamp_ms,
        "primary_price": primary.price,
        "comparison_price": comparison.price,
        "basis_abs": comparison.price - primary.price,
        "basis_bps": (comparison.price - primary.price) / primary.price * 10_000.0,
        "primary_native_to_hyperliquid": primary.native_to_hyperliquid,
        "comparison_native_to_hyperliquid": comparison.native_to_hyperliquid,
        "source_row_hashes": source_row_hashes,
        "source_refs": source_refs,
        "native_to_hyperliquid": False,
        "accepted_historical_coverage_proof": False,
    }
    return CrossVenueBasisFeatureRow(
        **payload,
        row_hash=cross_venue_basis_feature_row_hash(payload),
    )


def _build_orderflow_rows(
    *,
    rows: tuple[TradeBarInputRow, ...],
    source_ids: tuple[str, ...],
    coverage_label: CoverageLabel,
    bucket_seconds: int,
) -> tuple[OrderflowFeatureRow, ...]:
    bucket_ms = bucket_seconds * 1000
    grouped: dict[int, list[TradeBarInputRow]] = {}
    for row in rows:
        bucket_start = (row.source_timestamp_ms // bucket_ms) * bucket_ms
        grouped.setdefault(bucket_start, []).append(row)
    output: list[OrderflowFeatureRow] = []
    for bucket_start, bucket_rows in sorted(grouped.items()):
        output.append(
            _orderflow_row(
                bucket_start=bucket_start,
                bucket_ms=bucket_ms,
                source_ids=source_ids,
                coverage_label=coverage_label,
                rows=tuple(sorted(bucket_rows, key=lambda item: item.source_timestamp_ms)),
            )
        )
    return tuple(output)


def _orderflow_row(
    *,
    bucket_start: int,
    bucket_ms: int,
    source_ids: tuple[str, ...],
    coverage_label: CoverageLabel,
    rows: tuple[TradeBarInputRow, ...],
) -> OrderflowFeatureRow:
    total_volume = sum((row.quantity for row in rows), 0.0)
    quote_volumes = tuple(
        row.quote_quantity if row.quote_quantity is not None else row.price * row.quantity
        for row in rows
    )
    total_quote_volume = sum(quote_volumes, 0.0)
    if total_volume <= 0:
        raise ValueError("orderflow bucket total_volume must be positive")
    buy_volume = sum((row.quantity for row in rows if row.side == "buy"), 0.0)
    sell_volume = sum((row.quantity for row in rows if row.side == "sell"), 0.0)
    unknown_side_volume = sum(
        (row.quantity for row in rows if row.side in {None, "unknown"}),
        0.0,
    )
    buy_quote_volume = sum(
        (quote_volume for row, quote_volume in zip(rows, quote_volumes, strict=True) if row.side == "buy"),
        0.0,
    )
    sell_quote_volume = sum(
        (quote_volume for row, quote_volume in zip(rows, quote_volumes, strict=True) if row.side == "sell"),
        0.0,
    )
    unknown_quote_volume = sum(
        (
            quote_volume
            for row, quote_volume in zip(rows, quote_volumes, strict=True)
            if row.side in {None, "unknown"}
        ),
        0.0,
    )
    payload: dict[str, Any] = {
        "source_ids": source_ids,
        "venue": rows[0].venue,
        "venue_symbol": rows[0].venue_symbol,
        "hyperliquid_coin": rows[0].hyperliquid_coin,
        "market_type": rows[0].market_type,
        "coverage_label": coverage_label,
        "bucket_seconds": bucket_ms // 1000,
        "bucket_start_ms": bucket_start,
        "bucket_end_ms": bucket_start + bucket_ms,
        "trade_count": len(rows),
        "total_volume": total_volume,
        "total_quote_volume": total_quote_volume,
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "unknown_side_volume": unknown_side_volume,
        "buy_quote_volume": buy_quote_volume,
        "sell_quote_volume": sell_quote_volume,
        "unknown_side_quote_volume": unknown_quote_volume,
        "vwap": total_quote_volume / total_volume,
        "trade_imbalance": _imbalance(buy_volume, sell_volume),
        "quote_trade_imbalance": _imbalance(buy_quote_volume, sell_quote_volume),
        "source_row_hashes": tuple(row.source_row_hash for row in rows if row.source_row_hash),
        "native_to_hyperliquid": rows[0].native_to_hyperliquid,
        "accepted_historical_coverage_proof": False,
    }
    return OrderflowFeatureRow(
        **payload,
        row_hash=orderflow_feature_row_hash(payload),
    )


def _imbalance(buy_value: float, sell_value: float) -> float:
    total = buy_value + sell_value
    if total == 0:
        return 0.0
    return (buy_value - sell_value) / total


def _context_feature_report(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    input_row_count: int,
    rows: tuple[DerivativesContextFeatureRow, ...],
    source_ids: tuple[str, ...] = (),
    families: tuple[str, ...] = (),
    venue: str | None = None,
    venue_symbol: str | None = None,
    hyperliquid_coin: str | None = None,
    market_type: str | None = None,
    coverage_label: CoverageLabel | None = None,
    native_to_hyperliquid: bool = False,
    missing_timestamp_count: int = 0,
    missing_numeric_count: int = 0,
    blocker_reasons: tuple[str, ...] = (),
) -> DerivativesContextFeatureReport:
    row_manifest_hash = derivatives_context_feature_rows_hash(rows)
    report_id = derivatives_context_feature_report_id_for(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        families=families,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
    )
    return DerivativesContextFeatureReport(
        feature_report_id=report_id,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        families=families,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        market_type=market_type,
        coverage_label=coverage_label,
        rows=rows,
        row_count=len(rows),
        input_row_count=input_row_count,
        missing_timestamp_count=missing_timestamp_count,
        missing_numeric_count=missing_numeric_count,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
        native_to_hyperliquid=native_to_hyperliquid,
    )


def _bbo_feature_report(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    input_row_count: int,
    rows: tuple[BBOFeatureRow, ...],
    source_ids: tuple[str, ...] = (),
    venue: str | None = None,
    venue_symbol: str | None = None,
    hyperliquid_coin: str | None = None,
    market_type: str | None = None,
    coverage_label: CoverageLabel | None = None,
    native_to_hyperliquid: bool = False,
    missing_timestamp_count: int = 0,
    missing_size_count: int = 0,
    blocker_reasons: tuple[str, ...] = (),
) -> BBOFeatureReport:
    row_manifest_hash = bbo_feature_rows_hash(rows)
    report_id = bbo_feature_report_id_for(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
    )
    return BBOFeatureReport(
        feature_report_id=report_id,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        market_type=market_type,
        coverage_label=coverage_label,
        rows=rows,
        row_count=len(rows),
        input_row_count=input_row_count,
        missing_timestamp_count=missing_timestamp_count,
        missing_size_count=missing_size_count,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
        native_to_hyperliquid=native_to_hyperliquid,
    )


def _l2_depth_feature_report(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    input_row_count: int,
    rows: tuple[L2DepthFeatureRow, ...],
    source_ids: tuple[str, ...] = (),
    venue: str | None = None,
    venue_symbol: str | None = None,
    hyperliquid_coin: str | None = None,
    market_type: str | None = None,
    coverage_label: CoverageLabel | None = None,
    native_to_hyperliquid: bool = False,
    missing_timestamp_count: int = 0,
    zero_depth_count: int = 0,
    blocker_reasons: tuple[str, ...] = (),
) -> L2DepthFeatureReport:
    row_manifest_hash = l2_depth_feature_rows_hash(rows)
    report_id = l2_depth_feature_report_id_for(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
    )
    return L2DepthFeatureReport(
        feature_report_id=report_id,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        market_type=market_type,
        coverage_label=coverage_label,
        rows=rows,
        row_count=len(rows),
        input_row_count=input_row_count,
        missing_timestamp_count=missing_timestamp_count,
        zero_depth_count=zero_depth_count,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
        native_to_hyperliquid=native_to_hyperliquid,
    )


def _cross_venue_basis_feature_report(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    primary_venue: str,
    input_row_count: int,
    rows: tuple[CrossVenueBasisFeatureRow, ...],
    source_ids: tuple[str, ...] = (),
    venues: tuple[str, ...] = (),
    hyperliquid_coin: str | None = None,
    market_type: str | None = None,
    price_kind: str | None = None,
    missing_timestamp_count: int = 0,
    missing_primary_count: int = 0,
    duplicate_primary_count: int = 0,
    missing_comparison_count: int = 0,
    blocker_reasons: tuple[str, ...] = (),
) -> CrossVenueBasisFeatureReport:
    row_manifest_hash = cross_venue_basis_feature_rows_hash(rows)
    report_id = cross_venue_basis_feature_report_id_for(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venues=venues,
        primary_venue=primary_venue,
        hyperliquid_coin=hyperliquid_coin,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
    )
    return CrossVenueBasisFeatureReport(
        feature_report_id=report_id,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venues=venues,
        primary_venue=primary_venue,
        hyperliquid_coin=hyperliquid_coin,
        market_type=market_type,
        price_kind=price_kind,
        rows=rows,
        row_count=len(rows),
        input_row_count=input_row_count,
        missing_timestamp_count=missing_timestamp_count,
        missing_primary_count=missing_primary_count,
        duplicate_primary_count=duplicate_primary_count,
        missing_comparison_count=missing_comparison_count,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
    )


def _orderflow_report(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    bucket_seconds: int,
    input_row_count: int,
    rows: tuple[OrderflowFeatureRow, ...],
    source_ids: tuple[str, ...] = (),
    venue: str | None = None,
    venue_symbol: str | None = None,
    hyperliquid_coin: str | None = None,
    market_type: str | None = None,
    coverage_label: CoverageLabel | None = None,
    native_to_hyperliquid: bool = False,
    missing_side_count: int = 0,
    blocker_reasons: tuple[str, ...] = (),
) -> OrderflowFeatureReport:
    row_manifest_hash = orderflow_feature_rows_hash(rows)
    report_id = orderflow_feature_report_id_for(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        bucket_seconds=bucket_seconds,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
    )
    return OrderflowFeatureReport(
        feature_report_id=report_id,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        market_type=market_type,
        coverage_label=coverage_label,
        bucket_seconds=bucket_seconds,
        rows=rows,
        row_count=len(rows),
        input_row_count=input_row_count,
        missing_side_count=missing_side_count,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
        native_to_hyperliquid=native_to_hyperliquid,
    )
