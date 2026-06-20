# STAGE R106 Strategy Math Audit And Fast Research Nodes Report

Date: 2026-06-07

Work packet: `docs/work_packets/WPR106-70-strategy-math-audit-and-fast-research-nodes.md`

## Boundary

This work stayed research-only. No candidate pack was written, no promotion
state was changed, and no live, paper, order-placement, sizing, or runtime-mode
path was edited.

## Subagent Findings Used

Two read-only subagents were used for the next phase:

- Strategy audit: found no P0 live-boundary issue, but identified three P1
  correctness risks: latency entry pricing used signal close instead of the
  latency-observable bar, funding costs ignored `perp_last_funding_rate`, and
  `range_reversion_v1` fabricated a side when no real stretch existed.
- Fast-node design: recommended config-only exploratory nodes, direct
  `run_discovery`, small trial budgets, `1h` cosine KNN emphasis, and keeping
  exploratory run IDs away from exact gate evidence.

P2 follow-ups from the audit were logged in `docs/KNOWN_ISSUES.md` as
`ISSUE-R106-020` instead of expanding this packet into a broad rewrite.

## External Reference Check

Primary sources checked:

- Binance USD-M Futures funding-rate history documents `fundingRate`,
  `fundingTime`, and `markPrice` fields for historical funding evidence:
  <https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History>
- Binance USD-M Futures mark-price/premium-index documents `markPrice`,
  `indexPrice`, `lastFundingRate`, `interestRate`, and `nextFundingTime`:
  <https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price>
- Binance open-interest stats document public archive-style OI fields and
  limited retention, which supports treating current OI context as research
  evidence with explicit coverage limits:
  <https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics>
- scikit-learn `TimeSeriesSplit` keeps samples time ordered and supports a
  `gap`, matching the local direction for leakage-aware validation:
  <https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html>
- scikit-learn nearest-neighbor APIs support metric selection, including cosine
  distance usage through the nearest-neighbor stack:
  <https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.NearestNeighbors.html>
- scikit-learn `GaussianMixture` and hmmlearn `GaussianHMM` references support
  keeping the local distinction between GMM-style regime clustering and true
  HMM state modeling explicit:
  <https://scikit-learn.org/stable/modules/generated/sklearn.mixture.GaussianMixture.html>
  and <https://hmmlearn.readthedocs.io/en/latest/api.html#hmmlearn.hmm.GaussianHMM>

The external check supports the scoped fixes below. It does not establish a
formal proof that every strategy is economically correct; it reduces concrete
math/data-interface mistakes to tested code paths and records remaining risks.

## Correctness Fixes

- `signal_bar_close_plus_latency` now prices entry at the latency bar open
  instead of the signal close. The fill profile now labels this as a primary-bar
  latency fill.
- Funding-cost lookup now accepts `funding_rate`, `perp_last_funding_rate`, and
  `last_funding_rate`, ignoring missing, invalid, and non-finite values.
- Reference, vector, CUDA, and batched CUDA backtest paths now use the same
  funding-rate alias helper.
- `range_reversion_v1` no longer invents alternating long/short sides when
  both path z-score and directional slope are absent. If `path_zscore_20` is
  unavailable or below threshold, it may use real `directional_slope_atr` with
  a configurable `slope_stretch_threshold` defaulting to
  `min(stretch_threshold, 0.04)`.

## Fast Research Nodes

Six exploratory configs were added:

- `configs/discovery/fast_iter_knn_1h_btcusdt_v1.json`
- `configs/discovery/fast_iter_knn_1h_ethusdt_v1.json`
- `configs/discovery/fast_iter_knn_microdrift_1h_btcusdt_v1.json`
- `configs/discovery/fast_iter_knn_microdrift_1h_ethusdt_v1.json`
- `configs/discovery/fast_iter_knn_selective_1h_btcusdt_v1.json`
- `configs/discovery/fast_iter_knn_selective_1h_ethusdt_v1.json`

