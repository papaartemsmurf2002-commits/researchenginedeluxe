# WPR106-497 - V2 Bybit OKX Smoke Fetch Normalize

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-025`

## Objective

Continue `DATA-010` by adding a small, injectable Bybit/OKX public-market
smoke fetch and normalization layer for supported date-window endpoints.

This packet does not add heavy backfill, durable worker routing, download
caches, raw/bronze/silver archive writes, feature generation, accepted
historical coverage proof, candidate evidence, candidate packs, paper/live
behavior, order placement, sizing instructions, runtime-mode changes, or
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-497-v2-bybit-okx-smoke-fetch-normalize.md`
- `src/tradingbotsuite/v2/data_sources/bybit_okx.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_bybit_okx_fetch_normalize_phase56.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No Bybit/OKX collector scheduling, archive writes, broad backfill, or
  generated external market-data evidence.
- No real network probes in tests; all fetches must use injected clients.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_bybit_okx_fetch_normalize_phase56.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse WPR106-496 request builders and `BybitOkxGetResult`.
- Normalize only fixture/injected responses for date-window supported endpoint
  families such as klines, funding, and open interest.
- Emit stable row hashes, source URL/endpoint metadata, parsed timestamps,
  numeric fields, raw fields, and research-only boundary flags.
- Block recent/snapshot endpoints before fetch so they cannot masquerade as
  historical smoke coverage.

## Acceptance Criteria

- Bybit and OKX fixture payloads normalize into stable research-only rows.
- API errors, empty payloads, malformed rows, and unsupported endpoint-limited
  specs fail closed without archive writes.
- Smoke results remain external comparison outputs and never accepted
  historical coverage proof.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/bybit_okx.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_bybit_okx_fetch_normalize_phase56.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_bybit_okx_fetch_normalize_phase56.py -q
```

Result: 5 passed.

Combined DATA-010 focus:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_bybit_okx_availability_phase55.py tests/v2/test_bybit_okx_fetch_normalize_phase56.py -q
```

Result: 10 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 431 passed; `tests/contracts` 463 passed;
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds in-memory smoke fetch normalization only. It does not add
durable worker routing, collector scheduling, real network probes in tests,
downloads, raw/bronze/silver archive writes, accepted historical coverage
proof, candidate evidence, candidate packs, paper/live behavior, order
placement, sizing instructions, runtime-mode changes, or promotion claims.
