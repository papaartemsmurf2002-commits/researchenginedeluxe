# V2-AUDIT-ID: V2-AUD-BTDATA-001
# V2-CONTRACTS: docs/contracts/backtest_data_service_contract.md
# V2-BOUNDARY: research_only, coverage_gate, no_live_imports
# V2-OWNER: v2_backtest_data
"""V2 backtest-data bounded context."""

from __future__ import annotations

from tradingbotsuite.v2.backtest_data.coverage_gate import (
    CoverageGateError,
    require_coverage_for_evidence,
)
from tradingbotsuite.v2.backtest_data.jobs import run_backtest_data_job
from tradingbotsuite.v2.backtest_data.lockbox import (
    LockboxWindow,
    latest_full_calendar_month_lockbox,
    windows_overlap,
)
from tradingbotsuite.v2.backtest_data.schemas import (
    BacktestDataManifest,
    BacktestDataRequest,
    BacktestDataSlice,
    BacktestEvidenceMode,
)
from tradingbotsuite.v2.backtest_data.service import BacktestDataError, BacktestDataService

__all__ = [
    "BacktestDataError",
    "BacktestDataManifest",
    "BacktestDataRequest",
    "BacktestDataService",
    "BacktestDataSlice",
    "BacktestEvidenceMode",
    "CoverageGateError",
    "LockboxWindow",
    "latest_full_calendar_month_lockbox",
    "require_coverage_for_evidence",
    "run_backtest_data_job",
    "windows_overlap",
]
