# WPR106-333 Sandbox Artifact Catalog Iteration Action Bucket Representatives

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Write a compact representative Parquet sidecar for sandbox artifact catalog
iteration action-plan buckets so agents can jump from an action/source-queue
bucket directly to representative iteration/action metadata without joining the
full action-plan sidecar.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-333-sandbox-artifact-catalog-iteration-action-bucket-representatives.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_BUCKET_REPRESENTATIVES_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Derive representative rows only from already-derived artifact catalog
  iteration action-plan bucket rows and their source action-plan rows.
- Do not execute sandbox sweeps, iteration replay commands, strict validation,
  provider downloads, candidate-pack writes, paper/live signal generation,
  sizing, order placement, runtime-mode changes, live configuration writes,
  strategy-catalog mutations, archive manifest/source mutations, or promotion
  claims.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness,
  strict-validation descriptor queues, sidecar file identity metadata, and the
  2024+ window policy.

## Plan

1. Preserve bounded representative action-plan rows on each action/source-queue
   bucket.
2. Flatten bucket representatives into
   `sandbox_artifact_catalog_iteration_agent_action_plan_bucket_representatives.parquet`.
3. Register the representative sidecar in the catalog sidecar index with
   post-write file identity.
4. Add regressions for populated and empty representative sidecar behavior.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-332 added action/source-queue bucket
  rows with representative IDs but no flattened representative sidecar.
- 2026-06-19: Added
  `sandbox_artifact_catalog_iteration_agent_action_plan_bucket_representatives.parquet`
  with bounded representative rows derived from catalog action/source-queue
  bucket membership.
- 2026-06-19: Registered the representative sidecar in the artifact catalog
  sidecar index with post-write file identity metadata.

## Validation

- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog or iteration_index_summarizes_agent_iterations"`
  passed with 3 passed and 171 deselected.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  passed with 174 passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
  passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  passed with 11 passed.
- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  passed with 461 passed.

## Closeout

Closed 2026-06-19. WPR106-333 keeps artifact catalog iteration action bucket
representatives research-only and non-authorizing while making existing
representative iteration/action rows queryable without joining the full
action-plan sidecar. No candidate pack, paper/live signal, order/sizing/runtime
change, provider download, replay execution, validation execution, strategy
catalog mutation, archive manifest/source mutation, live configuration write,
or promotion claim was added.
