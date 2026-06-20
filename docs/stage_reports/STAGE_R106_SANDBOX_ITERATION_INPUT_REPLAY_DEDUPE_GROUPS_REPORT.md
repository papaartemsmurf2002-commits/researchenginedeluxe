# Stage R106 Sandbox Iteration Input Replay Dedupe Groups Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-316-sandbox-iteration-input-replay-dedupe-groups.md`

## Summary

WPR106-316 adds duplicate replay-context diagnostics to sandbox iteration input
replay worklists. Agents can now see when multiple indexed iterations point to
the same replay context before planning redundant archive-backed refreshes.

The new fields are descriptor-only triage metadata for agent workflow speed.

## Implementation

- Added per-row replay duplicate group keys.
- Added per-row replay-context duplicate counts and duplicate flags.
- Added summary rollups for unique replay contexts, duplicate replay-context
  groups, duplicate item counts, duplicate group-key counts, and duplicate
  group-key lists.
- Added archive bucket and archive-window unique replay-context rollups so
  agents can distinguish repeated worklist rows from distinct replay inputs.
- Added a deterministic digest fallback for older rows that have replay context
  payloads but no explicit `replay_context_id`.
- Focused regressions prove normal single contexts report no duplicates, copied
  manifest/brief contexts report duplicate groups, missing path readiness still
  fails closed, and JSON/Parquet worklist outputs preserve the new fields.

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

- 3 focused input replay tests passed.
- 7 focused input replay/index tests passed.
- 174 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
