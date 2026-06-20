# WPR106-68 - Discovery Runtime Preflight And Compute Reduction

## Purpose

Work toward `ISSUE-R106-019` by reproducing and fixing the failed no-regime
exact-discovery trial path, then add bounded preflight and compute-reduction
guards so future autopilot runs do not spend multi-day runtime on invalid or
low-value sweeps.

## Scope

Allowed edit paths:

- `docs/work_packets/WPR106-68-discovery-runtime-preflight-and-compute-reduction.md`
- `docs/stage_reports/STAGE_R106_DISCOVERY_RUNTIME_PREFLIGHT_AND_COMPUTE_REDUCTION_REPORT.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/research_discovery/**`
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/operator.py`
- `configs/discovery/exact_entry_sweep_btcusdt_durable_r104_v1.json`
- `configs/discovery/exact_entry_sweep_ethusdt_durable_r104_v1.json`
- `tests/research_discovery/**`
- `tests/tradingbotsuite/test_operator_ui.py`

Read-only evidence paths:

- `data/research/operator_runs/research_autopilot/**`
- `data/research/operator_runs/discovery_runs/**`
- `data/research/operator_runs/analysis_deltas/**`
- `docs/stage_reports/STAGE_R106_LATEST_AUTOPILOT_RUN_RESEARCH_ANALYSIS_REPORT.md`

Out of scope:

- Candidate-pack creation.
- Live, paper, order-placement, sizing, runtime-mode, or promotion behavior.
- Generated artifact rewrites outside temporary test output.
- Historical-data catalog rebuilds or full exact-discovery reruns.

## Plan

1. Reproduce the no-regime exact-discovery failure with a bounded run or focused
   unit path.
2. Fix the no-regime trial execution path without weakening regime/backend
   truthfulness validation.
3. Harden discovery accounting so failed durable trial records are counted
   separately from successful completed trials.
4. Add a preflight path that can run a representative bounded trial subset and
   fail before large exact sweeps.
5. Cut default exact-discovery compute where safe, prioritizing fewer duplicate
   threshold combinations and mandatory preflight over blind 570240-trial
   sweeps.
6. Validate with focused discovery tests, compile, and contracts if shared
   contracts are touched.

## Research Boundary

All outputs remain research-only and observe-only. This packet must not produce
candidate packs, promotion-ready artifacts, paper/live signals, or live runtime
changes.

## Outcome

- Resolved `ISSUE-R106-019`.
- Fixed the no-regime exact-discovery runtime path by passing
  `regime_model_backend` through cached KNN base materialization, preserving
  truthful `none` backend metadata for no-regime trials.
- Added large real-discovery preflight with bounded representative trials; a
  failed preflight blocks the run before full sweep execution.
- Split successful trial accounting from failed durable records in discovery
  manifests, snapshots, compute telemetry, and candidate-pack bridge checks.
- Made real-discovery runs with failed trial execution end `blocked` rather
  than analytically `completed`, while keeping durable trial records and partial
  ledgers available for debugging.
- Added operator evidence guards so failed-trial manifests and legacy
  all-`trial_execution_error` blocked ledgers cannot satisfy required exact
  discovery evidence.
- Reduced checked BTC/ETH exact discovery configs from 570240 to 3456
  research-only no-regime trials per symbol for the next bounded compute phase.
- Wrote report:
  `docs/stage_reports/STAGE_R106_DISCOVERY_RUNTIME_PREFLIGHT_AND_COMPUTE_REDUCTION_REPORT.md`.
- No candidate pack, live/paper/runtime behavior, order placement, sizing, or
  promotion claim was introduced.
