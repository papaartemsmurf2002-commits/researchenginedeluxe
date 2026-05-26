# Stage R106 Active Cycle Progress And Runtime Visibility Report

Date: 2026-05-22

## Summary

WPR106-06 adds active historical-cycle progress to the operator progress API
and Research UI. The progress payload is derived from the isolated operator run
directory before the final `research_cycle_manifest.json` exists, so a running
cycle can show aggregate candidate backtest completion, total backtest
evaluation completion, rate, ETA, output path, and compute policy.

The payload keeps aggregate candidate progress separate from all known
backtest evaluations. When split and cost-stress counts are known, the visible
bar uses total backtest-evaluation progress; final ranking, gate, and manifest
writing can still continue briefly after evaluation work reaches 100%.

## Discovery Runtime Check

The active R106 exact discovery specs still plan 570240 trials per symbol and
request the process executor with 48 workers. Existing R105 telemetry remains
the best completed-run evidence: the earlier 570240-trial sweep took about
31.2 wall-clock hours at about 304.9 trials per minute and consumed roughly one
busy core despite nominal 48-worker configuration.

This packet does not claim exact discovery is now under 30 hours. It makes the
current cycle progress visible and keeps discovery ETA/snapshot reporting in
the existing resumable discovery path.

## Validation

Passed:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_reports_historical_cycle_progress tests\tradingbotsuite\test_operator_ui.py::test_operator_research_progress_reports_historical_data_refresh_journal -q
$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q
```

Results:

- focused progress tests: `2 passed`
- operator UI tests: `53 passed`

## Boundaries

- Research outputs remain `research_only`, `observe_only`, and
  `promotion_ready: false`.
- No live-order, runtime-mode, or live-configuration code was changed.
