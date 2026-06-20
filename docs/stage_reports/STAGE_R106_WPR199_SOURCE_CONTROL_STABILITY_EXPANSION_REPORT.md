# Stage R106 WPR106-220 WPR199 Source-Control Stability Expansion Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent
Reconstructed: 2026-06-18 by WPR106-226 from `data/research/wpr106_220_wpr199_source_control_stability_expansion/wpr106_220_wpr199_source_control_stability_expansion_summary.json` and ledger evidence.

## Scope

WPR106-220 expanded the WPR106-219 same-direction WPR106-199 clue by testing
full WPR106-199 source controls and WPR106-188 negative controls. It evaluated
side filters, time filters, and causal source gates using only 2024-01-01
through 2026-04-30 for selection, then benchmarked fixed selected rows on
May 2026.

## Results

- Source rows selected: 120.
- Pre-May variant rows: 24,632.
- Positive pre-May rows: 21,833.
- Annual-target rows: 3,157.
- Strict pre-May rows: 152.
- Selected pre-May: 120/120 positive, median +0.637255, active mean +0.637288.
- Selected pre-May median trades: 318.
- Selected pre-May median active months: 26.
- Selected pre-May median losing months: four.
- Selected pre-May strict rows: 59 and annual-target rows: 83.

## May Benchmark

- Rows: 120.
- Active rows: 115.
- Positive rows: 29.
- Negative rows: 86.
- Flat rows: five.
- Median May return: -0.005859.
- Active mean May return: -0.007629.
- Best/worst May return: +0.014893 / -0.053315.
- Median May trade count: 11.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. The broad WPR106-199 expansion failed the May benchmark
despite a strong pre-May profile. WPR106-199 remains useful as a control or
ablation source, not as a dominant source for future selection.

## Artifacts

- `data/research/wpr106_220_wpr199_source_control_stability_expansion/wpr106_220_wpr199_source_control_stability_expansion_summary.json`
- `data/research/wpr106_220_wpr199_source_control_stability_expansion/pre_may/selected_pre_may_source_control_rows.parquet`
- `data/research/wpr106_220_wpr199_source_control_stability_expansion/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_220_wpr199_source_control_stability_expansion/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_220_wpr199_source_control_stability_expansion/selected_pre_may_may_comparison.parquet`

## Validation

Passed per ledger closeout:

```powershell
python -m compileall -q data\research\wpr106_220_wpr199_source_control_stability_expansion\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```
