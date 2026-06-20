# Stage R106 WPR106-150 Pair Relative-Value Regime/Exit Repair Report

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It does
not create a candidate pack, paper/live artifact, order-placement path, sizing
change, runtime-mode change, live configuration write, or promotion claim.

All regime gates, throttles, thresholds, exit choices, ranking, and selection
use only 2024-01-01 through 2026-04-30. May 2026 is benchmark-only after fixed
pre-May loose rows are selected. CUDA was not used and no CUDA speedup claim is
made.

## Method

WPR106-150 reuses the WPR106-125 true two-leg BTCUSDT/ETHUSDT pair context and
pair-return accounting. It does not rerun the full rejected relative-value
grid. It narrows around the WPR106-125 active pocket and adds:

- daily caps of 1 or 5 accepted pair trades per day;
- causal regime gates: all, stable-correlation, and flow-expansion states;
- a prior-completed-month loss throttle, `skip_after_loss1`;
- unit and rolling-1536 hedge ratios;
- fixed and score-flip exits;
- spread acceleration momentum, spread momentum, and relative-return momentum
  repair templates.

May replay carries the pre-May throttle state forward, so if April 2026 was a
loss under a fixed rule, the May benchmark can be flat because the rule
causally blocks May entries.

## Results

- Evaluated rows: 5,184.
- Positive pre-May rows: 986.
- Annual-target rows: 4.
- Loose pre-May rows: 8.
- Strict pre-May rows: 0.
- Selected rows: 8 loose rows.

The selected rows are all spread-acceleration momentum repair variants:

- Pre-May net return: +0.140573 to +0.234607.
- Trades: 84 to 134.
- Active months: 20 to 23.
- Losing months: 5 to 7.
- Annual losses: either 2024: 1, 2025: 3, 2026 Jan-Apr: 1 or 2024: 3, 2025: 3,
  2026 Jan-Apr: 1.
- Max drawdown: -0.022178 to -0.038389.
- Cost-stress survival: 4/4 scenarios.

The four annual-target rows are not viable leads: each has only 30 trades, 11
active months, +0.003453 pre-May return, best-month share 0.799766, and 1/4
cost-stress survival.

May 2026 benchmark after fixed pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 4.
- May-flat selected rows: 4.
- Best May return: 0.000000.
- Worst May return: -0.010919.
- Median May return: -0.005459.
- The four flat rows were fully skipped by the prior-month loss throttle.
- The four rolling-beta score-flip rows traded 6 times each and lost
  -0.010919, with 0/4 May cost-stress survival.

## Decision

WPR106-150 rejects the pair relative-value repair as candidate-ready or as a
new promising lead. The repair did improve the WPR106-125 pocket enough to
produce eight pre-May loose rows with lower drawdown, but it still fails the
ideal annual stability target and May does not support the repaired family.

The loss throttle is not a solution here. For unit-beta rows it turns May into
a flat no-trade month because April state blocks entries; for rolling-beta
rows May trades remain negative. The pair relative-value family remains useful
negative evidence unless a future packet brings materially different pair
universe, features, or execution logic.

## Artifacts

- `data/research/wpr106_150_pair_relative_value_regime_exit_repair/wpr106_150_pair_relative_value_regime_exit_repair_summary.json`
- `data/research/wpr106_150_pair_relative_value_regime_exit_repair/pre_may/repair_ranking.parquet`
- `data/research/wpr106_150_pair_relative_value_regime_exit_repair/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_150_pair_relative_value_regime_exit_repair/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_150_pair_relative_value_regime_exit_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_150_pair_relative_value_regime_exit_repair/scripts/run_wpr106_150_pair_relative_value_regime_exit_repair.py`

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_150_pair_relative_value_regime_exit_repair/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts result: 460 passed.
