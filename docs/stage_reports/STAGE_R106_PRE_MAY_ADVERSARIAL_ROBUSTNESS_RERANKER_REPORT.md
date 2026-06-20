# Stage R106 Pre-May Adversarial Robustness Reranker Report

Date: 2026-06-11
Packet: WPR106-120
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all reranking-feature design, objective scoring,
selection, deduplication, and policy choice. May source trades were loaded only
after the fixed pre-May selection table was written.

## Method

The runner
`data/research/wpr106_120_pre_may_adversarial_robustness_reranker/scripts/run_wpr106_120_pre_may_adversarial_robustness_reranker.py`
reads the full WPR106-119 pre-May diversity portfolio replay ranking and
reranks it with pre-May-only robustness objectives. It then uses the
WPR106-118/WPR106-119 trade-level replay helper to materialize fixed selected
pre-May rows and benchmark May.

Input universe:

- `data/research/wpr106_119_diversity_constrained_cross_family_replay/pre_may/diversity_portfolio_replay_ranking.parquet`
- 3,640 WPR106-119 replay rows.
- 254 rows passed the WPR106-120 base pre-May filter.

Base pre-May filter:

- annual loss target passed;
- positive total pre-May return;
- at least 120 trades;
- at least 24 active months;
- no more than 5 losing months;
- 0.35 to 5.0 trades per active day;
- max drawdown above -0.25;
- cost-stress survival at least 0.75;
- best-month share at most 0.45;
- no more than one rolling losing block;
- at least two source packets, three source families, and three source
  buckets;
- at most one ETH lead-anchor source;
- at least one support bucket source.

Objective families:

- `adversarial_block_floor`
- `anti_archetype_concentration`
- `recent_balance`
- `low_drawdown_cost`
- `trade_quality_stability`

The objectives used only pre-May replay metrics and source metadata:
rolling-block floors, recent/early block balance, drawdown, downside risk,
cost-stress totals, best-month concentration, member/source concentration,
BTC weight, ETH lead-anchor weight, ETH dense weight, skip pressure, day-cap
pressure, active days, expectancy, and active trade rate.

## Artifacts

Root:
`data/research/wpr106_120_pre_may_adversarial_robustness_reranker/`

Key outputs:

- `wpr106_120_pre_may_adversarial_robustness_reranker_summary.json`
- `wpr106_120_runner.log`
- `pre_may/wpr106_119_replay_universe_scored.parquet`
- `pre_may/base_candidate_scored_universe.parquet`
- `pre_may/base_candidate_scored_universe_top2000.csv`
- `pre_may/objective_scores.parquet`
- `pre_may/objective_scores_top2000.csv`
- `pre_may/selected_pre_may.parquet`
- `pre_may/selected_pre_may_replay_metrics.parquet`
- `pre_may/selected_pre_may_monthly_returns.parquet`
- `pre_may/selected_pre_may_daily_returns.parquet`
- `pre_may/selected_pre_may_trades.parquet`
- `may_benchmark/selected_may_benchmark_metrics.parquet`
- `may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `may_benchmark/selected_may_benchmark_trades.parquet`

## Pre-May Results

The selected set contains 80 strict-adversarial rows:

- 40 selected portfolio IDs overlap WPR106-119 selected IDs.
- 40 selected portfolio IDs are new versus WPR106-119.
- 60 selected member sets overlap WPR106-119 selected member sets.
- 20 selected member sets are new versus WPR106-119.

Selected pre-May diagnostics:

- Total pre-May net return: +0.451962 to +0.880990, median +0.660023.
- Trades: 522 to 1,241, median 831.5.
- Active months: 28 for every selected row.
- Active days: 472 to 772.
- Trades per active day: 1.000 to 1.608.
- Losing months: 3 to 5.
- Annual loss counts stayed within the target: 2024 max 2, 2025 max 2,
  2026 Jan-Apr max 1.
- Best-month share: 0.089743 to 0.255956.
- Max drawdown: -0.045107 to -0.120667.
- Cost-stress survival: 1.0 for every selected row.
- Rolling losing blocks: 0 to 1.
- Block minimum return: -0.047722 to +0.077528.
- Recent two-block return: +0.087706 to +0.261574.

Concentration diagnostics showed the reranker still leaned heavily on the same
source shape:

- BTC weight: 0.119792 to 0.400000, median 0.139188.
- ETH lead-anchor weight: 0.250000 to 0.414972, median 0.400443.
- ETH dense weight: 0.000000 to 0.476749, median 0.227141.
- Top weighted source share: 0.366487 to 0.646748, median 0.561819.

Overlap/day-cap controls were active:

- Skip pressure: 0.180288 to 0.560268, median 0.283249.
- Day-cap pressure: 0.000000 to 0.535714, median 0.003521.

## May Benchmark

May 2026 benchmark was run only after fixed pre-May selection:

- May-positive selected rows: 8
- May-negative selected rows: 72
- May-flat selected rows: 0
- Best May return: +0.009587
- Worst May return: -0.061829
- Median May return: -0.029856
- Mean May return: -0.027010
- May trade count range: 17 to 47
- May active-day range: 17 to 28
- May trades per active day: 1.000 to 1.741
- Median May cost-stress survival: 0.0

Overlap with WPR106-119 mattered:

- The 40 selected rows with the same WPR106-119 portfolio ID had 3 positive
  and 37 negative May rows, with median May -0.026018.
- The 40 new portfolio IDs had 5 positive and 35 negative May rows, with
  median May -0.035855.
- The 60 selected rows whose member sets overlapped WPR106-119 had 8 positive
  and 52 negative May rows, with median May -0.026690.
- The 20 genuinely new member sets were all May-negative, with median May
  -0.036047 and worst May -0.061829.

Objective-level May diagnostics:

- `adversarial_block_floor`: 5 positive, 11 negative, median -0.025024.
- `anti_archetype_concentration`: 2 positive, 22 negative, median -0.031148.
- `recent_balance`: 5 positive, 33 negative, median -0.028818.
- `low_drawdown_cost`: 7 positive, 49 negative, median -0.026339.
- `trade_quality_stability`: 8 positive, 70 negative, median -0.030545.

Weighted May contribution by packet/family/symbol remained dominated by the
same failing ETH lead-lag core:

- WPR106-108 single_leg_lead_lag ETHUSDT: -0.816702
- WPR106-106 flow_follow ETHUSDT: -0.233729
- WPR106-106 balanced ETHUSDT: -0.203574
- WPR106-107 rolling_knn ETHUSDT: -0.182819
- WPR106-106 balanced BTCUSDT: -0.177896
- WPR106-106 session_drift ETHUSDT: -0.158379
- WPR106-106 wick_fade ETHUSDT: +0.010769
- WPR106-109 prior_day_range BTCUSDT: +0.005670
- WPR106-115 range BTCUSDT: +0.003503

## Decision

This packet rejects the WPR106-120 pre-May adversarial robustness reranker as
candidate-ready evidence. The reranker did identify several May-positive rows
without using May, but the May-positive count stayed at 8 while the selected
set grew to 80 rows, the median May return worsened versus WPR106-119, and all
20 genuinely new member sets were May-negative.

The result is useful negative evidence: stronger pre-May block, drawdown, cost,
trade-quality, and concentration objectives still did not discover a new
holdout-stable archetype inside the WPR106-119 diversity universe. Future work
should stop trying to rescue this portfolio universe by reranking alone and
move to a genuinely new source family, feature construction, exit mechanism,
or model search.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_120_pre_may_adversarial_robustness_reranker/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
