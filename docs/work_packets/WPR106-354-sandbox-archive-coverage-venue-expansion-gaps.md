# WPR106-354 Sandbox Archive Coverage Venue Expansion Gaps

Status: closed
Owner: Codex Research Agent
Started: 2026-06-19

## Objective

Add compact venue-expansion gap rows to sandbox archive coverage output so
agents can see which OKX, Bybit, and Hyperliquid archive buckets are ready,
blocked, or missing for each observed symbol/data-family/interval without
manually comparing observed coverage rows.

## Scope

Allowed paths:

- `docs/work_packets/WPR106-354-sandbox-archive-coverage-venue-expansion-gaps.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_VENUE_EXPANSION_GAPS_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/archive_coverage.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Requirements

- Keep all outputs research-only, observe-only, sandbox-only, descriptor-only,
  and promotion-ready false.
- Derive venue-expansion gap rows only from already-produced archive coverage
  rows and requested-window diagnostics in the same coverage write.
- Do not execute sandbox sweeps, iteration replay commands, strict validation,
  provider downloads, candidate-pack writes, paper/live signal generation,
  sizing, order placement, runtime-mode changes, live configuration writes,
  strategy-catalog mutations, archive manifest/source mutations, or promotion
  claims.
- Do not change archive descriptor loading, market-frame normalization,
  source-integrity checks, coverage bucket status semantics, preflight
  behavior, replay readiness, trial IDs, ranking/scoring, or
  evidence-request selection.
- Preserve the 2024+ window policy; this packet must only summarize coverage
  already filtered by sandbox archive audit/coverage.

## Plan

1. Add deterministic venue-expansion gap rows for OKX, Bybit, and Hyperliquid
   across observed symbol/data-family/interval buckets.
2. Write a compact Parquet sidecar plus manifest counts/path fields from the
   archive coverage writer.
3. Extend archive coverage tests for ready, blocked, mixed, and missing target
   venue statuses.
4. Update the sandbox contract, active index, stage ledger, and stage report.
5. Run focused archive coverage validation plus compile/import-boundary/
   contracts baseline and diff hygiene.

## Implementation Log

- 2026-06-19: Opened packet after confirming coverage matrices expose observed
  venue/status buckets, but agents still have to manually compare OKX, Bybit,
  and Hyperliquid coverage across symbol/data-family/interval groups.
- 2026-06-19: Added
  `archive_coverage_venue_expansion_gaps.parquet`, derived only from
  in-memory archive coverage rows.
- 2026-06-19: Grouped venue targets by compact market symbol key, data family,
  and interval so Hyperliquid-style `BTC` descriptors can be compared with
  OKX/Bybit-style `BTCUSDT` descriptors for venue expansion triage.
- 2026-06-19: Added target status and descriptor-only action counts for ready,
  mixed, blocked, and missing OKX/Bybit/Hyperliquid archive buckets.

## Validation

- Passed:
  `$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_coverage_matrix"`
  - 3 passed, 171 deselected.
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
  sandbox-only, descriptor-only, and promotion-ready false. It only adds
  archive coverage venue-expansion diagnostics derived from existing coverage
  rows.
- It does not change archive descriptor loading, market-frame normalization,
  source-integrity checks, coverage bucket status semantics, preflight
  behavior, replay readiness, trial IDs, ranking/scoring, evidence-request
  selection, candidate-pack state, or promotion state.
- No sandbox sweep, iteration replay command, strict validation, provider
  download, candidate-pack write, paper/live signal generation, sizing, order
  placement, runtime-mode change, live configuration write, strategy-catalog
  mutation, archive manifest/source mutation, or promotion claim exists.
