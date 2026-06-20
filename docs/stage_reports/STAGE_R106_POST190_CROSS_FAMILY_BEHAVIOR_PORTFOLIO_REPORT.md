# Stage R106 WPR106-199 Post-190 Cross-Family Behavior Portfolio Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-199 moved beyond defending the rejected WPR106-198 health-gated
opening-range repair. It pooled recent selected trade evidence from WPR106-190
through WPR106-198, behavior-deduplicated exact accepted-trade paths, generated
two-, three-, and four-member overlap-aware portfolios, selected rows using
pre-May evidence only, and used May 2026 only as a fixed-set benchmark.

The goal was not to promote a portfolio. It was to test whether recent
discarded and diagnostic families could complement each other enough to improve
month-to-month stability under realistic source costs, same-symbol overlap
blocking, and portfolio-level daily caps.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/scripts/run_wpr106_199_post190_cross_family_behavior_portfolio.py`

The runner reuses the WPR106-187 portfolio evaluator and adds WPR106-199
source loading, side/timestamp normalization, top-per-packet source seeds, and
pre-May-only source-packet/source-id selection caps. The final run used:

- source packets WPR106-190 through WPR106-198;
- exact pre-May trade-path behavior hashes for source deduplication;
- quality, loss-complement, low-correlation, packet-diverse, and
  stability-rescue complement logic;
- selected portfolio daily caps of 1, 3, and 5 trades/day;
- source trade gross/cost/net returns reweighted by portfolio member count;
- same-symbol overlap blocking at the portfolio layer;
- monthly, drawdown, Sortino, cost-stress, drop-best-month, and rolling
  six-month diagnostics.

Runtime was 135.00 seconds. CUDA was not used and no speedup claim was made.

## Source Pool

Loaded selected source metric rows:

- WPR106-190 directional KNN confidence entries: 100.
- WPR106-191 directional KNN accepted-trade repair: 100.
- WPR106-192 causal motif lookup: 74.
- WPR106-193 motif path-managed exit repair: 97.
- WPR106-194 intrabar flow burst profiles: 100.
- WPR106-195 cross-asset residual spreads: 15.
- WPR106-196 anchored range/day-structure: 100.
- WPR106-197 opening-range short stability control: 100.
- WPR106-198 opening-range short behavior confirmation: 100.

Total source metric rows: 786.

Behavior-deduped source representatives:

- Total: 422.
- WPR106-190: 54.
- WPR106-191: 13.
- WPR106-192: 19.
- WPR106-193: 65.
- WPR106-194: 55.
- WPR106-195: 11.
- WPR106-196: 72.
- WPR106-197: 50.
- WPR106-198: 83.

The source pool confirmed why the selector tends to prefer recent
opening/anchored-range evidence: WPR106-196, WPR106-197, and WPR106-198 have
higher median pre-May returns and fewer median losing months than the older
KNN, motif, intrabar-flow, and pair-spread diagnostics.

## Portfolio Funnel

The runner evaluated 903 portfolio rows:

- 903 positive pre-May rows.
- 53 annual-target rows.
- 575 loose rows.
- 53 strict rows.

The fixed selected set contains 38 rows:

- 10 strict.
- 20 loose.
- 8 positive-stability rows.

Selected mode counts:

- `low_corr`: 28.
- `stability_rescue`: 6.
- `loss_complement`: 4.

Selected source packet inclusion counts:

- WPR106-190: 4.
- WPR106-191: 12.
- WPR106-195: 3.
- WPR106-196: 48.
- WPR106-197: 23.
- WPR106-198: 9.

No WPR106-192, WPR106-193, or WPR106-194 source survived the final selected
set after pre-May ranking and caps, although those packets were present in the
behavior-deduped source pool.

## Results

Selected pre-May replay:

- 38 active rows.
- 38 positive rows, zero negative rows, zero flat rows.
- Median net return: +0.623546.
- Active mean net return: +0.619484.
- Best/worst selected rows: +0.826019 / +0.390723.

May 2026 benchmark:

- 38 active rows.
- 13 positive rows, 25 negative rows, zero flat rows.
- Median net return: -0.006735.
- Active mean net return: -0.006911.
- Best/worst selected rows: +0.014893 / -0.034259.

May by selected tier:

- `strict`: 10 rows, seven positive, three negative, May median +0.006134,
  May active mean +0.004812, pre-May median +0.653902, median pre-May losing
  months 4.5.
- `loose`: 20 rows, six positive, 14 negative, May median -0.007227, May
  active mean -0.008328, pre-May median +0.738812, median pre-May losing
  months 8.
- `positive_stability`: eight rows, zero positive, eight negative, May median
  -0.017356, May active mean -0.018023, median pre-May losing months 9.5.

May by portfolio mode:

- `low_corr`: 28 rows, 13 positive, 15 negative, May median -0.001815.
- `stability_rescue`: six rows, zero positive, six negative, May median
  -0.023273.
- `loss_complement`: four rows, zero positive, four negative, May median
  -0.008993.

## Diagnostics

The best May row is `post190port199-315e1b76244b907a`, a loose low-correlation
two-member portfolio:

- sources: `WPR106-196:day196-22efa800f4494bb8` and
  `WPR106-197:or197-f37732bbc7bd4db6`;
- daily cap: 1;
- pre-May trades: 245;
- pre-May active months: 28;
- pre-May losing months: 6, split as 2 in 2024, 3 in 2025, and 1 in 2026
  Jan-Apr;
- pre-May net return: +0.799560;
- pre-May max drawdown: -0.103623;
- pre-May best-month share: 0.132261;
- 100% cost-stress survival;
- May net return: +0.014893 over eight trades.

The best strict-tier diagnostics are low-correlation three-member portfolios
that add a WPR106-190 or WPR106-191 KNN source to WPR106-196 and WPR106-197.
For example, `post190port199-92e72bdeb08ffec6` records +0.671686 pre-May over
301 trades, 28 active months, four pre-May losing months, 100% cost-stress
survival, and +0.012206 in May over eight trades. This is useful follow-up
evidence but not enough for candidate readiness.

## Interpretation

WPR106-199 rejects the broad post-190 cross-family portfolio set as
candidate-ready, portfolio-ready, or promotion-ready. The selected-set May
benchmark is negative overall despite strong pre-May evidence. Loose and
positive-stability tiers fail May decisively, and even the strict tier is a
small diagnostic subset rather than a fully gated candidate.

The packet does preserve a narrower diagnostic: strict low-correlation
portfolios combining WPR106-196 anchored/opening-range behavior, WPR106-197
opening-range short controls, and one KNN repair/confidence source can meet
the target pre-May losing-month profile and transfer modestly positive to May.
That needs a follow-up packet before any eligibility claim because source
concentration, source-level ablation, independent transparent baselines,
stability-region evidence, and candidate-pack gates are missing.

## Artifacts

- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/all_post190_source_metrics.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/behavior_dedup_source_representatives.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/portfolio_pre_may_ranking.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/portfolio_pre_may_monthly_returns.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/selected_pre_may_portfolios.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_199_post190_cross_family_behavior_portfolio/wpr106_199_post190_cross_family_behavior_portfolio_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_199_post190_cross_family_behavior_portfolio\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
