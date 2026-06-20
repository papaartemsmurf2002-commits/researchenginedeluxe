# Stage R106 WPR133 Relative-Strength Overlay Causal Audit Report

Date: 2026-06-12
Packet: WPR106-146
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

All KNN parameter grids, row rankings, controls, and selected rows used only
2024-01-01 through 2026-04-30. May 2026 was replayed only after fixed pre-May
rows and controls were written.

## Method

The runner
`data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/scripts/run_wpr106_146_wpr133_relative_strength_overlay_causal_audit.py`
imports the existing WPR106-137/WPR106-136 artifact helpers and audits the
target WPR106-137 overlay `tradeveto-3a585c9bd5b09303`, sourced from
`wpr133_leadlag:leadlag-18708dffa1413dce`.

Controls:

- raw WPR106-133 source trades before KNN/no-veto filtering at daily caps 1,
  3, and 5;
- exact WPR106-137 KNN parameters at daily caps 1, 3, and 5;
- long-only and short-only raw/KNN diagnostic side controls;
- 12,000 nearby KNN parameter rows over `path_flow` and `regime_reversal`,
  Lorentzian and Euclidean distance, 64/96/160/240/320-trade lookbacks,
  5/7/15/31 neighbors, all-side or same-side history, neighbor mean/win-rate
  thresholds, and daily caps 1, 3, and 5;
- selected-row behavior hashing and pre-May drop-best/drop-worst/drop-most
  active month sensitivity.

May replay used WPR106-136 frozen pre-May history for KNN scoring.

## Results

Exact WPR106-137 overlay baseline:

- Cap 3 exact overlay: 203 pre-May trades, 26 active months, 5 losing months,
  annual losses 2024: 1, 2025: 3, 2026 Jan-Apr: 1, +1.130996 pre-May net
  return, -0.136225 max drawdown, 0.157747 best-month share, full cost-stress
  survival, and +0.059766 May with 11 trades.
- It remains pre-May profile-ok but not strict because 2025 has 3 losing
  months and the annual target is missed.

Raw-source and side controls:

- Raw no-KNN source cap 3/5: 451 pre-May trades, 7 losing months, annual
  losses 2024: 4, 2025: 3, 2026 Jan-Apr: 0, +1.209539 pre-May, and +0.065272
  May with 17 trades.
- Raw cap 1: +1.007245 pre-May with 9 losing months and +0.048701 May.
- Raw long-only controls are May-negative and pre-May unstable: cap 3 has
  +0.533107 pre-May with 9 losing months and -0.001938 May.
- Raw short-only controls are May-positive but pre-May unstable: cap 3 has
  +0.676432 pre-May with 11 losing months and +0.067211 May.
- Exact KNN long/short side controls are May-positive but fail pre-May
  profile checks, so the stable behavior is not explained by a standalone
  one-sided rule.

Parameter neighborhood:

- Grid rows: 12,000.
- Pre-May profile-ok rows: 4,377.
- WPR106-146 strict-like rows: 45.
- WPR106-136 strict rows: 30.
- Selected fixed rows: 48, consisting of the 45 strict-like rows plus exact
  WPR106-137 baseline-parameter rows.
- Selected rows May-positive: 48/48.
- Best selected May: +0.067949.
- Median selected May: +0.051377.
- Worst selected May: +0.015398.

The top selected row is a `regime_reversal` feature-pack, Lorentzian,
same-side KNN variant with 64-trade lookback, 31 neighbors, neighbor mean
threshold -0.00025, neighbor win-rate threshold 0.46, and cap 3/5. It records:

- 242 pre-May trades;
- 25 active months;
- 4 losing months;
- annual losses 2024: 2, 2025: 2, 2026 Jan-Apr: 0;
- +1.140510 pre-May net return;
- -0.145973 max drawdown;
- 0.170868 best-month share;
- full cost-stress survival;
- +0.067949 May with 16 trades.

Behavior and cluster diagnostics:

- The 48 selected rows reduce to 17 unique pre-May behavior hashes and 8 unique
  May behavior hashes.
- The largest May behavior group contains 20 selected rows.
- The top selected row takes 16 of the raw source cap-3 May trades and excludes
  one raw-source negative short trade from 2026-05-23; its May improvement over
  the raw source is therefore small and path-coupled, not independent.
- Drop-month sensitivity over selected rows produced 144 diagnostics; all
  remained profile-ok and 122 remained strict-like.
- For the top selected row, dropping the best pre-May month still leaves
  +0.899073 pre-May, 24 active months, 4 losing months, annual losses
  2/2/0, and strict-like status.

## Decision

WPR106-146 upgrades the WPR106-133 relative-strength member from "May-positive
contributor inside a rejected ensemble" to a narrow research-only lead that
deserves more direct follow-up. The nearby `regime_reversal` + Lorentzian +
same-side KNN variants improve month-to-month stability and keep May positive
without using May for tuning.

It is still not candidate-ready. The May benchmark is substantially explained
by the same raw WPR106-133 source trade path, selected variants are behavior
clustered, and the source family was originally rejected as a broad fixed
family. The next useful work is not a candidate-pack attempt; it should run a
source-level causal stability packet around this ETH relative-strength lead,
including behavior-deduped parameter selection, additional pre-May rolling
holdouts, source-row neighbor controls, and portfolio/hedge tests that do not
reuse May for tuning.

## Artifacts

- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/wpr106_146_wpr133_relative_strength_overlay_causal_audit_summary.json`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/control_metrics.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/control_metrics.csv`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/selected_metrics.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/selected_metrics.csv`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/selected_behavior_diagnostics.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/pre_may/parameter_grid_pre_may_metrics.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/pre_may/parameter_grid_pre_may_top1000.csv`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/pre_may/selected_pre_may_parameter_rows.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/pre_may/selected_pre_may_replay_metrics.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/pre_may/selected_pre_may_month_sensitivity.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/may_benchmark/selected_may_benchmark_trades.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_146_wpr133_relative_strength_overlay_causal_audit/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
