# WPR106-70 - Strategy Math Audit And Fast Research Nodes

## Purpose

Audit the current research-only strategy, entry, exit, and horizon logic
against local code and external primary references, fix any scoped math/logic
bug found during the audit, and add sub-hour exploratory discovery nodes that
can iterate before a larger exact experiment is justified.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-70-strategy-math-audit-and-fast-research-nodes.md`
- `docs/stage_reports/STAGE_R106_STRATEGY_MATH_AUDIT_AND_FAST_RESEARCH_NODES_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/backtesting/costs.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `src/tradingbotsuite/backtesting/cuda_engine.py`
- `src/tradingbotsuite/backtesting/cuda_batched_engine.py`
- `src/tradingbotsuite/strategies/range_reversion.py`
- `configs/discovery/fast_iter_knn_1h_btcusdt_v1.json`
- `configs/discovery/fast_iter_knn_1h_ethusdt_v1.json`
- `configs/discovery/fast_iter_knn_microdrift_1h_btcusdt_v1.json`
- `configs/discovery/fast_iter_knn_microdrift_1h_ethusdt_v1.json`
- `configs/discovery/fast_iter_knn_selective_1h_btcusdt_v1.json`
- `configs/discovery/fast_iter_knn_selective_1h_ethusdt_v1.json`
- `tests/unit/test_execution_simulator.py`
- `tests/backtesting/test_vector_engine_matches_reference.py`
- `tests/backtesting/test_cuda_batched_fixed_holding.py`
- `tests/contracts/test_strategy_contracts.py`

Allowed generated research-output paths:

- `data/research/discovery_runs/fast_iter_knn_1h_btcusdt_v1/**`
- `data/research/discovery_runs/fast_iter_knn_1h_ethusdt_v1/**`
- `data/research/discovery_runs/fast_iter_knn_microdrift_1h_btcusdt_v1/**`
- `data/research/discovery_runs/fast_iter_knn_microdrift_1h_ethusdt_v1/**`
- `data/research/discovery_runs/fast_iter_knn_selective_1h_btcusdt_v1/**`
- `data/research/discovery_runs/fast_iter_knn_selective_1h_ethusdt_v1/**`

Read-only evidence and reference paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/stage_reports/STAGE_R106_STRATEGY_ENTRY_EXIT_HORIZON_COMPARISON_REPORT.md`
- `docs/stage_reports/STAGE_R106_DISCOVERY_RUNTIME_PREFLIGHT_AND_COMPUTE_REDUCTION_REPORT.md`
- `data/research/operator_runs/research_autopilot/**`
- `data/research/operator_runs/historical_cycles/**`
- `data/research/operator_runs/discovery_runs/**`
- `data/research/operator_runs/frozen_entry_exit_lab/**`
- `src/tradingbotsuite/strategies/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/research_discovery/**`
- `configs/discovery/feature_column_sets_v4.json`
- `configs/discovery/exact_entry_sweep_*_durable_r104_v1.json`
- `configs/discovery/standard_entry_discovery_*_durable_r104_v1.json`

Out of scope:

- Candidate-pack creation.
- Live, paper, order-placement, sizing, runtime-mode, or promotion behavior.
- Historical-data catalog rebuilds.
- Broad runner, operator, live-boundary, or candidate-gate rewrites.
- Treating fast exploratory outputs as exact-discovery gate evidence.

## Plan

1. Use subagents for parallel read-only audit/design support.
2. Cross-check strategy math and discovery assumptions against primary
   exchange/library references.
3. Patch scoped strategy logic only if a deterministic correctness issue is
   found.
4. Add BTC/ETH fast exploratory discovery nodes biased toward the prior useful
   `1h`, cosine, `k=13` surface.
5. Run bounded fast probes and focused validation.
6. Record the audit, limits, probe results, and next large-scale decision.

## Research Boundary

All outputs are research-only, observe-only, and promotion-disabled. Fast
discovery nodes are exploratory and may not be used as live, paper,
candidate-ready, or promotion-ready evidence.

## Outcome

Status: completed on 2026-06-07.

- Fixed three scoped correctness issues: latency entry pricing now uses the
  latency bar open, funding costs accept provider-backed funding-rate aliases,
  and range reversion no longer fabricates a side when stretch is absent.
- Added six fast BTC/ETH 1h KNN exploratory configs and ran 208 successful
  exploratory trials under the 1-hour compute limit.
- Found no interesting candidate and no justification for a larger
  threshold-only KNN optimization. The next useful phase is sparse-event
  construction before scaling.
- Reported evidence and validation in
  `docs/stage_reports/STAGE_R106_STRATEGY_MATH_AUDIT_AND_FAST_RESEARCH_NODES_REPORT.md`.
