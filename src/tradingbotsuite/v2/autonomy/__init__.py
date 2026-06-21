# V2-AUDIT-ID: V2-AUD-AUTONOMY-001
# V2-CONTRACTS: docs/contracts/autonomy_loop_contract.md
# V2-BOUNDARY: research_only, sandbox_diagnostic, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_autonomy
"""Research-only autonomy dry-run loop for v2."""

from __future__ import annotations

from tradingbotsuite.v2.autonomy.runner import AutonomyLoopError, run_autonomy_dry_run
from tradingbotsuite.v2.autonomy.schemas import (
    AutonomyDataMode,
    AutonomyBlockerReport,
    AutonomyDryRunConfig,
    AutonomyDryRunManifest,
    AutonomyDryRunResult,
    AutonomyLoopStatus,
    AutonomyStepResult,
    AutonomyStepStatus,
)

__all__ = [
    "AutonomyBlockerReport",
    "AutonomyDataMode",
    "AutonomyDryRunConfig",
    "AutonomyDryRunManifest",
    "AutonomyDryRunResult",
    "AutonomyLoopError",
    "AutonomyLoopStatus",
    "AutonomyStepResult",
    "AutonomyStepStatus",
    "run_autonomy_dry_run",
]
