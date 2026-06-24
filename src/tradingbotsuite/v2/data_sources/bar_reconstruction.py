# V2-AUDIT-ID: V2-AUD-DATASRC-036
# V2-CONTRACTS: docs/contracts/data_source_registry_contract.md
# V2-BOUNDARY: research_only, no_archive_writes, no_coverage_acceptance
# V2-OWNER: v2_data_sources
"""Generic trade-to-bar reconstruction helpers for v2 research data."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.data_sources.schemas import CoverageLabel
from tradingbotsuite.v2.security.boundary import require_research_boundary


class TradeBarInputRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    source_timestamp_ms: int = Field(ge=0)
    price: float = Field(gt=0)
    quantity: float = Field(ge=0)
    quote_quantity: float | None = Field(default=None, ge=0)
    side: str | None = Field(default=None, pattern=r"^(buy|sell|unknown)$")
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
    def _validate_input_row(self) -> "TradeBarInputRow":
        require_research_boundary(self, context="trade bar input row")
        if self.accepted_historical_coverage_proof:
            raise ValueError("trade bar input rows are not accepted historical coverage proof")
        if self.source_ref:
            PurePosixPath(self.source_ref)
        return self


class ReconstructedTradeBarRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_ids: tuple[str, ...] = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    coverage_label: CoverageLabel
    bucket_seconds: int = Field(ge=1)
    bar_start_ms: int = Field(ge=0)
    bar_end_ms: int = Field(ge=0)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    quote_volume: float = Field(ge=0)
    trade_count: int = Field(ge=1)
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
    def _validate_bar_row(self) -> "ReconstructedTradeBarRow":
        require_research_boundary(self, context="reconstructed trade bar row")
        if self.bar_end_ms <= self.bar_start_ms:
            raise ValueError("bar_end_ms must be greater than bar_start_ms")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("reconstructed low cannot exceed open/high/close")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("reconstructed high cannot be below open/low/close")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native reconstructed bars require native_hyperliquid coverage label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external reconstructed bars cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("reconstructed bars are not accepted historical coverage proof")
        if self.row_hash != reconstructed_trade_bar_row_hash(self):
            raise ValueError("row_hash does not match reconstructed bar row")
        return self


class TradeBarReconstructionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "trade_bar_reconstruction_report"
    reconstruction_report_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    venue: str | None = None
    venue_symbol: str | None = None
    hyperliquid_coin: str | None = None
    market_type: str | None = None
    coverage_label: CoverageLabel | None = None
    bucket_seconds: int = Field(ge=1)
    expected_start_ms: int | None = Field(default=None, ge=0)
    expected_end_ms: int | None = Field(default=None, ge=0)
    rows: tuple[ReconstructedTradeBarRow, ...] = ()
    row_count: int = Field(ge=0)
    input_row_count: int = Field(ge=0)
    source_row_hashes: tuple[str, ...] = ()
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
    def _validate_report(self) -> "TradeBarReconstructionReport":
        require_research_boundary(self, context="trade bar reconstruction report")
        if self.report_type != "trade_bar_reconstruction_report":
            raise ValueError("report_type must be trade_bar_reconstruction_report")
        if self.expected_start_ms is not None and self.expected_end_ms is not None:
            if self.expected_end_ms <= self.expected_start_ms:
                raise ValueError("expected_end_ms must be greater than expected_start_ms")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.row_manifest_hash != trade_bar_reconstruction_rows_hash(self.rows):
            raise ValueError("row_manifest_hash does not match rows")
        if self.row_count == 0 and not self.blocker_reasons:
            raise ValueError("empty reconstruction reports require blocker reasons")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native reconstruction reports require native_hyperliquid coverage label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external reconstruction reports cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("reconstruction reports are not accepted historical coverage proof")
        expected_id = trade_bar_reconstruction_report_id_for(
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            source_ids=self.source_ids,
            venue=self.venue,
            venue_symbol=self.venue_symbol,
            hyperliquid_coin=self.hyperliquid_coin,
            bucket_seconds=self.bucket_seconds,
            expected_start_ms=self.expected_start_ms,
            expected_end_ms=self.expected_end_ms,
            row_manifest_hash=self.row_manifest_hash,
            blocker_reasons=self.blocker_reasons,
        )
        if self.reconstruction_report_id != expected_id:
            raise ValueError("reconstruction_report_id does not match report identity")
        return self


class SourceNativeBarInputRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    coverage_label: CoverageLabel
    bucket_seconds: int = Field(ge=1)
    bar_start_ms: int = Field(ge=0)
    bar_end_ms: int = Field(ge=0)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    quote_volume: float | None = Field(default=None, ge=0)
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
    def _validate_source_bar(self) -> "SourceNativeBarInputRow":
        require_research_boundary(self, context="source-native bar input row")
        if self.bar_end_ms <= self.bar_start_ms:
            raise ValueError("bar_end_ms must be greater than bar_start_ms")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("source bar low cannot exceed open/high/close")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("source bar high cannot be below open/low/close")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native source bars require native_hyperliquid coverage label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external source bars cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("source-native bars are not accepted historical coverage proof")
        if self.source_ref:
            PurePosixPath(self.source_ref)
        return self


class ReconstructedBarComparisonRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    coverage_label: CoverageLabel
    bucket_seconds: int = Field(ge=1)
    bar_start_ms: int = Field(ge=0)
    bar_end_ms: int = Field(ge=0)
    status: str = Field(pattern=r"^(passed|failed|missing_reconstructed|extra_reconstructed)$")
    source_open: float | None = Field(default=None, gt=0)
    source_high: float | None = Field(default=None, gt=0)
    source_low: float | None = Field(default=None, gt=0)
    source_close: float | None = Field(default=None, gt=0)
    source_volume: float | None = Field(default=None, ge=0)
    source_quote_volume: float | None = Field(default=None, ge=0)
    reconstructed_open: float | None = Field(default=None, gt=0)
    reconstructed_high: float | None = Field(default=None, gt=0)
    reconstructed_low: float | None = Field(default=None, gt=0)
    reconstructed_close: float | None = Field(default=None, gt=0)
    reconstructed_volume: float | None = Field(default=None, ge=0)
    reconstructed_quote_volume: float | None = Field(default=None, ge=0)
    open_abs_diff: float | None = Field(default=None, ge=0)
    high_abs_diff: float | None = Field(default=None, ge=0)
    low_abs_diff: float | None = Field(default=None, ge=0)
    close_abs_diff: float | None = Field(default=None, ge=0)
    volume_abs_diff: float | None = Field(default=None, ge=0)
    quote_volume_abs_diff: float | None = Field(default=None, ge=0)
    source_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    reconstructed_row_hash: str | None = Field(default=None, min_length=64, max_length=64)
    reasons: tuple[str, ...] = ()
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
    def _validate_comparison_row(self) -> "ReconstructedBarComparisonRow":
        require_research_boundary(self, context="reconstructed bar comparison row")
        if self.bar_end_ms <= self.bar_start_ms:
            raise ValueError("bar_end_ms must be greater than bar_start_ms")
        if self.status != "passed" and not self.reasons:
            raise ValueError(f"{self.status} comparison rows require reasons")
        if self.status == "passed" and self.reasons:
            raise ValueError("passed comparison rows cannot carry reasons")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native comparison rows require native_hyperliquid coverage label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external comparison rows cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("comparison rows are not accepted historical coverage proof")
        if self.row_hash != reconstructed_bar_comparison_row_hash(self):
            raise ValueError("row_hash does not match comparison row")
        return self


class ReconstructedBarComparisonReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    report_type: str = "reconstructed_bar_comparison_report"
    comparison_report_id: str = Field(min_length=64, max_length=64)
    reconstruction_report_id: str = Field(min_length=64, max_length=64)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    source_bar_source_ids: tuple[str, ...] = Field(min_length=1)
    venue: str = Field(min_length=1)
    venue_symbol: str = Field(min_length=1)
    hyperliquid_coin: str | None = None
    market_type: str = Field(min_length=1)
    coverage_label: CoverageLabel
    bucket_seconds: int = Field(ge=1)
    price_tolerance: float = Field(ge=0)
    volume_tolerance: float = Field(ge=0)
    quote_volume_tolerance: float = Field(ge=0)
    rows: tuple[ReconstructedBarComparisonRow, ...]
    row_count: int = Field(ge=0)
    passed: bool
    passed_bucket_count: int = Field(ge=0)
    failed_bucket_count: int = Field(ge=0)
    missing_reconstructed_count: int = Field(ge=0)
    extra_reconstructed_count: int = Field(ge=0)
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
    def _validate_comparison_report(self) -> "ReconstructedBarComparisonReport":
        require_research_boundary(self, context="reconstructed bar comparison report")
        if self.report_type != "reconstructed_bar_comparison_report":
            raise ValueError("report_type must be reconstructed_bar_comparison_report")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows length")
        if self.passed_bucket_count != sum(1 for row in self.rows if row.status == "passed"):
            raise ValueError("passed_bucket_count does not match rows")
        if self.failed_bucket_count != sum(1 for row in self.rows if row.status == "failed"):
            raise ValueError("failed_bucket_count does not match rows")
        if self.missing_reconstructed_count != sum(
            1 for row in self.rows if row.status == "missing_reconstructed"
        ):
            raise ValueError("missing_reconstructed_count does not match rows")
        if self.extra_reconstructed_count != sum(
            1 for row in self.rows if row.status == "extra_reconstructed"
        ):
            raise ValueError("extra_reconstructed_count does not match rows")
        if self.passed != (not self.blocker_reasons and self.row_count > 0):
            raise ValueError("passed flag does not match blocker state")
        if self.row_manifest_hash != reconstructed_bar_comparison_rows_hash(self.rows):
            raise ValueError("row_manifest_hash does not match comparison rows")
        if self.native_to_hyperliquid and self.coverage_label != CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("native comparison reports require native_hyperliquid coverage label")
        if not self.native_to_hyperliquid and self.coverage_label == CoverageLabel.NATIVE_HYPERLIQUID:
            raise ValueError("external comparison reports cannot use native_hyperliquid label")
        if self.accepted_historical_coverage_proof:
            raise ValueError("comparison reports are not accepted historical coverage proof")
        expected_id = reconstructed_bar_comparison_report_id_for(
            reconstruction_report_id=self.reconstruction_report_id,
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            source_ids=self.source_ids,
            source_bar_source_ids=self.source_bar_source_ids,
            venue=self.venue,
            venue_symbol=self.venue_symbol,
            hyperliquid_coin=self.hyperliquid_coin,
            bucket_seconds=self.bucket_seconds,
            price_tolerance=self.price_tolerance,
            volume_tolerance=self.volume_tolerance,
            quote_volume_tolerance=self.quote_volume_tolerance,
            row_manifest_hash=self.row_manifest_hash,
            blocker_reasons=self.blocker_reasons,
        )
        if self.comparison_report_id != expected_id:
            raise ValueError("comparison_report_id does not match report identity")
        return self


def reconstruct_trade_bars_from_rows(
    *,
    trade_rows: Iterable[TradeBarInputRow | Mapping[str, Any]],
    source_registry_ref: str,
    symbol_map_ref: str,
    bucket_seconds: int = 60,
    expected_start_ms: int | None = None,
    expected_end_ms: int | None = None,
) -> TradeBarReconstructionReport:
    if bucket_seconds < 1:
        raise ValueError("bucket_seconds must be positive")
    parsed_rows = tuple(
        row if isinstance(row, TradeBarInputRow) else TradeBarInputRow.model_validate(dict(row))
        for row in trade_rows
    )
    if expected_start_ms is not None and expected_end_ms is not None:
        if expected_end_ms <= expected_start_ms:
            raise ValueError("expected_end_ms must be greater than expected_start_ms")
    if not parsed_rows:
        return _reconstruction_report(
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            bucket_seconds=bucket_seconds,
            expected_start_ms=expected_start_ms,
            expected_end_ms=expected_end_ms,
            input_row_count=0,
            rows=(),
            blocker_reasons=("empty_trade_rows",),
        )
    _validate_single_provenance(parsed_rows)
    if expected_start_ms is not None or expected_end_ms is not None:
        _validate_expected_window(parsed_rows, expected_start_ms, expected_end_ms)
    source_ids = tuple(sorted({row.source_id for row in parsed_rows}))
    native_to_hyperliquid = parsed_rows[0].native_to_hyperliquid
    coverage_label = (
        CoverageLabel.NATIVE_HYPERLIQUID
        if native_to_hyperliquid
        else CoverageLabel.EXTERNAL_COMPARISON
    )
    reconstructed_rows = _reconstruct_rows(
        rows=parsed_rows,
        source_ids=source_ids,
        coverage_label=coverage_label,
        bucket_seconds=bucket_seconds,
    )
    return _reconstruction_report(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        bucket_seconds=bucket_seconds,
        expected_start_ms=expected_start_ms,
        expected_end_ms=expected_end_ms,
        input_row_count=len(parsed_rows),
        rows=reconstructed_rows,
        source_ids=source_ids,
        venue=parsed_rows[0].venue,
        venue_symbol=parsed_rows[0].venue_symbol,
        hyperliquid_coin=parsed_rows[0].hyperliquid_coin,
        market_type=parsed_rows[0].market_type,
        coverage_label=coverage_label,
        native_to_hyperliquid=native_to_hyperliquid,
        source_row_hashes=tuple(row.source_row_hash for row in parsed_rows if row.source_row_hash),
    )


def compare_reconstructed_trade_bars_to_source_bars(
    *,
    reconstruction_report: TradeBarReconstructionReport | Mapping[str, Any],
    source_bars: Iterable[SourceNativeBarInputRow | Mapping[str, Any]],
    price_tolerance: float = 0.0,
    volume_tolerance: float = 0.0,
    quote_volume_tolerance: float = 0.0,
) -> ReconstructedBarComparisonReport:
    if price_tolerance < 0:
        raise ValueError("price_tolerance must be non-negative")
    if volume_tolerance < 0:
        raise ValueError("volume_tolerance must be non-negative")
    if quote_volume_tolerance < 0:
        raise ValueError("quote_volume_tolerance must be non-negative")
    parsed_report = (
        reconstruction_report
        if isinstance(reconstruction_report, TradeBarReconstructionReport)
        else TradeBarReconstructionReport.model_validate(dict(reconstruction_report))
    )
    parsed_source_bars = tuple(
        row if isinstance(row, SourceNativeBarInputRow) else SourceNativeBarInputRow.model_validate(dict(row))
        for row in source_bars
    )
    if not parsed_source_bars:
        raise ValueError("source_bars cannot be empty")
    _validate_source_bar_set(parsed_source_bars)
    _validate_comparison_provenance(parsed_report, parsed_source_bars[0])
    source_by_bucket = _unique_source_bars_by_bucket(parsed_source_bars)
    reconstructed_by_bucket = _unique_reconstructed_bars_by_bucket(parsed_report.rows)
    comparison_rows: list[ReconstructedBarComparisonRow] = []
    for source_bucket, source_row in sorted(source_by_bucket.items()):
        reconstructed = reconstructed_by_bucket.get(source_bucket)
        comparison_rows.append(
            _comparison_row(
                source_row=source_row,
                reconstructed=reconstructed,
                price_tolerance=price_tolerance,
                volume_tolerance=volume_tolerance,
                quote_volume_tolerance=quote_volume_tolerance,
            )
        )
    for reconstructed_bucket, reconstructed in sorted(reconstructed_by_bucket.items()):
        if reconstructed_bucket not in source_by_bucket:
            comparison_rows.append(
                _extra_reconstructed_row(
                    source_row=parsed_source_bars[0],
                    reconstructed=reconstructed,
                )
            )
    blocker_reasons = _comparison_blocker_reasons(tuple(comparison_rows))
    return _comparison_report(
        reconstruction_report=parsed_report,
        source_bars=parsed_source_bars,
        rows=tuple(comparison_rows),
        price_tolerance=price_tolerance,
        volume_tolerance=volume_tolerance,
        quote_volume_tolerance=quote_volume_tolerance,
        blocker_reasons=blocker_reasons,
    )


def reconstructed_trade_bar_row_hash(
    row: ReconstructedTradeBarRow | Mapping[str, Any],
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
    if isinstance(row, ReconstructedTradeBarRow):
        payload = row.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: value for key, value in dict(row).items() if key not in excluded}
        payload.setdefault("accepted_historical_coverage_proof", False)
        if isinstance(payload.get("coverage_label"), CoverageLabel):
            payload["coverage_label"] = payload["coverage_label"].value
    return canonical_json_hash(payload)


def reconstructed_bar_comparison_row_hash(
    row: ReconstructedBarComparisonRow | Mapping[str, Any],
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
    if isinstance(row, ReconstructedBarComparisonRow):
        payload = row.model_dump(mode="json", exclude=excluded)
    else:
        payload = {key: value for key, value in dict(row).items() if key not in excluded}
        payload.setdefault("accepted_historical_coverage_proof", False)
        if isinstance(payload.get("coverage_label"), CoverageLabel):
            payload["coverage_label"] = payload["coverage_label"].value
        for optional_key in (
            "source_open",
            "source_high",
            "source_low",
            "source_close",
            "source_volume",
            "source_quote_volume",
            "reconstructed_open",
            "reconstructed_high",
            "reconstructed_low",
            "reconstructed_close",
            "reconstructed_volume",
            "reconstructed_quote_volume",
            "open_abs_diff",
            "high_abs_diff",
            "low_abs_diff",
            "close_abs_diff",
            "volume_abs_diff",
            "quote_volume_abs_diff",
            "source_row_hash",
            "reconstructed_row_hash",
        ):
            payload.setdefault(optional_key, None)
        payload.setdefault("reasons", ())
    return canonical_json_hash(payload)


def reconstructed_bar_comparison_rows_hash(
    rows: tuple[ReconstructedBarComparisonRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def reconstructed_bar_comparison_report_id_for(
    *,
    reconstruction_report_id: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    source_ids: tuple[str, ...],
    source_bar_source_ids: tuple[str, ...],
    venue: str,
    venue_symbol: str,
    hyperliquid_coin: str | None,
    bucket_seconds: int,
    price_tolerance: float,
    volume_tolerance: float,
    quote_volume_tolerance: float,
    row_manifest_hash: str,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "report_type": "reconstructed_bar_comparison_report",
            "reconstruction_report_id": reconstruction_report_id,
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "source_ids": source_ids,
            "source_bar_source_ids": source_bar_source_ids,
            "venue": venue,
            "venue_symbol": venue_symbol,
            "hyperliquid_coin": hyperliquid_coin,
            "bucket_seconds": bucket_seconds,
            "price_tolerance": price_tolerance,
            "volume_tolerance": volume_tolerance,
            "quote_volume_tolerance": quote_volume_tolerance,
            "row_manifest_hash": row_manifest_hash,
            "blocker_reasons": blocker_reasons,
        }
    )


def trade_bar_reconstruction_rows_hash(
    rows: tuple[ReconstructedTradeBarRow, ...],
) -> str:
    return manifest_rows_hash(row.model_dump(mode="json") for row in rows)


def trade_bar_reconstruction_report_id_for(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    source_ids: tuple[str, ...],
    venue: str | None,
    venue_symbol: str | None,
    hyperliquid_coin: str | None,
    bucket_seconds: int,
    expected_start_ms: int | None,
    expected_end_ms: int | None,
    row_manifest_hash: str,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "report_type": "trade_bar_reconstruction_report",
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "source_ids": source_ids,
            "venue": venue,
            "venue_symbol": venue_symbol,
            "hyperliquid_coin": hyperliquid_coin,
            "bucket_seconds": bucket_seconds,
            "expected_start_ms": expected_start_ms,
            "expected_end_ms": expected_end_ms,
            "row_manifest_hash": row_manifest_hash,
            "blocker_reasons": blocker_reasons,
        }
    )


def _validate_source_bar_set(rows: tuple[SourceNativeBarInputRow, ...]) -> None:
    first = rows[0]
    for row in rows[1:]:
        if row.native_to_hyperliquid != first.native_to_hyperliquid:
            raise ValueError("cannot mix native and external source bars")
        if row.venue != first.venue:
            raise ValueError("source bars must share one venue")
        if row.venue_symbol != first.venue_symbol:
            raise ValueError("source bars must share one venue_symbol")
        if row.hyperliquid_coin != first.hyperliquid_coin:
            raise ValueError("source bars must share one hyperliquid_coin")
        if row.market_type != first.market_type:
            raise ValueError("source bars must share one market_type")
        if row.coverage_label != first.coverage_label:
            raise ValueError("source bars must share one coverage_label")
        if row.bucket_seconds != first.bucket_seconds:
            raise ValueError("source bars must share one bucket_seconds")


def _validate_comparison_provenance(
    report: TradeBarReconstructionReport,
    source_bar: SourceNativeBarInputRow,
) -> None:
    if report.venue != source_bar.venue:
        raise ValueError("reconstructed and source bars must share one venue")
    if report.venue_symbol != source_bar.venue_symbol:
        raise ValueError("reconstructed and source bars must share one venue_symbol")
    if report.hyperliquid_coin != source_bar.hyperliquid_coin:
        raise ValueError("reconstructed and source bars must share one hyperliquid_coin")
    if report.market_type != source_bar.market_type:
        raise ValueError("reconstructed and source bars must share one market_type")
    if report.coverage_label != source_bar.coverage_label:
        raise ValueError("reconstructed and source bars must share one coverage_label")
    if report.bucket_seconds != source_bar.bucket_seconds:
        raise ValueError("reconstructed and source bars must share one bucket_seconds")
    if report.native_to_hyperliquid != source_bar.native_to_hyperliquid:
        raise ValueError("reconstructed and source bars must share native provenance")


def _unique_source_bars_by_bucket(
    rows: tuple[SourceNativeBarInputRow, ...],
) -> dict[int, SourceNativeBarInputRow]:
    by_bucket: dict[int, SourceNativeBarInputRow] = {}
    for row in rows:
        existing = by_bucket.setdefault(row.bar_start_ms, row)
        if existing is not row:
            raise ValueError("source bars contain duplicate buckets")
    return by_bucket


def _unique_reconstructed_bars_by_bucket(
    rows: tuple[ReconstructedTradeBarRow, ...],
) -> dict[int, ReconstructedTradeBarRow]:
    by_bucket: dict[int, ReconstructedTradeBarRow] = {}
    for row in rows:
        existing = by_bucket.setdefault(row.bar_start_ms, row)
        if existing is not row:
            raise ValueError("reconstructed bars contain duplicate buckets")
    return by_bucket


def _comparison_row(
    *,
    source_row: SourceNativeBarInputRow,
    reconstructed: ReconstructedTradeBarRow | None,
    price_tolerance: float,
    volume_tolerance: float,
    quote_volume_tolerance: float,
) -> ReconstructedBarComparisonRow:
    if reconstructed is None:
        payload = _comparison_payload_base(source_row=source_row)
        payload.update(
            {
                "status": "missing_reconstructed",
                "source_open": source_row.open,
                "source_high": source_row.high,
                "source_low": source_row.low,
                "source_close": source_row.close,
                "source_volume": source_row.volume,
                "source_quote_volume": source_row.quote_volume,
                "source_row_hash": source_row.source_row_hash,
                "reasons": ("missing_reconstructed_bucket",),
            }
        )
        return ReconstructedBarComparisonRow(
            **payload,
            row_hash=reconstructed_bar_comparison_row_hash(payload),
        )
    diffs = {
        "open_abs_diff": abs(source_row.open - reconstructed.open),
        "high_abs_diff": abs(source_row.high - reconstructed.high),
        "low_abs_diff": abs(source_row.low - reconstructed.low),
        "close_abs_diff": abs(source_row.close - reconstructed.close),
        "volume_abs_diff": abs(source_row.volume - reconstructed.volume),
        "quote_volume_abs_diff": abs(
            (source_row.quote_volume or 0.0) - reconstructed.quote_volume
        ),
    }
    reasons = _tolerance_reasons(
        diffs=diffs,
        price_tolerance=price_tolerance,
        volume_tolerance=volume_tolerance,
        quote_volume_tolerance=quote_volume_tolerance,
        compare_quote_volume=source_row.quote_volume is not None,
    )
    payload = _comparison_payload_base(source_row=source_row)
    payload.update(
        {
            "status": "failed" if reasons else "passed",
            "source_open": source_row.open,
            "source_high": source_row.high,
            "source_low": source_row.low,
            "source_close": source_row.close,
            "source_volume": source_row.volume,
            "source_quote_volume": source_row.quote_volume,
            "reconstructed_open": reconstructed.open,
            "reconstructed_high": reconstructed.high,
            "reconstructed_low": reconstructed.low,
            "reconstructed_close": reconstructed.close,
            "reconstructed_volume": reconstructed.volume,
            "reconstructed_quote_volume": reconstructed.quote_volume,
            "source_row_hash": source_row.source_row_hash,
            "reconstructed_row_hash": reconstructed.row_hash,
            "reasons": reasons,
        }
    )
    payload.update(diffs)
    return ReconstructedBarComparisonRow(
        **payload,
        row_hash=reconstructed_bar_comparison_row_hash(payload),
    )


def _extra_reconstructed_row(
    *,
    source_row: SourceNativeBarInputRow,
    reconstructed: ReconstructedTradeBarRow,
) -> ReconstructedBarComparisonRow:
    payload = _comparison_payload_base(source_row=source_row)
    payload.update(
        {
            "bar_start_ms": reconstructed.bar_start_ms,
            "bar_end_ms": reconstructed.bar_end_ms,
            "status": "extra_reconstructed",
            "reconstructed_open": reconstructed.open,
            "reconstructed_high": reconstructed.high,
            "reconstructed_low": reconstructed.low,
            "reconstructed_close": reconstructed.close,
            "reconstructed_volume": reconstructed.volume,
            "reconstructed_quote_volume": reconstructed.quote_volume,
            "reconstructed_row_hash": reconstructed.row_hash,
            "reasons": ("extra_reconstructed_bucket",),
        }
    )
    return ReconstructedBarComparisonRow(
        **payload,
        row_hash=reconstructed_bar_comparison_row_hash(payload),
    )


def _comparison_payload_base(source_row: SourceNativeBarInputRow) -> dict[str, Any]:
    return {
        "venue": source_row.venue,
        "venue_symbol": source_row.venue_symbol,
        "hyperliquid_coin": source_row.hyperliquid_coin,
        "market_type": source_row.market_type,
        "coverage_label": source_row.coverage_label,
        "bucket_seconds": source_row.bucket_seconds,
        "bar_start_ms": source_row.bar_start_ms,
        "bar_end_ms": source_row.bar_end_ms,
        "native_to_hyperliquid": source_row.native_to_hyperliquid,
        "accepted_historical_coverage_proof": False,
    }


def _tolerance_reasons(
    *,
    diffs: Mapping[str, float],
    price_tolerance: float,
    volume_tolerance: float,
    quote_volume_tolerance: float,
    compare_quote_volume: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    for key in ("open_abs_diff", "high_abs_diff", "low_abs_diff", "close_abs_diff"):
        if diffs[key] > price_tolerance:
            reasons.append(key.replace("_abs_diff", "_tolerance_exceeded"))
    if diffs["volume_abs_diff"] > volume_tolerance:
        reasons.append("volume_tolerance_exceeded")
    if compare_quote_volume and diffs["quote_volume_abs_diff"] > quote_volume_tolerance:
        reasons.append("quote_volume_tolerance_exceeded")
    return tuple(reasons)


def _comparison_blocker_reasons(
    rows: tuple[ReconstructedBarComparisonRow, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if any(row.status == "missing_reconstructed" for row in rows):
        reasons.append("missing_reconstructed_buckets")
    if any(row.status == "extra_reconstructed" for row in rows):
        reasons.append("extra_reconstructed_buckets")
    if any(row.status == "failed" for row in rows):
        reasons.append("ohlcv_tolerance_failed")
    return tuple(reasons)


def _comparison_report(
    *,
    reconstruction_report: TradeBarReconstructionReport,
    source_bars: tuple[SourceNativeBarInputRow, ...],
    rows: tuple[ReconstructedBarComparisonRow, ...],
    price_tolerance: float,
    volume_tolerance: float,
    quote_volume_tolerance: float,
    blocker_reasons: tuple[str, ...],
) -> ReconstructedBarComparisonReport:
    row_manifest_hash = reconstructed_bar_comparison_rows_hash(rows)
    source_bar_source_ids = tuple(sorted({row.source_id for row in source_bars}))
    report_id = reconstructed_bar_comparison_report_id_for(
        reconstruction_report_id=reconstruction_report.reconstruction_report_id,
        source_registry_ref=reconstruction_report.source_registry_ref,
        symbol_map_ref=reconstruction_report.symbol_map_ref,
        source_ids=reconstruction_report.source_ids,
        source_bar_source_ids=source_bar_source_ids,
        venue=source_bars[0].venue,
        venue_symbol=source_bars[0].venue_symbol,
        hyperliquid_coin=source_bars[0].hyperliquid_coin,
        bucket_seconds=source_bars[0].bucket_seconds,
        price_tolerance=price_tolerance,
        volume_tolerance=volume_tolerance,
        quote_volume_tolerance=quote_volume_tolerance,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
    )
    return ReconstructedBarComparisonReport(
        comparison_report_id=report_id,
        reconstruction_report_id=reconstruction_report.reconstruction_report_id,
        source_registry_ref=reconstruction_report.source_registry_ref,
        symbol_map_ref=reconstruction_report.symbol_map_ref,
        source_ids=reconstruction_report.source_ids,
        source_bar_source_ids=source_bar_source_ids,
        venue=source_bars[0].venue,
        venue_symbol=source_bars[0].venue_symbol,
        hyperliquid_coin=source_bars[0].hyperliquid_coin,
        market_type=source_bars[0].market_type,
        coverage_label=source_bars[0].coverage_label,
        bucket_seconds=source_bars[0].bucket_seconds,
        price_tolerance=price_tolerance,
        volume_tolerance=volume_tolerance,
        quote_volume_tolerance=quote_volume_tolerance,
        rows=rows,
        row_count=len(rows),
        passed=not blocker_reasons and bool(rows),
        passed_bucket_count=sum(1 for row in rows if row.status == "passed"),
        failed_bucket_count=sum(1 for row in rows if row.status == "failed"),
        missing_reconstructed_count=sum(1 for row in rows if row.status == "missing_reconstructed"),
        extra_reconstructed_count=sum(1 for row in rows if row.status == "extra_reconstructed"),
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
        native_to_hyperliquid=source_bars[0].native_to_hyperliquid,
    )


def _validate_single_provenance(rows: tuple[TradeBarInputRow, ...]) -> None:
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


def _validate_expected_window(
    rows: tuple[TradeBarInputRow, ...],
    expected_start_ms: int | None,
    expected_end_ms: int | None,
) -> None:
    for row in rows:
        if expected_start_ms is not None and row.source_timestamp_ms < expected_start_ms:
            raise ValueError("trade row is before expected_start_ms")
        if expected_end_ms is not None and row.source_timestamp_ms >= expected_end_ms:
            raise ValueError("trade row is at or after expected_end_ms")


def _reconstruct_rows(
    *,
    rows: tuple[TradeBarInputRow, ...],
    source_ids: tuple[str, ...],
    coverage_label: CoverageLabel,
    bucket_seconds: int,
) -> tuple[ReconstructedTradeBarRow, ...]:
    bucket_ms = bucket_seconds * 1000
    grouped: dict[int, list[TradeBarInputRow]] = {}
    for row in rows:
        bucket_start = (row.source_timestamp_ms // bucket_ms) * bucket_ms
        grouped.setdefault(bucket_start, []).append(row)
    output: list[ReconstructedTradeBarRow] = []
    for bucket_start, bucket_rows in sorted(grouped.items()):
        ordered = sorted(bucket_rows, key=lambda item: item.source_timestamp_ms)
        prices = [row.price for row in ordered]
        quantity = sum(row.quantity for row in ordered)
        quote_quantity = sum(
            row.quote_quantity if row.quote_quantity is not None else row.price * row.quantity
            for row in ordered
        )
        payload: dict[str, Any] = {
            "source_ids": source_ids,
            "venue": ordered[0].venue,
            "venue_symbol": ordered[0].venue_symbol,
            "hyperliquid_coin": ordered[0].hyperliquid_coin,
            "market_type": ordered[0].market_type,
            "coverage_label": coverage_label,
            "bucket_seconds": bucket_seconds,
            "bar_start_ms": bucket_start,
            "bar_end_ms": bucket_start + bucket_ms,
            "open": prices[0],
            "high": max(prices),
            "low": min(prices),
            "close": prices[-1],
            "volume": quantity,
            "quote_volume": quote_quantity,
            "trade_count": len(ordered),
            "source_row_hashes": tuple(row.source_row_hash for row in ordered if row.source_row_hash),
            "native_to_hyperliquid": ordered[0].native_to_hyperliquid,
            "accepted_historical_coverage_proof": False,
        }
        output.append(
            ReconstructedTradeBarRow(
                **payload,
                row_hash=reconstructed_trade_bar_row_hash(payload),
            )
        )
    return tuple(output)


def _reconstruction_report(
    *,
    source_registry_ref: str,
    symbol_map_ref: str,
    bucket_seconds: int,
    expected_start_ms: int | None,
    expected_end_ms: int | None,
    input_row_count: int,
    rows: tuple[ReconstructedTradeBarRow, ...],
    source_ids: tuple[str, ...] = (),
    venue: str | None = None,
    venue_symbol: str | None = None,
    hyperliquid_coin: str | None = None,
    market_type: str | None = None,
    coverage_label: CoverageLabel | None = None,
    native_to_hyperliquid: bool = False,
    source_row_hashes: tuple[str, ...] = (),
    blocker_reasons: tuple[str, ...] = (),
) -> TradeBarReconstructionReport:
    row_manifest_hash = trade_bar_reconstruction_rows_hash(rows)
    report_id = trade_bar_reconstruction_report_id_for(
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        bucket_seconds=bucket_seconds,
        expected_start_ms=expected_start_ms,
        expected_end_ms=expected_end_ms,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
    )
    return TradeBarReconstructionReport(
        reconstruction_report_id=report_id,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        source_ids=source_ids,
        venue=venue,
        venue_symbol=venue_symbol,
        hyperliquid_coin=hyperliquid_coin,
        market_type=market_type,
        coverage_label=coverage_label,
        bucket_seconds=bucket_seconds,
        expected_start_ms=expected_start_ms,
        expected_end_ms=expected_end_ms,
        rows=rows,
        row_count=len(rows),
        input_row_count=input_row_count,
        source_row_hashes=source_row_hashes,
        row_manifest_hash=row_manifest_hash,
        blocker_reasons=blocker_reasons,
        native_to_hyperliquid=native_to_hyperliquid,
    )
