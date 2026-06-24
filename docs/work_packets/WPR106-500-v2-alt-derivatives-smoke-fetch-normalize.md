# WPR106-500 - V2 Alt Derivatives Smoke Fetch Normalize

Status: closed
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-028`

## Objective

Continue `DATA-011` by adding an in-memory, injectable smoke fetch and
normalization layer for the MEXC, Bitget, Gate, KuCoin, and HTX candle
availability requests introduced in WPR106-499.

This packet does not add heavy backfill, durable worker routing, download
caches, raw/bronze/silver archive writes, feature generation, accepted
historical coverage proof, candidate evidence, candidate packs, paper/live
behavior, order placement, sizing instructions, runtime-mode changes, or
promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-500-v2-alt-derivatives-smoke-fetch-normalize.md`
- `src/tradingbotsuite/v2/data_sources/alt_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_alt_derivatives_fetch_normalize_phase58.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, shadow,
  or candidate-pack truth-layer paths.
- No collector scheduling, archive writes, broad backfill, or generated
  external market-data evidence.
- No real network probes in tests; all fetches must use injected clients.
- No secrets, `.env`, credential files, private cache paths, or local operator
  databases.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_alt_derivatives_fetch_normalize_phase58.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Reuse WPR106-499 request builders and `AltDerivativesGetResult`.
- Normalize fixture/injected candle responses into stable rows with timestamp,
  OHLCV fields, raw fields, request URL, endpoint/source metadata, and row
  hash.
- Fail closed for empty responses, API errors, malformed rows, wrong source
  IDs, or non-strict-free source entries.

## Acceptance Criteria

- Fixture payloads for the five DATA-011 venues normalize into stable
  research-only rows.
- Empty payloads, malformed rows, API errors, and bad source claims fail closed
  without archive writes.
- Smoke results remain external comparison outputs and never accepted
  historical coverage proof.

## Changed Files

- `src/tradingbotsuite/v2/data_sources/alt_derivatives.py`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `docs/contracts/data_source_registry_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `tests/v2/test_alt_derivatives_fetch_normalize_phase58.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_alt_derivatives_fetch_normalize_phase58.py -q
```

Result: 4 passed.

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

Result: compile passed; `tests/v2` 440 passed; `tests/contracts` 463 passed;
`git diff --check` passed with expected LF-to-CRLF warnings only.

## Closeout Notes

This packet adds in-memory smoke fetch normalization only. It does not add
durable worker routing, collector scheduling, real network probes in tests,
downloads, raw/bronze/silver archive writes, accepted historical coverage
proof, candidate evidence, candidate packs, paper/live behavior, order
placement, sizing instructions, runtime-mode changes, or promotion claims.
