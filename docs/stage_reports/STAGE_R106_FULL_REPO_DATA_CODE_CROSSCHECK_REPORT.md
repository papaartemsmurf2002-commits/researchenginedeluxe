# Stage R106 Full Repo Data Code Crosscheck Report

Date: 2026-05-27
Work packet: `docs/work_packets/WPR106-21-full-repo-data-code-crosscheck.md`

## Summary

WPR106-21 ran a docs-only full repo data/code crosscheck on current `main`,
treating it as the migrated R106 branch. The audit did not change source code,
configs, fixture packs, generated research artifacts, live runtime behavior, or
candidate-pack outputs.

The R106 BTCUSDT and ETHUSDT candidate-depth data is present in the current
checkout mirror and validates as research-only durable public-archive evidence.
No new live-boundary, order-placement, runtime-mode, sizing, or unsafe
promotion-readiness regression was found. One new P1 handoff issue was
registered: `ISSUE-R106-003`, because the active catalog payload still points
at the old `C:\Users\papaa\Music\tradingbotsuite` checkout and the local
operator data tree lacks the modern-window profile artifacts described by later
R106 workflow docs.

## Governance And Data

- Repo state before audit: `## main...origin/main`; no unrelated tracked local
  edits were present before this packet.
- Branch mismatch is documented, not treated as a blocker: current checkout is
  `main`, while older stage docs still name `research/v3-experimental-engine`.
- Known issue state after this packet: no open P0 issues, two open P1 issues
  (`ISSUE-R104-001`, `ISSUE-R106-003`).
- Active catalog audited:
  `data/research/operator_runs/historical_data/refresh-historical-data-catalog-4dfa2700192f4b6fa1fa8fe833668cfb/historical_data_catalog.json`.
- Catalog boundary flags are correct:
  `research_only: true`, `observe_only: true`, `promotion_ready: false`,
  `live_signal_input: false`, `live_execution_input: false`,
  `operator_control_input: false`, `position_sizing_input: false`.

R106 candidate-depth data in the current checkout mirror:

| Symbol | Status | 15m bars | 1m bars | aggTrade proxy rows | Downloads/checksums | Fixture/readiness |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| BTCUSDT | `candidate_depth_ready` | 221,952 | 3,329,280 | 3,291,128 | 228/228 | valid, durable-public-archive ready |
| ETHUSDT | `candidate_depth_ready` | 221,952 | 3,329,280 | 3,317,494 | 228/228 | valid, durable-public-archive ready |

Data-quality checks from manifests:

- Required families are present for both symbols: `bars:15m`,
  `lower_timeframe_bars:1m`, and `agg_trade` trade-flow proxy.
- `bars` and `lower_timeframe_bars` report `gap_count: 0` and
  `duplicate_count: 0` for both symbols.
- `agg_trade` reports `duplicate_count: 0` for both symbols and preserves
  checksum-backed archive evidence.
- Fixture manifest SHA-256 values match the catalog payload for both symbols.
- `validate_historical_fixture_pack_manifest()` and
  `validate_public_archive_fixture_readiness()` pass for both current-checkout
  fixture manifests.

Provider surface classification:

| Provider | Classification | Candidate-depth status |
| --- | --- | --- |
| Binance Vision | active implemented primary public archive source | active for BTCUSDT/ETHUSDT candidate-depth evidence |
| Binance REST | implemented secondary diagnostic/backfill source | not active catalog source |
| Crypto Lake | implemented local/vendor export source, not auto-collected | inactive until export/cache manifests are supplied and validated |
| Bybit archive | registered public archive expansion source | ingestion/parser/gap/hash validation not implemented |
| Hyperliquid archive | registered requester-pays expansion source | requester-pays access, LZ4 parser, and account-journal reconciliation not implemented |

## Findings

`ISSUE-R106-003` was opened as P1. The current checkout contains valid mirrored
BTC/ETH candidate-depth data, but the active catalog's absolute path fields
still point outside this repo to `C:\Users\papaa\Music\tradingbotsuite`.
Because operator routes and job defaults consume active catalog paths, this can
misdirect or block the next migrated-checkout empirical sequence. The same audit
found no `modern_window_profile.json` files under `data/research/operator_runs`,
despite WPR106-16 docs describing modern-window profile artifacts/spec links.

No new P0 issue was found. No evidence was found that research modules place
orders, change live runtime mode, write live configuration, write sizing state,
or mark research artifacts as promotion-ready.

Static review notes:

- Boundary scans found no `place_order`, `cancel_order`, `set_runtime_mode`, or
  unsafe `promotion_ready: true` hits in research-owned packages/configs.
- Research/data code still imports Binance market-data adapter helpers in
  expected data collection paths; no order-placement adapter import was found.
- Recursive artifact scans remain present in bounded artifact indexing,
  telemetry fallback, and benchmark reporting paths. WPR106-20 reduced the
  highest-risk discovery finalization scan by using observed artifact counters,
  so this remains known performance debt rather than a new blocker.
- Oversized orchestration modules remain: `operator_console.py`,
  `research_cycle/runner.py`, `research_discovery/runner.py`, and
  `data/durable_public_archive.py`. They should be refactored only in a scoped
  maintainability packet after the catalog handoff and empirical gates are not
  blocked.

## Remaining Gates

Before any candidate-ready claim exists:

- Resolve `ISSUE-R106-003` so the migrated checkout has current-root-safe active
  catalog paths and modern-window profile artifacts/spec links when required.
- Complete ETH candidate-depth historical cycle and ETH exact discovery from
  active generated specs.
- Run current-output analysis, run-to-run delta, frozen-entry exit-lab, and
  candidate eligibility review across current exact outputs.
- Keep `ISSUE-R104-001` open until candidate-depth catalog evidence, deep
  cycles, exact sweeps, and eligibility review all pass.
- Preserve `research_only`, `observe_only`, and `promotion_ready: false`
  throughout the empirical workflow.

## Validation

- `python -m compileall -q src\tradingbotsuite`
  Result: passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  Result: passed, `427 passed in 5.18s`.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q`
  Result: passed, `210 passed in 85.36s`.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical -q`
  Result: passed, `42 passed in 204.07s`.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts tests\live -q`
  Result: passed, `92 passed in 2.92s`.

## Boundary

This packet was audit/report only. It did not edit production code, configs,
fixtures, generated data, live runtime mode, order placement, sizing behavior,
candidate-pack outputs, or promotion readiness.
