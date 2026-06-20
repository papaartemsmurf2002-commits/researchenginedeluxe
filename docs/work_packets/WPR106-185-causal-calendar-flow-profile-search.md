# WPR106-185 Causal Calendar Flow Profile Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the broad 2024-forward research search after WPR106-184 rejected the
behavior-deduped WPR106-183 selector. This packet tests a different family:
causal calendar/session/flow profiles that select recurring intraday BTCUSDT
and ETHUSDT opportunities from prior-month evidence only.

The goal is not to defend a single old lead. It is to test whether modern
calendar/session structure combined with completed-bar volatility, trend,
cross-symbol residual, and aggTrade-flow state can produce stable active
1-5-trades/day behavior after realistic costs and overlap controls.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May parameter/row selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bar context through May 2026 and 15m
  aggTrade-flow aggregation loaded through WPR106-183/WPR106-126 helpers.

Strategy family:

- rolling prior-month calendar profiles over day-of-week, hour, session, and
  15m slot structure;
- optional state keys using completed-bar volatility compression/expansion,
  trend, cross-symbol residual, and aggTrade-flow imbalance;
- long, short, and learned-direction profile variants;
- fixed 4/8/16/32/64-bar exits;
- accepted-trade daily caps of 1/3/5;
- overlap-aware execution and round-trip costs consistent with prior packets;
- ranking that rewards monthly stability, annual losing-month limits,
  drawdown, return after dropping best months, and active 1-5 trades/day
  behavior rather than one large profitable window.

May must not be used for profile learning, feature/filter choice, threshold
choice, parameter choice, ranking, row inclusion, deduplication, or selection.
For May benchmark, the profile state must be frozen using evidence available
through 2026-04-30.

## Allowed Paths

- `docs/work_packets/WPR106-185-causal-calendar-flow-profile-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_CALENDAR_FLOW_PROFILE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/**`

## Plan

1. Reuse WPR106-183/WPR106-126 packet-local loaders and accounting semantics.
2. Build completed-bar feature states for BTCUSDT and ETHUSDT over the 2024
   through May 2026 context.
3. For each month, construct calendar/profile scores from prior months only.
4. Replay candidate descriptors on 2024-01 through 2026-04 with overlap,
   daily caps, and costs.
5. Select fixed promising rows using only pre-May stability diagnostics.
6. Replay the fixed selected rows on May 2026 using profile evidence frozen at
   2026-04-30.
7. Write ranking, selected pre-May, May benchmark, monthly/daily/trade
   artifacts, summary, report, ledger update, and validation notes.

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
python -m compileall -q data\research\wpr106_185_causal_calendar_flow_profile_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a negative research result.

The packet-local runner
`data/research/wpr106_185_causal_calendar_flow_profile_search/scripts/run_wpr106_185_causal_calendar_flow_profile_search.py`
tested causal prior-month calendar/session/flow profiles over BTCUSDT and
ETHUSDT 15m bars plus aggTrade-flow state. The initial broader 4,320-row
screen attempt was stopped before artifacts because profile recomputation was
too slow. The runner was then narrowed to a staged 864-row first pass and
patched to cache forward returns and period masks per hold. The completed run
finished in 56.42 seconds. CUDA was not used and no speedup claim was made.

Screen:

- 864 rows.
- 174 positive pre-May rows.
- 12 annual-target rows, but those were sparse and not active-profile leads.
- 16 loose rows.
- 0 strict rows.

Full replay:

- 152 source rows expanded across daily caps 1/3/5 for 456 replay rows.
- 445 positive pre-May rows.
- 0 annual-target rows.
- 49 loose rows.
- 0 strict rows.

Selected pre-May replay:

- 72 selected rows: 33 `loose`, 39 `positive_stability`.
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

The fixed selected set is rejected as candidate-ready, portfolio-ready, or
promotion-ready. BTCUSDT day/hour short profiles were the only constructive
May diagnostic pocket: five selected BTCUSDT `dow_hour` short rows were all
May-positive at +0.012527, but each had only four May trades and seven to
eight losing pre-May months. The stronger pre-May ETHUSDT calendar profiles
transferred poorly to May.

Artifacts:

- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_screen_ranking.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_screen_top1000.csv`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_screen_monthly_returns.parquet`
- `data/research/wpr106_185_causal_calendar_flow_profile_search/pre_may/calendar_flow_profile_full_replay_ranking.parquet`
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
- `data/research/wpr106_185_causal_calendar_flow_profile_search/wpr106_185_causal_calendar_flow_profile_search_summary.json`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_185_causal_calendar_flow_profile_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
