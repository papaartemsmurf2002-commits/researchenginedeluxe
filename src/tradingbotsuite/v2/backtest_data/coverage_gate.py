# V2-AUDIT-ID: V2-AUD-BTDATA-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md, docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, coverage_gate, no_live_imports
# V2-OWNER: v2_backtest_data
"""Coverage gate integration point for future v2 backtest-data reads."""

from __future__ import annotations

from tradingbotsuite.v2.data_quality.schemas import (
    DEFAULT_COVERAGE_MIN,
    CoverageReport,
    EvidenceMode,
)


class CoverageGateError(ValueError):
    """Raised when a coverage report cannot support accepted research evidence."""


def require_coverage_for_evidence(
    report: CoverageReport,
    *,
    coverage_min: float = DEFAULT_COVERAGE_MIN,
) -> CoverageReport:
    """Return the report only when it can support accepted research evidence."""

    blockers = list(report.blocker_reasons)
    if report.evidence_mode == EvidenceMode.SANDBOX_DIAGNOSTIC:
        blockers.append("sandbox_diagnostic_non_evidence")
    if report.coverage_ratio < coverage_min and "coverage_below_minimum" not in blockers:
        blockers.append("coverage_below_minimum")
    if not report.evidence_eligible:
        blockers.append("coverage_report_not_evidence_eligible")
    if blockers:
        unique_blockers = tuple(dict.fromkeys(blockers))
        raise CoverageGateError(
            "coverage gate failed: " + ",".join(unique_blockers)
        )
    return report
