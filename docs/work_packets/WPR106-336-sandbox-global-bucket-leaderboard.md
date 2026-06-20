# WPR106-336 Sandbox Global Bucket Leaderboard

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add a cross-run bucket leaderboard to sandbox global leaderboard artifacts so
agents can rank venue, symbol, family, exit, filter, venue/symbol, and
venue/family clusters directly from integrity-checked sandbox rankings, even
when per-run `analysis_summary.json` files have not been generated yet.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-336-sandbox-global-bucket-leaderboard.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_BUCKET_LEADERBOARD_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/leaderboard.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, and
  promotion-ready false.
- Derive bucket leaderboard rows only from existing integrity-checked sandbox
  ranking rows and descriptor-only evidence requests that the global leaderboard
  already loads.
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

1. Add a global bucket leaderboard builder over already-loaded ranking rows.
2. Include top bucket rows in `sandbox_global_leaderboard.json`.
3. Write a compact `sandbox_global_bucket_leaderboard.parquet` with stable
   empty-schema behavior.
4. Extend global leaderboard regressions for populated bucket rows and
   non-promotable boundary flags.
5. Update sandbox contract, active index, stage ledger, and stage report.
6. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-335 made analysis-bucket rollups
  catalog-queryable but still depended on per-run analysis reports. The global
  leaderboard already has integrity-checked ranking rows available and can
  provide bucket ranking directly.
- 2026-06-19: Added `sandbox_global_bucket_leaderboard.parquet` and bounded
  `top_buckets` JSON preview rows to global leaderboard output.
- 2026-06-19: Bucket rows now group already-loaded rankings by venue, symbol,
  venue/symbol, family, exit profile, exit variant, filter variant, and
  venue/family, carrying compact counts, best representative trial fields,
  decision labels, and non-authorizing flags.
- 2026-06-19: Extended the global leaderboard regression to verify bucket
  rows, Parquet output, JSON preview rows, rank ordering, and boundary flags.

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

Closed 2026-06-19. WPR106-336 keeps global bucket leaderboard rows
research-only and non-authorizing while ranking venue, symbol, family, exit,
and filter clusters directly from integrity-checked sandbox rankings. No
candidate pack, paper/live signal, order/sizing/runtime change, provider
download, replay execution, validation execution, strategy catalog mutation,
archive manifest/source mutation, live configuration write, or promotion claim
was added.
