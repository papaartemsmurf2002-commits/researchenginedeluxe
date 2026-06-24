# WPR106-503 - V2 dYdX Deribit Smoke Fetch Normalize

Status: closed
Owner: Codex Research Agent
Date: 2026-06-24

## Audit IDs

- `V2-AUD-DATASRC-031`

## Objective

Continue `DATA-012` by adding fixture/injected-response smoke fetch and candle
normalization for dYdX indexer candles and Deribit public TradingView candle
data.

This packet does not add collectors, run real network probes in tests, download
market data, write archive data rows, create accepted historical coverage
proof, run backtests, create candidate evidence, create candidate packs, add
paper/live behavior, place orders, emit sizing instructions, change runtime
mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-503-v2-dydx-deribit-smoke-fetch-normalize.md`
- `src/tradingbotsuite/v2/data_sources/reference_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_reference_derivatives_fetch_normalize_phase60.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_reference_derivatives_fetch_normalize_phase60.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Normalize dYdX candle object rows and Deribit columnar TradingView responses
  into stable research-only rows.
- Preserve source ID, endpoint ID, venue symbol, request URL, source timestamp,
  raw fields, numeric fields, and row hash.
- Fail closed for empty payloads, API/fetch errors, malformed rows, bad source
  claims, and historical-coverage-proof attempts.

## Acceptance Criteria

- Injected dYdX and Deribit fixture payloads normalize to stable rows.
- Empty, malformed, and API-error payloads return blocked fetch results rather
  than rows.
- Source entries must remain strict-free allowed external comparison sources
  and cannot be accepted historical coverage proof.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/reference_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_reference_derivatives_fetch_normalize_phase60.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_reference_derivatives_fetch_normalize_phase60.py -q
```

Result: 5 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 450 passed; first `tests/contracts` attempt
hit the known Windows socketpair setup error after 462 passed; sequential
contract rerun passed with 463 passed. `git diff --check` passed with expected
LF-to-CRLF warnings only.

## Closeout Notes

This packet adds fixture/injected-response dYdX/Deribit candle smoke fetch
normalization. It does not add collectors, run real network probes in tests,
download market data, write archive market-data rows, create accepted
historical coverage proof, create candidate evidence, create candidate packs,
add paper/live behavior, place orders, emit sizing instructions, change runtime
mode, or make promotion claims.
