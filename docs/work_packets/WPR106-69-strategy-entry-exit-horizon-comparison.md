# WPR106-69 - Strategy Entry Exit Horizon Comparison

## Purpose

Compare available research-only strategy evidence across entry models, exit
models, and horizons, then identify durable trends and the easiest next
development path without launching new long-running compute.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-69-strategy-entry-exit-horizon-comparison.md`
- `docs/stage_reports/STAGE_R106_STRATEGY_ENTRY_EXIT_HORIZON_COMPARISON_REPORT.md`

Read-only evidence paths:

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md`
- `docs/stage_reports/STAGE_R106_LATEST_AUTOPILOT_RUN_RESEARCH_ANALYSIS_REPORT.md`
- `docs/stage_reports/STAGE_R106_DISCOVERY_RUNTIME_PREFLIGHT_AND_COMPUTE_REDUCTION_REPORT.md`
- `data/research/operator_runs/research_autopilot/**`
- `data/research/operator_runs/historical_cycles/**`
- `data/research/operator_runs/discovery_runs/**`
- `data/research/operator_runs/frozen_entry_exit_lab/**`
- `data/research/operator_runs/analysis/**`
- `data/research/operator_runs/analysis_deltas/**`

Out of scope:

- Source-code changes.
- Generated artifact rewrites.
- Historical-data catalog rebuilds, historical-cycle reruns, exact-discovery
  reruns, exit-lab reruns, or optimizer sweeps.
- Candidate-pack creation.
- Live, paper, order-placement, sizing, runtime-mode, or promotion behavior.

## Plan

1. Inventory the latest and prior valid research artifacts by symbol.
2. Compare transparent historical-cycle strategy families across horizons and
   feature sets.
3. Compare valid discovery/KNN entry evidence against the latest failed
   discovery run and prior stable discovery blockers.
4. Compare frozen-entry exit-lab evidence against fixed-holding controls.
5. Record trends, weak evidence, and the lowest-compute next research path.

## Research Boundary

This packet is analysis-only. All conclusions remain research-only,
observe-only, and promotion-disabled. No artifact may be treated as a live or
paper signal.

## Outcome

- Compared latest candidate-depth historical-cycle strategy evidence by entry
  family, fixed-holding exit, and horizon.
- Compared prior valid KNN exact-discovery lead evidence against the latest
  failed exact-discovery run.
- Compared replay-overlay KNN entries and frozen-entry exit-lab outputs for
  fixed holding versus `simple_runner_v1`.
- Scanned all local candidate-ranking artifacts for older context/funding/OI
  strategy trends and rejected-gate status.
- Wrote report:
  `docs/stage_reports/STAGE_R106_STRATEGY_ENTRY_EXIT_HORIZON_COMPARISON_REPORT.md`.
- No source code, generated artifacts, candidate packs, live/paper/runtime
  behavior, order placement, sizing, or promotion claim was changed.
