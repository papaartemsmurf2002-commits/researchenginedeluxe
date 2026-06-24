# WPR106-490 - V2 Binance Derivatives Backfill Orchestration

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-018`
- `V2-AUD-QUAL-012`

## Objective

Finish the local, non-worker `DATA-006` chain by adding a bounded orchestration
helper that runs Binance USD-M derivatives context pagination, local
raw/silver archive ingest, and data-family coverage report JSON writing in one
call.

This packet does not schedule durable workers, run backtests, create accepted
Hyperliquid-native evidence, create candidate evidence, create candidate packs,
add paper/live behavior, place orders, emit sizing instructions, change
runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-490-v2-binance-derivatives-backfill-orchestration.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_derivatives_backfill_phase53.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_backfill_phase53.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Compose the WPR106-487 paginator, WPR106-488 archive ingest, and WPR106-489
  coverage builder.
- Always write a coverage JSON report for completed or blocked attempts.
- Preserve page result ID, archive ingest ID, coverage report ID/ref,
  acceptance flag, and blocker reasons in the returned result.

## Acceptance Criteria

- A complete archived derivatives context window returns completed status and a
  coverage JSON ref.
- Missing buckets or current-OI snapshot-only attempts return blocked status
  with coverage JSON refs and explicit blocker reasons.
- The result identity and boundary flags are deterministic and research-only.

## Changed Files

- `docs/work_packets/WPR106-490-v2-binance-derivatives-backfill-orchestration.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_derivatives.py`
- `tests/v2/test_binance_derivatives_backfill_phase53.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_backfill_phase53.py -q
# 4 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_backfill_phase53.py tests/v2/test_binance_derivatives_coverage_phase52.py tests/v2/test_binance_derivatives_archive_ingest_phase51.py tests/v2/test_binance_derivatives_pagination_phase50.py tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_data_source_registry_phase37.py -q
# 37 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 406 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `run_binance_derivatives_context_backfill()` and
  `BinanceDerivativesContextBackfillResult`.
- The helper composes pagination, local raw/silver archive ingest, coverage
  report construction, and coverage JSON writing under
  `manifests/coverage_reports/`.
- Completed attempts return page, archive-ingest, and coverage refs; blocked
  attempts still preserve non-accepted coverage JSON and blocker reasons.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-006` still needs durable worker integration before unattended use.
