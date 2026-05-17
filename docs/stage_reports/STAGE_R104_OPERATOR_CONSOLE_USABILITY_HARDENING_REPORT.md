# Stage R104 Operator Console Usability Hardening Report

Date: 2026-05-17
Work packet: `docs/work_packets/WPR104-03-operator-console-usability-hardening.md`
Stage status: operator usability hardening complete; empirical candidate validation still pending

## Summary

WPR104-03 hardened the operator Research console around the durable R104
candidate-validation workflow. The UI now exposes a backend-derived progress
meter, milestone statuses, next action, recommended defaults, and clearer
function blocks for BTC/ETH cycle, discovery, readiness, inspection, and
eligibility work. The UI remains a thin local operator layer over existing
operator jobs, readiness checks, artifact manifests, and feed APIs.

All surfaces remain `research_only`, `observe_only`, and `promotion_ready:
false`. No live execution, runtime-mode changes, order placement, sizing, or
promotion behavior was added.

## Implemented

- Added `/api/operator/research/progress` backed by R104 readiness, queued and
  completed operator jobs, and job-produced research manifests.
- Added durable milestones for readiness, BTC/ETH historical cycles, BTC/ETH
  discovery, and candidate eligibility review.
- Scoped the command-center active-run state to primary R104 job types so old
  secondary jobs do not block the recommended next action.
- Kept discovery milestones waiting until the matching historical-cycle
  artifact exists, so the UI run order matches backend evidence state.
- Reworked `research.html` into a command center with progress meter,
  function blocks, recommended run order, recommended defaults, maturity
  labels, and secondary diagnostics below the primary R104 path.
- Made artifact indexing non-blocking for the command center and re-rendered
  the operator board after fresh artifacts load.
- Hardened shadow diagnostics so missing legacy signal columns no longer 500
  the Research page.
- Added operator feed request payloads and backend symbol derivation for job
  timeline entries, including ETH durable jobs.
- Improved timeline job rendering with stored status, requested/started/
  finished timestamps, and clearer job detail blocks.
- Contained narrow-screen layout overflow, including the Jobs table, while
  keeping detailed inspection data available.

## Validation

- `python -m compileall -q src/tradingbotsuite`
- Focused operator progress/feed/template regression:
  - `4 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_operator_ui.py -q`
  - `41 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - `425 passed`
- `git diff --check`
  - Passed with line-ending warnings only.
- Playwright visual verification against `http://127.0.0.1:8765/ui/research`:
  - Desktop `1440x1000`: `overflowX = 0`, six milestones, four function
    blocks, next action `Run BTC durable cycle`.
  - Mobile `390x900`: `overflowX = 0`, six milestones, four function blocks,
    Jobs table contained in its own scroller, next action
    `Run BTC durable cycle`.

## Remaining R104 Work

The branch is not empirically complete. The next operation is to use the
operator console to run the durable BTC/ETH historical cycles, run BTC/ETH
discovery after the matching cycle artifacts exist, then run candidate
eligibility review. A candidate can only be considered for a later promotion
handoff if eligibility blockers, exit lab, multiple testing, validation floors,
source provenance, side/split/regime evidence, and cost/funding stress pass on
durable evidence.
