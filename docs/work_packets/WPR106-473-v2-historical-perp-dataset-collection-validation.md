# WPR106-473 - V2 Historical Perp Dataset Collection Validation

Status: closed - self_checked
Owner: Codex Manager Development Agent
Date: 2026-06-22

## Audit IDs

- `V2-AUD-COLLECT-016`
- `V2-AUD-XVENUE-013`
- `V2-AUD-QUAL-006`

## Objective

Add and run a bounded research-only command that collects historical
Hyperliquid public candle data for many current eligible perpetual instruments,
writes it through the existing archive pipeline, validates archive coverage,
and cross-checks overlapping Binance USD-M candles as an external sanity check.

This packet collects and validates historical market data. It does not create
strategy evidence, candidate evidence, paper/live readiness, sizing, order
placement, runtime-mode changes, or promotion claims. Current-public universe
selection remains explicitly sandbox/current-universe evidence until a later
historical as-of universe source is supplied.

## Allowed Paths

- `docs/work_packets/WPR106-473-v2-historical-perp-dataset-collection-validation.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/data_quality_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/cli/main.py`
- `src/tradingbotsuite/v2/collectors/historical_dataset.py`
- `tests/v2/test_historical_dataset_collection_phase36.py`
- `data/research/operator_runs/v2_historical_dataset/**`

## No-Touch Paths

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer paths.
- No legacy GUI paths.
- No checked legacy evidence under `data/research/fixtures/**`,
  `data/research/historical_cycles/**`, or existing WPR evidence directories.
- No secrets, `.env`, credential files, private cache paths, or local operator
  DBs.

## Expected Tests

Focused:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/v2/test_historical_dataset_collection_phase36.py -q
```

Baseline:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/v2 -q
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
git diff --check
```

## Implementation Notes

- Use unsigned public Hyperliquid market-data endpoints only.
- Use the existing raw -> bronze -> silver archive services rather than writing
  ad hoc data files.
- Record current-public universe scope as sandbox/current-universe, not
  historical as-of accepted evidence.
- Validate timestamp coverage against the requested window and timeframe.
- Use Binance USD-M public klines only as cross-venue candle sanity evidence;
  Binance data is not Hyperliquid ground truth.
- Skip Binance validation cleanly when a matching `COINUSDT` contract is not
  available or a public request fails.

## Decisions Made

- Added `redx collectors historical-perps` as a bounded public historical data
  command instead of changing the durable worker contract. The command reuses
  existing raw, bronze, silver, coverage, snapshot, and universe services.
- Kept the output report `sandbox_diagnostic` and
  `accepted_research_ready=false` because the selection is current-public
  universe, not historical as-of universe.
- Added optional `--include-funding` so funding intake can be run explicitly
  rather than hidden inside every candle collection.
- Used Binance USD-M public klines only as cross-venue sanity validation for
  overlapping candle timestamps and close prices.
- Preserved original Hyperliquid venue symbols from the universe catalog so
  case-sensitive symbols such as `kPEPE` are fetched correctly.
- Recorded `ISSUE-R106-030` for old Hyperliquid public 1h windows returning
  empty while old daily candles and Binance 1h klines are available.

## Changed Files

- `docs/work_packets/WPR106-473-v2-historical-perp-dataset-collection-validation.md`
- `docs/contracts/collector_job_contract.md`
- `docs/contracts/venue_adapter_contract.md`
- `docs/contracts/data_quality_contract.md`
- `docs/audit/V2_AUDIT_INDEX.md`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/V2_ROADMAP_IMPLEMENTATION_STATUS.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/v2/cli/main.py`
- `src/tradingbotsuite/v2/collectors/historical_dataset.py`
- `tests/v2/test_historical_dataset_collection_phase36.py`
- generated local artifacts under `data/research/operator_runs/v2_historical_dataset/**`

## Acceptance Evidence

Focused validation:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\v2\test_historical_dataset_collection_phase36.py -q
# 2 passed
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite\v2\collectors\historical_dataset.py src\tradingbotsuite\v2\cli\main.py
# passed
```

Baseline validation:

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src\tradingbotsuite
# passed
$env:PYTHONPATH='src'; python -m pytest tests\v2 -q
# 330 passed
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
# 463 passed
git diff --check
# passed with expected LF-to-CRLF warnings only
```

Real public collection smoke:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main collectors historical-perps --output-root data\research\operator_runs\v2_historical_dataset --run-id wpr106-473-top25c-1d-2024-2026 --start-ts 2024-01-01T00:00:00+00:00 --end-ts 2026-06-01T00:00:00+00:00 --timeframe 1d --asof-date 2026-06-22 --max-instruments 25 --binance-timeout 20
# selected_instrument_count=25
# collected_instrument_count=25
# technical_coverage_pass_count=14
# binance_pass_count=24
# binance_warning_count=1
# accepted_research_ready=false
```

Funding smoke:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.v2.cli.main collectors historical-perps --output-root data\research\operator_runs\v2_historical_dataset --run-id wpr106-473-funding-smoke-btc-eth-sol-2024-01 --start-ts 2024-01-01T00:00:00+00:00 --end-ts 2024-02-01T00:00:00+00:00 --timeframe 1d --asof-date 2026-06-22 --max-instruments 0 --coin BTC --coin ETH --coin SOL --include-funding --max-funding-pages 10 --binance-timeout 20
# selected_instrument_count=3
# collected_instrument_count=3
# technical_coverage_pass_count=3
# funding_collected_count=3
# funding rows: BTC 744, ETH 744, SOL 744
# accepted_research_ready=false
```

Provider limitation evidence:

```text
Hyperliquid BTC 1h 2024-01-01..2024-01-08 returned 0 rows.
Hyperliquid BTC 1d 2024-01-01..2024-01-08 returned 8 rows.
Hyperliquid BTC 1h 2026-06-01..2026-06-08 returned 169 rows.
Binance BTCUSDT 1h 2024-01-01..2024-01-08 returned rows.
```

## No-Touch Review

- No live runtime, order-placement, sizing, runtime config, promotion, or
  candidate-pack truth-layer path was changed.
- No legacy GUI path was changed.
- No checked legacy evidence under `data/research/fixtures/**` or
  `data/research/historical_cycles/**` was rewritten.
- Generated WPR106-473 artifacts are local research outputs under
  `data/research/operator_runs/v2_historical_dataset/**`.
- The packet creates no accepted research, autonomous-ready, candidate-ready,
  paper/live/order/sizing/runtime, or promotion claim.
