# Stage R106 Autopilot Step Transparency And Cleanliness Audit Report

Date: 2026-05-30
Work packet: `docs/work_packets/WPR106-28-autopilot-step-transparency-and-cleanliness-audit.md`
Checkout: `main`, treated as the migrated R106 checkout under the stage ledger.

## Summary

This packet audited the operator research UI/autopilot path after the latest
autopilot failures and long-run stall fixes. It found no active Python server or
autopilot process at audit time, but it did find a stale generated autopilot
manifest still marked `running`. The code now makes that state visible as a
review condition instead of letting it look like a live run.

The packet also fixed the main transparency gap for future runs: while the
autopilot is inside a helper step, the progress API and UI now show the current
step key, symbol, attempt, elapsed time, ETA, ETA basis, latest completed step,
and manifest path.

No live execution, live config, runtime mode, sizing, order placement,
candidate-pack writing, generated artifact mutation, or promotion readiness
behavior was introduced.

## Process And Artifact Findings

- `git status --short --branch` reports `main...origin/main` with existing
  WPR106 dirty worktree changes. This packet only added the WPR106-28 docs,
  operator progress/UI telemetry, and focused operator UI tests.
- No `python.exe` process was running when checked, and
  `http://127.0.0.1:8000/api/operator/research/progress` was not serving.
- The newest generated autopilot artifact was
  `data/research/operator_runs/research_autopilot/run-research-autopilot-9a4ce549dd1c4ffba99ab54449ef2a0b/research_autopilot_manifest.json`.
  It had `autopilot_status: running`, `executed_step_count: 0`, `max_steps: 100`,
  and `updated_at_utc: 2026-05-29T17:47:55.833813+00:00`, but there was no active
  process. The artifact was not rewritten; the UI/backend now classify this
  pattern as `stale_review`.
- Older failed autopilot artifacts still show the already-addressed handoff
  classes:
  - `run-research-autopilot-d77072dd939744e296edbddac253e29b` failed on stale
    `ablation_report` cycle-evidence handoff.
  - `run-research-autopilot-52719942d4604874a51a67489bbbe98a-restart-retry-1`
    failed on stale `blocked_candidates` discovery-output handoff.
  These match the WPR106-24/WPR106-25/WPR106-26 portability fixes and are not new
  blockers.

## Code Changes

- `src/tradingbotsuite/operator_console.py`
  - Records `active_step` in the autopilot manifest before a helper starts.
  - Clears `active_step` on retry, failure, success, blocked exits, and final
    completion.
  - Adds `active_autopilot_progress` to the progress API while a
    `run-research-autopilot` job is active.
  - Adds rough step ETA estimates and candidate-eligibility estimates based on
    discovery manifest counts when available.
  - Adds stale-manifest summary fields for generated autopilot artifacts:
    `telemetry_status`, `stale_review`, `stale_review_reason`,
    `last_update_age_seconds`, `active_step`, and `latest_step`.

- `src/tradingbotsuite/web/templates/research.html`
  - Shows an active autopilot progress panel before historical-data, cycle, or
    discovery fallback panels.
  - Shows current step, symbol, attempt, elapsed time, ETA, scope, ETA basis,
    latest step, and manifest path.
  - Marks stale generated autopilot manifests with a `stale_review` pill and
    displays state detail, active step, latest step, and last update age.

- `tests/tradingbotsuite/test_operator_ui.py`
  - Covers active autopilot helper telemetry while a helper is blocked.
  - Covers cleanup of `active_step` after completion.
  - Covers stale generated autopilot manifests being summarized as
    `stale_review`.

## Cleanliness And Boundary Scan

- Research-owned package scan found no Hyperliquid execution adapter imports,
  execution adapter imports, or direct `.place_order(...)` calls in the audited
  research/data/features/backtesting/strategies/optimization/research-cycle/
  discovery/artifact surfaces. The only adapter hits were Binance market-data
  imports used for data intake.
- Promotion scan found no unsafe `promotion_ready: true` assignment in the
  audited source surfaces.
- Broad `runtime_mode` and order-placement text hits are concentrated in live
  modules, engine tests, contract tests, and explicit research boundary metadata
  such as `order_placement_used: false`.
- Existing artifact indexing is bounded by the repo's artifact-path index and
  skip/cap logic. A direct ad hoc recursive PowerShell search over
  `data/research/operator_runs` timed out because the artifact tree is large;
  this was a manual audit-command limitation, not a new operator UI path
  regression.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed:
  `427 passed`.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  passed: `78 passed`.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q` passed:
  `213 passed`.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical -q` passed:
  `42 passed`.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts tests\live -q`
  passed: `93 passed`.

## Status

No new P0/P1 issue was found. The previous long-run symptom was not an active
process at audit time; it was a stale generated manifest plus insufficient UI
telemetry. Future autopilot runs should expose the current helper step and ETA
from the moment the helper starts.

Recommended operator action: restart the UI from the current checkout and rerun
autopilot from the Research page. The stale historical manifest can remain as
evidence; rewriting generated artifacts should be a separate cleanup packet only
if the team wants old runs annotated in-place.
