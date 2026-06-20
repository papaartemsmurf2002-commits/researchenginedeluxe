# WPR106-337 Sandbox Artifact Catalog Global Bucket Leaderboard Metadata

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose already-written sandbox global bucket leaderboard metadata on artifact
catalog rows so agents can discover the companion bucket Parquet, bucket
counts, decision counts, and bounded top-bucket preview without reopening
leaderboard artifacts manually.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-337-sandbox-artifact-catalog-global-bucket-leaderboard-metadata.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_BUCKET_LEADERBOARD_METADATA_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Derive catalog row metadata only from the already-loaded
  `sandbox_global_leaderboard.json` payload.
- Do not open or recompute `sandbox_global_bucket_leaderboard.parquet` while
  building catalog rows.
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

1. Add global bucket leaderboard metadata fields to catalog rows for
   `global_leaderboard` artifacts.
2. Extend the global leaderboard/catalog regression to assert JSON and Parquet
   catalog discoverability.
3. Update the sandbox contract, active index, stage ledger, and stage report.
4. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-336 added the companion bucket
  leaderboard Parquet but artifact catalog rows only exposed the existence of
  the global leaderboard JSON.
- 2026-06-19: Added read-only global bucket metadata to catalog rows for
  `global_leaderboard` artifacts, including bucket count, bounded top-bucket
  count/types, bucket decision counts, and companion bucket Parquet path.
- 2026-06-19: Extended the global leaderboard regression to verify catalog JSON
  and catalog Parquet discoverability for the companion bucket leaderboard.

## Validation

- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "global_leaderboard"`
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

Closed 2026-06-19. WPR106-337 makes the artifact catalog expose
global bucket leaderboard companion metadata from the loaded leaderboard JSON
only. No bucket Parquet read, recomputation, sandbox sweep, provider download,
strict-cycle execution, replay command execution, validation execution,
candidate-pack write, paper/live signal, order/sizing/runtime change, live
configuration write, strategy catalog mutation, archive manifest/source
mutation, or promotion claim was added.
