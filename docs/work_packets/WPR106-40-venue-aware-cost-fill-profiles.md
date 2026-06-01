# WPR106-40 Venue-Aware Cost And Fill Profiles

## Goal

Add machine-readable venue-aware cost and fill profile evidence to research
backtests and historical-cycle cost-stress rows without changing strategies,
candidate gates, live/paper behavior, order placement, or promotion logic.

The packet must make clear that Binance historical cost evidence is research
evidence only and is not Hyperliquid execution proof.

## Current Repo Facts

- `CostModel` carries numeric `fee_bps`, `slippage_bps`, `spread_bps`,
  `funding_rate`, `funding_interval_ms`, and a default `venue` string.
- `BacktestSpec` exposes the numeric cost assumptions but does not expose a
  stable cost profile id, fill profile id, source venue, execution venue, or
  execution-proof scope.
- Backtest manifests include `cost_model`, and cache keys include that payload.
- Reference, vector, CUDA fixed-holding, and CUDA batched fixed-holding engines
  construct `CostModel` independently.
- Historical-cycle cost-stress scenarios are hardcoded in
  `research_cycle.runner._cost_stress_scenarios()` and carry numeric cost
  values only.
- Cost-stress rows gate candidates through existing survival checks; the
  current packet must not weaken those checks.

## Conflicts And Stale Docs Found

- Older docs mention cost/funding stress generally but do not distinguish venue
  cost-profile evidence from execution proof.
- Current stress scenarios implicitly look like Binance USDM historical research
  assumptions because the active BTC/ETH evidence source is Binance public
  archive data.

## Allowed Edit Paths

- `docs/work_packets/WPR106-40-venue-aware-cost-fill-profiles.md`
- `docs/work_packets/WPR106-40-progress.jsonl`
- `src/tradingbotsuite/backtesting/costs.py`
- `src/tradingbotsuite/backtesting/__init__.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `src/tradingbotsuite/backtesting/vector_engine.py`
- `src/tradingbotsuite/backtesting/cuda_engine.py`
- `src/tradingbotsuite/backtesting/cuda_batched_engine.py`
- `src/tradingbotsuite/research_cycle/runner.py`
- focused tests under `tests/contracts/**`, `tests/backtesting/**`,
  `tests/unit/**`, and `tests/historical/**`
- `docs/ACTIVE_INDEX.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/stage_reports/STAGE_R106_VENUE_AWARE_COST_FILL_PROFILES_REPORT.md`

## Forbidden Edit Paths

- strategy plugins and search spaces
- candidate gate thresholds or survival formulas
- live/paper/runtime/order-placement adapters
- generated research artifacts or fixture data
- Hyperliquid live/testnet configuration
- broad historical docs rewrites outside active index, ledger, and report
- `.pytest_cache/**`

## Subagents Used

- Cost Model Engineer: read-only audit of existing cost/fill surfaces,
  venue labels, stress rows, and validation risks.

## Tests To Run

```powershell
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_backtest_contracts.py tests\unit\test_execution_simulator.py -q
$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
git diff --check
```

## Artifacts Expected

- Backtest manifests expose stable cost/fill profile metadata.
- Backtest cache keys change when cost/fill profile metadata changes.
- Historical-cycle cost-stress rows expose scenario profile ids, source venue,
  execution venue, and explicit execution-proof scope.
- Existing scenario count and candidate gate survival semantics remain intact.
- Updated stage report.

No generated research artifacts, candidate packs, promotion claims, live
runtime behavior, or new strategy behavior are expected.

## Definition Of Done

- Venue cost/fill profile metadata is visible in backtest manifests and
  historical-cycle stress evidence.
- Unknown cost profile ids fail closed in backtest construction.
- Binance historical cost evidence is explicitly marked research-only and not
  Hyperliquid execution proof.
- Existing cost-stress scenarios remain at least as strict as before and still
  participate in the same survival gate.
- Focused and contract validation passes.

## Rollback Plan

Revert only files listed in allowed edit paths. Do not touch generated
artifacts, candidate packs, live/runtime paths, or unrelated cache state.
