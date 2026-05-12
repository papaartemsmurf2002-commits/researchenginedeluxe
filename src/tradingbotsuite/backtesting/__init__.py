"""Backtesting public API. Read docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md before execution-semantics edits."""

from __future__ import annotations

from tradingbotsuite.backtesting.benchmark import (
    BACKTEST_BENCHMARK_VERSION,
    write_backtest_benchmark_report,
)
from tradingbotsuite.backtesting.costs import CostBreakdown, CostModel
from tradingbotsuite.backtesting.cuda_engine import (
    CUDA_BACKTEST_ENGINE_VERSION,
    CUDA_EXECUTION_SCOPE,
    CudaFixedHoldingBacktestEngine,
    cuda_backtest_support_reason,
    cuda_runtime_evidence,
)
from tradingbotsuite.backtesting.cuda_batched_engine import (
    CUDA_BATCHED_BACKEND_NAME,
    CUDA_BATCHED_BACKTEST_ENGINE_VERSION,
    CUDA_BATCHED_EXECUTION_SCOPE,
    CudaBatchedFixedHoldingBacktestEngine,
    cuda_batched_backtest_support_reason,
)
from tradingbotsuite.backtesting.engine import (
    BACKTEST_ENGINE_VERSION,
    BacktestEngine,
    BacktestResult,
    BacktestSpec,
)
from tradingbotsuite.backtesting.execution_sim import ExecutionSimulator
from tradingbotsuite.backtesting.metrics import calculate_backtest_metrics
from tradingbotsuite.backtesting.portfolio import PortfolioAllocation, PortfolioSimulator
from tradingbotsuite.backtesting.vector_engine import (
    VECTOR_BACKTEST_ENGINE_VERSION,
    VectorBacktestEngine,
)

__all__ = [
    "BACKTEST_BENCHMARK_VERSION",
    "BACKTEST_ENGINE_VERSION",
    "BacktestEngine",
    "BacktestResult",
    "BacktestSpec",
    "CostBreakdown",
    "CostModel",
    "CUDA_BACKTEST_ENGINE_VERSION",
    "CUDA_BATCHED_BACKEND_NAME",
    "CUDA_BATCHED_BACKTEST_ENGINE_VERSION",
    "CUDA_BATCHED_EXECUTION_SCOPE",
    "CUDA_EXECUTION_SCOPE",
    "CudaBatchedFixedHoldingBacktestEngine",
    "CudaFixedHoldingBacktestEngine",
    "ExecutionSimulator",
    "PortfolioAllocation",
    "PortfolioSimulator",
    "VECTOR_BACKTEST_ENGINE_VERSION",
    "VectorBacktestEngine",
    "calculate_backtest_metrics",
    "cuda_batched_backtest_support_reason",
    "cuda_backtest_support_reason",
    "cuda_runtime_evidence",
    "write_backtest_benchmark_report",
]
