# WPR106-565 - V2 OF Materialization And Venue Probe Scaling

Status: self_checked
Owner: Codex Research Agent
Date opened: 2026-06-29

## Scope

Finish the deferred PR #5 follow-up scale work left after WPR106-564 by adding
bounded, research-only scale primitives for OF-style feature materialization
and venue probe pagination.

This packet must not collect new venue data, rewrite generated evidence, alter
PR #5 backtest math, change trade-frequency policy, or change losing-month
policy.

## Allowed paths

- `docs/work_packets/WPR106-565-v2-of-materialization-and-venue-probe-scaling.md`
- `src/tradingbotsuite/v2/data_sources/of_style_materialization.py`
- `src/tradingbotsuite/v2/data_sources/bybit_okx.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `tests/v2/test_of_style_materialization_phase78.py`
- `tests/v2/test_bybit_okx_fetch_normalize_phase56.py`

## No-touch review

- Do not touch live/runtime, order-placement, sizing, promotion,
  candidate-pack truth, secret, local-state, or generated historical evidence
  paths.
- Do not run real venue fetches in tests.
- Do not rewrite WPR106-549, WPR106-552, WPR106-556, ledger, Lead Book, or
  accepted-research generated outputs.
- Do not change the vectorized/Python backtest reference math, trade-frequency
  policy, losing-month policy, capacity policy, causality policy, or cost
  fallback semantics.

## Implementation plan

1. Add optional part/chunked OF-style materialization output while preserving
   existing JSONL defaults and report contracts.
2. Keep chunk identity stable through raw SHA, source metadata, feature-family,
   row hashes, output refs, and research-only boundary flags.
3. Add bounded Bybit/OKX page request planning for endpoints that support date
   windows, and add a multi-page fetch helper that accepts injected probes for
   fixture-only validation.
4. Export the new scale helpers from the data-source package.
5. Add focused tests covering chunk output, unchanged JSONL compatibility, page
   request URLs, page caps, and multi-page normalization without network calls.

## Validation target

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_of_style_materialization_phase78.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_bybit_okx_fetch_normalize_phase56.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
git diff --check
```

Broaden to full `tests\v2 -q` if exported data-source behavior changes more
widely than this packet expects.

## Completion notes

Implemented and self-checked:

- Added optional `parquet_parts` OF-style materialization output. Existing
  JSONL output remains the default and keeps its existing filename shape.
- Parquet part output writes `*.parts/index.json`, per-part Parquet files,
  per-file `.sha256` sidecars, part refs, part manifest hashes, row manifest
  hashes, source metadata, and research-only boundary flags.
- Added compatibility hashing so default JSONL source-result hashes do not
  change only because optional part fields have defaults.
- Added `BybitOkxPaginatedRequestPlan`,
  `build_bybit_okx_paginated_request_plan()`, and
  `fetch_bybit_okx_public_market_pages()` for bounded date-window page
  planning and injected-probe multi-page fetch normalization.
- Bounded page plans block recent/snapshot endpoints before probing and mark
  page-cap truncation explicitly.
- Exported the new Bybit/OKX scale helpers from
  `tradingbotsuite.v2.data_sources`.

Validation completed:

```powershell
py -3.11 -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_of_style_materialization_phase78.py tests\v2\test_bybit_okx_fetch_normalize_phase56.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2\test_bybit_okx_availability_phase55.py tests\v2\test_alt_derivatives_availability_phase57.py tests\v2\test_alt_derivatives_fetch_normalize_phase58.py -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\contracts -q
$env:PYTHONPATH='src'; py -3.11 -m pytest tests\v2 -q
```

Results: compileall passed; focused changed tests passed with `10` tests;
related venue tests passed with `13` tests; contracts passed with `463` tests;
full v2 passed with `602` tests. Pytest emitted the existing
`StarletteDeprecationWarning`.
