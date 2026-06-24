# WPR106-493 - V2 Hyperliquid Public WebSocket Source Registry

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-021`
- `V2-AUD-COLLECT-020`
- `V2-AUD-WORKER-027`

## Objective

Close the `DATA-008` source-registry gate for already implemented bounded
Hyperliquid public WebSocket collectors. Add checked source registry entries
for trades, BBO, L2 book, and candle streams, then require public WebSocket
worker specs to declare the exact matching source-registry source ID before
opening a stream.

This packet does not run public WebSocket collection, add broad unattended
capture, enable requester-pays official archives, run backtests, create
accepted historical coverage proof, create candidate evidence, create candidate
packs, add paper/live behavior, place orders, emit sizing instructions, change
runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-493-v2-hyperliquid-public-websocket-source-registry.md`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_trades.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_bbo.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_l2_book.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_candle.json`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_data_source_registry_phase37.py`
- `tests/v2/test_workers_phase7.py`
- `tests/v2/test_microstructure_collection_phase17.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No checked legacy evidence under `data/research/fixtures/**`,
  `data/research/historical_cycles/**`, or existing WPR evidence directories.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_source_registry_phase37.py tests/v2/test_workers_phase7.py tests/v2/test_microstructure_collection_phase17.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Add source-registry samples for:
  - `hyperliquid_ws_trades`;
  - `hyperliquid_ws_bbo`;
  - `hyperliquid_ws_l2_book`;
  - `hyperliquid_ws_candle`.
- Public WebSocket collector specs must include `source_registry_source_id`
  matching the exact stream/datatype route.
- Worker output refs should expose the declared `source_registry_source_id`.

## Acceptance Criteria

- All four public WebSocket source entries validate as strict-free native
  Hyperliquid `SourceRegistryEntry` objects with bounded-session caveats.
- Public WebSocket candle, trade, BBO, and L2 jobs fail before stream fetch when
  `source_registry_source_id` is missing or mismatched.
- Existing successful public WebSocket tests pass with matching source-registry
  source IDs and expose the source ID through output refs.

## Changed Files

- `configs/data_sources/samples/source_registry_hyperliquid_ws_trades.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_bbo.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_l2_book.json`
- `configs/data_sources/samples/source_registry_hyperliquid_ws_candle.json`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_data_source_registry_phase37.py`
- `tests/v2/test_workers_phase7.py`
- `tests/v2/test_microstructure_collection_phase17.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`

## Validation Evidence

```text
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_data_source_registry_phase37.py tests/v2/test_workers_phase7.py tests/v2/test_microstructure_collection_phase17.py -q
108 passed

$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
passed

$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
419 passed

$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
463 passed

git diff --check
passed with existing LF-to-CRLF warnings only
```

## Closeout Notes

WPR106-493 adds checked strict-free source entries for Hyperliquid public
WebSocket trades, BBO, L2 book, and candle streams, then enforces exact
`source_registry_source_id` declarations before public WebSocket stream fetch.
Matching jobs expose the source ID through durable output refs. Missing or
mismatched IDs fail before stream fetch or archive writes. The packet does not
run collection, add broad scheduling, create accepted historical coverage
proof, create candidate evidence, add paper/live behavior, place orders, emit
sizing instructions, change runtime mode, or make promotion claims.
