# WPR106-351 Sandbox Global Evidence-Request Source Summary Best Context

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Enrich the sandbox artifact catalog global evidence-request source-summary
Parquet sidecar with compact best-row context per source-context field/value
row. Agents should be able to prioritize source venue, symbol, data family,
interval, routing mode, venue descriptor, and data-path queues by best
leaderboard/source metric context without opening the full flat global
evidence-request table first.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-351-sandbox-global-evidence-request-source-summary-best-context.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_BEST_CONTEXT_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only
  where applicable, and promotion-ready false.
- Derive best-context fields only from the in-memory global evidence-request
  rows already produced during the same catalog write.
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

1. Add best leaderboard/source metric and identity columns to the
   source-summary sidecar schema.
2. Populate those columns from the same deterministic representative ordering
   used by WPR106-350.
3. Extend focused artifact catalog regression coverage.
4. Update the sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline and diff hygiene.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-350 added bounded representative
  request/source IDs and paths to the source-summary sidecar, but the compact
  source rows still lacked best-row metric context for queue prioritization.
- 2026-06-19: Added compact best-context columns to the source-summary sidecar
  schema for best leaderboard rank, best global score, best source metric
  rank/score/net return/trade count, best evidence-request trial ID, best
  source trial ID, best hypothesis ID, and best family.
- 2026-06-19: Populated best-context fields from the same deterministic
  in-memory global evidence-request row ordering used for bounded
  representatives.
- 2026-06-19: Extended focused artifact catalog regression coverage to assert
  each source-summary row's best-context fields match its top concrete flat
  global evidence-request row.
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
- Passed:
  `git diff --check`
  - No whitespace errors; existing LF-to-CRLF warnings were reported.
- Passed:
  direct trailing-whitespace scan of packet-touched files.

## Closeout

- Closed 2026-06-19. The packet keeps all outputs research-only, observe-only,
  sandbox-only, descriptor-only where applicable, and promotion-ready false. It
  does not open per-run evidence request files, open or recompute global
  leaderboard Parquet files, execute sandbox sweeps, iteration replay
  commands, strict validation, provider downloads, candidate-pack writes,
  paper/live signal generation, sizing, order placement, runtime-mode changes,
  live configuration writes, strategy-catalog mutations, archive
  manifest/source mutations, or promotion claims.
