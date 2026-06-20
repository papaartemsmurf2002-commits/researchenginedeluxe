# WPR106-314 Sandbox Iteration Input Replay Path Readiness

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add replay input path readiness diagnostics to the sandbox iteration input
replay worklist so agents can see whether the original strategy/catalog,
venue/archive, spec, and output path references still exist before attempting
to reproduce or refresh a one-command archive-backed sandbox iteration.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-314-sandbox-iteration-input-replay-path-readiness.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_PATH_READINESS_REPORT.md`
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
- Treat replay input readiness as descriptor navigation metadata only.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs,
  archive routing, preflight behavior, source-integrity behavior, and 2024+
  window policy.
- Check only filesystem existence/type for replay input references; do not
  open, parse, hash, or modify referenced source files or directories.

## Plan

1. Add a replay input-reference availability helper for files and directories
   named in `input_replay_context`.
2. Project availability status, present/missing counts, missing keys, and
   bounded reference rows into replay worklist items.
3. Make `input_replay_ready` fail closed when required replay input references
   are missing or have the wrong filesystem type.
4. Add focused regressions for all-present replay inputs and missing replay
   input references in JSON/Parquet worklist outputs.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming WPR106-313 creates a dedicated
  input replay worklist, but only reports produced artifact availability rather
  than whether the original replay input paths still exist.
- 2026-06-19: Added replay input path availability diagnostics for output,
  spec, strategy catalog, catalog root, venue archive manifest, and archive
  root references already present in `input_replay_context`.
- 2026-06-19: Projected replay input path status, reference counts, missing
  keys, wrong-type keys, status counts, and bounded reference rows into replay
  worklist items and summary rollups.
- 2026-06-19: Made replay worklist `input_replay_ready` fail closed when replay
  inputs are missing or have the wrong filesystem type.
- 2026-06-19: Added focused regressions for all-present replay inputs and a
  missing catalog root replay input through JSON/Parquet worklist outputs.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration input replay worklist
items now include replay input path readiness diagnostics, and worklist
summaries aggregate path availability counts. Diagnostics check only
filesystem existence and expected file-vs-directory type.

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

Final results: 2 focused input replay path-readiness tests passed, 6 focused
input replay/index tests passed, 173 sandbox tests passed, package compileall
passed, 11 import-boundary tests passed, and 461 contract tests passed.
