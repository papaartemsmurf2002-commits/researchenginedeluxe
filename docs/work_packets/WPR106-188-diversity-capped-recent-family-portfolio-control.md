# WPR106-188 Diversity-Capped Recent Family Portfolio Control

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the broad 2024-forward research search after WPR106-187 rejected
recent-family behavior portfolios. WPR106-187 showed that May-blind portfolio
selection concentrated in WPR106-183/WPR106-184 multi-timeframe VWAP/residual
behavior and then lost uniformly in May. This packet tests the control question:
whether the non-dominant recent families can form a more stable research-only
portfolio when the WPR106-183/WPR106-184 VWAP family is excluded or tightly
capped before any May benchmark is run.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May source and portfolio selection.

Inputs:

- WPR106-187 source metric and trade artifacts when present.
- WPR106-180 through WPR106-186 selected metric/trade artifacts only through
  the WPR106-187 normalized source pool.

Portfolio/control family:

- exact pre-May accepted-trade path behavior deduplication;
- deterministic source-pool controls that exclude WPR106-183/WPR106-184 or
  cap them at one member per portfolio;
- packet/family-balanced source selection using only pre-May diagnostics;
- equal-source portfolio replay with same-symbol overlap skipping, embedded
  source costs, and accepted-trade daily caps of 1/3/5;
- pre-May-only ranking by monthly stability, annual losing-month limits,
  return after dropping best months, rolling six-month floor, active trade
  behavior, source diversity, and drawdown.

May must not be used for source-pool construction, behavior deduplication,
portfolio construction, row ranking, cap choice, source inclusion, or
selection. May is benchmark-only after fixed pre-May selection.

## Allowed Paths

- `docs/work_packets/WPR106-188-diversity-capped-recent-family-portfolio-control.md`
- `docs/stage_reports/STAGE_R106_DIVERSITY_CAPPED_RECENT_FAMILY_PORTFOLIO_CONTROL_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/**`

## Plan

1. Load WPR106-187 normalized source metrics and selected source trades.
2. Recompute or reuse exact pre-May accepted-trade path hashes to confirm
   behavior-deduplicated source representatives.
3. Build multiple May-blind control universes:
   - exclude WPR106-183/WPR106-184;
   - cap WPR106-183/WPR106-184 at one member;
   - packet-balanced portfolios with no packet majority.
4. Generate deterministic 2/3/4-member portfolios from pre-May quality,
   loss-complement, packet-diversity, and drawdown-complement scores.
5. Replay portfolios on pre-May with embedded source costs, equal source
   weights, same-symbol overlap skipping, and daily caps.
6. Select fixed portfolios from pre-May diagnostics only.
7. Replay the fixed selected portfolios on May 2026.
8. Write source/control pool, portfolio ranking, selected pre-May, May
   benchmark, monthly/daily/trade artifacts, summary, report, ledger update,
   and validation notes.

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
python -m compileall -q data\research\wpr106_188_diversity_capped_recent_family_portfolio_control\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a negative research result.

The packet-local runner
`data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/scripts/run_wpr106_188_diversity_capped_recent_family_portfolio_control.py`
reused the WPR106-187 trade accounting, embedded source costs, same-symbol
overlap skipping, daily caps, monthly diagnostics, and cost-stress logic. It
changed the pre-May portfolio generator to enforce three source-universe
controls before fixed selection:

- `exclude_vwap`: excludes WPR106-183/WPR106-184 sources;
- `cap_one_vwap`: allows at most one WPR106-183/WPR106-184 source;
- `packet_balanced`: prevents any single packet from dominating a portfolio.

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

Selected pre-May replay:

- 100 selected rows: 16 `strict`, 84 `loose`.
- 45 `exclude_vwap`, 32 `cap_one_vwap`, 23 `packet_balanced`.
- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.692091.
- Active mean net return: +0.714204.
- Best/worst selected rows: +1.086975 / +0.503086.

May 2026 benchmark replay:

- 3 positive rows, 97 negative rows, 0 flat rows.
- Median net return: -0.027960.
- Active mean net return: -0.030845.
- Best/worst selected rows: +0.001586 / -0.082318.
- `exclude_vwap`: 0 positive / 45 negative, median -0.036071.
- `cap_one_vwap`: 0 positive / 32 negative, median -0.029453.
- `packet_balanced`: 3 positive / 20 negative, median -0.015642.

The fixed selected set is rejected as candidate-ready, portfolio-ready, or
promotion-ready. The no-VWAP and one-VWAP-control universes both failed May
completely; packet-balanced rows reduced but did not eliminate the May loss,
and the best May row was only +0.001586 across 18 trades.

Artifacts:

- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/all_recent_source_metrics.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/behavior_dedup_source_representatives.parquet`
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/pre_may/portfolio_pre_may_ranking.parquet`
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
- `data/research/wpr106_188_diversity_capped_recent_family_portfolio_control/wpr106_188_diversity_capped_recent_family_portfolio_control_summary.json`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_188_diversity_capped_recent_family_portfolio_control\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
