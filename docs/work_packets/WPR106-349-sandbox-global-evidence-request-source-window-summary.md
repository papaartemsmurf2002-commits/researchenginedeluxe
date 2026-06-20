# WPR106-349 Sandbox Global Evidence-Request Source Window Summary

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Enrich the sandbox artifact catalog global evidence-request source-summary
Parquet sidecar with compact source market-window and unique-count metadata so
agents can verify 2024+ source coverage by source venue, symbol, data family,
interval, routing mode, venue descriptor, and data path without scanning the
full flat request table.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-349-sandbox-global-evidence-request-source-window-summary.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_WINDOW_SUMMARY_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive enriched sidecar rows only from the in-memory global evidence-request
  summary and global evidence-request rows already produced during the same
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

1. Add source market-window and unique-count columns to the source-summary
   sidecar schema.
2. Build those fields from already-flattened in-memory global evidence-request
   rows while preserving compact field/value summary rows.
3. Extend focused artifact catalog regression coverage.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline and diff hygiene.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-348 made source summary counts
  sidecar-indexed, but the sidecar did not yet expose market-window bounds for
  quick 2024+ source coverage triage.
- 2026-06-19: Added source-summary sidecar columns for unique request-trial
  counts, source leaderboard counts, and source market start/end min/max
  bounds per source-context field/value row.
- 2026-06-19: Derived the new fields from the already-flattened in-memory
  global evidence-request rows produced during the same catalog write, without
  opening per-run evidence requests or recomputing leaderboards.
- 2026-06-19: Extended artifact catalog regression coverage to assert the
  source-summary sidecar's unique counts, source leaderboard counts, and 2024+
  source market-window bounds.
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
