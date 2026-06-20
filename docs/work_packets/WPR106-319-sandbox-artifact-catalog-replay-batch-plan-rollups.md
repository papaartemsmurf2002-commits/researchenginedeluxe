# WPR106-319 Sandbox Artifact Catalog Replay Batch Plan Rollups

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add top-level replay batch-plan rollups and a bounded replay batch-plan queue to
sandbox artifact catalogs so agents can find high-value replay refresh plans
without scanning every catalog row.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-319-sandbox-artifact-catalog-replay-batch-plan-rollups.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BATCH_PLAN_ROLLUPS_REPORT.md`
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
- Treat replay batch-plan catalog rollups and queues as read-only navigation
  metadata only.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Add top-level catalog summary counts for replay batch-plan artifacts,
   descriptors, ready/blocked source rows, suppressed duplicates, and unique
   ready replay contexts.
2. Add a bounded queue of replay batch-plan catalog rows sorted for agent
   triage.
3. Derive rollups and queue items only from already-built catalog rows.
4. Add focused regressions for duplicate-rich and blocked replay batch plans.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming catalog rows expose replay
  batch-plan counts, but top-level catalog payloads do not yet summarize or
  queue those artifacts for quick agent selection.
- 2026-06-19: Added top-level replay batch-plan catalog summary counts for
  artifacts, descriptors, ready/blocked source rows, suppressed duplicates,
  unique ready replay contexts, and replay batch-plan status counts.
- 2026-06-19: Added a bounded replay batch-plan queue sorted by plan item count,
  suppressed duplicates, ready source rows, blocked source rows, and artifact
  path.
- 2026-06-19: Added focused regressions covering duplicate-rich ready batch
  plans and blocked-only zero-descriptor batch plans in catalog summaries and
  queue items.

## Completion Notes

Implemented and closed on 2026-06-19. Sandbox artifact catalogs now include a
top-level replay batch-plan summary and a bounded replay batch-plan queue. The
summary aggregates replay batch-plan artifact count, descriptor count,
source/ready/blocked worklist counts, suppressed duplicates, unique ready
replay contexts, and status counts. The queue exposes the highest-value
batch-plan artifacts for agent triage.

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
