# Stage R106 WPR106-114 Pre-May Rolling OOS Cluster-Veto Search Report

Date: 2026-06-11
Owner: Codex Research Agent
Status: closed

## Boundary

WPR106-114 is research-only, observe-only, and promotion-ready false. It uses
the WPR106-113 cross-family daily risk-throttle candidate universe as diagnostic
input, then applies stronger pre-May rolling pseudo-OOS and source-cluster
filters before inspecting May 2026. This is not a fully independent OOS
experiment because WPR106-113 generated its candidate universe from the full
pre-May window.

All validation, scoring, ranking, selection, source-cluster diagnostics, and
veto thresholds use only 2024-01-01 through 2026-04-30. May 2026 remains fully
out of tuning and is used only after fixed pre-May rows are selected.

## Method

The runner is:

`data/research/wpr106_114_pre_may_rolling_oos_cluster_veto_search/scripts/run_wpr106_114_pre_may_rolling_oos_cluster_veto_search.py`

Inputs are the WPR106-113 `combined_ranking.parquet`,
`combined_monthly_returns.parquet`, and `deduped_source_pool.parquet`
artifacts. The run evaluates the 40,320-row WPR106-113 portfolio universe
across rolling validation blocks:

- 2024 Q3, 2024 Q4
- 2025 Q1, Q2, Q3, Q4
- 2026 January through April

The diagnostic veto metrics include rolling validation return, losing rolling
blocks, late-2025/2026 return, failed-cluster member share, ETH member share,
packet concentration, source/family diversity, monthly losses, active rate,
drawdown, and cost-stress survival.

May benchmark replay reuses the WPR106-113 trade-level execution semantics for
the fixed selected rows. May labels, returns, distributions, timing, and source
behavior are not used before selection.

## Artifacts

Root:

`data/research/wpr106_114_pre_may_rolling_oos_cluster_veto_search/`

Key pre-May artifacts:

- `pre_may/rolling_oos_ranking.parquet`
- `pre_may/rolling_oos_fold_metrics.parquet`
- `pre_may/cluster_veto_summary.parquet`
- `pre_may/selected_pre_may.parquet`
- `pre_may/selected_pre_may_replay_metrics.parquet`
- `pre_may/selected_pre_may_monthly_returns.parquet`
- `pre_may/selected_pre_may_daily_returns.parquet`
- `pre_may/selected_pre_may_trades.parquet`

Key May benchmark artifacts:

- `may_benchmark/selected_may_benchmark_metrics.parquet`
- `may_benchmark/selected_may_benchmark_monthly_returns.parquet`
- `may_benchmark/selected_may_benchmark_daily_returns.parquet`
- `may_benchmark/selected_may_benchmark_trades.parquet`

## Results

Candidate rows evaluated: 40,320.

Pre-May screen:

- WPR106-113 base strict rows: 4,182.
- WPR106-113 base loose rows: 16,896.
- Rolling strict rows after WPR106-114 checks: 0.
- Rolling loose rows after WPR106-114 checks: 942.
- Selected rows: 68 rolling-loose rows across 17 unique member sets.
- Selected pre-May trades: 53,092.

The top selected row is `riskcombo-a9a222fd65016439`. It returns +0.631458
pre-May with 661 trades, 661 active days, 1.000 trades per active day,
28 active months, 4 losing months, annual losses of 2024: 2, 2025: 2, and
2026 Jan-Apr: 0, max drawdown -0.041733, full cost-stress survival,
rolling validation return +0.456776, and one losing rolling block.

The selected set remains concentrated:

- ETH member share: min 1.000, median 1.000, max 1.000.
- Failed-cluster share: min 0.750, median 0.833333, max 0.833333.
- Only 4 of 68 selected rows satisfy the target of no more than two losing
  months in both full pre-May years, 2024 and 2025.

May benchmark after fixed pre-May selection:

- May-positive selected rows: 0.
- May-negative selected rows: 68.
- May-flat selected rows: 0.
- Best selected May return: -0.010799
  (`riskcombo-79e578945c52123e`).
- Worst selected May return: -0.025147
  (`riskcombo-c3409722b9ad66d8`).
- Median selected May return: -0.013841.

## Interpretation

The rolling validation and cluster-veto pass removes the apparent WPR106-113
strict candidate surface: no portfolio row survives as rolling strict. The
fallback rolling-loose surface is still concentrated in the same ETH-heavy
failed source cluster, and every fixed selected row loses in May.

This rejects the current WPR106-113 candidate universe as candidate-ready
evidence. The result supports continuing the broader 2024-forward research
search, but not by defending the same ETH-heavy WPR106-106/108/109 sleeve unless
a future pre-May-only source-regime test explains why it should transfer.

No candidate pack, paper/live artifact, order placement, sizing change,
runtime-mode change, live configuration write, CUDA speedup claim, or promotion
claim exists.

## Validation

Passed:

```powershell
python -m compileall -q data/research/wpr106_114_pre_may_rolling_oos_cluster_veto_search/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Contracts reported 460 passed.
