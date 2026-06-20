# WPR106-335 Sandbox Artifact Catalog Analysis Bucket Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Flatten sandbox run analysis bucket rollups into a compact artifact catalog
Parquet sidecar so agents can query venue, family, exit, filter, and
venue/family run clusters across many sandbox runs without opening every
`analysis_summary.json`.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-335-sandbox-artifact-catalog-analysis-bucket-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_ANALYSIS_BUCKET_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Derive sidecar rows only from already-loaded `analysis_summary.json` payloads
  and their embedded bounded bucket rollups.
- Do not execute sandbox sweeps, iteration replay commands, strict validation,
  provider downloads, candidate-pack writes, paper/live signal generation,
  sizing, order placement, runtime-mode changes, live configuration writes,
  strategy-catalog mutations, archive manifest/source mutations, or promotion
  claims.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness,
  strict-validation descriptor queues, artifact catalog sidecar identity, and
  the 2024+ window policy.

## Plan

1. Add a stable Parquet schema for catalog analysis bucket rollup rows.
2. Flatten `run_analysis` artifacts into sidecar rows with source path/run
   metadata, bucket identity, counts, best representative trial fields, and
   non-authorizing flags.
3. Register the sidecar in the catalog sidecar index with post-write file
   identity.
4. Add regressions for populated and empty sidecar behavior.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-334 added run-local analysis bucket
  rollups but left cross-run discovery dependent on opening each analysis JSON.
- 2026-06-19: Added
  `sandbox_artifact_catalog_analysis_bucket_rollups.parquet` with one row per
  embedded run analysis bucket rollup, including source analysis paths, source
  run ID, bucket identity, counts, best representative trial fields, and
  non-authorizing flags.
- 2026-06-19: Registered the analysis bucket rollup sidecar in the catalog
  sidecar index with post-write file identity metadata.
- 2026-06-19: Extended populated and empty catalog sidecar regressions for the
  analysis bucket sidecar.

## Validation

- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "artifact_catalog_indexes_known_artifacts or artifact_catalog_surfaces_failed_run_integrity"`
  passed with 2 passed and 172 deselected.
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

Closed 2026-06-19. WPR106-335 keeps artifact catalog analysis bucket rows
research-only and non-authorizing while making existing run-local analysis
rollups queryable across many sandbox runs from one compact Parquet sidecar. No
candidate pack, paper/live signal, order/sizing/runtime change, provider
download, replay execution, validation execution, strategy catalog mutation,
archive manifest/source mutation, live configuration write, or promotion claim
was added.
