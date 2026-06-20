# Stage R106 KNN Annual-Target Coverage Expansion Report

Date: 2026-06-11
Packet: WPR106-117
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of source-row selection, threshold/query/session/regime
expansion, ranking, and fixed selection. It was loaded only after selected
pre-May rows were fixed.

## Method

The runner
`data/research/wpr106_117_knn_annual_target_coverage_expansion/scripts/run_wpr106_117_knn_annual_target_coverage_expansion.py`
uses WPR106-116 ranking artifacts to choose source neighborhoods, then
recomputes causal Lorentzian KNN scores from the WPR106-96 BTCUSDT and ETHUSDT
15m feature frames.

Source-row rule:

- Start from WPR106-116 rows with positive pre-May return and annual loss
  target of at most 2 losing months in 2024, 2 in 2025, and 1 in 2026 Jan-Apr.
- Prefer rows with at least 40 trades and at least 10 active months.
- Sort by active months, trade count, pre-May return, and source ranking score.
- Keep the top source rows within each
  symbol/feature-pack/lookback/neighbors/horizon/side neighborhood.

The resulting 20 source rows were expanded across threshold multipliers,
query spacing of 4 and 8 bars, original plus neighboring session/regime
filters, and max-trades/day caps of 1, 2, and 4. Neighbor labels remained
causal: each neighbor's label had to be completed before the query signal.

## Artifacts

Root:
`data/research/wpr106_117_knn_annual_target_coverage_expansion/`

Key outputs:

- `wpr106_117_knn_annual_target_coverage_expansion_summary.json`
- `wpr106_117_runner.log`
- `pre_may/source_annual_target_rows.parquet`
- `pre_may/coverage_expansion_ranking.parquet`
- `pre_may/coverage_expansion_top2000.csv`
- `pre_may/selected_pre_may.parquet`
- `pre_may/selected_pre_may_replay_metrics.parquet`
- `pre_may/selected_pre_may_monthly_returns.parquet`
- `pre_may/selected_pre_may_daily_returns.parquet`
- `pre_may/selected_pre_may_trades.parquet`
- `may_benchmark/selected_may_benchmark_metrics.parquet`
- `may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `may_benchmark/selected_may_benchmark_trades.parquet`

## Results

Pre-May expansion:

- Source rows: 20
- Expanded rows: 4,320
- Positive pre-May rows: 1,804
- Annual-target rows: 210
- Coverage-loose rows: 36
- Coverage-strict rows: 0
- Selected rows: 27
- Selection tier: coverage-loose

Coverage-loose rows by family:

- BTCUSDT trend_pullback_state: 18
- ETHUSDT trend_pullback_state: 9
- ETHUSDT price_path_vol: 9

The strict gate failed because no annual-target row reached 20 active pre-May
months. Nine ETHUSDT trend_pullback_state rows passed every other strict
condition, with +0.304182 total pre-May net return, 86 trades, 18 active
months, five losing months, max drawdown -0.127323, best-month share 0.421685,
one rolling losing block, and full cost-stress survival.

## Selected Clusters

The 27 selected rows collapse to 9 parameter clusters and 3 practical
archetypes:

- BTCUSDT trend_pullback_state, long, all sessions, high-vol regime,
  threshold multiplier 1.15, max 1/2/4 trades per day: +0.223524 to +0.227545
  pre-May, 90 to 105 trades, 17 active months, 5 losing months, max drawdown
  from -0.097361 to -0.105438, best-month share from 0.445303 to 0.468685.
- ETHUSDT trend_pullback_state, long, Asia session, all regimes, threshold
  multiplier 1.00, max 1/2/4 trades per day: +0.304182 pre-May, 86 trades, 18
  active months, 5 losing months, max drawdown -0.127323, best-month share
  0.421685.
- ETHUSDT price_path_vol, short, US session, trend regime, threshold
  multiplier 1.00, max 1/2/4 trades per day: +0.169168 to +0.180604 pre-May,
  69 to 70 trades, 18 active months, 4 losing months, max drawdown -0.109096,
  best-month share from 0.419192 to 0.447528.

All selected rows preserved annual loss counts at 2024 <= 2, 2025 <= 2, and
2026 Jan-Apr <= 1. Selected rows had full cost-stress survival pre-May and
roughly one trade per active day after overlap and day-cap handling.

## May Benchmark

May 2026 benchmark was run only after fixed pre-May selection:

- May-positive selected rows: 9
- May-negative selected rows: 0
- May-flat selected rows: 18
- Best May return: +0.000777
- Worst May return: 0.000000

All May-positive rows were the ETHUSDT price_path_vol short archetype and each
had one May trade. The BTCUSDT and ETHUSDT trend_pullback_state selected rows
were flat in May. The lack of May losses is favorable, but the low May activity
is not enough to treat this as robust holdout confirmation.

## Decision

WPR106-117 improves the WPR106-116 KNN annual-target neighborhood by recovering
active-ish rows with 69 to 105 pre-May trades, 17 to 18 active months, annual
loss targets satisfied, full cost-stress survival, and no negative selected
May benchmark rows. It is still not candidate-ready because the strict
20-active-month target was not reached, the selected set is concentrated in a
small number of neighborhoods, and May benchmark activity was sparse.

The KNN family should remain in the broader research search, but future work
should focus on expanding active-month coverage without relaxing the annual
loss target, deduplicating equivalent source-neighborhood behavior, and testing
whether orthogonal feature packs or ensemble overlays can add activity in the
inactive months without introducing May-tuned selection.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_117_knn_annual_target_coverage_expansion/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
