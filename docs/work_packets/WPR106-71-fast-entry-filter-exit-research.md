# WPR106-71 - Fast Entry Filter Exit Research

## Purpose

Continue the research-only search for possible profitable strategy candidates by
testing entry surfaces separately from filters and exit models. Focus on small,
fast experiments that can identify whether any entry/filter/exit combination is
worth a later large-compute optimization.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-71-fast-entry-filter-exit-research.md`
- `docs/stage_reports/STAGE_R106_FAST_ENTRY_FILTER_EXIT_RESEARCH_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `configs/research/fast_exit_probe_btcusdt_r106_v1.json`
- `configs/research/fast_exit_probe_ethusdt_r106_v1.json`
- `configs/research/fast_filter_probe_btcusdt_r106_v1.json`
- `configs/research/fast_filter_probe_ethusdt_r106_v1.json`
- `configs/discovery/fast_iter_knn_sparse_events_btcusdt_v1.json`
- `configs/discovery/fast_iter_knn_sparse_events_ethusdt_v1.json`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/research_cycle/spec.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- `tests/contracts/test_backtest_contracts.py`
- `tests/contracts/test_research_cycle_contract.py`
- `tests/backtesting/test_exit_policy_expansion.py`
- `tests/historical/test_full_cycle_synthetic.py`

Allowed generated research-output paths:

- `data/research/historical_cycles/fast_exit_probe_btcusdt_r106_v1/**`
- `data/research/historical_cycles/fast_exit_probe_ethusdt_r106_v1/**`
- `data/research/historical_cycles/fast_filter_probe_btcusdt_r106_v1/**`
- `data/research/historical_cycles/fast_filter_probe_ethusdt_r106_v1/**`
- `data/research/discovery_runs/fast_iter_knn_sparse_events_btcusdt_v1/**`
- `data/research/discovery_runs/fast_iter_knn_sparse_events_ethusdt_v1/**`
- `data/research/operator_runs/r106_71_frozen_entry_exit_micro_lab_btcusdt_v1/**`
- `data/research/operator_runs/r106_71_frozen_entry_exit_micro_lab_ethusdt_v1/**`

Read-only evidence and reference paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/stage_reports/STAGE_R106_STRATEGY_MATH_AUDIT_AND_FAST_RESEARCH_NODES_REPORT.md`
- `docs/stage_reports/STAGE_R106_STRATEGY_ENTRY_EXIT_HORIZON_COMPARISON_REPORT.md`
- `configs/research/full_cycle_btcusdt_durable_public_archive_r104_v1.json`
- `configs/research/full_cycle_ethusdt_durable_public_archive_r104_v1.json`
- `configs/research/full_cycle_btcusdt_candidate_blueprints_v1.json`
- `configs/research/full_cycle_ethusdt_candidate_blueprints_blocked_v1.json`
- `configs/discovery/discovery_exit_lab_v4.json`
- `configs/discovery/filter_ablation_matrix_v5.json`
- `configs/discovery/perp_filter_ablation_matrix_v4.json`
- `data/research/fixtures/*_public_archive_multi_window_v1/**`
- `data/research/fixtures/*_context_provider_latest_month_v1/**`
- `data/research/historical_cycles/**`
- `data/research/discovery_runs/**`
- `data/research/operator_runs/**`
- `src/tradingbotsuite/backtesting/**`
- `src/tradingbotsuite/research_cycle/**`
- `src/tradingbotsuite/strategies/**`

Out of scope:

- Candidate-pack creation.
- Live, paper, order-placement, sizing, runtime-mode, or promotion behavior.
- Historical-data catalog rebuilds.
- Broad feature-provider rewrites.
- Treating fast exploratory outputs as candidate-ready evidence.

## Plan

1. Use read-only subagents to map exit-tooling and entry/filter evidence.
2. Identify the smallest existing experiment path for separating entries,
   filters, and exits.
3. Add fast BTC/ETH research-only configs or a narrowly scoped exit-policy
   addition only if existing policies cannot express the requested base exits.
4. Run bounded probes under local fast-compute constraints.
5. Compare entry-only baseline, filter-gated variants, and exit-policy variants
   against fixed-hold/base exits.
6. Record whether anything deserves larger compute, and why.

## Research Boundary

All outputs are research-only, observe-only, and promotion-disabled. No result
from this packet may be used as live, paper, candidate-pack, or promotion-ready
evidence without a later gate process.

## Outcome

Completed 2026-06-07.

Added fast research-only BTC/ETH configs for durable public-archive exit probes
and latest-window entry/filter/exit probes. The durable public-archive fast exit
probes produced zero trades because the available fast-probe feature frame had
only 32 rows and 100 percent missingness on the rolling features needed by the
tested strategies. The latest-window diagnostic probes identified two promising
next research directions: ETH `trend_following_v1` at 24h/72h with
`simple_runner_v1` or `trailing_atr_after_profit`, and BTC
`volatility_breakout_v1` at 72h with the same two exits.

Ran frozen-entry KNN sparse exit labs on 24h/512 and 72h/256 cooldown slices.
The exit policies improved some comparisons versus fixed hold, but all best
KNN sparse results remained negative, so KNN should not receive large-compute
optimization until a better sparse-event selector is added.

Added and resolved `ISSUE-R106-021` after context exits crashed the fast context
cycles when required raw context columns were absent from the execution frame.
The research-cycle runner now writes fail-closed blocked backtest artifacts for
context-exit column gaps, preserves the `last_funding_rate` execution alias, and
keeps the cycle alive. BTC/ETH fast-filter probes were rerun with
`funding_aware_exit_v1` restored; both completed and wrote blocked rows for
price-feature funding-aware candidates without context instead of crashing.

Stage report:
`docs/stage_reports/STAGE_R106_FAST_ENTRY_FILTER_EXIT_RESEARCH_REPORT.md`
