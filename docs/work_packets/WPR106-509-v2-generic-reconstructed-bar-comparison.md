# WPR106-509 - V2 Generic Reconstructed Bar Comparison

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-037`

## Objective

Continue `DATA-014` by adding a venue-neutral, research-only comparison layer
between reconstructed trade bars and source-native candle bars. The comparison
records OHLCV absolute differences, pass/fail/missing status, tolerance
metadata, source registry and symbol-map refs, and stable report identity.

This packet does not add collectors, download market data, write archive rows,
create accepted coverage, build feature panels, run backtests, create
candidate evidence, create candidate packs, add paper/live behavior, place
orders, emit sizing instructions, change runtime mode, or make promotion
claims.

## Allowed Paths

- `docs/work_packets/WPR106-509-v2-generic-reconstructed-bar-comparison.md`
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

- Add generic source-native candle-bar input rows plus comparison row/report
  models.
- Compare only matching venue, symbol, market type, bucket size, and native
  provenance class.
- Missing reconstructed buckets and tolerance breaches become blocker reasons.
- Passing comparisons remain quality metadata only, not coverage acceptance.

## Acceptance Criteria

- Matching reconstructed/native rows pass with zero blocker reasons.
- Missing reconstructed buckets and tolerance breaches fail closed.
- Mixed venue/symbol/provenance comparisons are rejected before a report is
  emitted.
- Comparison reports remain research-only, observe-only, non-promotable, and
  not accepted historical coverage proof.

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

Result: 9 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 469 passed; `tests/contracts` 463 passed.
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds generic reconstructed-vs-source candle comparison as
research-only quality metadata. It does not add collectors, downloads, archive
writes, accepted coverage, gold panels, candidate evidence, candidate packs,
paper/live behavior, order placement, sizing instructions, runtime-mode
changes, or promotion claims.
