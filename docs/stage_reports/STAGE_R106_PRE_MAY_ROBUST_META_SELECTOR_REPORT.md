# Stage R106 Pre-May Robust Meta-Selector Report

Date: 2026-06-12
Packet: WPR106-138
Status: closed

## Boundary

This packet is research-only, observe-only, and promotion-ready false. It did
not write a candidate pack, paper/live artifact, order, sizing change, runtime
change, live configuration, CUDA speedup claim, or promotion claim.

May 2026 was held out of source-packet inclusion, row inclusion, robustness
score construction, threshold choice, ranking, and fixed selection. The runner
loaded May benchmark artifacts only after writing the fixed pre-May selection.

## Method

The runner
`data/research/wpr106_138_pre_may_robust_meta_selector/scripts/run_wpr106_138_pre_may_robust_meta_selector.py`
tests whether a pre-May-only robustness selector can improve holdout behavior
across prior 2024-forward selected rows.

Inputs:

- WPR106-130 prior-day level/gap selected rows.
- WPR106-131 volatility term-structure selected rows.
- WPR106-132 multi-horizon trend-state selected rows.
- WPR106-133 cross-symbol lead-lag selected rows.
- WPR106-134 microstructure state-transition selected rows.
- WPR106-135 microstructure annual-target portfolios.
- WPR106-136 cross-family KNN trade-veto overlays.
- WPR106-137 diversity-constrained KNN-veto ensembles.

The selector normalizes single-strategy, equal-sleeve portfolio, KNN-veto
overlay, and KNN-veto ensemble rows into one ranking table. It scores each row
using only 2024-01 through 2026-04 monthly evidence:

- annual losing-month counts;
- total losing months;
- worst and median month;
- rolling six-month loss counts and return floor;
- 2025-11 through 2026-04 late-window return;
- 2026 Jan-Apr return;
- active months and active days;
- trades per active day, allowing 1-5 as normal active behavior;
- drawdown, Sortino, cost-stress survival, and best-month concentration.

Strict rows require positive pre-May return, at least 50 trades, at least 40
active days, at least 20 active months, no more than two losing months in each
full year, no more than one losing month in Jan-Apr 2026, at most five losing
months total, no more than two losing months in any rolling six-month window,
worst month no worse than -0.08, max drawdown no worse than -0.12, best-month
share no more than 0.25, full cost-stress survival, and 0.25 to 5.0 trades per
active day.

## Results

Pre-May meta-selector screen:

- Input selected rows: 558.
- Source packets: 8.
- Row kinds: 4.
- Positive pre-May rows: 558.
- Selector-strict rows: 168.
- Selector-loose rows: 277.
- Fixed selected rows: 100 strict rows.

Strict rows by source packet:

- WPR106-137 diversity-constrained KNN-veto ensemble: 94.
- WPR106-135 microstructure annual-target portfolio: 61.
- WPR106-136 cross-family KNN trade-veto overlay: 12.
- WPR106-131 volatility term-structure: 1.

The fixed top-100 strict selection contains:

- 69 WPR106-137 KNN-veto ensemble rows.
- 31 WPR106-135 equal-sleeve portfolio rows.

The top selected row is:

- Row ID:
  `wpr106_137_diversity_constrained_knn_veto_ensemble:vetoensemble-b7901da9b03fc7df`.
- Source packet: WPR106-137.
- Row kind: KNN-veto ensemble.
- Selection rank in source packet: 10.
- Trades: 344.
- Active days: 305.
- Trades per active day: 1.127869.
- Active months: 26.
- Selector losing months: 2.
- Annual losses: 2024: 2, 2025: 0, 2026 Jan-Apr: 0.
- Pre-May net return: +0.820014.
- Max drawdown: -0.042254.
- Sortino daily: 0.599548.
- Best-month share: 0.080792.
- Late six-month return: +0.194012.
- Selector score: 4.474714.

May 2026 benchmark after fixed strict pre-May selection:

- May-positive selected rows: 20.
- May-negative selected rows: 80.
- May-flat selected rows: 0.
- Best May net return: +0.012709.
- Worst May net return: -0.035239.
- Median May net return: -0.009168.
- The top selected row returned -0.005679 in May over 21 trades and 20 active
  days.

The best May rows were WPR106-137 ensemble rows around selection ranks 48 to
51, each returning +0.012709. The worst May rows were also WPR106-137 ensemble
rows, led by `vetoensemble-5cac443ea8bae8cc` and
`vetoensemble-4aa4879bb0a72f8f`, each returning -0.035239.

## Decision

The pre-May robust meta-selector is rejected as a candidate lead. It gives the
old selected families, portfolios, KNN-veto overlays, and KNN-veto ensembles a
common stability-oriented screen and improves the May median versus the plain
WPR106-137 top-100 selection, but the fixed selected set still fails the
untouched May 2026 benchmark with 80% negative selected rows and a negative
median month.

Useful follow-up context: pre-May month-stability screening helps avoid the
most fragile rows but remains insufficient when the underlying selected pool is
dominated by KNN-veto ensembles and microstructure portfolios that share the
same broad May degradation. Future work should move back to fresh strategy
families or materially different features/exits rather than adding another
selector layer over these same selected rows.

## Artifacts

- `data/research/wpr106_138_pre_may_robust_meta_selector/wpr106_138_pre_may_robust_meta_selector_summary.json`
- `data/research/wpr106_138_pre_may_robust_meta_selector/pre_may/normalized_pre_may_rows.parquet`
- `data/research/wpr106_138_pre_may_robust_meta_selector/pre_may/normalized_pre_may_monthly_returns.parquet`
- `data/research/wpr106_138_pre_may_robust_meta_selector/pre_may/meta_selector_ranking.parquet`
- `data/research/wpr106_138_pre_may_robust_meta_selector/pre_may/meta_selector_top2000.csv`
- `data/research/wpr106_138_pre_may_robust_meta_selector/pre_may/selected_pre_may.parquet`
- `data/research/wpr106_138_pre_may_robust_meta_selector/pre_may/selected_pre_may.csv`
- `data/research/wpr106_138_pre_may_robust_meta_selector/pre_may/selected_pre_may_monthly_returns.parquet`
- `data/research/wpr106_138_pre_may_robust_meta_selector/may_benchmark/normalized_may_benchmark_rows.parquet`
- `data/research/wpr106_138_pre_may_robust_meta_selector/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_138_pre_may_robust_meta_selector/may_benchmark/selected_may_benchmark_metrics.csv`
- `data/research/wpr106_138_pre_may_robust_meta_selector/may_benchmark/selected_may_benchmark_monthly_returns.parquet`

## Validation

- `python -m compileall -q data/research/wpr106_138_pre_may_robust_meta_selector/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed

No CUDA path was used, and no speedup was claimed.
