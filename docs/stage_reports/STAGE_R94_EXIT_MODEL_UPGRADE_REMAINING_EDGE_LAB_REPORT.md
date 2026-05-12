# Stage R94 Exit Model Upgrade And Remaining-Edge Lab Report

Date: 2026-05-12
Branch: `research/v3-experimental-engine`
Packet: `docs/work_packets/WPR94-11-exit-model-upgrade-remaining-edge-lab.md`

## Summary

WPR94-11 is complete. Discovery exit-lab evidence now covers executable
basis/premium normalization exits, current GMM transition exits, KNN
remaining-edge exits, KNN dynamic barriers, and existing funding/OI exits while
preserving fixed-holding comparators.

True HMM transition and liquidity/depth adverse-selection exits are explicitly
deferred and cannot win exit-lab candidate gates. The current regime transition
path is named as GMM/current-regime evidence, not true HMM evidence.

## Changes

- Added primary-bar research exits:
  - `basis_normalization_exit_v1`
  - `premium_normalization_exit_v1`
  - `gmm_transition_exit_v1`
  - `knn_remaining_edge_exit_v1`
  - `knn_dynamic_barriers_v1`
- Registered those exits in reference execution simulation only.
- Preserved vector backend fixed-holding-only scope.
- Passed perp, GMM, and KNN context columns through the research backtest market
  frame for exit execution.
- Expanded `discovery_exit_lab_v4` grouping to side, split, regime mode, holding
  window, cost stress, feature setup, and KNN setup where present.
- Added deferred evidence labels for true HMM transition and durable depth/L2
  adverse-selection exits.

## Boundary

No live trading behavior, live config writes, order placement, promotion
readiness, candidate-pack writing, or sizing logic changed.

Research outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

## Validation

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_exit_lab.py tests\backtesting\test_exit_policy_expansion.py tests\backtesting\test_vector_engine_matches_reference.py tests\contracts\test_backtest_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q
python -m compileall -q src\tradingbotsuite
python -m json.tool configs\discovery\discovery_exit_lab_v4.json > $null
git diff --check
```

Results:

- Focused WPR94-11 tests: 94 passed.
- Contracts: 387 passed.
- Research discovery: 144 passed.
- Backtesting: 82 passed.
- Compileall: passed.
- JSON parse check: passed.
- Diff check: passed with existing CRLF conversion warnings only.
