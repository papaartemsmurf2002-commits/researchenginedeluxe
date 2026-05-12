# Known Issues

Last updated: 2026-05-12

This registry is the blocking issue source for orchestrator stage gates.

Severity levels:

- P0: safety, data leakage, live trading risk, corrupt data, branch boundary violation.
- P1: invalid backtest assumption, non-deterministic experiment, broken artifact contract, severe performance blocker.
- P2: incomplete docs, minor missing tests, non-blocking refactor debt.
- P3: polish and convenience.

Stage advancement stop rule:

- Any open P0 blocks stage advancement.
- Four or more unresolved P1 issues block stage advancement.
- P2/P3 can carry forward only with explicit orchestrator note and owner.

## Current summary

| Severity | Open | In progress | Resolved | Accepted debt |
| --- | ---: | ---: | ---: | ---: |
| P0 | 0 | 0 | 0 | 0 |
| P1 | 1 | 0 | 4 | 0 |
| P2 | 0 | 0 | 0 | 0 |
| P3 | 0 | 0 | 0 | 0 |

## ISSUE-R1-001: Research branch still contains live execution surfaces

Severity: P1
Stage discovered: Stage 1 - Repo cartography
Owner: Orchestrator Agent / Live Safety Agent
Status: resolved
Paths affected: `run_manual.py`, `run_live_smoke.py`, `src/tradingbotsuite/adapters/execution.py`, `src/tradingbotsuite/core/engine.py`, `src/tradingbotsuite/runtime.py`, `src/tradingbotsuite/web/operator.py`, `src/tradingbot/live.py`, `src/tradingbot/data/hyperliquid.py`

### Problem

The research branch carries live-adjacent launchers and execution adapters. This does not prove research modules are placing orders, but it increases branch-boundary risk and must be isolated or guarded before any later research artifact can be interpreted as live-ready.

### Evidence

Stage 1 cartography identified Hyperliquid execution adapters, manual runtime launchers, operator commands, and legacy `tradingbot` live paths on `research/v3-experimental-engine`.

### Required resolution

Stage 2 must formalize import and artifact contracts. Stage 10/11 must keep live execution on the live branch and require promotion/shadow validation before any research output reaches live runtime behavior.

### Resolution notes

Stage 2 added `docs/contracts/boundary_contract.md` and `tests/contracts/test_import_boundaries.py` to prevent research modules from importing order-placement paths. Stage 10/11 added live preflight and promotion/shadow validation so research outputs cannot become live execution inputs without explicit later approval.

## ISSUE-R1-002: Research CLI and live/operator CLI are coupled in one entry module

Severity: P1
Stage discovered: Stage 1 - Repo cartography
Owner: Orchestrator Agent / Documentation Agent
Status: resolved
Paths affected: `src/tradingbotsuite/main.py`, `src/tradingbotsuite/operator_console.py`, `src/tradingbotsuite/web/operator.py`

### Problem

`src/tradingbotsuite/main.py` exposes live/operator commands and research commands in the same module, and the operator UI can queue research jobs. This needs explicit contract documentation and later enforcement so live mode cannot run research jobs.

### Evidence

Stage 1 command inventory found `serve`, `manual`, `smoke-live`, `build-dataset`, `train-model`, `calibrate-model`, `replay-eval`, HMM/KNN commands, provider fetch commands, and experiment commands in the same CLI module.

### Required resolution

Stage 2 should document command ownership and boundary rules. Stage 10 should enforce live-mode rejection of research jobs.

### Resolution notes

Stage 2 documented command ownership in `docs/contracts/boundary_contract.md`. Stage 10 added `src/tradingbotsuite/live/preflight.py`, CLI guards in `src/tradingbotsuite/main.py`, and tests in `tests/live/test_preflight.py` so live mode rejects research commands before execution. Stage 12.1 added the new `plan-feature-ablation` research command to the same live rejection set.

## ISSUE-R44-001: Final crosscheck found research evidence hygiene blockers

