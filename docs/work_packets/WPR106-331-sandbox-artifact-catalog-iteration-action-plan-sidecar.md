# WPR106-331 Sandbox Artifact Catalog Iteration Action Plan Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Project existing sandbox iteration-index agent action plans into the sandbox
artifact catalog and write a compact Parquet sidecar so agents can find
cross-iteration repair, replay, rejection-review, and descriptor-only
strict-validation work without reopening each full `sandbox_iteration_index.json`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-331-sandbox-artifact-catalog-iteration-action-plan-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_ITERATION_ACTION_PLAN_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Read only already-loaded sandbox iteration-index JSON payloads discovered by
  the artifact catalog.
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

1. Extract compact iteration action-plan counts from cataloged
   `iteration_index` artifacts.
2. Flatten bounded action-plan rows into a catalog Parquet sidecar with
   boundary flags and non-authorizing fields.
3. Register the sidecar in the artifact catalog sidecar index with row count
   and post-write file identity.
4. Add regressions for populated and empty action-plan sidecar behavior.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming artifact catalogs index
  `sandbox_iteration_index.json` generically but do not flatten its existing
  `agent_action_plan` rows for cross-iteration agent workflow triage.
- 2026-06-19: Added compact iteration-index action-plan counts to artifact
  catalog rows and a new
  `sandbox_artifact_catalog_iteration_agent_action_plan.parquet` sidecar.
- 2026-06-19: Registered the new sidecar in the artifact catalog sidecar index
  so it receives row-count, empty-status, byte-size, and SHA-256 identity
  metadata after the catalog write.

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

Closed 2026-06-19. WPR106-331 keeps artifact catalog iteration action-plan
rows research-only and non-authorizing while making existing iteration-index
agent workflow queues queryable from the artifact catalog. No candidate pack,
paper/live signal, order/sizing/runtime change, provider download, replay
execution, validation execution, strategy catalog mutation, archive
manifest/source mutation, live configuration write, or promotion claim was
added.
