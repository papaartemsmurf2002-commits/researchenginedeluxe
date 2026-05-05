# WPR49-01 Perp Context Manifest Foundation

Owner: Codex Research Agent
Status: closed
Stage: R49 perp context manifest foundation
Date opened: 2026-05-05
Date closed: 2026-05-05

## Goal

Extend current context-family validation and manifest metadata for perpetual research without changing historical-cycle behavior or adding new required data families.

## Allowed Paths

```text
src/tradingbotsuite/data/contracts.py
src/tradingbotsuite/data/historical_fixture_pack.py
src/tradingbotsuite/research/market_data.py
tests/contracts/
tests/tradingbotsuite/test_market_data_collection.py
docs/work_packets/
docs/stage_reports/
docs/ORCHESTRATOR_STAGE_LEDGER.md
docs/KNOWN_ISSUES.md
```

## Constraints

- Preserve existing context families: `funding_rate`, `premium_index`, `open_interest`, `agg_trade`.
- Preserve WPR47 Crypto Lake free-sample fallback semantics: no provider credentials, no AWS profile setup, and no paid-access assumptions.
- Keep `source_access_mode: free_sample` evidence as diagnostic fallback evidence only.
- Keep synthetic context disallowed for provider-backed candidate evidence.
- Do not require liquidation, L2, cross-exchange, multi-symbol cycle behavior, or live/promotion changes.
- Preserve research-only boundaries: `research_only`, `observe_only`, and `promotion_ready: false`.

## Required Behavior

- Add non-breaking manifest metadata where appropriate:
  - `retention_policy`
  - `coverage_scope`
  - `latest_window_only`
  - `context_family_role`
  - `stream_health` for future stream families
- Ensure direct latest-window context cannot support multi-year claims.
- Ensure normalized manifests remain truthful about gaps, duplicates, row counts, coverage, source access mode, and diagnostic status.
- Keep current cycle specs, fixtures, and existing tests compatible.

## Validation Plan

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_historical_fixture_pack_contract.py tests\contracts\test_data_contracts.py tests\tradingbotsuite\test_market_data_collection.py -q
```

## Close Evidence

Closed in `docs/stage_reports/STAGE_R49_PERP_CONTEXT_MANIFEST_FOUNDATION_REPORT.md`.

Validation:

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_data_contracts.py tests\contracts\test_historical_fixture_pack_contract.py tests\tradingbotsuite\test_market_data_collection.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\integration\test_provider_intake_smoke.py tests\contracts\test_import_boundaries.py -q
git diff --check
```

Results: compile passed; focused WPR49 tests passed with 60 tests; full contract suite passed with 103 tests; provider intake/import-boundary smoke passed with 7 tests; `git diff --check` returned 0 with existing LF-to-CRLF working-copy warnings only.
