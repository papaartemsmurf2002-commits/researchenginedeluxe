# Stage R106 Sandbox Iteration Input Replay Worklist Report

Date: 2026-06-19
Owner: Codex Research Agent
Work packet: `docs/work_packets/WPR106-313-sandbox-iteration-input-replay-worklist.md`

## Summary

WPR106-313 materializes a dedicated input replay worklist from sandbox
iteration indexes. WPR106-312 put inert replay context into manifests, briefs,
rows, queues, and action plans; this packet makes that replay context directly
queryable as `sandbox_iteration_input_replay_worklist.json` and
`sandbox_iteration_input_replay_worklist.parquet`.

The worklist is version 1. It is a descriptor-only agent handoff artifact, not
an execution queue.

## Implementation

- Added replay worklist constants and builder helpers to the sandbox
  iteration-index path.
- Each worklist item carries sandbox boundary flags, replay context ID,
  command name, non-executing argv list, execution mode, strategy/venue input
  modes, resolved paths or roots, data-window fields, run/build options,
  recommended action context, source queues, artifact availability, and compact
  result/request/blocker counts.
- Iteration indexes now expose worklist version, count, missing-context count,
  summary rollups, embedded worklist rows, and JSON/Parquet worklist paths.
- The existing `index-rapid-strategy-sandbox-iterations` path writes the
  dedicated replay worklist JSON/Parquet artifacts whenever reports are
  enabled.
- The sandbox artifact catalog now discovers
  `sandbox_iteration_input_replay_worklist.json` as
  `iteration_input_replay_worklist`.
- Focused regressions prove worklist JSON/Parquet rows preserve argv-list
  replay metadata and sandbox boundary flags.

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
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay_context"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay_context or iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Results:

- 1 focused input replay context/worklist test passed.
- 5 focused input replay/index tests passed.
- 172 sandbox tests passed.
- Package compileall passed.
- 11 import-boundary tests passed.
- 461 contract tests passed.
