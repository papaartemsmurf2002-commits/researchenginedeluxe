# Stage R106 WPR106-209 Cross-Flow Exhaustion Transfer Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-209 continued the broad 2024-forward research search after WPR106-208
rejected the calendar/session train-window controls. It did not defend the
rejected BTC sparse side-veto lead, the WPR106-139 calendar pocket, or any
prior selected artifact directly.

The packet tested a new order-flow interaction family around two diagnostic
clues:

- WPR106-154 BTCUSDT -> ETHUSDT synchronized-flow / cross-divergence was a
  narrow annual-target near-miss but missed active-month and May robustness.
- WPR106-194 ETHUSDT late-flow exhaustion fade had May-positive pockets but
  unstable pre-May month distribution.

All feature construction, score definitions, threshold calibration, state-gate
choice, row ranking, behavior de-duplication, and selected-row inclusion used
only 2024-01-01 through 2026-04-30 UTC. May 2026 was replayed only after fixed
selected rows existed.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/scripts/run_wpr106_209_cross_flow_exhaustion_transfer_repair.py`

The runner imports WPR106-154 and WPR106-153 helpers for WPR106-96
BTCUSDT/ETHUSDT 15m bars and 1m aggTrade intrabar features. It keeps all new
logic local to the WPR106-209 artifact tree.

It builds completed-bar interaction scores from:

- leader and target signed-flow pressure;
- leader and target late-minute flow pressure;
- target late-flow exhaustion and late-volume share;
- target flow/price divergence and absorption proxies;
- leader/target synchronized flow and cross-divergence strength;
- relative leader-target flow gap;
- target range, volume, and concentration state.

The bounded grid covers:

- BTCUSDT -> ETHUSDT and ETHUSDT -> BTCUSDT leader-target pairs;
- normalization windows 96 and 384 bars;
- 8, 16, and 32 bar holds;
- all, EU, and US sessions;
- six templates and six state gates;
- both, long-only, and short-only side policies;
- 1, 2, 3, and 5 target raw signals per day;
- 1, 3, and 5 accepted-trade daily caps;
- no throttle and prior-month loss throttle.

Rows are scored on pre-May only for annual loss caps, active-month coverage,
cost-stress survival, drawdown, best-month dependence, drop-best-month
robustness, rolling six-month stability, latest Jan-April 2026 coverage, and
consecutive losing-month clusters. Preselected rows are replayed with trades
and behavior-deduplicated by accepted pre-May trade path before May replay.

Runtime was 525.99 seconds. CUDA was not used and no speedup was claimed.

## Results

Pre-May screen:

- Evaluated rows: 93,312.
- Positive pre-May rows: 3,197.
- Positive annual-target rows: 0.
- Loose pre-May rows: 324.
- Strict pre-May rows: 0.
- Preselected rows: 118.
- Behavior-deduplicated selected rows: 25.

Selected pre-May replay:

- 25 positive rows, 0 negative rows, 0 flat rows.
- Median total net return: +0.319612.
- Best selected pre-May return: +0.672164.
- Worst selected pre-May return: +0.127749.

May 2026 benchmark after fixed pre-May selection:

- 25 benchmark rows.
- 9 positive rows, 12 negative rows, 4 flat rows.
- Median May return: 0.000000.
- Best May return: +0.062942.
- Worst May return: -0.088245.

The top pre-May row is `xflowexh209-e9e7ca4876a95b6e`: BTCUSDT-led ETHUSDT
`relative_gap_absorption_reversion`, all state gate, US session, both-sided,
32-bar hold, target rate 1/day, daily cap 1, and prior-month loss throttle.
It records +0.672164 pre-May over 394 trades, 21 active months, seven losing
months, max drawdown -0.193599, 100% cost-stress survival, and +0.062942 in
May over 24 trades. It fails the annual target with 2024/2025/2026 Jan-April
losing-month counts of 4/3/0.

Selected rows concentrate in BTCUSDT-led ETHUSDT behavior:

- `relative_gap_absorption_reversion` provides the strongest pre-May and best
  May rows, but leader-target-disagree variants are May-negative and all rows
  miss annual stability.
- `leader_late_pressure_transfer` / `sync_cross` produces several May-positive
  rows, but still carries 7-8 pre-May losing months.
- ETHUSDT-led BTCUSDT target-late-exhaustion rows are smaller and mixed; the
  three selected BTCUSDT target-late-exhaustion rows have two May positives
  and one May negative.

## Decision

WPR106-209 is rejected as candidate-ready, portfolio-ready, paper/live-ready,
or promotion-ready. The repair improves the old WPR106-154/WPR106-194
diagnostics by finding active, cost-positive, behavior-deduplicated pre-May
rows and a few May-positive rows, but it produces zero annual-target rows and
zero strict rows. The dominant failure remains month-to-month loss clustering,
especially excess 2024 and 2025 losing months.

The useful research evidence is that BTCUSDT-led ETHUSDT relative-flow
absorption reversion and leader-late transfer remain worth treating as
diagnostic order-flow behaviors. They are not stable enough for candidate,
paper, live, portfolio, or promotion claims without a genuinely new
pre-May-only stability mechanism.

## Artifacts

- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/wpr106_209_cross_flow_exhaustion_transfer_repair_summary.json`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/cross_flow_exhaustion_ranking.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/cross_flow_exhaustion_top2500.csv`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/cross_flow_exhaustion_monthly_returns.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/family_summary.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/preselected_pre_may.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_209_cross_flow_exhaustion_transfer_repair/selected_pre_may_may_comparison.parquet`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_209_cross_flow_exhaustion_transfer_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
