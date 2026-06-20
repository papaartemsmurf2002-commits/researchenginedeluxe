# WPR106-343 Sandbox Artifact Catalog Global Evidence-Request Metadata

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose compact global evidence-request metadata directly on sandbox global
leaderboard catalog rows and the artifact catalog manifest so agents can see
whether requestable strict-validation descriptors exist, how many hypotheses
own them, and what decision/request labels they carry before opening any
evidence-request sidecar.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-343-sandbox-artifact-catalog-global-evidence-request-metadata.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_EVIDENCE_REQUEST_METADATA_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive row-level global evidence-request metadata only from bounded
  `top_hypotheses` already present in loaded `sandbox_global_leaderboard.json`
  payloads.
- Derive catalog-level global evidence-request metadata only from the
  in-memory evidence-request rows and bucket queues already produced during the
  same catalog write.
- Do not open or recompute `sandbox_global_leaderboard.parquet` while building
  these metadata fields.
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

1. Add small metadata helpers for global leaderboard evidence-request preview
   rows and in-memory request sidecar rows.
2. Surface row-level request counts, unique hypothesis counts, decision counts,
   requested-validation counts, and tested venue/symbol/family counts on global
   leaderboard catalog rows.
3. Surface catalog-level request/bucket/representative summary fields on the
   catalog manifest.
4. Extend focused catalog/global leaderboard regression coverage.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-342 made evidence-request bucket
  representatives queryable while the main catalog row still did not expose
  whether a global leaderboard had requestable descriptor rows without reading
  a sidecar.
- 2026-06-19: Added global leaderboard catalog-row metadata for evidence
  request count, unique request-trial count, requesting-hypothesis count,
  requested-validation counts, leaderboard-decision counts, family counts, and
  tested venue/symbol counts derived from bounded loaded leaderboard JSON
  preview rows.
- 2026-06-19: Added a top-level `global_evidence_request_summary` and direct
  catalog manifest aliases derived from in-memory evidence-request rows, bucket
  queues, and representative rows produced during the same catalog write.
- 2026-06-19: Extended focused artifact catalog/global leaderboard coverage for
  populated JSON row metadata, catalog Parquet row metadata, top-level summary
  metadata, non-authorizing flags, and zero-count empty-sidecar behavior.
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

- Closed 2026-06-19. The packet keeps catalog rows and summaries
  research-only, observe-only, sandbox-only, descriptor-only, and
  promotion-ready false. It does not open or recompute
  `sandbox_global_leaderboard.parquet`, execute sandbox sweeps, iteration
  replay commands, strict validation, provider downloads, candidate-pack
  writes, paper/live signal generation, sizing, order placement, runtime-mode
  changes, live configuration writes, strategy-catalog mutations, archive
  manifest/source mutations, or promotion claims.
