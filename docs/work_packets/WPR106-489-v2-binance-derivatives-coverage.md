# WPR106-489 - V2 Binance Derivatives Coverage

Status: closed - self_checked
Owner: Codex Research Agent
Date: 2026-06-23

## Audit IDs

- `V2-AUD-DATASRC-017`
- `V2-AUD-QUAL-011`

## Objective

Continue `DATA-006` by adding data-family coverage report construction for
archived Binance USD-M derivatives context rows. Funding, open interest, mark
price, index price, premium index, taker flow, long/short ratio, and basis
coverage must remain separate from candle/trade coverage and must preserve
external non-Hyperliquid-native semantics.

This packet does not schedule durable workers, run backtests, create accepted
Hyperliquid-native evidence, create candidate evidence, create candidate packs,
add paper/live behavior, place orders, emit sizing instructions, change
runtime mode, or make promotion claims.

## Allowed Paths

- `docs/work_packets/WPR106-489-v2-binance-derivatives-coverage.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/**`
- `tests/v2/test_binance_derivatives_coverage_phase52.py`

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
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_coverage_phase52.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Consume completed `BinanceDerivativesContextPageResult` and matching
  `BinanceDerivativesContextArchiveIngestResult`.
- Build `DataFamilyCoverageReport` with source-registry, symbol-map, universe,
  archive snapshot refs, external-comparison label, bucket counts, missing
  bucket strings, and blocker reasons.
- Keep current open-interest snapshot coverage non-accepted because it is not
  a historical window.
- Require archive refs and archive snapshot refs before accepted external
  context coverage.

## Acceptance Criteria

- Archived complete funding/context windows can produce accepted
  external-comparison coverage when all refs and buckets are present.
- Missing buckets produce non-accepted coverage with explicit missing bucket
  metadata.
- Current open-interest snapshot coverage is reported but not accepted.
- Coverage reports preserve full research-only boundary flags and never
  relabel Binance context as Hyperliquid-native.

## Changed Files

- `docs/work_packets/WPR106-489-v2-binance-derivatives-coverage.md`
- `docs/contracts/data_source_registry_contract.md`
- `docs/contracts/data_family_coverage_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `src/tradingbotsuite/v2/data_sources/__init__.py`
- `src/tradingbotsuite/v2/data_sources/binance_derivatives.py`
- `tests/v2/test_binance_derivatives_coverage_phase52.py`

## Validation Evidence

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_coverage_phase52.py -q
# 4 passed
```

Related:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_binance_derivatives_coverage_phase52.py tests/v2/test_binance_derivatives_archive_ingest_phase51.py tests/v2/test_binance_derivatives_pagination_phase50.py tests/v2/test_binance_derivatives_fetch_phase49.py tests/v2/test_binance_derivatives_context_phase48.py tests/v2/test_data_source_registry_phase37.py -q
# 33 passed
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
# 402 passed
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
# 463 passed
git diff --check
# passed with existing LF-to-CRLF working-copy warnings only
```

## Closeout Notes

- Added `build_binance_derivatives_context_coverage_report()`.
- Derivatives context coverage reports use the existing
  `DataFamilyCoverageReport` schema and stay separate from candle/trade
  coverage.
- Complete archived context windows can be accepted only as
  external-comparison coverage with completed page/archive evidence,
  raw/silver refs, archive snapshot refs, and no missing buckets.
- Current open-interest snapshots, blocked inputs, missing archive evidence,
  missing timestamps, missing bucket seconds, missing buckets, and low coverage
  become non-accepted blocker reasons.
- No-touch review: no live runtime, order-placement, sizing, runtime config,
  promotion, shadow, candidate-pack, legacy GUI, secret, or checked legacy
  evidence paths were edited by this packet.

## Follow-up

- `DATA-006` still needs durable worker integration.
