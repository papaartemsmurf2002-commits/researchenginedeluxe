# Boundary and Command Contract

## Branch ownership

`research/v3-experimental-engine` owns research platform development. `live/v1-runtime-hardening` owns fail-closed runtime behavior.

## Research branch import rules

- `src/tradingbotsuite/research/**` must not import live order-placement adapters.
- The same forbidden import boundary applies to
  `src/tradingbotsuite/research_discovery/**`,
  `src/tradingbotsuite/research_cycle/**`,
  `src/tradingbotsuite/optimization/**`,
  `src/tradingbotsuite/research_artifacts/**`,
  `src/tradingbotsuite/data/**`, `src/tradingbotsuite/features/**`,
  `src/tradingbotsuite/backtesting/**`, and
  `src/tradingbotsuite/strategies/**`.
- Research modules must not import `tradingbotsuite.runtime`.
- Research modules must not import legacy live shells.
- Offline journal validation is allowed if it does not place, cancel, size, or supervise live orders.

## Command ownership

Research commands on this branch:

- `benchmark-discovery-run`
- `benchmark-historical-research-cycle`
- `benchmark-research-experiment`
- `build-historical-fixture-pack`
- `build-dataset`
- `calibrate-model`
- `collect-binance-bars`
- `collect-binance-context`
- `evaluate-discovery-candidate-pack-eligibility`
- `fetch-binance-vision`
- `fetch-crypto-lake`
- `monitor-hmm-knn`
- `plan-feature-ablation`
- `plan-stage12-research`
- `plan-stage13-readiness`
- `prepare-hmm-knn-research-data`
- `replay-eval`
- `replay-hmm-knn`
- `research`
- `research-hmm-knn`
- `run-discovery`
- `run-hmm-knn-experiments`
- `run-historical-research-cycle`
- `run-research-experiment`
- `train-model`
- `write-hmm-knn-sweep-datasets`

The installed canonical command is `tradingbotsuite`. The legacy
`tradingbot` console script remains compatibility-only for the older
Lorentzian Classification package and is not the active research workflow
entrypoint.

Live-adjacent commands and launchers on this branch are preserved but not research workflow steps:

- `serve`
- `manual`
- `smoke-live`
- `run_server.py`
- `run_manual.py`
- `run_live_smoke.py`

## Legacy source rule

Vendor-specific chart import, parity diagnostics, and source-script workflows must not return to the active research tree unless a future work packet explicitly reopens that scope.
