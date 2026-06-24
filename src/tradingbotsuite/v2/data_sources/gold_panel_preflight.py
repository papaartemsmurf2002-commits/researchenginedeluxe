# V2-AUDIT-ID: V2-AUD-DATASRC-048
# V2-CONTRACTS: docs/contracts/data_family_coverage_contract.md, docs/contracts/gold_research_panel_contract.md
# V2-BOUNDARY: research_only, no_archive_writes, no_gold_panel_rows
# V2-OWNER: v2_data_sources
"""Multi-symbol coverage and gold-panel preflight helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.data_sources.coverage_gates import (
    DataFamilyCoverageGateResult,
    evaluate_data_family_coverage_gate,
)
from tradingbotsuite.v2.data_sources.feature_reconstruction import (
    BBOFeatureReport,
    CrossVenueBasisFeatureReport,
    DerivativesContextFeatureReport,
    L2DepthFeatureReport,
    OrderflowFeatureReport,
)
from tradingbotsuite.v2.data_sources.gold_panels import (
    GoldResearchPanelFeatureRef,
    GoldResearchPanelManifest,
    build_gold_research_panel_manifest,
)
from tradingbotsuite.v2.data_sources.schemas import (
    ALLOWED_DATA_FAMILIES,
    CoverageLabel,
    DataFamilyCoverageReport,
)
from tradingbotsuite.v2.security.boundary import require_research_boundary


FeatureReconstructionReport = (
    OrderflowFeatureReport
    | DerivativesContextFeatureReport
    | BBOFeatureReport
    | L2DepthFeatureReport
    | CrossVenueBasisFeatureReport
)


class DataFamilyCoverageSymbolSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    summary_type: str = "data_family_coverage_symbol_summary"
    summary_id: str = Field(min_length=64, max_length=64)
    symbol: str = Field(min_length=1)
    universe_snapshot_ref: str = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    archive_snapshot_ref: str | None = None
    required_families: tuple[str, ...] = Field(min_length=1)
    coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
    coverage_report_count: int = Field(ge=0)
    accepted_report_count: int = Field(ge=0)
    report_ids: tuple[str, ...] = ()
    accepted_family_report_ids: dict[str, str] = Field(default_factory=dict)
    missing_families: tuple[str, ...] = ()
    rejected_families: tuple[str, ...] = ()
    coverage_gate_id: str = Field(min_length=64, max_length=64)
    coverage_gate_passed: bool = False
    blocker_reasons: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
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
    def _validate_summary(self) -> "DataFamilyCoverageSymbolSummary":
        require_research_boundary(self, context="data family coverage symbol summary")
        if self.summary_type != "data_family_coverage_symbol_summary":
            raise ValueError("summary_type must be data_family_coverage_symbol_summary")
        if tuple(sorted(set(self.required_families))) != self.required_families:
            raise ValueError("required_families must be sorted and unique")
        if self.coverage_report_count != len(self.report_ids):
            raise ValueError("coverage_report_count must match report_ids length")
        if self.accepted_report_count > self.coverage_report_count:
            raise ValueError("accepted_report_count cannot exceed coverage_report_count")
        if self.coverage_gate_passed:
            if self.blocker_reasons:
                raise ValueError("passed symbol summaries cannot carry blocker reasons")
            if self.missing_families or self.rejected_families:
                raise ValueError("passed symbol summaries cannot carry missing or rejected families")
            if set(self.accepted_family_report_ids) != set(self.required_families):
                raise ValueError("passed symbol summaries require accepted reports for every family")
        elif not self.blocker_reasons:
            raise ValueError("blocked symbol summaries require blocker reasons")
        if self.accepted_historical_coverage_proof:
            raise ValueError("symbol coverage summaries are not accepted coverage proof")
        expected_id = data_family_coverage_symbol_summary_id_for(
            symbol=self.symbol,
            universe_snapshot_ref=self.universe_snapshot_ref,
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            archive_snapshot_ref=self.archive_snapshot_ref,
            required_families=self.required_families,
            coverage_min=self.coverage_min,
            report_ids=self.report_ids,
            accepted_family_report_ids=self.accepted_family_report_ids,
            missing_families=self.missing_families,
            rejected_families=self.rejected_families,
            coverage_gate_id=self.coverage_gate_id,
            coverage_gate_passed=self.coverage_gate_passed,
            blocker_reasons=self.blocker_reasons,
        )
        if self.summary_id != expected_id:
            raise ValueError("summary_id does not match data-family coverage symbol summary")
        return self


class GoldPanelPreflightSymbolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    result_type: str = "gold_panel_preflight_symbol_result"
    result_id: str = Field(min_length=64, max_length=64)
    symbol: str = Field(min_length=1)
    coverage_summary: DataFamilyCoverageSymbolSummary
    coverage_gate: DataFamilyCoverageGateResult
    feature_report_ids: tuple[str, ...] = ()
    accepted_feature_report_ids: tuple[str, ...] = ()
    feature_refs: tuple[GoldResearchPanelFeatureRef, ...] = ()
    feature_ref_count: int = Field(ge=0)
    gold_panel_manifest: GoldResearchPanelManifest
    panel_ready: bool = False
    blocker_reasons: tuple[str, ...] = ()
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
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
    def _validate_result(self) -> "GoldPanelPreflightSymbolResult":
        require_research_boundary(self, context="gold panel preflight symbol result")
        if self.result_type != "gold_panel_preflight_symbol_result":
            raise ValueError("result_type must be gold_panel_preflight_symbol_result")
        if self.coverage_summary.symbol != self.symbol:
            raise ValueError("coverage summary symbol mismatch")
        if self.coverage_gate.symbol != self.symbol:
            raise ValueError("coverage gate symbol mismatch")
        if self.gold_panel_manifest.symbol != self.symbol:
            raise ValueError("gold panel manifest symbol mismatch")
        if self.coverage_summary.coverage_gate_id != self.coverage_gate.gate_id:
            raise ValueError("coverage summary gate ID mismatch")
        if self.gold_panel_manifest.coverage_gate_id != self.coverage_gate.gate_id:
            raise ValueError("gold panel manifest gate ID mismatch")
        if self.feature_ref_count != len(self.feature_refs):
            raise ValueError("feature_ref_count must match feature_refs length")
        if self.panel_ready != self.gold_panel_manifest.panel_ready:
            raise ValueError("panel_ready must match gold panel manifest readiness")
        if self.panel_ready and self.blocker_reasons:
            raise ValueError("ready preflight symbols cannot carry blocker reasons")
        if not self.panel_ready and not self.blocker_reasons:
            raise ValueError("blocked preflight symbols require blocker reasons")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel preflight symbols are not accepted coverage proof")
        expected_id = gold_panel_preflight_symbol_result_id_for(
            symbol=self.symbol,
            coverage_summary_id=self.coverage_summary.summary_id,
            coverage_gate_id=self.coverage_gate.gate_id,
            feature_report_ids=self.feature_report_ids,
            accepted_feature_report_ids=self.accepted_feature_report_ids,
            feature_ref_ids=tuple(_feature_ref_identity(ref) for ref in self.feature_refs),
            gold_panel_id=self.gold_panel_manifest.panel_id,
            panel_ready=self.panel_ready,
            blocker_reasons=self.blocker_reasons,
        )
        if self.result_id != expected_id:
            raise ValueError("result_id does not match gold panel preflight symbol result")
        return self


class GoldPanelPreflightResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    result_type: str = "gold_panel_preflight_result"
    preflight_id: str = Field(min_length=64, max_length=64)
    panel_name: str = Field(min_length=1)
    interval: str = Field(min_length=1)
    symbols: tuple[str, ...] = Field(min_length=1)
    required_families: tuple[str, ...] = Field(min_length=1)
    coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
    universe_snapshot_ref: str = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    archive_snapshot_ref: str | None = None
    symbol_results: tuple[GoldPanelPreflightSymbolResult, ...] = Field(min_length=1)
    symbol_count: int = Field(ge=1)
    ready_symbol_count: int = Field(ge=0)
    blocked_symbol_count: int = Field(ge=0)
    panel_manifest_ids: tuple[str, ...] = ()
    blocker_reasons: tuple[str, ...] = ()
    all_symbols_ready: bool = False
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
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
    def _validate_preflight(self) -> "GoldPanelPreflightResult":
        require_research_boundary(self, context="gold panel preflight result")
        if self.result_type != "gold_panel_preflight_result":
            raise ValueError("result_type must be gold_panel_preflight_result")
        if tuple(sorted(set(self.symbols))) != self.symbols:
            raise ValueError("symbols must be sorted and unique")
        if tuple(sorted(set(self.required_families))) != self.required_families:
            raise ValueError("required_families must be sorted and unique")
        if self.symbol_count != len(self.symbol_results):
            raise ValueError("symbol_count must match symbol_results length")
        if self.symbol_count != len(self.symbols):
            raise ValueError("symbol_count must match symbols length")
        if self.ready_symbol_count != sum(1 for result in self.symbol_results if result.panel_ready):
            raise ValueError("ready_symbol_count does not match symbol results")
        if self.blocked_symbol_count != self.symbol_count - self.ready_symbol_count:
            raise ValueError("blocked_symbol_count does not match symbol results")
        expected_manifest_ids = tuple(result.gold_panel_manifest.panel_id for result in self.symbol_results)
        if self.panel_manifest_ids != expected_manifest_ids:
            raise ValueError("panel_manifest_ids must match symbol result manifests")
        if self.all_symbols_ready != (self.ready_symbol_count == self.symbol_count):
            raise ValueError("all_symbols_ready does not match symbol readiness")
        if self.all_symbols_ready and self.blocker_reasons:
            raise ValueError("ready preflight results cannot carry blocker reasons")
        if not self.all_symbols_ready and not self.blocker_reasons:
            raise ValueError("blocked preflight results require blocker reasons")
        if self.accepted_historical_coverage_proof:
            raise ValueError("gold panel preflight results are not accepted coverage proof")
        expected_id = gold_panel_preflight_result_id_for(
            panel_name=self.panel_name,
            interval=self.interval,
            symbols=self.symbols,
            required_families=self.required_families,
            coverage_min=self.coverage_min,
            universe_snapshot_ref=self.universe_snapshot_ref,
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            archive_snapshot_ref=self.archive_snapshot_ref,
            symbol_result_ids=tuple(result.result_id for result in self.symbol_results),
            panel_manifest_ids=self.panel_manifest_ids,
            all_symbols_ready=self.all_symbols_ready,
            blocker_reasons=self.blocker_reasons,
        )
        if self.preflight_id != expected_id:
            raise ValueError("preflight_id does not match gold panel preflight result")
        return self


def preflight_gold_research_panels(
    *,
    coverage_reports: Iterable[DataFamilyCoverageReport | Mapping[str, Any]],
    feature_reports: Iterable[FeatureReconstructionReport | Mapping[str, Any] | BaseModel],
    symbols: Iterable[str],
    required_families: Iterable[str],
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    panel_name: str,
    interval: str,
    archive_snapshot_ref: str | None = None,
    coverage_min: float = 0.98,
) -> GoldPanelPreflightResult:
    declared_symbols = _sorted_unique(symbols, field_name="symbols")
    required = _sorted_unique(required_families, field_name="required_families")
    unknown_families = sorted(set(required) - ALLOWED_DATA_FAMILIES)
    if unknown_families:
        raise ValueError("unknown required families: " + ",".join(unknown_families))
    reports = tuple(
        report
        if isinstance(report, DataFamilyCoverageReport)
        else DataFamilyCoverageReport.model_validate(dict(report))
        for report in coverage_reports
    )
    parsed_feature_reports = tuple(_parse_feature_report(report) for report in feature_reports)
    _validate_coverage_report_context(
        reports=reports,
        symbols=declared_symbols,
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
    )
    _validate_feature_report_context(
        reports=parsed_feature_reports,
        symbols=declared_symbols,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
    )

    symbol_results: list[GoldPanelPreflightSymbolResult] = []
    for symbol in declared_symbols:
        symbol_reports = tuple(report for report in reports if report.symbol == symbol)
        gate = evaluate_data_family_coverage_gate(
            coverage_reports=symbol_reports,
            required_families=required,
            universe_snapshot_ref=universe_snapshot_ref,
            source_registry_ref=source_registry_ref,
            symbol_map_ref=symbol_map_ref,
            archive_snapshot_ref=archive_snapshot_ref,
            symbol=symbol,
            coverage_min=coverage_min,
        )
        summary = _coverage_symbol_summary(
            symbol=symbol,
            gate=gate,
            reports=symbol_reports,
        )
        symbol_feature_reports = tuple(
            report for report in parsed_feature_reports if _feature_report_symbol(report) == symbol
        )
        feature_refs, feature_blockers, accepted_feature_report_ids = _feature_refs_for_symbol(
            reports=symbol_feature_reports,
            required_families=required,
        )
        manifest = build_gold_research_panel_manifest(
            coverage_gate=gate,
            feature_refs=feature_refs,
            panel_name=panel_name,
            interval=interval,
            symbol=symbol,
        )
        blockers = _unique(
            (
                *summary.blocker_reasons,
                *feature_blockers,
                *manifest.blocker_reasons,
            )
        )
        symbol_results.append(
            _gold_panel_preflight_symbol_result(
                symbol=symbol,
                coverage_summary=summary,
                coverage_gate=gate,
                feature_report_ids=tuple(sorted(report.feature_report_id for report in symbol_feature_reports)),
                accepted_feature_report_ids=accepted_feature_report_ids,
                feature_refs=feature_refs,
                gold_panel_manifest=manifest,
                blocker_reasons=blockers,
            )
        )

    return _gold_panel_preflight_result(
        panel_name=panel_name,
        interval=interval,
        symbols=declared_symbols,
        required_families=required,
        coverage_min=coverage_min,
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol_results=tuple(symbol_results),
    )


def data_family_coverage_symbol_summary_id_for(
    *,
    symbol: str,
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None,
    required_families: tuple[str, ...],
    coverage_min: float,
    report_ids: tuple[str, ...],
    accepted_family_report_ids: dict[str, str],
    missing_families: tuple[str, ...],
    rejected_families: tuple[str, ...],
    coverage_gate_id: str,
    coverage_gate_passed: bool,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "summary_type": "data_family_coverage_symbol_summary",
            "symbol": symbol,
            "universe_snapshot_ref": universe_snapshot_ref,
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "archive_snapshot_ref": archive_snapshot_ref,
            "required_families": required_families,
            "coverage_min": coverage_min,
            "report_ids": report_ids,
            "accepted_family_report_ids": accepted_family_report_ids,
            "missing_families": missing_families,
            "rejected_families": rejected_families,
            "coverage_gate_id": coverage_gate_id,
            "coverage_gate_passed": coverage_gate_passed,
            "blocker_reasons": blocker_reasons,
        }
    )


def gold_panel_preflight_symbol_result_id_for(
    *,
    symbol: str,
    coverage_summary_id: str,
    coverage_gate_id: str,
    feature_report_ids: tuple[str, ...],
    accepted_feature_report_ids: tuple[str, ...],
    feature_ref_ids: tuple[str, ...],
    gold_panel_id: str,
    panel_ready: bool,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "result_type": "gold_panel_preflight_symbol_result",
            "symbol": symbol,
            "coverage_summary_id": coverage_summary_id,
            "coverage_gate_id": coverage_gate_id,
            "feature_report_ids": feature_report_ids,
            "accepted_feature_report_ids": accepted_feature_report_ids,
            "feature_ref_ids": feature_ref_ids,
            "gold_panel_id": gold_panel_id,
            "panel_ready": panel_ready,
            "blocker_reasons": blocker_reasons,
        }
    )


def gold_panel_preflight_result_id_for(
    *,
    panel_name: str,
    interval: str,
    symbols: tuple[str, ...],
    required_families: tuple[str, ...],
    coverage_min: float,
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None,
    symbol_result_ids: tuple[str, ...],
    panel_manifest_ids: tuple[str, ...],
    all_symbols_ready: bool,
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "result_type": "gold_panel_preflight_result",
            "panel_name": panel_name,
            "interval": interval,
            "symbols": symbols,
            "required_families": required_families,
            "coverage_min": coverage_min,
            "universe_snapshot_ref": universe_snapshot_ref,
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "archive_snapshot_ref": archive_snapshot_ref,
            "symbol_result_ids": symbol_result_ids,
            "panel_manifest_ids": panel_manifest_ids,
            "all_symbols_ready": all_symbols_ready,
            "blocker_reasons": blocker_reasons,
        }
    )


def gold_panel_feature_refs_from_report(
    report: FeatureReconstructionReport | Mapping[str, Any] | BaseModel,
    *,
    required_families: Iterable[str] | None = None,
) -> tuple[GoldResearchPanelFeatureRef, ...]:
    parsed = _parse_feature_report(report)
    required = None if required_families is None else set(_sorted_unique(required_families, field_name="required_families"))
    refs, blockers = _feature_refs_from_report(parsed, required_families=required)
    if blockers:
        return ()
    return refs


def _coverage_symbol_summary(
    *,
    symbol: str,
    gate: DataFamilyCoverageGateResult,
    reports: tuple[DataFamilyCoverageReport, ...],
) -> DataFamilyCoverageSymbolSummary:
    report_ids = tuple(sorted(report.coverage_report_id for report in reports))
    accepted_report_count = sum(
        1
        for report in reports
        if report.accepted_for_research_reporting
        and report.coverage_ratio >= gate.coverage_min
        and not report.reason
    )
    summary_id = data_family_coverage_symbol_summary_id_for(
        symbol=symbol,
        universe_snapshot_ref=gate.universe_snapshot_ref,
        source_registry_ref=gate.source_registry_ref,
        symbol_map_ref=gate.symbol_map_ref,
        archive_snapshot_ref=gate.archive_snapshot_ref,
        required_families=gate.required_families,
        coverage_min=gate.coverage_min,
        report_ids=report_ids,
        accepted_family_report_ids=gate.accepted_family_report_ids,
        missing_families=gate.missing_families,
        rejected_families=gate.rejected_families,
        coverage_gate_id=gate.gate_id,
        coverage_gate_passed=gate.passed,
        blocker_reasons=gate.blocker_reasons,
    )
    return DataFamilyCoverageSymbolSummary(
        summary_id=summary_id,
        symbol=symbol,
        universe_snapshot_ref=gate.universe_snapshot_ref,
        source_registry_ref=gate.source_registry_ref,
        symbol_map_ref=gate.symbol_map_ref,
        archive_snapshot_ref=gate.archive_snapshot_ref,
        required_families=gate.required_families,
        coverage_min=gate.coverage_min,
        coverage_report_count=len(report_ids),
        accepted_report_count=accepted_report_count,
        report_ids=report_ids,
        accepted_family_report_ids=gate.accepted_family_report_ids,
        missing_families=gate.missing_families,
        rejected_families=gate.rejected_families,
        coverage_gate_id=gate.gate_id,
        coverage_gate_passed=gate.passed,
        blocker_reasons=gate.blocker_reasons,
    )


def _gold_panel_preflight_symbol_result(
    *,
    symbol: str,
    coverage_summary: DataFamilyCoverageSymbolSummary,
    coverage_gate: DataFamilyCoverageGateResult,
    feature_report_ids: tuple[str, ...],
    accepted_feature_report_ids: tuple[str, ...],
    feature_refs: tuple[GoldResearchPanelFeatureRef, ...],
    gold_panel_manifest: GoldResearchPanelManifest,
    blocker_reasons: tuple[str, ...],
) -> GoldPanelPreflightSymbolResult:
    result_id = gold_panel_preflight_symbol_result_id_for(
        symbol=symbol,
        coverage_summary_id=coverage_summary.summary_id,
        coverage_gate_id=coverage_gate.gate_id,
        feature_report_ids=feature_report_ids,
        accepted_feature_report_ids=accepted_feature_report_ids,
        feature_ref_ids=tuple(_feature_ref_identity(ref) for ref in feature_refs),
        gold_panel_id=gold_panel_manifest.panel_id,
        panel_ready=gold_panel_manifest.panel_ready,
        blocker_reasons=blocker_reasons,
    )
    return GoldPanelPreflightSymbolResult(
        result_id=result_id,
        symbol=symbol,
        coverage_summary=coverage_summary,
        coverage_gate=coverage_gate,
        feature_report_ids=feature_report_ids,
        accepted_feature_report_ids=accepted_feature_report_ids,
        feature_refs=feature_refs,
        feature_ref_count=len(feature_refs),
        gold_panel_manifest=gold_panel_manifest,
        panel_ready=gold_panel_manifest.panel_ready,
        blocker_reasons=blocker_reasons,
    )


def _gold_panel_preflight_result(
    *,
    panel_name: str,
    interval: str,
    symbols: tuple[str, ...],
    required_families: tuple[str, ...],
    coverage_min: float,
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None,
    symbol_results: tuple[GoldPanelPreflightSymbolResult, ...],
) -> GoldPanelPreflightResult:
    blockers = _unique(tuple(reason for result in symbol_results for reason in result.blocker_reasons))
    ready_symbol_count = sum(1 for result in symbol_results if result.panel_ready)
    all_symbols_ready = ready_symbol_count == len(symbol_results)
    panel_manifest_ids = tuple(result.gold_panel_manifest.panel_id for result in symbol_results)
    preflight_id = gold_panel_preflight_result_id_for(
        panel_name=panel_name,
        interval=interval,
        symbols=symbols,
        required_families=required_families,
        coverage_min=coverage_min,
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol_result_ids=tuple(result.result_id for result in symbol_results),
        panel_manifest_ids=panel_manifest_ids,
        all_symbols_ready=all_symbols_ready,
        blocker_reasons=blockers,
    )
    return GoldPanelPreflightResult(
        preflight_id=preflight_id,
        panel_name=panel_name,
        interval=interval,
        symbols=symbols,
        required_families=required_families,
        coverage_min=coverage_min,
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol_results=symbol_results,
        symbol_count=len(symbol_results),
        ready_symbol_count=ready_symbol_count,
        blocked_symbol_count=len(symbol_results) - ready_symbol_count,
        panel_manifest_ids=panel_manifest_ids,
        blocker_reasons=blockers,
        all_symbols_ready=all_symbols_ready,
    )


def _feature_refs_for_symbol(
    *,
    reports: tuple[FeatureReconstructionReport, ...],
    required_families: tuple[str, ...],
) -> tuple[tuple[GoldResearchPanelFeatureRef, ...], tuple[str, ...], tuple[str, ...]]:
    refs: list[GoldResearchPanelFeatureRef] = []
    blockers: list[str] = []
    accepted_report_ids: list[str] = []
    required = set(required_families)
    for report in sorted(reports, key=lambda item: item.feature_report_id):
        report_refs, report_blockers = _feature_refs_from_report(report, required_families=required)
        if report_blockers:
            blockers.extend(report_blockers)
            continue
        accepted_report_ids.append(report.feature_report_id)
        refs.extend(report_refs)
    refs_by_identity = {_feature_ref_identity(ref): ref for ref in refs}
    ordered_refs = tuple(refs_by_identity[key] for key in sorted(refs_by_identity))
    return ordered_refs, _unique(tuple(blockers)), tuple(sorted(set(accepted_report_ids)))


def _feature_refs_from_report(
    report: FeatureReconstructionReport,
    *,
    required_families: set[str] | None,
) -> tuple[tuple[GoldResearchPanelFeatureRef, ...], tuple[str, ...]]:
    blockers = _feature_report_blockers(report, required_families=required_families)
    if blockers:
        return (), blockers
    if isinstance(report, OrderflowFeatureReport):
        return _orderflow_refs(report), ()
    if isinstance(report, DerivativesContextFeatureReport):
        return _derivatives_context_refs(report), ()
    if isinstance(report, BBOFeatureReport):
        return _static_report_refs(report, family="bbo", feature_names=("mid_price", "spread", "spread_bps", "top_size_imbalance")), ()
    if isinstance(report, L2DepthFeatureReport):
        return _static_report_refs(report, family="l2_snapshots", feature_names=("bid_depth", "ask_depth", "total_depth", "depth_imbalance")), ()
    if isinstance(report, CrossVenueBasisFeatureReport):
        return _static_report_refs(report, family="basis", feature_names=("primary_price", "comparison_price", "basis_abs", "basis_bps")), ()
    raise TypeError(f"unsupported feature report type: {type(report).__name__}")


def _feature_report_blockers(
    report: FeatureReconstructionReport,
    *,
    required_families: set[str] | None,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if report.row_count == 0:
        blockers.append(f"feature_report_empty:{report.feature_report_id}")
    if report.blocker_reasons:
        blockers.append(f"feature_report_blocked:{report.feature_report_id}")
    if not report.source_ids:
        blockers.append(f"feature_report_missing_source_ids:{report.feature_report_id}")
    if report.coverage_label is None:
        blockers.append(f"feature_report_missing_coverage_label:{report.feature_report_id}")
    families = _feature_report_families(report)
    if required_families is not None and not set(families).intersection(required_families):
        blockers.append(f"feature_report_has_no_required_family:{report.feature_report_id}")
    return tuple(blockers)


def _orderflow_refs(report: OrderflowFeatureReport) -> tuple[GoldResearchPanelFeatureRef, ...]:
    return tuple(
        _feature_ref(
            report=report,
            family="trades",
            feature_name=feature_name,
            row_count=report.row_count,
        )
        for feature_name in (
            "trade_count",
            "total_volume",
            "total_quote_volume",
            "buy_volume",
            "sell_volume",
            "vwap",
            "trade_imbalance",
            "quote_trade_imbalance",
        )
    )


def _derivatives_context_refs(
    report: DerivativesContextFeatureReport,
) -> tuple[GoldResearchPanelFeatureRef, ...]:
    refs: list[GoldResearchPanelFeatureRef] = []
    feature_keys_by_family: dict[str, set[str]] = {}
    row_counts: dict[tuple[str, str], int] = {}
    for row in report.rows:
        for key in row.numeric_features:
            feature_keys_by_family.setdefault(row.family, set()).add(key)
            row_counts[(row.family, key)] = row_counts.get((row.family, key), 0) + 1
    for family in sorted(feature_keys_by_family):
        for feature_name in sorted(feature_keys_by_family[family]):
            refs.append(
                _feature_ref(
                    report=report,
                    family=family,
                    feature_name=feature_name,
                    row_count=row_counts[(family, feature_name)],
                )
            )
    return tuple(refs)


def _static_report_refs(
    report: FeatureReconstructionReport,
    *,
    family: str,
    feature_names: tuple[str, ...],
) -> tuple[GoldResearchPanelFeatureRef, ...]:
    return tuple(
        _feature_ref(
            report=report,
            family=family,
            feature_name=feature_name,
            row_count=report.row_count,
        )
        for feature_name in feature_names
    )


def _feature_ref(
    *,
    report: FeatureReconstructionReport,
    family: str,
    feature_name: str,
    row_count: int,
) -> GoldResearchPanelFeatureRef:
    coverage_label = report.coverage_label
    if coverage_label is None:
        raise ValueError("feature report coverage_label is required")
    column_name = _feature_column_name(report=report, family=family, feature_name=feature_name)
    return GoldResearchPanelFeatureRef(
        column_name=column_name,
        family=family,
        feature_report_id=report.feature_report_id,
        source_registry_ref=report.source_registry_ref,
        symbol_map_ref=report.symbol_map_ref,
        source_ids=report.source_ids,
        venue=report.venue if hasattr(report, "venue") else None,
        venue_symbol=report.venue_symbol if hasattr(report, "venue_symbol") else None,
        coverage_label=coverage_label,
        row_count=row_count,
        row_manifest_hash=report.row_manifest_hash,
        nullable=False,
        coverage_flag_column=f"coverage_flag_{family}",
        native_to_hyperliquid=report.native_to_hyperliquid,
    )


def _feature_column_name(
    *,
    report: FeatureReconstructionReport,
    family: str,
    feature_name: str,
) -> str:
    prefix = "hl" if report.native_to_hyperliquid else _safe_column_part(_report_venue(report) or "external")
    return "_".join(
        part
        for part in (
            prefix,
            _safe_column_part(family),
            _safe_column_part(feature_name),
        )
        if part
    )


def _feature_report_families(report: FeatureReconstructionReport) -> tuple[str, ...]:
    if isinstance(report, OrderflowFeatureReport):
        return ("trades",)
    if isinstance(report, DerivativesContextFeatureReport):
        return report.families
    if isinstance(report, BBOFeatureReport):
        return ("bbo",)
    if isinstance(report, L2DepthFeatureReport):
        return ("l2_snapshots",)
    if isinstance(report, CrossVenueBasisFeatureReport):
        return ("basis",)
    raise TypeError(f"unsupported feature report type: {type(report).__name__}")


def _feature_report_symbol(report: FeatureReconstructionReport) -> str:
    symbol = getattr(report, "hyperliquid_coin", None) or getattr(report, "venue_symbol", None)
    if not symbol:
        raise ValueError(f"feature report missing symbol context: {report.feature_report_id}")
    return str(symbol)


def _report_venue(report: FeatureReconstructionReport) -> str | None:
    if isinstance(report, CrossVenueBasisFeatureReport):
        return "cross_venue"
    return getattr(report, "venue", None)


def _parse_feature_report(
    report: FeatureReconstructionReport | Mapping[str, Any] | BaseModel,
) -> FeatureReconstructionReport:
    if isinstance(
        report,
        (
            OrderflowFeatureReport,
            DerivativesContextFeatureReport,
            BBOFeatureReport,
            L2DepthFeatureReport,
            CrossVenueBasisFeatureReport,
        ),
    ):
        return report
    payload = report.model_dump(mode="json") if isinstance(report, BaseModel) else dict(report)
    report_type = payload.get("report_type")
    if report_type == "orderflow_feature_reconstruction_report":
        return OrderflowFeatureReport.model_validate(payload)
    if report_type == "derivatives_context_feature_reconstruction_report":
        return DerivativesContextFeatureReport.model_validate(payload)
    if report_type == "bbo_spread_feature_reconstruction_report":
        return BBOFeatureReport.model_validate(payload)
    if report_type == "l2_depth_feature_reconstruction_report":
        return L2DepthFeatureReport.model_validate(payload)
    if report_type == "cross_venue_basis_feature_reconstruction_report":
        return CrossVenueBasisFeatureReport.model_validate(payload)
    raise ValueError(f"unsupported feature report_type: {report_type}")


def _validate_coverage_report_context(
    *,
    reports: tuple[DataFamilyCoverageReport, ...],
    symbols: tuple[str, ...],
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None,
) -> None:
    declared = set(symbols)
    for report in reports:
        if report.symbol not in declared:
            raise ValueError("coverage report symbol outside declared symbols")
        if report.universe_snapshot_ref != universe_snapshot_ref:
            raise ValueError("coverage report universe_snapshot_ref mismatch")
        if report.source_registry_ref != source_registry_ref:
            raise ValueError("coverage report source_registry_ref mismatch")
        if report.symbol_map_ref != symbol_map_ref:
            raise ValueError("coverage report symbol_map_ref mismatch")
        if archive_snapshot_ref is not None and report.archive_snapshot_ref != archive_snapshot_ref:
            raise ValueError("coverage report archive_snapshot_ref mismatch")


def _validate_feature_report_context(
    *,
    reports: tuple[FeatureReconstructionReport, ...],
    symbols: tuple[str, ...],
    source_registry_ref: str,
    symbol_map_ref: str,
) -> None:
    declared = set(symbols)
    for report in reports:
        if _feature_report_symbol(report) not in declared:
            raise ValueError("feature report symbol outside declared symbols")
        if report.source_registry_ref != source_registry_ref:
            raise ValueError("feature report source_registry_ref mismatch")
        if report.symbol_map_ref != symbol_map_ref:
            raise ValueError("feature report symbol_map_ref mismatch")


def _feature_ref_identity(ref: GoldResearchPanelFeatureRef) -> str:
    return canonical_json_hash(
        {
            "column_name": ref.column_name,
            "family": ref.family,
            "feature_report_id": ref.feature_report_id,
            "row_manifest_hash": ref.row_manifest_hash,
            "row_count": ref.row_count,
            "coverage_flag_column": ref.coverage_flag_column,
        }
    )


def _sorted_unique(values: Iterable[str], *, field_name: str) -> tuple[str, ...]:
    output = tuple(sorted({str(value) for value in values if str(value)}))
    if not output:
        raise ValueError(f"{field_name} must not be empty")
    return output


def _safe_column_part(value: str) -> str:
    output = []
    previous_underscore = False
    for char in value.lower():
        if char.isalnum():
            output.append(char)
            previous_underscore = False
        elif not previous_underscore:
            output.append("_")
            previous_underscore = True
    return "".join(output).strip("_")


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def gold_panel_preflight_symbol_results_hash(
    results: tuple[GoldPanelPreflightSymbolResult, ...],
) -> str:
    return manifest_rows_hash(result.model_dump(mode="json") for result in results)
