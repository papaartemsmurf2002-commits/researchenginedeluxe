# WPR106-344 Sandbox Artifact Catalog Global Evidence-Request Priority Queue

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add a bounded global evidence-request priority queue to sandbox artifact
catalogs so agents can start from the highest-ranked descriptor-only global
leaderboard strict-validation requests without scanning the full flat global
evidence-request sidecar first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-344-sandbox-artifact-catalog-global-evidence-request-priority-queue.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_PRIORITY_QUEUE_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive priority queue rows only from in-memory global evidence-request rows
  already produced from bounded `top_hypotheses` in loaded
  `sandbox_global_leaderboard.json` payloads during the same catalog write.
- Do not open or recompute `sandbox_global_leaderboard.parquet` while building
  the queue or sidecar.
- Do not execute sandbox sweeps, iteration replay commands, strict validation,
  provider downloads, candidate-pack writes, paper/live signal generation,
  sizing, order placement, runtime-mode changes, live configuration writes,
  strategy-catalog mutations, archive manifest/source mutations, or promotion
  claims.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  the 2024+ window policy.

## Plan

1. Add a bounded global evidence-request priority queue sorted by global
   leaderboard rank, best score, source artifact, and request identity.
2. Write a compact priority queue Parquet sidecar with stable empty-schema
   behavior and register it in the catalog sidecar index.
3. Expose catalog manifest queue limit/count/path/row-count metadata.
4. Extend focused catalog/global leaderboard regression coverage.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-343 exposed global
  evidence-request metadata but agents still needed to open the full flat
  global request sidecar to inspect the top concrete descriptor rows.
- 2026-06-19: Added
  `sandbox_artifact_catalog_global_evidence_request_priority_queue.parquet`
  schema and a bounded queue derived from in-memory global evidence-request
  rows.
- 2026-06-19: Registered the priority queue in the catalog sidecar index with
  post-write file identity metadata and exposed catalog manifest
  limit/count/path/row-count fields.
- 2026-06-19: Extended global evidence-request summary metadata with priority
  queue counts.
- 2026-06-19: Extended focused artifact catalog/global leaderboard coverage for
  empty-schema behavior, populated queue ordering, queue row metadata,
  sidecar-index row counts, and non-authorizing flags.
- 2026-06-19: Updated the sandbox contract, active index, stage ledger, and
  stage report.

## Validation

- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "global_leaderboard or artifact_catalog"`
  - 4 passed, 170 deselected.
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q`
  - 174 passed.
- Passed:
  `$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite`
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q`
  - 11 passed.
- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - 461 passed.

## Closeout

- Closed 2026-06-19. The packet keeps catalog rows, queues, and sidecars
  research-only, observe-only, sandbox-only, descriptor-only, and
  promotion-ready false. It does not open or recompute
  `sandbox_global_leaderboard.parquet`, execute sandbox sweeps, iteration
  replay commands, strict validation, provider downloads, candidate-pack
  writes, paper/live signal generation, sizing, order placement, runtime-mode
  changes, live configuration writes, strategy-catalog mutations, archive
  manifest/source mutations, or promotion claims.
