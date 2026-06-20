# Stage R106 Fast Entry Filter Exit Research Report

Date: 2026-06-07

Work packet: `docs/work_packets/WPR106-71-fast-entry-filter-exit-research.md`

## Boundary

This packet stayed research-only, observe-only, and promotion-disabled. No
candidate pack, live or paper runtime setting, order adapter, sizing policy, or
promotion artifact was changed. The fast latest-window outputs below are
diagnostic screens only and are not candidate-ready evidence.

## External Math And Logic Crosscheck

The requested "100 percent correct" standard is not something this packet can
truthfully certify. The useful standard here is a bounded logic audit plus
reproducible evidence and fail-closed blockers.

Checked references used to steer this phase:

- scikit-learn nearest-neighbor documentation confirms that KNN behavior depends
  heavily on neighbor count, distance metric, dimensionality, and search
  backend; brute force nearest-neighbor scaling can become expensive quickly:
  https://scikit-learn.org/stable/modules/neighbors.html and
  https://scikit-learn.org/1.0/modules/generated/sklearn.neighbors.KNeighborsClassifier.html
- scikit-learn `TimeSeriesSplit` documents ordered time-series splitting and a
  gap parameter, supporting the branch emphasis on purge and embargo style
  validation rather than random shuffling:
  https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- hmmlearn documents HMMs as unsupervised latent-state learning and inference,
  matching the branch rule that HMM-style regime claims require actual HMM
  backend evidence and no-regime baselines:
  https://hmmlearn.readthedocs.io/en/stable/
- Wiley's page for Lopez de Prado, `Advances in Financial Machine Learning`,
  supports the packet's use of triple-barrier and purged-validation concepts as
  research validation patterns:
  https://www.wiley-vch.de/en/areas-interest/finance-economics-law/finance-investments-13fi/finance-investments-special-topics-13fiz/advances-in-financial-machine-learning-978-1-119-48208-6
- Binance official derivative market-data docs confirm that funding rate,
  premium/mark-price, and open-interest statistics are separate context
  surfaces, so context exits must preserve those columns explicitly:
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History,
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price, and
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics

The subagent review split the next-step logic:

- McClintock: KNN replay is only worth another pass if entries are thinned first;
  the previous dense KNN replay produced roughly 970k BTC and 958k ETH signals
  and fixed/simple exits collapsed to negative results.
- Darwin: frozen-entry exit labs are the right mechanism for separating entry
  model quality from exit model quality; compact fixed/simple/trailing/barrier
  and hard-stop exits are enough for the next fast screen.

## Experiments

### Durable public archive fast exit probe

Configs:

- `configs/research/fast_exit_probe_btcusdt_r106_v1.json`
- `configs/research/fast_exit_probe_ethusdt_r106_v1.json`

Outputs:

- `data/research/historical_cycles/fast_exit_probe_btcusdt_r106_v1`
- `data/research/historical_cycles/fast_exit_probe_ethusdt_r106_v1`

Both symbols wrote 136 ranked rows and 181 backtest-index rows, but total trade
count was zero. The feature build contained only 32 primary rows and key rolling
features such as `atr`, `atr_percentile`, `choppiness`,
`directional_slope_atr`, `path_zscore_20`, and
`volatility_shock_zscore` had 100 percent missingness. This is not an
actionable optimization surface; it is a fixture density limitation for this
specific fast probe.

### Frozen-entry KNN sparse exit labs

Inputs were sliced from the prior WPR106 replay entry signals and tested with a
compact exit grid. The first dense top-3 replay attempt was stopped after
exceeding fast-loop runtime, so two cooldown slices were used instead.

Outputs:

- `data/research/operator_runs/r106_71_frozen_entry_exit_micro_lab_btcusdt_v1`
- `data/research/operator_runs/r106_71_frozen_entry_exit_micro_lab_ethusdt_v1`

Results:

| Symbol and slice | Rows | Positive rows | Gate result | Best net result |
| --- | ---: | ---: | --- | ---: |
| BTC 24h cooldown, 512 max per candidate | 24 | 0 | 1 passed, 2 blocked | -0.538425 |
| ETH 24h cooldown, 512 max per candidate | 24 | 0 | 3 passed, 0 blocked | -0.554497 |
| BTC 72h cooldown, 256 max per candidate | 24 | 0 | 3 passed, 0 blocked | -0.358336 |
| ETH 72h cooldown, 256 max per candidate | 24 | 0 | 2 passed, 1 blocked | -0.310350 |

The KNN exit labs show small improvements over fixed hold in some rows, mostly
from `max_mae_stop` and `simple_runner_v1`, but all best net results remain
deeply negative. KNN should not receive large-compute optimization yet unless a
new entry selector materially reduces bad events before exit optimization.

### Latest-window fast filter and exit probes

Configs:

- `configs/research/fast_filter_probe_btcusdt_r106_v1.json`
- `configs/research/fast_filter_probe_ethusdt_r106_v1.json`

Outputs:

- `data/research/historical_cycles/fast_filter_probe_btcusdt_r106_v1`
- `data/research/historical_cycles/fast_filter_probe_ethusdt_r106_v1`

