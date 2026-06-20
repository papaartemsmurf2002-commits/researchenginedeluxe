# WPR106-338 Sandbox Artifact Catalog Global Bucket Top-Buckets Sidecar

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Flatten bounded `top_buckets` rows from indexed
`sandbox_global_leaderboard.json` artifacts into a compact artifact-catalog
Parquet sidecar so agents can query cross-run global bucket leaders from the
catalog output without opening every leaderboard JSON or companion bucket
Parquet file first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-338-sandbox-artifact-catalog-global-bucket-top-buckets-sidecar.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARTIFACT_CATALOG_GLOBAL_BUCKET_TOP_BUCKETS_SIDECAR_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Derive sidecar rows only from bounded `top_buckets` already present in the
  loaded `sandbox_global_leaderboard.json` payload.
- Do not open or recompute `sandbox_global_bucket_leaderboard.parquet` while
  building catalog sidecar rows.
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

1. Add a global bucket top-buckets sidecar schema and row projector.
2. Register the sidecar in the catalog sidecar index and catalog manifest.
3. Extend focused catalog/global leaderboard regression coverage.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-337 made the companion global bucket
  path discoverable but still required agents to open each leaderboard JSON or
  bucket Parquet to query the bounded top-bucket rows.
- 2026-06-19: Added
  `sandbox_artifact_catalog_global_bucket_top_buckets.parquet`, populated only
  from bounded `top_buckets` rows in loaded global leaderboard JSON payloads.
- 2026-06-19: Registered the new sidecar in the catalog sidecar index with
  post-write file identity metadata and empty-schema behavior when no global
  leaderboard top buckets exist.
- 2026-06-19: Extended focused catalog/global leaderboard regressions to verify
  populated sidecar rows, empty sidecar behavior, sidecar index row counts, rank
  ordering, bucket values, source paths, and non-authorizing flags.

## Validation

- 2026-06-19:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "global_leaderboard or artifact_catalog"`
  passed with 4 passed and 170 deselected.
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

Closed 2026-06-19. WPR106-338 adds a catalog-owned Parquet sidecar for bounded
global leaderboard top-bucket rows, derived only from loaded leaderboard JSON
payloads. No full bucket Parquet read, recomputation, sandbox sweep, provider
download, strict-cycle execution, replay command execution, validation
execution, candidate-pack write, paper/live signal, order/sizing/runtime
change, live configuration write, strategy catalog mutation, archive
manifest/source mutation, or promotion claim was added.
