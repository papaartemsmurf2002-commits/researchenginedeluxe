# V2-AUDIT-ID: V2-AUD-QUAL-001
# V2-CONTRACTS: docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, coverage_gate, no_live_imports
# V2-OWNER: v2_data_quality
"""V2 data-quality bounded context."""

from __future__ import annotations

from tradingbotsuite.v2.data_quality.coverage import (
    coverage_report_for_bars,
    expected_bar_count,
    timeframe_to_timedelta,
)
from tradingbotsuite.v2.data_quality.jobs import run_data_quality_job
from tradingbotsuite.v2.data_quality.schemas import CoverageReport, DataQualityCheck

__all__ = [
    "CoverageReport",
    "DataQualityCheck",
    "coverage_report_for_bars",
    "expected_bar_count",
    "run_data_quality_job",
    "timeframe_to_timedelta",
]
