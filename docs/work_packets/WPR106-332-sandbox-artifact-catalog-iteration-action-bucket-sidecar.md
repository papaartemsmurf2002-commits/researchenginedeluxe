# WPR106-332 Sandbox Artifact Catalog Iteration Action Bucket Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add a compact artifact catalog sidecar that groups existing iteration-index
agent action-plan rows by action and source queue, with bounded representative
iteration IDs, so agents can triage cross-iteration repair, replay,
rejection-review, and descriptor-only strict-validation work without scanning
every action-plan row first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-332-sandbox-artifact-catalog-iteration-action-bucket-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_BUCKET_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Derive bucket rows only from already-loaded `iteration_index` action-plan
  rows in the artifact catalog build.
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

1. Derive bounded action and source-queue buckets from catalog action-plan rows.
2. Write `sandbox_artifact_catalog_iteration_agent_action_plan_bucket_queue.parquet`.
3. Register the sidecar in the catalog sidecar index with post-write file
   identity.
4. Add regressions for populated and empty bucket sidecar behavior.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-331 made action-plan rows queryable
  from the artifact catalog but left action/source-queue buckets implicit.
- 2026-06-19: Added a bounded action/source-queue bucket queue derived from
  already-flattened artifact catalog iteration action-plan rows.
- 2026-06-19: Wrote
  `sandbox_artifact_catalog_iteration_agent_action_plan_bucket_queue.parquet`
  and registered it in the artifact catalog sidecar index with post-write file
  identity metadata.

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

Closed 2026-06-19. WPR106-332 keeps artifact catalog iteration action buckets
research-only and non-authorizing while making existing cross-iteration action
and source-queue workflow buckets queryable from the artifact catalog. No
candidate pack, paper/live signal, order/sizing/runtime change, provider
download, replay execution, validation execution, strategy catalog mutation,
archive manifest/source mutation, live configuration write, or promotion claim
was added.
