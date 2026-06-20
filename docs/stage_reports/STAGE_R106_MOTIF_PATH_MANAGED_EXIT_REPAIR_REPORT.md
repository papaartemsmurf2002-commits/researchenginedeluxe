# Stage R106 WPR106-193 Motif Path-Managed Exit Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent

## Scope

WPR106-193 followed WPR106-192 by testing whether conservative path-managed
exits could repair the active May motif clue without changing the May-blind
source entries. It used the fixed WPR106-192 selected motif source rows and
replayed only exit-policy variants.

All source inclusion, stop/target choices, maximum-hold choices, row ranking,
and selected-row inclusion used only 2024-01-01 through 2026-04-30 UTC. May
2026 was replayed only after fixed pre-May exit-policy selection.

## Implementation

The artifact-only runner is:

- `data/research/wpr106_193_motif_path_managed_exit_repair/scripts/run_wpr106_193_motif_path_managed_exit_repair.py`

The runner imports the WPR106-192 runner and WPR106-170 helpers to rebuild the
same WPR106-96 BTCUSDT/ETHUSDT source contexts, motif lookup state, cost model,
and monthly/accounting diagnostics. It keeps WPR106-192 motif entries fixed and
changes only the exit surface.

The path-managed exit policy uses primary 15m OHLC bars inside the holding
window:

- entry at the next bar open;
- stop-loss and take-profit barriers checked from entry bar through the bar
  before scheduled time exit;
- if stop and target are both touched in the same 15m bar, stop is assumed
  first;
- time exit at scheduled maximum-hold open if no barrier is hit;
- same-symbol overlap blocking uses the actual earlier exit index.

The grid evaluates the fixed-hold baseline plus stop/target primary-bar exits
over stop losses of 0.6%, 1.0%, 1.5%, and 2.5%; take profits of 0.8%, 1.2%,
1.8%, and 3.0%; and half/full maximum-hold fractions. CUDA was not used and no
speedup claim was made.

## Results

Pre-May screen:

- 74 WPR106-192 source rows.
- 33 exit policies per source.
- 2,442 evaluated exit rows.
- 524 positive pre-May rows.
- 0 annual-target rows.
- 5 loose rows.
- 0 strict rows.

Pre-May by exit policy:

- `fixed_hold_baseline`: 74 rows, 74 positive, 0 loose, 0 strict, best
  +0.489121, median +0.205355, median drawdown -0.447557.
- `stop_target_primary_bar`: 2,368 rows, 450 positive, 5 loose, 0 strict, best
  +0.337281, median -0.234951, median drawdown -0.405830.

The five loose rows were BTCUSDT `flow_absorption` stop/target variants with
0.8% take profit and 1.5% or 2.5% stop loss. Their drawdowns improved to
roughly -0.025554 to -0.033726 and their pre-May returns were +0.065745 to
+0.083917. They were not fixed-selected because they had only two active
latest-four pre-May months, 16 to 17 latest-four trades, and did not meet the
annual-target standard.

Fixed selected set:

- 97 selected rows.
- All 97 are `positive_recent_stability` fallback rows.
- 88 ETHUSDT rows and 9 BTCUSDT rows.
- Exit policy mix: 62 `fixed_hold_baseline` rows and 35
  `stop_target_primary_bar` rows.

Selected pre-May replay:

- 97 positive rows, 0 negative rows, 0 flat rows.
- Median net return: +0.201987.
- Active mean net return: +0.209225.
- Best/worst selected rows: +0.489121 / +0.028659.

May 2026 benchmark replay:

- 97 active rows.
- 46 positive rows and 51 negative rows.
- Median net return: -0.002639.
- Active mean net return: +0.004805.
- Best/worst selected rows: +0.090413 / -0.074075.

May by selected exit policy:

- `fixed_hold_baseline`: 62 rows, 39 positive and 23 negative, May median
  +0.011492, best +0.090413, worst -0.030529.
- `stop_target_primary_bar`: 35 rows, 7 positive and 28 negative, May median
  -0.004568, best +0.014049, worst -0.074075.

The best May row was still the original ETHUSDT `trend_pullback_clock`
fixed-hold baseline sourced from WPR106-192 row `motif192-e04007619d5902f3`.
It had +0.439334 pre-May and +0.090413 in May, but retained 14 pre-May losing
months and -0.439939 pre-May max drawdown.

## Interpretation

WPR106-193 is rejected as candidate-ready, portfolio-ready, or
promotion-ready. Conservative primary-bar stop/target exits reduced drawdown
for a few BTCUSDT flow-absorption rows, but those rows were sparse and stale.
For the active ETHUSDT motif rows that drove WPR106-192's May transfer,
path-managed exits did not improve the holdout: selected stop/target rows had
a negative May median and far worse positive/negative balance than fixed hold.

The useful diagnostic is negative: the WPR106-192 active May clue is not
repaired by simple stop/target path exits. Future work should change source
logic, risk state, portfolio construction, or another family rather than
promote these exit variants.

## Artifacts

- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/motif_exit_pre_may_ranking.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/motif_exit_pre_may_ranking.csv`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/motif_exit_pre_may_monthly_returns.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/selected_pre_may_exit_rows.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/selected_pre_may_exit_rows.csv`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/selected_pre_may_replay_metrics.csv`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/selected_pre_may_daily_returns.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_193_motif_path_managed_exit_repair/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/may_benchmark/selected_may_benchmark_trades.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/selected_pre_may_may_comparison.parquet`
- `data/research/wpr106_193_motif_path_managed_exit_repair/selected_pre_may_may_comparison.csv`
- `data/research/wpr106_193_motif_path_managed_exit_repair/wpr106_193_motif_path_managed_exit_repair_summary.json`
- `data/research/wpr106_193_motif_path_managed_exit_repair/wpr106_193_run_stdout.log`
- `data/research/wpr106_193_motif_path_managed_exit_repair/wpr106_193_run_stderr.log`

## Research Boundary

All outputs remain `research_only`, `observe_only`, and
`promotion_ready: false`. No candidate pack, paper/live artifact, order path,
sizing change, runtime-mode change, live configuration write, CUDA speedup
claim, or promotion claim was created.

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_193_motif_path_managed_exit_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
