# WPR106-313 Sandbox Iteration Input Replay Worklist

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Materialize a dedicated descriptor-only input replay worklist from sandbox
iteration indexes so agents can query reproducible one-command replay metadata
directly from compact JSON/Parquet artifacts without parsing nested
iteration-index rows, action queues, or agent action-plan items.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-313-sandbox-iteration-input-replay-worklist.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_WORKLIST_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute replay commands, strict validation, write candidate packs,
  create paper/live signals, define sizing, place orders, change runtime mode,
  write live configuration, download provider data, mutate strategy catalogs,
  mutate archive manifests/source files, or claim promotion readiness.
- Treat replay worklist rows as descriptor navigation metadata only.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs,
  archive routing, preflight behavior, source-integrity behavior, and 2024+
  window policy.
- Keep command metadata as argv lists rather than shell strings.

## Plan

1. Add a replay worklist builder to sandbox iteration indexes, producing one
   bounded row per indexed iteration with available `input_replay_context`.
2. Write dedicated `sandbox_iteration_input_replay_worklist.json` and
   `sandbox_iteration_input_replay_worklist.parquet` artifacts when iteration
   index reports are written.
3. Surface worklist counts, missing-context counts, truncation metadata, paths,
   and summary rollups in the iteration-index payload.
4. Add focused regressions proving replay worklist JSON/Parquet artifacts carry
   argv-list replay context and sandbox boundary flags.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming WPR106-312 exposes replay context
  in manifests, briefs, rows, queues, and action plans, but does not provide a
  dedicated queryable replay worklist artifact for agents.
- 2026-06-19: Added replay worklist constants, item builder, summary builder,
  and report writer integration to the sandbox iteration-index path.
- 2026-06-19: Iteration indexes now expose worklist version, count,
  missing-context count, summary rollups, embedded worklist rows, and dedicated
  JSON/Parquet worklist artifact paths.
- 2026-06-19: Registered `sandbox_iteration_input_replay_worklist.json` with
  the sandbox artifact catalog as `iteration_input_replay_worklist`.
- 2026-06-19: Added focused regressions proving replay worklist JSON/Parquet
  rows carry argv-list replay context and sandbox boundary flags.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration indexes now
materialize `sandbox_iteration_input_replay_worklist.json` and
`sandbox_iteration_input_replay_worklist.parquet` whenever reports are written.
The worklist is version 1 and includes one row per indexed iteration with
available `input_replay_context`, plus missing-context counts and summary
rollups.

This is descriptor navigation metadata only. The packet did not execute replay
commands, strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration,
download provider data, mutate strategy catalogs, mutate archive manifests or
source files, or claim promotion readiness.

The packet did not alter sandbox scoring, ranking math, falsification
decisions, blocker/rejection semantics, evidence-request selection, trial IDs,
archive routing, compatibility preflight, source-integrity behavior, or 2024+
window policy.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay_context"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay_context or iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 1 focused input replay context/worklist test passed, 5 focused
input replay/index tests passed, 172 sandbox tests passed, package compileall
passed, 11 import-boundary tests passed, and 461 contract tests passed.
