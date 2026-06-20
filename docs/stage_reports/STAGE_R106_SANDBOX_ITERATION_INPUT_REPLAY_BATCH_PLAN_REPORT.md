# Stage R106 Sandbox Iteration Input Replay Batch Plan Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-317-sandbox-iteration-input-replay-batch-plan.md`

## Summary

WPR106-317 adds a descriptor-only input replay batch plan artifact to sandbox
iteration indexes. Agents can now find one ready representative replay
descriptor per unique replay context, while duplicate and blocked worklist rows
remain accounted for in summary metadata.

The new artifact improves agent workflow speed without adding execution
behavior.

## Implementation

- Added batch-plan JSON and Parquet artifact names and versioning.
- Built batch-plan items from already-built input replay worklist rows.
- Included only `input_replay_ready` rows as plan items.
- Selected one representative per duplicate replay-context group.
- Preserved argv as structured lists, not shell scripts.
- Added explicit non-authorization fields for replay command execution, strict
  validation, and candidate-pack writes.
- Added summary rollups for source worklist rows, ready rows, blocked rows,
  suppressed duplicates, duplicate-group keys, path-readiness status, and
  archive/window buckets.
- Registered `sandbox_iteration_input_replay_batch_plan.json` in the sandbox
  artifact catalog as `iteration_input_replay_batch_plan`.
- Focused regressions cover normal ready contexts, duplicated ready contexts,
  blocked replay rows, no-write mode, JSON/Parquet output, and artifact catalog
  discovery.

## Boundary

This is descriptor navigation metadata only. The packet did not execute replay
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
