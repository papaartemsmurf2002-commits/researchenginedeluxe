# WPR106-487 - V2 Binance Derivatives Pagination

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-015`

## Objective

Continue `DATA-006` by adding bounded multi-page fetch coordination for
Binance USD-M public derivatives context endpoints. The helper must build
endpoint-specific request pages, call the WPR106-486 single-request
fetch/normalize layer, advance cursors from normalized timestamps, enforce
max-page limits, preserve page result IDs, and fail closed on non-advancing
or blocked pages.

This packet does not write archive rows, create coverage reports, schedule
durable workers, run backtests, create accepted Hyperliquid-native evidence,
create candidate evidence, create candidate packs, add paper/live behavior,
place orders, emit sizing instructions, change runtime mode, or make
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-487-v2-binance-derivatives-pagination.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_derivatives_pagination_phase50.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_pagination_phase50.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Paginated historical families require bounded `start_time_ms` and
  `end_time_ms`.
- Current open-interest remains a one-page current-context fetch.
- Cursor advancement uses normalized row timestamps and interval/period bucket
  seconds where available.
- `max_pages` exhaustion with remaining window becomes blocker metadata.

## Acceptance Criteria

- Funding and kline families fetch multiple pages offline and advance cursors
  deterministically.
- Current OI can run exactly one page without time-range params.
- Blocked pages, non-advancing cursors, and max-page exhaustion fail closed.
- Result identity, page refs, row hashes, and boundary flags are deterministic
  and research-only.

## Changed Files

- `docs/work_packets/WPR106-487-v2-binance-derivatives-pagination.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_derivatives.py`
- `tests/v2/test_binance_derivatives_pagination_phase50.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_pagination_phase50.py -q
# 5 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_pagination_phase50.py tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_data_source_registry_phase37.py -q
# 25 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 394 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `fetch_binance_derivatives_context_pages()` and
  `BinanceDerivativesContextPageResult`.
- Historical time-range endpoints now require bounded `start_time_ms` and
  `end_time_ms`; current open interest remains a single current-context page.
- Page URLs, fetch-result IDs, row hashes, row counts, and blocker reasons are
  preserved in the page result.
- Cursor advancement uses normalized timestamps plus bucket seconds where the
  request has an interval or period; funding-style rows advance by timestamp
  plus one millisecond.
- Missing bounds, blocked pages, request errors, non-advancing cursors, and
  max-page exhaustion fail closed as blocker metadata.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-006` still needs raw/bronze/silver archive writes, funding/OI/context
  coverage reports, and durable worker integration.
