# WPR106-486 - V2 Binance Derivatives Fetch Normalize

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-014`

## Objective

Continue `DATA-006` by adding an injectable fetch-and-normalize layer for one
prebuilt Binance USD-M public derivatives context request. The layer must
capture HTTP/provenance metadata, parse endpoint JSON shapes, normalize rows
with source timestamps, interval/period buckets, base/quote unit annotations,
stable row hashes, and fail-closed blocker metadata.

This packet does not add multi-page pagination, archive writes,
coverage-report acceptance, durable worker scheduling, backtests, accepted
Hyperliquid-native evidence, candidate evidence, candidate packs, paper/live
behavior, order placement, sizing instructions, runtime-mode changes, or
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-486-v2-binance-derivatives-fetch-normalize.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_derivatives_fetch_phase49.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked legacy evidence under `data/research/fixtures/**`,
  `data/research/historical_cycles/**`, or existing WPR evidence directories.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_fetch_phase49.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Consume `BinanceDerivativesContextRequest` values produced by WPR106-485.
- Use an injectable GET client so tests do not require Binance network access.
- Normalize endpoint JSON into generic context rows with source family, symbol,
  timestamp, publication timestamp, bucket seconds, numeric fields, unit
  fields, and raw fields.
- Return fetch results with HTTP status, content hash, byte count, row counts,
  normalized-row hash, blocker reasons, and full research-only boundary flags.

## Acceptance Criteria

- Funding, current OI, kline, taker/ratio, and basis payload shapes normalize
  through offline tests.
- Base/quote quantity/value units are explicit in normalized rows where source
  fields allow them.
- HTTP errors, oversized responses, invalid JSON, and invalid rows fail closed.
- Boundary flags remain research-only and non-promotional.

## Changed Files

- `docs/work_packets/WPR106-486-v2-binance-derivatives-fetch-normalize.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_derivatives.py`
- `tests/v2/test_binance_derivatives_fetch_phase49.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_fetch_phase49.py -q
# 5 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_data_source_registry_phase37.py -q
# 20 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 389 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `fetch_binance_derivatives_context_request()` with injectable GET
  support and no required Binance network access in tests.
- Added fetch result, GET result, normalized row, and fetch status schemas with
  stable content/row/fetch hashes and full research-only boundary flags.
- Normalized funding, current OI, OI statistics, mark/index/premium klines,
  taker buy/sell volume, long/short ratios, and basis into generic context rows
  with source timestamps, publication timestamps, interval/period buckets,
  numeric fields, unit fields, and raw fields.
- HTTP errors, explicit fetch errors, oversized responses, invalid JSON,
  invalid row shapes, and invalid timestamps fail closed as blocker metadata.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-006` still needs multi-page pagination, raw/bronze/silver archive
  writes, funding/OI/context coverage reports, and durable worker integration.