Severity: P1
Stage discovered: Stage R44 - Final crosscheck hardening
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/research_cycle/benchmark.py`, `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/backtesting/splits.py`, `src/tradingbotsuite/optimization/stability.py`, `src/tradingbotsuite/research/market_data.py`, `src/tradingbotsuite/research/feature_ablation.py`, `.gitignore`, `data/research/fixtures/btcusdt_context_provider_latest_month_v1/**`

### Problem

The final crosscheck found several issues that could weaken reproducibility or evidence truthfulness before push: relative benchmark output paths could recurse under generated spec locations, provider benchmark evidence depended on an ignored fixture, non-contiguous holdout splits could include unrelated rows, stability and ablation grouping omitted exit-policy identity, fixed-interval context manifests did not detect gaps, and generic feature-ablation runs could be labeled validation-incomplete when all configured evidence was executable.

### Evidence

Independent agent review and full-suite validation identified the benchmark path risk, ignored provider fixture risk, split/evidence grouping issues, context gap reporting issue, and failing tests in benchmark artifact accounting, removed-source boundaries, and feature-ablation execution scope.

### Required resolution

Before commit/push, make provider fixture evidence durable, resolve benchmark paths to absolute directories, use short generated backtest run directory names, preserve exact holdout membership, include exit-policy identity in stability/ablation grouping, make context gap checks interval-aware, and rerun focused plus full validation.

### Resolution notes

Stage R44 fixes implemented all required changes and added regression coverage. The provider latest-month fixture pack is unignored for commit. Focused validation passed, WPR42 provider benchmark was rerun without filename-length warnings, and full validation is recorded in the R44 stage report.

## ISSUE-R58-001: OI contraction exit accepted non-finite context

Severity: P1
Stage discovered: Stage R58 - OI contraction exit policy
Owner: Codex Research Agent
Status: resolved
Paths affected: `src/tradingbotsuite/backtesting/exits.py`, `tests/backtesting/test_exit_policy_expansion.py`

### Problem

The new `oi_contraction_exit_v1` policy initially treated infinite OI values as valid row-level context. A row with infinite OI notional and negative-infinite OI delta/z-score could trigger an exit instead of failing closed to the normal time exit.

### Evidence

Final review of the WPR58 diff reproduced an `oi_contraction_exit_v1` trigger on non-finite OI context, contradicting the stage report's row-level missing or non-finite context behavior.

### Required resolution

Reject non-finite values in optional numeric context conversion and add regression coverage for `inf` and `-inf` OI rows.

### Resolution notes

Stage R58 updated `_optional_numeric` to return no context for non-finite numbers and added `test_oi_contraction_exit_skips_non_finite_oi_context`. Focused validation passed after the fix.

## ISSUE-R95-001: CUDA backtest backend absent for NVIDIA acceleration path

Severity: P1
Stage discovered: Stage R95 - Performance candidate-selection engine crosscheck
Owner: Codex Research Agent
Status: open
Paths affected: `src/tradingbotsuite/research_cycle/runner.py`, `src/tradingbotsuite/backtesting/**`, `src/tradingbotsuite/optimization/**`

### Problem

The research-cycle candidate-selection path can now record NVIDIA/CUDA preference and run aggregate candidate backtests with bounded CPU workers, but no concrete CUDA/GPU backtest backend is registered. GPU acceleration therefore cannot truthfully be claimed for candidate search or stability-region evaluation yet.

### Evidence

WPR95 crosscheck found only reference and fixed-holding vector CPU backtest backends. The performance plan reports `blocked_no_cuda_backtest_backend_registered` whenever GPU acceleration is requested.

### Required resolution

Add a validated CUDA-capable research backtest or feature-evaluation backend with backend evidence, parity checks against the reference engine, deterministic artifact identity, and fallback behavior before any NVIDIA speedup claim is allowed.

### Resolution notes

Open. Current mitigation is explicit artifact truthfulness plus CPU aggregate-backtest parallelism via `compute.cpu_threads`.

## Issue template

```markdown
## ISSUE-ID: Short title

Severity: P0/P1/P2/P3
Stage discovered:
Owner:
Status: open | in_progress | resolved | accepted_debt
Paths affected:

### Problem

### Evidence

### Required resolution

### Resolution notes
```
