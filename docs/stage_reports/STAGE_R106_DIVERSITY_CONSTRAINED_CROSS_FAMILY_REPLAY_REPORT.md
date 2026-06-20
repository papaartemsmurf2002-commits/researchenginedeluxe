# Stage R106 Diversity-Constrained Cross-Family Replay Report

Date: 2026-06-11
Packet: WPR106-119
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of all source filtering, diversity-bucket assignment,
member choice, weighting, replay policy selection, ranking, and fixed
selection. It was loaded only after selected pre-May portfolios were fixed.

## Method

The runner
`data/research/wpr106_119_diversity_constrained_cross_family_replay/scripts/run_wpr106_119_diversity_constrained_cross_family_replay.py`
reuses the WPR106-118 normalization and trade-level replay helper, then applies
explicit source diversity constraints before ranking.

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

Diversity rules applied before ranking:

- at least one BTCUSDT source;
- at least one ETHUSDT source;
- at least three source families;
- at least two source packets;
- no more than one source from the ETH lead-lag/session-anchor bucket;
- at least one source from a KNN, regime-switch, flow, dense, or barpath
  support bucket.

Replay controls:

- same-symbol overlap blocking;
- max concurrent positions of 1, 2, or 4;
- max trades/day caps of 1, 2, or 4;
- optional entry-day loss/profit guards;
- equal, source-score-capped, and BTC-floor weight modes;
- cost-stress recomputation from accepted weighted gross returns and weighted
  round-trip costs.

## Artifacts

Root:
`data/research/wpr106_119_diversity_constrained_cross_family_replay/`

Key outputs:

- `wpr106_119_diversity_constrained_cross_family_replay_summary.json`
- `wpr106_119_runner.log`
- `pre_may/source_manifest.parquet`
- `pre_may/source_metrics.parquet`
- `pre_may/source_monthly_returns.parquet`
- `pre_may/diversity_source_pool.parquet`
- `pre_may/diversity_monthly_screen_ranking.parquet`
- `pre_may/diversity_monthly_screen_top2000.csv`
- `pre_may/diversity_portfolio_replay_ranking.parquet`
- `pre_may/diversity_portfolio_replay_top2000.csv`
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
- Diversity source pool rows: 144
- Monthly-screen rows: 497,313
- Trade-level portfolio replay rows: 3,640

Pre-May replay results:

- Positive rows: 3,640
- Annual-target rows: 254
- Loose rows: 254
- Strict rows: 254
- Selected rows: 60
- Selection tier: strict

The selected rows were strong by the pre-May objective:

- Total pre-May net return: +0.539572 to +0.880990, median +0.701459.
- Trades: 536 to 1,241, median 836.5.
- Active months: 28 for every selected row.
- Active days: 530 to 772.
- Trades per active day: 1.000 to 1.608.
- Losing months: 3 to 5.
- Annual loss counts stayed within the target: 2024 max 2, 2025 max 2,
  2026 Jan-Apr max 1.
- Best-month share: 0.089743 to 0.197120.
- Max drawdown: -0.045107 to -0.105492.
- Cost-stress survival: 1.0 for every selected row.
- Rolling losing blocks: 0 for every selected row.

Overlap and rate controls were active in the selected pre-May replays:

- Overlap skips: 1 to 472, mean 241.45.
- Concurrent skips: 0 to 281, mean 33.15.
- Day-cap skips: 0 to 720, mean 105.30.

## Source Diversity

The diversity source pool had 144 rows:

- ETHUSDT dense: 45
- BTCUSDT dense: 20
- ETH lead-anchor: 18
- BTCUSDT anchor/other: 14
- ETHUSDT flow: 12
- ETHUSDT KNN: 10
- BTCUSDT KNN: 8
- BTCUSDT flow: 6
- ETHUSDT regime-switch: 5
- BTCUSDT cross-asset: 3
- BTCUSDT regime-switch: 3

This pool was materially broader than the WPR106-118 selected set. The
selected rows were also forced to keep BTC and ETH exposure, at least three
families, at least two packets, at least three diversity buckets, and at most
one ETH lead-anchor source.

