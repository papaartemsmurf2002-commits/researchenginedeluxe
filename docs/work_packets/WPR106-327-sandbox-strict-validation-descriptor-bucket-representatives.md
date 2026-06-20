# WPR106-327 Sandbox Strict Validation Descriptor Bucket Representatives

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Write a strict-validation descriptor bucket representative Parquet sidecar so
agents can jump from venue/symbol validation-request buckets to representative
descriptor metadata without scanning or joining the full descriptor table first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-327-sandbox-strict-validation-descriptor-bucket-representatives.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_BUCKET_REPRESENTATIVES_REPORT.md`
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
- Derive representative rows only from already-flattened strict-validation
  descriptor catalog rows and the bounded descriptor bucket queue.
- Representative rows may expose read-only bucket identity, descriptor identity,
  source trial, venue, symbol, requested-validation, market-window, source
  metric, and routing metadata.
- Empty catalogs must still write a stable empty-schema Parquet sidecar for
  automation.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  2024+ window policy.

## Plan

1. Add descriptor bucket representative metadata to bucket queue items.
2. Write a flat representative Parquet sidecar with stable empty-schema
   behavior.
3. Add focused regressions for populated representative rows and empty
   no-bucket sidecars.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-326 added descriptor bucket queues but
  only exposed representative descriptor IDs in the bucket sidecar.
- 2026-06-19: Added compact representative metadata to strict-validation
  descriptor bucket queue items, derived only from already-flattened descriptor
  catalog rows.
- 2026-06-19: Added
  `sandbox_artifact_catalog_strict_validation_descriptor_bucket_representatives.parquet`
  with stable empty-schema behavior.
- 2026-06-19: Added payload path and row-count fields for the representative
  sidecar.
- 2026-06-19: Added focused regressions for populated representative rows and
  failed-integrity empty sidecars.
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

Closed 2026-06-19. The packet adds read-only strict-validation descriptor
bucket representative Parquet rows for agent navigation. It does not execute or
authorize strict validation, write candidate packs, execute replay commands,
mutate source catalogs/manifests, download provider data, create paper/live
artifacts, define sizing, place orders, change runtime mode, write live
configuration, or claim promotion readiness.
