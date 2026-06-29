# V2-AUDIT-ID: V2-AUD-PKG-001
# V2-CONTRACTS: docs/PRODUCT_SCOPE.md
# V2-BOUNDARY: research_only, no_live_imports, no_order_or_sizing
# V2-OWNER: v2_backtest_engine
"""V2 backtest-engine bounded context."""

from __future__ import annotations

from tradingbotsuite.v2.backtest_engine.artifacts import (
    ArtifactMode,
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
from tradingbotsuite.v2.backtest_engine.benchmarks import (
    BacktestBenchmarkConfig,
    BacktestBenchmarkReport,
    BenchmarkTier,
    run_archive_backtest_benchmark,
)
from tradingbotsuite.v2.backtest_engine.engine import (
    BacktestEngineError,
    recompute_metrics_from_run_manifest,
    run_event_driven_backtest,
    run_event_driven_placeholder,
    run_vectorized_backtest,
)
from tradingbotsuite.v2.backtest_engine.fast_lane import (
    FastLaneMetricDiff,
    FastLaneParityReport,
    FastLaneParityStatus,
    FullArtifactReplayMetricDiff,
    FullArtifactReplayPlan,
    FullArtifactReplayVerification,
    FullArtifactReplayVerificationStatus,
    ReferenceRerunPlan,
    audit_fast_lane_parity,
    build_full_artifact_replay_plan,
    build_reference_rerun_plan,
    select_reference_audit_sample,
    verify_full_artifact_replay,
)
from tradingbotsuite.v2.backtest_engine.jobs import run_backtest_job

__all__ = [
    "BacktestEngineError",
    "BacktestBenchmarkConfig",
    "BacktestBenchmarkReport",
    "BenchmarkTier",
    "ArtifactMode",
    "BacktestMetrics",
    "BacktestRunConfig",
    "BacktestRunResult",
    "EngineLane",
    "FastLaneMetricDiff",
    "FastLaneParityReport",
    "FastLaneParityStatus",
    "FullArtifactReplayMetricDiff",
    "FullArtifactReplayPlan",
    "FullArtifactReplayVerification",
    "FullArtifactReplayVerificationStatus",
    "MissingDataPolicy",
    "ReferenceRerunPlan",
    "RunArtifactRef",
    "RunManifest",
    "RunStatus",
    "StrategyContext",
    "ValidationStatus",
    "audit_fast_lane_parity",
    "build_full_artifact_replay_plan",
    "build_reference_rerun_plan",
    "recompute_metrics_from_run_manifest",
    "run_archive_backtest_benchmark",
    "run_backtest_job",
    "run_event_driven_backtest",
    "run_event_driven_placeholder",
    "run_vectorized_backtest",
    "select_reference_audit_sample",
    "verify_full_artifact_replay",
]
