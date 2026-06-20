# WPR106-312 Sandbox Iteration Input Replay Context

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose bounded one-command iteration input replay context in sandbox iteration
manifests, agent briefs, and iteration-index worklists so agents can reproduce
or refresh an archive-backed sandbox iteration from handoff artifacts without
manually reconstructing CLI arguments from scattered manifest fields.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-312-sandbox-iteration-input-replay-context.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ITERATION_INPUT_REPLAY_CONTEXT_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/iteration.py`
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
- Treat replay context as descriptor navigation metadata only.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs,
  archive routing, preflight behavior, source-integrity behavior, and 2024+
  window policy.
- Keep command metadata as argv lists rather than shell strings so paths remain
  explicit and non-executing.

## Plan

1. Add one-command input replay context to sandbox agent iteration payloads,
   including original input mode, resolved input paths/roots, window/options,
   and a non-executing `command_argv` descriptor.
2. Project replay context into agent briefs.
3. Project replay context into iteration-index rows, queue items, recommended
   action details where useful, and agent action-plan items.
4. Add focused regressions proving catalog/archive root iterations carry
   replay argv context through manifest, brief, index, queue, action plan, and
   Parquet outputs.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming existing iteration handoff
  artifacts expose many result and repair fields but do not preserve a compact
  argv-style descriptor of the original one-command iteration inputs/options.
- 2026-06-19: Added deterministic `input_replay_context` payloads to completed
  and preflight-blocked one-command iteration manifests.
- 2026-06-19: Added replay context to sandbox iteration agent briefs.
- 2026-06-19: Projected replay context into iteration-index rows, action queue
  items, recommended action details, and global agent action-plan items.
- 2026-06-19: Bumped the iteration action queue schema to version 13 because
  queue and action-plan payloads now include input replay context.
- 2026-06-19: Added focused regressions for catalog/archive-root iterations and
  replay-context propagation through manifest, brief, index row, queue, action
  plan, and Parquet outputs.

## Completion Notes

Implemented and closed on 2026-06-19. One-command sandbox iteration manifests
and agent briefs now include inert `input_replay_context` metadata with a
deterministic replay context ID, command name, non-executing argv list,
strategy/venue input modes, resolved paths or roots, data windows, and
bounded run/build options. Iteration-index rows, action queue items,
recommended action details, and global agent action-plan items carry the same
context for agent reproduction and refresh handoffs.

The action queue schema version is now 13.

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
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay_context or iteration_index"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Final results: 5 focused input-replay/index tests passed, 172 sandbox tests
passed, package compileall passed, 11 import-boundary tests passed, and 461
contract tests passed.
