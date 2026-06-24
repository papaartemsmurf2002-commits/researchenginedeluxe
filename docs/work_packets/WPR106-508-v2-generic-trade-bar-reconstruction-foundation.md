# WPR106-508 - V2 Generic Trade Bar Reconstruction Foundation

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-036`

## Objective

Start `DATA-014` by adding a venue-neutral, research-only trade-to-bar
reconstruction foundation. The helper consumes already-normalized trade-like
rows, buckets them into OHLCV bars, preserves source registry and symbol-map
refs, distinguishes Hyperliquid-native from external-comparison provenance,
and emits stable report and row hashes.

This packet does not add collectors, download market data, write archive rows,
compare reconstructed bars against source-native candles, create accepted
coverage, build feature panels, run backtests, create candidate evidence,
create candidate packs, add paper/live behavior, place orders, emit sizing
instructions, change runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-508-v2-generic-trade-bar-reconstruction-foundation.md`
- `src/tradingbotsuite/v2/data_sources/bar_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_bar_reconstruction_phase63.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector behavior changes in this packet.
- No archive data downloads, generated market-data rows, accepted historical
  coverage proof, data-family coverage acceptance, or gold panel writes.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_bar_reconstruction_phase63.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add generic `TradeBarInputRow`, `ReconstructedTradeBarRow`, and
  `TradeBarReconstructionReport` models.
- Keep native Hyperliquid and external comparison rows separate; mixed native
  and external rows fail closed.
- Preserve source registry and symbol-map refs in the reconstruction report.
- Treat empty input as blocker evidence rather than accepted coverage.

## Acceptance Criteria

- External rows reconstruct deterministic minute OHLCV bars while remaining
  non-native to Hyperliquid.
- Native rows may reconstruct native-labeled bars but still remain
  non-promotable and not accepted historical coverage proof.
- Empty rows, mixed native/external provenance, and bad historical-coverage
  claims fail closed.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/bar_reconstruction.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_bar_reconstruction_phase63.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_bar_reconstruction_phase63.py -q
```

Result: 5 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 465 passed; `tests/contracts` 463 passed.
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet starts DATA-014 with generic trade-to-bar reconstruction for
already-normalized input rows only. It does not add collectors, downloads,
archive writes, source-native candle comparison, accepted coverage, gold
panels, candidate evidence, candidate packs, paper/live behavior, order
placement, sizing instructions, runtime-mode changes, or promotion claims.
