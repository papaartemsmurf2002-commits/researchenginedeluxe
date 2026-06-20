# WPR106-183 Multi-Timeframe VWAP Residual State Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the 2024-forward broad research search after the WPR106-182
multi-horizon KNN rejection with a different, transparent strategy family.
This packet tests multi-timeframe state logic built from completed-bar VWAP
distance, EMA trend, rolling volatility state, wick/flow behavior, and
BTC/ETH cross-symbol residuals.

The goal is to revisit discarded trend, range, VWAP, and relative-value ideas
with more explicit multi-timeframe state gating and active 1-5 trades/day
support, while keeping the month-to-month stability target central.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bar context through May 2026 and 15m
  aggTrade-flow aggregation loaded through the WPR106-126 helper.

Strategy templates:

- trend-pullback continuation around EMA/VWAP state;
- VWAP reclaim/failure after session displacement;
- residual reversion after BTC/ETH relative under/over-performance;
- residual momentum continuation during aligned cross-symbol trend;
- flow/wick exhaustion fade after short-term path extension.

Variant dimensions:

- BTCUSDT and ETHUSDT;
- all/Asia/EU/US sessions;
- long/short/both side modes;
- 8/16/32/64-bar fixed holds;
- 1/3/5 target raw signal rates per day;
- 1/3/5 accepted-trade daily caps;
- volatility, flow, residual, VWAP-distance, trend, and wick filters;
- direct and inverse side policies where logically meaningful.

All score definitions, feature windows, thresholds, row inclusion, ranking,
and selection must use only 2024-01-01 through 2026-04-30. May 2026 must not
be used for feature/filter/threshold/side/hold/daily-cap choice, ranking, or
selection.

The packet is artifact-only unless a blocking correctness issue is discovered.

## Allowed Paths

- `docs/work_packets/WPR106-183-multitimeframe-vwap-residual-state-search.md`
- `docs/stage_reports/STAGE_R106_MULTITIMEFRAME_VWAP_RESIDUAL_STATE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/**`

## Plan

1. Reuse WPR106-126 source-context loading, completed-bar alignment, cost, and
   metrics helpers.
2. Build packet-local completed-bar feature frames for each symbol, including
   multi-timeframe EMA/VWAP distances, volatility state, wick/range state,
   flow state, and BTC/ETH residual state.
3. Calibrate score thresholds from pre-May rows only to target 1/3/5 raw
   signal rates per active day.
4. Evaluate fixed-hold candidates with overlap handling, daily caps, costs,
   cost stress, active-month coverage, annual losing-month caps, best-month
   concentration, rolling-month stability, and dropout robustness.
5. Select fixed pre-May rows without May feedback.
6. Replay only the fixed selected rows on May 2026.
7. Write ranking, selected replay, monthly/daily/trade artifacts, summary,
   report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_183_multitimeframe_vwap_residual_state_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a negative research result.

The packet-local runner
`data/research/wpr106_183_multitimeframe_vwap_residual_state_search/scripts/run_wpr106_183_multitimeframe_vwap_residual_state_search.py`
used a staged broad screen so the search could remain wide without replaying
all daily-cap variants through full monthly diagnostics. The first stage
screened 165,720 rows at daily cap 3, then replayed a 1,228-row source pool
across daily caps 1/3/5 for 3,684 full pre-May candidate rows.

Pre-May screen:

- 165,720 screened rows.
- 28,568 positive rows.
- 45 annual-target rows.
- 447 loose rows.
- 0 strict rows.

Full pre-May replay:

- 3,684 rows.
- 3,653 positive rows.
- 129 annual-target rows.
- 1,240 loose rows.
- 0 strict rows.
- 100 selected rows: 90 `dropout_repair`, 10 `loose`.

Selected pre-May replay:

- 100 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +1.011917.
- Active mean net return: +0.837380.
- Best/worst selected rows: +1.460809 / +0.183472.
- 100 selected rows collapsed to 63 unique pre-May trade-path hashes; largest
  duplicate group was 6 rows.

May 2026 benchmark replay:

- 24 positive rows, 76 negative rows, 0 flat rows.
- Median net return: -0.031082.
- Active mean net return: -0.027420.
- Best/worst selected rows: +0.019486 / -0.094876.
- 100 selected rows collapsed to 31 unique May trade-path hashes; largest May
  duplicate group was 9 rows.

The fixed selected set is rejected as candidate-ready, portfolio-ready, or
promotion-ready. The strongest diagnostic May pocket is BTCUSDT
`squeeze_release_follow` direct-long EU-session residual-extreme compressed
state with flow-contra filtering and a 64-bar hold: +0.480141 pre-May across
156 trades with six losing months, then +0.019486 in May across five trades.
That pocket is preserved only as a research clue because the selected set
failed May, no strict pre-May rows existed, and duplicate behavior reduces
independent evidence.

Artifacts:

- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/screen_daily_cap3_ranking.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/full_replay_source_pool.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/multitimeframe_vwap_residual_state_ranking.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/family_feature_summary.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/selected_pre_may_may_comparison_with_path_hashes.csv`
- `data/research/wpr106_183_multitimeframe_vwap_residual_state_search/wpr106_183_multitimeframe_vwap_residual_state_search_summary.json`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_183_multitimeframe_vwap_residual_state_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
