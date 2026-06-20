# Stage R106 Sandbox Iteration Recent Window Presets Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-270-sandbox-iteration-recent-window-presets.md`
Status: closed

## Summary

WPR106-270 adds generated-spec recent-window presets to one-command sandbox
agent iterations so agents can launch current archive-backed screens without
manually choosing stale calendar windows.

## Implementation

- Added a generated-spec window resolver in `iteration.py`.
- Preserved explicit `window_start` / `window_end` behavior.
- Added `recent_365d`, `recent_days`, and `recent_<N>d` style preset support.
- Presets resolve against an optional `window_as_of_date` and record the
  resolved start/end, lookback days, raw start, and 2024-floor clipping status.
- Spec-file runs reject window-preset overrides instead of silently rewriting
  the provided spec.
- Iteration manifests and agent briefs now carry `window_selection` metadata.
- The CLI command `run-rapid-strategy-sandbox-iteration` now accepts
  `--window-preset`, `--window-as-of-date`, and `--window-lookback-days`.

## Boundary

This packet only selects generated sandbox iteration data windows. It does not
download provider data, execute strict validation, write candidate artifacts,
create paper/live signals, define sizing, place orders, mutate runtime mode,
write live configuration, mutate source archive files, or claim promotion
readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "recent_window or cli_command_runs_sandbox_agent_iteration"
# 4 passed, 103 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 107 passed

$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py -q
# 22 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 461 passed
```

## Remaining Work

Future packets can expose additional agent presets if actual archive use shows
that shorter intraday or venue-specific windows are more useful.
