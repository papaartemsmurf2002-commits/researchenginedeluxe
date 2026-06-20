# Stage R106 Four-Bar Lead-Discovery Bridge Report

Date: 2026-06-09

Work packet: `docs/work_packets/WPR106-76-four-bar-lead-discovery-bridge.md`

Status: Completed as research-only, observe-only, and `promotion_ready: false`.
No candidate pack, paper/live artifact, live config, runtime-mode change, order
placement, sizing change, or promotion claim was created.

## Purpose

WPR106-75 was blocked by missing BTC/ETH four-bar HMM/KNN event-label datasets,
not by exit design. This packet built the smallest durable bridge needed for the
existing no-RSI KNN matrix specs:

- dense long/short events at signal close;
- four completed-bar fixed-hold labels;
- `event_end_time_ms`, `label_exit_time_ms`, and `purge_after_time_ms`;
- no-RSI close-path, range/wick, volatility-state, and aggTrade proxy features;
- explicit `missing_*` columns for unavailable book, funding, basis, premium,
  and open-interest context.

## Dataset Bridge

Added `build-four-bar-knn-dataset` as a registered research command. Live
preflight rejects it through the research-command registry, and the boundary
contract lists the command.

Full durable datasets were written from the active Binance Vision candidate-depth
fixture packs:

- BTCUSDT:
  `data/research/hmm_knn_four_bar/btcusdt_no_rsi_four_bar_dataset.parquet`
  with 554,864 rows, sha256
  `230a8f911c980e7cb598c5e046b3fb2a2700a78ef6f1f765058681ccfe8b1bc3`.
- ETHUSDT:
  `data/research/hmm_knn_four_bar/ethusdt_no_rsi_four_bar_dataset.parquet`
  with 554,864 rows, sha256
  `c64211c74dd0159fbe5b9d1d9a5333758a9f81706cd3a4759a71ffb98a3d94dd`.

Each full dataset contains 443,896 `15m -> 1h` rows and 110,968 `1h -> 4h`
rows. Sidecar manifests remain research-only and promotion-disabled.

For bounded matrix execution, deterministic evenly spaced compact datasets were
also generated from the same durable fixtures. The post-fix matrix runs used the
2k-per-interval datasets:

- BTCUSDT compact2k: 7,984 rows, sha256
  `eb06c1517d4aef55aa379564fc9581dcc8b16d835e27b920a31d0acf1c18cbf2`.
- ETHUSDT compact2k: 7,984 rows, sha256
  `4b58554e0893acdc9def1502ed492f7697af6afda00f3736f3c2e844fe426af5`.

## Runner Fixes

Two runner issues surfaced only after the durable rows existed:

- The original KNN distance path tried to allocate a full test-by-train-by-feature
  tensor. The first full BTC matrix attempt failed with a 1.12 TiB allocation.
  `_knn_predict` now evaluates distances in bounded batches without changing
  neighbor weighting, labels, scoring, or diagnostics.
- Explicitly missing `funding_rate` values were `NaN`. `_funding_cost` now treats
  non-finite funding rates as zero cost while preserving missingness flags.
  Before this fix, `expected_net_return_after_costs` became `NaN` and every KNN
  row failed acceptance.

Regression coverage was added for four-bar event-end semantics, dataset manifest
creation, horizon filtering, explicit purge metadata, batched artifact execution,
and missing funding context.

## Matrix Runs

The WPR106-75 BTC and ETH 18-row no-RSI matrix specs both ran post-fix on the
compact2k durable datasets:

- BTC output:
  `data/research/hmm_knn_four_bar/btcusdt_no_rsi_four_bar_compact2k_matrix_r106_v1`
  with 18/18 rows passed.
- ETH output:
  `data/research/hmm_knn_four_bar/ethusdt_no_rsi_four_bar_compact2k_matrix_r106_v1`
  with 18/18 rows passed.

Both matrix manifests are `research_only: true`, `observe_only: true`, and
`promotion_ready: false`.

Generated entry-quality analysis:

- `data/research/hmm_knn_four_bar/wpr106_76_four_bar_lead_analysis.json`
- `data/research/hmm_knn_four_bar/wpr106_76_four_bar_lead_analysis.csv`

## Entry Quality

Fixed four-bar same-entry holding was negative before selection:

