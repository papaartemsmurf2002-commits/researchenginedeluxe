# WPR106-474 - V2 Data Source Registry Foundation

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-001`
- `V2-AUD-DATASRC-002`
- `V2-AUD-QUAL-007`

## Objective

Implement the first local foundation slice from
`docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`: source registry
cost-class schemas, symbol-map schemas, and data-family coverage report
schemas. This packet turns the remote roadmap's strict-free and provenance
contracts into validated local artifacts before larger collectors/backfills are
expanded.

This packet is research-only infrastructure. It does not collect venue data,
create accepted research evidence, create candidate evidence, write candidate
packs, add paper/live behavior, place orders, emit sizing instructions, mutate
runtime mode, or create promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-474-v2-data-source-registry-foundation.md`
- `docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `configs/data_sources/**`
- `src/tradingbotsuite/v2/config/schemas.py`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_data_source_registry_phase37.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_source_registry_phase37.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Source registry entries must distinguish `zero_cost_public`,
  `public_rate_limited`, `free_sample_only`,
  `public_requester_pays_transfer`, and `paid_or_keyed`.
- Strict-zero-dollar mode must reject paid/keyed sources and requester-pays
  sources unless an explicit later operator packet scopes them.
- Quarantined Hyperliquid official requester-pays sources must not be marked
  strict-zero-dollar allowed or accepted under strict-free.
- Symbol-map rows must represent missing, ambiguous, delisted, not-checked,
  and manual-review states as first-class states rather than failures hidden by
  omission.
- Data-family coverage reports must carry the full v2 research-only invariant
  and must not treat forward captures, recent snapshots, external proxies, or
  free samples as accepted historical Hyperliquid-native coverage by omission.

## Acceptance Criteria

- JSON schemas exist for source registry entries, symbol-map rows, and
  data-family coverage reports.
- Pydantic models validate the same constraints as the JSON schemas.
- Sample fixtures validate successfully.
- Invalid paid/keyed, requester-pays, ambiguous mapping, and mislabeled
  coverage examples fail closed in focused tests.
- The packet preserves the v2 research-only boundary and touches only allowed
  paths.

## Changed Files

- `docs/work_packets/WPR106-474-v2-data-source-registry-foundation.md`
- `docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `configs/data_sources/v2_source_registry.schema.json`
- `configs/data_sources/v2_symbol_map.schema.json`
- `configs/data_sources/v2_data_family_coverage.schema.json`
- `configs/data_sources/samples/source_registry_binance_vision_usdm_trades.json`
- `configs/data_sources/samples/source_registry_hyperliquid_official_fills_quarantined.json`
- `configs/data_sources/samples/symbol_map_sol_2026_06_22.json`
- `configs/data_sources/samples/data_family_coverage_hl_btc_trades_forward_segment.json`
- `src/tradingbotsuite/v2/config/schemas.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/schemas.py`
- `tests/v2/test_data_source_registry_phase37.py`

## Acceptance Evidence

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_data_source_registry_phase37.py -q
# 10 passed
```

Compile validation:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed
```

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer path was changed.
- No legacy GUI path was changed.
- No checked legacy evidence under `data/research/fixtures/**` or
  `data/research/historical_cycles/**` was rewritten.
- The packet writes no generated market/research evidence and performs no
  venue/API fetch.
- The packet creates no accepted research, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion claim.

## Follow-Up

- `DATA-002` still needs the resolver implementation that probes venue metadata
  and writes symbol-map snapshots for the liquid Hyperliquid universe.
- `DATA-003` still needs the roadmap-specific daily Hyperliquid as-of universe
  snapshot collector tied to this source registry.
- `DATA-004` and later packets should consume `SourceRegistryEntry` and
  `VenueSymbolMapRow` before running availability scans or downloads.