All use thread execution for these tiny Windows-launched probes. A direct
process-pool launch from stdin failed because child processes attempted to
reload `<stdin>`, so the broken generated BTC attempt was removed and the configs
were switched to thread executor. File-backed/operator runs can still use
process workers where appropriate.

## Probe Results

All run artifacts are under `data/research/discovery_runs/` and are
research-only, observe-only, and promotion-disabled.

| Run family | Symbol | Trials | Failed | Interesting | Blocked | Wall seconds | Main blockers |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| sampled | BTCUSDT | 32 | 0 | 0 | 32 | 1.342 | near ceiling, low independent events, feature preflight, negative expectancy |
| sampled | ETHUSDT | 32 | 0 | 0 | 32 | 1.295 | low independent events, feature preflight, high overlap |
| microdrift | BTCUSDT | 24 | 0 | 0 | 24 | 2.216 | signal rate above ceiling |
| microdrift | ETHUSDT | 24 | 0 | 0 | 24 | 1.815 | signal rate above ceiling |
| selective | BTCUSDT | 48 | 0 | 0 | 48 | 3.364 | signal rate above ceiling |
| selective | ETHUSDT | 48 | 0 | 0 | 48 | 2.839 | signal rate above ceiling |

Total successful exploratory trials: 208.
Total successful discovery wall time: about 13.77 seconds.

The initial sampled nodes found the rough tension:

- BTCUSDT: signal-rate blockers and negative expectancy dominated. The
  `alternative_non_wt_price_state` feature set also failed finite-column
  preflight and should be removed from future fast KNN probes.
- ETHUSDT: most settings were too sparse, with low independent-event count and
  no useful positive pocket.

The microdrift and selective nodes raised probability, EV, agreement, and vote
margin thresholds. That drift made the issue clearer rather than better:

- BTCUSDT selective: signal rate ranged from `0.3125` to `0.5`, overlap ratio
  from `0.666667` to `0.733333`, side collapse was `1.0` for every candidate,
  and realized expectancy ranged from `-0.034404` to `-0.004468`.
- ETHUSDT selective: signal rate ranged from `0.3125` to `0.375`, overlap ratio
  from `0.636364` to `0.7`, side collapse was `1.0` for every candidate, and
  realized expectancy ranged from `-0.085192` to `-0.065739`.

## Decision

There is no trend here that deserves a larger KNN threshold-only optimization.
The easy way forward is not more trials on the same surface; it is adding an
explicit sparse-event construction layer before scaling:

- cooldown or rolling top-score selection after KNN acceptance,
- side-balance constraints so one-sided collapse is visible before scoring,
- event-rate scoring that emphasizes independent events over accepted-bar
  density,
- then rerun a 24 to 48 trial exact fast node before any large experiment.

The most promising next large-scale candidate would be a sparse-event KNN probe
or a separate context/perp retest, not the current 1h cosine threshold drift.

## Validation

Commands run:

- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/research_discovery/test_discovery_spec.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/unit/test_execution_simulator.py::test_signal_bar_close_plus_latency_uses_latency_bar_open_not_signal_close tests/unit/test_execution_simulator.py::test_execution_simulator_uses_perp_last_funding_rate_alias_for_costs tests/contracts/test_strategy_contracts.py::test_range_reversion_does_not_fabricate_side_when_stretch_is_absent -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/backtesting/test_vector_engine_matches_reference.py::test_cuda_fixed_holding_matches_reference_with_fake_cupy tests/backtesting/test_cuda_batched_fixed_holding.py::test_cuda_batched_fixed_holding_matches_reference_vector_and_r96_with_fake_cupy -q`
- `git diff --check`

Results:

- Compile: passed.
- Contract baseline: `442 passed`.
- Discovery spec tests: `18 passed`.
- Focused correctness tests: `3 passed`.
- Backtest parity tests: `11 passed`.
- Diff check: no whitespace errors; only existing CRLF normalization warnings.
