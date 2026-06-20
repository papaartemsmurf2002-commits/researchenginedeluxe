# Stage R106 WPR106-222 Directional KNN Source Stability Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent
Reconstructed: 2026-06-18 by WPR106-226 from `data/research/wpr106_222_directional_knn_source_stability_repair/wpr106_222_directional_knn_source_stability_repair_summary.json` and ledger evidence.

## Scope

WPR106-222 revisited Lorentzian/KNN evidence at the source level rather than
only post-filtering selected old artifacts. It used WPR106-190 and WPR106-213
source paths, side/time/source gates, KNN bundles, daily caps, and portfolio
health gates. May 2026 was loaded only after fixed rows were written.

## Results

- Full source components: 200.
- Searched source components: 84.
- Source-gated variants: 5,518.
- Selected source variants: 60.
- Bundles: 266.
- Pre-May portfolio rows: 17,024.
- Positive pre-May rows: 17,024.
- Annual-target rows: 4,686.
- Strict pre-May rows: 380.
- Selected rows: 160.
- Selected pre-May: 160/160 positive, median +0.464644, active mean +0.488391.
- Selected pre-May median trades: 267.
- Selected pre-May median active months: 24.
- Selected pre-May median losing months: five.
- Selected pre-May strict rows: 68 and annual-target rows: 111.

## May Benchmark

- Rows: 160.
- Active rows: 137.
- Positive rows: 137.
- Negative rows: zero.
- Flat rows: 23.
- Median May return: +0.001407.
- Active mean May return: +0.001413.
- Best/worst May return: +0.009924 / 0.000000.
- Median May trade count: one.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. The source-level KNN repair produced the best KNN stability
evidence of this sequence, but May transfer was too sparse and selected rows
still had inactive pre-May months. Future KNN work should generate denser
source paths or change feature/model code before portfolio selection.

## Artifacts

- `data/research/wpr106_222_directional_knn_source_stability_repair/wpr106_222_directional_knn_source_stability_repair_summary.json`
- `data/research/wpr106_222_directional_knn_source_stability_repair/pre_may/selected_pre_may_source_gated_knn_rows.parquet`
- `data/research/wpr106_222_directional_knn_source_stability_repair/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_222_directional_knn_source_stability_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_222_directional_knn_source_stability_repair/selected_pre_may_may_comparison.parquet`

## Validation

Passed per ledger closeout:

```powershell
python -m compileall -q data\research\wpr106_222_directional_knn_source_stability_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
