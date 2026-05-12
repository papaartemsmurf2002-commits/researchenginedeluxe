# WPR97-05 Fastest Exact Default Polish

Status: closed
Owner: Codex Research Agent
Stage: R97 aggressive CUDA/TensorCore stability search

## Goal

Finish the R97 runtime polish by making the default research-cycle compute
policy explicitly select the fastest parity-safe route available in the current
engine:

- CPU vector aggregate screening for supported fixed-holding primary-bar
  workloads.
- Reference validation under `auto`.
- Explicit CUDA/Tensor Core profiles only when requested for GPU evidence.
- 15 aggregate CPU workers by default, matching the branch performance plan.

## Allowed Paths

- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/**`
- `docs/work_packets/**`
- `src/tradingbotsuite/research_cycle/**`
- `tests/contracts/**`
- `tests/historical/**`

## Non-Goals

- Do not change live trading, live config, order placement, promotion readiness,
  or sizing logic.
- Do not make CUDA/Tensor Core evidence satisfy candidate gates directly.
- Do not weaken reference validation, comparator, exit-lab, validation-floor, or
  research-only boundaries.
- Do not change backtesting math or strategy signals.

## Plan

1. Add a `fastest_exact` compute profile and make it the default.
2. Set default `cpu_threads` to 15 for aggregate screening.
3. Keep `conservative` as a backward-compatible CPU/vector profile.
4. Make performance-plan and fallback evidence distinguish
   `fastest_exact` from old conservative routing.
5. Update tests and close with focused validation plus a default full-cycle
   smoke.

## Exit Evidence

- Added `fastest_exact` as the default compute profile.
- Set default aggregate CPU workers to 15.
- Preserved explicit CUDA/Tensor Core routing and reference validation under
  `auto`.
- Added distinct performance-plan/fallback evidence for fastest-exact vector
  selection.
- Validation and default smoke evidence are recorded in
  `docs/stage_reports/STAGE_R97_FASTEST_EXACT_DEFAULT_POLISH_REPORT.md`.
