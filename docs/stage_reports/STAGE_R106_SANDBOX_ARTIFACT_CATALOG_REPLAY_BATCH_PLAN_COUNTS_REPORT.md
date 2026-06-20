# Stage R106 Sandbox Artifact Catalog Replay Batch Plan Counts Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-318-sandbox-artifact-catalog-replay-batch-plan-counts.md`

## Summary

WPR106-318 projects input replay batch-plan readiness and duplicate suppression
counts into sandbox artifact catalog rows. Agents can now rank batch-plan
artifacts by ready rows, blocked rows, descriptors, unique ready contexts, and
suppressed duplicates without reopening every batch-plan JSON file.

## Implementation

- Added catalog row fields for source worklist item count, ready source item
  count, blocked source item count, and suppressed duplicate source item count.
- Added catalog row fields for batch-plan item count and unique ready replay
  context count from the batch-plan summary.
- Kept the projection derived only from the already-loaded batch-plan JSON
  payload and summary.
- Added focused regressions for duplicated ready replay contexts and blocked
  zero-descriptor replay plans.

## Boundary

This is read-only navigation metadata only. The packet did not execute replay
commands, strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration,
download provider data, mutate strategy catalogs, mutate archive manifests or
source files, or claim promotion readiness.

The packet did not alter sandbox scoring, ranking math, falsification
decisions, blocker/rejection semantics, evidence-request selection, trial IDs,
archive routing, compatibility preflight, source-integrity behavior, replay
readiness, or 2024+ window policy.

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

- 3 focused input replay tests passed.
- 7 focused input replay/index tests passed.
- 174 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
