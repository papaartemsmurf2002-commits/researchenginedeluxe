# WPR106-324 Sandbox Strict Validation Bundle Parquet Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Write a compact strict-validation bundle queue Parquet sidecar beside sandbox
artifact catalogs so agents can query descriptor-only validation handoff
bundles without opening catalog JSON or individual bundle JSON files.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-324-sandbox-strict-validation-bundle-parquet-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_BUNDLE_PARQUET_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Do not execute strict validation, replay commands, write candidate packs,
  create paper/live signals, define sizing, place orders, change runtime mode,
  write live configuration, download provider data, mutate strategy catalogs,
  mutate archive manifests/source files, or claim promotion readiness.
- Derive the sidecar only from the already-built strict-validation bundle queue
  and catalog row metadata.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.
- Empty or blocked catalogs must still write a stable empty-schema Parquet
  sidecar for automation.

## Plan

1. Add a strict-validation bundle queue Parquet sidecar name, schema, and row
   writer.
2. Include sidecar path and row-count metadata in artifact catalog payloads.
3. Add focused regressions for populated and empty sidecar behavior.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after confirming WPR106-323 exposes the bundle
  queue only in catalog JSON, while replay bucket queues already have flat
  Parquet sidecars for agent automation.
- 2026-06-19: Added a strict-validation bundle queue Parquet sidecar with a
  stable empty schema, sidecar path metadata, and row-count metadata in artifact
  catalog payloads.
- 2026-06-19: Added focused catalog regressions for populated run/suite bundle
  sidecar rows and no-bundle empty sidecar behavior.
- 2026-06-19: Updated the sandbox research contract, active index, stage ledger,
  and stage report.

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

WPR106-324 is closed. Sandbox artifact catalogs now write
`sandbox_artifact_catalog_strict_validation_bundle_queue.parquet` beside the
catalog JSON/Parquet outputs. The sidecar is derived only from the bounded
strict-validation bundle queue, keeps sandbox boundary flags, includes explicit
non-authorizing flags, and writes an empty-schema Parquet file when no bundle
queue rows exist. No replay command execution, validation execution, provider
download, strict-cycle execution, candidate pack, paper/live artifact,
order/sizing/runtime change, live configuration write, strategy catalog
mutation, archive manifest/source mutation, or promotion claim exists.
