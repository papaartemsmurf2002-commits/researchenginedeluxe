# Stage R106 Sandbox Iteration Input Replay Context Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-312-sandbox-iteration-input-replay-context.md`

## Summary

WPR106-312 surfaces compact, inert input replay context in one-command sandbox
iteration handoff artifacts. Agents can now inspect the command name,
non-executing argv list, strategy/venue input modes, resolved paths or roots,
data windows, and bounded run/build options from an iteration manifest, agent
brief, iteration index row, queue item, or action-plan item without rebuilding
the original CLI arguments from scattered fields.

The action queue schema version is now 13.

## Implementation

- Added deterministic `input_replay_context` payloads to completed and
  preflight-blocked one-command iteration manifests.
- Added replay context to sandbox iteration agent briefs.
- Each replay context includes sandbox boundary flags, `replay_context_id`,
  command name, `command_argv`, `command_argv_truncated: false`,
  `execution_mode: descriptor_only_no_execution`, input modes, resolved input
  paths or roots, data-window values, and bounded run/build options.
- Iteration indexes now project replay context into rows, action queue items,
  recommended action details, and global agent action-plan items.
- Focused regressions prove catalog/archive-root iterations carry replay
  context through manifest, brief, index row, strict-validation queue item,
  action plan, and Parquet outputs.

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
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay_context or iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 5 focused input-replay/index tests passed.
- 172 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
