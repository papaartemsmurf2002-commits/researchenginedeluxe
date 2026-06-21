# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_backtest_engine
"""V2 backtest-engine bounded context."""

from __future__ import annotations

from tradingbotsuite.v2.backtest_engine.artifacts import (
    BacktestMetrics,
    BacktestRunConfig,
    BacktestRunResult,
    EngineLane,
    MissingDataPolicy,
    RunArtifactRef,
    RunManifest,
    RunStatus,
    StrategyContext,
    ValidationStatus,
)
from tradingbotsuite.v2.backtest_engine.engine import (
    BacktestEngineError,
    recompute_metrics_from_run_manifest,
    run_event_driven_backtest,
    run_event_driven_placeholder,
    run_vectorized_backtest,
)
from tradingbotsuite.v2.backtest_engine.jobs import run_backtest_job

__all__ = [
    "BacktestEngineError",
    "BacktestMetrics",
    "BacktestRunConfig",
    "BacktestRunResult",
    "EngineLane",
    "MissingDataPolicy",
    "RunArtifactRef",
    "RunManifest",
    "RunStatus",
    "StrategyContext",
    "ValidationStatus",
    "recompute_metrics_from_run_manifest",
    "run_backtest_job",
    "run_event_driven_backtest",
    "run_event_driven_placeholder",
    "run_vectorized_backtest",
]
