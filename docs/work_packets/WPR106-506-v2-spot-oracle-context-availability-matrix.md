# WPR106-506 - V2 Spot Oracle Context Availability Matrix

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-034`

## Objective

Continue `DATA-013` by adding a research-only availability matrix for strict
free/public spot, oracle, and on-chain context sources. The matrix builds
deterministic request URLs, requires verified symbol-map entries before probes,
records available/missing/probe-error/blocked-mapping rows, and writes a
manifest under source availability provenance.

This packet does not add collectors, run live data collection, download market
data into archive rows, create accepted historical coverage proof, normalize
venue payloads, run backtests, create candidate evidence, create candidate
packs, add paper/live behavior, place orders, emit sizing instructions, change
runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-506-v2-spot-oracle-context-availability-matrix.md`
- `src/tradingbotsuite/v2/data_sources/spot_oracle_context.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_spot_oracle_context_availability_phase61.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No archive data downloads, generated market-data rows, or accepted
  historical coverage proof.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_spot_oracle_context_availability_phase61.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add endpoint specs for Coinbase spot candles, Kraken spot OHLC, Pyth Hermes
  latest prices, DefiLlama current prices, DexScreener search, and
  GeckoTerminal pool search.
- Keep requests deterministic and bounded to one day where a source supports
  historical windows.
- Require strict-zero-dollar source entries and verified external mappings
  before probes.
- Treat spot sources as `external_comparison` and oracle/context sources as
  `spot_or_oracle_context`.

## Acceptance Criteria

- Request-builder tests pin expected URLs for all six sources.
- Availability manifest tests prove available rows, mapping blocks without
  probes, and rejection of historical coverage-source claims.
- Manifest rows remain research-only, observe-only, non-native to Hyperliquid,
  and not promotion/candidate/paper/live/sizing/order/runtime evidence.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/spot_oracle_context.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_spot_oracle_context_availability_phase61.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_spot_oracle_context_availability_phase61.py -q
```

Result: 4 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 455 passed; `tests/contracts` 463 passed.
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds metadata-only DATA-013 context availability request and
manifest scaffolding. It does not add collectors, downloads, archive
market-data rows, normalized venue payloads, accepted historical coverage
proof, candidate evidence, candidate packs, paper/live behavior, order
placement, sizing instructions, runtime-mode changes, or promotion claims.
