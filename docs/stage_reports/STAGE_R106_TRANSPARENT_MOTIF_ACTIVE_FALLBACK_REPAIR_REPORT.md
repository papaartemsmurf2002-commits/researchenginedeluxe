# Stage R106 WPR106-221 Transparent Motif Active Fallback Repair Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent
Reconstructed: 2026-06-18 by WPR106-226 from `data/research/wpr106_221_transparent_motif_active_fallback_repair/wpr106_221_transparent_motif_active_fallback_repair_summary.json` and ledger evidence.

## Scope

WPR106-221 tested causal fallback sleeves for the transparent motif
replacement family. It loaded WPR106-201 opening-range and WPR106-212 motif
components before selection, excluded canonical WPR106-202 motif behavior, and
used May 2026 only after fixed selected rows were written.

## Results

- Evaluated pre-May rows: 13,824.
- Positive pre-May rows: 13,534.
- Annual-target rows: 24.
- Loose pre-May rows: 7,404.
- Strict pre-May rows: zero.
- Selected rows: 140.
- Selected pre-May: 140/140 positive, median +0.446878, active mean +0.416701.
- Selected pre-May median trades: 651.
- Selected pre-May median active months: 27.
- Selected pre-May median losing months: six.
- Selected pre-May strict rows: zero and annual-target rows: zero.

## May Benchmark

- Rows: 140.
- Active rows: 140.
- Positive rows: 113.
- Negative rows: 27.
- Flat rows: zero.
- Median May return: +0.011323.
- Active mean May return: +0.010638.
- Best/worst May return: +0.027940 / -0.027753.
- Median May trade count: 39.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. The active fallback repair is one of the better remaining
research leads because May transfer was positive and activity was broad. The
blocker is annual loss-month distribution, especially the 2024 loss count.

## Artifacts

- `data/research/wpr106_221_transparent_motif_active_fallback_repair/wpr106_221_transparent_motif_active_fallback_repair_summary.json`
- `data/research/wpr106_221_transparent_motif_active_fallback_repair/pre_may/selected_pre_may_fallback_repair_rows.parquet`
- `data/research/wpr106_221_transparent_motif_active_fallback_repair/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_221_transparent_motif_active_fallback_repair/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_221_transparent_motif_active_fallback_repair/selected_pre_may_may_comparison.parquet`

## Validation

Passed per ledger closeout:

```powershell
python -m compileall -q data\research\wpr106_221_transparent_motif_active_fallback_repair\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
