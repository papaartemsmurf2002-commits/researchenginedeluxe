# Stage R106 WPR106-203 Cross-Diagnostic Component Portfolio Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-203 tested whether two recent diagnostic components can complement each
other in a May-blind portfolio:

- WPR106-201 ETHUSDT opening-range short active-coverage repairs, which were
  profitable pre-May but mixed in May and still too unstable as standalone
  rows.
- WPR106-202 ETHUSDT motif risk-throttle rows, which transferred well to May
  but had too many pre-May losing months as standalone rows.

The packet fixes both component sources before the portfolio search. Component
pool construction, behavior deduplication, portfolio weighting, overlap
blocking, daily caps, causal monthly health gates, ranking, and selected-row
inclusion use only 2024-01-01 through 2026-04-30 UTC. May 2026 is used only as
a benchmark after the selected portfolio set exists.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_203_cross_diagnostic_component_portfolio/scripts/run_wpr106_203_cross_diagnostic_component_portfolio.py`

The runner reads WPR106-201 and WPR106-202 selected metric and trade artifacts,
normalizes component trades, behavior-deduplicates each component pool, and
evaluates deterministic cross-component portfolios with:

- opening/motif weights of 0.25/0.75, 0.40/0.60, and 0.60/0.40;
- portfolio daily caps of 1 or 2 accepted trades;
- same-symbol no-overlap blocking over weighted component trades;
- time and motif-first priority modes;
- no health gate, rolling 3-month loss-count <= 1, and rolling 6-month
  loss-count <= 2 causal health gates.

An initial broader cross-product run was stopped after a timeout before final
ranking artifacts were written. The completed bounded run evaluated 10
opening components by 10 motif components in 136.38 seconds. CUDA was not used
and no speedup claim was made.

## Results

WPR106-203 evaluated 3,600 pre-May portfolio rows:

- 3,600 positive pre-May rows.
- 1,309 annual-target rows.
- 922 loose rows.
- 116 strict rows.

The fixed selected set contains 100 rows, all selected from the strict
component-portfolio tier:

- 100/100 positive pre-May rows.
- Median pre-May net return: +0.812433.
- Active mean pre-May net return: +0.807436.
- Best/worst selected pre-May returns: +0.877259 / +0.738347.
- Median active months: 25.
- Median inactive months: 3.
- Median losing months: 4.
- 100/100 annual-target rows.

Selected-row controls by construction:

- Health gates: 40 rolling 6-month loss-count <= 2, 38 no gate, and 22 rolling
  3-month loss-count <= 1.
- Priority modes: 50 time-priority and 50 motif-first.
- Daily caps: 52 cap-1 rows and 48 cap-2 rows.

The best pre-May row is `port203-0ffa2c67c72701ab`, combining opening
component `or201-1f16731b9eeb37f1` with motif component
`motif202-00860ffdbf2eb058` at 0.60/0.40 weight, daily cap 1, time priority,
and no health gate. It records +0.877259 pre-May over 234 trades, all 28
pre-May months active, five losing months, max drawdown -0.070521, 100%
cost-stress survival, and May +0.020262 over 11 trades.

The best stability row is `port203-9d00a85ae9eed7fc`, combining opening
component `or201-d092f14fcee5eeaf` with motif component
`motif202-00860ffdbf2eb058` at 0.60/0.40 weight, daily cap 1, time priority,
and rolling 6-month loss-count <= 2. It records +0.763664 pre-May over 187
trades, 25 active months, three inactive months, two losing months, max
drawdown -0.043528, 100% cost-stress survival, and annual loss-month counts of
0 in 2024, 1 in 2025, and 1 in 2026 Jan-Apr.

## May Benchmark

May 2026 was not used for selection. The fixed selected set benchmarks as:

- 100 active rows.
- 100 positive rows and zero negative rows.
- Median May net return: +0.018368.
- Active mean May net return: +0.017915.
- Best/worst selected May returns: +0.025316 / +0.013304.
- Median May active months: 1.
- Zero May losing-month rows.

The best stability row `port203-9d00a85ae9eed7fc` benchmarks +0.013304 in May
over 8 trades, with max drawdown -0.014678. The best May row is
`port203-be171911513e74db`, with +0.025316 in May over 11 trades after
+0.806748 pre-May, 27 active months, five losing months, and max drawdown
-0.045716.

## Interpretation

WPR106-203 is the strongest current research-only diagnostic lead from the
2024-forward search because the selected component portfolios clear strict
pre-May stability gates and benchmark positive in May without May tuning.

It is not candidate-ready, portfolio-ready, paper/live-ready, or promotion-ready.
The result combines post-selected diagnostic components and still needs
source-level ablations, leave-one-component-out controls, weight-neighborhood
tests, shuffled or negative controls, no-trade and transparent baselines,
independent candidate-pack gate materialization, and broader stability-region
evidence before it can be treated as more than a promising research component
portfolio.

No WPR106-203 row is candidate-ready or promotion-ready.

## Artifacts

- `data/research/wpr106_203_cross_diagnostic_component_portfolio/controls/opening_component_pool.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/controls/motif_component_pool.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/pre_may/cross_diagnostic_portfolio_pre_may_ranking.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/pre_may/cross_diagnostic_portfolio_pre_may_top5000.csv`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/pre_may/cross_diagnostic_portfolio_pre_may_monthly_returns.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/pre_may/selected_pre_may_portfolio_rows.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_203_cross_diagnostic_component_portfolio/wpr106_203_cross_diagnostic_component_portfolio_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed final close validation:

```powershell
python -m compileall -q data\research\wpr106_203_cross_diagnostic_component_portfolio\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
