# Stage R27 Fixture-Family Context Materialization Report

Date: 2026-05-04

## Scope

WPR27 implemented fixture-pack-only materialization for optional research context families:

- `funding_rate`
- `premium_index`
- `open_interest`
- `agg_trade`

The work remains research-only, observe-only, and not promotion-ready. It does not touch live, paper, shadow, testnet, canary, order-placement, capital allocation, provider downloading, or strategy alpha logic.

## Changes

- `src/tradingbotsuite/data/historical_fixture_pack.py`
  - Validates present context families with `symbol`, an event-time field, hash, and row-count evidence.
  - Exposes context-family provenance in `HistoricalFixturePackValidation.to_payload()`.

- `src/tradingbotsuite/features/builders.py`
  - Adds `materialize_fixture_family_context()` with backward as-of joins by symbol and event time.
  - Maps known family fields into existing research feature inputs such as `funding_rate`, `funding_rate_change`, `premium_basis_rate`, `basis_bps`, `open_interest_change_pct`, `primary_signed_imbalance_ratio`, `top_of_book_imbalance`, and `spread_bps`.
  - Rejects ambiguous duplicate family events for the same `symbol,event_time`.
  - Records per-family join evidence, null rates, joined columns, and a deterministic context hash.

- `src/tradingbotsuite/features/cache.py`
  - Adds `fixture_family_context_sha256` to feature cache identity.
  - Writes full fixture-family context evidence into feature cache manifests.

- `src/tradingbotsuite/research_cycle/runner.py`
  - Materializes fixture-family context immediately after fixture-pack validation and before dataset hashing.
  - Carries context provenance into data-source, data-quality, feature-build, and feature-cache manifests.

- Tests cover validation payloads, fail-closed malformed families, no-lookahead as-of behavior, duplicate family rejection, cycle-level materialization, cache-manifest evidence, and cache-key invalidation when family content changes.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\features\test_feature_builders.py tests\contracts\test_historical_fixture_pack_contract.py -q` passed: 15 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_local_fixture_pack.py -q` passed: 5 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_preflight.py -q` passed: 24 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 76 tests.
- `git diff --check` completed with line-ending warnings only.

## Result

WPR27 is complete. Fixture-backed historical research cycles can now consume validated optional context families without requiring those fields to be prejoined in the cycle dataset. The joins are point-in-time bounded, provenance is explicit, and feature cache identity changes when optional family content changes.
