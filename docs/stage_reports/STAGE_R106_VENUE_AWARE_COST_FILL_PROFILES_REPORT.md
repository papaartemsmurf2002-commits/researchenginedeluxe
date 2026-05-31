# Stage R106 Venue-Aware Cost And Fill Profiles Report

Date: 2026-05-31

Work packet: `docs/work_packets/WPR106-40-venue-aware-cost-fill-profiles.md`

## Scope

Added venue-aware research cost/fill profile metadata to backtest and
historical-cycle cost-stress evidence. This was metadata, validation, and
manifest hardening only.

This packet did not add strategies, filters, models, live/paper behavior,
order placement, promotion logic, candidate-pack eligibility changes, or
generated research artifacts.

## Changes

- Added registered research cost profiles in `backtesting.costs` with stable
  `cost_profile_id`, `fill_profile_id`, source venue, execution venue, evidence
  scope, and execution-proof scope.
- Backtest manifests and cache-key components now include cost/fill profile
  metadata through `CostModel.to_payload()`.
- Unknown cost profile ids and unknown fill profile ids fail closed before
  backtest artifacts are written.
- Reference, vector, CUDA fixed-holding, and CUDA batched fixed-holding engines
  all use the same cost-profile construction helper.
- Historical-cycle cost-stress scenarios are generated from the registered
  profile contract while preserving the existing 11-scenario set.
- Historical-cycle backtest-index rows and metrics-by-cost-stress rows now
  expose venue/cost/fill profile metadata and
  `not_hyperliquid_execution_proof`.

## Validation

- `python -m compileall -q src\tradingbotsuite` passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts\test_backtest_contracts.py tests\unit\test_execution_simulator.py -q` passed: 38 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\historical\test_full_cycle_synthetic.py -q` passed: 20 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q` passed: 432 tests.
- `$env:PYTHONPATH='src'; python -m pytest tests\research_artifacts\test_candidate_pack.py -q` passed: 37 tests.
- `git diff --check` passed with only existing CRLF warnings.

## Boundary Statement

The cost/fill profiles are research evidence only. The default source venue is
Binance USDM, the execution venue is `binance_usdm_research`, and the
execution-proof scope is `historical_research_only_not_live_execution_proof`.
The evidence explicitly remains not Hyperliquid execution proof.

## Remaining Work

The next empirical packet should route WPR106-31 replayed KNN prediction
artifacts through historical-cycle overlay, ranking, full exit lab,
multiple-testing, validation floors, and candidate-pack eligibility without
weakening gates.
