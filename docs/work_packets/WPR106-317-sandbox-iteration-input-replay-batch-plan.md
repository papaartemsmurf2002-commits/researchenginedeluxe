# WPR106-317 Sandbox Iteration Input Replay Batch Plan

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add a descriptor-only input replay batch plan artifact to sandbox iteration
indexes so agents can identify one ready representative replay descriptor per
unique replay context and avoid redundant refresh planning across duplicate
worklist rows.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-317-sandbox-iteration-input-replay-batch-plan.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_BATCH_PLAN_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration_index.py`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute replay commands, strict validation, write candidate packs,
  create paper/live signals, define sizing, place orders, change runtime mode,
  write live configuration, download provider data, mutate strategy catalogs,
  mutate archive manifests/source files, or claim promotion readiness.
- Treat the batch plan as descriptor navigation metadata only. It may carry
  argv lists for human/agent handoff, but it must not be a shell script,
  scheduler, executor, or validation authorization artifact.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Build a replay batch plan from already-built input replay worklist rows.
2. Include only `input_replay_ready` rows in plan items and select one
   representative per duplicate group.
3. Summarize blocked rows, duplicate suppression, archive/window buckets, and
   path-readiness counts without executing anything.
4. Write JSON and Parquet batch-plan artifacts from iteration indexing and
   register the JSON artifact in the sandbox artifact catalog.
5. Add focused regressions for ready duplicates, blocked rows, no-write mode,
   JSON/Parquet output, and artifact catalog discovery.
6. Update sandbox contract, active index, stage ledger, and stage report.
7. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming replay worklists now expose
  duplicate replay-context groups, but still require agents to manually choose
  one ready representative per unique replay context for refresh planning.
- 2026-06-19: Added replay batch-plan builders that consume already-built
  replay worklist rows, include only ready rows in plan items, select one
  representative per duplicate group, and summarize blocked rows separately.
- 2026-06-19: Wired batch-plan JSON/Parquet writing into sandbox iteration
  indexing and registered the batch-plan JSON with the sandbox artifact catalog.
- 2026-06-19: Added focused regressions for normal ready contexts, duplicated
  ready contexts, blocked replay rows, no-write mode, JSON/Parquet batch-plan
  output, and artifact catalog discovery.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration indexes now emit a
descriptor-only input replay batch plan as JSON and Parquet. The plan includes
one ready representative replay descriptor per unique replay context, keeps argv
as structured lists, summarizes duplicate suppression and blocked replay rows,
and is discoverable through the sandbox artifact catalog.

This is descriptor navigation metadata only. The packet did not execute replay
commands, strict validation, write candidate packs, create paper/live signals,
define sizing, place orders, change runtime mode, write live configuration,
download provider data, mutate strategy catalogs, mutate archive manifests or
source files, or claim promotion readiness.

The packet did not alter sandbox scoring, ranking math, falsification
decisions, blocker/rejection semantics, evidence-request selection, trial IDs,
archive routing, compatibility preflight, source-integrity behavior, replay
readiness, or 2024+ window policy.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay or iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 3 focused input replay tests passed, 7 focused input
replay/index tests passed, 174 sandbox tests passed, package compileall passed,
11 import-boundary tests passed, and 461 contract tests passed.
