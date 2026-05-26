# WPR106-06 Active Cycle Progress And Runtime Visibility

## Scope

Expose lightweight progress for active historical-cycle jobs and make the
operator UI distinguish cycle, discovery, and data-refresh progress without
waiting for a completed artifact.

Status: closed

## Allowed paths

- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR106-06-active-cycle-progress-and-runtime-visibility.md`
- `docs/stage_reports/STAGE_R106_ACTIVE_CYCLE_PROGRESS_AND_RUNTIME_VISIBILITY_REPORT.md`

## Constraints

- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- No live-order, runtime-mode, or live-configuration changes.
- Progress must be derived from existing run artifacts and job metadata.
- Do not restart or interrupt any active operator job as part of this packet.

## Acceptance

- `/api/operator/research/progress` includes active historical-cycle progress
  for queued/running `run-historical-research-cycle` jobs.
- The Research UI renders a historical-cycle progress bar with aggregate
  candidate count, total backtest-evaluation count, rate, and ETA.
- Existing discovery and historical-data progress rendering still works.
- Focused operator UI tests cover the new payload.

## Close Evidence

- `docs/stage_reports/STAGE_R106_ACTIVE_CYCLE_PROGRESS_AND_RUNTIME_VISIBILITY_REPORT.md`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
