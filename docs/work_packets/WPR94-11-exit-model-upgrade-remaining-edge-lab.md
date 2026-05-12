# WPR94-11 Exit Model Upgrade And Remaining-Edge Lab

Status: closed
Owner: Codex Research Agent
Date: 2026-05-12

## Purpose

Expand discovery exit-lab evidence so BTC/ETH research leads are judged by
executable exit logic, not only fixed-hold or simple triple-barrier labels.

## Allowed Paths

- `docs/work_packets/WPR94-11-exit-model-upgrade-remaining-edge-lab.md`
- `docs/stage_reports/STAGE_R94_EXIT_MODEL_UPGRADE_REMAINING_EDGE_LAB_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `src/tradingbotsuite/research_discovery/exit_lab.py`
- `src/tradingbotsuite/backtesting/exits.py`
- `src/tradingbotsuite/backtesting/execution_sim.py`
- `src/tradingbotsuite/backtesting/engine.py`
- `configs/discovery/discovery_exit_lab_v4.json`
- `tests/research_discovery/test_exit_lab.py`
- `tests/backtesting/test_exit_policy_expansion.py`
- `tests/backtesting/test_vector_engine_matches_reference.py`
- `tests/contracts/test_backtest_contracts.py`

## Scope

- Add or expose research-only exit families where existing data contracts allow:
  - basis/premium normalization exits
  - current GMM-regime transition exit
  - KNN remaining-edge exit
  - KNN dynamic-barrier exit metadata/evidence
  - already-supported funding-aware and OI-contraction exits where applicable
- Keep true HMM transition exit deferred until a true HMM backend exists.
- Keep liquidity adverse-selection/depth exits diagnostic/deferred until durable
  book/depth evidence exists.
- Require exit comparisons to share identical entries, splits, costs, feature
  sets, regime mode, and KNN setup.
- Record evidence by side, split, regime mode, holding window, and cost stress.

## Non-Goals

- No live trading behavior, live config writes, order placement, runtime mode
  changes, promotion readiness, candidate-pack writing, or sizing logic changes.
- No true HMM claim.
- No true depth/L2 or liquidity adverse-selection exit candidate-ready claim.
- No strategy family blueprint configs; those belong to a later packet.

## Validation Plan

```powershell
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_exit_lab.py tests\backtesting\test_exit_policy_expansion.py tests\backtesting\test_vector_engine_matches_reference.py tests\contracts\test_backtest_contracts.py -q
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q
python -m compileall -q src\tradingbotsuite
git diff --check
```

## Validation Result

- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery\test_exit_lab.py tests\backtesting\test_exit_policy_expansion.py tests\backtesting\test_vector_engine_matches_reference.py tests\contracts\test_backtest_contracts.py -q` - 94 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` - 387 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_discovery -q` - 144 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\backtesting -q` - 82 passed.
- `python -m compileall -q src\tradingbotsuite` - passed.
- `python -m json.tool configs\discovery\discovery_exit_lab_v4.json > $null` - passed.
- `git diff --check` - passed with existing CRLF conversion warnings only.

## Exit Evidence

- Added executable primary-bar research exit policies:
  `basis_normalization_exit_v1`, `premium_normalization_exit_v1`,
  `gmm_transition_exit_v1`, `knn_remaining_edge_exit_v1`, and
  `knn_dynamic_barriers_v1`.
- Extended the reference backtest market-frame passthrough so those exits can
  consume existing perp, GMM, and KNN context columns without changing live or
  sizing behavior.
- Kept vector backtesting limited to fixed-holding exits and added rejection
  coverage for the new research exits.
- Upgraded discovery exit-lab grouping to preserve side, split, regime mode,
  cost stress, feature setup, and KNN setup where present.
- Added exit-lab families for basis/premium normalization, current GMM regime
  transitions, KNN remaining edge, KNN dynamic barriers, and supported
  funding/OI exits.
- Marked true HMM transition and liquidity/depth adverse-selection exits as
  deferred evidence so they cannot become candidate-ready winners before their
  data/backend prerequisites exist.
- All exit-lab and backtest artifacts remain `research_only: true`,
  `observe_only: true`, and `promotion_ready: false`.
