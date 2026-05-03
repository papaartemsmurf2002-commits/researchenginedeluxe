# Known Issues

Last updated: 2026-05-03

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
| P1 | 0 | 0 | 2 | 0 |
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
