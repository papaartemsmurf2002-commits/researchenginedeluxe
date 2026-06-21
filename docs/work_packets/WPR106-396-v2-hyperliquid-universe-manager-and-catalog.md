# WPR106-396 V2 Hyperliquid Universe Manager And Catalog

Status: closed
Owner: Codex Research Agent
Created: 2026-06-20

## Objective

Implement Phase 5 of `docs/V2_READY_TO_USE_IMPLEMENTATION_ROADMAP.md`: create
the v2 Hyperliquid universe manager and instrument catalog with the USD 5M
daily notional rule, raw-before-parse payload archiving, as-of/current universe
modes, below-threshold exclusion records, and HIP-3/RWA metadata blocking.

This packet implements fixture-backed universe refresh/list/explain/diff
infrastructure and a research-safe Hyperliquid info client. It does not start
continuous collectors, run provider backfills, implement data quality coverage,
run strategy/backtest workflows, append ledgers, create Lead Book storage,
create paper/live behavior, place orders, change runtime mode, touch sizing, or
write candidate packs.

## Audit IDs

- `V2-AUD-UNIV-001`
- `V2-AUD-HIP3-001`

## Dependencies

- `docs/contracts/universe_contract.md`
- `docs/contracts/archive_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `src/tradingbotsuite/v2/archive/**`
- `src/tradingbotsuite/v2/universe/models.py`
- `src/tradingbotsuite/v2/cli/main.py`

## Allowed Paths

- `docs/contracts/universe_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `src/tradingbotsuite/v2/universe/**`
- `src/tradingbotsuite/v2/venues/hyperliquid/**`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/**`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/work_packets/WPR106-396-v2-hyperliquid-universe-manager-and-catalog.md`
- `docs/KNOWN_ISSUES.md` only if a blocking issue is discovered

## Boundary Constraints

- Preserve research-only, observe-only, non-promotable semantics.
- Do not create or modify candidate packs.
- Do not create paper/live artifacts.
- Do not place orders, change runtime mode, write live configuration, or add
  sizing/order-placement behavior.
- Tests must use fixtures and must not require network.
- Raw `metaAndAssetCtxs` payloads must be archived before parsing.
- Current-universe snapshots must be labeled sandbox-only and cannot support
  accepted evidence.

## Acceptance Criteria

- `python -m tradingbotsuite.v2.cli.main universe refresh --venue hyperliquid
  --min-day-notional-usd 5000000 --payload-file <fixture> --archive-root <dir>`
  creates raw payload, instrument catalog, and universe snapshot rows.
- Non-BTC/ETH symbols can pass eligibility in fixtures.
- Below-threshold instruments are archived but excluded.
- HIP-3/RWA prefixed symbols are represented with namespace metadata.
- Missing HIP-3/RWA metadata blocks accepted evidence.
- As-of selection does not use future volume snapshots.
- Current-universe mode is sandbox-only.

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

No broad non-v2 tests are required unless shared implementation files outside
the v2 shell are changed.

## Stop Conditions

- A no-touch live/runtime/order/sizing path must be modified.
- A real collector, backtest runner, ledger append workflow, Lead Book store,
  candidate-pack, paper/live, order, sizing, runtime, or promotion behavior
  becomes necessary.

## Completion Notes

Closed on 2026-06-20.

- Added `HyperliquidInfoClient`, a small unsigned public-info client for the
  `metaAndAssetCtxs` payload. It has no signing, account, order, leverage,
  margin, sizing, or runtime behavior.
- Added Hyperliquid universe parsing for `metaAndAssetCtxs` payloads.
- Added `InstrumentCatalogRow`, `AssetContextSnapshotRow`,
  `UniverseSnapshotRow`, and `UniverseRefreshResult` schema models.
- Added USD 5M daily notional eligibility rules, status checks, coverage/history
  placeholders, current-universe sandbox labeling, and HIP-3/RWA metadata
  completeness blockers.
- Added raw-before-parse archiving through the Phase 4 raw writer.
- Added Parquet-backed instrument catalog, asset context snapshots, and universe
  snapshots under the archive `manifests/` directory.
- Added as-of universe selection that chooses the latest snapshot at or before
  the requested date, avoiding future volume snapshots.
- Added universe diff and instrument explain helpers.
- Added v2 CLI commands:
  - `universe refresh`
  - `universe list`
  - `universe explain`
  - `universe diff`
- Added fixture-backed Phase 5 tests proving:
  - non-BTC/ETH symbols can pass the USD 5M rule;
  - below-threshold instruments are archived but excluded;
  - HIP-3 prefixed symbols are represented with namespace metadata;
  - missing HIP-3/RWA metadata blocks accepted evidence;
  - as-of selection does not use future volume snapshots;
  - current-universe mode is sandbox-only;
  - CLI refresh/list/explain paths work from local fixtures.
- Marked `V2-AUD-UNIV-001` and `V2-AUD-HIP3-001` as `self_checked`.
- No continuous collectors, backtests, strategy evaluation, ledger append
  workflow, Lead Book storage, paper/live behavior, order placement, sizing,
  runtime-mode changes, candidate-pack writing, or promotion behavior was
  implemented.

Validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
python -m compileall -q src\tradingbotsuite\v2
git diff --check
```

Result:

- Focused v2 tests passed: 36 passed.
- `compileall` for `src\tradingbotsuite\v2` passed.
- `git diff --check` passed with LF-to-CRLF warnings only for existing
  text-file line-ending behavior.
