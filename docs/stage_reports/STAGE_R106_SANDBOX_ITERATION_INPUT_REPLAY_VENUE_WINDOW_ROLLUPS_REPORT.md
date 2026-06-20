# Stage R106 Sandbox Iteration Input Replay Venue Window Rollups Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-315-sandbox-iteration-input-replay-venue-window-rollups.md`

## Summary

WPR106-315 adds venue/window rollups to sandbox iteration input replay worklist
summaries. Agents can now see replay coverage by archive venue, symbol,
data-family, interval, requested window, readiness, and path availability
without scanning every worklist row.

These rollups are descriptor-only triage metadata for archive-backed
multi-venue iteration coverage.

## Implementation

- Added worklist summary counts for archive venue, symbol, data family,
  interval, and replay window fields.
- Added composite archive bucket counts for
  `venue|symbol|data_family|interval`.
- Added composite requested-window bucket counts for
  `window_start|window_end|window_preset`.
- Added composite archive-window bucket counts for
  `venue|symbol|data_family|interval|window_start|window_end`.
- Split archive and archive-window bucket counts into ready and blocked
  subsets using existing `input_replay_ready` state.
- Focused regressions prove ready Hyperliquid and blocked Bybit replay rows
  surface the expected archive/window rollups.

## Boundary

This is descriptor navigation metadata only. The packet did not execute replay
commands, strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration,
download provider data, mutate strategy catalogs, mutate archive manifests or
source files, or claim promotion readiness.

The packet did not alter sandbox scoring, ranking math, falsification
decisions, blocker/rejection semantics, evidence-request selection, trial IDs,
archive routing, compatibility preflight, source-integrity behavior, or 2024+
window policy.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay or iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 2 focused input replay venue/window tests passed.
- 6 focused input replay/index tests passed.
- 173 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
