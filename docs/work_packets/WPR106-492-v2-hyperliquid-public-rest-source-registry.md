# WPR106-492 - V2 Hyperliquid Public REST Source Registry

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-020`

## Objective

Close the `DATA-007` source-registry traceability gap for already implemented
Hyperliquid native public REST collector paths. Add checked source registry
entries for public funding history, recent candle snapshot, and L2 book
snapshot sources, then prove the entries are strict-zero-dollar, native to
Hyperliquid, and explicitly not accepted historical coverage proof.

This packet does not rewrite collector behavior, open public network calls,
run broad collection, add WebSocket source entries, enable requester-pays
official archives, run backtests, create candidate evidence, create candidate
packs, add paper/live behavior, place orders, emit sizing instructions, change
runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-492-v2-hyperliquid-public-rest-source-registry.md`
- `configs/data_sources/samples/source_registry_hyperliquid_info_funding_history.json`
- `configs/data_sources/samples/source_registry_hyperliquid_info_candle_snapshot_recent.json`
- `configs/data_sources/samples/source_registry_hyperliquid_info_l2_book_snapshot.json`
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

- Add checked source-registry samples for:
  - `hyperliquid_info_funding_history`;
  - `hyperliquid_info_candle_snapshot_recent`;
  - `hyperliquid_info_l2_book_snapshot`.
- Keep all three `zero_cost_public`, `native_to_hyperliquid=true`, and
  `accepted_historical_coverage_proof=false`.
- Preserve recent-window and snapshot-only caveats in each entry.

## Acceptance Criteria

- All three Hyperliquid public REST source entries validate as
  `SourceRegistryEntry` objects and pass `require_strict_zero_dollar_source()`.
- Funding, candle snapshot, and L2 snapshot entries expose required provenance
  fields matching existing durable collector output refs.
- Tests prove none of the entries can be interpreted as accepted six-month
  historical coverage proof.

## Changed Files

- `configs/data_sources/samples/source_registry_hyperliquid_info_funding_history.json`
- `configs/data_sources/samples/source_registry_hyperliquid_info_candle_snapshot_recent.json`
- `configs/data_sources/samples/source_registry_hyperliquid_info_l2_book_snapshot.json`
- `tests/v2/test_data_source_registry_phase37.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`

## Validation Evidence

```text
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_source_registry_phase37.py -q
11 passed

$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
passed

$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
410 passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
463 passed

git diff --check
passed with existing LF-to-CRLF warnings only
```

## Closeout Notes

WPR106-492 records the existing Hyperliquid public REST collector sources in
the v2 source registry. Funding history, recent candle snapshot, and one-shot
L2 book snapshot entries are strict-free and native to Hyperliquid, but remain
non-accepted historical coverage proof by themselves. No collector behavior,
network operation, broad scheduler, accepted research evidence, candidate
evidence, paper/live behavior, order placement, sizing, runtime-mode change, or
promotion claim was added.
