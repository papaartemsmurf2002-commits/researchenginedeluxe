# WPR106-97 Preselected Portfolio May Benchmark Expansion

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Goal

Expand the May 2026 benchmark from the WPR106-96 rank-1 portfolio check to
the WPR106-95 preselected May-holdout portfolio candidates. Use only
pre-May-selected combinations and frozen sleeve definitions, keep May 2026 out
of tuning and selection, and report May as benchmark evidence for the broader
2024-forward research search.

## Scope

- Benchmark WPR106-95 combinations that already had
  `may_holdout_candidate: true` before May 2026 benchmark evaluation.
- Reuse WPR106-96 verified May 2026 BTCUSDT and ETHUSDT source context.
- Materialize only the missing feature contexts needed to replay the frozen
  WPR106-95 sleeves over the full 2024-01-01 through 2026-05-31 context.
- Replay frozen sleeve parameters, costs, holding/exit settings, and
  feature-set definitions without May-driven changes.
- Filter full-context sleeve trades to May-entry trades, then compute equal
  sleeve portfolio benchmark metrics by preselected combination.
- Report May trades, signals, active days, trades per active day, overlap-day
  share, daily behavior, net return, expectancy, and whether May contradicts
  the pre-May stability story.
- Keep all outputs research-only, observe-only, and promotion-ready false.

## Allowed paths

- `docs/work_packets/WPR106-97-preselected-portfolio-may-benchmark-expansion.md`
- `docs/stage_reports/STAGE_R106_PRESELECTED_PORTFOLIO_MAY_BENCHMARK_EXPANSION_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_97*/**`

## Out of scope

- No May 2026 tuning, ranking feedback, optimizer feedback, feature choice,
  filter choice, threshold choice, parameter change, strategy choice, or
  selection change.
- No new strategy, feature, research-cycle, live-boundary, or operator UI code
  unless a blocking correctness issue is discovered and separately documented.
- No candidate pack, promotion artifact, paper/live artifact, order placement,
  position sizing, runtime-mode change, or live-configuration write.
- No synthetic fallback data.
- No CUDA speedup claim.

## Exit evidence

- Unique WPR106-95 preselected sleeve definitions are extracted and linked to
  their frozen historical-cycle configs:
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/input/wpr106_97_unique_sleeves.csv`
  and
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/input/wpr106_97_config_inventory.csv`.
- Required full-context feature frames and a feature context manifest are
  written under
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/features/`.
- Full-context frozen sleeve replays and May-only sleeve summaries are written
  under
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/backtests_full_context/`
  and
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/may_only/`.
- Preselected combination May benchmark tables and a summary JSON are written
  under
  `data/research/wpr106_97_preselected_portfolio_may_benchmark_expansion/`.
- All 36 unique sleeve replays passed. The 40 preselected combinations
  produced 24 positive May rows and 16 negative May rows; all 40 remained in
  the 1 to 5 trades-per-active-day range.
- Best May row: WPR106-95 rank 13 `combo-f4f5b5aa62ffd476` with 30 trades,
  24 active days, 1.250 trades per active day, 0.250 overlap-day share, and
  +0.044274 equal-sleeve portfolio return.
- WPR106-95 rank 1 `combo-d9edcc252c323b03` reproduced the WPR106-96
  +0.026603 May return exactly. Ranks 3 through 12 were negative because the
  repeated BTCUSDT `fbbe/6e79` volatility-breakout sleeve lost about -0.104401
  in May.
- Stage report records benchmark-only methodology, May non-tuning boundary,
  limitations, and next research implications.
- Validation baseline passed:
  `python -m compileall -q src/tradingbotsuite` and
  `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` with 460
  passed.
