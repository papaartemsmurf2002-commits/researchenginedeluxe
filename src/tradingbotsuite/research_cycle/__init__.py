"""Historical research-cycle API. Read docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md before orchestration edits."""

from __future__ import annotations

from tradingbotsuite.research_cycle.benchmark import ResearchCycleBenchmarkResult, write_research_cycle_benchmark_report
from tradingbotsuite.research_cycle.runner import HistoricalResearchCycleResult, run_historical_research_cycle
from tradingbotsuite.research_cycle.spec import HistoricalResearchCycleSpec

__all__ = [
    "HistoricalResearchCycleResult",
    "HistoricalResearchCycleSpec",
    "ResearchCycleBenchmarkResult",
    "run_historical_research_cycle",
    "write_research_cycle_benchmark_report",
]
