# Stage R106 Cross-Family Loss-Complement Ensemble Search Report

Date: 2026-06-11
Packet: WPR106-118
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all source filtering, source deduplication,
combination screening, portfolio replay policy selection, ranking, and fixed
selection. It was loaded only after selected pre-May portfolios were fixed.

## Method

The runner
`data/research/wpr106_118_cross_family_loss_complement_ensemble_search/scripts/run_wpr106_118_cross_family_loss_complement_ensemble_search.py`
normalizes compatible selected trade streams from recent 2024-forward
research packets, computes pre-May source metrics, deduplicates by monthly
behavior, screens cross-family combinations by loss-month complementarity, then
replays the strongest combinations at trade level.

Loaded direct source packets:

- WPR106-105 causal barpath/flow exits
- WPR106-106 dense causal score search
- WPR106-107 rolling Lorentzian KNN
- WPR106-108 cross-asset relative value and lead-lag
- WPR106-109 session anchor intraday
- WPR106-111 1m aggTrade flow microstructure
- WPR106-112 1m path-managed exits
- WPR106-115 regime-switch intraday
- WPR106-116 walk-forward Lorentzian KNN
- WPR106-117 KNN annual-target coverage expansion

Excluded:

- WPR106-110, because it has monthly meta-policy output but no trade-level
  stream.
- WPR106-113 and WPR106-114, because they are already portfolio replays and
  would create recursive portfolio-of-portfolio accounting.

Replay controls:

- same-symbol overlap blocking;
- max concurrent positions of 1, 2, or 4;
- max trades/day caps of 1, 2, or 4;
- optional entry-day loss/profit guards;
- equal and source-score-weighted member weights;
- cost-stress recomputation from accepted weighted gross returns and weighted
  round-trip costs.

## Artifacts

Root:
`data/research/wpr106_118_cross_family_loss_complement_ensemble_search/`

Key outputs:

- `wpr106_118_cross_family_loss_complement_ensemble_summary.json`
- `wpr106_118_runner.log`
- `pre_may/source_manifest.parquet`
- `pre_may/source_metrics.parquet`
- `pre_may/source_monthly_returns.parquet`
- `pre_may/source_pool.parquet`
- `pre_may/monthly_screen_ranking.parquet`
- `pre_may/monthly_screen_top2000.csv`
- `pre_may/portfolio_replay_ranking.parquet`
- `pre_may/portfolio_replay_top2000.csv`
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

Loaded evidence:

- Pre-May trade rows loaded: 185,714
- May trade rows loaded: 6,028
- Source metric rows: 893
- Source pool rows after filtering/deduplication: 96
- Monthly-screen rows: 57,060
- Trade-level portfolio replay rows: 2,940

Pre-May replay results:

- Positive rows: 2,940
- Annual-target rows: 203
- Loose rows: 203
- Strict rows: 202
- Selected rows: 40
- Selection tier: strict

Strict rows were strong by the pre-May objective: selected rows had 28 active
months, 402 to 643 trades, 3 to 5 losing months, full cost-stress survival,
max drawdown from -0.040682 to -0.107574, and best-month share from 0.084027
to 0.207375. The selected active rate was roughly one trade per active day.

## Composition

The selected strict set was much narrower than the source pool:

- WPR106-108 single_leg_lead_lag ETHUSDT: 69 selected member slots, 8 unique
  source candidates.
- WPR106-109 prior_day_range ETHUSDT: 45 slots, 7 unique source candidates.
- WPR106-106 volatility_breakout ETHUSDT: 26 slots, 1 unique source candidate.
- WPR106-109 session_range ETHUSDT: 11 slots, 2 unique source candidates.
- WPR106-109 opening_range ETHUSDT: 2 slots, 2 unique source candidates.
- WPR106-106 session_drift ETHUSDT: 1 slot, 1 unique source candidate.

No selected portfolio included BTCUSDT after replay ranking. WPR106-115,
WPR106-116, and WPR106-117 were loaded and available to the source metrics,
but did not survive into the selected strict portfolios. The practical selected
archetype is an ETH-only blend of lead-lag plus session-anchor behavior.

## May Benchmark

May 2026 benchmark was run only after fixed pre-May selection:

- May-positive selected rows: 0
- May-negative selected rows: 40
- May-flat selected rows: 0
- Best May return: -0.008687
- Worst May return: -0.042144
- May trade count range: 14 to 23
- Median May return: -0.020541

May losses were broad across the selected source archetype. Weighted May
contribution by packet/family:

- WPR106-108 single_leg_lead_lag ETHUSDT: -0.469804 weighted return across 40
  selected portfolios.
- WPR106-109 prior_day_range ETHUSDT: -0.222339 across 38 portfolios.
- WPR106-106 volatility_breakout ETHUSDT: -0.073358 across 26 portfolios.
- WPR106-109 session_range ETHUSDT: -0.040792 across 10 portfolios.
- WPR106-106 session_drift ETHUSDT: -0.014348 in 1 portfolio.
- WPR106-109 opening_range ETHUSDT: -0.007922 across 2 portfolios.

Rank 1 pre-May portfolio `losscomp-4e88ca2fe976fba4` returned +0.790323
pre-May with 533 trades, 28 active months, 3 losing months, max drawdown
-0.069420, and best-month share 0.128757, then benchmarked -0.026014 in May.
The best May-selected portfolio still lost -0.008687.

## Decision

This packet rejects the current loss-complement ensemble construction as
candidate-ready evidence. The pre-May funnel can produce highly stable-looking
strict portfolios, but the fixed selected set failed the May benchmark
uniformly. This is especially important because the pre-May metrics looked
better than many prior single-family rows: full active-month coverage, low
drawdown, low best-month concentration, and full cost-stress survival were not
enough to survive a one-month holdout.

Future broad search should avoid simply recombining ETH lead-lag/session-anchor
families by pre-May monthly complementarity. A next useful lane is either to
force stronger symbol/family diversity before ranking, or to test a genuinely
new source family/feature space rather than letting the same ETH archetype
dominate the portfolio optimizer.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_118_cross_family_loss_complement_ensemble_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
