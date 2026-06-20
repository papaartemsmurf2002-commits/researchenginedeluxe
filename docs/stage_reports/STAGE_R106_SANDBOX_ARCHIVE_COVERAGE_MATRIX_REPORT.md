# Stage R106 Sandbox Archive Coverage Matrix Report

Date: 2026-06-18
Work packet: `docs/work_packets/WPR106-260-sandbox-archive-coverage-matrix.md`
Status: closed

## Summary

WPR106-260 adds a compact archive coverage matrix for sandbox venue manifests
so agents can see ready, blocked, and mixed local archive coverage by venue,
symbol, data family, interval, and 2024+ window before launching sweeps or
suites.

## Implementation

- Added `summarize_sandbox_archive_coverage()` in
  `src/tradingbotsuite/research_sandbox/archive_coverage.py`.
- Coverage summaries reuse `audit_sandbox_archive_descriptors()` so
  source-integrity checks, 2024+ filtering, shared-market-data smoke behavior,
  and loader blockers remain consistent with audit, preflight, and sweeps.
- Coverage artifacts write `archive_coverage_matrix.json` and
  `archive_coverage_matrix.parquet` with sandbox boundary flags.
- Coverage rows group by venue, symbol, data family, and interval, then expose
  descriptor IDs, source paths, ready/blocked descriptor counts, row counts,
  market bounds, declared/observed window bounds, and blocker/warning counts.
- The sandbox artifact catalog now discovers `archive_coverage_matrix.json`.

## Boundary

The packet adds read-only archive coverage summaries only. It does not execute
sandbox sweeps, execute strict validation, change strategy math, change trial
IDs, write candidate packs, create paper/live signals, define sizing, place
orders, change runtime mode, write live configuration, download provider data,
mutate source archive files, or claim promotion readiness.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q -k "archive_coverage"
# 1 passed, 86 deselected

$env:PYTHONPATH='src'; python -m pytest tests\research_sandbox\test_sandbox_foundation.py -q
# 87 passed

python -m compileall -q src\tradingbotsuite
# passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_import_boundaries.py -q
# 11 passed

$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# attempted three times; each reached 460 passed tests, then failed during
# pytest-asyncio Windows event-loop socket setup with known WinError 10055

$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py::test_provider_kline_fixture_pack_builder_accepts_collected_binance_context_manifest -q
# 1 passed
```

## Remaining Work

Coverage matrices are available as a read-only API and cataloged artifact. A
later packet can add a dedicated CLI command if agents need direct command-line
coverage generation outside the existing Python API.
