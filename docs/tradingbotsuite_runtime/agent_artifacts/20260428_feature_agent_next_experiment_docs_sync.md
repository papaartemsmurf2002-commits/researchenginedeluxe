# Feature Agent Next Experiment Docs Sync

## Agent

Feature Agent

## Task Received

Update planning docs with the selected next experiment matrix. Update Markdown only. Add the next-experiment matrix summary to `HMM_MULTI_KNN_REALIZATION_PLAN.md` or `HMM_MULTI_KNN_AGENT_RUNBOOK.md`. Keep wording explicit that experiments are offline research only.

## Command Run

```powershell
rg -n "Architecture Gap Triage|Next research iteration|experiment|research-only" docs/tradingbotsuite_runtime
```

## Files Read

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_backtest_agent_next_experiment_matrix.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_execution_risk_next_experiment_boundary_review.md`
- Relevant next-experiment spec hits surfaced by the requested search.

## Files Changed

- `docs/tradingbotsuite_runtime/HMM_MULTI_KNN_REALIZATION_PLAN.md`
- `docs/tradingbotsuite_runtime/agent_artifacts/20260428_feature_agent_next_experiment_docs_sync.md`

## Sync Summary

Added `Next Experiment Matrix Summary` to the realization plan under `Architecture Gap Triage`.

The planning doc now captures the selected staged matrix:

- Stage A: current-artifact diagnostics.
- Stage B: data and label regeneration.
- Stage C: implementation-backed experiments.

It also lists the top ten selected experiments:

1. Regenerate BTC dataset with exchange-context quality gates.
2. Regenerate labels with full triple-barrier audit fields.
3. Regime flip-cooldown sensitivity.
4. KNN small-K softmax sweep.
5. KNN observed-core feature subset.
6. Regime posterior threshold sensitivity.
7. Regime entropy threshold sensitivity.
8. KNN price-trend-WT3D subset.
9. Meta threshold diagnostic ladder.
10. Monitoring red-to-yellow acceptance overlay.

## Offline Research Boundary

The realization plan now explicitly states:

- all next experiments are offline research only;
- experiments must use cloned research configs, local or explicitly authorized historical datasets, and temp or explicit research output directories;
- outputs must keep `research_only: true`, `promotion_ready: false`, and monitoring `observe_only: true`;
- no experiment may feed HMM/KNN outputs into live gates, sizing, Hyperliquid execution, safety behavior, runtime-mode switching, or operator live controls;
- dataset regeneration must not use current-only websocket/order-book state to backfill historical rows.

## Validation Notes

- No Python or test files were changed.
- No tests were run because this task was Markdown-only.
- The selected matrix was sourced from `20260428_backtest_agent_next_experiment_matrix.md` and bounded by `20260428_execution_risk_next_experiment_boundary_review.md`.

## Open Issues

- None for this documentation sync.

## Handoff Notes

- Backtest/Data/Regime/KNN/Meta/Monitoring agents should treat the realization plan matrix as the planning summary, and the detailed agent artifacts as the implementation specs.
- Any future experiment runner should write manifests, metrics, diagnostics, and monitoring reports into explicit research experiment directories and must preserve the offline research-only boundary.
