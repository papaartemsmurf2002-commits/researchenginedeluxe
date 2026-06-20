# Stage R106 WPR106-185 Causal Calendar Flow Profile Search Report

Status: closed
Date: 2026-06-12
Owner: Codex Research Agent

## Scope

WPR106-185 continued the broad 2024-forward strategy search after the
WPR106-184 behavior-deduped WPR106-183 selector failed May. It tested a
different family: causal prior-month calendar/session/flow profiles over
BTCUSDT and ETHUSDT 15m bars with completed-bar volatility, trend,
cross-symbol residual, and aggTrade-flow state.

Selection and ranking used only 2024-01-01 through 2026-04-30 UTC. May 2026
was benchmark-only after fixed pre-May selection. May was not used for profile
learning, parameter choice, row inclusion, ranking, or selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_185_causal_calendar_flow_profile_search/scripts/run_wpr106_185_causal_calendar_flow_profile_search.py`

The runner imported WPR106-183 and WPR106-126 helpers so source loading,
completed-bar feature construction, round-trip costs, overlap handling, daily
caps, and metrics matched recent packets. For each evaluation month, it built
profile keys from prior months only. May profiles were frozen from evidence
through 2026-04-30.

The first broad attempt used a 4,320-row grid and was stopped before artifacts
because profile recomputation was too slow. The completed runner used a staged
864-row screen and cached forward returns plus period masks per hold. Runtime
was 56.42 seconds. CUDA was not used and no speedup claim was made.

## Results

Screen:

- 864 rows.
- 174 positive pre-May rows.
- 12 annual-target rows, all too sparse to be active-profile leads.
- 16 loose rows.
- 0 strict rows.

Full replay:

- 152 source rows expanded across daily caps 1/3/5.
- 456 replay rows.
- 445 positive pre-May rows.
- 0 annual-target rows.
- 49 loose rows.
- 0 strict rows.

Selected pre-May replay:

- 72 selected rows.
- 33 `loose` rows and 39 `positive_stability` rows.
- 72 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.451598.
- Active mean net return: +0.507759.
- Best/worst selected rows: +0.980383 / +0.108446.

May 2026 benchmark replay:

- 21 positive rows, 51 negative rows, 0 flat rows.
- Median net return: -0.009405.
- Active mean net return: -0.015629.
- Best/worst selected rows: +0.012527 / -0.105538.
- Aggregate selected May total: -1.125269 across 427 trades.

By symbol, BTCUSDT was mixed at 10 positive and 7 negative May rows, with
median +0.005644 but mean -0.001923. ETHUSDT failed broadly at 11 positive and
44 negative May rows, with median -0.012684 and mean -0.019865.

The best May diagnostic row was BTCUSDT `dow_hour`, 6-month lookback, short
profile, target five raw signals/day, 64-bar hold, daily cap 3. It recorded
+0.457161 pre-May across 169 trades with eight losing months, then +0.012527
in May across four trades. The five selected BTCUSDT `dow_hour` short rows
were all May-positive, but the pocket is too sparse and unstable to promote.

## Interpretation

The causal calendar-flow profile family can find active, post-cost,
pre-May-profitable rows, but its selected set does not transfer to May. The
strongest pre-May rows are mostly ETHUSDT calendar profiles with too many
losing months and poor May behavior. The BTCUSDT day/hour short pocket remains
a research-only clue, not a validated strategy.

WPR106-185 therefore rejects the causal calendar-flow profile family as
candidate-ready, portfolio-ready, or promotion-ready.

## Artifacts

- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_screen_ranking.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_screen_top1000.csv`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_screen_monthly_returns.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_full_replay_ranking.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_full_replay_ranking.csv`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_full_replay_monthly_returns.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/selected_pre_may_calendar_flow_profiles.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/wpr106_185_causal_calendar_flow_profile_search_summary.json`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_185_causal_calendar_flow_profile_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
