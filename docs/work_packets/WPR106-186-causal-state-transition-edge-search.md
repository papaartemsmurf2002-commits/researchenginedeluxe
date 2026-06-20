# WPR106-186 Causal State Transition Edge Search

Status: closed
Owner: Codex Research Agent
Date: 2026-06-12

## Objective

Continue the broad 2024-forward research search after WPR106-185 rejected
causal calendar-flow profiles. This packet tests a different adaptive family:
causal market-state transition edges learned from prior months only.

The packet evaluates whether completed-bar volatility state, trend state,
VWAP displacement, BTC/ETH residual state, and aggTrade-flow state transitions
can identify active 1-5-trades/day opportunities that are stable month to
month after costs and overlap controls.

This is an artifact-only research packet, not a candidate-promotion packet.

## Scope

Selection/tuning window:

- 2024-01-01 through 2026-04-30 UTC.

Benchmark-only window:

- May 2026, replayed only after fixed pre-May parameter/row selection.

Inputs:

- WPR106-96 BTCUSDT/ETHUSDT 15m bar context through May 2026 and 15m
  aggTrade-flow aggregation loaded through WPR106-183/WPR106-126 helpers.
- WPR106-185 packet-local rolling profile helper logic for prior-month-only
  profile fitting and efficient cached replay.

Strategy family:

- rolling prior-month state profiles over volatility/trend/flow/VWAP/residual
  state combinations;
- transition keys for volatility-release, flow-flip, residual-shift, and
  session-state variants;
- long, short, and learned-direction variants;
- fixed 8/16/32/64-bar exits;
- accepted-trade daily caps of 1/3/5;
- overlap-aware execution and round-trip costs consistent with recent packets;
- ranking that rewards monthly stability, annual losing-month limits,
  drawdown, return after dropping best months, and active 1-5 trades/day
  behavior.

May must not be used for profile learning, feature/filter choice, parameter
choice, row inclusion, ranking, deduplication, or selection. For May benchmark,
state profiles must be frozen using evidence available through 2026-04-30.

## Allowed Paths

- `docs/work_packets/WPR106-186-causal-state-transition-edge-search.md`
- `docs/stage_reports/STAGE_R106_CAUSAL_STATE_TRANSITION_EDGE_SEARCH_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_186_causal_state_transition_edge_search/**`

## Plan

1. Reuse WPR106-183/WPR106-126 source loaders, completed-bar features, and
   accounting semantics.
2. Reuse WPR106-185 prior-month-only rolling profile replay helpers where
   applicable.
3. Build packet-local completed-bar state and transition keys.
4. Replay descriptors on 2024-01 through 2026-04 with overlap, daily caps, and
   costs.
5. Select fixed promising rows using only pre-May stability diagnostics.
6. Replay the fixed selected rows on May 2026 using state profiles frozen at
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
python -m compileall -q data\research\wpr106_186_causal_state_transition_edge_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

## Result

Closed on 2026-06-12 as a negative research result.

The packet-local runner
`data/research/wpr106_186_causal_state_transition_edge_search/scripts/run_wpr106_186_causal_state_transition_edge_search.py`
tested causal market-state transition profiles over BTCUSDT and ETHUSDT 15m
bars plus aggTrade-flow state. It reused WPR106-183/WPR106-126 source loading,
completed-bar feature construction, overlap handling, daily caps, round-trip
costs, and metrics, plus WPR106-185 prior-month profile replay helpers.

Run profile:

- 1,296 screen rows.
- Runtime: 70.33 seconds.
- CUDA was not used and no speedup claim was made.

Screen:

- 37 positive pre-May rows.
- 15 annual-target rows, but those were sparse or negative and did not become
  active-profile leads.
- 0 loose rows.
- 0 strict rows.

Full replay:

- 34 source rows expanded across daily caps 1/3/5 for 102 replay rows.
- 89 positive pre-May rows.
- 0 annual-target rows.
- 0 loose rows.
- 0 strict rows.

Selected pre-May replay:

- 34 selected rows, all `positive_stability`.
- 34 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.221411.
- Active mean net return: +0.234561.
- Best/worst selected rows: +0.511401 / +0.067338.

May 2026 benchmark replay:

- 18 positive rows, 16 negative rows, 0 flat rows.
- Median net return: +0.008596.
- Active mean net return: -0.019641.
- Best/worst selected rows: +0.055395 / -0.155169.
- Aggregate selected May total: -0.667796 across 439 trades.

The fixed selected set is rejected as candidate-ready, portfolio-ready, or
promotion-ready. It has no strict or loose pre-May rows, selected rows have
10 to 14 losing pre-May months, return after dropping the best three months is
often negative, and the May active mean is negative despite a positive median.

BTCUSDT transition-state short rows are the clearest research clue: selected
BTCUSDT rows were 12 positive and 3 negative in May, and the top BTCUSDT
`transition_vol_flow_trend` short row recorded +0.255860 pre-May across 189
trades and +0.055395 in May across 12 trades. It still had 12 pre-May losing
months and negative drop-best-three-month return, so it remains a research clue
only.

Artifacts:

- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_screen_ranking.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_screen_top1000.csv`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_screen_monthly_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_full_replay_ranking.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/state_transition_edge_full_replay_monthly_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_state_transition_edges.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_186_causal_state_transition_edge_search/wpr106_186_causal_state_transition_edge_search_summary.json`

Validation passed:

```powershell
python -m compileall -q data\research\wpr106_186_causal_state_transition_edge_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
