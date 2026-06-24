# WPR106-475 - V2 Symbol Map Resolver Scaffold

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-003`
- `V2-AUD-XVENUE-014`

## Objective

Implement the `DATA-002` resolver scaffold from
`docs/roadmaps/V2_HYPERLIQUID_DATA_VENUE_ROADMAP.md`. The resolver converts
Hyperliquid coins into deterministic per-venue candidate symbols, consumes
explicit availability/probe results, and emits `VenueSymbolMapRow` records with
verified, missing, ambiguous, delisted, not-checked, and manual-review states.

This packet does not make network calls, download data, run backtests, create
accepted research evidence, create candidate evidence, write candidate packs,
add paper/live behavior, place orders, emit sizing instructions, mutate runtime
mode, or create promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-475-v2-symbol-map-resolver-scaffold.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `configs/data_sources/samples/**`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_symbol_map_resolver_phase38.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_symbol_map_resolver_phase38.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Preserve Hyperliquid coin spelling exactly in the native mapping.
- Generate deterministic candidates for Binance, Bybit, OKX, Bitget, MEXC,
  Gate, KuCoin, HTX, dYdX, Coinbase, Kraken, Pyth, DexScreener, and
  GeckoTerminal without implying they are verified.
- Treat availability/probe inputs as authoritative for this packet.
- A venue with no probe result must remain `not_checked`.
- A venue with ambiguous or manual-review probe evidence must become blocker
  evidence before any external backfill can run.
- Spot/oracle/context mappings must remain market-type separated from
  perpetual mappings.

## Acceptance Criteria

- Resolver emits one `VenueSymbolMapRow` per Hyperliquid coin.
- Verified mappings require explicit availability evidence.
- Missing, ambiguous, delisted, not-checked, and manual-review states are
  represented explicitly.
- `kPEPE`-style Hyperliquid coins can map to `1000PEPEUSDT`-style Binance
  perpetual candidates when verified by availability evidence.
- The resolver preserves research-only boundaries by producing mapping
  metadata only.

## Changed Files

- `docs/work_packets/WPR106-475-v2-symbol-map-resolver-scaffold.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `configs/data_sources/samples/symbol_map_kpepe_resolved_2026_06_22.json`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/symbol_resolver.py`
- `tests/v2/test_symbol_map_resolver_phase38.py`

## Acceptance Evidence

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_symbol_map_resolver_phase38.py -q
# 7 passed
```

Baseline validation:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 347 passed
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed
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

- `DATA-003` should tie daily Hyperliquid as-of universe snapshots to this
  resolver and write symbol-map manifests under the archive root.
- `DATA-004` should feed real Binance Vision path-probe availability into
  `SymbolProbeResult` rows before any backfill.
- Later external venue packets should add venue-specific probe collectors while
  keeping candidate generation separate from verification.
