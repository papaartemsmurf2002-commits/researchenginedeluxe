# Stage R106 Sandbox Artifact Catalog Replay Batch Plan Rollups Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-319-sandbox-artifact-catalog-replay-batch-plan-rollups.md`

## Summary

WPR106-319 adds top-level replay batch-plan rollups and a bounded replay
batch-plan queue to sandbox artifact catalogs. Agents can now select useful
replay batch-plan artifacts from catalog-level metadata instead of scanning all
catalog rows.

## Implementation

- Added replay batch-plan catalog summary counts for artifact count,
  descriptor count, source worklist item count, ready source item count, blocked
  source item count, suppressed duplicate source item count, plan item count,
  unique ready replay-context count, and status counts.
- Added a bounded replay batch-plan queue sorted by plan item count, suppressed
  duplicates, ready source rows, blocked source rows, and artifact path.
- Kept rollups and queue items derived only from already-built catalog rows.
- Added focused regressions for duplicate-rich ready batch plans and
  blocked-only zero-descriptor batch plans.

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
