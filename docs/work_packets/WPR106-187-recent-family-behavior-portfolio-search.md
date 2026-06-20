# WPR106-187 Recent Family Behavior Portfolio Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the broad 2024-forward research search after WPR106-186 rejected
causal state-transition edges. This packet tests whether recent rejected
families from WPR106-180 through WPR106-186 are individually unstable but can
combine into a more stable overlap-aware research-only portfolio when selected
strictly from pre-May evidence.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May source and portfolio selection.

Inputs:

- Selected trade and metric artifacts from WPR106-180 through WPR106-186 when
  present.

Portfolio family:

- source rows behavior-deduplicated by pre-May accepted trade paths;
- source quality and loss-complement scoring using only pre-May monthly
  returns;
- deterministic source portfolios of 2/3/5 members;
- equal-source weighting, same-symbol overlap skipping, and portfolio daily
  accepted-trade caps of 1/3/5;
- pre-May-only ranking by monthly stability, annual losing-month limits,
  return after dropping best months, rolling six-month floor, active trade
  behavior, and drawdown.

May must not be used for source-pool construction, behavior deduplication,
portfolio construction, row ranking, cap choice, source inclusion, or
selection. May is benchmark-only after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-187-recent-family-behavior-portfolio-search.md`
- `docs/stage_reports/STAGE_R106_RECENT_FAMILY_BEHAVIOR_PORTFOLIO_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/**`

## Plan

1. Load selected pre-May and May metric/trade artifacts from WPR106-180 through
   WPR106-186.
2. Normalize source rows into a packet/source/candidate identity table.
3. Deduplicate source rows by exact pre-May accepted-trade path hash.
4. Generate deterministic pre-May-only portfolios by quality and
   loss-complement scoring.
5. Replay portfolios on pre-May with embedded source costs, equal source
   weights, same-symbol overlap skipping, and daily caps.
6. Select fixed portfolios from pre-May diagnostics only.
7. Replay the fixed selected portfolios on May 2026.
8. Write source pool, portfolio ranking, selected pre-May, May benchmark,
   monthly/daily/trade artifacts, summary, report, ledger update, and
   validation notes.

## Research Boundary

All outputs remain:

- `research_only: true`
- `observe_only: true`
- `promotion_ready: false`

This packet must not create a candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim.

## Validation

At close, run:

```powershell
python -m compileall -q data\research\wpr106_187_recent_family_behavior_portfolio_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a negative research result.

The packet-local runner
`data/research/wpr106_187_recent_family_behavior_portfolio_search/scripts/run_wpr106_187_recent_family_behavior_portfolio_search.py`
loaded selected source metrics and trades from WPR106-180 through WPR106-186,
computed exact pre-May accepted-trade path hashes, deduplicated sources by
behavior, generated deterministic equal-source portfolios using pre-May quality
and loss-complement rules, replayed them with same-symbol overlap skipping,
daily caps, and embedded source costs, and benchmarked fixed selected
portfolios on May only after pre-May selection.

An initial larger portfolio generation pass was stopped before portfolio
artifacts because complement scoring was too slow. The completed run used a
bounded first pass over the top 60 deduplicated sources, 25 seeds, 2/3-member
portfolios, and quality/loss-complement/packet-diverse modes. Runtime was
16.48 seconds. CUDA was not used and no speedup claim was made.

Source and portfolio pool:

- 511 source metric rows loaded.
- 281 behavior-deduplicated pre-May source representatives.
- 144 generated portfolio rows.
- 144 positive pre-May portfolio rows.
- 0 annual-target rows.
- 134 loose rows.
- 0 strict rows.

Selected pre-May replay:

- 31 selected rows: 29 `loose`, 2 `positive_stability`.
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

The fixed selected portfolio set is rejected as candidate-ready,
portfolio-ready, or promotion-ready. Pre-May selection concentrated heavily in
WPR106-183 ETHUSDT rolling-VWAP extension sources: the most-used selected
source appeared in all 31 selected portfolios. May rejected every selected
portfolio, so recent-family behavior portfolios do not repair the WPR106-180
through WPR106-186 failures as configured.

Artifacts:

- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/all_recent_source_metrics.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/behavior_dedup_source_representatives.parquet`
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/pre_may/portfolio_pre_may_ranking.parquet`
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
- `data/research/wpr106_187_recent_family_behavior_portfolio_search/wpr106_187_recent_family_behavior_portfolio_search_summary.json`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_187_recent_family_behavior_portfolio_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