- BTC `15m -> 1h`: 1,561 events, net -1.543111, PF 0.950011.
- BTC `1h -> 4h`: 1,561 events, net -1.516843, PF 0.950873.
- ETH `15m -> 1h`: 1,561 events, net -1.463179, PF 0.966049.
- ETH `1h -> 4h`: 1,561 events, net -1.439788, PF 0.966518.

This separates entry quality from exit quality: the four-bar exit is fixed and
negative on dense same-entry holding, while selected KNN/filter rows improved
entry quality.

Cleanest primary KNN lead:

- BTCUSDT `btc-1h-price-vol-flow-lorentzian-inverse-compatible`
  (`1h -> 4h`, no RSI, price/vol/aggTrade flow pack):
  290 trades, expectancy +0.003286, net +0.952940, PF 1.197370,
  3/4 positive split checks, at least 55 trades per split, cost-stress survival
  8/11, and max split PnL share 0.594908.

Strongest bounded sparse/top-score KNN/filter diagnostics:

- BTCUSDT `btc-15m-price-vol-flow-lorentzian-inverse-compatible`,
  top-score 50 per split:
  200 trades, expectancy +0.009870, net +1.974001, PF 1.776735,
  4/4 positive splits, 50 trades per split, cost stress 11/11, max split share
  0.477036.
- BTCUSDT same row, top-score 40 per split:
  160 trades, expectancy +0.011824, net +1.891904, PF 1.976646,
  4/4 positive splits, 40 trades per split, cost stress 11/11, max split share
  0.425227.
- ETHUSDT `eth-1h-price-path-lorentzian-uniform-same`,
  top-score 50 with aligned aggTrade flow:
  200 trades, expectancy +0.006643, net +1.328592, PF 1.330931,
  3/4 positive splits, 50 trades per split, cost stress 10/11, max split share
  0.596699.

Rows named `perp_context_no_rsi` are not evidence for funding, OI, premium, or
crowding because those fields are explicitly missing in the current fixtures.
They are treated as price/flow/missingness diagnostics only.

The transparent ETH `15m -> 1h` trend/vol baseline also passed compact gates:
215 trades, expectancy +0.010513, net +2.260278, PF 1.404019, 4/4 splits, and
cost stress 11/11. It repeats across matrix slugs because it is a baseline over
the same rows, not multiple independent discoveries.

Compared with WPR106-74, the BTC top-score KNN/filter rows are stronger compact
evidence than the earlier sparse BTC rows, which were aggregate-positive but
failed or only partially completed cost/split stress. This is still compact
sampled evidence, not validation-scale evidence.

## Decision

Choose **larger validation** as the next phase.

The next packet should scale only a narrow set of research-only rows:

- primary BTCUSDT `1h -> 4h` no-RSI `price_vol_flow_no_rsi` KNN;
- BTCUSDT `15m -> 1h` top-score KNN/filter over the Lorentzian price/vol/flow
  row;
- ETHUSDT `15m -> 1h` transparent trend/vol and aligned-flow top-score
  comparators as baselines, with duplicate-baseline accounting.

Do not move to OKX/Bybit venue intake yet. Current BTC/ETH Binance Vision
fixtures can answer the immediate question well enough to justify larger
validation. Venue intake remains the next route only if full validation breaks
the compact leads or if funding/OI/premium/crowding features become required.

## Validation

Passed:

- `python -m compileall -q src\tradingbotsuite`
- `python -m compileall -q src\tradingbotsuite\research\hmm_knn.py src\tradingbotsuite\research\knn_four_bar.py`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`: 449 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\live\test_cli_boundary.py tests\live\test_preflight.py -q`: 44 passed.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py -q`: 46 passed, with existing XGBoost/CuPy environment warnings.
- `$env:PYTHONPATH='src'; python -m pytest tests\tradingbotsuite\test_hmm_knn.py::test_funding_cost_treats_explicit_missing_context_as_zero tests\tradingbotsuite\test_hmm_knn.py::test_hmm_knn_research_writes_expected_research_only_artifacts tests\tradingbotsuite\test_hmm_knn.py::test_four_bar_dataset_builder_writes_research_only_dataset_and_manifest -q`
- `$env:PYTHONPATH='src'; python -m tradingbotsuite.main build-four-bar-knn-dataset --help`

## Research Boundary

All artifacts remain research-only, observe-only, and `promotion_ready: false`.
The results are lead-discovery evidence only. They are not live signals, not
candidate packs, not paper/live readiness, and not promotion claims.
