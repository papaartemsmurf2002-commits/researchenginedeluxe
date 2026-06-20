# WPR106-316 Sandbox Iteration Input Replay Dedupe Groups

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add duplicate replay-context diagnostics to the sandbox iteration input replay
worklist so agents can avoid rerunning identical sandbox iteration inputs when
multiple indexed iterations point at the same replay context.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-316-sandbox-iteration-input-replay-dedupe-groups.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_DEDUPE_GROUPS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
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
- Treat duplicate replay-context metadata as descriptor navigation metadata
  only.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, and 2024+ window
  policy.

## Plan

1. Mark replay worklist rows with duplicate replay-context group keys, duplicate
   counts, and duplicate flags derived only from already-built worklist rows.
2. Add summary rollups for unique replay contexts, duplicate groups, duplicate
   item counts, duplicate IDs, and archive/window unique-context counts.
3. Add focused regressions proving duplicated replay contexts are visible in
   JSON and Parquet worklist outputs without changing readiness.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming replay worklists expose replay
  context IDs and venue/window rollups, but do not yet identify duplicate
  contexts that would cause redundant agent refresh work.
- 2026-06-19: Added post-build replay worklist duplicate annotations using
  `replay_context_id` with a deterministic digest fallback for older rows.
- 2026-06-19: Added summary rollups for unique replay contexts, duplicate
  replay-context groups/items, duplicate group keys, and archive/window unique
  replay-context counts.
- 2026-06-19: Added focused regressions for single replay contexts, duplicate
  replay contexts, missing replay input paths, JSON worklist output, and
  Parquet worklist output.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration input replay worklist
rows now expose duplicate group keys, per-row duplicate counts, and duplicate
flags. Worklist summaries now expose unique replay-context counts, duplicate
group counts, duplicate item counts, duplicate group-key counts, and
archive/window unique replay-context rollups.

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
