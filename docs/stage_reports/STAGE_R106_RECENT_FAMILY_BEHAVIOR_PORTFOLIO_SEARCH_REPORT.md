# Stage R106 WPR106-187 Recent Family Behavior Portfolio Search Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-187 continued the broad 2024-forward strategy search after WPR106-186
rejected causal state-transition edges. It tested whether recent rejected
families from WPR106-180 through WPR106-186 could combine into stable
overlap-aware portfolios when selected strictly from pre-May source behavior.

All source scoring, source behavior deduplication, portfolio construction,
portfolio ranking, daily-cap choice, and selected-row inclusion used only
2024-01-01 through 2026-04-30 UTC. May 2026 was benchmark-only after fixed
pre-May selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_187_recent_family_behavior_portfolio_search/scripts/run_wpr106_187_recent_family_behavior_portfolio_search.py`

The runner loaded selected metric and trade artifacts from WPR106-180 through
WPR106-186, normalized source IDs as `packet:candidate_id`, computed exact
pre-May accepted-trade path hashes, and selected one representative per
behavior hash. It generated deterministic equal-source portfolios from
pre-May source quality, loss-complement, and packet-diversity scoring. Portfolio
replay embedded source-level costs, applied equal source weights, skipped
same-symbol overlap, and enforced portfolio daily accepted-trade caps of 1/3/5.

An initial broader portfolio generation pass was stopped before portfolio
artifacts because complement scoring was too slow. The completed run used the
top 60 behavior-deduplicated sources, 25 seeds, 2/3-member portfolios, and
quality/loss-complement/packet-diverse modes. Runtime was 16.48 seconds. CUDA
was not used and no speedup claim was made.

## Results

Source and portfolio pool:

- 511 source metric rows loaded.
- 281 behavior-deduplicated source representatives.
- Source representatives by packet: WPR106-180: 74, WPR106-181: 34,
  WPR106-182: 2, WPR106-183: 63, WPR106-184: 43, WPR106-185: 42,
  WPR106-186: 23.
- 144 generated portfolio rows.
- 144 positive pre-May rows.
- 0 annual-target rows.
- 134 loose rows.
- 0 strict rows.

Selected pre-May replay:

- 31 selected rows.
- 29 `loose` rows and 2 `positive_stability` rows.
- 31 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.572010.
- Active mean net return: +0.601865.
- Best/worst selected rows: +0.866785 / +0.407620.

May 2026 benchmark replay:

- 0 positive rows, 31 negative rows, 0 flat rows.
- Median net return: -0.033519.
- Active mean net return: -0.032355.
- Best/worst selected rows: -0.015019 / -0.056857.
- Aggregate selected May total: -1.002990 across 346 trades.

The best May row was still negative: a 3-member `packet_diverse` portfolio at
daily cap 1 using three WPR106-183 ETHUSDT sources. It recorded +0.491304
pre-May with six losing months, then -0.015019 in May across eight trades.

## Interpretation

Recent-family behavior portfolios do not repair the rejected WPR106-180 through
WPR106-186 families as configured. Pre-May ranking concentrated in WPR106-183
ETHUSDT rolling-VWAP extension behavior despite source behavior deduplication;
the most-used source appeared in all 31 selected portfolios. May rejected every
selected portfolio.

WPR106-187 therefore rejects recent-family behavior portfolios as
candidate-ready, portfolio-ready, or promotion-ready.

## Artifacts

- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/all_recent_source_metrics.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/behavior_dedup_source_representatives.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/behavior_dedup_source_representatives.csv`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/portfolio_pre_may_ranking.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/portfolio_pre_may_ranking.csv`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/portfolio_pre_may_monthly_returns.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/selected_pre_may_portfolios.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/wpr106_187_recent_family_behavior_portfolio_search_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_187_recent_family_behavior_portfolio_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
