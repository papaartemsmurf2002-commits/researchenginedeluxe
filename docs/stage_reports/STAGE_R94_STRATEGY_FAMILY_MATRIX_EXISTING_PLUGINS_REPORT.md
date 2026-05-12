# Stage R94 Strategy Family Matrix Existing Plugins Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR94-12-strategy-family-matrix-existing-plugins.md`

## Summary

WPR94-12 is complete. The branch now has a research-only strategy-family matrix
that uses existing strategy plugins for trend continuation, range/chop
reversion, funding/basis, OI flow, current GMM regime, KNN local analog overlay,
and diagnostic liquidation families.

Every family records a no-trade comparator and transparent comparator coverage.
KNN is explicitly modeled as a local analog/filter overlay with required
non-KNN companion strategies, not as standalone alpha. The BTCUSDT cycle defers
KNN strategy and KNN exits until split-safe materialized prediction overlays
exist. Current regime evidence is named as GMM/current-regime evidence, not true
HMM evidence, and the no-regime/GMM mode requirements are explicit.

## Changes

- Added `configs/research/strategy_family_matrix_existing_plugins_v1.json`.
- Added `configs/research/full_cycle_btcusdt_strategy_family_matrix_v1.json`.
- Extended historical research-cycle parsing to accept the WPR94-11 research
  exit-policy identifiers.
- Added contract tests for strategy plugin compatibility, comparator coverage,
  KNN overlay restrictions, diagnostic liquidation scope, GMM wording, and
  research-only cycle parsing.
- Marked the latest-month BTCUSDT cycle fixture diagnostic-only and
  candidate-pack ineligible.

## Boundary

No live trading behavior, live config writes, order placement, promotion
readiness, candidate-pack writing, or sizing logic changed.

Research outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_research_cycle_contract.py tests\contracts\test_strategy_contracts.py tests\historical\test_full_cycle_synthetic.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
python -m json.tool configs\research\strategy_family_matrix_existing_plugins_v1.json > $null
python -m json.tool configs\research\full_cycle_btcusdt_strategy_family_matrix_v1.json > $null
git diff --check
```

Results:

- Focused WPR94-12 tests: 316 passed.
- Contracts: 393 passed.
- Research discovery: 144 passed.
- Compileall: passed.
- JSON parse checks: passed.
- Diff check: passed with existing CRLF conversion warnings only.
