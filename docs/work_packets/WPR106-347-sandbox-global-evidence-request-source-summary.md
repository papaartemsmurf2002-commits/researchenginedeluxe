# WPR106-347 Sandbox Global Evidence-Request Source Summary

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Expose compact source-context count maps in sandbox artifact catalog global
evidence-request summaries so agents can see source venue, symbol, data family,
interval, routing, descriptor, and data-path availability before opening bucket
or flat request sidecars.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-347-sandbox-global-evidence-request-source-summary.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_GLOBAL_EVIDENCE_REQUEST_SOURCE_SUMMARY_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive source summary counts only from in-memory global evidence-request rows
  already produced from bounded global leaderboard JSON previews during the
  same catalog write.
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

1. Add source venue, symbol, data family, interval, and data-path count maps to
   the global evidence-request summary.
2. Surface those count maps on the artifact catalog manifest next to existing
   source routing and venue descriptor counts.
3. Extend focused artifact catalog regression assertions.
4. Update sandbox contract, active index, stage ledger, and stage report.
5. Run focused sandbox validation plus compile/import-boundary/contracts
   baseline and diff hygiene.

## Implementation Log

- 2026-06-19: Opened packet after WPR106-346 added source-context bucket queue
  and representative rows, but the top-level catalog summary still exposed only
  source routing-mode and venue-descriptor count maps.
- 2026-06-19: Added source venue, source symbol, source data family, source
  interval, source routing-mode, source venue descriptor, and source data-path
  count maps to the in-memory global evidence-request summary.
- 2026-06-19: Surfaced those maps as top-level artifact catalog manifest fields
  next to the existing global evidence-request summary and sidecar metadata.
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
