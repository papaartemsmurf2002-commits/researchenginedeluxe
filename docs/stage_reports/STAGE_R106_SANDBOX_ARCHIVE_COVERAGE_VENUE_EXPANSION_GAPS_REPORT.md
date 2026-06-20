# Stage R106 Sandbox Archive Coverage Venue Expansion Gaps Report

Date: 2026-06-19
Packet: `docs/work_packets/WPR106-354-sandbox-archive-coverage-venue-expansion-gaps.md`
Status: closed

## Summary

WPR106-354 adds
`archive_coverage_venue_expansion_gaps.parquet` to sandbox archive coverage
output. The sidecar compares OKX, Bybit, and Hyperliquid readiness for each
observed market-symbol/data-family/interval group and labels each target venue
as ready, mixed, blocked, or missing.

The rows also include descriptor-only target actions:

- `use_ready_archive_bucket`
- `repair_blocked_descriptors_or_use_ready_bucket`
- `repair_blocked_archive_bucket`
- `add_archive_descriptor_for_target_venue`

The market grouping uses a compact symbol key so Hyperliquid-style `BTC`
coverage can be compared with OKX/Bybit-style `BTCUSDT` coverage during
venue-expansion triage.

## Boundary

The packet adds archive coverage diagnostics only. It does not change archive
descriptor loading, market-frame normalization, source-integrity checks,
coverage bucket status semantics, preflight behavior, replay readiness, trial
IDs, ranking/scoring, evidence-request selection, candidate-pack state, or
promotion state.

No sandbox sweep, iteration replay command, strict validation, provider
download, candidate-pack write, paper/live signal generation, sizing, order
placement, runtime-mode change, live configuration write, strategy-catalog
mutation, archive manifest/source mutation, or promotion claim was made.

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
