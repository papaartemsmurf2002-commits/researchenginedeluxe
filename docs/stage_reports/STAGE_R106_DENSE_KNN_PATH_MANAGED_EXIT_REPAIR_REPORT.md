# Stage R106 WPR106-224 Dense KNN Path-Managed Exit Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent
Reconstructed: 2026-06-18 by WPR106-226 from `data/research/wpr106_224_dense_knn_path_managed_exit_repair/wpr106_224_dense_knn_path_managed_exit_repair_summary.json` and ledger evidence.

## Scope

WPR106-224 tested packet-local path-managed exits over fixed WPR106-223 dense
KNN selected paths. The packet used side-specific path favorable/adverse
returns and evaluated fixed-hold, stop-only, target-only, and conservative
target/stop policies. May 2026 was loaded only after fixed selected rows.

## Results

- Source selected rows: 71.
- Source pre-May trade rows: 21,060.
- Exit policies: 36.
- Pre-May policy rows: 2,556.
- Positive pre-May rows: 552.
- Annual-target rows: 16.
- Strict rows: zero.
- Selected rows: 140.
- Selected pre-May: 140/140 positive, median +0.314421, active mean +0.350790.
- Selected pre-May median trades: 219.
- Selected pre-May median active months: 21.
- Selected pre-May median losing months: seven.
- Selected pre-May annual-target rows: 16 and strict rows: zero.

## May Benchmark

- Rows: 140.
- Active rows: 73.
- Positive rows: 73.
- Negative rows: zero.
- Flat rows: 67.
- Median May return: +0.000994.
- Active mean May return: +0.006685.
- Best/worst May return: +0.022261 / 0.000000.
- Median May trade count: one.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. Simple target-only exits were more promising than
target/stop combinations, and `flow_wick_density` with two-loss-month veto
remains the strongest dense KNN transfer clue. The blocker is still 2025 loss
clustering and active coverage before exits.

## Artifacts

- `data/research/wpr106_224_dense_knn_path_managed_exit_repair/wpr106_224_dense_knn_path_managed_exit_repair_summary.json`
- `data/research/wpr106_224_dense_knn_path_managed_exit_repair/pre_may/selected_pre_may_path_managed_exit_rows.parquet`
- `data/research/wpr106_224_dense_knn_path_managed_exit_repair/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_224_dense_knn_path_managed_exit_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_224_dense_knn_path_managed_exit_repair/selected_pre_may_may_comparison.parquet`

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_224_dense_knn_path_managed_exit_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
