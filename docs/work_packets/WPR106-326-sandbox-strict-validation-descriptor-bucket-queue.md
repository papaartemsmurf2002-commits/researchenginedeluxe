# WPR106-326 Sandbox Strict Validation Descriptor Bucket Queue

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add a bounded strict-validation descriptor bucket queue to sandbox artifact
catalogs so agents can quickly see which venue/symbol validation-request
clusters are ready without scanning every descriptor row.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-326-sandbox-strict-validation-descriptor-bucket-queue.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_BUCKET_QUEUE_REPORT.md`
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
- Derive bucket rows only from already-flattened strict-validation descriptor
  catalog rows.
- Bucket rows may expose read-only venue, symbol, requested-validation, source
  scope, count, metric, and representative descriptor metadata.
- Empty catalogs must still write a stable empty-schema Parquet sidecar for
  automation.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Add descriptor bucket queue constants, schema, and row builders.
2. Emit bounded descriptor bucket queue JSON metadata plus a flat Parquet
   sidecar from artifact catalogs.
3. Add focused regressions for populated multi-venue bucket rows and empty
   bucket sidecar behavior.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-325 made individual descriptors
  queryable but left venue/symbol clustering to downstream scans.
- 2026-06-19: Added bounded strict-validation descriptor bucket queues grouped
  by venue/symbol and venue/symbol/requested-validation, with representative
  descriptor/source-trial/bundle IDs.
- 2026-06-19: Added a compact descriptor bucket queue Parquet sidecar with
  stable empty-schema behavior.
- 2026-06-19: Added focused catalog regressions for populated multi-venue
  bucket rows and empty no-bundle bucket sidecars.
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

WPR106-326 is closed. Sandbox artifact catalogs now expose
`strict_validation_descriptor_bucket_queue` metadata and write
`sandbox_artifact_catalog_strict_validation_descriptor_bucket_queue.parquet`.
The bucket queue is derived only from flattened descriptor catalog rows, groups
requests by venue/symbol and venue/symbol/requested-validation, records compact
counts and representative descriptor IDs, keeps sandbox boundary flags, and
writes an empty-schema Parquet file when no bucket rows exist. No replay command
execution, validation execution, provider download, strict-cycle execution,
candidate pack, paper/live artifact, order/sizing/runtime change, live
configuration write, strategy catalog mutation, archive manifest/source
mutation, or promotion claim exists.
