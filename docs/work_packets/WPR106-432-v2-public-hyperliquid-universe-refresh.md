# WPR106-432 - V2 Public Hyperliquid Universe Refresh Provenance

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-21

## Audit IDs

- `V2-AUD-UNIV-002`
- `V2-AUD-COLLECT-005`
- `V2-AUD-XVENUE-002`

## Purpose

Make the Hyperliquid universe-refresh path explicitly support an unsigned
public API source mode with venue raw-request/raw-response provenance. This
packet tightens the existing public-info fallback into auditable metadata for
the operational loop's universe step. It does not add candle/funding market
record API fetches, WebSocket streaming, official network downloads, private
Hyperliquid endpoints, account state, order placement, sizing, runtime-mode
mutation, candidate-pack behavior, or promotion behavior.

## Allowed Paths

- `docs/work_packets/WPR106-432-v2-public-hyperliquid-universe-refresh.md`
- `docs/contracts/universe_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/contracts.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/info.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/venues/__init__.py`
- `src/tradingbotsuite/v2/universe/models.py`
- `src/tradingbotsuite/v2/universe/hyperliquid.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_workers_phase7.py`

## No-Touch Paths

No no-touch path is in scope. This packet must not modify live/runtime/order
placement/sizing/promotion paths, candidate-pack truth-layer paths, generated
research evidence, legacy GUI paths, old `tradingbot` compatibility code,
secrets, credential files, or unreviewed local state.

## Decisions Made

- Use the already-scoped Hyperliquid public `/info` endpoint and
  `type=metaAndAssetCtxs`; do not introduce any signed/private API surface.
- Add explicit `public_api` source provenance for universe refresh results and
  durable worker output refs.
- Require CLI and worker callers to choose either a local `payload_file` or
  explicit `source=public_api` instead of silently treating an omitted fixture
  path as a network request.
- Use injectable HTTP transport in tests so validation never depends on live
  network availability.
- Keep raw-before-parse archiving unchanged: the raw archive contains the
  venue payload before parser output is written, while venue request/response
  IDs are surfaced as provenance refs.
- Treat public universe metadata as necessary intake evidence, not as
  autonomous-ready or accepted backtest evidence by itself.

## Expected Tests

- Focused:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_workers_phase7.py -q`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
- Baseline:
  - `python -m compileall -q src/tradingbotsuite`
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- Hygiene:
  - `git diff --check`

## Changed Files

- `docs/work_packets/WPR106-432-v2-public-hyperliquid-universe-refresh.md`
- `docs/contracts/universe_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/worker_job_contract.md`
- `docs/V2_OPERATIONS_RUNBOOK.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `src/tradingbotsuite/v2/venues/contracts.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/info.py`
- `src/tradingbotsuite/v2/venues/hyperliquid/__init__.py`
- `src/tradingbotsuite/v2/venues/__init__.py`
- `src/tradingbotsuite/v2/universe/models.py`
- `src/tradingbotsuite/v2/universe/hyperliquid.py`
- `src/tradingbotsuite/v2/collectors/jobs.py`
- `src/tradingbotsuite/v2/cli/main.py`
- `tests/v2/test_universe_phase5.py`
- `tests/v2/test_workers_phase7.py`

## Acceptance Evidence

- Focused universe/worker lane:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2/test_universe_phase5.py tests/v2/test_workers_phase7.py -q`
  - Result: `40 passed`
- Broad v2:
  - `$env:PYTHONPATH='src'; python -m pytest tests/v2 -q`
  - Result: `209 passed`
- Baseline compile:
  - `python -m compileall -q src/tradingbotsuite`
  - Result: passed
- Contract baseline:
  - `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
  - Result: `463 passed`
- Diff hygiene:
  - `git diff --check`
  - Result: passed with existing LF-to-CRLF working-copy warnings only
- Optional live public-info smoke into a temporary archive outside the repo:
  - `$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main universe refresh --archive-root <temp> --venue hyperliquid --source public_api --asof-date 2026-06-21 --min-day-notional-usd 5000000 --include-hip3-dexs`
  - Result: succeeded; `source_mode=public_api`, `instrument_count=230`,
    `eligible_count=23`, `venue_adapter_id=hyperliquid_public_info_v1`,
    `source_endpoint_or_subscription=info/metaAndAssetCtxs`, and raw
    request/response IDs were emitted.

## Boundary Statement

The packet remains research-only and observe-only. Public Hyperliquid metadata
refresh must not create accepted-evidence status by itself, autonomous-ready
status, candidate-pack eligibility, paper/live/order/sizing/runtime behavior,
or promotion readiness.
