# WPR106-476 - V2 Universe Data-Source Manifest Bridge

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-004`
- `V2-AUD-UNIV-006`

## Objective

Connect the existing Hyperliquid universe snapshot rows to the new data-source
registry and symbol-map layer required by
`docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md` `DATA-003`. The packet
adds deterministic local manifest envelopes for strict-free source registry
snapshots and per-universe symbol-map snapshots under the archive `manifests`
tree.

This packet does not add venue/API fetches, historical data downloads,
backtests, accepted research evidence, candidate evidence, candidate packs,
paper/live behavior, order placement, sizing instructions, runtime-mode
mutation, or promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-476-v2-universe-data-source-manifest-bridge.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `configs/data_sources/samples/**`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_universe_data_source_manifest_bridge_phase39.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked legacy evidence under `data/research/fixtures/**`,
  `data/research/historical_cycles/**`, or existing WPR evidence directories.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_data_source_manifest_bridge_phase39.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse existing `UniverseSnapshotRow` output from the Hyperliquid universe
  manager; do not duplicate the collector.
- Require all bridge source entries to pass strict-zero-dollar checks and to be
  accepted under strict-free mode.
- Require at least one Hyperliquid-native universe metadata/snapshot source
  entry before writing the bridge manifests.
- Preserve below-threshold rows in symbol-map manifests as explicit
  non-eligible/exclusion evidence.
- Preserve Hyperliquid venue coin spelling through an optional
  `coin_by_instrument_id` mapping.
- Treat symbol candidates as unverified unless explicit probe evidence marks a
  venue mapping verified.

## Acceptance Criteria

- A source-registry snapshot JSON is written below
  `manifests/source_registry/` with deterministic ID/hash metadata.
- A symbol-map snapshot JSON is written below `manifests/symbol_maps/` with one
  row per supplied universe row.
- Non-strict-free, requester-pays, paid/keyed, or strict-free-unaccepted source
  entries fail before manifest writes.
- Ambiguous/manual-review symbol-map probe evidence is preserved as blocker
  evidence.
- The manifest bundle preserves research-only boundary flags.

## Changed Files

- `docs/work_packets/WPR106-476-v2-universe-data-source-manifest-bridge.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `configs/data_sources/samples/source_registry_hyperliquid_info_meta_asset_ctxs.json`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/manifest_bridge.py`
- `src/tradingbotsuite/v2/data_sources/schemas.py`
- `tests/v2/test_universe_data_source_manifest_bridge_phase39.py`

## Acceptance Evidence

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_universe_data_source_manifest_bridge_phase39.py -q
# 5 passed
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_data_source_registry_phase37.py tests\v2\test_symbol_map_resolver_phase38.py -q
# 17 passed
```

Baseline validation:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 352 passed
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF warnings only
```

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer path was changed.
- No legacy GUI path was changed.
- No checked legacy evidence under `data/research/fixtures/**` or
  `data/research/historical_cycles/**` was rewritten.
- The packet writes no generated market/research evidence during tests outside
  temporary pytest archives and performs no venue/API fetch.
- The packet creates no accepted research, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion claim.

## Follow-Up

- `DATA-004` should implement Binance Vision availability scanning against
  verified symbol-map rows and source-registry refs.
- Later historical backfill packets should consume the bridge outputs instead
  of ad hoc source or symbol assumptions.
