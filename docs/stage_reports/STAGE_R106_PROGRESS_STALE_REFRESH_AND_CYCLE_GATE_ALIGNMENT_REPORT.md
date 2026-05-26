# Stage R106 Progress Stale Refresh And Cycle Gate Alignment Report

Date: 2026-05-22

## Summary

WPR106-07 fixes the misleading checklist state after the completed BTC R106
cycle:

- Completed historical-data refresh journals are no longer returned as
  `active_historical_data_progress` when no refresh job is active.
- Historical-cycle checklist validation now accepts the current
  `candidate_gate_report` output key.
- The materialized-candidate floor now accepts the generated R106
  candidate-depth cycle evidence of 63 materialized candidates when the
  manifest still records 2048 brute-force-equivalent coverage.

The completed BTC cycle now reports complete in progress diagnostics, and the
next required action is BTC exact discovery.

## Investigation

The UI was showing `Historical Data Refresh complete` because the progress API
returned the latest completed refresh journal as active progress. The BTC cycle
row was blocked because the checklist still expected a legacy `gate_report`
key and a hard 64 materialized-candidate floor, while the completed R106
manifest writes `candidate_gate_report` and records 63 materialized candidates
with 2048 brute-force-equivalent coverage.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_progress_accepts_candidate_depth_catalog_artifact_ids tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_does_not_show_completed_refresh_as_active tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_reports_historical_data_refresh_journal -q
```

Results:

- focused operator progress tests: `3 passed`

## Boundary

No generated evidence files were modified. No live-order, runtime-mode, or
live-configuration paths were changed.
