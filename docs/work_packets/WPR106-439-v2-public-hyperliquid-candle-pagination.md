# WPR106-439 - V2 Public Hyperliquid Candle Pagination

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-COLLECT-010`
- `V2-AUD-XVENUE-007`
- `V2-AUD-ARCH-016`

## Objective

Extend the explicit public Hyperliquid `/info` `candleSnapshot` collector mode
so durable `recent_candle_bootstrap` jobs split requested time ranges into
bounded page windows instead of issuing one large request. The worker must keep
per-page raw request/response provenance, enforce a configured page cap, and
write the combined page rows through the existing raw -> bronze -> silver
archive pipeline.

This packet improves recent-window archive intake only. It does not prove full
historical candle coverage, accepted research evidence, 2024+ readiness,
six-month readiness, candidate-pack output, paper/live/order/sizing/runtime
behavior, or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-439-v2-public-hyperliquid-candle-pagination.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked historical evidence under `data/research/**`.
- No secrets, `.env`, local SQLite operator DBs, private cache, or generated
  runtime output paths.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q
```

Baseline:

```powershell
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
git diff --check
```

## Implementation Notes

- Keep `source=public_api` as the only public candle venue-fetch path.
- Split candle requests by interval and a configurable
  `max_candles_per_public_page`, defaulting to and never exceeding the
  documented 5000-candle cap.
- Enforce `max_public_info_pages`, failing closed if the requested range would
  exceed the cap.
- Return page count plus plural raw request ID, raw response ID, and raw payload
  hash refs. Preserve single-page refs for existing consumers.
- Keep the raw archive write before normalization and keep existing coverage and
  snapshot behavior.
- Reject unsupported variable-width candle intervals when deterministic page
  windows cannot be computed.

## Decisions Made

- Added bounded public candle pagination inside the existing
  `recent_candle_bootstrap` `source=public_api` worker mode instead of adding a
  new job kind.
- Used deterministic fixed-width page windows from the declared candle
  interval and `max_candles_per_public_page`, defaulting to the documented
  5000-candle public endpoint cap.
- Made `max_candles_per_public_page` fail closed when it exceeds the
  documented 5000-candle public endpoint cap.
- Preserved existing single-page `raw_request_id`, `raw_response_id`, and
  `raw_payload_sha256` output refs from the first page for compatibility, and
  added plural refs as the authoritative multi-page provenance.
- Made `max_public_info_pages` fail closed before archive writes when a
  requested range exceeds the configured page cap.
- Rejected unsupported variable-width candle intervals for pagination rather
  than silently approximating them.
- Kept the result explicitly labeled as recent-window intake and not accepted
  historical evidence.

## Changed Files

- `docs/work_packets/WPR106-439-v2-public-hyperliquid-candle-pagination.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused worker validation:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_workers_phase7.py -q`
  - Result: `37 passed`
- Compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contracts:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: initial runs hit the existing Windows asyncio socketpair validation
    issue before an async test body ran; isolated retries passed with
    `463 passed`.
- Full v2 suite:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `228 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF warnings only.

## No-Touch Review

- No no-touch path was edited.
- No live runtime, order-placement, sizing, runtime config, promotion,
  candidate-pack truth-layer, legacy GUI, checked `data/research/**` evidence,
  secret, credential, local DB, or private cache path was touched.
- The worker uses only the explicit public Hyperliquid `source=public_api`
  candle path already scoped by WPR106-433 and does not add signed/private,
  account, order, sizing, runtime, or promotion behavior.
- The packet adds no accepted-evidence, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion behavior.
