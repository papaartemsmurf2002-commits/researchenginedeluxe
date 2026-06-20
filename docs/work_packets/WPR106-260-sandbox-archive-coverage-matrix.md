# WPR106-260 Sandbox Archive Coverage Matrix

Status: closed
Owner: Codex Research Agent
Created: 2026-06-18

## Objective

Add a compact archive coverage matrix for sandbox venue manifests so agents can
quickly see which Binance, OKX, Bybit, Hyperliquid, and local-manifest inputs
are ready by venue, symbol, data family, interval, and 2024+ window before
launching archive-backed suites or sweeps.

## Scope

- Add a read-only sandbox archive coverage summary API.
- Reuse existing descriptor loading and archive audit behavior so source
  integrity, 2024+ filtering, and shared-market-data smoke semantics stay
  consistent.
- Write compact JSON and Parquet coverage artifacts with sandbox boundary
  flags.
- Summarize ready/blocked descriptor counts, blocker reasons, row counts,
  normalized market bounds, and descriptor-window bounds by coverage bucket.
- Add focused tests for multi-venue ready/blocked coverage.
- Update the sandbox contract and stage docs.

## Allowed Paths

- `docs/work_packets/WPR106-260-sandbox-archive-coverage-matrix.md`
- `docs/stage_reports/STAGE_R106_SANDBOX_ARCHIVE_COVERAGE_MATRIX_REPORT.md`
- `docs/contracts/sandbox_research_contract.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/research_sandbox/archive_coverage.py`
- `src/tradingbotsuite/research_sandbox/__init__.py`
- `src/tradingbotsuite/research_sandbox/catalog.py`
- `tests/research_sandbox/**`
- `docs/KNOWN_ISSUES.md` only if a new blocking evidence or boundary risk is
  discovered

## Acceptance Evidence

- Coverage summaries load venue archive manifests and emit sandbox-only JSON
  and Parquet artifacts.
- Coverage buckets group descriptors by venue, symbol, data family, and
  interval.
- Ready and blocked descriptor counts, row counts, timestamp bounds,
  descriptor-window bounds, descriptor IDs, source paths, and blocker counts
  are present in the output.
- Source-integrity mismatches and no-2024+ data remain blockers through the
  existing audit path.
- Outputs remain research-only, observe-only, promotion-ready false,
  sandbox-only, candidate-evidence false, and candidate-pack-ineligible.
- Validation includes focused sandbox tests, import-boundary tests, package
  compile, and the contract baseline when the local validation environment
  allows pytest-asyncio socket setup.

## Boundary

This packet adds read-only archive coverage summaries only. It does not execute
sandbox sweeps, execute strict validation, change strategy math, change trial
IDs, write candidate packs, create paper/live signals, define sizing, place
orders, change runtime mode, write live configuration, download provider data,
mutate source archive files, or claim promotion readiness.

## Completion Notes

Implemented and closed on 2026-06-18. Added
`summarize_sandbox_archive_coverage()` as a read-only coverage matrix over the
existing archive descriptor audit path. Coverage buckets group descriptors by
venue, symbol, data family, and interval, and record ready/blocked descriptor
counts, descriptor IDs, source paths, row counts, market bounds,
declared/observed window bounds, and blocker/warning counts. The sandbox
artifact catalog now indexes `archive_coverage_matrix.json`.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_coverage"
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest -q
```

Final results: 1 focused archive-coverage sandbox test passed, 87 sandbox
tests passed, package compileall passed, and 11 import-boundary tests passed.
The full contract baseline was attempted three times and each run reached 460
passed tests before failing during pytest-asyncio Windows event-loop socket
setup with known `WinError 10055`; the affected async contract test passed
when run alone.
