# V2-AUDIT-ID: V2-AUD-DATASRC-043
# V2-CONTRACTS: docs/contracts/data_family_coverage_contract.md
# V2-BOUNDARY: research_only, no_archive_writes, no_gold_panel_claim
# V2-OWNER: v2_data_sources
"""Data-family coverage gates for v2 research readiness checks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tradingbotsuite.v2.archive.hashing import canonical_json_hash, manifest_rows_hash
from tradingbotsuite.v2.config.schemas import V2_SCHEMA_VERSION
from tradingbotsuite.v2.config.time import utc_now
from tradingbotsuite.v2.data_sources.schemas import DataFamilyCoverageReport
from tradingbotsuite.v2.security.boundary import require_research_boundary


class DataFamilyCoverageGateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = V2_SCHEMA_VERSION
    gate_type: str = "data_family_coverage_gate"
    gate_id: str = Field(min_length=64, max_length=64)
    universe_snapshot_ref: str = Field(min_length=1)
    source_registry_ref: str = Field(min_length=1)
    symbol_map_ref: str = Field(min_length=1)
    archive_snapshot_ref: str | None = None
    symbol: str = Field(min_length=1)
    required_families: tuple[str, ...] = Field(min_length=1)
    coverage_min: float = Field(default=0.98, ge=0.0, le=1.0)
    report_ids: tuple[str, ...] = ()
    accepted_family_report_ids: dict[str, str] = Field(default_factory=dict)
    missing_families: tuple[str, ...] = ()
    rejected_families: tuple[str, ...] = ()
    report_manifest_hash: str = Field(min_length=64, max_length=64)
    blocker_reasons: tuple[str, ...] = ()
    passed: bool = False
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
    def _validate_gate(self) -> "DataFamilyCoverageGateResult":
        require_research_boundary(self, context="data family coverage gate")
        if self.gate_type != "data_family_coverage_gate":
            raise ValueError("gate_type must be data_family_coverage_gate")
        if tuple(sorted(set(self.required_families))) != self.required_families:
            raise ValueError("required_families must be sorted and unique")
        if self.passed:
            if self.blocker_reasons:
                raise ValueError("passed coverage gates cannot carry blocker reasons")
            if self.missing_families or self.rejected_families:
                raise ValueError("passed coverage gates cannot carry missing or rejected families")
            if set(self.accepted_family_report_ids) != set(self.required_families):
                raise ValueError("passed coverage gates require accepted reports for every family")
        elif not self.blocker_reasons:
            raise ValueError("blocked coverage gates require blocker reasons")
        if self.accepted_historical_coverage_proof:
            raise ValueError("coverage gate results are not accepted historical coverage proof")
        expected_id = data_family_coverage_gate_id_for(
            universe_snapshot_ref=self.universe_snapshot_ref,
            source_registry_ref=self.source_registry_ref,
            symbol_map_ref=self.symbol_map_ref,
            archive_snapshot_ref=self.archive_snapshot_ref,
            symbol=self.symbol,
            required_families=self.required_families,
            coverage_min=self.coverage_min,
            report_manifest_hash=self.report_manifest_hash,
            missing_families=self.missing_families,
            rejected_families=self.rejected_families,
            blocker_reasons=self.blocker_reasons,
        )
        if self.gate_id != expected_id:
            raise ValueError("gate_id does not match data-family coverage gate")
        return self


def evaluate_data_family_coverage_gate(
    *,
    coverage_reports: Iterable[DataFamilyCoverageReport | Mapping[str, Any]],
    required_families: Iterable[str],
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    symbol: str,
    archive_snapshot_ref: str | None = None,
    coverage_min: float = 0.98,
) -> DataFamilyCoverageGateResult:
    required = tuple(sorted(set(required_families)))
    if not required:
        raise ValueError("required_families must not be empty")
    if coverage_min < 0 or coverage_min > 1:
        raise ValueError("coverage_min must be between 0 and 1")
    reports = tuple(
        report
        if isinstance(report, DataFamilyCoverageReport)
        else DataFamilyCoverageReport.model_validate(dict(report))
        for report in coverage_reports
    )
    _validate_gate_context(
        reports=reports,
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol=symbol,
    )
    reports_by_family: dict[str, list[DataFamilyCoverageReport]] = {}
    for report in reports:
        reports_by_family.setdefault(report.family, []).append(report)
    accepted_family_report_ids: dict[str, str] = {}
    missing_families: list[str] = []
    rejected_families: list[str] = []
    for family in required:
        family_reports = sorted(
            reports_by_family.get(family, ()),
            key=lambda item: item.coverage_report_id,
        )
        if not family_reports:
            missing_families.append(family)
            continue
        accepted = [
            report
            for report in family_reports
            if report.accepted_for_research_reporting
            and report.coverage_ratio >= coverage_min
            and not report.reason
        ]
        if not accepted:
            rejected_families.append(family)
            continue
        accepted_family_report_ids[family] = accepted[0].coverage_report_id
    blockers: list[str] = []
    if not reports:
        blockers.append("empty_coverage_reports")
    if missing_families:
        blockers.append("missing_required_family")
    if rejected_families:
        blockers.append("rejected_required_family")
    passed = not blockers
    return _coverage_gate_result(
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol=symbol,
        required_families=required,
        coverage_min=coverage_min,
        reports=reports,
        accepted_family_report_ids=dict(sorted(accepted_family_report_ids.items())),
        missing_families=tuple(missing_families),
        rejected_families=tuple(rejected_families),
        blocker_reasons=tuple(blockers),
        passed=passed,
    )


def data_family_coverage_reports_hash(
    reports: tuple[DataFamilyCoverageReport, ...],
) -> str:
    return manifest_rows_hash(
        report.model_dump(mode="json")
        for report in sorted(reports, key=lambda item: item.coverage_report_id)
    )


def data_family_coverage_gate_id_for(
    *,
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None,
    symbol: str,
    required_families: tuple[str, ...],
    coverage_min: float,
    report_manifest_hash: str,
    missing_families: tuple[str, ...],
    rejected_families: tuple[str, ...],
    blocker_reasons: tuple[str, ...],
) -> str:
    return canonical_json_hash(
        {
            "gate_type": "data_family_coverage_gate",
            "universe_snapshot_ref": universe_snapshot_ref,
            "source_registry_ref": source_registry_ref,
            "symbol_map_ref": symbol_map_ref,
            "archive_snapshot_ref": archive_snapshot_ref,
            "symbol": symbol,
            "required_families": required_families,
            "coverage_min": coverage_min,
            "report_manifest_hash": report_manifest_hash,
            "missing_families": missing_families,
            "rejected_families": rejected_families,
            "blocker_reasons": blocker_reasons,
        }
    )


def _validate_gate_context(
    *,
    reports: tuple[DataFamilyCoverageReport, ...],
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None,
    symbol: str,
) -> None:
    for report in reports:
        if report.universe_snapshot_ref != universe_snapshot_ref:
            raise ValueError("coverage report universe_snapshot_ref mismatch")
        if report.source_registry_ref != source_registry_ref:
            raise ValueError("coverage report source_registry_ref mismatch")
        if report.symbol_map_ref != symbol_map_ref:
            raise ValueError("coverage report symbol_map_ref mismatch")
        if archive_snapshot_ref is not None and report.archive_snapshot_ref != archive_snapshot_ref:
            raise ValueError("coverage report archive_snapshot_ref mismatch")
        if report.symbol != symbol:
            raise ValueError("coverage report symbol mismatch")


def _coverage_gate_result(
    *,
    universe_snapshot_ref: str,
    source_registry_ref: str,
    symbol_map_ref: str,
    archive_snapshot_ref: str | None,
    symbol: str,
    required_families: tuple[str, ...],
    coverage_min: float,
    reports: tuple[DataFamilyCoverageReport, ...],
    accepted_family_report_ids: dict[str, str],
    missing_families: tuple[str, ...],
    rejected_families: tuple[str, ...],
    blocker_reasons: tuple[str, ...],
    passed: bool,
) -> DataFamilyCoverageGateResult:
    report_manifest_hash = data_family_coverage_reports_hash(reports)
    gate_id = data_family_coverage_gate_id_for(
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol=symbol,
        required_families=required_families,
        coverage_min=coverage_min,
        report_manifest_hash=report_manifest_hash,
        missing_families=missing_families,
        rejected_families=rejected_families,
        blocker_reasons=blocker_reasons,
    )
    return DataFamilyCoverageGateResult(
        gate_id=gate_id,
        universe_snapshot_ref=universe_snapshot_ref,
        source_registry_ref=source_registry_ref,
        symbol_map_ref=symbol_map_ref,
        archive_snapshot_ref=archive_snapshot_ref,
        symbol=symbol,
        required_families=required_families,
        coverage_min=coverage_min,
        report_ids=tuple(sorted(report.coverage_report_id for report in reports)),
        accepted_family_report_ids=accepted_family_report_ids,
        missing_families=missing_families,
        rejected_families=rejected_families,
        report_manifest_hash=report_manifest_hash,
        blocker_reasons=blocker_reasons,
        passed=passed,
    )
