# WPR106-329 Sandbox Artifact Catalog Sidecar Index

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add a compact sidecar index Parquet file to sandbox artifact catalogs so agents
can discover catalog, replay, and strict-validation sidecar paths and row
counts without parsing the full catalog JSON first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-329-sandbox-artifact-catalog-sidecar-index.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_SIDECAR_INDEX_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute sandbox sweeps, strict validation, replay commands, provider
  downloads, candidate-pack writes, paper/live signal generation, sizing, order
  placement, runtime-mode changes, live configuration writes, strategy-catalog
  mutations, archive manifest/source mutations, or promotion claims.
- Index only catalog writer sidecar outputs and already-computed row counts.
- Sidecar index rows may expose sidecar category, name, path, file name, row
  count, empty status, and automation role metadata.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness,
  strict-validation descriptor queues, and the 2024+ window policy.

## Plan

1. Add a fixed sidecar index Parquet filename, columns, and row builder.
2. Populate rows for catalog, replay-batch-plan, and strict-validation sidecar
   outputs with row counts and empty flags.
3. Write the sidecar index after companion sidecars and expose its path/count in
   the catalog payload.
4. Add focused regressions for populated and empty/failed-integrity catalog
   sidecar indexes.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-328 added another strict-validation
  sidecar, increasing the need for a direct sidecar inventory for agents.
- 2026-06-19: Added fixed sidecar index filename and stable Parquet schema.
- 2026-06-19: Added sidecar index rows for the catalog Parquet, replay
  batch-plan bucket sidecars, and strict-validation bundle/descriptor sidecars.
- 2026-06-19: Added catalog payload metadata for sidecar index path, row count,
  and rows.
- 2026-06-19: Added focused regressions for populated sidecar indexes and
  failed-integrity empty strict-validation sidecars.
- 2026-06-19: Updated sandbox contract, active index, stage ledger, and stage
  report.

## Validation

- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog"`:
  2 passed, 172 deselected.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`:
  174 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`:
  passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`:
  11 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`:
  461 passed.

## Closeout

Closed 2026-06-19. The packet adds read-only catalog sidecar index rows for
agent navigation. It does not execute or authorize strict validation, write
candidate packs, execute replay commands, mutate source catalogs/manifests,
download provider data, create paper/live artifacts, define sizing, place
orders, change runtime mode, write live configuration, or claim promotion
readiness.
