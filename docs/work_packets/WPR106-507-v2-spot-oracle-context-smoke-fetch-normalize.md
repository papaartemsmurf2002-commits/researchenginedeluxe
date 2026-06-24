# WPR106-507 - V2 Spot Oracle Context Smoke Fetch Normalize

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-035`

## Objective

Continue `DATA-013` by adding an in-memory smoke fetch and normalization layer
for the spot/oracle/on-chain context availability requests introduced by
WPR106-506. The layer consumes injected HTTP responses, classifies empty,
fetch-error, parse-error, and completed outcomes, and emits stable normalized
rows with source/request provenance and research-only boundary flags.

This packet does not add collectors, run live data collection, download market
data into archive rows, create accepted historical coverage proof, run
backtests, create candidate evidence, create candidate packs, add paper/live
behavior, place orders, emit sizing instructions, change runtime mode, or make
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-507-v2-spot-oracle-context-smoke-fetch-normalize.md`
- `src/tradingbotsuite/v2/data_sources/spot_oracle_context.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_spot_oracle_context_fetch_normalize_phase62.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No archive data downloads, generated market-data rows, accepted historical
  coverage proof, or data-family coverage acceptance.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_spot_oracle_context_fetch_normalize_phase62.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse `SpotOracleContextAvailabilityRequest` and strict-free source-entry
  validation from the availability matrix.
- Normalize Coinbase/Kraken candle rows, Pyth parsed price rows, DefiLlama
  coin entries, DexScreener pairs, and GeckoTerminal pool entries into a
  generic context row with stable hashes.
- Keep normalized output in memory only; no raw, bronze, silver, coverage, or
  archive writes.

## Acceptance Criteria

- Completed smoke fetches emit stable normalized rows for all six DATA-013
  endpoint families.
- Empty payloads and API errors fail closed with blocker metadata.
- Bad source claims and historical-coverage-proof source entries fail before
  normalization.
- Normalized rows remain research-only, observe-only, non-native to
  Hyperliquid, and not promotion/candidate/paper/live/sizing/order/runtime
  evidence.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/spot_oracle_context.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_spot_oracle_context_fetch_normalize_phase62.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_spot_oracle_context_fetch_normalize_phase62.py -q
```

Result: 5 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 460 passed; first `tests/contracts`
attempt hit the known Windows socketpair setup error after 462 passed;
sequential contract rerun passed with 463 passed. `git diff --check` passed
with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds in-memory DATA-013 smoke fetch normalization for injected
responses only. It does not add collectors, downloads, archive market-data
rows, accepted historical coverage proof, candidate evidence, candidate packs,
paper/live behavior, order placement, sizing instructions, runtime-mode
changes, or promotion claims.
