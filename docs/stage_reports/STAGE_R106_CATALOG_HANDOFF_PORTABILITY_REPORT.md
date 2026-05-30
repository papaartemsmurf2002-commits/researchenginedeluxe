# Stage R106 Catalog Handoff Portability Report

Date: 2026-05-27
Packet: `WPR106-22-catalog-handoff-portability`
Status: closed

## Summary

Resolved the actionable P1 catalog handoff blocker from WPR106-21. The migrated
`main` checkout can now reuse the active R106 historical-data catalog and active
cycle/discovery specs even when those generated artifacts still contain absolute
paths from the old checkout.

No generated fixture pack, generated catalog artifact, source active spec,
cycle output, discovery ledger, live runtime configuration, order-placement
surface, sizing behavior, candidate pack, or promotion readiness was changed.

## Changes

- `read_historical_data_catalog()` now rebases stale absolute operator-run path
  fields to the current mirrored catalog run directory when the mirrored target
  or parent exists locally.
- Operator catalog diagnostics and artifact indexing consume the normalized
  catalog payload.
- Operator isolated historical-cycle and discovery jobs normalize embedded
  source spec paths before writing per-job isolated specs, so dataset manifests
  and readiness paths no longer point at
  `C:\Users\papaa\Music\tradingbotsuite`.
- Regression tests cover migrated catalog reads, default active-catalog spec
  routing, and isolated cycle/discovery spec payload normalization.

## Issue Status

- `ISSUE-R106-003`: resolved by WPR106-22.
- `ISSUE-R104-001`: remains open. This packet did not and cannot truthfully
  produce the missing empirical ETH brute-force cycle, ETH exact discovery,
  current-output analysis/delta/exit-lab/eligibility review, or candidate gate
  evidence.

The migrated pre-profile catalog still truthfully has no local
`modern_window_profile.json` artifacts. That is not treated as a candidate-ready
claim or promotion evidence; refreshed catalogs continue to write/index modern
profiles when produced, and nested profile path fields are covered by the same
read-time rebase.

## Validation

Passed:

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_market_data_collection.py -q`
  - `31 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_operator_ui.py -q`
  - `75 passed`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `427 passed`

Targeted real-catalog check:

- Active catalog paths for BTCUSDT and ETHUSDT resolve under
  `C:\Users\papaa\Music\researchenginedeluxe`.
- Rebased active cycle specs reference existing mirrored fixture manifests for
  both symbols.

## Next Work

Continue empirical R106 work:

- ETH brute-force cycle.
- ETH exact discovery.
- Current-output analysis and delta review.
- Frozen-entry exit lab and candidate eligibility review across current exact
  outputs.
- Candidate-ready gate evidence before any promotion or trading claim.
