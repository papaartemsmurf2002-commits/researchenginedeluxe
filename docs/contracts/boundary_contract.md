# Boundary and Command Contract

## Branch ownership

`research/v3-experimental-engine` owns research platform development. `live/v1-runtime-hardening` owns fail-closed runtime behavior.

## Research branch import rules

- `src/tradingbotsuite/research/**` must not import live order-placement adapters.
- Research modules must not import `tradingbotsuite.runtime`.
- Research modules must not import legacy live shells.
- Offline journal validation is allowed if it does not place, cancel, size, or supervise live orders.

## Command ownership

Research commands on this branch:

- `build-dataset`
- `train-model`
- `calibrate-model`
- `replay-eval`
- `research-hmm-knn`
- `replay-hmm-knn`
- `monitor-hmm-knn`
- `run-hmm-knn-experiments`
- `write-hmm-knn-sweep-datasets`
- `collect-binance-bars`
- `fetch-binance-vision`
- `fetch-crypto-lake`
- `prepare-hmm-knn-research-data`
- `run-research-experiment`
- `benchmark-research-experiment`

Live-adjacent commands and launchers on this branch are preserved but not research workflow steps:

- `serve`
- `manual`
- `smoke-live`
- `run_server.py`
- `run_manual.py`
- `run_live_smoke.py`

## Legacy source rule

Vendor-specific chart import, parity diagnostics, and source-script workflows must not return to the active research tree unless a future work packet explicitly reopens that scope.
