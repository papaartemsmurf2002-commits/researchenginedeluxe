# WPR106-07 Progress Stale Refresh And Cycle Gate Alignment

Status: closed

## Scope

Fix the operator checklist state after completed R106 BTC cycle evidence:

- Do not render a completed historical-data refresh journal as the active run
  progress panel.
- Accept the current historical-cycle manifest output name
  `candidate_gate_report`.
- Align the deep-cycle materialized-candidate floor with the generated R106
  candidate-depth cycle evidence while still rejecting compact screening runs.

## Allowed paths

- `src/tradingbotsuite/operator_console.py`
- `src/tradingbotsuite/web/templates/research.html`
- `tests/tradingbotsuite/test_operator_ui.py`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/work_packets/WPR106-07-progress-stale-refresh-and-cycle-gate-alignment.md`
- `docs/stage_reports/STAGE_R106_PROGRESS_STALE_REFRESH_AND_CYCLE_GATE_ALIGNMENT_REPORT.md`

## Constraints

- Do not modify generated evidence files.
- Do not weaken research-only/live-boundary requirements.
- Keep compact R104 screening artifacts blocked as insufficient evidence.

## Acceptance

- Completed historical-data refresh progress is not shown as active progress
  when no refresh job is active.
- The completed R106 BTC cycle manifest is not blocked by stale output-key or
  off-by-one materialized-candidate checks.
- Focused operator UI tests pass.

## Close Evidence

- `docs/stage_reports/STAGE_R106_PROGRESS_STALE_REFRESH_AND_CYCLE_GATE_ALIGNMENT_REPORT.md`
- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_progress_accepts_candidate_depth_catalog_artifact_ids tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_does_not_show_completed_refresh_as_active tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_reports_historical_data_refresh_journal -q`