## Composition

The selected strict set still concentrated in a recurring structure. Top
selected member slots by packet/family/symbol:

- WPR106-108 single_leg_lead_lag ETHUSDT: 54 slots.
- WPR106-107 rolling_knn ETHUSDT: 31 slots.
- WPR106-106 session_drift ETHUSDT: 18 slots.
- WPR106-111 flow_price_divergence ETHUSDT: 16 slots.
- WPR106-106 wick_fade ETHUSDT: 15 slots.
- WPR106-109 prior_day_range BTCUSDT: 14 slots.
- WPR106-106 balanced BTCUSDT: 13 slots.
- WPR106-109 opening_range BTCUSDT: 11 slots.
- WPR106-106 flow_follow ETHUSDT: 10 slots.
- WPR106-115 volatility ETHUSDT: 10 slots.

The forced BTC sleeves were present, but the highest-ranked portfolios still
depended heavily on one ETH lead-lag source plus ETH dense or KNN behavior.

## May Benchmark

May 2026 benchmark was run only after fixed pre-May selection:

- May-positive selected rows: 8
- May-negative selected rows: 52
- May-flat selected rows: 0
- Best May return: +0.009587
- Worst May return: -0.045300
- Median May return: -0.026690
- May trade count range: 17 to 47
- May active-day range: 17 to 27
- May trades per active day: 1.000 to 1.741

The best May row was `divcombo-e7475b49e26e8975` at selection rank 37. It had
+0.738946 pre-May return, 771 pre-May trades, 592 active days, 4 losing
pre-May months, max drawdown -0.060935, and May return +0.009587 from 21 May
trades across 18 active days. Its members were:

- WPR106-106 ETHUSDT volatility_breakout `dense-a63178a8ab37caca`
- WPR106-106 ETHUSDT wick_fade `dense-f2c1338bdd392f17`
- WPR106-108 ETHUSDT single_leg_lead_lag `xasset-264398ad33c1ce89`
- WPR106-109 BTCUSDT prior_day_range `anchor-125c3cb4afa2cd09`

Other May-positive rows were lower-ranked and largely shared the same ETH
lead-lag plus ETH dense/wick pattern with a small BTC sleeve. The top five
pre-May selected portfolios were all May-negative.

Weighted May contribution by packet/family/symbol:

- WPR106-108 single_leg_lead_lag ETHUSDT: -0.549137
- WPR106-106 balanced BTCUSDT: -0.153690
- WPR106-107 rolling_knn ETHUSDT: -0.149053
- WPR106-106 balanced ETHUSDT: -0.135631
- WPR106-106 session_drift ETHUSDT: -0.119343
- WPR106-106 flow_follow ETHUSDT: -0.101953
- WPR106-111 flow_price_divergence ETHUSDT: -0.059932
- WPR106-106 wick_fade ETHUSDT: +0.015416
- WPR106-109 prior_day_range BTCUSDT: +0.007243
- WPR106-115 range BTCUSDT: +0.006116
- WPR106-109 opening_range BTCUSDT: +0.003994

May cost-stress survival was weak across the fixed selected set: mean 0.091667
and median 0.0. This is consistent with the benchmark rejection rather than a
promising cost-stable holdout result.

## Decision

This packet rejects the current diversity-constrained cross-family replay as
candidate-ready evidence. The diversity constraints improved on WPR106-118 by
finding some May-positive strict rows, but 52 of 60 fixed selected portfolios
lost money in May, the top pre-May ranks were May-negative, and the May-positive
rows remained lower-ranked and archetype-concentrated.

The useful research lead is narrow: ETH dense/wick behavior plus one ETH
lead-lag source and a small BTC sleeve can survive May in a few fixed rows.
That is not enough for promotion or paper/live use. Future work should treat
this as a source of hypotheses, not as a defendable candidate, and should
continue testing genuinely different source families or selection objectives
that do not simply reselect the same ETH lead-lag/dense core.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_119_diversity_constrained_cross_family_replay/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
