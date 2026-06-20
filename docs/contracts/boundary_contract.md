# Boundary and Command Contract

## Branch ownership

`research/v3-experimental-engine` owns research platform development. `live/v1-runtime-hardening` owns fail-closed runtime behavior.

## Research branch import rules

- `src/tradingbotsuite/research/**` must not import live order-placement adapters.
- The same forbidden import boundary applies to
  `src/tradingbotsuite/research_sandbox/**`,
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

## Research Backtest Fill-Source Rule

- `signal_bar_close_plus_latency` is the compatibility source for signal-close
  entry pricing after latency-based entry-bar selection. It must not silently
  resolve to a primary bar open fill.
- Primary bar open latency fills must use `next_bar_open` or the explicit
  `primary_bar_open_plus_latency` source name.
- Research manifests must keep these semantics visible through fill-profile
  metadata: `signal_close_latency_fill` for signal-close compatibility fills
  and `primary_bar_latency_fill` for primary-open latency fills.
- These fill-source labels are research backtest assumptions only. They are not
  live or paper execution proof, sizing instructions, order-placement
  instructions, promotion authority, or candidate-pack authorization.

## Command ownership

Research commands on this branch:

- `analyze-research-delta`
- `analyze-research-results`
- `audit-rapid-strategy-sandbox-archives`
- `benchmark-discovery-run`
- `benchmark-hardware-utilization`
- `benchmark-historical-research-cycle`
- `benchmark-research-experiment`
- `build-historical-fixture-pack`
- `build-four-bar-knn-dataset`
- `build-rapid-strategy-sandbox-archive-manifest`
- `build-rapid-strategy-sandbox-strategy-catalog`
- `build-dataset`
- `calibrate-model`
- `collect-binance-bars`
- `collect-binance-context`
- `collect-durable-data`
- `evaluate-discovery-candidate-pack-eligibility`
- `export-rapid-strategy-sandbox-venue-expansion-candidate-manifest`
- `export-rapid-strategy-sandbox-venue-expansion-requests`
- `export-rapid-strategy-sandbox-validation-requests`
- `fetch-binance-vision`
- `fetch-crypto-lake`
- `index-rapid-strategy-sandbox-artifacts`
- `index-rapid-strategy-sandbox-iterations`
- `materialize-rapid-strategy-sandbox-venue-expansion-requests`
- `map-binance-archive-four-bar-datasets`
- `monitor-hmm-knn`
- `plan-feature-ablation`
- `plan-stage12-research`
- `plan-stage13-readiness`
- `preflight-rapid-strategy-sandbox`
- `preflight-rapid-strategy-sandbox-validation-requests`
- `prepare-hmm-knn-research-data`
- `rank-rapid-strategy-sandbox-artifacts`
- `refresh-historical-data-catalog`
- `replay-eval`
- `replay-hmm-knn`
- `research`
- `research-hmm-knn`
- `run-discovery`
- `run-frozen-entry-exit-lab`
- `run-four-bar-knn-larger-validation`
- `run-hmm-knn-experiments`
- `run-historical-research-cycle`
- `run-rapid-strategy-sandbox`
- `run-rapid-strategy-sandbox-iteration`
- `run-rapid-strategy-sandbox-suite`
- `run-research-autopilot`
- `run-research-experiment`
- `show-rapid-strategy-sandbox-next-action`
- `summarize-rapid-strategy-sandbox-archive-coverage`
- `summarize-rapid-strategy-sandbox-hypotheses`
- `summarize-rapid-strategy-sandbox`
- `summarize-rapid-strategy-sandbox-throughput`
- `train-model`
- `verify-rapid-strategy-sandbox-artifacts`
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
