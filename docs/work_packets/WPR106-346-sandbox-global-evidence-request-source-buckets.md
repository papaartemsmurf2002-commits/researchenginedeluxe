# WPR106-346 Sandbox Global Evidence-Request Source Buckets

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Extend sandbox artifact catalog global evidence-request bucket queues and
bucket representatives with actual source-context routing fields so agents can
triage descriptor-only strict-validation requests by source venue descriptor,
source venue/symbol, source routing mode, and source data path without scanning
the full flat request table.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-346-sandbox-global-evidence-request-source-buckets.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_BUCKETS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive buckets only from in-memory global evidence-request rows already
  produced from bounded global leaderboard JSON previews during the same
  catalog write.
- Do not open per-run evidence request files, open or recompute global
  leaderboard Parquet files, execute sandbox sweeps, iteration replay commands,
  strict validation, provider downloads, candidate-pack writes, paper/live
  signal generation, sizing, order placement, runtime-mode changes, live
  configuration writes, strategy-catalog mutations, archive manifest/source
  mutations, or promotion claims.
- Preserve sandbox scoring, ranking math, falsification decisions,
  blocker/rejection semantics, evidence-request selection, trial IDs, archive
  routing, preflight behavior, source-integrity behavior, replay readiness, and
  the 2024+ window policy.

## Plan

1. Add source-context scalar fields needed for bucketing to global
   evidence-request rows when context is available.
2. Extend global evidence-request bucket memberships with source-context
   buckets such as source venue descriptor, source venue/symbol, source routing
   mode, and source data path.
3. Surface source bucket fields in bucket queue and representative Parquet
   sidecars while preserving empty-schema behavior.
4. Extend focused global leaderboard/artifact catalog regression coverage.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-345 exposed source context on flat
  global evidence-request rows and the priority queue, but source-context
  routing was not yet available in global request bucket queues or bucket
  representative rows.
- 2026-06-19: Added source venue, source symbol, source data family, and source
  interval scalar fields to global evidence-request source-context columns.
- 2026-06-19: Extended global evidence-request bucket memberships with
  descriptor-only source venue, source symbol, source venue/symbol, source data
  family, source interval, source venue descriptor, source routing mode, and
  source data path buckets.
- 2026-06-19: Surfaced source-context fields on bucket queue rows and both
  bucket-level plus row-level source-context fields on bucket representative
  rows while preserving empty-schema Parquet behavior.
- 2026-06-19: Extended focused artifact catalog regression coverage and updated
  the sandbox contract, active index, stage ledger, and stage report.

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
- Passed:
  `git diff --check`
  - No whitespace errors; existing LF-to-CRLF warnings were reported.
- Passed:
  direct trailing-whitespace scan of packet-touched files.

## Closeout

- Closed 2026-06-19. The packet keeps all outputs research-only, observe-only,
  sandbox-only, descriptor-only where applicable, and promotion-ready false. It
  does not open per-run evidence request files, open or recompute global
  leaderboard Parquet files, execute sandbox sweeps, iteration replay commands,
  strict validation, provider downloads, candidate-pack writes, paper/live
  signal generation, sizing, order placement, runtime-mode changes, live
  configuration writes, strategy-catalog mutations, archive manifest/source
  mutations, or promotion claims.
