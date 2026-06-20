# Stage R106 WPR106-223 Dense KNN Source Generation Search Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent
Reconstructed: 2026-06-18 by WPR106-226 from `data/research/wpr106_223_dense_knn_source_generation_search/wpr106_223_dense_knn_source_generation_search_summary.json` and ledger evidence.

## Scope

WPR106-223 generated fresh dense KNN source paths for ETHUSDT with packet-local
feature packs, Lorentzian/Euclidean distances, k values 7/17/31, 8/16-bar
holds, 384/768-bar lookbacks, session/regime filters, target signal rates
2/5/8 per day, daily caps 1/2/5, and causal monthly gates. May 2026 was
computed only after fixed selected rows.

## Results

- Evaluated pre-May base rows: 139,968.
- Base positive pre-May rows: 18,619.
- Base annual-target rows: 8,089.
- Base strict rows: zero.
- Monthly gated pre-May rows: 220.
- Gated positive rows: 196.
- Gated annual-target rows: 28.
- Gated strict rows: zero.
- Selected rows: 71.
- Selected pre-May: 71/71 positive, median +0.200877, active mean +0.254229.
- Selected pre-May median trades: 212.
- Selected pre-May median active months: 24.
- Selected pre-May median losing months: eight.
- Selected pre-May annual-target rows: five and strict rows: zero.

## May Benchmark

- Rows: 71.
- Active rows: 43.
- Positive rows: 43.
- Negative rows: zero.
- Flat rows: 28.
- Median May return: +0.001341.
- Active mean May return: +0.004476.
- Best/worst May return: +0.022261 / 0.000000.
- Median May trade count: two.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. Dense KNN source generation improved May participation but
worsened the pre-May loss-month profile. Future KNN work should address
feature/label construction and 2025 loss clustering before adding more gates.

## Artifacts

- `data/research/wpr106_223_dense_knn_source_generation_search/wpr106_223_dense_knn_source_generation_search_summary.json`
- `data/research/wpr106_223_dense_knn_source_generation_search/pre_may/selected_pre_may_dense_knn_rows.parquet`
- `data/research/wpr106_223_dense_knn_source_generation_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_223_dense_knn_source_generation_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_223_dense_knn_source_generation_search/selected_pre_may_may_comparison.parquet`

## Validation

Passed per ledger closeout:

```powershell
python -m compileall -q data\research\wpr106_223_dense_knn_source_generation_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
