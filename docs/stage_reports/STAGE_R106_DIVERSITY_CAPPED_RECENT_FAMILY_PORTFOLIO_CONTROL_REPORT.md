# Stage R106 WPR106-188 Diversity-Capped Recent Family Portfolio Control Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-188 continued the broad 2024-forward strategy search after WPR106-187
rejected recent-family behavior portfolios. It tested whether the WPR106-187
pre-May concentration in WPR106-183/WPR106-184 VWAP/residual behavior could be
controlled by excluding that family, capping it at one member, or requiring
packet-balanced portfolios.

All source-pool controls, portfolio construction, portfolio ranking, daily-cap
choice, and selected-row inclusion used only 2024-01-01 through 2026-04-30 UTC.
May 2026 was benchmark-only after fixed pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/scripts/run_wpr106_188_diversity_capped_recent_family_portfolio_control.py`

The runner reuses the WPR106-187 trade accounting, embedded source costs,
same-symbol overlap skipping, daily caps, monthly diagnostics, and cost-stress
logic. It changes only the pre-May portfolio generator and selector controls:

- `exclude_vwap`: excludes WPR106-183/WPR106-184 sources;
- `cap_one_vwap`: allows at most one WPR106-183/WPR106-184 source;
- `packet_balanced`: prevents any single packet from dominating a portfolio.

The completed run generated 4,665 portfolio rows from 281 behavior-deduplicated
source representatives. Runtime was 361.07 seconds. CUDA was not used and no
speedup claim was made.

## Results

Source and portfolio pool:

- 511 source metric rows loaded.
- 281 behavior-deduplicated source representatives.
- 106 dominant WPR106-183/WPR106-184 representatives.
- 175 non-dominant representatives.
- 4,665 generated portfolio rows.
- 4,665 positive pre-May rows.
- 74 annual-target rows.
- 2,939 loose rows.
- 74 strict rows.

Rows by control universe:

- `exclude_vwap`: 1,557 rows, zero strict rows, 836 loose rows.
- `cap_one_vwap`: 1,557 rows, 32 strict rows, 944 loose rows.
- `packet_balanced`: 1,551 rows, 42 strict rows, 1,159 loose rows.

Selected pre-May replay:

- 100 selected rows: 16 `strict`, 84 `loose`.
- Control mix: 45 `exclude_vwap`, 32 `cap_one_vwap`, 23 `packet_balanced`.
- Dominant-member mix: 45 rows with zero dominant members, 39 with one, and 16
  with two.
- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.692091.
- Active mean net return: +0.714204.
- Best/worst selected rows: +1.086975 / +0.503086.

May 2026 benchmark replay:

- 3 positive rows, 97 negative rows, 0 flat rows.
- Median net return: -0.027960.
- Active mean net return: -0.030845.
- Best/worst selected rows: +0.001586 / -0.082318.

May by control universe:

- `exclude_vwap`: 0 positive / 45 negative, median -0.036071, mean -0.037170.
- `cap_one_vwap`: 0 positive / 32 negative, median -0.029453, mean -0.031890.
- `packet_balanced`: 3 positive / 20 negative, median -0.015642, mean
  -0.017015.

The best May row was only marginally positive: `divport188-e0ab90d8037f7f33`
recorded +0.778071 pre-May across 406 trades, six pre-May losing months,
drop-best-three return +0.519679, rolling six-month minimum -0.006022, and
May +0.001586 across 18 trades. It is a loose `packet_balanced`
drawdown-complement portfolio using one source each from WPR106-180,
WPR106-183, and WPR106-185.

## Interpretation

Diversity-capping the WPR106-183/WPR106-184 VWAP family does not rescue the
recent-family portfolio approach. The no-VWAP universe produced stable-looking
pre-May rows but had zero May-positive selected portfolios. The one-VWAP cap
also had zero May-positive selected portfolios. Packet-balanced rows reduced
the May loss but only produced three tiny positive May rows, all loose rather
than strict.

WPR106-188 therefore rejects diversity-capped recent-family portfolios as
candidate-ready, portfolio-ready, or promotion-ready. The result strengthens
the WPR106-187 conclusion that pre-May portfolio stability across these recent
families is not transferring into the sealed May 2026 benchmark.

## Artifacts

- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/all_recent_source_metrics.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/behavior_dedup_source_representatives.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/behavior_dedup_source_representatives.csv`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/portfolio_pre_may_ranking.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/portfolio_pre_may_ranking.csv`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/portfolio_pre_may_monthly_returns.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/selected_pre_may_portfolios.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/wpr106_188_diversity_capped_recent_family_portfolio_control_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_188_diversity_capped_recent_family_portfolio_control\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
