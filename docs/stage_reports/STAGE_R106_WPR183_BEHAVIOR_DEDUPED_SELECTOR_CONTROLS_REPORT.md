# Stage R106 WPR106-184 WPR183 Behavior-Deduped Selector Controls Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-184 followed up the rejected WPR106-183 multi-timeframe VWAP/residual
state selected set. WPR106-183 had many profitable pre-May rows but its fixed
selected set was behavior-duplicate-heavy and failed May 2026. This packet
tested whether a strictly May-blind behavior-deduped selector over the
WPR106-183 full replay universe could improve benchmark transfer.

Selection, ranking, path hashing, deduplication, caps, and row inclusion used
only 2024-01-01 through 2026-04-30 UTC. May 2026 was replayed only after the
fixed pre-May selection was written.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/scripts/run_wpr106_184_wpr183_behavior_deduped_selector_controls.py`

The runner imported the WPR106-183 packet-local helpers so completed-bar
features, source context, costs, overlap handling, daily caps, and accounting
matched the prior packet. It loaded the WPR106-183 full pre-May replay ranking,
replayed eligible rows with accepted-trade ledgers, hashed exact pre-May
accepted-trade paths, selected one representative per path hash, and ranked
representatives with pre-May-only monthly stability, annual losing-month,
rolling-floor, return-after-dropping-best-months, cost-stress, drawdown,
family/template/symbol/session/side, and active-rate diagnostics.

Runtime was 79.15 seconds. CUDA was not used and no speedup claim was made.

## Results

Behavior replay and deduplication:

- 3,684 WPR106-183 source ranking rows.
- 3,409 eligible source rows replayed with trades.
- 1,823 unique pre-May trade-path hashes.
- 1,823 behavior-deduplicated representatives.
- 1,823 positive pre-May representatives.
- 4 annual-target rows, 677 loose rows, 0 strict rows.

Fixed selected set:

- 100 selected rows.
- 77 `dedup_dropout_repair` rows and 23 `dedup_loose` rows.
- 100 unique pre-May trade-path hashes.
- 54 unique May trade-path hashes.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.884393.
- Active mean net return: +0.784029.
- Best/worst selected rows: +1.460809 / +0.097654.

May 2026 benchmark replay:

- 21 positive rows, 79 negative rows, 0 flat rows.
- Median net return: -0.026900.
- Active mean net return: -0.029790.
- Best/worst selected rows: +0.028018 / -0.094876.
- Aggregate selected May total: -2.979006 across 639 trades.

By symbol, the selected BTCUSDT rows were mixed at 17 positive and 19 negative
May rows, with median -0.000266 and mean -0.004589. The selected ETHUSDT rows
failed broadly at 4 positive and 60 negative May rows, with median -0.045057
and mean -0.043966.

The best May row was BTCUSDT `session_vwap_reclaim_failure` /
`session_vwap_reclaim`, direct both-side, EU session, compressed volatility,
flow-confirm filter, 64-bar hold, daily cap 1. It recorded +0.531281 pre-May
across 403 trades with eight losing months, then +0.028018 in May across 15
trades. BTCUSDT residual-reversion, residual-momentum, squeeze-release, and
session-VWAP pockets produced some May-positive diagnostics, but they were too
small and mixed to offset the selected-set failure.

## Interpretation

Behavior deduplication fixed the WPR106-183 duplicate-path problem at the
selection layer: the 100 selected rows had 100 unique pre-May trade paths. It
did not fix month-to-month transfer. The selected set remained heavily exposed
to pre-May-attractive behavior that May rejected, especially ETHUSDT inverse
rolling-VWAP extension rows.

WPR106-184 therefore rejects the WPR106-183 behavior-deduped selector as
candidate-ready, portfolio-ready, or promotion-ready. The BTCUSDT May-positive
session-VWAP/residual pockets remain research-only clues for later independent
families or controls. They are not enough to promote the WPR106-183 family.

## Artifacts

- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/eligible_source_pool.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/pre_may_behavior_replay_metrics.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/pre_may_behavior_monthly_returns.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/pre_may_behavior_daily_returns.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/pre_may_behavior_trades.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/behavior_dedup_representatives.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/selected_pre_may_behavior_dedup.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_184_wpr183_behavior_deduped_selector_controls/wpr106_184_wpr183_behavior_deduped_selector_controls_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_184_wpr183_behavior_deduped_selector_controls\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
