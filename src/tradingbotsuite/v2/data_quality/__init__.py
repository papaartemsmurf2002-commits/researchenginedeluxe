# V2-AUDIT-ID: V2-AUD-QUAL-001
# V2-CONTRACTS: docs/contracts/data_quality_contract.md
# V2-BOUNDARY: research_only, coverage_gate, no_live_imports
# V2-OWNER: v2_data_quality
"""V2 data-quality bounded context."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "CoverageReport",
    "DataQualityCheck",
    "coverage_report_for_bars",
    "expected_bar_count",
    "run_data_quality_job",
    "timeframe_to_timedelta",
]

_EXPORT_MODULES = {
    "CoverageReport": "tradingbotsuite.v2.data_quality.schemas",
    "DataQualityCheck": "tradingbotsuite.v2.data_quality.schemas",
    "coverage_report_for_bars": "tradingbotsuite.v2.data_quality.coverage",
    "expected_bar_count": "tradingbotsuite.v2.data_quality.coverage",
    "run_data_quality_job": "tradingbotsuite.v2.data_quality.jobs",
    "timeframe_to_timedelta": "tradingbotsuite.v2.data_quality.coverage",
}


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is not None:
        value = getattr(import_module(module_name), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
