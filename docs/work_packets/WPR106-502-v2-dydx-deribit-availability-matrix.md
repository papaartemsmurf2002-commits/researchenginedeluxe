# WPR106-502 - V2 dYdX Deribit Availability Matrix

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-030`

## Objective

Continue `DATA-012` by adding a metadata-only dYdX/Deribit candle availability
matrix and extending deterministic symbol-map candidate coverage for Deribit
perpetual instruments.

This packet does not add collectors, download market data, write archive data
rows, create accepted historical coverage proof, normalize venue data, run
backtests, create candidate evidence, create candidate packs, add paper/live
behavior, place orders, emit sizing instructions, change runtime mode, or make
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-502-v2-dydx-deribit-availability-matrix.md`
- `src/tradingbotsuite/v2/data_sources/reference_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/symbol_resolver.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_reference_derivatives_availability_phase59.py`
- `tests/v2/test_symbol_map_resolver_phase38.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No archive raw/bronze/silver data writes in this packet.
- No real dYdX/Deribit network probes in tests.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_reference_derivatives_availability_phase59.py tests/v2/test_symbol_map_resolver_phase38.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add `deribit_perpetual` as a deterministic unverified candidate symbol,
  using Deribit `BASE-PERPETUAL` instrument names.
- Add source-scoped endpoint specs for dYdX indexer candles and Deribit
  public TradingView candle data.
- Require verified symbol-map rows before constructing requests.
- Write only metadata availability manifests under `manifests/source_availability/`.
- Preserve `native_to_hyperliquid=false`,
  `accepted_historical_coverage_proof=false`, and all canonical research-only
  boundary flags.

## Acceptance Criteria

- Deterministic request builders are stable for dYdX and Deribit candle probes.
- Availability manifests record available, missing, blocked-mapping, and
  probe-error status without writing archive market-data rows.
- Source entries must remain strict-free allowed external comparison sources
  and cannot be accepted historical coverage proof.
- Deribit candidate symbol generation is covered by symbol-map tests.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/reference_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/symbol_resolver.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_reference_derivatives_availability_phase59.py`
- `tests/v2/test_symbol_map_resolver_phase38.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_reference_derivatives_availability_phase59.py tests/v2/test_symbol_map_resolver_phase38.py -q
```

Result: 11 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 445 passed; `tests/contracts` 463 passed;
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds metadata-only dYdX/Deribit availability matrices and Deribit
symbol candidate coverage. It does not add collectors, run real network probes
in tests, download market data, write archive market-data rows, create accepted
historical coverage proof, create candidate evidence, create candidate packs,
add paper/live behavior, place orders, emit sizing instructions, change runtime
mode, or make promotion claims.
