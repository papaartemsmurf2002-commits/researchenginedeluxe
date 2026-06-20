# WPR106-315 Sandbox Iteration Input Replay Venue Window Rollups

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add venue/symbol/data-family/interval and replay-window rollups to the sandbox
iteration input replay worklist so agents can quickly see which archive-backed
venues and windows are ready, blocked, or missing coverage across indexed
iterations without scanning every worklist row.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-315-sandbox-iteration-input-replay-venue-window-rollups.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_VENUE_WINDOW_ROLLUPS_REPORT.md`
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
- Treat replay rollups as descriptor navigation metadata only.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs,
  archive routing, preflight behavior, source-integrity behavior, and 2024+
  window policy.

## Plan

1. Add replay worklist summary rollups by archive venue, symbol, data family,
   interval, venue/symbol/family/interval bucket, requested window, readiness,
   and path availability.
2. Keep rollups derived only from already-built replay worklist rows.
3. Add focused regressions proving Bybit/Hyperliquid replay rows surface
   venue-window rollups and readiness counts.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming replay worklists expose per-row
  venue/window fields, but summaries only roll up command/input-mode/path
  readiness and do not show venue-window coverage for agent triage.
- 2026-06-19: Added replay worklist summary counts for archive venue, symbol,
  data family, interval, window start/end/preset, and composite archive/window
  buckets.
- 2026-06-19: Split archive and archive-window bucket counts into ready and
  blocked subsets using existing `input_replay_ready` state.
- 2026-06-19: Added focused regression assertions for ready Hyperliquid replay
  rows and blocked Bybit replay rows.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox iteration input replay worklist
summaries now expose venue/symbol/data-family/interval, requested-window,
archive-bucket, and archive-window bucket rollups, including ready and blocked
subsets. The rollups are derived only from existing replay worklist rows.

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

Final results: 2 focused input replay venue/window tests passed, 6 focused
input replay/index tests passed, 173 sandbox tests passed, package compileall
passed, 11 import-boundary tests passed, and 461 contract tests passed.
