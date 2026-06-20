# Stage R106 Sandbox Iteration Input Replay Path Readiness Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-314-sandbox-iteration-input-replay-path-readiness.md`

## Summary

WPR106-314 adds replay input path readiness diagnostics to the sandbox
iteration input replay worklist. Agents can now query whether the original
one-command replay inputs still exist before attempting to reproduce or refresh
an archive-backed sandbox iteration.

The diagnostics are descriptor-only path/type checks. They do not open, parse,
hash, download, repair, or mutate referenced inputs.

## Implementation

- Added a replay input path-availability helper to the iteration-index module.
- Worklist rows now report output/spec/catalog/archive input references,
  expected file-vs-directory type, present/missing/wrong-type status, missing
  keys, wrong-type keys, status counts, and bounded reference rows.
- `input_replay_ready` now fails closed when command metadata is invalid,
  execution mode is unexpected, or replay input references are missing or have
  the wrong filesystem type.
- Replay worklist summaries now aggregate path availability status counts,
  missing/wrong-type key counts, and total referenced/present/missing/wrong
  type path counts.
- Focused regressions cover all-present replay inputs and a missing catalog
  root reference through JSON/Parquet worklist outputs.

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

- 2 focused input replay path-readiness tests passed.
- 6 focused input replay/index tests passed.
- 173 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
