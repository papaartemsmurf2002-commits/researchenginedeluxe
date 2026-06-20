# WPR106-328 Sandbox Strict Validation Descriptor Priority Queue

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add a bounded strict-validation descriptor priority queue to sandbox artifact
catalogs so agents can start from the highest-priority descriptor-only evidence
requests across bundles without scanning the full descriptor sidecar first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-328-sandbox-strict-validation-descriptor-priority-queue.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_STRICT_VALIDATION_DESCRIPTOR_PRIORITY_QUEUE_REPORT.md`
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
- Derive priority rows only from already-flattened strict-validation descriptor
  catalog rows.
- Priority rows may expose read-only descriptor identity, source trial, venue,
  symbol, requested-validation, market-window, source metric, routing,
  required-evidence count, and strict-validation entrypoint metadata.
- Empty catalogs must still write a stable empty-schema Parquet sidecar for
  automation.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness,
  descriptor bucket queues, and the 2024+ window policy.

## Plan

1. Add a bounded strict-validation descriptor queue sorted by source metric,
   source rank, and deterministic descriptor identity.
2. Write a flat descriptor priority Parquet sidecar with stable empty-schema
   behavior.
3. Add focused regressions for populated priority rows and empty no-descriptor
   sidecars.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-327 added descriptor bucket
  representative sidecars but left no bounded top-descriptor start queue.
- 2026-06-19: Added a bounded strict-validation descriptor priority queue
  sorted by source metric score, source metric rank, and stable descriptor
  identity.
- 2026-06-19: Added
  `sandbox_artifact_catalog_strict_validation_descriptor_queue.parquet` with
  stable empty-schema behavior.
- 2026-06-19: Added catalog payload metadata for queue limit, queue count,
  queue rows, sidecar path, and sidecar row count.
- 2026-06-19: Added focused regressions for populated priority rows and
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
priority queue rows for agent navigation. It does not execute or authorize
strict validation, write candidate packs, execute replay commands, mutate
source catalogs/manifests, download provider data, create paper/live artifacts,
define sizing, place orders, change runtime mode, write live configuration, or
claim promotion readiness.
