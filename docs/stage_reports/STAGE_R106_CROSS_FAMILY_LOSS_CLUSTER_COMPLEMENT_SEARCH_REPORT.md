# Stage R106 WPR106-225 Cross-Family Loss-Cluster Complement Search Report

Status: closed
Date: 2026-06-13
Owner: Codex Research Agent
Reconstructed: 2026-06-18 by WPR106-226 from `data/research/wpr106_225_cross_family_loss_cluster_complement_search/wpr106_225_cross_family_loss_cluster_complement_search_summary.json` and ledger evidence.

## Scope

WPR106-225 tested cross-family costed selected trade paths from WPR106-220,
WPR106-221, WPR106-222, and WPR106-224. It evaluated singles, cross-family
pairs, triples, and quads with equal, stability-weighted, and
loss-complement-weighted allocations, same-symbol no-overlap handling, and
portfolio daily caps of 2, 3, and 5 trades/day. May 2026 was benchmark-only.

## Results

- Source rows: 560.
- Source pre-May trades: 215,710.
- Source component pool: 56.
- Portfolio specs: 14,040.
- Positive pre-May ranking rows: 13,914.
- Loose rows: 10,648.
- Annual-target rows: 4,236.
- Strict rows: 1,569.
- Selected rows: 180.
- Selected pre-May: 180/180 positive, median +0.612399, active mean +0.631866.
- Selected pre-May median trades: 502.
- Selected pre-May total trades: 81,925.
- Selected pre-May median active months: 27.
- Selected pre-May median losing months: four.
- Selected pre-May strict rows: 80 and annual-target rows: 140.

## May Benchmark

- Rows: 180.
- Active rows: 180.
- Positive rows: two.
- Negative rows: 178.
- Flat rows: zero.
- Median May return: -0.005795.
- Active mean May return: -0.006737.
- Best/worst May return: +0.008411 / -0.018541.
- Median May trade count: 17.
- Total selected May trades: 3,080.

## Decision

Rejected as candidate-ready, portfolio-ready, paper/live-ready, or
promotion-ready. The pre-May strict/annual profile failed the May benchmark.
Every selected portfolio included WPR106-220; every selected cross-family
complement row was negative in May. WPR106-220 should remain a control or
ablation source, not a dominant selector source.

## Artifacts

- `data/research/wpr106_225_cross_family_loss_cluster_complement_search/wpr106_225_cross_family_loss_cluster_complement_search_summary.json`
- `data/research/wpr106_225_cross_family_loss_cluster_complement_search/controls/source_component_pool.parquet`
- `data/research/wpr106_225_cross_family_loss_cluster_complement_search/controls/portfolio_spec_manifest.parquet`
- `data/research/wpr106_225_cross_family_loss_cluster_complement_search/pre_may/selected_pre_may_cross_family_rows.parquet`
- `data/research/wpr106_225_cross_family_loss_cluster_complement_search/pre_may/selected_pre_may_trades.parquet`
- `data/research/wpr106_225_cross_family_loss_cluster_complement_search/may_benchmark/selected_may_benchmark_metrics.parquet`
- `data/research/wpr106_225_cross_family_loss_cluster_complement_search/selected_pre_may_may_comparison.parquet`

## Validation

Passed:

```powershell
python -m compileall -q data\research\wpr106_225_cross_family_loss_cluster_complement_search\scripts
python -m compileall -q src\tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests\contracts -q
```

Contracts reported 460 passed.
