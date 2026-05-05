# Stage R49 Perp Context Manifest Foundation Report

Date: 2026-05-05
Branch: `research/v3-experimental-engine`
Work packet: `docs/work_packets/WPR49-01-perp-context-manifest-foundation.md`
Status: closed

## Scope

R49 added non-breaking perpetual context metadata and quality checks for research data manifests and fixture-pack context families. It did not add required liquidation, L2, cross-exchange, multi-symbol cycle behavior, live execution, promotion acceptance, or provider credentials.

## Changes

- Added optional context metadata fields for provider/archive manifests:
  - `retention_policy`
  - `coverage_scope`
  - `latest_window_only`
  - `context_family_role`
  - `stream_health`
- Marked Binance USD-M REST context as `latest_window_backfill` and `latest_window_only: true` so direct endpoint rows cannot imply multi-year coverage.
- Marked Crypto Lake free-sample rows as `free_sample_diagnostic`, preserving `source_access_mode: free_sample` and diagnostic-only behavior.
- Added fixed-interval context gap metadata and variable-cadence gap non-applicability metadata for archive/fallback manifests.
- Changed Crypto Lake funding/open-interest context duplicate checks to use `(symbol, event_time_ms)` instead of trade IDs.
- Preserved WPR47 free-sample semantics: no paid access, provider-account setup, AWS profile setup, or secret material.
- Propagated context metadata into generated fixture-pack family entries and `source.context_sources`.
- Hardened data manifest contracts so `extra` cannot override reserved boundary fields and `promotion_ready` remains false for research manifests.

## Validation

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_data_contracts.py tests\contracts\test_historical_fixture_pack_contract.py tests\tradingbotsuite\test_market_data_collection.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\integration\test_provider_intake_smoke.py tests\contracts\test_import_boundaries.py -q
git diff --check
```

Results:

- Compile passed.
- Focused WPR49 tests: 60 passed.
- Full contract suite: 103 passed.
- Provider intake/import-boundary smoke: 7 passed.
- `git diff --check` returned 0. Git reported existing LF-to-CRLF working-copy warnings only.

## Research Boundary

All new behavior remains `research_only`, `observe_only`, and `promotion_ready: false`. The work adds evidence-truthfulness metadata only; it does not create live signals, paper/shadow/testnet/canary execution, promotion readiness, capital allocation, or order placement.
