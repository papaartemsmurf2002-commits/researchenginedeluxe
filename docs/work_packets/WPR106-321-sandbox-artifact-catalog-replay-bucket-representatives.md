# WPR106-321 Sandbox Artifact Catalog Replay Bucket Representatives

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add bounded replay batch-plan archive bucket and archive-window bucket
representative queues to sandbox artifact catalogs so agents can jump from a
venue/window bucket to relevant descriptor-only replay batch-plan artifacts
without scanning every queue item or opening every batch-plan JSON.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-321-sandbox-artifact-catalog-replay-bucket-representatives.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_REPLAY_BUCKET_REPRESENTATIVES_REPORT.md`
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
- Derive bucket representative queues only from already-indexed catalog rows.
- Treat artifact paths and bucket counts as read-only navigation metadata.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Build bounded archive bucket and archive-window bucket representative queues
   from replay batch-plan catalog rows.
2. Keep queue entries boundary-bearing and descriptor-only, with representative
   artifact path metadata and ready/planned counts.
3. Add focused regressions for ready duplicate-rich plans and blocked-only
   plans.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-320 exposed bucket count maps but left
  bucket-to-artifact navigation implicit inside replay batch-plan queue items.
- 2026-06-19: Added bounded archive bucket and archive-window bucket
  representative queues to sandbox artifact catalog payloads, derived only from
  already-indexed replay batch-plan catalog rows.
- 2026-06-19: Added boundary-bearing representative queue entries with
  ready/planned bucket counts, artifact path metadata, descriptor-only state,
  and explicit non-executing authorization flags.
- 2026-06-19: Added focused regressions for duplicate-rich ready batch plans and
  blocked-only batch plans.
- 2026-06-19: Updated the sandbox research contract, active index, stage ledger,
  and stage report.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay"`:
  3 passed, 171 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "input_replay or iteration_index"`:
  7 passed, 167 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`:
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`:
  11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`:
  461 passed.

## Closeout

WPR106-321 is closed. Sandbox artifact catalogs now expose bounded replay
batch-plan archive bucket and archive-window bucket representative queues so
agents can jump from a venue/window bucket to relevant descriptor-only
batch-plan artifacts without opening every batch-plan JSON. The queues are
derived only from catalog rows and remain read-only navigation metadata. No
replay command execution, validation execution, provider download,
strict-cycle execution, candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, strategy catalog
mutation, archive manifest/source mutation, or promotion claim exists.
