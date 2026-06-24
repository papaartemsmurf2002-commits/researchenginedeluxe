# WPR106-501 - V2 dYdX Deribit Source Registry Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-029`

## Objective

Start `DATA-012` by adding source-registry entries for dYdX indexer public
market data and Deribit public derivatives market data before any external
reference/context collector or probe is added.

This packet does not add collectors, run API probes, download market data,
write archive rows, create availability matrices, normalize venue data, run
backtests, create accepted historical coverage proof, create candidate
evidence, create candidate packs, add paper/live behavior, place orders, emit
sizing instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-501-v2-dydx-deribit-source-registry-foundation.md`
- `configs/data_sources/samples/source_registry_dydx_indexer_public.json`
- `configs/data_sources/samples/source_registry_deribit_public.json`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_data_source_registry_phase37.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No dYdX/Deribit network probes or generated external market-data evidence.
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

- Add strict-free-allowed `public_rate_limited` source samples for
  `dydx_indexer_public` and `deribit_public`.
- Keep both `native_to_hyperliquid=false`, external/reference comparison
  labeled, and `accepted_historical_coverage_proof=false`.
- Record overlap, symbol-map, endpoint-limit, pagination, availability-matrix,
  raw request/response, and context-only caveats for later collectors.

## Acceptance Criteria

- The two source entries validate as `SourceRegistryEntry` objects and pass
  `require_strict_zero_dollar_source()`.
- Tests prove they remain external comparison/context sources and cannot be
  used as Hyperliquid-native or accepted historical coverage proof.

## Changed Files

- `configs/data_sources/samples/source_registry_dydx_indexer_public.json`
- `configs/data_sources/samples/source_registry_deribit_public.json`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_data_source_registry_phase37.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_source_registry_phase37.py -q
```

Result: 16 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 441 passed; `tests/contracts` 463 passed;
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds registry foundation only. It does not add dYdX or Deribit
collectors, API probes, downloads, generated market-data evidence, archive
writes, availability matrices, accepted historical coverage proof, candidate
evidence, candidate packs, paper/live behavior, order placement, sizing
instructions, runtime-mode changes, or promotion claims.
