# WPR106-28 Autopilot Step Transparency And Cleanliness Audit

## Summary

Audit the post-WPR106-27 operator/autopilot path for remaining transparency,
progress-reporting, and cleanliness problems. Patch only confirmed UI/API gaps
that make long autopilot runs hard to diagnose.

Status: closed on 2026-05-30. The packet found and fixed two operator-facing
diagnostic gaps: active autopilot helper steps were not visible while running,
and stale `running` autopilot manifests could look active even after the process
was gone.

## Allowed Paths

Edit scope:

- `docs/work_packets/WPR106-28-autopilot-step-transparency-and-cleanliness-audit.md`
- `docs/stage_reports/STAGE_R106_AUTOPILOT_STEP_TRANSPARENCY_AND_CLEANLINESS_AUDIT_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md` only if a new blocking issue is found
- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`

Do not edit generated research artifacts, runtime SQLite state, fixture packs,
live config, runtime mode, sizing, order placement, strategy logic, backtest
logic, or promotion readiness behavior.

## Audit Plan

1. Inspect the operator progress API and research UI rendering path.
2. Verify how autopilot records in-progress steps and logs helper execution.
3. Check for remaining broad-scan, stale-path, live-boundary, and
   promotion-readiness hazards relevant to the touched surfaces.
4. Add explicit active-autopilot progress with current step, attempt, elapsed
   time, ETA/basis, latest completed step, and stale-telemetry notes.
5. Add tests for the API-visible active step and for manifest cleanup after
   completion.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed,
  `427 passed`.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  passed, `78 passed`.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q` passed,
  `213 passed`.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical -q` passed,
  `42 passed`.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts tests\live -q`
  passed, `93 passed`.

## Acceptance Criteria

- The research progress API exposes active autopilot step telemetry.
- The UI renders the active autopilot step before falling back to generic
  discovery/cycle panels.
- A running helper step is written to the autopilot manifest before the helper
  blocks or runs for a long time.
- Finished, failed, or retried steps clear `active_step` so stale UI state is
  not presented as current work.
- Validation passes for the operator UI tests and contract baseline.
