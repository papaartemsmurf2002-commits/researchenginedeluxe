# WPR106-318 Sandbox Artifact Catalog Replay Batch Plan Counts

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Project descriptor-only input replay batch-plan readiness and duplicate
suppression counts into sandbox artifact catalog rows so agents can rank and
triage batch-plan artifacts without reopening every batch-plan JSON file.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-318-sandbox-artifact-catalog-replay-batch-plan-counts.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_COUNTS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
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
- Treat catalog batch-plan counts as read-only navigation metadata only.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Add catalog row count fields for replay batch-plan source, ready, blocked,
   plan, unique ready, and suppressed duplicate counts.
2. Derive fields only from the already-loaded artifact payload and summary.
3. Add focused regressions proving duplicate and blocked batch-plan catalog rows
   surface the new counts and keep boundary flags false.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming batch-plan artifacts are
  discoverable by kind, but artifact catalog rows do not yet expose ready,
  blocked, source, or suppressed duplicate counts for agent triage.
- 2026-06-19: Added catalog row projection for replay batch-plan source,
  ready, blocked, suppressed duplicate, plan item, and unique-ready-context
  counts from the already-loaded batch-plan JSON payload and summary.
- 2026-06-19: Added focused regressions proving catalog rows expose counts for
  both duplicated ready replay contexts and blocked zero-descriptor replay
  plans while preserving sandbox boundary flags.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox artifact catalog rows now expose
input replay batch-plan source worklist item count, ready source item count,
blocked source item count, suppressed duplicate source item count, plan item
count, and unique ready replay context count.

This is read-only navigation metadata only. The packet did not execute replay
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