These use latest-window context fixtures and are diagnostic only. They are
useful for finding research directions, not for candidate claims.

BTC summary:

- 222 ranked rows, 54 positive rows, 5,109 total trades after restoring
  `funding_aware_exit_v1`.
- Best result: `volatility_breakout_v1`, `features_price_trend_vol`, 72h,
  `simple_runner_v1`, params
  `{"atr_percentile_threshold":0.25,"shock_threshold":0.7,"spacing_bars":8}`,
  30 trades, net 0.140613, expectancy 0.004471, profit factor 2.882972.
- Same entry with trailing exit was also positive: 25 trades, net 0.101481,
  expectancy 0.003942.
- Best horizon was 72h by best net; 72h also had the least negative mean net
  of the tested horizons.
- Best fixed-vs-treatment delta was the same volatility breakout 72h
  simple-runner row: treatment 0.140613 versus fixed 0.052648, delta 0.087966.
- `funding_aware_exit_v1` wrote 37 rows, 9 positive rows, and 13 blocked rows.
  The blocked rows were all `features_price_trend_vol` candidates without
  funding context. The best executed funding-aware BTC row was 0.038542 net.

ETH summary:

- 222 ranked rows, 43 positive rows, 5,184 total trades after restoring
  `funding_aware_exit_v1`.
- Best result: `trend_following_v1`, `features_price_trend_vol`, 24h,
  `simple_runner_v1`, params
  `{"funding_penalty_threshold":0.00025,"max_choppiness":58.0,"slope_threshold":0.12,"spacing_bars":12}`,
  57 trades, net 0.313310, expectancy 0.004892, profit factor 2.703250.
- The 72h trend row with `simple_runner_v1` was also strong: 40 trades, net
  0.216966, expectancy 0.005031, profit factor 3.027659.
- The same 24h and 72h entries remained positive under
  `trailing_atr_after_profit`.
- Best horizon by net was 24h, while 72h had the best mean net among horizons.
- Best fixed-vs-treatment delta was ETH trend 24h simple runner: treatment
  0.313310 versus fixed -0.167727, delta 0.481037.
- `funding_aware_exit_v1` wrote 37 rows, 6 positive rows, and 13 blocked rows.
  The best executed funding-aware ETH row was `funding_crowding_fade_v2`, 72h,
  8 trades, net 0.104650. It was close to, but did not beat, the same entry
  under fixed holding at 0.110259.

## Blocker Fixed

Added and resolved `ISSUE-R106-021` in `docs/KNOWN_ISSUES.md`.

Context exits such as `funding_aware_exit_v1` can crash a whole fast cycle when
raw context columns such as `funding_rate` are not preserved into the execution
frame. Both BTC and ETH fast-filter probes initially failed this way. The runner
now catches context-exit column gaps for configured context exits and writes a
blocked candidate-level backtest artifact instead of stopping the cycle. The
execution market frame also preserves the `last_funding_rate` alias.

Post-fix BTC/ETH reruns restored `funding_aware_exit_v1`; both cycles completed.
Each symbol wrote 13 blocked aggregate rows for price-feature funding-aware
candidates without funding context, while perp-context funding-aware candidates
executed normally.

## Decisions

- Do not spend large compute on the current dense or cooldown-thinned KNN replay
  entries. The exit model improves loss shape, not profitability.
- Next large-compute candidate for durable validation: ETH `trend_following_v1`
  with 24h and 72h horizons, `simple_runner_v1` and
  `trailing_atr_after_profit`.
- Next BTC candidate: `volatility_breakout_v1` at 72h with `simple_runner_v1`
  and `trailing_atr_after_profit`.
- Secondary context direction: funding crowding and perp-basis strategies are
  interesting but low sample in this diagnostic window. Funding-aware exits now
  execute or block per candidate, but the best ETH funding-aware row did not
  beat fixed holding on the same entry.
- CUDA was not used in this packet because the active comparison needed rich
  exit policies and frozen-entry labs, while the existing CUDA path is scoped to
  fixed-holding research backtests. No GPU speedup claim is made.

## Validation

- `python -m compileall -q src/tradingbotsuite` passed.
- Focused regressions passed:
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts/test_backtest_contracts.py::test_backtest_market_frame_preserves_last_funding_rate_alias tests/historical/test_full_cycle_synthetic.py::test_full_cycle_context_exit_missing_columns_blocks_candidate_not_cycle -q`.
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` passed with
  443 tests.
- `git diff --check` returned no whitespace errors; PowerShell reported only
  CRLF warnings from the already dirty worktree.

## Next Phase

1. Run durable multi-window validation for ETH trend 24h/72h simple/trailing
   and BTC volatility breakout 72h simple/trailing.
2. If context strategies remain in scope, rerun funding crowding and perp-basis
   with larger durable/context evidence and compare funding-aware exits against
   fixed, simple runner, and trailing exits.
3. If KNN continues, add a sparse-event selector before exit labs: rolling
   top-score gating, side-balance caps, and overlap cooldowns should be tested
   before any large KNN optimization.
