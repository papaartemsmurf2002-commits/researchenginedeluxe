# WPR106-495 - V2 Bybit OKX Source Registry Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-023`

## Objective

Start `DATA-010` by adding source-registry entries for Bybit and OKX public
derivatives market data before any external gap-filler collector is added.
Entries must be public-rate-limited, external to Hyperliquid, strict-free
allowed, and explicitly non-native/non-accepted historical coverage proof.

This packet does not add Bybit or OKX collectors, run API probes, download
market data, write archive rows, create availability matrices, run backtests,
create accepted historical coverage proof, create candidate evidence, create
candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-495-v2-bybit-okx-source-registry-foundation.md`
- `configs/data_sources/samples/source_registry_bybit_public_market.json`
- `configs/data_sources/samples/source_registry_okx_public_market.json`
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
- No Bybit/OKX network probes or generated external market-data evidence.
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

- Add `bybit_public_market` and `okx_public_market` source samples.
- Keep both `public_rate_limited`, `native_to_hyperliquid=false`,
  `research_role=external_comparison`, and
  `accepted_historical_coverage_proof=false`.
- Record endpoint-limit caveats so future collectors must add availability
  matrices and endpoint-specific pagination before backfill.

## Acceptance Criteria

- Bybit and OKX source entries validate as `SourceRegistryEntry` objects and
  pass `require_strict_zero_dollar_source()`.
- Tests prove both remain external comparison/proxy sources and cannot be used
  as Hyperliquid-native or accepted historical coverage proof.

## Changed Files

- `configs/data_sources/samples/source_registry_bybit_public_market.json`
- `configs/data_sources/samples/source_registry_okx_public_market.json`
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

Result: 14 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 421 passed; `tests/contracts` 463 passed;
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds registry foundation only. It does not add Bybit/OKX
collectors, API probes, downloads, generated market-data evidence, archive
writes, availability matrices, accepted historical coverage proof, candidate
evidence, candidate packs, paper/live behavior, order placement, sizing,
runtime-mode changes, or promotion claims.
